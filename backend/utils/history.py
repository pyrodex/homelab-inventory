"""
Helpers for extracting device state and computing diffs for history tracking
"""
from typing import Any, Dict, Optional

from models import Device

TRACKED_FIELDS = [
    'name',
    'device_type',
    'ip_address',
    'deviceFunction',
    'vendor_id',
    'model_id',
    'location_id',
    'serial_number',
    'networks',
    'interface_type',
    'poe_powered',
    'poe_standards',
    'monitoring_enabled'
]


def extract_device_state(device: Device) -> Dict[str, Any]:
    """Return a dict of tracked fields for a device."""
    return {
        'name': device.name,
        'device_type': device.device_type,
        'ip_address': device.ip_address,
        'deviceFunction': getattr(device, 'device_function', None),
        'vendor_id': device.vendor_id,
        'model_id': device.model_id,
        'location_id': device.location_id,
        'serial_number': device.serial_number,
        'networks': device.networks,
        'interface_type': device.interface_type,
        'poe_powered': device.poe_powered,
        'poe_standards': device.poe_standards,
        'monitoring_enabled': device.monitoring_enabled,
    }


def compute_diff(
    old_state: Optional[Dict[str, Any]],
    new_state: Optional[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """Compute field-level diff between two device states."""
    old_state = old_state or {}
    new_state = new_state or {}
    diff: Dict[str, Dict[str, Any]] = {}

    for field in TRACKED_FIELDS:
        old_value = old_state.get(field)
        new_value = new_state.get(field)
        if old_value != new_value:
            diff[field] = {'old': old_value, 'new': new_value}

    return diff

