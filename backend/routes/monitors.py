"""
Monitor routes
"""
from flask import Blueprint, request, jsonify
from marshmallow import ValidationError as MarshmallowValidationError

from flask import jsonify
from models import db, Device, Monitor
from validators import MonitorSchema
from exceptions import DatabaseError
import logging

monitors_bp = Blueprint('monitors', __name__)


def register_monitor_routes(app, limiter):
    """Register monitor routes with the app"""
    app.register_blueprint(monitors_bp, url_prefix='/api')
    
    # Apply rate limiting
    limiter.limit("30 per minute")(add_monitor)
    limiter.limit("30 per minute")(update_monitor)
    limiter.limit("30 per minute")(delete_monitor)


@monitors_bp.route('/devices/<int:device_id>/monitors', methods=['POST'])
def add_monitor(device_id):
    """Add a monitor to a device"""
    device = Device.query.get_or_404(device_id)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input
    schema = MonitorSchema()
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    monitor = Monitor(
        device_id=device_id,
        monitor_type=validated_data['monitor_type'],
        endpoint=validated_data.get('endpoint'),
        port=validated_data.get('port'),
        enabled=validated_data.get('enabled', True),
        notes=validated_data.get('notes')
    )
    try:
        db.session.add(monitor)
        db.session.commit()
        return jsonify(monitor.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to create monitor: {error_msg}")
        return jsonify(DatabaseError("Failed to create monitor due to an internal error.").to_dict()), 500


@monitors_bp.route('/monitors/<int:monitor_id>', methods=['PUT'])
def update_monitor(monitor_id):
    """Update a monitor"""
    monitor = Monitor.query.get_or_404(monitor_id)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Filter out read-only fields (id, device_id are not updatable)
    updatable_fields = ['monitor_type', 'endpoint', 'port', 'enabled', 'notes']
    filtered_data = {k: v for k, v in data.items() if k in updatable_fields}
    
    # Validate input (partial validation for updates)
    schema = MonitorSchema(partial=True)
    try:
        validated_data = schema.load(filtered_data)
    except MarshmallowValidationError as err:
        logging.warning(f"Validation error for monitor {monitor_id} update: {err.messages}")
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    for key in ['monitor_type', 'endpoint', 'port', 'enabled', 'notes']:
        if key in validated_data:
            setattr(monitor, key, validated_data[key])
    
    try:
        db.session.commit()
        return jsonify(monitor.to_dict())
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to update monitor: {error_msg}")
        return jsonify(DatabaseError("Failed to update monitor due to an internal error.").to_dict()), 500


@monitors_bp.route('/monitors/<int:monitor_id>', methods=['DELETE'])
def delete_monitor(monitor_id):
    """Delete a monitor"""
    monitor = Monitor.query.get_or_404(monitor_id)
    try:
        db.session.delete(monitor)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to delete monitor: {error_msg}")
        return jsonify(DatabaseError("Failed to delete monitor due to an internal error.").to_dict()), 500

