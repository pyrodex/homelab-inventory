"""
Tests for device tags and relationships (links / impact analysis)
"""
import io

import pytest

from models import db, Device, DeviceHistory, DeviceLink, Tag


@pytest.fixture
def app():
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


def _device(client, name, **extra):
    body = {'name': name, 'device_type': 'linux_server_virtual', 'ip_address': extra.pop('ip', '10.0.0.1'),
            'deviceFunction': 'test', **extra}
    resp = client.post('/api/devices', json=body)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()['data']


def _link(client, source, target, link_type, **extra):
    return client.post(f'/api/devices/{source}/links', json={'target_id': target, 'link_type': link_type, **extra})


@pytest.fixture
def lab(client):
    """
    ups <-powered_by- core-sw <-connected_to- pve01 <-runs_on- vm-a
                                                ^-runs_on- vm-b
    pve01 -powered_by-> ups
    """
    ids = {n: _device(client, n)['id'] for n in ['ups', 'core-sw', 'pve01', 'vm-a', 'vm-b', 'loner']}
    assert _link(client, ids['core-sw'], ids['ups'], 'powered_by', port='outlet 1').status_code == 201
    assert _link(client, ids['pve01'], ids['core-sw'], 'connected_to', port='Et12').status_code == 201
    assert _link(client, ids['pve01'], ids['ups'], 'powered_by').status_code == 201
    assert _link(client, ids['vm-a'], ids['pve01'], 'runs_on').status_code == 201
    assert _link(client, ids['vm-b'], ids['pve01'], 'runs_on').status_code == 201
    return ids


# --- Tags -------------------------------------------------------------------

def test_tags_normalized_on_create_and_update(client):
    dev = _device(client, 'nas', tags=['Storage', ' prod ', 'storage', 'Home Lab'])
    assert dev['tags'] == ['home-lab', 'prod', 'storage']
    resp = client.put(f"/api/devices/{dev['id']}", json={'tags': 'prod; backup'})
    assert resp.get_json()['data']['tags'] == ['backup', 'prod']
    # Updates without a tags key leave tags alone
    resp = client.put(f"/api/devices/{dev['id']}", json={'deviceFunction': 'NAS'})
    assert resp.get_json()['data']['tags'] == ['backup', 'prod']


def test_invalid_tags_rejected(client):
    resp = client.post('/api/devices', json={'name': 'x', 'device_type': 'icmp_only', 'ip_address': '10.0.0.9',
                                             'deviceFunction': 'f', 'tags': ['ok', 'bad/tag']})
    assert resp.status_code == 400
    assert 'tags' in resp.get_json()['details']


def test_tag_history_recorded(client, app):
    dev = _device(client, 'nas', tags=['prod'])
    client.put(f"/api/devices/{dev['id']}", json={'tags': ['prod', 'storage']})
    with app.app_context():
        entries = DeviceHistory.query.filter_by(device_id=dev['id']).order_by(DeviceHistory.id).all()
        assert entries[0].diff['tags'] == {'old': None, 'new': ['prod']}
        assert entries[1].diff == {'tags': {'old': ['prod'], 'new': ['prod', 'storage']}}


def test_no_tags_does_not_create_noise_in_history(client, app):
    dev = _device(client, 'plain')
    client.put(f"/api/devices/{dev['id']}", json={'tags': []})
    with app.app_context():
        entries = DeviceHistory.query.filter_by(device_id=dev['id']).all()
        assert len(entries) == 1 and 'tags' not in entries[0].diff


def test_filter_devices_by_tags(client):
    _device(client, 'a', tags=['prod', 'storage'])
    _device(client, 'b', tags=['prod'])
    _device(client, 'c')
    names = lambda r: sorted(d['name'] for d in r.get_json()['data'])
    assert names(client.get('/api/devices?tag=prod')) == ['a', 'b']
    assert names(client.get('/api/devices?tag=prod&tag=storage')) == ['a']
    assert names(client.get('/api/devices?tag=prod,storage')) == ['a']
    search = client.get('/api/search/devices?tag=storage').get_json()
    assert [d['name'] for d in search['results']] == ['a']
    # free-text search matches tags too
    assert [d['name'] for d in client.get('/api/search/devices?q=stor').get_json()['results']] == ['a']


def test_tag_list_rename_merge_delete(client, app):
    a = _device(client, 'a', tags=['prd', 'storage'])
    b = _device(client, 'b', tags=['prod'])
    tags = {t['name']: t for t in client.get('/api/tags').get_json()['data']}
    assert tags['prd']['device_count'] == 1

    # rename onto an existing tag merges
    resp = client.put(f"/api/tags/{tags['prd']['id']}", json={'name': 'PROD'})
    assert resp.status_code == 200
    assert client.get(f"/api/devices/{a['id']}").get_json()['data']['tags'] == ['prod', 'storage']
    names = [t['name'] for t in client.get('/api/tags').get_json()['data']]
    assert names == ['prod', 'storage']

    # plain rename
    client.put(f"/api/tags/{tags['storage']['id']}", json={'name': 'nas'})
    assert client.get(f"/api/devices/{a['id']}").get_json()['data']['tags'] == ['nas', 'prod']

    # delete strips it from devices
    prod_id = next(t['id'] for t in client.get('/api/tags').get_json()['data'] if t['name'] == 'prod')
    assert client.delete(f'/api/tags/{prod_id}').status_code == 200
    assert client.get(f"/api/devices/{b['id']}").get_json()['data']['tags'] == []


