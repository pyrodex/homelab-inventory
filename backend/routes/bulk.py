"""
Bulk operations routes
"""
from flask import Blueprint, request, jsonify, send_file
from flask_limiter import Limiter
import csv
import io
import json
import logging

from models import db, Device, Vendor, Model, Location
from validators import DeviceSchema
from exceptions import DatabaseError, ValidationError
from marshmallow import ValidationError as MarshmallowValidationError

bulk_bp = Blueprint('bulk', __name__)

# Limiter will be set by register_bulk_routes
limiter = None


def register_bulk_routes(app, limiter_instance):
    """Register bulk operation routes with the app"""
    global limiter
    limiter = limiter_instance
    app.register_blueprint(bulk_bp, url_prefix='/api/bulk')
    
    # Apply rate limiting (more restrictive for bulk operations)
    limiter.limit("10 per minute")(bulk_import_devices)
    limiter.limit("10 per minute")(bulk_export_devices)
    limiter.limit("5 per minute")(bulk_delete_devices)


@bulk_bp.route('/devices/import', methods=['POST'])
def bulk_import_devices():
    """Import devices from CSV or JSON"""
    if not request.is_json and not request.content_type.startswith('multipart/form-data'):
        return jsonify({'error': 'Content-Type must be application/json or multipart/form-data'}), 400
    
    try:
        # Handle JSON import
        if request.is_json:
            data = request.json
            if not isinstance(data, list):
                return jsonify({'error': 'JSON data must be an array of devices'}), 400
            
            devices_created = []
            devices_failed = []
            schema = DeviceSchema()
            
            for idx, device_data in enumerate(data):
                try:
                    validated_data = schema.load(device_data)
                    device = Device(**validated_data)
                    db.session.add(device)
                    devices_created.append(device_data.get('name', f'Device {idx+1}'))
                except MarshmallowValidationError as err:
                    devices_failed.append({
                        'index': idx,
                        'name': device_data.get('name', f'Device {idx+1}'),
                        'error': err.messages
                    })
                except Exception as e:
                    devices_failed.append({
                        'index': idx,
                        'name': device_data.get('name', f'Device {idx+1}'),
                        'error': str(e)
                    })
            
            if devices_created:
                db.session.commit()
            
            return jsonify({
                'status': 'completed',
                'created': len(devices_created),
                'failed': len(devices_failed),
                'created_devices': devices_created,
                'failed_devices': devices_failed
            }), 201 if devices_created else 400
        
        # Handle CSV import
        elif 'file' in request.files:
            file = request.files['file']
            if not file.filename.endswith('.csv'):
                return jsonify({'error': 'File must be a CSV file'}), 400
            
            # Read CSV
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            
            devices_created = []
            devices_failed = []
            schema = DeviceSchema()
            
            for idx, row in enumerate(csv_reader):
                try:
                    # Convert CSV row to device data
                    device_data = {
                        'name': row.get('name', '').strip(),
                        'device_type': row.get('device_type', '').strip(),
                        'ip_address': row.get('ip_address', '').strip() or None,
                        'function': row.get('function', '').strip() or None,
                        'serial_number': row.get('serial_number', '').strip() or None,
                        'networks': row.get('networks', '').strip() or None,
                        'interface_type': row.get('interface_type', '').strip() or None,
                        'poe_standards': row.get('poe_standards', '').strip() or None,
                        'monitoring_enabled': row.get('monitoring_enabled', 'true').lower() == 'true',
                        'poe_powered': row.get('poe_powered', 'false').lower() == 'true'
                    }
                    
                    # Handle vendor/model/location by name (lookup IDs)
                    if row.get('vendor'):
                        vendor = Vendor.query.filter_by(name=row['vendor'].strip()).first()
                        if vendor:
                            device_data['vendor_id'] = vendor.id
                    
                    if row.get('model') and 'vendor_id' in device_data:
                        model = Model.query.filter_by(
                            name=row['model'].strip(),
                            vendor_id=device_data['vendor_id']
                        ).first()
                        if model:
                            device_data['model_id'] = model.id
                    
                    if row.get('location'):
                        location = Location.query.filter_by(name=row['location'].strip()).first()
                        if location:
                            device_data['location_id'] = location.id
                    
                    validated_data = schema.load(device_data)
                    device = Device(**validated_data)
                    db.session.add(device)
                    devices_created.append(device_data.get('name', f'Row {idx+1}'))
                except Exception as e:
                    devices_failed.append({
                        'row': idx + 2,  # +2 because row 1 is header
                        'name': row.get('name', f'Row {idx+1}'),
                        'error': str(e)
                    })
            
            if devices_created:
                db.session.commit()
            
            return jsonify({
                'status': 'completed',
                'created': len(devices_created),
                'failed': len(devices_failed),
                'created_devices': devices_created,
                'failed_devices': devices_failed
            }), 201 if devices_created else 400
        
        else:
            return jsonify({'error': 'No file or JSON data provided'}), 400
            
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Bulk import failed: {error_msg}")
        return jsonify({'error': 'Bulk import failed', 'message': error_msg}), 500


