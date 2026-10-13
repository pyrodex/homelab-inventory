"""
Tests for IPAM ping sweeps, dnsmasq lease import, and observation-aware IPAM
"""
import io
import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from models import db, Device, IpObservation, Subnet
from services import dhcp_leases, ipam_scan, netprobe

NOW = int(time.time())

LEASES_V4 = f"""{NOW + 3600} aa:bb:cc:dd:ee:01 10.0.0.50 laptop 01:aa:bb:cc:dd:ee:01
{NOW + 3600} AA-BB-CC-DD-EE-02 10.0.0.51 * *
0 aa:bb:cc:dd:ee:03 10.0.0.52 printer *
{NOW - 60} aa:bb:cc:dd:ee:04 10.0.0.53 old-phone *
garbage line
{NOW + 3600} not-a-mac 10.0.0.54 x *
"""

LEASES_V6 = f"""duid 00:01:00:01:2c:aa:bb:cc:00:11:22:33:44:55
{NOW + 3600} 12345678 fd00::50 nas6 00:01:00:01:aa
"""


@pytest.fixture
def app(monkeypatch):
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    monkeypatch.delenv('IPAM_LEASES_TOKEN', raising=False)
    monkeypatch.delenv('IPAM_SCAN_MAX_HOSTS', raising=False)
    monkeypatch.delenv('IPAM_STALE_AFTER_HOURS', raising=False)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def subnet(app):
    with app.app_context():
        db.session.add(Device(name='nas', device_type='linux_server_physical', ip_address='10.0.0.10'))
        s = Subnet(cidr='10.0.0.0/26', name='LAN', gateway='10.0.0.1')
        db.session.add(s)
        db.session.commit()
        return s.id


def fake_ping(alive):
    def _ping(target, timeout=1.0):
        return (True, 0.4, None) if target in alive else (False, None, 'No response')
    return _ping


# --- netprobe ---------------------------------------------------------------

def test_ping_command_units_per_platform():
    assert netprobe.build_ping_command('h', 1.0, 'Linux') == ['ping', '-c', '1', '-W', '1', 'h']
    assert netprobe.build_ping_command('h', 1.5, 'Linux')[4] == '2'  # whole seconds, rounded up
    assert netprobe.build_ping_command('h', 1.0, 'Darwin') == ['ping', '-c', '1', '-W', '1000', 'h']
    assert netprobe.build_ping_command('h', 1.0, 'FreeBSD')[4] == '1000'
    assert netprobe.build_ping_command('h', 1.0, 'Windows') == ['ping', '-n', '1', '-w', '1000', 'h']


def test_sweep_concurrent_and_resolves_only_alive(monkeypatch):
    monkeypatch.setattr(netprobe, 'ping', fake_ping({'10.0.0.2'}))
    looked_up = []
    monkeypatch.setattr(netprobe, 'reverse_dns', lambda ip: looked_up.append(ip) or 'host.lan')
    res = netprobe.sweep(['10.0.0.1', '10.0.0.2', '10.0.0.3'])
    assert res['10.0.0.2'] == {'reachable': True, 'rtt_ms': 0.4, 'hostname': 'host.lan', 'error': None}
    assert res['10.0.0.1']['reachable'] is False
    assert looked_up == ['10.0.0.2']


def test_discovery_endpoint_keeps_order(client, monkeypatch):
    monkeypatch.setattr(netprobe, 'ping', fake_ping({'192.168.9.3'}))
    monkeypatch.setattr(netprobe, 'reverse_dns', lambda ip: None)
    data = client.post('/api/discovery', json={'cidr': '192.168.9.0/29'}).get_json()['data']
    assert [r['ip'] for r in data['results']] == [f'192.168.9.{i}' for i in range(1, 7)]
    assert data['summary']['reachable'] == 1


# --- dnsmasq parsing / import ----------------------------------------------