def test_bulk_csv_and_json_tags(client):
    csv_body = ('name,device_type,ip_address,deviceFunction,tags\n'
                'csv1,icmp_only,10.1.0.1,ping,"prod,edge"\n')
    resp = client.post('/api/bulk/devices/import', data={'file': (io.BytesIO(csv_body.encode()), 'd.csv')},
                       content_type='multipart/form-data')
    assert resp.status_code == 201, resp.get_json()
    resp = client.post('/api/bulk/devices/import', json=[
        {'name': 'json1', 'device_type': 'icmp_only', 'ip_address': '10.1.0.2', 'deviceFunction': 'x', 'tags': ['edge']},
        'not-an-object',
    ])
    assert resp.get_json()['created'] == 1 and resp.get_json()['failed'] == 1
    assert sorted(d['name'] for d in client.get('/api/devices?tag=edge').get_json()['data']) == ['csv1', 'json1']
    export = client.get('/api/bulk/devices/export?format=csv').get_data(as_text=True)
    assert 'tags' in export.splitlines()[0] and '"edge,prod"' in export


# --- Links ------------------------------------------------------------------

def test_link_validation(client, lab):
    ids = lab
    assert _link(client, ids['loner'], ids['loner'], 'runs_on').status_code == 400
    assert _link(client, ids['loner'], 99999, 'runs_on').status_code == 400
    assert _link(client, ids['loner'], ids['pve01'], 'bogus').status_code == 400
    assert _link(client, ids['loner'], ids['pve01'], 'runs_on', port='x' * 51).status_code == 400
    # duplicate
    assert _link(client, ids['vm-a'], ids['pve01'], 'runs_on').status_code == 409
    # only one host
    resp = _link(client, ids['vm-a'], ids['loner'], 'runs_on')
    assert resp.status_code == 400 and 'already runs on' in str(resp.get_json())
    # runs_on loop: pve01 -> vm-a would make vm-a -> pve01 -> vm-a
    resp = _link(client, ids['pve01'], ids['vm-a'], 'runs_on')
    assert resp.status_code == 400 and 'loop' in str(resp.get_json())
    # connected_to in both directions is allowed (switch uplinks)
    assert _link(client, ids['core-sw'], ids['pve01'], 'connected_to').status_code == 201


def test_device_links_payload(client, lab):
    data = client.get(f"/api/devices/{lab['pve01']}/links").get_json()['data']
    assert sorted((l['link_type'], l['target_name']) for l in data['outgoing']) == [
        ('connected_to', 'core-sw'), ('powered_by', 'ups')]
    assert sorted(l['source_name'] for l in data['incoming']) == ['vm-a', 'vm-b']
    dev = client.get(f"/api/devices/{lab['pve01']}").get_json()['data']
    assert {l['target_name'] for l in dev['links']} == {'core-sw', 'ups'}


def test_impact_analysis(client, lab):
    data = client.get(f"/api/devices/{lab['ups']}/impact").get_json()['data']
    by_name = {d['name']: d for d in data['affected']}
    assert set(by_name) == {'core-sw', 'pve01', 'vm-a', 'vm-b'}
    assert data['direct'] == 2 and data['count'] == 4
    assert by_name['core-sw']['depth'] == 1 and by_name['pve01']['depth'] == 1
    assert by_name['vm-a']['depth'] == 2
    assert [s['link_type'] for s in by_name['vm-a']['via']] == ['powered_by', 'runs_on']
    assert by_name['vm-a']['via'][-1]['from_id'] == lab['pve01']

    only_net = client.get(f"/api/devices/{lab['core-sw']}/impact?types=connected_to").get_json()['data']
    assert [d['name'] for d in only_net['affected']] == ['pve01']
    assert client.get(f"/api/devices/{lab['ups']}/impact?types=nope").status_code == 400
    assert client.get(f"/api/devices/{lab['loner']}/impact").get_json()['data']['count'] == 0


def test_impact_handles_cycles(client, lab):
    # connected_to loop between switch and host must not hang
    _link(client, lab['core-sw'], lab['pve01'], 'connected_to')
    data = client.get(f"/api/devices/{lab['pve01']}/impact").get_json()['data']
    assert {d['name'] for d in data['affected']} == {'core-sw', 'vm-a', 'vm-b'}


def test_link_update_delete_and_history(client, app, lab):
    link_id = client.get(f"/api/devices/{lab['pve01']}/links").get_json()['data']['outgoing'][0]['id']
    resp = client.put(f'/api/links/{link_id}', json={'port': 'Et13', 'notes': 'moved'})
    assert resp.get_json()['data']['port'] == 'Et13'
    assert client.delete(f'/api/links/{link_id}').status_code == 200
    with app.app_context():
        types = [h.change_type for h in DeviceHistory.query.filter_by(device_id=lab['pve01']).order_by(DeviceHistory.id)]
        assert types == ['create', 'link_add', 'link_add', 'link_update', 'link_remove']


def test_deleting_device_removes_its_links(client, app, lab):
    assert client.delete(f"/api/devices/{lab['pve01']}").status_code == 200
    with app.app_context():
        assert DeviceLink.query.filter(
            (DeviceLink.source_id == lab['pve01']) | (DeviceLink.target_id == lab['pve01'])).count() == 0
        assert DeviceLink.query.count() == 1  # core-sw -> ups remains


def test_prometheus_labels_include_tags_and_host(client, lab):
    client.put(f"/api/devices/{lab['vm-a']}", json={'tags': ['prod', 'web']})
    client.post(f"/api/devices/{lab['vm-a']}/monitors", json={'monitor_type': 'node_exporter'})
    sd = client.get('/api/prometheus/sd').get_json()
    labels = next(t['labels'] for t in sd if t['labels']['device_name'] == 'vm-a')
    assert labels['tags'] == ',prod,web,'
    assert labels['runs_on'] == 'pve01'
