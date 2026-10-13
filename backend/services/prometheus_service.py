"""
Prometheus export service
"""
import yaml
import io
import os
import tempfile
import shutil
from pathlib import Path
from flask import send_file

# Note: Import models here to avoid circular imports
# Device will be passed in from routes


DEVICE_TYPES = [
    'linux_server_physical', 'linux_server_virtual', 'freebsd_server',
    'network_switch', 'wireless_ap', 'icmp_only', 'ip_camera',
    'video_streamer', 'iot_device', 'url', 'dns_record',
    'ipmi_console', 'ups_nut'
]

MONITORING_TYPES = [
    'node_exporter', 'smartctl_exporter', 'snmp', 'icmp', 'http',
    'https', 'dns', 'ipmi', 'nut', 'docker'
]


def get_monitor_directory_name(monitor_type, device_type):
    """Return the directory name based on monitor type and device type"""
    if monitor_type == 'node_exporter':
        if device_type.startswith('linux_server_'):
            return 'linux_node_exporter'
        elif device_type == 'freebsd_server':
            return 'freebsd_node_exporter'
    return monitor_type


DEFAULT_PORTS = {
    'node_exporter': 9100,
    'smartctl_exporter': 9633,
    'snmp': 161,
    'http': 80,
    'https': 443,
    'dns': 53,
    'ipmi': 623,
    'nut': 3493,
    'docker': 8090
}


def build_monitor_target(device, monitor):
    """
    Compute the Prometheus target string for one monitor on a device.
    Shared by file export, HTTP service discovery, and status matching so
    all three always agree on what a target looks like.
    """
    monitor_type = monitor.monitor_type
    target = device.ip_address or ''
    if monitor.port:
        if ':' in target:
            target = target.split(':')[0] + f':{monitor.port}'
        else:
            target = f'{target}:{monitor.port}'
    elif ':' not in target and monitor_type in DEFAULT_PORTS:
        target = f'{target}:{DEFAULT_PORTS[monitor_type]}'

    if monitor_type == 'http' and not target.startswith('http://'):
        target = f'http://{target}'
    elif monitor_type == 'https' and not target.startswith('https://'):
        target = f'https://{target}'
    return target


def build_target_labels(device, monitor):
    """Labels attached to every exported target."""
    return {
        'inventory_device_id': str(device.id),
        'device_name': device.name,
        'device_type': device.device_type,
        'ip_address': device.ip_address or '',
        'deviceFunction': device.device_function or '',
        'networks': device.networks or '',
        'vendor': device.vendor_obj.name if device.vendor_obj else '',
        'model': device.model_obj.name if device.model_obj else '',
        'location': device.location_obj.name if device.location_obj else '',
        'serial_number': device.serial_number or '',
        'interface_type': device.interface_type or '',
        'poe_powered': 'true' if device.poe_powered else 'false',
        'poe_standards': device.poe_standards or '',
        'monitor_type': monitor.monitor_type,
        'monitor_endpoint': monitor.endpoint or '',
        # ",a,b," so `tags=~".*,prod,.*"` matches one tag exactly (Consul-style)
        'tags': f",{','.join(t.name for t in device.tags)}," if device.tags else '',
        'runs_on': next((l.target.name for l in device.outgoing_links if l.link_type == 'runs_on'), ''),
    }


def iter_enabled_targets(devices):
    """Yield (device, monitor, group_name, target) for every enabled monitor."""
    for device in devices:
        if not device.ip_address:
            continue
        for monitor in device.monitors:
            if not monitor.enabled:
                continue
            group = get_monitor_directory_name(monitor.monitor_type, device.device_type)
            yield device, monitor, group, build_monitor_target(device, monitor)


def build_prometheus_targets(devices):
    """Build Prometheus target configuration from devices"""
    monitors_by_type = {}
    for device, monitor, group, target in iter_enabled_targets(devices):
        monitors_by_type.setdefault(group, []).append({
            'device_name': device.name,
            'target': target,
            'labels': build_target_labels(device, monitor)
        })
    return monitors_by_type


def build_http_sd(devices, group=None):
    """
    Build a Prometheus HTTP service discovery payload:
    [{"targets": [...], "labels": {...}}, ...]
    Optionally limited to a single group (same names as the export folders,
    e.g. linux_node_exporter, snmp, icmp).
    """
    payload = []
    for device, monitor, group_name, target in iter_enabled_targets(devices):
        if group and group_name != group:
            continue
        labels = build_target_labels(device, monitor)
        labels['inventory_group'] = group_name
        payload.append({'targets': [target], 'labels': labels})
    return payload


def export_to_disk(export_path, devices):
    """Export Prometheus targets to disk"""
    export_dir = Path(export_path)
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Remove only files, not directories
    for item in export_dir.iterdir():
        if item.is_dir():
            for file in item.iterdir():
                if file.is_file():
                    file.unlink()
        else:
            item.unlink()
    
    monitors_by_type = build_prometheus_targets(devices)
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
    
    return {
        'status': 'success',
        'message': f'Successfully wrote {files_created} target files to {export_path}',
        'path': export_path,
        'files_created': files_created
    }


def export_to_zip(devices):
    """Export Prometheus targets as ZIP archive"""
    temp_dir = tempfile.mkdtemp()
    
    try:
        monitors_by_type = build_prometheus_targets(devices)
        
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

