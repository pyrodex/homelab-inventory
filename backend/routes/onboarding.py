"""
IPAM "Add to monitoring": probe an address and create/enable monitoring.
"""
import ipaddress
import logging

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError as MarshmallowValidationError

from models import Device, DeviceHistory, IpObservation, Location, Monitor, Subnet, db
from services import onboarding
from services.ipam import build_address_index
from utils.history import compute_diff, extract_device_state
from utils.tags import parse_tag_input, resolve_tags
from validators import DeviceSchema, MonitorSchema

onboarding_bp = Blueprint('onboarding', __name__)

MAX_MONITORS = 20


def register_onboarding_routes(app, limiter):
    app.register_blueprint(onboarding_bp, url_prefix='/api/ipam')
    limiter.limit("30 per minute")(probe)
    limiter.limit("30 per minute")(add_to_monitoring)


def _parse_ip(value):
    try:
        return str(ipaddress.ip_address(str(value or '').strip()))
    except ValueError:
        return None


def _existing_device(ip):
    """A device whose IP or monitor endpoint uses this address (first by id)."""
    index = build_address_index(Device.query.all())
    parsed = ipaddress.ip_address(ip)
    refs = index.get(parsed.version, {}).get(int(parsed), [])
    if not refs:
        return None
    return db.session.get(Device, min(r['device_id'] for r in refs))


@onboarding_bp.route('/probe', methods=['POST'])
def probe():
    """
    Probe one address for "Add to monitoring". The address must be inside a
    defined subnet, so this can't be used to scan arbitrary hosts.
    """
    data = request.get_json(silent=True) or {}
    ip = _parse_ip(data.get('ip'))
    if not ip:
        return jsonify({'error': 'Validation error', 'details': {'ip': ['A valid IP address is required']}}), 400
    subnet = onboarding.subnet_containing(ip, Subnet.query.all())
    if subnet is None:
        return jsonify({'error': 'Validation error',
                        'details': {'ip': ['Only addresses inside a defined subnet can be probed']}}), 400

    result = onboarding.probe_address(ip)
    result['suggested'] = onboarding.suggest(result)
    obs = IpObservation.query.filter_by(ip=ip).first()
    hostname = (obs.dhcp_hostname or obs.ptr_hostname or obs.ping_hostname or obs.hostname) if obs else None
    result['hostname'] = hostname or result['ptr']
    result['suggested']['name'] = onboarding.default_name(ip, result['ptr'], hostname)
    result['subnet'] = {'id': subnet.id, 'cidr': subnet.cidr, 'name': subnet.name,
                        'location_id': subnet.location_id}
    device = _existing_device(ip)
    result['device'] = device.to_dict() if device else None
    return jsonify(result)


def _validate_monitors(raw):
    if not isinstance(raw, list) or not raw:
        return None, {'monitors': ['Pick at least one monitor']}
    if len(raw) > MAX_MONITORS:
        return None, {'monitors': [f'At most {MAX_MONITORS} monitors']}
    schema = MonitorSchema()
    clean, errors = [], {}
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            errors[str(i)] = ['Each monitor must be an object']
            continue
        try:
            m = schema.load({k: v for k, v in item.items() if k in ('monitor_type', 'endpoint', 'port', 'notes')})
            clean.append({'monitor_type': m['monitor_type'], 'port': m.get('port'),
                          'endpoint': m.get('endpoint'), 'notes': m.get('notes')})
        except MarshmallowValidationError as err:
            errors[str(i)] = err.messages
    if errors:
        return None, {'monitors': errors}
    return onboarding.dedupe_monitors(clean), None


@onboarding_bp.route('/monitor', methods=['POST'])
def add_to_monitoring():
    """
    One transaction for both cases:
      * device_id given  -> turn monitoring on and add monitors (duplicates skipped)
      * no device_id     -> create the device at `ip` with these monitors
    Body: {ip, device_id?, name?, device_type?, deviceFunction?, location_id?, tags?, monitors:[...]}
    """
    data = request.get_json(silent=True) or {}
    monitors, errors = _validate_monitors(data.get('monitors'))
    if errors:
        return jsonify({'error': 'Validation error', 'details': errors}), 400

    try:
        if data.get('device_id'):
            device = db.session.get(Device, int(data['device_id']))
            if device is None:
                return jsonify({'error': 'Device not found'}), 404
            before = extract_device_state(device)
            existing = {(m.monitor_type, m.port, m.endpoint) for m in device.monitors}
            added = []
            for m in monitors:
                key = (m['monitor_type'], m['port'], m['endpoint'])
                if key in existing:
                    continue
                device.monitors.append(Monitor(enabled=True, **m))
                added.append(m['monitor_type'])
            device.monitoring_enabled = True
            diff = compute_diff(before, extract_device_state(device))
            parts = []
            if 'monitoring_enabled' in diff:
                parts.append('enabled monitoring')
            if added:
                parts.append('added ' + ', '.join(added))
            db.session.add(DeviceHistory(
                device_id=device.id, change_type='update', diff=diff,
                summary=f"IPAM: {' and '.join(parts) or 'no changes'} for '{device.name}'",
            ))
            db.session.commit()
            return jsonify({'created': False, 'added_monitors': added, 'device': device.to_dict()}), 200

        ip = _parse_ip(data.get('ip'))
        if not ip:
            return jsonify({'error': 'Validation error', 'details': {'ip': ['A valid IP address is required']}}), 400
        conflict = _existing_device(ip)
        if conflict is not None:
            return jsonify({'error': f"{ip} is already used by '{conflict.name}'",
                            'device': conflict.to_dict()}), 409

        try:
            tag_names = parse_tag_input(data.get('tags'))
        except ValueError as exc:
            return jsonify({'error': 'Validation error', 'details': {'tags': [str(exc)]}}), 400
        location_id = data.get('location_id') or None
        if location_id is not None and not db.session.get(Location, int(location_id)):
            return jsonify({'error': 'Validation error', 'details': {'location_id': ['Location not found']}}), 400

        payload = {
            'name': (data.get('name') or '').strip() or ip,
            'device_type': data.get('device_type') or 'icmp_only',
            'ip_address': ip,
            'deviceFunction': (data.get('deviceFunction') or '').strip() or 'Added from IPAM',
            'location_id': location_id,
            'networks': data.get('networks') or None,
            'monitoring_enabled': True,
        }
        try:
            clean = DeviceSchema().load(payload)
        except MarshmallowValidationError as err:
            return jsonify({'error': 'Validation error', 'details': err.messages}), 400

        device = Device(**clean)
        device.tags = resolve_tags(tag_names)
        for m in monitors:
            device.monitors.append(Monitor(enabled=True, **m))
        db.session.add(device)
        db.session.flush()
        db.session.add(DeviceHistory(
            device_id=device.id, change_type='create',
            summary=f"Created device '{device.name}' from IPAM with "
                    f"{', '.join(m['monitor_type'] for m in monitors)} monitoring",
            diff=compute_diff(None, extract_device_state(device)),
        ))
        db.session.commit()
        return jsonify({'created': True, 'added_monitors': [m['monitor_type'] for m in monitors],
                        'device': device.to_dict()}), 201
    except Exception as exc:
        db.session.rollback()
        logging.error(f"Add to monitoring failed: {exc}", exc_info=True)
        return jsonify({'error': 'Failed to add monitoring due to an internal error'}), 500
