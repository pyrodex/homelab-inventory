"""
Tests for IPAM "Add to monitoring": probe + create/enable monitoring
"""
import socket
import threading

import pytest

from models import db, Device, DeviceHistory, Location, Monitor, Subnet
from services import netprobe, onboarding


@pytest.fixture
def app(monkeypatch):
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def lab(app):
    with app.app_context():
        loc = Location(name='Rack A')
        db.session.add(loc)
        db.session.flush()
        db.session.add(Subnet(cidr='127.0.0.0/29', name='loopback lab', location_id=loc.id))
        db.session.add(Subnet(cidr='10.0.0.0/24', name='LAN'))
        off = Device(name='old-nvr', device_type='ip_camera', ip_address='10.0.0.35', monitoring_enabled=False,
                     device_function='NVR')
        db.session.add(off)
        db.session.flush()
        db.session.add(Monitor(device_id=off.id, monitor_type='icmp'))
        db.session.commit()
        return {'loc': loc.id, 'nvr': off.id}


@pytest.fixture
def listeners(monkeypatch):
    """Real TCP listeners on 127.0.0.1 standing in for node_exporter and NUT."""
    socks = []

    def listen():
        s = socket.socket()
        s.bind(('127.0.0.1', 0))
        s.listen(5)
        socks.append(s)

        def accept_loop():
            while True:
                try:
                    conn, _ = s.accept()
                    conn.close()
                except OSError:
                    return
        threading.Thread(target=accept_loop, daemon=True).start()
        return s.getsockname()[1]

    node_port, nut_port = listen(), listen()
    closed = socket.socket()
    closed.bind(('127.0.0.1', 0))
    closed_port = closed.getsockname()[1]
    closed.close()  # nothing listening here
    monkeypatch.setattr(onboarding, 'PROBE_PORTS', [
        (node_port, 'node_exporter', 'node_exporter'),
        (nut_port, 'nut', 'NUT'),
        (closed_port, 'http', 'HTTP'),
    ])
    monkeypatch.setattr(netprobe, 'ping', lambda ip, timeout=1.0: (True, 0.1, None))
    monkeypatch.setattr(netprobe, 'reverse_lookup', lambda ip: ('ups-a.lan', 'found'))
    yield
    for s in socks:
        s.close()


def test_probe_detects_open_ports_and_suggests(client, lab, listeners):
    data = client.post('/api/ipam/probe', json={'ip': '127.0.0.1'}).get_json()
    by_type = {p['monitor_type']: p['open'] for p in data['ports']}
    assert by_type == {'node_exporter': True, 'nut': True, 'http': False}
    suggested = [m['monitor_type'] for m in data['suggested']['monitors']]
    assert suggested == ['icmp', 'node_exporter', 'nut']
    assert data['suggested']['device_type'] == 'ups_nut'
    assert data['suggested']['name'] == 'ups-a'
    assert data['subnet']['location_id'] == lab['loc']
    assert data['device'] is None


def test_probe_rejects_addresses_outside_subnets(client, lab):
    assert client.post('/api/ipam/probe', json={'ip': '8.8.8.8'}).status_code == 400
    assert client.post('/api/ipam/probe', json={'ip': 'not-an-ip'}).status_code == 400


def test_probe_reports_existing_device(client, lab, monkeypatch):
    monkeypatch.setattr(onboarding, 'probe_address', lambda ip: {
        'ip': ip, 'reachable': False, 'rtt_ms': None, 'ptr': None, 'ports': []})
    data = client.post('/api/ipam/probe', json={'ip': '10.0.0.35'}).get_json()
    assert data['device']['name'] == 'old-nvr' and data['device']['monitoring_enabled'] is False
    assert data['suggested']['monitors'] == [{'monitor_type': 'icmp', 'port': None, 'reason': 'default'}]


def test_create_device_with_monitors(client, app, lab):
    resp = client.post('/api/ipam/monitor', json={
        'ip': '10.0.0.77', 'name': 'mystery-box', 'device_type': 'linux_server_physical',
        'location_id': lab['loc'], 'tags': ['found'],
        'monitors': [{'monitor_type': 'icmp'}, {'monitor_type': 'node_exporter'}, {'monitor_type': 'icmp'}],
    })
    assert resp.status_code == 201
    dev = resp.get_json()['device']
    assert dev['name'] == 'mystery-box' and dev['monitoring_enabled'] is True and dev['tags'] == ['found']
    assert sorted(m['monitor_type'] for m in dev['monitors']) == ['icmp', 'node_exporter']  # deduped
    with app.app_context():
        h = DeviceHistory.query.filter_by(device_id=dev['id']).one()
        assert h.change_type == 'create' and 'node_exporter' in h.summary
    # it's now in inventory and monitored
    subnet = next(s for s in client.get('/api/subnets').get_json() if s['cidr'] == '10.0.0.0/24')
    statuses = {a['ip']: a['status'] for a in client.get(f"/api/subnets/{subnet['id']}").get_json()['addresses']}
    assert statuses['10.0.0.77'] == 'monitored'
    # and Prometheus SD picks it up
    targets = [t['targets'][0] for t in client.get('/api/prometheus/sd').get_json()]
    assert '10.0.0.77' in targets and '10.0.0.77:9100' in targets


def test_create_defaults_and_conflict(client, lab):
    resp = client.post('/api/ipam/monitor', json={'ip': '10.0.0.88', 'monitors': [{'monitor_type': 'icmp'}]})
    dev = resp.get_json()['device']
    assert dev['name'] == '10.0.0.88' and dev['device_type'] == 'icmp_only'
    assert dev['deviceFunction'] == 'Added from IPAM'
    again = client.post('/api/ipam/monitor', json={'ip': '10.0.0.88', 'monitors': [{'monitor_type': 'icmp'}]})
    assert again.status_code == 409 and again.get_json()['device']['id'] == dev['id']


def test_enable_existing_device(client, app, lab):
    resp = client.post('/api/ipam/monitor', json={
        'device_id': lab['nvr'], 'monitors': [{'monitor_type': 'icmp'}, {'monitor_type': 'http', 'port': 8080}]})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['created'] is False and body['added_monitors'] == ['http']  # icmp already existed
    assert body['device']['monitoring_enabled'] is True
    with app.app_context():
        h = DeviceHistory.query.filter_by(device_id=lab['nvr']).order_by(DeviceHistory.id.desc()).first()
        assert h.diff['monitoring_enabled'] == {'old': False, 'new': True}
        assert 'enabled monitoring' in h.summary and 'added http' in h.summary


@pytest.mark.parametrize('body,field', [
    ({'ip': '10.0.0.90', 'monitors': []}, 'monitors'),
    ({'ip': '10.0.0.90', 'monitors': [{'monitor_type': 'telepathy'}]}, 'monitors'),
    ({'ip': '10.0.0.90', 'monitors': [{'monitor_type': 'http', 'port': 70000}]}, 'monitors'),
    ({'ip': 'nope', 'monitors': [{'monitor_type': 'icmp'}]}, 'ip'),
    ({'ip': '10.0.0.90', 'device_type': 'toaster', 'monitors': [{'monitor_type': 'icmp'}]}, 'device_type'),
    ({'ip': '10.0.0.90', 'location_id': 999, 'monitors': [{'monitor_type': 'icmp'}]}, 'location_id'),
])
def test_validation_creates_nothing(client, app, lab, body, field):
    resp = client.post('/api/ipam/monitor', json=body)
    assert resp.status_code == 400 and field in resp.get_json()['details']
    with app.app_context():
        assert Device.query.filter_by(ip_address='10.0.0.90').count() == 0
