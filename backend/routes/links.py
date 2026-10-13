"""
Device relationship (link) and tag routes.

A link reads "source depends on target":
  vm-01  --runs_on-->      pve01
  pve01  --connected_to--> core-sw   (port Et12)
  pve01  --powered_by-->   ups       (outlet 3)

Impact analysis walks links backwards: everything that (transitively)
depends on a device is affected when it goes down.
"""
import logging
from collections import deque

from flask import Blueprint, jsonify, request

from models import LINK_TYPES, Device, DeviceHistory, DeviceLink, Tag, db
from utils.response import not_found_response, success_response, validation_error_response
from utils.tags import normalize_tag
from validators import sanitize_string

links_bp = Blueprint('links', __name__)

MAX_IMPACT_NODES = 2000


def register_link_routes(app, limiter):
    app.register_blueprint(links_bp, url_prefix='/api')
    limiter.limit("60 per minute")(create_link)
    limiter.limit("60 per minute")(update_link)
    limiter.limit("60 per minute")(delete_link)
    limiter.limit("30 per minute")(rename_tag)
    limiter.limit("30 per minute")(delete_tag)


def _link_label(link_type, target_name, port):
    text = f"{link_type.replace('_', ' ')} {target_name}"
    return f"{text} (port {port})" if port else text


def _record(device_id, change_type, summary, old, new):
    db.session.add(DeviceHistory(
        device_id=device_id,
        change_type=change_type,
        summary=summary,
        diff={'link': {'old': old, 'new': new}},
    ))


def _clean_optional(value, max_len):
    if value is None:
        return None
    value = sanitize_string(str(value))
    if not value:
        return None
    if len(value) > max_len:
        raise ValueError(f"must be at most {max_len} characters")
    return value


def _would_cycle(source_id, target_id, link_type):
    """True if target already (transitively) depends on source via link_type."""
    seen, queue = set(), deque([target_id])
    while queue:
        current = queue.popleft()
        if current == source_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        for (next_id,) in db.session.query(DeviceLink.target_id).filter_by(source_id=current, link_type=link_type):
            queue.append(next_id)
    return False


# --- Links ------------------------------------------------------------------

@links_bp.route('/devices/<int:device_id>/links', methods=['GET'])
def get_device_links(device_id):
    device = db.session.get(Device, device_id)
    if not device:
        return not_found_response("Device", device_id)
    return success_response({
        'outgoing': [l.to_dict() for l in device.outgoing_links],
        'incoming': [l.to_dict() for l in device.incoming_links],
    })


@links_bp.route('/devices/<int:device_id>/links', methods=['POST'])
def create_link(device_id):
    device = db.session.get(Device, device_id)
    if not device:
        return not_found_response("Device", device_id)
    data = request.get_json(silent=True) or {}

    errors = {}
    link_type = data.get('link_type')
    if link_type not in LINK_TYPES:
        errors['link_type'] = [f"Must be one of: {', '.join(LINK_TYPES)}"]
    try:
        target_id = int(data.get('target_id'))
    except (TypeError, ValueError):
        target_id = None
        errors['target_id'] = ['Target device is required']
    target = db.session.get(Device, target_id) if target_id else None
    if target_id and not target:
        errors['target_id'] = ['Target device not found']
    elif target_id == device_id:
        errors['target_id'] = ['A device cannot depend on itself']
    try:
        port = _clean_optional(data.get('port'), 50)
    except ValueError as exc:
        errors['port'] = [str(exc)]
    try:
        notes = _clean_optional(data.get('notes'), 255)
    except ValueError as exc:
        errors['notes'] = [str(exc)]
    if errors:
        return validation_error_response(errors)

    if DeviceLink.query.filter_by(source_id=device_id, target_id=target_id, link_type=link_type).first():
        return jsonify({'error': f"{device.name} already {link_type.replace('_', ' ')} {target.name}"}), 409
    if link_type == 'runs_on' and DeviceLink.query.filter_by(source_id=device_id, link_type='runs_on').first():
        return validation_error_response({'link_type': [f"{device.name} already runs on another host; remove that first"]})
    if link_type in ('runs_on', 'powered_by') and _would_cycle(device_id, target_id, link_type):
        return validation_error_response({'target_id': [f"{target.name} already depends on {device.name}; that would be a loop"]})

    link = DeviceLink(source_id=device_id, target_id=target_id, link_type=link_type, port=port, notes=notes)
    try:
        db.session.add(link)
        _record(device_id, 'link_add', f"Linked '{device.name}': {_link_label(link_type, target.name, port)}",
                None, _link_label(link_type, target.name, port))
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logging.error(f"Failed to create link: {exc}")
        return jsonify({'error': 'Failed to create link'}), 500
    return success_response(link.to_dict(), "Link created", 201)


