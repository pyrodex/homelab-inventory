"""
Database models
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


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

