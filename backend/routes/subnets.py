"""
Subnet / IPAM routes.

Subnets are defined in CIDR notation; utilization is computed on the fly from
device IP addresses and monitor endpoints, so there is nothing to keep in sync.
"""
import ipaddress
import logging

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError as MarshmallowValidationError
from sqlalchemy.orm import selectinload

from exceptions import ConflictError, DatabaseError
from models import Device, Location, Subnet, db
from services.ipam import (
    analyze_subnet,
    build_address_index,
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


def _load_devices():
    return Device.query.options(selectinload(Device.monitors)).all()


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
    payload = []
    for subnet in subnets:
        analysis = analyze_subnet(subnet, index)
        item = subnet.to_dict()
        item['summary'] = analysis['summary']
        item['version'] = analysis['version']
        item['conflict_count'] = len(analysis['conflicts'])
        item['reserved_error'] = analysis['reserved_error']
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
    analysis = analyze_subnet(subnet, build_address_index(_load_devices()))
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
    analysis = analyze_subnet(subnet, build_address_index(_load_devices()))
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

    updatable = ['cidr', 'name', 'description', 'vlan_id', 'gateway', 'reserved_ranges', 'location_id']
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
