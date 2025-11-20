"""
Prometheus export routes
"""
from flask import Blueprint, request, jsonify
import os

from models import Device
from services.prometheus_service import export_to_disk, export_to_zip
from config import Config

prometheus_bp = Blueprint('prometheus', __name__)


def register_prometheus_routes(app, limiter):
    """Register Prometheus routes with the app"""
    app.register_blueprint(prometheus_bp, url_prefix='/api/prometheus')
    
    # Apply rate limiting
    limiter.limit("10 per minute")(export_prometheus_config)


@prometheus_bp.route('/export', methods=['GET'])
def export_prometheus_config():
    """Export Prometheus configuration"""
    devices = Device.query.filter_by(monitoring_enabled=True).all()
    
    export_mode = request.args.get('mode', 'write')
    export_path = os.environ.get('PROMETHEUS_EXPORT_PATH', Config.PROMETHEUS_EXPORT_PATH)
    
    if export_mode == 'write':
        result = export_to_disk(export_path, devices)
        return jsonify(result)
    else:  # download mode
        return export_to_zip(devices)

