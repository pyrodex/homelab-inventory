"""
Tests for outgoing webhooks, against a real HTTP receiver on localhost
"""
import hashlib
import hmac
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from models import db, Device, IpObservation, Subnet, Webhook, WebhookDelivery
from services import netprobe, ipam_scan, webhooks as webhooks_service


class Receiver:
    """Records POSTs. Path controls the response: /ok, /fail (500), /bad (400), /redirect (302)."""

    def __init__(self):
        self.requests = []
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                receiver.requests.append({'path': self.path, 'headers': dict(self.headers), 'body': body})
                code = {'/fail': 500, '/bad': 400, '/redirect': 302}.get(self.path, 200)
                self.send_response(code)
                if code == 302:
                    self.send_header('Location', '/ok')
                self.end_headers()
                self.wfile.write(b'nope' if code >= 400 else b'ok')

        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def events(self, path=None):
        return [json.loads(r['body']) for r in self.requests if path is None or r['path'] == path]

    def close(self):
        self.server.shutdown()


@pytest.fixture
def app(monkeypatch):
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    monkeypatch.setattr(webhooks_service.dispatcher, 'synchronous', True)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def receiver():
    r = Receiver()
    yield r
    r.close()


def _hook(client, url, **extra):
    resp = client.post('/api/webhooks', json={'name': 'HA', 'url': url, **extra})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def _device(client, name='nas', **extra):
    body = {'name': name, 'device_type': 'linux_server_physical', 'ip_address': '10.0.0.10',
            'deviceFunction': 'NAS', **extra}
    resp = client.post('/api/devices', json=body)
    assert resp.status_code == 201
    return resp.get_json()['data']


def test_validation(client):
    bad = [
        {'name': '', 'url': 'http://x.lan/hook'},
        {'name': 'a', 'url': 'ftp://x.lan/hook'},
        {'name': 'a', 'url': 'not a url'},
        {'name': 'a', 'url': 'http://user:pw@x.lan/hook'},
        {'name': 'a', 'url': 'http://x.lan/hook', 'events': ['device.exploded']},
        {'name': 'a', 'url': 'http://x.lan/hook', 'events': []},
    ]
    for body in bad:
        assert client.post('/api/webhooks', json=body).status_code == 400, body
    listing = client.get('/api/webhooks').get_json()
    assert 'device.created' in listing['events'] and listing['webhooks'] == []


def test_device_lifecycle_events_signed(client, receiver):
    hook = _hook(client, f'{receiver.url}/ok', generate_secret=True)
    secret = hook['secret']
    assert hook['has_secret'] and len(secret) >= 32
    assert 'secret' not in client.get('/api/webhooks').get_json()['webhooks'][0]  # never listed

    dev = _device(client, tags=['prod'])
    client.put(f"/api/devices/{dev['id']}", json={'deviceFunction': 'Backup NAS'})
    client.delete(f"/api/devices/{dev['id']}")

    events = receiver.events()
    assert [e['event'] for e in events] == ['device.created', 'device.updated', 'device.deleted']
    created, updated, deleted = events
    assert created['device']['name'] == 'nas' and created['device']['tags'] == ['prod']
    assert updated['changes'] == {'deviceFunction': {'old': 'NAS', 'new': 'Backup NAS'}}
    assert deleted['device']['id'] == dev['id'] and deleted['device']['name'] == 'nas'
    assert all(e['source'] == 'homelab-inventory' and e['id'] for e in events)

    for req in receiver.requests:
        expected = 'sha256=' + hmac.new(secret.encode(), req['body'], hashlib.sha256).hexdigest()
        assert req['headers']['X-Hub-Signature-256'] == expected
        assert req['headers']['Content-Type'] == 'application/json'
        assert req['headers']['X-Homelab-Event'] == json.loads(req['body'])['event']


def test_no_event_for_rolled_back_or_failed_change(client, receiver):
    _hook(client, f'{receiver.url}/ok')
    resp = client.post('/api/devices', json={'name': 'x', 'device_type': 'nope'})
    assert resp.status_code == 400
    assert receiver.requests == []


def test_event_filter_and_disable(client, receiver):
    hook = _hook(client, f'{receiver.url}/ok', events=['device.deleted'])
    dev = _device(client)
    assert receiver.requests == []
    client.delete(f"/api/devices/{dev['id']}")
    assert [e['event'] for e in receiver.events()] == ['device.deleted']

    client.put(f"/api/webhooks/{hook['id']}", json={'enabled': False})
    _device(client, 'b')
    assert len(receiver.requests) == 1


def test_relationship_bulk_and_tag_rename_events(client, receiver):
    _hook(client, f'{receiver.url}/ok', events=['device.relationship_changed', 'device.created', 'device.updated'])
    host = _device(client, 'pve01', tags=['proxmox'])
    vm = _device(client, 'vm', ip_address='10.0.0.20')
    client.post(f"/api/devices/{vm['id']}/links", json={'target_id': host['id'], 'link_type': 'runs_on'})
    client.post('/api/bulk/devices/import', json=[
        {'name': 'b1', 'device_type': 'icmp_only', 'ip_address': '10.0.0.30', 'deviceFunction': 'x'}])
    tag_id = client.get('/api/tags').get_json()['data'][0]['id']
    client.put(f'/api/tags/{tag_id}', json={'name': 'pve'})
    events = receiver.events()
    kinds = [e['event'] for e in events]
    assert kinds == ['device.created', 'device.created', 'device.relationship_changed',
                     'device.created', 'device.updated']
    assert events[2]['change_type'] == 'link_add' and events[3]['change_type'] == 'bulk_import'
    assert events[4]['changes']['tags'] == {'old': ['proxmox'], 'new': ['pve']}