def test_parse_dnsmasq_v4_and_v6():
    parsed = dhcp_leases.parse_dnsmasq_leases(LEASES_V4 + LEASES_V6)
    by_ip = {l['ip']: l for l in parsed['leases']}
    assert set(by_ip) == {'10.0.0.50', '10.0.0.51', '10.0.0.52', '10.0.0.53', 'fd00::50'}
    assert by_ip['10.0.0.50']['hostname'] == 'laptop' and by_ip['10.0.0.50']['mac'] == 'aa:bb:cc:dd:ee:01'
    assert by_ip['10.0.0.51']['hostname'] is None and by_ip['10.0.0.51']['mac'] == 'aa:bb:cc:dd:ee:02'
    assert by_ip['10.0.0.52']['expires'] is None  # infinite
    assert by_ip['fd00::50']['mac'] is None and by_ip['fd00::50']['hostname'] == 'nas6'
    assert [n for n, _ in parsed['skipped']] == [5, 6]


def test_import_snapshot_per_source(app):
    with app.app_context():
        r = dhcp_leases.import_leases(LEASES_V4, source='file:/a')
        assert (r['leases'], r['active'], r['expired'], r['released']) == (4, 3, 1, 0)
        dhcp_leases.import_leases(LEASES_V6, source='file:/b')
        # second snapshot from /a drops .51 -> released; /b untouched
        r2 = dhcp_leases.import_leases(LEASES_V4.replace(' 10.0.0.51 ', ' 10.0.0.60 '), source='file:/a')
        assert r2['released'] == 1
        active = {o.ip for o in IpObservation.query.filter_by(dhcp_active=True)}
        assert active == {'10.0.0.50', '10.0.0.52', '10.0.0.60', 'fd00::50'}


def test_expire_leases(app):
    with app.app_context():
        dhcp_leases.import_leases(LEASES_V4, source='s')
        later = datetime.now(timezone.utc) + timedelta(hours=2)
        assert dhcp_leases.expire_leases(now=later) == 2  # .50 and .51; .52 is infinite
        assert {o.ip for o in IpObservation.query.filter_by(dhcp_active=True)} == {'10.0.0.52'}


def test_upload_endpoint_raw_multipart_token_size(client, monkeypatch):
    resp = client.post('/api/ipam/dhcp/leases?source=pihole', data=LEASES_V4, content_type='text/plain')
    assert resp.status_code == 200 and resp.get_json()['source'] == 'upload:pihole'
    resp = client.post('/api/ipam/dhcp/leases', data={'file': (io.BytesIO(LEASES_V6.encode()), 'l')},
                       content_type='multipart/form-data')
    assert resp.get_json()['leases'] == 1
    assert client.post('/api/ipam/dhcp/leases', data=b'').status_code == 400
    # exactly what `curl --data-binary @file` sends
    curl_like = client.post('/api/ipam/dhcp/leases?source=curl', data=LEASES_V4.encode(),
                            content_type='application/x-www-form-urlencoded')
    assert curl_like.status_code == 200 and curl_like.get_json()['active'] == 3

    monkeypatch.setenv('IPAM_LEASES_TOKEN', 'tok')
    assert client.post('/api/ipam/dhcp/leases', data=LEASES_V4).status_code == 401
    ok = client.post('/api/ipam/dhcp/leases', data=LEASES_V4, headers={'Authorization': 'Bearer tok'})
    assert ok.status_code == 200
    monkeypatch.delenv('IPAM_LEASES_TOKEN')

    big = b'0 aa:bb:cc:dd:ee:ff 10.0.0.1 x *\n' * 80000
    assert client.post('/api/ipam/dhcp/leases', data=big).status_code == 413

    # the later default-source uploads reported the same IPs, so they own them now
    status = client.get('/api/ipam/dhcp/status').get_json()
    assert status['active_by_source'] == {'upload:upload': 3}  # last V4 snapshot released the V6 lease


