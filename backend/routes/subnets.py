"""
Subnet / IPAM routes.

Subnets are defined in CIDR notation; utilization is computed on the fly from
device IP addresses and monitor endpoints, so there is nothing to keep in sync.
"""
import ipaddress
import logging

import hmac
import os

from flask import Blueprint, current_app, jsonify, request
from marshmallow import ValidationError as MarshmallowValidationError
from sqlalchemy.orm import selectinload

from exceptions import ConflictError, DatabaseError
from models import Device, IpObservation, Location, Subnet, db
from services import dhcp_leases, ipam_scan
from services.ipam import (
    analyze_subnet,
    build_address_index,
    build_observation_index,
    extract_ip,
    find_unassigned,
    next_free,
    normalize_cidr,
    parse_reserved,
)
from validators import SubnetSchema

subnets_bp = Blueprint('subnets', __name__)

MAX_NEXT_FREE = 256


def register_subnet_routes(app, limiter):
    """Register subnet routes with the app"""
    app.register_blueprint(subnets_bp, url_prefix='/api')

    limiter.limit("30 per minute")(create_subnet)
    limiter.limit("30 per minute")(update_subnet)
    limiter.limit("30 per minute")(delete_subnet)
    limiter.limit("10 per minute")(start_scan)
    limiter.limit("60 per minute")(upload_leases)


def _load_devices():
    return Device.query.options(selectinload(Device.monitors)).all()


def _load_observations():
    return build_observation_index(IpObservation.query.all(), stale_after=ipam_scan.stale_after())


def _sort_key(subnet):
    try:
        net = ipaddress.ip_network(subnet.cidr, strict=False)
        return (net.version, int(net.network_address), net.prefixlen)
    except ValueError:
        return (99, 0, 0)


def _validate_payload(data, existing_id=None, partial=False):
    """
    Validate and normalize a subnet payload. Returns (clean_data, error_response).
    """
    schema = SubnetSchema(partial=partial)
    try:
        clean = schema.load(data)
    except MarshmallowValidationError as err:
        return None, (jsonify({'error': 'Validation error', 'details': err.messages}), 400)

    details = {}
    network = None

    if 'cidr' in clean:
        try:
            clean['cidr'] = normalize_cidr(clean['cidr'])
            network = ipaddress.ip_network(clean['cidr'])
        except ValueError as exc:
            details['cidr'] = [str(exc)]
    elif existing_id is not None:
        network = ipaddress.ip_network(Subnet.query.get(existing_id).cidr)

    if network is not None:
        gateway = clean.get('gateway')
        if gateway:
            gw = extract_ip(gateway)
            if gw is None or gw.version != network.version or gw not in network:
                details['gateway'] = [f"Gateway must be an IP address inside {network}"]
            else:
                clean['gateway'] = str(gw)

        reserved = clean.get('reserved_ranges')
        if reserved:
            try:
                parse_reserved(reserved, network)
            except ValueError as exc:
                details['reserved_ranges'] = [str(exc)]

    if clean.get('location_id') is not None and not Location.query.get(clean['location_id']):
        details['location_id'] = ['Location not found']

    if clean.get('scan_enabled') and network is not None:
        reason = ipam_scan.scan_eligibility(str(network))
        if reason:
            details['scan_enabled'] = [reason]

    if details:
        return None, (jsonify({'error': 'Validation error', 'details': details}), 400)

    if 'cidr' in clean:
        dup = Subnet.query.filter_by(cidr=clean['cidr']).first()
        if dup and dup.id != existing_id:
            return None, (jsonify(ConflictError(f"Subnet {clean['cidr']} already exists").to_dict()), 409)

    return clean, None


@subnets_bp.route('/subnets', methods=['GET'])
def get_subnets():
    """List subnets with utilization summaries"""
    subnets = sorted(Subnet.query.all(), key=_sort_key)
    index = build_address_index(_load_devices())
    observations = _load_observations()
    payload = []
    for subnet in subnets:
        analysis = analyze_subnet(subnet, index, observations)
        item = subnet.to_dict()
        item['summary'] = analysis['summary']
        item['version'] = analysis['version']
        item['conflict_count'] = len(analysis['conflicts'])
        item['reserved_error'] = analysis['reserved_error']
        item['scan_running'] = ipam_scan.is_running(subnet.id)
        item['scan_eligible'] = ipam_scan.scan_eligibility(subnet.cidr) is None
        payload.append(item)
    return jsonify(payload)


