"""
Outgoing webhooks.

Events come from DeviceHistory: every device change path (API, bulk import /
delete, tag rename, relationship edits) already writes a history row, so a
session listener picks those up after a successful commit. Nothing fires for
rolled-back changes, and no route needs its own hook.

Delivery: JSON POST, 5 s timeout, no redirects, up to 3 attempts with
backoff (immediately, +10 s, +60 s). If the webhook has a secret, the body
is signed GitHub-style:

    X-Hub-Signature-256: sha256=<hex HMAC-SHA256(secret, raw body)>

Deliveries are queued in memory; anything still queued when the process
stops is lost (the delivery log shows what was sent).
"""
import hashlib
import hmac
import json
import logging
import queue
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from sqlalchemy import event as sa_event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

USER_AGENT = 'homelab-inventory-webhooks/1'
TIMEOUT_SECONDS = 5
RETRY_DELAYS = (0, 10, 60)
KEEP_DELIVERIES = 50
MAX_RESPONSE_SNIPPET = 200

CHANGE_TYPE_EVENTS = {
    'create': 'device.created',
    'bulk_import': 'device.created',
    'update': 'device.updated',
    'delete': 'device.deleted',
    'bulk_delete': 'device.deleted',
    'link_add': 'device.relationship_changed',
    'link_update': 'device.relationship_changed',
    'link_remove': 'device.relationship_changed',
}


class _NoRedirect(HTTPRedirectHandler):
    """A webhook URL is where the data goes; don't follow it anywhere else."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


_opener = build_opener(_NoRedirect)


def sign(secret: str, body: bytes) -> str:
    return 'sha256=' + hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()


def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


class WebhookDispatcher:
    def __init__(self):
        self.app = None
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.synchronous = False  # tests: deliver inline, no retries delay

    # --- wiring -------------------------------------------------------------

    def init_app(self, app):
        self.app = app
        import os
        self.synchronous = bool(app.config.get('WEBHOOKS_SYNCHRONOUS')) or \
            os.environ.get('WEBHOOKS_SYNCHRONOUS', '').lower() in ('1', 'true', 'yes')
        app.extensions['webhooks'] = self
        if not sa_event.contains(Session, 'after_flush', _collect_history):
            sa_event.listen(Session, 'after_flush', _collect_history)
            sa_event.listen(Session, 'after_commit', _flush_pending)
            sa_event.listen(Session, 'after_rollback', _drop_pending)

    def _ensure_worker(self):
        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._run, name='webhook-dispatcher', daemon=True)
                self._worker.start()

    # --- producing ----------------------------------------------------------

    def emit(self, event_name: str, data: dict, occurred_at: Optional[str] = None):
        """Queue an event for every enabled webhook that subscribes to it."""
        if self.app is None:
            return
        item = ('event', event_name, data, occurred_at or _now_iso())
        if self.synchronous:
            self._handle(item)
        else:
            self._ensure_worker()
            self._queue.put(item)

    def emit_history(self, snapshots):
        for snap in snapshots:
            event_name = CHANGE_TYPE_EVENTS.get(snap['change_type'])
            if event_name:
                self.emit(event_name, {'history': snap}, snap.get('created_at'))

    # --- consuming ----------------------------------------------------------

    def _run(self):
        while True:
            item = self._queue.get()
            try:
                self._handle(item)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"Webhook dispatch failed: {exc}")

    def _handle(self, item):
        kind = item[0]
        with self.app.app_context():
            from models import Webhook, db
            try:
                if kind == 'event':
                    _, event_name, data, occurred_at = item
                    hooks = [h for h in Webhook.query.filter_by(enabled=True).all() if h.wants(event_name)]
                    if not hooks:
                        return
                    payload = build_payload(event_name, data, occurred_at)
                    for hook in hooks:
                        self._attempt(hook.id, event_name, payload, attempt=1)
                elif kind == 'retry':
                    _, hook_id, event_name, payload, attempt = item
                    self._attempt(hook_id, event_name, payload, attempt)
            finally:
                db.session.remove()

    def _schedule_retry(self, hook_id, event_name, payload, attempt):
        if attempt > len(RETRY_DELAYS):
            return
        delay = 0 if self.synchronous else RETRY_DELAYS[attempt - 1]
        item = ('retry', hook_id, event_name, payload, attempt)
        if self.synchronous:
            self._handle(item)
            return

        def enqueue():
            self._queue.put(item)
        timer = threading.Timer(delay, enqueue)
        timer.daemon = True
        timer.start()

    def _attempt(self, hook_id, event_name, payload, attempt):
        from models import Webhook, WebhookDelivery, db
        hook = db.session.get(Webhook, hook_id)
        if hook is None or not hook.enabled:
            return None
        result = deliver(hook.url, hook.secret, event_name, payload)
        db.session.add(WebhookDelivery(
            webhook_id=hook.id,
            delivery_id=payload['id'],
            event=event_name,
            attempt=attempt,
            status_code=result['status_code'],
            success=result['success'],
            error=result['error'],
            duration_ms=result['duration_ms'],
        ))
        db.session.commit()
        _trim_log(hook.id)
        if not result['success'] and result.get('retryable', True):
            self._schedule_retry(hook.id, event_name, payload, attempt + 1)
        return result

    def send_test(self, hook) -> dict:
        """Synchronous one-shot 'ping' delivery for the UI's Test button."""
        from models import WebhookDelivery, db
        payload = build_payload('ping', {'message': f"Test delivery for webhook '{hook.name}'"}, _now_iso())
        result = deliver(hook.url, hook.secret, 'ping', payload)
        db.session.add(WebhookDelivery(
            webhook_id=hook.id, delivery_id=payload['id'], event='ping', attempt=1,
            status_code=result['status_code'], success=result['success'],
            error=result['error'], duration_ms=result['duration_ms'],
        ))
        db.session.commit()
        _trim_log(hook.id)
        return result


