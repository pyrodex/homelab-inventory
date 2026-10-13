"""
Tests for reverse DNS (PTR) in IPAM sweeps and analysis
"""
import socket

import pytest

from models import db, Device, IpObservation, Subnet
from services import ipam_scan, netprobe, webhooks as webhooks_service


@pytest.fixture
def app(monkeypatch):
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    for var in ('IPAM_SWEEP_PTR', 'IPAM_PTR_BLOCKS_FREE', 'IPAM_STALE_AFTER_HOURS'):
        monkeypatch.delenv(var, raising=False)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def lan(app):
    """10.0.0.0/28: nas (.10) inventoried; .1 gateway."""
    with app.app_context():
        db.session.add(Device(name='nas', device_type='linux_server_physical', ip_address='10.0.0.10'))
        s = Subnet(cidr='10.0.0.0/28', name='LAN', gateway='10.0.0.1')
        db.session.add(s)
        db.session.commit()
        return s.id


def network(monkeypatch, alive, ptr, errors=()):
    """Fake ping + PTR: `alive` answer pings, `ptr` maps ip -> name, `errors` resolver failures."""
    monkeypatch.setattr(netprobe, 'ping', lambda t, timeout=1.0: (t in alive, 0.3 if t in alive else None, None))

    def lookup(ip):
        if ip in errors:
            return None, netprobe.PTR_ERROR
        return (ptr[ip], netprobe.PTR_FOUND) if ip in ptr else (None, netprobe.PTR_NONE)
    monkeypatch.setattr(netprobe, 'reverse_lookup', lookup)


# --- reverse_lookup classification -----------------------------------------

@pytest.mark.parametrize('outcome,expected', [
    (('found', 'host.lan'), ('host.lan', 'found')),
    (socket.herror(1, 'Unknown host'), (None, 'none')),   # HOST_NOT_FOUND
    (socket.herror(4, 'No address'), (None, 'none')),     # NO_DATA
    (socket.herror(2, 'Try again'), (None, 'error')),     # TRY_AGAIN
    (socket.gaierror(-3, 'Temporary failure'), (None, 'error')),
    (OSError('network down'), (None, 'error')),
])
def test_reverse_lookup_classifies_outcomes(monkeypatch, outcome, expected):
    def fake(ip):
        if isinstance(outcome, Exception):
            raise outcome
        return (outcome[1], [], [ip])
    monkeypatch.setattr(socket, 'gethostbyaddr', fake)
    assert netprobe.reverse_lookup('10.0.0.5') == expected


def test_sweep_resolve_modes(monkeypatch):
    looked = []
    monkeypatch.setattr(netprobe, 'ping', lambda t, timeout=1.0: (t == '10.0.0.2', 0.1, None))
    monkeypatch.setattr(netprobe, 'reverse_lookup', lambda ip: (looked.append(ip), (None, 'none'))[1])
    ips = ['10.0.0.1', '10.0.0.2', '10.0.0.3']
    netprobe.sweep(ips, resolve='alive')
    assert looked == ['10.0.0.2']
    looked.clear()
    netprobe.sweep(ips, resolve='all')
    assert sorted(looked) == ips
    looked.clear()
    res = netprobe.sweep(ips, resolve='none')
    assert looked == [] and res['10.0.0.2']['ptr_status'] is None


# --- sweeps record PTR ------------------------------------------------------

def test_sweep_records_ptr_for_every_address(app, lan, monkeypatch):
    network(monkeypatch, alive={'10.0.0.1', '10.0.0.10', '10.0.0.5'},
            ptr={'10.0.0.5': 'printer.lan', '10.0.0.7': 'old-server.lan', '10.0.0.1': 'gw.lan'})
    with app.app_context():
        result = ipam_scan.scan_subnet(lan)
        assert result['alive'] == 3 and result['ptr_found'] == 3
        rows = {o.ip: o for o in IpObservation.query.all()}
        # DNS-only address gets a row; silent address without PTR does not
        assert rows['10.0.0.7'].ptr_hostname == 'old-server.lan' and rows['10.0.0.7'].ping_reachable is False
        assert '10.0.0.8' not in rows
        assert rows['10.0.0.5'].ptr_hostname == 'printer.lan' and rows['10.0.0.5'].ping_hostname == 'printer.lan'
        # inventoried host answered but has no PTR: checked, empty
        assert rows['10.0.0.10'].ptr_checked_at is not None and rows['10.0.0.10'].ptr_hostname is None


def test_ptr_removed_clears_but_resolver_error_keeps(app, lan, monkeypatch):
    network(monkeypatch, alive=set(), ptr={'10.0.0.7': 'old.lan', '10.0.0.8': 'keep.lan'})
    with app.app_context():
        ipam_scan.scan_subnet(lan)
    # .7's record deleted from DNS; resolver errors out for .8
    network(monkeypatch, alive=set(), ptr={}, errors={'10.0.0.8'})
    with app.app_context():
        ipam_scan.scan_subnet(lan)
        rows = {o.ip: o for o in IpObservation.query.all()}
        assert rows['10.0.0.7'].ptr_hostname is None
        assert rows['10.0.0.8'].ptr_hostname == 'keep.lan'