def test_retries_on_5xx_but_not_4xx_or_redirect(client, app, receiver):
    fail = _hook(client, f'{receiver.url}/fail')
    _device(client)
    assert len(receiver.events('/fail')) == 3  # 3 attempts
    with app.app_context():
        rows = WebhookDelivery.query.filter_by(webhook_id=fail['id']).order_by(WebhookDelivery.id).all()
        assert [r.attempt for r in rows] == [1, 2, 3]
        assert all(r.status_code == 500 and not r.success for r in rows)
        assert len({r.delivery_id for r in rows}) == 1  # same delivery id across retries

    client.put(f"/api/webhooks/{fail['id']}", json={'enabled': False})
    bad = _hook(client, f'{receiver.url}/bad')
    redirect = _hook(client, f'{receiver.url}/redirect')
    _device(client, 'second', ip_address='10.0.0.11')
    assert len(receiver.events('/bad')) == 1
    assert len(receiver.events('/redirect')) == 1 and receiver.events('/ok') == []  # not followed
    deliveries = client.get(f"/api/webhooks/{redirect['id']}/deliveries").get_json()
    assert 'redirect not followed' in deliveries[0]['error']
    assert client.get('/api/webhooks').get_json()['webhooks'][0]['last_delivery'] is not None
    assert bad['id']


def test_unreachable_receiver_is_recorded(client):
    hook = _hook(client, 'http://127.0.0.1:9/hook')  # discard port: connection refused
    result = client.post(f"/api/webhooks/{hook['id']}/test").get_json()
    assert result['success'] is False and 'Connection failed' in result['error']


def test_test_endpoint_and_secret_rotation(client, receiver):
    hook = _hook(client, f'{receiver.url}/ok', secret='s1')
    result = client.post(f"/api/webhooks/{hook['id']}/test").get_json()
    assert result['success'] is True and result['status_code'] == 200
    ping = receiver.events()[0]
    assert ping['event'] == 'ping'
    rotated = client.put(f"/api/webhooks/{hook['id']}", json={'generate_secret': True}).get_json()
    assert rotated['secret'] != 's1'
    cleared = client.put(f"/api/webhooks/{hook['id']}", json={'secret': ''}).get_json()
    assert cleared['has_secret'] is False
    client.post(f"/api/webhooks/{hook['id']}/test")
    assert 'X-Hub-Signature-256' not in receiver.requests[-1]['headers']


def test_delivery_log_is_trimmed(client, app, receiver, monkeypatch):
    monkeypatch.setattr(webhooks_service, 'KEEP_DELIVERIES', 3)
    hook = _hook(client, f'{receiver.url}/ok')
    for _ in range(5):
        client.post(f"/api/webhooks/{hook['id']}/test")
    assert len(client.get(f"/api/webhooks/{hook['id']}/deliveries").get_json()) == 3
    assert client.delete(f"/api/webhooks/{hook['id']}").status_code == 204
    with app.app_context():
        assert WebhookDelivery.query.count() == 0


def test_ipam_address_discovered(client, app, receiver, monkeypatch):
    _hook(client, f'{receiver.url}/ok', events=['ipam.address_discovered'])
    _device(client)  # 10.0.0.10 is inventoried
    with app.app_context():
        s = Subnet(cidr='10.0.0.0/28', name='LAN')
        db.session.add(s)
        db.session.commit()
        sid = s.id
    monkeypatch.setattr(netprobe, 'ping', lambda t, timeout=1.0: (t in ('10.0.0.10', '10.0.0.5'), 0.2, None))
    monkeypatch.setattr(netprobe, 'reverse_dns', lambda ip: None)
    monkeypatch.setattr(netprobe, 'reverse_lookup', lambda ip: (None, 'none'))
    with app.app_context():
        ipam_scan.scan_subnet(sid)
        ipam_scan.scan_subnet(sid)  # second sweep: nothing new
    events = receiver.events()
    assert [e['address']['ip'] for e in events] == ['10.0.0.5']
    assert events[0]['discovered_by'] == 'ping_sweep' and events[0]['subnet']['cidr'] == '10.0.0.0/28'

    client.post('/api/ipam/dhcp/leases', data='0 aa:bb:cc:dd:ee:ff 10.0.0.7 phone *\n0 aa:bb:cc:dd:ee:01 10.0.0.5 x *\n',
                content_type='text/plain')
    events = receiver.events()
    assert [e['address']['ip'] for e in events] == ['10.0.0.5', '10.0.0.7']  # .5 already known
    assert events[1]['discovered_by'] == 'dhcp' and events[1]['address']['hostname'] == 'phone'


def test_listener_registered_once(app):
    from services.webhooks import dispatcher
    dispatcher.init_app(app)  # second init must not double-register
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    from services.webhooks import _collect_history
    assert event.contains(Session, 'after_flush', _collect_history)


def test_async_mode_delivers_in_background(client, app, receiver, monkeypatch):
    monkeypatch.setattr(webhooks_service.dispatcher, 'synchronous', False)
    _hook(client, f'{receiver.url}/ok')
    _device(client)
    import time
    for _ in range(100):
        if receiver.requests:
            break
        time.sleep(0.02)
    assert [e['event'] for e in receiver.events()] == ['device.created']