dispatcher = WebhookDispatcher()


# --- payloads / transport -------------------------------------------------

def build_payload(event_name: str, data: dict, occurred_at: str) -> dict:
    from models import Device, db
    payload = {
        'id': str(uuid.uuid4()),
        'event': event_name,
        'occurred_at': occurred_at,
        'source': 'homelab-inventory',
    }
    history = data.get('history')
    if history is not None:
        device = db.session.get(Device, history['device_id']) if history.get('device_id') else None
        if device is not None and event_name != 'device.deleted':
            payload['device'] = device.to_dict()
        else:
            # Deleted (or already gone): rebuild what we knew from the diff
            old = {k: v.get('old') for k, v in (history.get('diff') or {}).items()}
            payload['device'] = {'id': history.get('device_id'), **{k: v for k, v in old.items() if v is not None}}
        payload['changes'] = history.get('diff') or {}
        payload['summary'] = history.get('summary')
        payload['change_type'] = history.get('change_type')
    else:
        payload.update(data)
    return payload


def deliver(url: str, secret: Optional[str], event_name: str, payload: dict) -> dict:
    body = json.dumps(payload, separators=(',', ':'), default=str).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': USER_AGENT,
        'X-Homelab-Event': event_name,
        'X-Homelab-Delivery': payload['id'],
    }
    if secret:
        headers['X-Hub-Signature-256'] = sign(secret, body)
    started = time.monotonic()
    status, error, retryable = None, None, True
    try:
        req = Request(url, data=body, headers=headers, method='POST')
        with _opener.open(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310 - user-configured URL
            status = resp.status
            resp.read(MAX_RESPONSE_SNIPPET)
    except HTTPError as exc:
        status = exc.code
        snippet = exc.read(MAX_RESPONSE_SNIPPET).decode('utf-8', errors='replace') if exc.fp else ''
        error = f"HTTP {exc.code}" + (f": {snippet.strip()}" if snippet.strip() else '')
        # 3xx (redirect refused) and 4xx other than 408/429 won't fix themselves
        retryable = exc.code >= 500 or exc.code in (408, 429)
        if 300 <= exc.code < 400:
            error = f"HTTP {exc.code} redirect not followed"
    except URLError as exc:
        error = f"Connection failed: {exc.reason}"
    except Exception as exc:  # timeouts, bad URLs
        error = f"{type(exc).__name__}: {exc}"
    success = status is not None and 200 <= status < 300
    return {
        'success': success,
        'status_code': status,
        'error': None if success else (error or f"HTTP {status}")[:500],
        'duration_ms': int((time.monotonic() - started) * 1000),
        'retryable': retryable and not success,
    }


def _trim_log(hook_id):
    from models import WebhookDelivery, db
    ids = [row.id for row in WebhookDelivery.query.filter_by(webhook_id=hook_id)
           .order_by(WebhookDelivery.id.desc()).offset(KEEP_DELIVERIES).all()]
    if ids:
        WebhookDelivery.query.filter(WebhookDelivery.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()


# --- session hooks --------------------------------------------------------

def _collect_history(session, flush_context):
    from models import DeviceHistory
    pending = session.info.setdefault('webhook_history', [])
    for obj in session.new:
        if isinstance(obj, DeviceHistory):
            pending.append({
                'device_id': obj.device_id,
                'change_type': obj.change_type,
                'summary': obj.summary,
                'diff': obj.diff,
                'created_at': (obj.created_at.isoformat() + 'Z') if obj.created_at else _now_iso(),
            })


def _flush_pending(session):
    pending = session.info.pop('webhook_history', None)
    if pending:
        dispatcher.emit_history(pending)


def _drop_pending(session):
    session.info.pop('webhook_history', None)


def emit_discovered(new_ips, source):
    """
    Fire ipam.address_discovered for addresses seen for the first time that
    aren't in inventory. Called by sweeps and lease imports after commit.
    """
    if not new_ips or dispatcher.app is None:
        return
    import ipaddress
    from models import Device, IpObservation, Subnet
    from services.ipam import build_address_index
    index = build_address_index(Device.query.all())
    networks = []
    for s in Subnet.query.all():
        try:
            networks.append((s, ipaddress.ip_network(s.cidr, strict=False)))
        except ValueError:
            continue
    for obs in IpObservation.query.filter(IpObservation.ip.in_(list(new_ips))).all():
        ip = ipaddress.ip_address(obs.ip)
        if int(ip) in index.get(ip.version, {}):
            continue
        subnet = next((s for s, n in sorted(networks, key=lambda x: -x[1].prefixlen)
                       if n.version == ip.version and ip in n), None)
        dispatcher.emit('ipam.address_discovered', {
            'address': obs.to_dict(),
            'discovered_by': source,
            'subnet': {'id': subnet.id, 'cidr': subnet.cidr, 'name': subnet.name} if subnet else None,
        })
