"""
Health check and monitoring routes
"""
from flask import Blueprint, jsonify
from datetime import datetime
import os

from models import db, Device

# Try to import psutil, but make it optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

health_bp = Blueprint('health', __name__)


def register_health_routes(app, limiter):
    """Register health check routes with the app"""
    app.register_blueprint(health_bp, url_prefix='/api/health')


@health_bp.route('', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'homelab-inventory-api'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503


@health_bp.route('/detailed', methods=['GET'])
def detailed_health():
    """Detailed health check with system metrics"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db_healthy = True
        db_error = None
    except Exception as e:
        db_healthy = False
        db_error = str(e)
    
    # Get database stats
    device_count = Device.query.count() if db_healthy else 0
    
    # Get system metrics if psutil is available
    if PSUTIL_AVAILABLE:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health_data = {
                'status': 'healthy' if db_healthy else 'degraded',
                'timestamp': datetime.utcnow().isoformat(),
                'service': 'homelab-inventory-api',
                'database': {
                    'status': 'healthy' if db_healthy else 'unhealthy',
                    'error': db_error,
                    'device_count': device_count
                },
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory': {
                        'total_gb': round(memory.total / (1024**3), 2),
                        'available_gb': round(memory.available / (1024**3), 2),
                        'percent': memory.percent
                    },
                    'disk': {
                        'total_gb': round(disk.total / (1024**3), 2),
                        'free_gb': round(disk.free / (1024**3), 2),
                        'percent': disk.percent
                    }
                }
            }
            
            status_code = 200 if db_healthy else 503
            return jsonify(health_data), status_code
        except Exception as e:
            # psutil error, return basic health
            return jsonify({
                'status': 'healthy' if db_healthy else 'degraded',
                'timestamp': datetime.utcnow().isoformat(),
                'service': 'homelab-inventory-api',
                'database': {
                    'status': 'healthy' if db_healthy else 'unhealthy',
                    'error': db_error,
                    'device_count': device_count
                },
                'note': f'System metrics unavailable: {str(e)}'
            }), 200 if db_healthy else 503
    else:
        # psutil not available, return basic health
        return jsonify({
            'status': 'healthy' if db_healthy else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'homelab-inventory-api',
            'database': {
                'status': 'healthy' if db_healthy else 'unhealthy',
                'error': db_error,
                'device_count': device_count
            },
            'note': 'System metrics unavailable (psutil not installed)'
        }), 200 if db_healthy else 503

