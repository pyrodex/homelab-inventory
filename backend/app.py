from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
import yaml
import io
import os
from sqlalchemy import event
from sqlalchemy.engine import Engine
import logging
from marshmallow import ValidationError as MarshmallowValidationError

from validators import (
    DeviceSchema, MonitorSchema, VendorSchema, ModelSchema, LocationSchema
)

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# Use environment variable for database path, fallback to current directory
db_path = os.environ.get('DATABASE_PATH', 'homelab.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# CORS Configuration - restrict to allowed origins
allowed_origins = os.environ.get('CORS_ORIGINS', '*').split(',')
if '*' in allowed_origins:
    # Development mode - allow all origins
    CORS(app)
else:
    # Production mode - restrict to specific origins
    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

# Rate Limiting Configuration
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://"  # Use in-memory storage (consider Redis for production)
)

# Rate limit error handler
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': f'Too many requests. Please try again later. Limit: {e.description}'
    }), 429

db = SQLAlchemy(app)

# CRITICAL FIX: Enable foreign key constraints in SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Device Types
DEVICE_TYPES = [
    'linux_server_physical',
    'linux_server_virtual',
    'freebsd_server',
    'network_switch',
    'wireless_ap',
    'icmp_only',
    'ip_camera',
    'video_streamer',
    'iot_device',
    'url',
    'dns_record',
    'ipmi_console',
    'ups_nut'
]

# Monitoring Types
MONITORING_TYPES = [
    'node_exporter',
    'smartprom',
    'snmp',
    'icmp',
    'http',
    'https',
    'dns',
    'ipmi',
    'nut',
    'docker'
]

# PoE Standards
POE_STANDARDS = [
    'PoE (802.3af)',
    'PoE+ (802.3at)',
    'PoE++ (802.3bt Type 3)',
    'PoE+++ (802.3bt Type 4)',
    'Passive PoE',
    'Other'
]

# Models
class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    devices = db.relationship('Device', backref='location_obj', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'device_count': len(self.devices),
            'created_at': self.created_at.isoformat()
        }

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    models = db.relationship('Model', backref='vendor', lazy=True, cascade='all, delete-orphan')
    devices = db.relationship('Device', backref='vendor_obj', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'model_count': len(self.models),
            'device_count': len(self.devices),
            'created_at': self.created_at.isoformat()
        }

class Model(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    devices = db.relationship('Device', backref='model_obj', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor.name,
            'device_count': len(self.devices),
            'created_at': self.created_at.isoformat()
        }

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    ip_address = db.Column(db.String(100))
    function = db.Column(db.String(200))
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=True)
    model_id = db.Column(db.Integer, db.ForeignKey('model.id'), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)
    serial_number = db.Column(db.String(100))
    networks = db.Column(db.String(200))  # Comma-separated: LAN,IoT,DMZ,GUEST or ALL
    interface_type = db.Column(db.String(200))  # Comma-separated interface types
    poe_powered = db.Column(db.Boolean, default=False)
    poe_standards = db.Column(db.String(200))  # Comma-separated PoE standards
    monitoring_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    monitors = db.relationship('Monitor', backref='device', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'device_type': self.device_type,
            'ip_address': self.ip_address,
            'function': self.function,
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor_obj.name if self.vendor_obj else None,
            'model_id': self.model_id,
            'model_name': self.model_obj.name if self.model_obj else None,
            'location_id': self.location_id,
            'location_name': self.location_obj.name if self.location_obj else None,
            'serial_number': self.serial_number,
            'networks': self.networks,
            'interface_type': self.interface_type,
            'poe_powered': self.poe_powered,
            'poe_standards': self.poe_standards,
            'monitoring_enabled': self.monitoring_enabled,
            'monitors': [m.to_dict() for m in self.monitors],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Monitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    monitor_type = db.Column(db.String(50), nullable=False)
    endpoint = db.Column(db.String(200))
    port = db.Column(db.Integer)
    enabled = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'monitor_type': self.monitor_type,
            'endpoint': self.endpoint,
            'port': self.port,
            'enabled': self.enabled,
            'notes': self.notes
        }

# Routes
@app.route('/api/devices', methods=['GET'])
def get_devices():
    device_type = request.args.get('type')
    if device_type:
        devices = Device.query.filter_by(device_type=device_type).all()
    else:
        devices = Device.query.all()
    return jsonify([d.to_dict() for d in devices])

@app.route('/api/devices/<int:device_id>', methods=['GET'])
def get_device(device_id):
    device = Device.query.get_or_404(device_id)
    return jsonify(device.to_dict())

