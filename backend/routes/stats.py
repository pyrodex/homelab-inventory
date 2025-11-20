"""
Stats routes
"""
from flask import Blueprint, jsonify
from models import Device

DEVICE_TYPES = [
    'linux_server_physical', 'linux_server_virtual', 'freebsd_server',
    'network_switch', 'wireless_ap', 'icmp_only', 'ip_camera',
    'video_streamer', 'iot_device', 'url', 'dns_record',
    'ipmi_console', 'ups_nut'
]

stats_bp = Blueprint('stats', __name__)


def register_stats_routes(app):
    """Register stats routes with the app"""
    app.register_blueprint(stats_bp, url_prefix='/api')


@stats_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get dashboard statistics"""
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