@subnets_bp.route('/subnets/unassigned', methods=['GET'])
def get_unassigned_devices():
    """Devices whose IP address is not inside any defined subnet"""
    devices = Device.query.all()
    return jsonify(find_unassigned(devices, Subnet.query.all()))


@subnets_bp.route('/subnets/<int:subnet_id>', methods=['GET'])
def get_subnet(subnet_id):
    """Full utilization detail for one subnet (per-address listing for small subnets)"""
    subnet = Subnet.query.get_or_404(subnet_id)
    analysis = analyze_subnet(subnet, build_address_index(_load_devices()), _load_observations())
    reason = ipam_scan.scan_eligibility(subnet.cidr)
    analysis['scan'] = {
        'running': ipam_scan.is_running(subnet.id),
        'eligible': reason is None,
        'ineligible_reason': reason,
        'stale_after_hours': ipam_scan.stale_after().total_seconds() / 3600,
    }
    return jsonify(analysis)


@subnets_bp.route('/subnets/<int:subnet_id>/next-free', methods=['GET'])
def get_next_free(subnet_id):
    """Return the next N free addresses (default 1, max 256)"""
    subnet = Subnet.query.get_or_404(subnet_id)
    try:
        count = int(request.args.get('count', 1))
    except (TypeError, ValueError):
        return jsonify({'error': 'count must be an integer'}), 400
    count = max(1, min(count, MAX_NEXT_FREE))
    analysis = analyze_subnet(subnet, build_address_index(_load_devices()), _load_observations())
    return jsonify({
        'subnet_id': subnet.id,
        'cidr': subnet.cidr,
        'addresses': next_free(analysis, count),
        'free_total': analysis['summary']['free'],
    })


