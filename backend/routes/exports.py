"""
Export routes: Ansible dynamic inventory and NetBox CSV bulk import.
"""
from flask import Blueprint, Response, jsonify, request, send_file
import io
import os
from sqlalchemy.orm import selectinload

from models import Device, Subnet
from services.exports import (
    NETBOX_FILES,
    ansible_inventory_yaml,
    build_ansible_inventory,
    build_netbox_tables,
    netbox_csv,
    netbox_zip,
)
from utils.tags import apply_tag_filter, tag_filter_values

exports_bp = Blueprint('exports', __name__)


def register_export_routes(app, limiter):
    app.register_blueprint(exports_bp, url_prefix='/api/export')
    limiter.limit("60 per minute")(ansible_inventory)
    limiter.limit("20 per minute")(netbox_export)


def _truthy(value):
    return str(value).lower() in ('1', 'true', 'yes', 'on')


def _devices(args):
    query = Device.query.options(
        selectinload(Device.monitors),
        selectinload(Device.tags),
        selectinload(Device.outgoing_links),
    )
    query = apply_tag_filter(query, Device, tag_filter_values(args))
    if args.get('monitoring_enabled') is not None:
        query = query.filter(Device.monitoring_enabled == _truthy(args.get('monitoring_enabled')))
    return query.all()


@exports_bp.route('/ansible', methods=['GET'])
def ansible_inventory():
    """
    Ansible dynamic inventory.
      (default)       --list JSON: {"_meta": {"hostvars": ...}, "<group>": {"hosts": [...]}}
      ?host=<name>    --host JSON: that host's vars ({} if unknown, as Ansible expects)
      ?format=yaml    static YAML inventory (download)
    Filters: ?tag=a&tag=b (all must match), ?monitoring_enabled=true,
             ?include_all_types=true to include URL / DNS record entries.
    """
    try:
        devices = _devices(request.args)
    except ValueError as exc:
        return jsonify({'error': 'Validation error', 'details': {'tag': [str(exc)]}}), 400
    inventory = build_ansible_inventory(
        devices, Subnet.query.all(),
        include_non_hosts=_truthy(request.args.get('include_all_types', 'false')),
        all_devices=Device.query.all(),
    )
    host = request.args.get('host')
    if host is not None:
        return jsonify(inventory['_meta']['hostvars'].get(host, {}))
    if request.args.get('format') == 'yaml':
        body = ansible_inventory_yaml(inventory)
        if _truthy(request.args.get('download', 'true')):
            return Response(body, mimetype='text/yaml',
                            headers={'Content-Disposition': 'attachment; filename=homelab_inventory.yml'})
        return Response(body, mimetype='text/yaml')
    return jsonify(inventory)


@exports_bp.route('/ansible/script', methods=['GET'])
def ansible_inventory_script():
    """The standalone dynamic-inventory script (stdlib only) for `-i`."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts', 'ansible_inventory.py')
    with open(path, 'r', encoding='utf-8') as fh:
        body = fh.read()
    return Response(body, mimetype='text/x-python',
                    headers={'Content-Disposition': 'attachment; filename=homelab_inventory.py'})


@exports_bp.route('/netbox', methods=['GET'])
def netbox_export():
    """
    NetBox bulk-import CSVs.
      (default)          ZIP of ordered CSVs + README.txt
      ?file=<key>        one CSV, e.g. ?file=devices (keys: tags, sites, manufacturers,
                         device_roles, device_types, devices, virtual_machines, vlans,
                         prefixes, ip_addresses)
      ?summary=true      JSON row counts per file (for the UI)
      ?default_site=X    site for devices without a location (default "Homelab")
    """
    default_site = (request.args.get('default_site') or 'Homelab').strip()[:100] or 'Homelab'
    try:
        devices = _devices(request.args)
    except ValueError as exc:
        return jsonify({'error': 'Validation error', 'details': {'tag': [str(exc)]}}), 400
    tables = build_netbox_tables(devices, Subnet.query.all(), default_site=default_site,
                                 all_devices=Device.query.all())

    if _truthy(request.args.get('summary', 'false')):
        return jsonify([
            {'key': key, 'filename': filename, 'where': where, 'rows': len(tables[key])}
            for key, filename, where in NETBOX_FILES
        ])

    key = request.args.get('file')
    if key:
        names = {k: f for k, f, _w in NETBOX_FILES}
        if key not in names:
            return jsonify({'error': f"Unknown file '{key}'", 'files': list(names)}), 400
        return Response(netbox_csv(key, tables[key]), mimetype='text/csv',
                        headers={'Content-Disposition': f'attachment; filename={names[key]}'})

    return send_file(io.BytesIO(netbox_zip(tables)), mimetype='application/zip',
                     as_attachment=True, download_name='netbox_import.zip')