def test_sweep_ptr_can_be_disabled(app, lan, monkeypatch):
    monkeypatch.setenv('IPAM_SWEEP_PTR', 'false')
    network(monkeypatch, alive={'10.0.0.5'}, ptr={'10.0.0.5': 'printer.lan', '10.0.0.7': 'old.lan'})
    with app.app_context():
        ipam_scan.scan_subnet(lan)
        assert {o.ip for o in IpObservation.query.all()} == {'10.0.0.5'}  # no DNS-only rows


# --- IPAM analysis ----------------------------------------------------------

def test_dns_only_status_and_blocking(client, app, lan, monkeypatch):
    network(monkeypatch, alive={'10.0.0.1', '10.0.0.5', '10.0.0.10'},
            ptr={'10.0.0.2': 'old-server.lan', '10.0.0.5': 'printer.lan', '10.0.0.10': 'nas.lan', '10.0.0.1': 'gw.lan'})
    with app.app_context():
        ipam_scan.scan_subnet(lan)

    data = client.get(f'/api/subnets/{lan}').get_json()
    by_ip = {a['ip']: a for a in data['addresses']}
    assert by_ip['10.0.0.2']['status'] == 'dns' and by_ip['10.0.0.2']['ptr'] == 'old-server.lan'
    assert by_ip['10.0.0.5']['status'] == 'seen' and by_ip['10.0.0.5']['ptr'] == 'printer.lan'
    assert by_ip['10.0.0.10']['status'] == 'monitored' and by_ip['10.0.0.10']['ptr'] == 'nas.lan'
    assert by_ip['10.0.0.1']['status'] == 'gateway' and by_ip['10.0.0.1']['ptr'] == 'gw.lan'
    assert 'ptr' not in by_ip['10.0.0.3']

    s = data['summary']
    assert (s['dns_only'], s['unknown_active'], s['with_ptr']) == (1, 1, 4)
    assert s['ptr_blocks_free'] is True
    assert s['free'] == 14 - 1 - 1 - 1 - 1  # usable - gateway - nas - seen(.5) - dns(.2)
    assert client.get(f'/api/subnets/{lan}/next-free').get_json()['addresses'] == ['10.0.0.3']

    nas = next(u for u in data['used_addresses'] if u['ip'] == '10.0.0.10')
    assert nas['ptr'] == 'nas.lan' and nas['ptr_checked'] is True
    unknown = {u['ip']: u for u in data['unknown_addresses']}
    assert unknown['10.0.0.2']['status'] == 'dns' and unknown['10.0.0.2']['hostname'] == 'old-server.lan'


def test_inventory_device_without_ptr_is_reported(client, app, lan, monkeypatch):
    # nas is down *and* has no PTR: still reported as checked, with no record
    network(monkeypatch, alive=set(), ptr={})
    with app.app_context():
        ipam_scan.scan_subnet(lan)
    nas = next(u for u in client.get(f'/api/subnets/{lan}').get_json()['used_addresses'] if u['ip'] == '10.0.0.10')
    assert nas['ptr'] is None and nas['ptr_checked'] is True


def test_dns_only_can_be_allowed_as_free(client, app, lan, monkeypatch):
    monkeypatch.setenv('IPAM_PTR_BLOCKS_FREE', 'false')
    network(monkeypatch, alive=set(), ptr={'10.0.0.2': 'old.lan'})
    with app.app_context():
        ipam_scan.scan_subnet(lan)
    data = client.get(f'/api/subnets/{lan}').get_json()
    assert {a['ip']: a['status'] for a in data['addresses']}['10.0.0.2'] == 'dns'  # still flagged
    assert data['summary']['ptr_blocks_free'] is False
    assert client.get(f'/api/subnets/{lan}/next-free').get_json()['addresses'] == ['10.0.0.2']


def test_webhook_only_when_dns_only_address_comes_alive(client, app, lan, monkeypatch):
    monkeypatch.setattr(webhooks_service.dispatcher, 'synchronous', True)
    emitted = []
    monkeypatch.setattr(webhooks_service.dispatcher, 'emit', lambda name, data, occurred_at=None: emitted.append(
        (name, data['address']['ip'])))
    network(monkeypatch, alive=set(), ptr={'10.0.0.2': 'old.lan'})
    with app.app_context():
        ipam_scan.scan_subnet(lan)
    assert emitted == []  # a PTR record alone isn't "discovered on the network"
    network(monkeypatch, alive={'10.0.0.2'}, ptr={'10.0.0.2': 'old.lan'})
    with app.app_context():
        ipam_scan.scan_subnet(lan)
        ipam_scan.scan_subnet(lan)  # already known: no repeat
    assert emitted == [('ipam.address_discovered', '10.0.0.2')]