@app.route('/api/devices', methods=['POST'])
@limiter.limit("20 per minute")
def create_device():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input
    schema = DeviceSchema()
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    device = Device(
        name=validated_data['name'],
        device_type=validated_data['device_type'],
        ip_address=validated_data.get('ip_address'),
        function=validated_data.get('function'),
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
        return jsonify(device.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        if 'readonly' in error_msg.lower() or 'read-only' in error_msg.lower():
            return jsonify({'error': 'Database is read-only. Please check file permissions.'}), 500
        logging.error(f"Failed to create device: {error_msg}")
        return jsonify({'error': 'Failed to create device due to an internal error.'}), 500

@app.route('/api/devices/<int:device_id>', methods=['PUT'])
@limiter.limit("20 per minute")
def update_device(device_id):
    device = Device.query.get_or_404(device_id)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input (partial validation for updates)
    schema = DeviceSchema(partial=True)
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    for key in ['name', 'device_type', 'ip_address', 'function', 
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
        return jsonify(device.to_dict())
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        if 'readonly' in error_msg.lower() or 'read-only' in error_msg.lower():
            return jsonify({'error': 'Database is read-only. Please check file permissions.'}), 500
        logging.error(f"Failed to update device: {error_msg}")
        return jsonify({'error': 'Failed to update device due to an internal error.'}), 500

@app.route('/api/devices/<int:device_id>', methods=['DELETE'])
@limiter.limit("20 per minute")
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)
    try:
        db.session.delete(device)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)  # Fixed: error_msg now assigned before use
        logging.error(f"Error deleting device {device_id}: {error_msg}", exc_info=True)
        if 'readonly' in error_msg.lower() or 'read-only' in error_msg.lower():
            return jsonify({'error': 'Database is read-only. Please check file permissions.'}), 500
        return jsonify({'error': 'Failed to delete device due to an internal error.'}), 500

@app.route('/api/devices/<int:device_id>/monitors', methods=['POST'])
@limiter.limit("30 per minute")
def add_monitor(device_id):
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
        return jsonify({'error': 'Failed to create monitor due to an internal error.'}), 500

@app.route('/api/monitors/<int:monitor_id>', methods=['PUT'])
@limiter.limit("30 per minute")
def update_monitor(monitor_id):
    monitor = Monitor.query.get_or_404(monitor_id)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input (partial validation for updates)
    schema = MonitorSchema(partial=True)
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
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
        return jsonify({'error': 'Failed to update monitor due to an internal error.'}), 500

@app.route('/api/monitors/<int:monitor_id>', methods=['DELETE'])
@limiter.limit("30 per minute")
def delete_monitor(monitor_id):
    monitor = Monitor.query.get_or_404(monitor_id)
    try:
        db.session.delete(monitor)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to delete monitor: {error_msg}")
        return jsonify({'error': 'Failed to delete monitor due to an internal error.'}), 500

@app.route('/api/prometheus/export', methods=['GET'])
@limiter.limit("10 per minute")
def export_prometheus_config():
    import tempfile
    import shutil
    from pathlib import Path
    
    devices = Device.query.filter_by(monitoring_enabled=True).all()
    
    export_path = os.environ.get('PROMETHEUS_EXPORT_PATH', '/app/prometheus_targets')
    export_mode = request.args.get('mode', 'write')
    
    # Helper function to determine the directory name based on monitor and device type
    def get_monitor_directory_name(monitor_type, device_type):
        """Return the directory name based on monitor type and device type"""
        if monitor_type == 'node_exporter':
            if device_type.startswith('linux_server_'):
                return 'linux_node_exporter'
            elif device_type == 'freebsd_server':
                return 'freebsd_node_exporter'
        return monitor_type
    
    if export_mode == 'write':
        export_dir = Path(export_path)
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Remove only files, not directories
        for item in export_dir.iterdir():
            if item.is_dir():
                # Remove all files within the directory but keep the directory itself
                for file in item.iterdir():
                    if file.is_file():
                        file.unlink()
            else:
                # Remove files in the root export directory
                item.unlink()
        
        monitors_by_type = {}
        
        for device in devices:
            for monitor in device.monitors:
                if not monitor.enabled:
                    continue
                
                monitor_type = monitor.monitor_type
                
                # Determine the effective directory name
                directory_name = get_monitor_directory_name(monitor_type, device.device_type)
                
                if directory_name not in monitors_by_type:
                    monitors_by_type[directory_name] = []
                
                target = device.ip_address
                if monitor.port:
                    if ':' in target:
                        target = target.split(':')[0] + f':{monitor.port}'
                    else:
                        target = f'{target}:{monitor.port}'
                elif ':' not in target:
                    default_ports = {
                        'node_exporter': 9100,
                        'smartprom': 9902,
                        'snmp': 161,
                        'http': 80,
                        'https': 443,
                        'dns': 53,
                        'ipmi': 623,
                        'nut': 3493,
                        'docker': 8090
                    }
                    if monitor_type in default_ports:
                        target = f'{target}:{default_ports[monitor_type]}'
                
                if monitor_type == 'http' and not target.startswith('http://'):
                    target = f'http://{target}'
                elif monitor_type == 'https' and not target.startswith('https://'):
                    target = f'https://{target}'
                
                labels = {
                    'device_name': device.name,
                    'device_type': device.device_type,
                    'ip_address': device.ip_address or '',
                    'function': device.function or '',
                    'networks': device.networks or '',
                    'vendor': device.vendor_obj.name if device.vendor_obj else '',
                    'model': device.model_obj.name if device.model_obj else '',
                    'location': device.location_obj.name if device.location_obj else '',
                    'serial_number': device.serial_number or '',
                    'interface_type': device.interface_type or '',
                    'poe_powered': 'true' if device.poe_powered else 'false',
                    'poe_standards': device.poe_standards or '',
                    'monitor_type': monitor_type,
                    'monitor_endpoint': monitor.endpoint or ''
                }
                
                monitors_by_type[directory_name].append({
                    'device_name': device.name,
                    'target': target,
                    'labels': labels
                })
        
        files_created = 0
        for directory_name, monitor_list in monitors_by_type.items():
            monitor_dir = export_dir / directory_name
            monitor_dir.mkdir(exist_ok=True)
            
            for monitor_data in monitor_list:
                safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in monitor_data['device_name'])
                filename = f"{safe_name}.yaml"
                filepath = monitor_dir / filename
                
                yaml_content = [{
                    'targets': [monitor_data['target']],
                    'labels': monitor_data['labels']
                }]
                
                with open(filepath, 'w') as f:
                    yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)
                files_created += 1
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully wrote {files_created} target files to {export_path}',
            'path': export_path,
            'files_created': files_created
        })
    
    else:  # download mode
        temp_dir = tempfile.mkdtemp()
        
        try:
            monitors_by_type = {}
            
            for device in devices:
                for monitor in device.monitors:
                    if not monitor.enabled:
                        continue
                    
                    monitor_type = monitor.monitor_type
                    
                    # Determine the effective directory name
                    directory_name = get_monitor_directory_name(monitor_type, device.device_type)
                    
                    if directory_name not in monitors_by_type:
                        monitors_by_type[directory_name] = []
                    
                    target = device.ip_address
                    if monitor.port:
                        if ':' in target:
                            target = target.split(':')[0] + f':{monitor.port}'
                        else:
                            target = f'{target}:{monitor.port}'
                    elif ':' not in target:
                        default_ports = {
                            'node_exporter': 9100,
                            'smartprom': 9902,
                            'snmp': 161,
                            'http': 80,
                            'https': 443,
                            'dns': 53,
                            'ipmi': 623,
                            'nut': 3493,
                            'docker': 8090
                        }
                        if monitor_type in default_ports:
                            target = f'{target}:{default_ports[monitor_type]}'
                    
                    if monitor_type == 'http' and not target.startswith('http://'):
                        target = f'http://{target}'
                    elif monitor_type == 'https' and not target.startswith('https://'):
                        target = f'https://{target}'
                    
                    labels = {
                        'device_name': device.name,
                        'device_type': device.device_type,
                        'ip_address': device.ip_address or '',
                        'function': device.function or '',
                        'networks': device.networks or '',
                        'vendor': device.vendor_obj.name if device.vendor_obj else '',
                        'model': device.model_obj.name if device.model_obj else '',
                        'location': device.location_obj.name if device.location_obj else '',
                        'serial_number': device.serial_number or '',
                        'interface_type': device.interface_type or '',
                        'poe_powered': 'true' if device.poe_powered else 'false',
                        'poe_standards': device.poe_standards or '',
                        'monitor_type': monitor_type,
                        'monitor_endpoint': monitor.endpoint or ''
                    }
                    
                    monitors_by_type[directory_name].append({
                        'device_name': device.name,
                        'target': target,
                        'labels': labels
                    })
            
            for directory_name, monitor_list in monitors_by_type.items():
                monitor_dir = Path(temp_dir) / directory_name
                monitor_dir.mkdir(exist_ok=True)
                
                for monitor_data in monitor_list:
                    safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in monitor_data['device_name'])
                    filename = f"{safe_name}.yaml"
                    filepath = monitor_dir / filename
                    
                    yaml_content = [{
                        'targets': [monitor_data['target']],
                        'labels': monitor_data['labels']
                    }]
                    
                    with open(filepath, 'w') as f:
                        yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)
            
            zip_path = Path(temp_dir) / 'prometheus_targets'
            shutil.make_archive(str(zip_path), 'zip', temp_dir)
            
            with open(f'{zip_path}.zip', 'rb') as f:
                zip_data = f.read()
            
            shutil.rmtree(temp_dir)
            
            return send_file(
                io.BytesIO(zip_data),
                mimetype='application/zip',
                as_attachment=True,
                download_name='prometheus_targets.zip'
            )
        
        except Exception as e:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise e

