"""
Tests for subnet / IPAM support
"""
import ipaddress

import pytest

from models import db, Device, Monitor, Subnet
from services.ipam import extract_ip, parse_reserved, usable_bounds


@pytest.fixture
def app():
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['RATELIMIT_ENABLED'] = False
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
    """A /28 with a mix of monitored, unmonitored and monitor-only addresses"""
    with app.app_context():
        monitored = Device(name='nas', device_type='linux_server_physical',
                           ip_address='10.0.0.2', monitoring_enabled=True)
        disabled = Device(name='old-cam', device_type='ip_camera',
                          ip_address='10.0.0.3', monitoring_enabled=False)
        by_port = Device(name='web', device_type='url',
                         ip_address='10.0.0.4:8080', monitoring_enabled=True)
        hostname = Device(name='dns', device_type='dns_record',
                          ip_address='pihole.lan', monitoring_enabled=True)
        outside = Device(name='far', device_type='icmp_only',
                         ip_address='172.16.5.5', monitoring_enabled=True)
        db.session.add_all([monitored, disabled, by_port, hostname, outside])
        db.session.flush()
        # A monitor endpoint pointing at a different IP also consumes it
        db.session.add(Monitor(device_id=hostname.id, monitor_type='http',
                               endpoint='http://10.0.0.5:80/admin', enabled=True))
        db.session.add(Subnet(cidr='10.0.0.0/28', name='Lab', gateway='10.0.0.1',
                              reserved_ranges='10.0.0.10-12, 10.0.0.14'))
        db.session.commit()
        return Subnet.query.first().id


# --- unit helpers -----------------------------------------------------------

@pytest.mark.parametrize('raw,expected', [
    ('192.168.1.5', '192.168.1.5'),
    ('192.168.1.5:9100', '192.168.1.5'),
    ('https://192.168.1.5:8443/x', '192.168.1.5'),
    ('fd00::1', 'fd00::1'),
    ('[fd00::1]:443', 'fd00::1'),
    ('nas.lan', None),
    ('nas.lan:22', None),
    ('', None),
    (None, None),
])
def test_extract_ip(raw, expected):
    ip = extract_ip(raw)
    assert (str(ip) if ip else None) == expected


def test_parse_reserved_formats():
    net = ipaddress.ip_network('192.168.1.0/24')
    ranges = parse_reserved('192.168.1.10\n192.168.1.100-199, 192.168.1.240/29', net)
    assert len(ranges) == 3
    assert ranges[1][1] - ranges[1][0] + 1 == 100
    assert ranges[2][1] - ranges[2][0] + 1 == 8


def test_parse_reserved_rejects_outside():
    with pytest.raises(ValueError):
        parse_reserved('10.9.9.9', ipaddress.ip_network('10.0.0.0/24'))


def test_usable_bounds_edge_prefixes():
    assert usable_bounds(ipaddress.ip_network('10.0.0.0/31')) == (
        int(ipaddress.ip_address('10.0.0.0')), int(ipaddress.ip_address('10.0.0.1')))
    lo, hi = usable_bounds(ipaddress.ip_network('10.0.0.0/30'))
    assert hi - lo + 1 == 2


# --- API --------------------------------------------------------------------

def test_utilization_detail(client, lab):
    resp = client.get(f'/api/subnets/{lab}')
    assert resp.status_code == 200
    data = resp.get_json()
    s = data['summary']
    # /28 = 16 addresses, 14 usable
    assert s['usable'] == 14
    assert s['used'] == 4          # .2 .3 .4 .5
    assert s['monitored'] == 3     # .2 .4 .5
    assert s['unmonitored'] == 1   # .3
    assert s['reserved'] == 5      # gateway .1 + .10-.12 + .14
    assert s['free'] == 5          # .6 .7 .8 .9 .13
    assert [(r['start'], r['end']) for r in data['free_ranges']] == [
        ('10.0.0.6', '10.0.0.9'), ('10.0.0.13', '10.0.0.13')]

    statuses = {a['ip']: a['status'] for a in data['addresses']}
    assert statuses['10.0.0.0'] == 'network'
    assert statuses['10.0.0.1'] == 'gateway'
    assert statuses['10.0.0.3'] == 'unmonitored'
    assert statuses['10.0.0.5'] == 'monitored'
    assert statuses['10.0.0.11'] == 'reserved'
    assert statuses['10.0.0.15'] == 'broadcast'


def test_next_free(client, lab):
    resp = client.get(f'/api/subnets/{lab}/next-free?count=6')
    data = resp.get_json()
    assert data['addresses'] == ['10.0.0.6', '10.0.0.7', '10.0.0.8', '10.0.0.9', '10.0.0.13']


def test_list_includes_summary(client, lab):
    data = client.get('/api/subnets').get_json()
    assert len(data) == 1
    assert data[0]['summary']['free'] == 5


def test_unassigned_devices(client, lab):
    data = client.get('/api/subnets/unassigned').get_json()
    assert [d['ip_address'] for d in data] == ['172.16.5.5']


def test_create_normalizes_and_rejects_duplicates(client):
    resp = client.post('/api/subnets', json={'cidr': '192.168.50.17/24', 'name': 'IoT'})
    assert resp.status_code == 201
    assert resp.get_json()['cidr'] == '192.168.50.0/24'
    dup = client.post('/api/subnets', json={'cidr': '192.168.50.0/24'})
    assert dup.status_code == 409


@pytest.mark.parametrize('payload,field', [
    ({'cidr': '192.168.1.0'}, 'cidr'),
    ({'cidr': 'nope/24'}, 'cidr'),
    ({'cidr': '192.168.1.0/24', 'gateway': '10.0.0.1'}, 'gateway'),
    ({'cidr': '192.168.1.0/24', 'reserved_ranges': '192.168.2.1'}, 'reserved_ranges'),
    ({'cidr': '192.168.1.0/24', 'vlan_id': 5000}, 'vlan_id'),
])
def test_create_validation(client, payload, field):
    resp = client.post('/api/subnets', json=payload)
    assert resp.status_code == 400
    assert field in resp.get_json()['details']


def test_update_and_delete(client, lab):
    resp = client.put(f'/api/subnets/{lab}', json={'name': 'Renamed', 'reserved_ranges': ''})
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Renamed'
    assert client.get(f'/api/subnets/{lab}').get_json()['summary']['free'] == 9

    # Shrinking the CIDR so the gateway falls outside is rejected
    bad = client.put(f'/api/subnets/{lab}', json={'cidr': '10.0.0.8/29'})
    assert bad.status_code == 400

    assert client.delete(f'/api/subnets/{lab}').status_code == 204
    assert client.get('/api/subnets').get_json() == []


def test_large_subnet_skips_listing(client):
    client.post('/api/subnets', json={'cidr': '10.10.0.0/16'})
    sid = client.get('/api/subnets').get_json()[0]['id']
    data = client.get(f'/api/subnets/{sid}').get_json()
    assert data['addresses'] is None
    assert data['summary']['free'] == 65534


def test_ipv6_subnet_with_large_reservation(client):
    resp = client.post('/api/subnets', json={
        'cidr': 'fd00:1::/64', 'reserved_ranges': 'fd00:1::/80'})
    assert resp.status_code == 201
    data = client.get(f"/api/subnets/{resp.get_json()['id']}").get_json()
    assert data['addresses'] is None
    assert data['summary']['free'] == 2 ** 64 - 1 - 2 ** 48 + 1
