"""
Database models
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


def _iso_utc(value):
    """ISO-8601 with an explicit UTC offset (naive datetimes here are UTC)."""
    return value.isoformat() + 'Z' if value else None


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
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    devices = db.relationship('Device', backref='model_obj', lazy=True)
    
    # Composite unique constraint for vendor + model name
    __table_args__ = (
        db.UniqueConstraint('vendor_id', 'name', name='uq_vendor_model'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor.name,
            'device_count': len(self.devices),
            'created_at': self.created_at.isoformat()
        }


device_tags = db.Table(
    'device_tag',
    db.Column('device_id', db.Integer, db.ForeignKey('device.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True, index=True),
)


class Tag(db.Model):
    """Free-form label attached to devices (e.g. prod, storage, k8s)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'device_count': len(self.devices),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    device_type = db.Column(db.String(50), nullable=False, index=True)
    ip_address = db.Column(db.String(100), index=True)
    # Keep underlying column name for compatibility, expose attribute as device_function
    device_function = db.Column('function', db.String(200), index=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=True, index=True)
    model_id = db.Column(db.Integer, db.ForeignKey('model.id'), nullable=True, index=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True, index=True)
    serial_number = db.Column(db.String(100), index=True)
    networks = db.Column(db.String(200))  # Comma-separated: LAN,IoT,DMZ,GUEST or ALL
    interface_type = db.Column(db.String(200))  # Comma-separated interface types
    poe_powered = db.Column(db.Boolean, default=False, index=True)
    poe_standards = db.Column(db.String(200))  # Comma-separated PoE standards
    monitoring_enabled = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    monitors = db.relationship('Monitor', backref='device', lazy=True, cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=device_tags, backref=db.backref('devices', lazy=True),
                           lazy='selectin', order_by='Tag.name')
    outgoing_links = db.relationship('DeviceLink', foreign_keys='DeviceLink.source_id',
                                     backref='source', lazy=True, cascade='all, delete-orphan')
    incoming_links = db.relationship('DeviceLink', foreign_keys='DeviceLink.target_id',
                                     backref='target', lazy=True, cascade='all, delete-orphan')
    
    # Composite indexes for common query patterns
    __table_args__ = (
        db.Index('idx_device_type_monitoring', 'device_type', 'monitoring_enabled'),
        db.Index('idx_vendor_model', 'vendor_id', 'model_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'device_type': self.device_type,
            'ip_address': self.ip_address,
            'deviceFunction': self.device_function,
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
            'tags': [t.name for t in self.tags],
            'links': [l.to_dict() for l in self.outgoing_links],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    # Backwards-compatible alias if older code references .function
    @property
    def function(self):
        return self.device_function

    @function.setter
    def function(self, value):
        self.device_function = value


class Monitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False, index=True)
    monitor_type = db.Column(db.String(50), nullable=False, index=True)
    endpoint = db.Column(db.String(200))
    port = db.Column(db.Integer, index=True)
    enabled = db.Column(db.Boolean, default=True, index=True)
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


class DeviceHistory(db.Model):
    """Audit log of device changes"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(
        db.Integer,
        db.ForeignKey('device.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    change_type = db.Column(db.String(50), nullable=False, index=True)  # create, update, delete, bulk_import, bulk_delete
    diff = db.Column(db.JSON, nullable=False)
    summary = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    device = db.relationship(
        'Device',
        backref=db.backref('history_entries', lazy=True, passive_deletes=True)
    )

    __table_args__ = (
        db.Index('idx_history_device_created_at', 'device_id', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'change_type': self.change_type,
            'diff': self.diff,
            'summary': self.summary,
            'created_at': self.created_at.isoformat()
        }



class Subnet(db.Model):
    """An IP subnet tracked for IPAM-style address utilization"""
    id = db.Column(db.Integer, primary_key=True)
    cidr = db.Column(db.String(64), nullable=False, unique=True, index=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    vlan_id = db.Column(db.Integer)
    gateway = db.Column(db.String(64))
    # Comma/newline separated IPs, ranges (a-b) or CIDRs that should not be handed out
    # (e.g. DHCP pools, VIPs, future use)
    reserved_ranges = db.Column(db.Text)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True, index=True)
    # Scheduled ping sweep (IPv4, bounded size) to find live addresses not in inventory
    scan_enabled = db.Column(db.Boolean, nullable=False, default=False)
    scan_interval_minutes = db.Column(db.Integer, nullable=False, default=60)
    last_scan_at = db.Column(db.DateTime)
    last_scan_duration_ms = db.Column(db.Integer)
    last_scan_alive = db.Column(db.Integer)
    last_scan_error = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    location = db.relationship('Location', backref=db.backref('subnets', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'cidr': self.cidr,
            'name': self.name,
            'description': self.description,
            'vlan_id': self.vlan_id,
            'gateway': self.gateway,
            'reserved_ranges': self.reserved_ranges,
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else None,
            'scan_enabled': bool(self.scan_enabled),
            'scan_interval_minutes': self.scan_interval_minutes,
            'last_scan_at': _iso_utc(self.last_scan_at),
            'last_scan_duration_ms': self.last_scan_duration_ms,
            'last_scan_alive': self.last_scan_alive,
            'last_scan_error': self.last_scan_error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


LINK_TYPES = ('runs_on', 'connected_to', 'powered_by')


class DeviceLink(db.Model):
    """
    Directed dependency between two devices: source depends on target.
      runs_on      - VM/container -> hypervisor/host
      connected_to - device -> switch/AP (optionally with port)
      powered_by   - device -> UPS/PDU/PoE switch (optionally with port)
    """
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('device.id', ondelete='CASCADE'), nullable=False, index=True)
    target_id = db.Column(db.Integer, db.ForeignKey('device.id', ondelete='CASCADE'), nullable=False, index=True)
    link_type = db.Column(db.String(20), nullable=False, index=True)
    port = db.Column(db.String(50))
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('source_id', 'target_id', 'link_type', name='uq_device_link'),
        db.CheckConstraint('source_id != target_id', name='ck_device_link_not_self'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'source_id': self.source_id,
            'source_name': self.source.name if self.source else None,
            'target_id': self.target_id,
            'target_name': self.target.name if self.target else None,
            'link_type': self.link_type,
            'port': self.port,
            'notes': self.notes,
        }


class IpObservation(db.Model):
    """
    What the network says about an address, independent of inventory:
    the latest ping-sweep result and/or DHCP lease. One row per IP.
    """
    __tablename__ = 'ip_observation'
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(64), nullable=False, unique=True, index=True)
    hostname = db.Column(db.String(255))
    mac = db.Column(db.String(64))
    # ping sweep
    ping_last_checked = db.Column(db.DateTime)
    ping_last_seen = db.Column(db.DateTime, index=True)
    ping_reachable = db.Column(db.Boolean)
    ping_rtt_ms = db.Column(db.Float)
    ping_hostname = db.Column(db.String(255))
    # DHCP lease (dnsmasq)
    dhcp_source = db.Column(db.String(255), index=True)
    dhcp_hostname = db.Column(db.String(255))
    dhcp_client_id = db.Column(db.String(255))
    dhcp_expires = db.Column(db.DateTime)   # NULL with dhcp_active = infinite lease
    dhcp_active = db.Column(db.Boolean, nullable=False, default=False, index=True)
    dhcp_last_seen = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'ip': self.ip,
            'hostname': self.dhcp_hostname or self.ping_hostname or self.hostname,
            'mac': self.mac,
            'ping_reachable': self.ping_reachable,
            'ping_last_seen': _iso_utc(self.ping_last_seen),
            'ping_last_checked': _iso_utc(self.ping_last_checked),
            'ping_rtt_ms': self.ping_rtt_ms,
            'dhcp_active': bool(self.dhcp_active),
            'dhcp_expires': _iso_utc(self.dhcp_expires),
            'dhcp_source': self.dhcp_source,
        }
