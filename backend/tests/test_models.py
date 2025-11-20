"""
Tests for database models
"""
import pytest
from datetime import datetime
from models import db, Device, Vendor, Model, Location, Monitor


@pytest.fixture
def app():
    """Create test Flask app"""
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


def test_location_creation(app):
    """Test creating a location"""
    with app.app_context():
        location = Location(name="Test Location")
        db.session.add(location)
        db.session.commit()
        
        assert location.id is not None
        assert location.name == "Test Location"
        assert isinstance(location.created_at, datetime)


def test_vendor_creation(app):
    """Test creating a vendor"""
    with app.app_context():
        vendor = Vendor(name="Test Vendor")
        db.session.add(vendor)
        db.session.commit()
        
        assert vendor.id is not None
        assert vendor.name == "Test Vendor"


def test_model_creation(app):
    """Test creating a model"""
    with app.app_context():
        vendor = Vendor(name="Test Vendor")
        db.session.add(vendor)
        db.session.commit()
        
        model = Model(name="Test Model", vendor_id=vendor.id)
        db.session.add(model)
        db.session.commit()
        
        assert model.id is not None
        assert model.name == "Test Model"
        assert model.vendor_id == vendor.id


def test_device_creation(app):
    """Test creating a device"""
    with app.app_context():
        vendor = Vendor(name="Test Vendor")
        location = Location(name="Test Location")
        db.session.add(vendor)
        db.session.add(location)
        db.session.commit()
        
        device = Device(
            name="Test Device",
            device_type="linux_server_physical",
            ip_address="192.168.1.1",
            function="Test Server",
            vendor_id=vendor.id,
            location_id=location.id,
            serial_number="SN123456"
        )
        db.session.add(device)
        db.session.commit()
        
        assert device.id is not None
        assert device.name == "Test Device"
        assert device.monitoring_enabled is True  # Default value


def test_device_to_dict(app):
    """Test device serialization"""
    with app.app_context():
        vendor = Vendor(name="Test Vendor")
        location = Location(name="Test Location")
        db.session.add(vendor)
        db.session.add(location)
        db.session.commit()
        
        device = Device(
            name="Test Device",
            device_type="linux_server_physical",
            ip_address="192.168.1.1",
            vendor_id=vendor.id,
            location_id=location.id
        )
        db.session.add(device)
        db.session.commit()
        
        device_dict = device.to_dict()
        assert device_dict['id'] == device.id
        assert device_dict['name'] == "Test Device"
        assert device_dict['vendor_name'] == "Test Vendor"
        assert device_dict['location_name'] == "Test Location"
        assert 'monitors' in device_dict