@subnets_bp.route('/subnets', methods=['POST'])
def create_subnet():
    """Create a subnet"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    clean, error = _validate_payload(data)
    if error:
        return error

    subnet = Subnet(**clean)
    try:
        db.session.add(subnet)
        db.session.commit()
        return jsonify(subnet.to_dict()), 201
    except Exception as exc:
        db.session.rollback()
        logging.error(f"Failed to create subnet: {exc}")
        raise DatabaseError("Failed to create subnet due to an internal error.")


@subnets_bp.route('/subnets/<int:subnet_id>', methods=['PUT'])
def update_subnet(subnet_id):
    """Update a subnet"""
    subnet = Subnet.query.get_or_404(subnet_id)
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    updatable = ['cidr', 'name', 'description', 'vlan_id', 'gateway', 'reserved_ranges', 'location_id',
                 'scan_enabled', 'scan_interval_minutes']
    filtered = {k: v for k, v in data.items() if k in updatable}
    clean, error = _validate_payload(filtered, existing_id=subnet_id, partial=True)
    if error:
        return error

    # If only the CIDR changed, re-check existing gateway/reservations against it
    if 'cidr' in clean:
        network = ipaddress.ip_network(clean['cidr'])
        gateway = clean.get('gateway', subnet.gateway)
        gw = extract_ip(gateway) if gateway else None
        if gateway and (gw is None or gw.version != network.version or gw not in network):
            return jsonify({'error': 'Validation error',
                            'details': {'gateway': [f"Gateway {gateway} is not inside {network}"]}}), 400
        try:
            parse_reserved(clean.get('reserved_ranges', subnet.reserved_ranges), network)
        except ValueError as exc:
            return jsonify({'error': 'Validation error', 'details': {'reserved_ranges': [str(exc)]}}), 400
        if clean.get('scan_enabled', subnet.scan_enabled):
            reason = ipam_scan.scan_eligibility(str(network))
            if reason:
                return jsonify({'error': 'Validation error', 'details': {'scan_enabled': [reason]}}), 400

    for key, value in clean.items():
        setattr(subnet, key, value)
    try:
        db.session.commit()
        return jsonify(subnet.to_dict())
    except Exception as exc:
        db.session.rollback()
        logging.error(f"Failed to update subnet: {exc}")
        raise DatabaseError("Failed to update subnet due to an internal error.")


@subnets_bp.route('/subnets/<int:subnet_id>', methods=['DELETE'])
def delete_subnet(subnet_id):
    """Delete a subnet (devices are untouched)"""
    subnet = Subnet.query.get_or_404(subnet_id)
    try:
        db.session.delete(subnet)
        db.session.commit()
        return '', 204
    except Exception as exc:
        db.session.rollback()
        logging.error(f"Failed to delete subnet: {exc}")
        raise DatabaseError("Failed to delete subnet due to an internal error.")


# --- Ping sweeps ------------------------------------------------------------

@subnets_bp.route('/subnets/<int:subnet_id>/scan', methods=['POST'])
def start_scan(subnet_id):
    """Start a ping sweep now (runs in the background)."""
    subnet = Subnet.query.get_or_404(subnet_id)
    reason = ipam_scan.scan_eligibility(subnet.cidr)
    if reason:
        return jsonify({'error': reason}), 400
    if not ipam_scan.scan_in_background(current_app._get_current_object(), subnet.id):
        return jsonify({'status': 'already_running'}), 409
    return jsonify({'status': 'started'}), 202


@subnets_bp.route('/subnets/<int:subnet_id>/scan', methods=['GET'])
def scan_status(subnet_id):
    subnet = Subnet.query.get_or_404(subnet_id)
    return jsonify({
        'running': ipam_scan.is_running(subnet.id),
        'last_scan_at': subnet.to_dict()['last_scan_at'],
        'last_scan_alive': subnet.last_scan_alive,
        'last_scan_duration_ms': subnet.last_scan_duration_ms,
        'last_scan_error': subnet.last_scan_error,
    })


# --- DHCP leases ------------------------------------------------------------

def _leases_authorized():
    token = os.environ.get('IPAM_LEASES_TOKEN') or None
    if not token:
        return True
    header = request.headers.get('Authorization', '')
    supplied = header[7:] if header.startswith('Bearer ') else ''
    return hmac.compare_digest(supplied.encode(), token.encode())


@subnets_bp.route('/ipam/dhcp/leases', methods=['POST'])
def upload_leases():
    """
    Import a dnsmasq lease file. Send it as multipart `file`, or as the raw
    request body (e.g. `curl --data-binary @/var/lib/misc/dnsmasq.leases`).
    ?source=<label> keeps snapshots from different servers separate
    (default: "upload"). Bearer token required if IPAM_LEASES_TOKEN is set.
    """
    if not _leases_authorized():
        return jsonify({'error': 'Unauthorized'}), 401
    # Choose by content type *before* touching request.files/form: curl
    # --data-binary labels the body x-www-form-urlencoded, and letting Flask
    # parse it as a form would consume the raw lease text.
    form_source = None
    if request.mimetype == 'multipart/form-data':
        upload = request.files.get('file')
        raw = upload.read(dhcp_leases.MAX_LEASE_BYTES + 1) if upload else b''
        form_source = request.form.get('source')
    else:
        raw = request.get_data(cache=False, parse_form_data=False)[: dhcp_leases.MAX_LEASE_BYTES + 1]
    if not raw:
        return jsonify({'error': 'No lease data provided'}), 400
    if len(raw) > dhcp_leases.MAX_LEASE_BYTES:
        return jsonify({'error': 'Lease data is too large'}), 413
    source = request.args.get('source') or form_source or 'upload'
    try:
        result = dhcp_leases.import_leases(raw.decode('utf-8', errors='replace'), source=f'upload:{source}')
    except dhcp_leases.LeaseParseError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(result), 200


@subnets_bp.route('/ipam/dhcp/status', methods=['GET'])
def dhcp_status():
    watcher = current_app.extensions.get('lease_watcher')
    sources = (db.session.query(IpObservation.dhcp_source, db.func.count(IpObservation.id))
               .filter(IpObservation.dhcp_active.is_(True))
               .group_by(IpObservation.dhcp_source).all())
    return jsonify({
        'watched_files': dhcp_leases.configured_lease_paths(),
        'file_results': watcher.last_results if watcher else {},
        'active_by_source': {src or 'unknown': n for src, n in sources},
        'token_required': bool(os.environ.get('IPAM_LEASES_TOKEN')),
    })
