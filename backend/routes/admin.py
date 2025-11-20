"""
Admin routes (vendors, models, locations)
"""
from flask import Blueprint, request, jsonify
from marshmallow import ValidationError as MarshmallowValidationError

from flask import jsonify
from models import db, Vendor, Model, Location
from validators import VendorSchema, ModelSchema, LocationSchema
from exceptions import DatabaseError, ConflictError, NotFoundError
import logging

admin_bp = Blueprint('admin', __name__)


def register_admin_routes(app, limiter):
    """Register admin routes with the app"""
    app.register_blueprint(admin_bp, url_prefix='/api')
    
    # Apply rate limiting
    limiter.limit("30 per minute")(create_vendor)
    limiter.limit("30 per minute")(update_vendor)
    limiter.limit("30 per minute")(delete_vendor)
    limiter.limit("30 per minute")(create_model)
    limiter.limit("30 per minute")(update_model)
    limiter.limit("30 per minute")(delete_model)
    limiter.limit("30 per minute")(create_location)
    limiter.limit("30 per minute")(update_location)
    limiter.limit("30 per minute")(delete_location)


# Location routes
@admin_bp.route('/locations', methods=['GET'])
def get_locations():
    """Get all locations"""
    locations = Location.query.order_by(Location.name).all()
    return jsonify([l.to_dict() for l in locations])


@admin_bp.route('/locations/<int:location_id>', methods=['GET'])
def get_location(location_id):
    """Get a single location by ID"""
    location = Location.query.get_or_404(location_id)
    return jsonify(location.to_dict())