@bulk_bp.route('/devices/export', methods=['GET'])
def bulk_export_devices():
    """Export devices as CSV or JSON"""
    format_type = request.args.get('format', 'json').lower()
    device_type = request.args.get('type')
    
    # Get devices
    if device_type and device_type != 'all':
        devices = Device.query.filter_by(device_type=device_type).all()
    else:
        devices = Device.query.all()
    
    if format_type == 'csv':
        # Generate CSV
        output = io.StringIO()
        fieldnames = [
            'id', 'name', 'device_type', 'ip_address', 'function', 'vendor', 'model',
            'location', 'serial_number', 'networks', 'interface_type', 
            'poe_powered', 'poe_standards', 'monitoring_enabled', 'created_at', 'updated_at'
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for device in devices:
            writer.writerow({
                'id': device.id,
                'name': device.name,
                'device_type': device.device_type,
                'ip_address': device.ip_address or '',
                'function': device.function or '',
                'vendor': device.vendor_obj.name if device.vendor_obj else '',
                'model': device.model_obj.name if device.model_obj else '',
                'location': device.location_obj.name if device.location_obj else '',
                'serial_number': device.serial_number or '',
                'networks': device.networks or '',
                'interface_type': device.interface_type or '',
                'poe_powered': 'true' if device.poe_powered else 'false',
                'poe_standards': device.poe_standards or '',
                'monitoring_enabled': 'true' if device.monitoring_enabled else 'false',
                'created_at': device.created_at.isoformat() if device.created_at else '',
                'updated_at': device.updated_at.isoformat() if device.updated_at else ''
            })
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='devices_export.csv'
        )
    
    else:  # JSON
        devices_data = [device.to_dict() for device in devices]
        return jsonify(devices_data)


@bulk_bp.route('/devices/delete', methods=['POST'])
def bulk_delete_devices():
    """Bulk delete devices"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data or 'device_ids' not in data:
        return jsonify({'error': 'device_ids array is required'}), 400
    
    device_ids = data['device_ids']
    if not isinstance(device_ids, list):
        return jsonify({'error': 'device_ids must be an array'}), 400
    
    if len(device_ids) == 0:
        return jsonify({'error': 'At least one device ID is required'}), 400
    
    if len(device_ids) > 100:
        return jsonify({'error': 'Cannot delete more than 100 devices at once'}), 400
    
    deleted_count = 0
    failed_ids = []
    
    try:
        for device_id in device_ids:
            try:
                device = Device.query.get(device_id)
                if device:
                    db.session.delete(device)
                    deleted_count += 1
                else:
                    failed_ids.append({'id': device_id, 'error': 'Device not found'})
            except Exception as e:
                failed_ids.append({'id': device_id, 'error': str(e)})
        
        if deleted_count > 0:
            db.session.commit()
        
        return jsonify({
            'status': 'completed',
            'deleted': deleted_count,
            'failed': len(failed_ids),
            'failed_ids': failed_ids
        }), 200
        
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Bulk delete failed: {error_msg}")
        return jsonify({'error': 'Bulk delete failed', 'message': error_msg}), 500

