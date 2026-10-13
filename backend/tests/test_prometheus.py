"""
Tests for Prometheus HTTP SD, scrape-config generation, and live status
"""
import pytest
import yaml

from models import db, Device, Monitor
from services import prometheus_status


@pytest.fixture
def app(monkeypatch):
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['RATELIMIT_ENABLED'] = False
    monkeypatch.delenv('PROMETHEUS_URL', raising=False)
    monkeypatch.delenv('PROMETHEUS_SD_TOKEN', raising=False)
    prometheus_status.clear_cache()
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def devices(app):
    with app.app_context():
        nas = Device(name='nas', device_type='linux_server_physical', ip_address='10.0.0.2')
        sw = Device(name='core-sw', device_type='network_switch', ip_address='10.0.0.3')
        cam = Device(name='cam', device_type='ip_camera', ip_address='10.0.0.4')
        off = Device(name='old', device_type='icmp_only', ip_address='10.0.0.9', monitoring_enabled=False)
        noip = Device(name='noip', device_type='icmp_only', ip_address=None)
        db.session.add_all([nas, sw, cam, off, noip])
        db.session.flush()
        db.session.add_all([
            Monitor(device_id=nas.id, monitor_type='node_exporter'),
            Monitor(device_id=nas.id, monitor_type='icmp'),
            Monitor(device_id=sw.id, monitor_type='snmp'),
            Monitor(device_id=cam.id, monitor_type='icmp'),
            Monitor(device_id=cam.id, monitor_type='http', enabled=False),
            Monitor(device_id=off.id, monitor_type='icmp'),
            Monitor(device_id=noip.id, monitor_type='icmp'),
        ])
        db.session.commit()
        return {'nas': nas.id, 'sw': sw.id, 'cam': cam.id, 'off': off.id, 'noip': noip.id}


def _series(metric_name, value, **labels):
    return {'metric': {'__name__': metric_name, **labels}, 'value': [1700000000, str(value)]}


# --- HTTP SD ----------------------------------------------------------------

def test_sd_lists_enabled_targets(client, devices):
    data = client.get('/api/prometheus/sd').get_json()
    targets = sorted(t['targets'][0] for t in data)
    # disabled device, disabled monitor and device without IP are excluded
    assert targets == ['10.0.0.2', '10.0.0.2:9100', '10.0.0.3:161', '10.0.0.4']
    nas_node = next(t for t in data if t['targets'] == ['10.0.0.2:9100'])
    assert nas_node['labels']['inventory_group'] == 'linux_node_exporter'
    assert nas_node['labels']['inventory_device_id'] == str(devices['nas'])


def test_sd_group_filter(client, devices):
    data = client.get('/api/prometheus/sd?group=icmp').get_json()
    assert sorted(t['targets'][0] for t in data) == ['10.0.0.2', '10.0.0.4']
    assert client.get('/api/prometheus/sd?group=nope').get_json() == []


def test_sd_token(client, devices, monkeypatch):
    monkeypatch.setenv('PROMETHEUS_SD_TOKEN', 's3cret')
    assert client.get('/api/prometheus/sd').status_code == 401
    assert client.get('/api/prometheus/sd', headers={'Authorization': 'Bearer nope'}).status_code == 401
    ok = client.get('/api/prometheus/sd', headers={'Authorization': 'Bearer s3cret'})
    assert ok.status_code == 200 and len(ok.get_json()) == 4


def test_sd_groups(client, devices):
    data = client.get('/api/prometheus/sd/groups').get_json()
    assert data == [
        {'group': 'icmp', 'targets': 2},
        {'group': 'linux_node_exporter', 'targets': 1},
        {'group': 'snmp', 'targets': 1},
    ]


def test_scrape_config_is_valid_yaml(client, devices, monkeypatch):
    monkeypatch.setenv('PROMETHEUS_SD_TOKEN', 's3cret')
    resp = client.get('/api/prometheus/sd/scrape-config?base_url=http://inv.lan:5000&blackbox=bb:9115')
    jobs = {j['job_name']: j for j in yaml.safe_load(resp.get_data(as_text=True))}
    assert set(jobs) == {'inventory_icmp', 'inventory_linux_node_exporter', 'inventory_snmp'}
    icmp = jobs['inventory_icmp']
    assert icmp['metrics_path'] == '/probe'
    assert icmp['params'] == {'module': ['icmp']}
    sd = icmp['http_sd_configs'][0]
    assert sd['url'] == 'http://inv.lan:5000/api/prometheus/sd?group=icmp'
    assert sd['authorization'] == {'credentials': '<PROMETHEUS_SD_TOKEN>'}
    assert icmp['relabel_configs'][-1]['replacement'] == 'bb:9115'
    assert 'relabel_configs' not in jobs['inventory_linux_node_exporter']


