"""
Device routes
"""
from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from marshmallow import ValidationError as MarshmallowValidationError
from datetime import datetime

from models import db, Device, DeviceHistory, Vendor, Model, Location
from utils.history import extract_device_state, compute_diff
from validators import DeviceSchema
from exceptions import DatabaseError, ReadOnlyDatabaseError
from utils.response import (
    success_response, error_response, validation_error_response,
    not_found_response, conflict_response
)
import logging

devices_bp = Blueprint('devices', __name__)


def register_device_routes(app, limiter):
    """Register device routes with the app"""
    app.register_blueprint(devices_bp, url_prefix='/api/devices')
    
    # Apply rate limiting
    limiter.limit("20 per minute")(create_device)
    limiter.limit("20 per minute")(update_device)
    limiter.limit("20 per minute")(delete_device)
    limiter.limit("60 per minute")(get_all_history)
    limiter.limit("60 per minute")(get_device_history)


def _collect_lookup_ids(history_entries):
    """Collect referenced foreign key ids from a list of history entries."""
    id_sets = {
        'vendor_id': set(),
        'model_id': set(),
        'location_id': set(),
    }
    for entry in history_entries:
        for field, change in (entry.diff or {}).items():
            if field in id_sets:
                for value in (change.get('old'), change.get('new')):
                    if isinstance(value, int):
                        id_sets[field].add(value)
    return id_sets


def _build_lookup_maps(id_sets):
    """Return mapping dicts for foreign key fields to human-readable names."""
    lookups = {}
    if id_sets.get('vendor_id'):
        lookups['vendor_id'] = {v.id: v.name for v in Vendor.query.filter(Vendor.id.in_(id_sets['vendor_id'])).all()}
    if id_sets.get('model_id'):
        lookups['model_id'] = {m.id: m.name for m in Model.query.filter(Model.id.in_(id_sets['model_id'])).all()}
    if id_sets.get('location_id'):
        lookups['location_id'] = {location.id: location.name for location in Location.query.filter(Location.id.in_(id_sets['location_id'])).all()}
    return lookups


def _format_display_diff(diff, lookups):
    """Create a display-friendly diff that swaps ids for names when possible."""
    display_diff = {}
    for field, change in (diff or {}).items():
        display_change = {
            'old': change.get('old'),
            'new': change.get('new')
        }
        if field in lookups:
            display_change['old_label'] = lookups[field].get(change.get('old'))
            display_change['new_label'] = lookups[field].get(change.get('new'))
        display_diff[field] = display_change
    return display_diff


@devices_bp.route('/history', methods=['GET'])
def get_all_history():
    """Retrieve change history across all devices with pagination."""
    try:
        limit_param = request.args.get('limit', default='50')
        offset = request.args.get('offset', default=0, type=int)

        offset = 0 if offset is None or offset < 0 else offset

        limit = None
        if limit_param and str(limit_param).lower() != 'all':
            try:
                limit_int = int(limit_param)
            except (TypeError, ValueError):
                return validation_error_response({'limit': ['Invalid limit value']})
            limit = 1 if limit_int < 1 else min(limit_int, 500)

        query = DeviceHistory.query.order_by(DeviceHistory.created_at.desc())
        total = query.count()

        history_query = query
        if offset:
            history_query = history_query.offset(offset)
        if limit is not None:
            history_query = history_query.limit(limit)

        items = history_query.all()

        id_sets = _collect_lookup_ids(items)
        lookup_maps = _build_lookup_maps(id_sets)

        device_ids = {entry.device_id for entry in items if entry.device_id}
        device_lookup = {}
        if device_ids:
            device_lookup = {
                d.id: {
                    'name': d.name,
                    'device_type': d.device_type,
                    'ip_address': d.ip_address
                }
                for d in Device.query.filter(Device.id.in_(device_ids)).all()
            }

        items_payload = []
        for item in items:
            device_info = device_lookup.get(item.device_id, {})
            items_payload.append({
                'id': item.id,
                'device_id': item.device_id,
                'device_name': device_info.get('name'),
                'device_type': device_info.get('device_type'),
                'device_ip': device_info.get('ip_address'),
                'change_type': item.change_type,
                'diff': item.diff,
                'display_diff': _format_display_diff(item.diff, lookup_maps),
                'summary': item.summary,
                'created_at': item.created_at.isoformat()
            })

        effective_limit = limit if limit is not None else (total if total else 0)

        return success_response({
            'items': items_payload,
            'total': total,
            'limit': effective_limit,
            'offset': offset
        })
    except Exception as e:
        logging.error(f"Failed to fetch all device history: {e}", exc_info=True)
        return error_response("Failed to fetch device history due to an internal error", status_code=500, error_code='DATABASE_ERROR')