@app.route('/api/stats', methods=['GET'])
def get_stats():
    total_devices = Device.query.count()
    enabled_devices = Device.query.filter_by(monitoring_enabled=True).count()
    
    device_type_counts = {}
    for dtype in DEVICE_TYPES:
        count = Device.query.filter_by(device_type=dtype).count()
        if count > 0:
            device_type_counts[dtype] = count
    
    return jsonify({
        'total_devices': total_devices,
        'enabled_devices': enabled_devices,
        'disabled_devices': total_devices - enabled_devices,
        'device_type_counts': device_type_counts
    })

# Location routes
@app.route('/api/locations', methods=['GET'])
def get_locations():
    locations = Location.query.order_by(Location.name).all()
    return jsonify([l.to_dict() for l in locations])

@app.route('/api/locations/<int:location_id>', methods=['GET'])
def get_location(location_id):
    location = Location.query.get_or_404(location_id)
    return jsonify(location.to_dict())

@app.route('/api/locations', methods=['POST'])
@limiter.limit("30 per minute")
def create_location():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input
    schema = LocationSchema()
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    existing = Location.query.filter_by(name=validated_data['name']).first()
    if existing:
        return jsonify({'error': 'Location already exists'}), 400
    
    location = Location(name=validated_data['name'])
    try:
        db.session.add(location)
        db.session.commit()
        return jsonify(location.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to create location: {error_msg}")
        return jsonify({'error': 'Failed to create location due to an internal error.'}), 500

@app.route('/api/locations/<int:location_id>', methods=['PUT'])
@limiter.limit("30 per minute")
def update_location(location_id):
    location = Location.query.get_or_404(location_id)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input (partial validation for updates)
    schema = LocationSchema(partial=True)
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    if 'name' in validated_data:
        existing = Location.query.filter_by(name=validated_data['name']).first()
        if existing and existing.id != location_id:
            return jsonify({'error': 'Location name already exists'}), 400
        location.name = validated_data['name']
    
    try:
        db.session.commit()
        return jsonify(location.to_dict())
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to update location: {error_msg}")
        return jsonify({'error': 'Failed to update location due to an internal error.'}), 500

@app.route('/api/locations/<int:location_id>', methods=['DELETE'])
@limiter.limit("30 per minute")
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)
    
    if len(location.devices) > 0:
        return jsonify({'error': f'Cannot delete location. {len(location.devices)} device(s) are using this location'}), 400
    
    try:
        db.session.delete(location)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to delete location: {error_msg}")
        return jsonify({'error': 'Failed to delete location due to an internal error.'}), 500

