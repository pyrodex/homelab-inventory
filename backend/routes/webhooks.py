"""
Webhook management routes.
"""
import secrets
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from models import WEBHOOK_EVENTS, Webhook, WebhookDelivery, db
from services.webhooks import dispatcher
from validators import sanitize_string

webhooks_bp = Blueprint('webhooks', __name__)


def register_webhook_routes(app, limiter):
    app.register_blueprint(webhooks_bp, url_prefix='/api')
    limiter.limit("30 per minute")(create_webhook)
    limiter.limit("30 per minute")(update_webhook)
    limiter.limit("10 per minute")(test_webhook)


def _validate(data, partial=False):
    """Return (clean, errors). `secret` semantics: absent = keep, ''/None = clear."""
    clean, errors = {}, {}

    if 'name' in data or not partial:
        name = sanitize_string(data.get('name') or '')
        if not name or len(name) > 100:
            errors['name'] = ['Name is required (max 100 characters)']
        clean['name'] = name

    if 'url' in data or not partial:
        url = (data.get('url') or '').strip()
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            errors['url'] = ['Must be an http:// or https:// URL']
        elif len(url) > 2048:
            errors['url'] = ['URL is too long']
        elif parsed.username or parsed.password:
            errors['url'] = ['Put credentials in a secret, not in the URL']
        clean['url'] = url

    if 'events' in data or not partial:
        # Missing means "everything"; an explicit empty list is a mistake, not "all"
        events = data['events'] if 'events' in data else ['*']
        if isinstance(events, str):
            events = [e.strip() for e in events.split(',') if e.strip()]
        if not isinstance(events, list) or not events:
            errors['events'] = ['Pick at least one event']
        else:
            unknown = [e for e in events if e != '*' and e not in WEBHOOK_EVENTS]
            if unknown:
                errors['events'] = [f"Unknown event(s): {', '.join(unknown)}"]
            clean['events'] = '*' if '*' in events else ','.join(sorted(set(events)))

    if 'enabled' in data:
        clean['enabled'] = bool(data.get('enabled'))

    generated = None
    if data.get('generate_secret'):
        generated = secrets.token_urlsafe(32)
        clean['secret'] = generated
    elif 'secret' in data:
        secret = data.get('secret')
        if secret in (None, ''):
            clean['secret'] = None
        elif not isinstance(secret, str) or len(secret) > 255:
            errors['secret'] = ['Secret must be a string of at most 255 characters']
        else:
            clean['secret'] = secret
    return clean, errors, generated


def _response(hook, generated=None, status=200):
    body = hook.to_dict()
    if generated:
        body['secret'] = generated  # shown once, at creation/rotation
    return jsonify(body), status


@webhooks_bp.route('/webhooks', methods=['GET'])
def list_webhooks():
    return jsonify({
        'events': list(WEBHOOK_EVENTS),
        'webhooks': [h.to_dict() for h in Webhook.query.order_by(Webhook.name).all()],
    })


@webhooks_bp.route('/webhooks', methods=['POST'])
def create_webhook():
    clean, errors, generated = _validate(request.get_json(silent=True) or {})
    if errors:
        return jsonify({'error': 'Validation error', 'details': errors}), 400
    hook = Webhook(**clean)
    db.session.add(hook)
    db.session.commit()
    return _response(hook, generated, 201)


@webhooks_bp.route('/webhooks/<int:hook_id>', methods=['PUT'])
def update_webhook(hook_id):
    hook = db.session.get(Webhook, hook_id)
    if not hook:
        return jsonify({'error': 'Webhook not found'}), 404
    clean, errors, generated = _validate(request.get_json(silent=True) or {}, partial=True)
    if errors:
        return jsonify({'error': 'Validation error', 'details': errors}), 400
    for key, value in clean.items():
        setattr(hook, key, value)
    db.session.commit()
    return _response(hook, generated)


@webhooks_bp.route('/webhooks/<int:hook_id>', methods=['DELETE'])
def delete_webhook(hook_id):
    hook = db.session.get(Webhook, hook_id)
    if not hook:
        return jsonify({'error': 'Webhook not found'}), 404
    WebhookDelivery.query.filter_by(webhook_id=hook.id).delete(synchronize_session=False)
    db.session.delete(hook)
    db.session.commit()
    return '', 204


@webhooks_bp.route('/webhooks/<int:hook_id>/test', methods=['POST'])
def test_webhook(hook_id):
    """Send a `ping` event right now and return the result."""
    hook = db.session.get(Webhook, hook_id)
    if not hook:
        return jsonify({'error': 'Webhook not found'}), 404
    result = dispatcher.send_test(hook)
    return jsonify({k: v for k, v in result.items() if k != 'retryable'})


@webhooks_bp.route('/webhooks/<int:hook_id>/deliveries', methods=['GET'])
def list_deliveries(hook_id):
    hook = db.session.get(Webhook, hook_id)
    if not hook:
        return jsonify({'error': 'Webhook not found'}), 404
    rows = hook.deliveries.order_by(WebhookDelivery.id.desc()).limit(50).all()
    return jsonify([r.to_dict() for r in rows])