@links_bp.route('/links/<int:link_id>', methods=['PUT'])
def update_link(link_id):
    link = db.session.get(DeviceLink, link_id)
    if not link:
        return not_found_response("Link", link_id)
    data = request.get_json(silent=True) or {}
    errors = {}
    before = _link_label(link.link_type, link.target.name, link.port)
    for field, max_len in (('port', 50), ('notes', 255)):
        if field in data:
            try:
                setattr(link, field, _clean_optional(data.get(field), max_len))
            except ValueError as exc:
                errors[field] = [str(exc)]
    if errors:
        db.session.rollback()
        return validation_error_response(errors)
    after = _link_label(link.link_type, link.target.name, link.port)
    if after != before:
        _record(link.source_id, 'link_update', f"Updated link on '{link.source.name}'", before, after)
    db.session.commit()
    return success_response(link.to_dict(), "Link updated")


@links_bp.route('/links/<int:link_id>', methods=['DELETE'])
def delete_link(link_id):
    link = db.session.get(DeviceLink, link_id)
    if not link:
        return not_found_response("Link", link_id)
    label = _link_label(link.link_type, link.target.name, link.port)
    _record(link.source_id, 'link_remove', f"Unlinked '{link.source.name}': {label}", label, None)
    db.session.delete(link)
    db.session.commit()
    return success_response(None, "Link removed")


@links_bp.route('/devices/<int:device_id>/impact', methods=['GET'])
def get_impact(device_id):
    """
    Everything that transitively depends on this device.
    ?types=runs_on,powered_by limits which link types are followed.
    """
    device = db.session.get(Device, device_id)
    if not device:
        return not_found_response("Device", device_id)
    types = [t for t in (request.args.get('types') or '').split(',') if t] or list(LINK_TYPES)
    bad = [t for t in types if t not in LINK_TYPES]
    if bad:
        return validation_error_response({'types': [f"Unknown link type(s): {', '.join(bad)}"]})

    affected = {}
    queue = deque([(device_id, 0, [])])
    seen = {device_id}
    truncated = False
    while queue:
        current, depth, path = queue.popleft()
        rows = (DeviceLink.query
                .filter(DeviceLink.target_id == current, DeviceLink.link_type.in_(types))
                .all())
        for link in rows:
            dep = link.source
            if dep.id in seen:
                continue
            if len(affected) >= MAX_IMPACT_NODES:
                truncated = True
                break
            seen.add(dep.id)
            step = {'from': link.target.name, 'from_id': link.target_id, 'link_type': link.link_type, 'port': link.port}
            affected[dep.id] = {
                'device_id': dep.id,
                'name': dep.name,
                'device_type': dep.device_type,
                'ip_address': dep.ip_address,
                'monitoring_enabled': dep.monitoring_enabled,
                'depth': depth + 1,
                'via': path + [step],
            }
            queue.append((dep.id, depth + 1, path + [step]))

    items = sorted(affected.values(), key=lambda d: (d['depth'], d['name'].lower()))
    return success_response({
        'device_id': device.id,
        'name': device.name,
        'types': types,
        'count': len(items),
        'direct': sum(1 for d in items if d['depth'] == 1),
        'truncated': truncated,
        'affected': items,
    })


# --- Tags -------------------------------------------------------------------

@links_bp.route('/tags', methods=['GET'])
def get_tags():
    tags = Tag.query.order_by(Tag.name).all()
    return success_response([t.to_dict() for t in tags])


@links_bp.route('/tags/<int:tag_id>', methods=['PUT'])
def rename_tag(tag_id):
    """Rename a tag; renaming onto an existing tag merges the two."""
    tag = db.session.get(Tag, tag_id)
    if not tag:
        return not_found_response("Tag", tag_id)
    data = request.get_json(silent=True) or {}
    try:
        new_name = normalize_tag(data.get('name') or '')
    except ValueError as exc:
        return validation_error_response({'name': [str(exc)]})
    if new_name == tag.name:
        return success_response(tag.to_dict())

    old_name = tag.name
    existing = Tag.query.filter_by(name=new_name).first()
    affected = list(tag.devices)
    before = {d.id: sorted(t.name for t in d.tags) for d in affected}
    if existing:
        for device in affected:
            if existing not in device.tags:
                device.tags.append(existing)
            device.tags.remove(tag)
        db.session.delete(tag)
        result = existing
    else:
        tag.name = new_name
        result = tag
    db.session.flush()
    for device in affected:
        after = sorted(t.name for t in device.tags)
        db.session.add(DeviceHistory(
            device_id=device.id, change_type='update',
            summary=f"Tag '{old_name}' renamed to '{new_name}'",
            diff={'tags': {'old': before[device.id], 'new': after}},
        ))
    db.session.commit()
    return success_response(result.to_dict(), "Tag renamed" if not existing else "Tags merged")


@links_bp.route('/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    tag = db.session.get(Tag, tag_id)
    if not tag:
        return not_found_response("Tag", tag_id)
    for device in list(tag.devices):
        before = sorted(t.name for t in device.tags)
        device.tags.remove(tag)
        db.session.add(DeviceHistory(
            device_id=device.id, change_type='update',
            summary=f"Tag '{tag.name}' deleted",
            diff={'tags': {'old': before, 'new': [n for n in before if n != tag.name] or None}},
        ))
    db.session.delete(tag)
    db.session.commit()
    return success_response(None, "Tag deleted")