@admin_bp.route('/locations', methods=['POST'])
def create_location():
    """Create a new location"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input
    schema = LocationSchema()
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    existing = Location.query.filter_by(name=validated_data['name']).first()
    if existing:
        return jsonify(ConflictError('Location already exists').to_dict()), 409
    
    location = Location(name=validated_data['name'])
    try:
        db.session.add(location)
        db.session.commit()
        return jsonify(location.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to create location: {error_msg}")
        raise DatabaseError("Failed to create location due to an internal error.")


@admin_bp.route('/locations/<int:location_id>', methods=['PUT'])
def update_location(location_id):
    """Update a location"""
    location = Location.query.get_or_404(location_id)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input (partial validation for updates)
    schema = LocationSchema(partial=True)
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    if 'name' in validated_data:
        existing = Location.query.filter_by(name=validated_data['name']).first()
        if existing and existing.id != location_id:
            return jsonify(ConflictError('Location name already exists').to_dict()), 409
        location.name = validated_data['name']
    
    try:
        db.session.commit()
        return jsonify(location.to_dict())
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to update location: {error_msg}")
        return jsonify(DatabaseError("Failed to update location due to an internal error.").to_dict()), 500


@admin_bp.route('/locations/<int:location_id>', methods=['DELETE'])
def delete_location(location_id):
    """Delete a location"""
    location = Location.query.get_or_404(location_id)
    
    if len(location.devices) > 0:
        return jsonify({'error': f'Cannot delete location. {len(location.devices)} device(s) are using this location'}), 400
    
    try:
        db.session.delete(location)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to delete location: {error_msg}")
        return jsonify(DatabaseError("Failed to delete location due to an internal error.").to_dict()), 500


# Vendor routes
@admin_bp.route('/vendors', methods=['GET'])
def get_vendors():
    """Get all vendors"""
    vendors = Vendor.query.order_by(Vendor.name).all()
    return jsonify([v.to_dict() for v in vendors])


@admin_bp.route('/vendors/<int:vendor_id>', methods=['GET'])
def get_vendor(vendor_id):
    """Get a single vendor by ID"""
    vendor = Vendor.query.get_or_404(vendor_id)
    return jsonify(vendor.to_dict())


@admin_bp.route('/vendors', methods=['POST'])
def create_vendor():
    """Create a new vendor"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input
    schema = VendorSchema()
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    existing = Vendor.query.filter_by(name=validated_data['name']).first()
    if existing:
        return jsonify(ConflictError('Vendor already exists').to_dict()), 409
    
    vendor = Vendor(name=validated_data['name'])
    try:
        db.session.add(vendor)
        db.session.commit()
        return jsonify(vendor.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to create vendor: {error_msg}")
        raise DatabaseError("Failed to create vendor due to an internal error.")


@admin_bp.route('/vendors/<int:vendor_id>', methods=['PUT'])
def update_vendor(vendor_id):
    """Update a vendor"""
    vendor = Vendor.query.get_or_404(vendor_id)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input (partial validation for updates)
    schema = VendorSchema(partial=True)
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    if 'name' in validated_data:
        existing = Vendor.query.filter_by(name=validated_data['name']).first()
        if existing and existing.id != vendor_id:
            return jsonify(ConflictError('Vendor name already exists').to_dict()), 409
        vendor.name = validated_data['name']
    
    try:
        db.session.commit()
        return jsonify(vendor.to_dict())
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to update vendor: {error_msg}")
        return jsonify(DatabaseError("Failed to update vendor due to an internal error.").to_dict()), 500


@admin_bp.route('/vendors/<int:vendor_id>', methods=['DELETE'])
def delete_vendor(vendor_id):
    """Delete a vendor"""
    vendor = Vendor.query.get_or_404(vendor_id)
    
    if len(vendor.devices) > 0:
        return jsonify({'error': f'Cannot delete vendor. {len(vendor.devices)} device(s) are using this vendor'}), 400
    
    try:
        db.session.delete(vendor)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to delete vendor: {error_msg}")
        return jsonify(DatabaseError("Failed to delete vendor due to an internal error.").to_dict()), 500


# Model routes
@admin_bp.route('/models', methods=['GET'])
def get_models():
    """Get all models, optionally filtered by vendor"""
    vendor_id = request.args.get('vendor_id')
    if vendor_id:
        models = Model.query.filter_by(vendor_id=vendor_id).order_by(Model.name).all()
    else:
        models = Model.query.order_by(Model.name).all()
    return jsonify([m.to_dict() for m in models])


@admin_bp.route('/models/<int:model_id>', methods=['GET'])
def get_model(model_id):
    """Get a single model by ID"""
    model = Model.query.get_or_404(model_id)
    return jsonify(model.to_dict())


@admin_bp.route('/models', methods=['POST'])
def create_model():
    """Create a new model"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input
    schema = ModelSchema()
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    vendor = Vendor.query.get(validated_data['vendor_id'])
    if not vendor:
        return jsonify(NotFoundError('Vendor not found').to_dict()), 404
    
    model = Model(
        name=validated_data['name'],
        vendor_id=validated_data['vendor_id']
    )
    try:
        db.session.add(model)
        db.session.commit()
        return jsonify(model.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to create model: {error_msg}")
        return jsonify(DatabaseError("Failed to create model due to an internal error.").to_dict()), 500


@admin_bp.route('/models/<int:model_id>', methods=['PUT'])
def update_model(model_id):
    """Update a model"""
    model = Model.query.get_or_404(model_id)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.json
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate input (partial validation for updates)
    schema = ModelSchema(partial=True)
    try:
        validated_data = schema.load(data)
    except MarshmallowValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400
    
    if 'name' in validated_data:
        model.name = validated_data['name']
    if 'vendor_id' in validated_data:
        vendor = Vendor.query.get(validated_data['vendor_id'])
        if not vendor:
            return jsonify(NotFoundError('Vendor not found').to_dict()), 404
        model.vendor_id = validated_data['vendor_id']
    
    try:
        db.session.commit()
        return jsonify(model.to_dict())
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to update model: {error_msg}")
        return jsonify(DatabaseError("Failed to update model due to an internal error.").to_dict()), 500


@admin_bp.route('/models/<int:model_id>', methods=['DELETE'])
def delete_model(model_id):
    """Delete a model"""
    model = Model.query.get_or_404(model_id)
    
    if len(model.devices) > 0:
        return jsonify({'error': f'Cannot delete model. {len(model.devices)} device(s) are using this model'}), 400
    
    try:
        db.session.delete(model)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logging.error(f"Failed to delete model: {error_msg}")
        return jsonify(DatabaseError("Failed to delete model due to an internal error.").to_dict()), 500

