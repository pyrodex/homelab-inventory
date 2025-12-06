"""
Device routes
"""
from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from marshmallow import ValidationError as MarshmallowValidationError
from datetime import datetime

from models import db, Device
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
    
    try:
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

