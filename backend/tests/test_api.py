"""
Tests for API endpoints
"""
import pytest
import json
from models import db, Device, Vendor, Location


@pytest.fixture
def app():
    """Create test Flask app"""
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    flask_app.config['RATELIMIT_ENABLED'] = False  # Disable rate limiting for tests
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def sample_data(app):
    """Create sample data for tests"""
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
        
        return {
            'vendor_id': vendor.id,
            'location_id': location.id,
            'device_id': device.id
        }


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_get_devices(client, sample_data):
    """Test getting all devices"""
    response = client.get('/api/devices')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['name'] == "Test Device"


def test_get_device(client, sample_data):
    """Test getting a single device"""
    device_id = sample_data['device_id']
    response = client.get(f'/api/devices/{device_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['name'] == "Test Device"
    assert data['ip_address'] == "192.168.1.1"


def test_create_device(client, sample_data):
    """Test creating a device"""
    device_data = {
        'name': 'New Device',
        'device_type': 'linux_server_virtual',
        'ip_address': '192.168.1.2',
        'function': 'Web Server',
        'vendor_id': sample_data['vendor_id'],
        'location_id': sample_data['location_id'],
        'serial_number': 'SN789012'
    }
    
    response = client.post(
        '/api/devices',
        data=json.dumps(device_data),
        content_type='application/json'
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'New Device'


def test_create_device_validation_error(client):
    """Test device creation with invalid data"""
    device_data = {
        'name': '',  # Empty name should fail validation
        'device_type': 'invalid_type',  # Invalid device type
    }
    
    response = client.post(
        '/api/devices',
        data=json.dumps(device_data),
        content_type='application/json'
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_get_vendors(client, sample_data):
    """Test getting all vendors"""
    response = client.get('/api/vendors')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['name'] == "Test Vendor"


def test_get_locations(client, sample_data):
    """Test getting all locations"""
    response = client.get('/api/locations')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['name'] == "Test Location"