@devices_bp.route('', methods=['GET'])
def get_devices():
    """Get all devices, optionally filtered by type"""
    device_type = request.args.get('type')
    if device_type:
        devices = Device.query.filter_by(device_type=device_type).all()
    else:
        devices = Device.query.all()
    return success_response([d.to_dict() for d in devices])


@devices_bp.route('/<int:device_id>', methods=['GET'])
def get_device(device_id):
    """Get a single device by ID"""
    device = Device.query.get(device_id)
    if not device:
        return not_found_response("Device", device_id)
    return success_response(device.to_dict())


@devices_bp.route('', methods=['POST'])
def create_device():
    """Create a new device"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    # Backwards compatibility: map legacy field name
    if 'function' in data and 'deviceFunction' not in data:
        data['deviceFunction'] = data['function']
    
    # Filter out read-only/computed fields that shouldn't be in create requests
    # These fields come from the database relationships and computed properties
    readonly_fields = ['id', 'created_at', 'updated_at', 'vendor_name', 'model_name', 
                      'location_name', 'monitors']
    
    # Only keep fields that are actually creatable
    creatable_fields = ['name', 'device_type', 'ip_address', 'deviceFunction', 'vendor_id', 
                       'model_id', 'location_id', 'serial_number', 'networks', 
                       'interface_type', 'poe_powered', 'poe_standards', 'monitoring_enabled']
    
    filtered_data = {k: v for k, v in data.items() if k in creatable_fields}
    
    # Validate input
    schema = DeviceSchema()
    try:
        validated_data = schema.load(filtered_data)
    except MarshmallowValidationError as err:
        logging.warning(f"Validation error for device creation: {err.messages}. Filtered data: {filtered_data}")
        return validation_error_response(err.messages)
    
    device = Device(
        name=validated_data['name'],
        device_type=validated_data['device_type'],
        ip_address=validated_data.get('ip_address'),
        device_function=validated_data.get('device_function'),
        vendor_id=validated_data.get('vendor_id'),
        model_id=validated_data.get('model_id'),
        location_id=validated_data.get('location_id'),
        serial_number=validated_data.get('serial_number'),
        networks=validated_data.get('networks'),
        interface_type=validated_data.get('interface_type'),
        poe_powered=validated_data.get('poe_powered', False),
        poe_standards=validated_data.get('poe_standards'),
        monitoring_enabled=validated_data.get('monitoring_enabled', True)
    )
    try:
        db.session.add(device)
        db.session.flush()  # ensure device.id for history
        db.session.add(DeviceHistory(
            device_id=device.id,
            change_type='create',
            summary=f"Created device '{device.name}'",
            diff=compute_diff(None, extract_device_state(device))
        ))
        db.session.commit()
        return success_response(device.to_dict(), "Device created successfully", 201)
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        if 'readonly' in error_msg.lower() or 'read-only' in error_msg.lower():
            return error_response("Database is read-only", status_code=500, error_code='READONLY_DATABASE')
        logging.error(f"Failed to create device: {error_msg}")
        return error_response("Failed to create device due to an internal error", status_code=500, error_code='DATABASE_ERROR')


@devices_bp.route('/<int:device_id>', methods=['PUT'])
def update_device(device_id):
    """Update an existing device"""
    device = Device.query.get(device_id)
    if not device:
        return not_found_response("Device", device_id)

    previous_state = extract_device_state(device)
    
    if not request.is_json:
        return error_response('Content-Type must be application/json', status_code=400)
    
    data = request.json
    if not data:
        return error_response('Request body is required', status_code=400)

    # Backwards compatibility: map legacy field name
    if 'function' in data and 'deviceFunction' not in data:
        data['deviceFunction'] = data['function']
    
    # Filter out read-only/computed fields that shouldn't be updated
    # These fields come from the database relationships and computed properties
    readonly_fields = ['id', 'created_at', 'updated_at', 'vendor_name', 'model_name', 
                      'location_name', 'monitors']
    
    # Only keep fields that are actually updatable
    updatable_fields = ['name', 'device_type', 'ip_address', 'deviceFunction', 'vendor_id', 
                       'model_id', 'location_id', 'serial_number', 'networks', 
                       'interface_type', 'poe_powered', 'poe_standards', 'monitoring_enabled']
    
    filtered_data = {k: v for k, v in data.items() if k in updatable_fields}
    
    # For partial updates, remove empty strings from required fields to avoid validation errors
    if isinstance(filtered_data, dict):
        # Remove empty strings for required fields in partial updates
        for key in ['name', 'device_type']:
            if key in filtered_data and filtered_data[key] == '':
                # Keep existing value, don't update
                filtered_data.pop(key)
    
    # Validate input (partial validation for updates)
    schema = DeviceSchema(partial=True)
    try:
        validated_data = schema.load(filtered_data)
    except MarshmallowValidationError as err:
        logging.warning(f"Validation error for device {device_id} update: {err.messages}. Filtered data: {filtered_data}")
        return validation_error_response(err.messages)
    
    for key in ['name', 'device_type', 'ip_address', 'device_function', 
                'vendor_id', 'model_id', 'location_id', 'serial_number', 
                'networks', 'interface_type', 'poe_standards']:
        if key in validated_data:
            setattr(device, key, validated_data[key])
    
    if 'poe_powered' in validated_data:
        device.poe_powered = validated_data['poe_powered']
    if 'monitoring_enabled' in validated_data:
        device.monitoring_enabled = validated_data['monitoring_enabled']
    
    device.updated_at = datetime.utcnow()
    
    try:
        new_state = extract_device_state(device)
        diff = compute_diff(previous_state, new_state)

        if diff:
            db.session.add(DeviceHistory(
                device_id=device.id,
                change_type='update',
                summary=f"Updated device '{device.name}'",
                diff=diff
            ))

        db.session.commit()
        return success_response(device.to_dict(), "Device updated successfully")
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        if 'readonly' in error_msg.lower() or 'read-only' in error_msg.lower():
            return error_response("Database is read-only", status_code=500, error_code='READONLY_DATABASE')
        logging.error(f"Failed to update device: {error_msg}")
        return error_response("Failed to update device due to an internal error", status_code=500, error_code='DATABASE_ERROR')


@devices_bp.route('/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    """Delete a device"""
    device = Device.query.get(device_id)
    if not device:
        return not_found_response("Device", device_id)

    previous_state = extract_device_state(device)
    
    try:
        db.session.add(DeviceHistory(
            device_id=device.id,
            change_type='delete',
            summary=f"Deleted device '{device.name}'",
            diff=compute_diff(previous_state, None)
        ))
        db.session.delete(device)
        db.session.commit()
        return success_response(None, "Device deleted successfully", 200)
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Error deleting device {device_id}: {error_msg}", exc_info=True)
        if 'readonly' in error_msg.lower() or 'read-only' in error_msg.lower():
            return error_response("Database is read-only", status_code=500, error_code='READONLY_DATABASE')
        return error_response("Failed to delete device due to an internal error", status_code=500, error_code='DATABASE_ERROR')


@devices_bp.route('/<int:device_id>/history', methods=['GET'])
def get_device_history(device_id):
    """Retrieve change history for a device"""
    device = Device.query.get(device_id)
    if not device:
        return not_found_response("Device", device_id)

    try:
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)

        limit = 1 if limit < 1 else min(limit, 100)
        offset = 0 if offset < 0 else offset

        query = DeviceHistory.query.filter_by(device_id=device_id).order_by(DeviceHistory.created_at.desc())
        total = query.count()
        items = query.offset(offset).limit(limit).all()

        id_sets = _collect_lookup_ids(items)
        lookup_maps = _build_lookup_maps(id_sets)

        items_payload = []
        for item in items:
            items_payload.append({
                'id': item.id,
                'device_id': item.device_id,
                'change_type': item.change_type,
                'diff': item.diff,
                'display_diff': _format_display_diff(item.diff, lookup_maps),
                'summary': item.summary,
                'created_at': item.created_at.isoformat()
            })

        return success_response({
            'items': items_payload,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logging.error(f"Failed to fetch device history for {device_id}: {e}", exc_info=True)
        return error_response("Failed to fetch device history due to an internal error", status_code=500, error_code='DATABASE_ERROR')