def test_lease_ownership_moves_between_sources(app):
    with app.app_context():
        line = f"{NOW + 3600} aa:bb:cc:dd:ee:01 10.0.0.50 laptop *\n"
        dhcp_leases.import_leases(line, source='a')
        dhcp_leases.import_leases(line, source='b')       # b now owns .50
        assert dhcp_leases.import_leases('', source='a')['released'] == 0
        assert IpObservation.query.filter_by(ip='10.0.0.50').one().dhcp_active
        assert dhcp_leases.import_leases('', source='b')['released'] == 1


def test_lease_file_watcher(app, tmp_path, monkeypatch):
    path = tmp_path / 'dnsmasq.leases'
    path.write_text(LEASES_V4)
    monkeypatch.setenv('DNSMASQ_LEASES_PATH', f'{path},{tmp_path / "missing.leases"}')
    watcher = dhcp_leases.LeaseFileWatcher(app)
    watcher.poll_once()
    assert watcher.last_results[str(path)]['active'] == 3
    assert 'error' in watcher.last_results[str(tmp_path / 'missing.leases')]
    watcher.last_results[str(path)] = 'unchanged'
    watcher.poll_once()  # same mtime -> no re-import
    assert watcher.last_results[str(path)] == 'unchanged'
    path.write_text(LEASES_V4.splitlines()[0] + '\n')
    os.utime(path, (time.time() + 5, time.time() + 5))
    watcher.poll_once()
    assert watcher.last_results[str(path)]['released'] == 2


# --- sweeps -----------------------------------------------------------------

def test_scan_eligibility(monkeypatch):
    assert ipam_scan.scan_eligibility('10.0.0.0/24') is None
    assert 'IPv4-only' in ipam_scan.scan_eligibility('fd00::/64')
    assert 'limited to 1024' in ipam_scan.scan_eligibility('10.0.0.0/21')
    monkeypatch.setenv('IPAM_SCAN_MAX_HOSTS', '4096')
    assert ipam_scan.scan_eligibility('10.0.0.0/21') is None


def test_scan_subnet_records_observations(app, subnet, monkeypatch):
    monkeypatch.setattr(netprobe, 'ping', fake_ping({'10.0.0.1', '10.0.0.10', '10.0.0.33'}))
    monkeypatch.setattr(netprobe, 'reverse_dns', lambda ip: 'mystery.lan' if ip == '10.0.0.33' else None)
    with app.app_context():
        result = ipam_scan.scan_subnet(subnet)
        assert result['status'] == 'ok' and result['scanned'] == 62 and result['alive'] == 3
        s = db.session.get(Subnet, subnet)
        assert s.last_scan_alive == 3 and s.last_scan_at and s.last_scan_error is None
        assert IpObservation.query.count() == 3  # silent addresses don't get rows
        obs = IpObservation.query.filter_by(ip='10.0.0.33').one()
        assert obs.ping_reachable and obs.ping_hostname == 'mystery.lan'

    # a second sweep where .33 is gone keeps last_seen but marks it unreachable
    monkeypatch.setattr(netprobe, 'ping', fake_ping(set()))
    with app.app_context():
        ipam_scan.scan_subnet(subnet)
        obs = IpObservation.query.filter_by(ip='10.0.0.33').one()
        assert obs.ping_reachable is False and obs.ping_last_seen is not None


def test_scan_rejects_ineligible(app):
    with app.app_context():
        s = Subnet(cidr='fd00:1::/64')
        db.session.add(s)
        db.session.commit()
        assert ipam_scan.scan_subnet(s.id)['status'] == 'ineligible'
        assert 'IPv4-only' in db.session.get(Subnet, s.id).last_scan_error


def test_due_subnets(app, subnet):
    with app.app_context():
        s = db.session.get(Subnet, subnet)
        assert ipam_scan.due_subnet_ids() == []  # scanning off
        s.scan_enabled, s.scan_interval_minutes = True, 30
        db.session.commit()
        assert ipam_scan.due_subnet_ids() == [subnet]  # never scanned
        s.last_scan_at = datetime.utcnow() - timedelta(minutes=10)
        db.session.commit()
        assert ipam_scan.due_subnet_ids() == []
        assert ipam_scan.due_subnet_ids(now=datetime.utcnow() + timedelta(minutes=25)) == [subnet]


