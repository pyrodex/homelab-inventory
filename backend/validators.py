"""
Input validation schemas using Marshmallow
"""
from marshmallow import Schema, fields, validate, ValidationError, pre_load
import ipaddress
import re


def validate_ip_or_hostname(value):
    """Validate IP address or hostname"""
    if not value:
        return
    value = value.strip()
    
    # Try IP address first
    try:
        ipaddress.ip_address(value)
        return
    except ValueError:
        pass
    
    # Try hostname (with optional port)
    if ':' in value:
        hostname, port = value.rsplit(':', 1)
        try:
            port_num = int(port)
            if not (1 <= port_num <= 65535):
                raise ValidationError("Port must be between 1 and 65535")
        except ValueError:
            raise ValidationError("Invalid port number")
    else:
        hostname = value
    
    # Validate hostname format
    if len(hostname) > 253:
        raise ValidationError("Hostname too long (max 253 characters)")
    
    # Basic hostname validation (RFC 1123)
    hostname_pattern = re.compile(
        r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])'
        r'(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    )
    
    if not hostname_pattern.match(hostname):
        # Allow IP:port format
        try:
            ipaddress.ip_address(hostname.split(':')[0])
            return
        except ValueError:
            raise ValidationError("Invalid IP address or hostname format")


def validate_url(value):
    """Validate URL format"""
    if not value:
        return
    value = value.strip()
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    if not url_pattern.match(value):
        raise ValidationError("Invalid URL format")


def sanitize_string(value):
    """Sanitize string input"""
    if not value:
        return value
    # Remove null bytes and control characters except newline and tab
    value = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', str(value))
    # Strip whitespace
    return value.strip()


class DeviceSchema(Schema):
    """Validation schema for Device creation/update"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    device_type = fields.Str(
        required=True,
        validate=validate.OneOf([
            'linux_server_physical', 'linux_server_virtual', 'freebsd_server',
            'network_switch', 'wireless_ap', 'icmp_only', 'ip_camera',
            'video_streamer', 'iot_device', 'url', 'dns_record',
            'ipmi_console', 'ups_nut'
        ])
    )
    ip_address = fields.Str(allow_none=True, validate=validate_ip_or_hostname)
    function = fields.Str(allow_none=True, validate=validate.Length(max=200))
    vendor_id = fields.Int(allow_none=True)
    model_id = fields.Int(allow_none=True)
    location_id = fields.Int(allow_none=True)
    serial_number = fields.Str(allow_none=True, validate=validate.Length(max=100))
    networks = fields.Str(allow_none=True, validate=validate.Length(max=200))
    interface_type = fields.Str(allow_none=True, validate=validate.Length(max=200))
    poe_powered = fields.Bool(missing=False)
    poe_standards = fields.Str(allow_none=True, validate=validate.Length(max=200))
    monitoring_enabled = fields.Bool(missing=True)
    
    @pre_load
    def sanitize_fields(self, data, **kwargs):
        """Sanitize string fields"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = sanitize_string(value)
        return data


class MonitorSchema(Schema):
    """Validation schema for Monitor creation/update"""
    monitor_type = fields.Str(
        required=True,
        validate=validate.OneOf([
            'node_exporter', 'smartprom', 'snmp', 'icmp', 'http',
            'https', 'dns', 'ipmi', 'nut', 'docker'
        ])
    )
    endpoint = fields.Str(allow_none=True, validate=validate.Length(max=200))
    port = fields.Int(allow_none=True, validate=validate.Range(min=1, max=65535))
    enabled = fields.Bool(missing=True)
    notes = fields.Str(allow_none=True)
    
    @pre_load
    def sanitize_fields(self, data, **kwargs):
        """Sanitize string fields"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = sanitize_string(value)
        return data


class VendorSchema(Schema):
    """Validation schema for Vendor creation/update"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    
    @pre_load
    def sanitize_fields(self, data, **kwargs):
        """Sanitize string fields"""
        if isinstance(data, dict):
            if 'name' in data and isinstance(data['name'], str):
                data['name'] = sanitize_string(data['name'])
        return data


class ModelSchema(Schema):
    """Validation schema for Model creation/update"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    vendor_id = fields.Int(required=True)
    
    @pre_load
    def sanitize_fields(self, data, **kwargs):
        """Sanitize string fields"""
        if isinstance(data, dict):
            if 'name' in data and isinstance(data['name'], str):
                data['name'] = sanitize_string(data['name'])
        return data


class LocationSchema(Schema):
    """Validation schema for Location creation/update"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    
    @pre_load
    def sanitize_fields(self, data, **kwargs):
        """Sanitize string fields"""
        if isinstance(data, dict):
            if 'name' in data and isinstance(data['name'], str):
                data['name'] = sanitize_string(data['name'])
        return data

