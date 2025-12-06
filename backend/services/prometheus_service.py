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
    'node_exporter', 'smartprom', 'snmp', 'icmp', 'http',
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


def build_prometheus_targets(devices):
    """Build Prometheus target configuration from devices"""
    monitors_by_type = {}
    
    for device in devices:
        for monitor in device.monitors:
            if not monitor.enabled:
                continue
            
            monitor_type = monitor.monitor_type
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
                'deviceFunction': device.device_function or '',
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
    
    return monitors_by_type


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