# --- IPAM integration -------------------------------------------------------

def test_observations_block_free_addresses(client, app, subnet, monkeypatch):
    monkeypatch.setattr(netprobe, 'ping', fake_ping({'10.0.0.1', '10.0.0.2', '10.0.0.10'}))
    monkeypatch.setattr(netprobe, 'reverse_dns', lambda ip: None)
    with app.app_context():
        ipam_scan.scan_subnet(subnet)
    client.post('/api/ipam/dhcp/leases', data=f"{NOW + 3600} aa:bb:cc:dd:ee:09 10.0.0.3 phone *\n")

    data = client.get(f'/api/subnets/{subnet}').get_json()
    statuses = {a['ip']: a['status'] for a in data['addresses']}
    assert statuses['10.0.0.1'] == 'gateway'       # answering gateway is expected
    assert statuses['10.0.0.2'] == 'seen'
    assert statuses['10.0.0.3'] == 'dhcp'
    assert statuses['10.0.0.10'] == 'monitored'
    s = data['summary']
    assert (s['unknown_active'], s['seen'], s['dhcp']) == (2, 1, 1)
    assert s['free'] == 62 - 1 - 1 - 2  # usable - gateway - nas - unknown
    assert {u['ip'] for u in data['unknown_addresses']} == {'10.0.0.2', '10.0.0.3'}
    nas = next(u for u in data['used_addresses'] if u['ip'] == '10.0.0.10')
    assert nas['observed']['seen'] is True
    assert client.get(f'/api/subnets/{subnet}/next-free').get_json()['addresses'] == ['10.0.0.4']


def test_stale_observations_free_up(client, app, subnet, monkeypatch):
    with app.app_context():
        db.session.add(IpObservation(ip='10.0.0.2', ping_reachable=False,
                                     ping_last_seen=datetime.utcnow() - timedelta(hours=100)))
        db.session.commit()
    assert client.get(f'/api/subnets/{subnet}').get_json()['summary']['unknown_active'] == 0
    monkeypatch.setenv('IPAM_STALE_AFTER_HOURS', '200')
    assert client.get(f'/api/subnets/{subnet}').get_json()['summary']['unknown_active'] == 1


def test_scan_api_and_settings(client, app, subnet, monkeypatch):
    monkeypatch.setattr(netprobe, 'ping', fake_ping({'10.0.0.5'}))
    monkeypatch.setattr(netprobe, 'reverse_dns', lambda ip: None)
    resp = client.put(f'/api/subnets/{subnet}', json={'scan_enabled': True, 'scan_interval_minutes': 15})
    assert resp.status_code == 200 and resp.get_json()['scan_interval_minutes'] == 15
    assert client.put(f'/api/subnets/{subnet}', json={'scan_interval_minutes': 1}).status_code == 400

    assert client.post(f'/api/subnets/{subnet}/scan').status_code == 202
    assert client.get(f'/api/subnets/{subnet}/scan').get_json()['running'] is True
    for _ in range(100):
        if not client.get(f'/api/subnets/{subnet}/scan').get_json()['running']:
            break
        time.sleep(0.05)
    # The fixture's app context makes test requests share one session; drop its
    # cached rows so we read what the scan thread committed.
    db.session.expire_all()
    status = client.get(f'/api/subnets/{subnet}/scan').get_json()
    assert status['last_scan_alive'] == 1 and status['last_scan_at'].endswith('Z')

    # enabling sweeps on an ineligible subnet is refused
    big = client.post('/api/subnets', json={'cidr': '10.8.0.0/16', 'scan_enabled': True})
    assert big.status_code == 400 and 'scan_enabled' in big.get_json()['details']
    v6 = client.post('/api/subnets', json={'cidr': 'fd00:9::/64'}).get_json()
    assert client.post(f"/api/subnets/{v6['id']}/scan").status_code == 400