# Vendor routes
@app.route('/api/vendors', methods=['GET'])
def get_vendors():
    vendors = Vendor.query.order_by(Vendor.name).all()
    return jsonify([v.to_dict() for v in vendors])

@app.route('/api/vendors/<int:vendor_id>', methods=['GET'])
def get_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    return jsonify(vendor.to_dict())

@app.route('/api/vendors', methods=['POST'])
@limiter.limit("30 per minute")
def create_vendor():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input
    schema = VendorSchema()
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    existing = Vendor.query.filter_by(name=validated_data['name']).first()
    if existing:
        return jsonify({'error': 'Vendor already exists'}), 400
    
    vendor = Vendor(name=validated_data['name'])
    try:
        db.session.add(vendor)
        db.session.commit()
        return jsonify(vendor.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to create vendor: {error_msg}")
        return jsonify({'error': 'Failed to create vendor due to an internal error.'}), 500

@app.route('/api/vendors/<int:vendor_id>', methods=['PUT'])
@limiter.limit("30 per minute")
def update_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input (partial validation for updates)
    schema = VendorSchema(partial=True)
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    if 'name' in validated_data:
        existing = Vendor.query.filter_by(name=validated_data['name']).first()
        if existing and existing.id != vendor_id:
            return jsonify({'error': 'Vendor name already exists'}), 400
        vendor.name = validated_data['name']
    
    try:
        db.session.commit()
        return jsonify(vendor.to_dict())
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to update vendor: {error_msg}")
        return jsonify({'error': 'Failed to update vendor due to an internal error.'}), 500

@app.route('/api/vendors/<int:vendor_id>', methods=['DELETE'])
@limiter.limit("30 per minute")
def delete_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    
    if len(vendor.devices) > 0:
        return jsonify({'error': f'Cannot delete vendor. {len(vendor.devices)} device(s) are using this vendor'}), 400
    
    try:
        db.session.delete(vendor)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to delete vendor: {error_msg}")
        return jsonify({'error': 'Failed to delete vendor due to an internal error.'}), 500

# Model routes
@app.route('/api/models', methods=['GET'])
def get_models():
    vendor_id = request.args.get('vendor_id')
    if vendor_id:
        models = Model.query.filter_by(vendor_id=vendor_id).order_by(Model.name).all()
    else:
        models = Model.query.order_by(Model.name).all()
    return jsonify([m.to_dict() for m in models])

@app.route('/api/models/<int:model_id>', methods=['GET'])
def get_model(model_id):
    model = Model.query.get_or_404(model_id)
    return jsonify(model.to_dict())

@app.route('/api/models', methods=['POST'])
@limiter.limit("30 per minute")
def create_model():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input
    schema = ModelSchema()
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    vendor = Vendor.query.get(validated_data['vendor_id'])
    if not vendor:
        return jsonify({'error': 'Vendor not found'}), 404
    
    model = Model(
        name=validated_data['name'],
        vendor_id=validated_data['vendor_id']
    )
    try:
        db.session.add(model)
        db.session.commit()
        return jsonify(model.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to create model: {error_msg}")
        return jsonify({'error': 'Failed to create model due to an internal error.'}), 500

@app.route('/api/models/<int:model_id>', methods=['PUT'])
@limiter.limit("30 per minute")
def update_model(model_id):
    model = Model.query.get_or_404(model_id)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input (partial validation for updates)
    schema = ModelSchema(partial=True)
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    if 'name' in validated_data:
        model.name = validated_data['name']
    if 'vendor_id' in validated_data:
        vendor = Vendor.query.get(validated_data['vendor_id'])
        if not vendor:
            return jsonify({'error': 'Vendor not found'}), 404
        model.vendor_id = validated_data['vendor_id']
    
    try:
        db.session.commit()
        return jsonify(model.to_dict())
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to update model: {error_msg}")
        return jsonify({'error': 'Failed to update model due to an internal error.'}), 500

@app.route('/api/models/<int:model_id>', methods=['DELETE'])
@limiter.limit("30 per minute")
def delete_model(model_id):
    model = Model.query.get_or_404(model_id)
    
    if len(model.devices) > 0:
        return jsonify({'error': f'Cannot delete model. {len(model.devices)} device(s) are using this model'}), 400
    
    try:
        db.session.delete(model)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to delete model: {error_msg}")
        return jsonify({'error': 'Failed to delete model due to an internal error.'}), 500

# Initialize database
def init_database():
    """Initialize database and check/update schema"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        if existing_tables:
            print(f"Found existing database with tables: {existing_tables}")
            
            required_tables = ['vendor', 'model', 'location', 'device', 'monitor']
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                print(f"Missing tables detected: {missing_tables}")
                print("Creating missing tables...")
                db.create_all()
                print("Missing tables created successfully!")
            else:
                print("All required tables exist.")
                print("Checking for schema updates...")
                
                # Check Device table for new columns
                device_columns = [col['name'] for col in inspector.get_columns('device')]
                
                if 'location_id' not in device_columns:
                    print("Adding location_id column to device table...")
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE device ADD COLUMN location_id INTEGER'))
                        conn.commit()
                    print("location_id column added successfully!")
                
                if 'poe_standards' not in device_columns:
                    print("Adding poe_standards column to device table...")
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE device ADD COLUMN poe_standards VARCHAR(200)'))
                        conn.commit()
                    print("poe_standards column added successfully!")
                
                print("Schema check complete.")
        else:
            print("No existing database found. Creating new database...")
            db.create_all()
            print("Database created successfully!")

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000)
