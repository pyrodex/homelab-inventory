"""
Advanced search routes
"""
from flask import Blueprint, request, jsonify
from sqlalchemy import or_, and_
import logging

from models import db, Device, Vendor, Model, Location

search_bp = Blueprint('search', __name__)


def register_search_routes(app, limiter):
    """Register search routes with the app"""
    app.register_blueprint(search_bp, url_prefix='/api/search')
    
    # Apply rate limiting
    limiter.limit("60 per minute")(advanced_search)


@search_bp.route('/devices', methods=['GET'])
def advanced_search():
    """Advanced search with multiple filters"""
    try:
        query = Device.query
        
        # Get query parameters
        search_term = request.args.get('q', '').strip()
        device_type = request.args.get('type')
        vendor_id = request.args.get('vendor_id', type=int)
        model_id = request.args.get('model_id', type=int)
        location_id = request.args.get('location_id', type=int)
        monitoring_enabled = request.args.get('monitoring_enabled')
        poe_powered = request.args.get('poe_powered')
        has_ip = request.args.get('has_ip')
        
        # Apply filters
        if device_type:
            query = query.filter(Device.device_type == device_type)
        
        if vendor_id:
            query = query.filter(Device.vendor_id == vendor_id)
        
        if model_id:
            query = query.filter(Device.model_id == model_id)
        
        if location_id:
            query = query.filter(Device.location_id == location_id)
        
        if monitoring_enabled is not None:
            monitoring_enabled_bool = monitoring_enabled.lower() == 'true'
            query = query.filter(Device.monitoring_enabled == monitoring_enabled_bool)
        
        if poe_powered is not None:
            poe_powered_bool = poe_powered.lower() == 'true'
            query = query.filter(Device.poe_powered == poe_powered_bool)
        
        if has_ip is not None:
            has_ip_bool = has_ip.lower() == 'true'
            if has_ip_bool:
                query = query.filter(Device.ip_address.isnot(None))
            else:
                query = query.filter(Device.ip_address.is_(None))
        
        # Apply search term across multiple fields
        if search_term:
            search_filter = or_(
                Device.name.ilike(f'%{search_term}%'),
                Device.ip_address.ilike(f'%{search_term}%'),
                Device.function.ilike(f'%{search_term}%'),
                Device.serial_number.ilike(f'%{search_term}%'),
                Device.networks.ilike(f'%{search_term}%'),
                Device.notes.ilike(f'%{search_term}%')
            )
            query = query.filter(search_filter)
        
        # Execute query
        devices = query.all()
        
        return jsonify({
            'results': [d.to_dict() for d in devices],
            'count': len(devices),
            'filters_applied': {
                'search_term': search_term,
                'device_type': device_type,
                'vendor_id': vendor_id,
                'model_id': model_id,
                'location_id': location_id,
                'monitoring_enabled': monitoring_enabled,
                'poe_powered': poe_powered,
                'has_ip': has_ip
            }
        })
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Advanced search failed: {error_msg}")
        return jsonify({'error': 'Search failed', 'message': error_msg}), 500