def test_scrape_config_all_groups(client):
    body = client.get('/api/prometheus/sd/scrape-config?all=true').get_data(as_text=True)
    assert len(yaml.safe_load(body)) == 12


def test_file_export_skips_devices_without_ip(client, devices, tmp_path, monkeypatch):
    monkeypatch.setenv('PROMETHEUS_EXPORT_PATH', str(tmp_path))
    resp = client.get('/api/prometheus/export?mode=write')
    assert resp.status_code == 200
    assert resp.get_json()['files_created'] == 4


# --- Live status ------------------------------------------------------------

def test_status_disabled_when_unconfigured(client, devices):
    data = client.get('/api/prometheus/status').get_json()
    assert data == {'enabled': False, 'error': None, 'summary': None, 'devices': {}}


def test_status_matching(client, devices, monkeypatch):
    monkeypatch.setenv('PROMETHEUS_URL', 'http://prom:9090')
    ids = devices

    def fake_query(expr, settings):
        if expr == 'up':
            return [
                # matched by inventory_device_id + monitor_type
                _series('up', 1, inventory_device_id=str(ids['nas']), monitor_type='node_exporter',
                        instance='10.0.0.2:9100', job='node'),
                # blackbox exporter itself is up, but probe_success below must win
                _series('up', 1, instance='10.0.0.4', job='blackbox'),
                # matched only by instance (hand-written job, no inventory labels)
                _series('up', 0, instance='10.0.0.3:161', job='snmp'),
            ]
        return [
            _series('probe_success', 1, device_name='nas', monitor_type='icmp', instance='10.0.0.2'),
            _series('probe_success', 0, instance='10.0.0.4', job='blackbox'),
        ]

    monkeypatch.setattr(prometheus_status, '_query', fake_query)
    data = client.get('/api/prometheus/status').get_json()
    assert data['enabled'] is True and data['error'] is None
    d = data['devices']
    assert d[str(ids['nas'])]['state'] == 'up'
    assert d[str(ids['sw'])]['state'] == 'down'
    assert d[str(ids['cam'])]['state'] == 'down'
    cam_icmp = d[str(ids['cam'])]['monitors'][0]
    assert cam_icmp['metric'] == 'probe_success'
    assert d[str(ids['off'])]['state'] == 'disabled'
    assert d[str(ids['noip'])]['state'] == 'unknown'
    assert data['summary'] == {'up': 1, 'down': 2, 'degraded': 0, 'unknown': 1, 'disabled': 1}


def test_status_degraded_and_unknown(client, devices, monkeypatch):
    monkeypatch.setenv('PROMETHEUS_URL', 'http://prom:9090')

    def fake_query(expr, settings):
        if expr == 'up':
            return [_series('up', 1, instance='10.0.0.2:9100')]
        return [_series('probe_success', 0, instance='10.0.0.2')]

    monkeypatch.setattr(prometheus_status, '_query', fake_query)
    d = client.get('/api/prometheus/status').get_json()['devices']
    assert d[str(devices['nas'])]['state'] == 'degraded'
    assert d[str(devices['sw'])]['state'] == 'unknown'


def test_status_reports_errors_and_caches(client, devices, monkeypatch):
    monkeypatch.setenv('PROMETHEUS_URL', 'http://prom:9090')
    calls = {'n': 0}

    def boom(expr, settings):
        calls['n'] += 1
        raise RuntimeError('nope')

    monkeypatch.setattr(prometheus_status, '_query', boom)
    first = client.get('/api/prometheus/status').get_json()
    assert first['enabled'] is True and 'nope' in first['error']
    client.get('/api/prometheus/status')
    assert calls['n'] == 1  # second call served from cache
    client.get('/api/prometheus/status?refresh=true')
    assert calls['n'] == 2


def test_query_sends_auth(monkeypatch):
    captured = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"status":"success","data":{"result":[]}}'

    def fake_urlopen(req, timeout, context):
        captured['auth'] = req.get_header('Authorization')
        captured['url'] = req.full_url
        return FakeResp()

    monkeypatch.setattr(prometheus_status, 'urlopen', fake_urlopen)
    settings = {'url': 'http://p:9090', 'bearer_token': 'tok', 'username': None, 'password': None,
                'verify_tls': True, 'timeout': 1}
    assert prometheus_status._query('up', settings) == []
    assert captured['auth'] == 'Bearer tok'
    assert captured['url'] == 'http://p:9090/api/v1/query?query=up'


def test_sd_payload_matches_prometheus_spec(client, devices):
    """HTTP SD requires string label values and valid label names."""
    import re
    name_re = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    for group in client.get('/api/prometheus/sd').get_json():
        assert set(group) == {'targets', 'labels'}
        assert all(isinstance(t, str) and t for t in group['targets'])
        for key, value in group['labels'].items():
            assert name_re.match(key) and not key.startswith('__'), key
            assert isinstance(value, str)
