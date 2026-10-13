"""
Tests for Ansible inventory and NetBox CSV exports
"""
import csv
import io
import zipfile

import pytest
import yaml

from models import db, Device, DeviceLink, Location, Model, Monitor, Subnet, Tag, Vendor
from services.exports import NETBOX_COLUMNS, NETBOX_FILES


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


@pytest.fixture
def lab(app):
    with app.app_context():
        rack = Location(name='Basement Rack')
        vendor = Vendor(name='Supermicro')
        db.session.add_all([rack, vendor])
        db.session.flush()
        model = Model(name='X11SCL-F', vendor_id=vendor.id)
        prod, web = Tag(name='prod'), Tag(name='web-tier')
        db.session.add_all([model, prod, web])
        db.session.flush()

        pve = Device(name='pve01', device_type='linux_server_physical', ip_address='192.168.1.10',
                     vendor_id=vendor.id, model_id=model.id, location_id=rack.id, serial_number='SN1',
                     networks='LAN,IoT', device_function='Hypervisor')
        pve.tags = [prod]
        vm = Device(name='web 01', device_type='linux_server_virtual', ip_address='192.168.1.50:8080',
                    location_id=rack.id, device_function='Web')
        vm.tags = [prod, web]
        orphan_vm = Device(name='lonely-vm', device_type='linux_server_virtual', ip_address='10.9.9.9')
        sw = Device(name='core-sw', device_type='network_switch', ip_address='192.168.1.2',
                    monitoring_enabled=False)
        dup = Device(name='core-sw', device_type='icmp_only', ip_address='192.168.1.2')
        url = Device(name='grafana', device_type='url', ip_address='grafana.lan')
        url.tags = [web]
        hostname_only = Device(name='nas', device_type='linux_server_physical', ip_address='nas.lan')
        db.session.add_all([pve, vm, orphan_vm, sw, dup, url, hostname_only])
        db.session.flush()
        db.session.add_all([
            DeviceLink(source_id=vm.id, target_id=pve.id, link_type='runs_on'),
            Monitor(device_id=pve.id, monitor_type='node_exporter'),
            Monitor(device_id=pve.id, monitor_type='icmp', enabled=False),
            Subnet(cidr='192.168.1.0/24', name='LAN', vlan_id=10, gateway='192.168.1.1', location_id=rack.id),
            Subnet(cidr='10.9.0.0/16', name='Lab'),
        ])
        db.session.commit()
        return {'pve': pve.id, 'vm': vm.id, 'sw': sw.id, 'dup': dup.id}


# --- Ansible ----------------------------------------------------------------

def test_ansible_list_shape_and_groups(client, lab):
    inv = client.get('/api/export/ansible').get_json()
    hostvars = inv['_meta']['hostvars']
    # URL entries excluded by default; duplicate names made unique; spaces slugged
    assert set(hostvars) == {'pve01', 'web-01', 'lonely-vm', 'core-sw', f"core-sw-{lab['dup']}", 'nas'}
    assert 'ungrouped' in inv['all']['children']
    for group in inv['all']['children']:
        assert group in inv and isinstance(inv[group]['hosts'], list)
        assert group.replace('_', '').isalnum() and not group[0].isdigit()

    assert set(inv['tag_prod']['hosts']) == {'pve01', 'web-01'}
    assert inv['tag_web_tier']['hosts'] == ['web-01']
    assert inv['runs_on_pve01']['hosts'] == ['web-01']
    assert set(inv['location_basement_rack']['hosts']) == {'pve01', 'web-01'}
    assert inv['vendor_supermicro']['hosts'] == ['pve01']
    assert set(inv['network_lan']['hosts']) == {'pve01'}
    assert inv['monitoring_disabled']['hosts'] == ['core-sw']


def test_ansible_hostvars(client, lab):
    hv = client.get('/api/export/ansible').get_json()['_meta']['hostvars']
    pve = hv['pve01']
    assert pve['ansible_host'] == '192.168.1.10'
    assert pve['homelab_tags'] == ['prod']
    assert pve['homelab_monitors'] == ['node_exporter']  # disabled monitor excluded
    assert pve['homelab_subnet'] == '192.168.1.0/24' and pve['homelab_vlan'] == 10
    assert pve['homelab_networks'] == ['LAN', 'IoT']
    vm = hv['web-01']
    assert vm['ansible_host'] == '192.168.1.50'  # port stripped
    assert vm['homelab_name'] == 'web 01' and vm['homelab_runs_on'] == 'pve01'
    assert hv['nas']['ansible_host'] == 'nas.lan'


def test_ansible_host_mode_and_filters(client, lab):
    assert client.get('/api/export/ansible?host=pve01').get_json()['homelab_id'] == lab['pve']
    assert client.get('/api/export/ansible?host=nope').get_json() == {}
    only_prod = client.get('/api/export/ansible?tag=prod').get_json()['_meta']['hostvars']
    assert set(only_prod) == {'pve01', 'web-01'}
    enabled = client.get('/api/export/ansible?monitoring_enabled=true').get_json()['_meta']['hostvars']
    # the disabled core-sw is gone; the other one keeps its unfiltered name
    assert 'core-sw' not in enabled and f"core-sw-{lab['dup']}" in enabled
    assert enabled[f"core-sw-{lab['dup']}"]['homelab_id'] == lab['dup']
    everything = client.get('/api/export/ansible?include_all_types=true').get_json()
    assert 'grafana' in everything['_meta']['hostvars']


def test_ansible_yaml_matches_json(client, lab):
    resp = client.get('/api/export/ansible?format=yaml')
    assert 'attachment' in resp.headers['Content-Disposition']
    doc = yaml.safe_load(resp.get_data(as_text=True))
    hosts = doc['all']['hosts']
    assert hosts['pve01']['ansible_host'] == '192.168.1.10'
    assert 'homelab_runs_on' not in hosts['pve01']  # empty vars dropped
    assert set(doc['all']['children']['tag_prod']['hosts']) == {'pve01', 'web-01'}


def test_contrib_script_against_app(client, lab, monkeypatch, capsys):
    """Run the shipped inventory script with urlopen routed to the test client."""
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'ansible_inventory.py')
    spec = importlib.util.spec_from_file_location('homelab_inventory', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class Resp:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self.body

    def fake_urlopen(req, timeout, context):
        assert req.get_header('Authorization') == 'Bearer t0k'
        path = req.full_url.split('http://inv', 1)[1]
        return Resp(client.get(path).get_data())

    monkeypatch.setattr(mod, 'urlopen', fake_urlopen)
    monkeypatch.setenv('HOMELAB_INVENTORY_URL', 'http://inv/')
    monkeypatch.setenv('HOMELAB_INVENTORY_TOKEN', 't0k')
    monkeypatch.setenv('HOMELAB_INVENTORY_FILTER', 'tag=prod')
    monkeypatch.setattr('sys.argv', ['x', '--list'])
    mod.main()
    import json
    data = json.loads(capsys.readouterr().out)
    assert set(data['_meta']['hostvars']) == {'pve01', 'web-01'}
    monkeypatch.setattr('sys.argv', ['x', '--host', 'pve01'])
    mod.main()
    assert json.loads(capsys.readouterr().out)['ansible_host'] == '192.168.1.10'


def test_script_is_served(client):
    resp = client.get('/api/export/ansible/script')
    assert resp.status_code == 200 and 'HOMELAB_INVENTORY_URL' in resp.get_data(as_text=True)
    assert 'homelab_inventory.py' in resp.headers['Content-Disposition']


# --- NetBox -----------------------------------------------------------------

# Import form fields from NetBox 4.7 (dcim/ipam/virtualization/extras
# forms/bulk_import.py). Every exported column must be one of these.
NETBOX_FORM_FIELDS = {
    'tags': {'name', 'slug', 'color', 'weight', 'description', 'object_types', 'owner'},
    'sites': {'name', 'slug', 'status', 'region', 'group', 'tenant', 'facility', 'time_zone', 'description',
              'physical_address', 'shipping_address', 'latitude', 'longitude', 'owner', 'comments', 'tags'},
    'manufacturers': {'name', 'slug', 'description', 'owner', 'comments', 'tags'},
    'device_roles': {'name', 'slug', 'parent', 'color', 'vm_role', 'config_template', 'description', 'owner',
                     'comments', 'tags'},
    'device_types': {'manufacturer', 'default_platform', 'model', 'slug', 'part_number', 'u_height',
                     'exclude_from_utilization', 'is_full_depth', 'subdevice_role', 'airflow', 'cooling_method',
                     'description', 'weight', 'weight_unit', 'end_of_life', 'owner', 'comments', 'tags'},
    'devices': {'name', 'role', 'tenant', 'manufacturer', 'device_type', 'platform', 'serial', 'asset_tag', 'status',
                'site', 'location', 'rack', 'position', 'face', 'latitude', 'longitude', 'parent', 'device_bay',
                'airflow', 'cooling_method', 'virtual_chassis', 'vc_position', 'vc_priority', 'cluster',
                'description', 'config_template', 'owner', 'comments', 'tags'},
    'virtual_machines': {'name', 'virtual_machine_type', 'role', 'status', 'start_on_boot', 'site', 'cluster',
                         'device', 'platform', 'vcpus', 'memory', 'disk', 'description', 'serial', 'tenant', 'owner',
                         'comments', 'tags', 'config_template'},
    'vlans': {'site', 'group', 'vid', 'name', 'tenant', 'status', 'role', 'description', 'qinq_role', 'qinq_svlan',
              'owner', 'comments', 'tags'},
    'prefixes': {'prefix', 'vrf', 'tenant', 'vlan_group', 'vlan_site', 'vlan', 'status', 'role', 'scope_type',
                 'scope_name', 'scope_id', 'is_pool', 'mark_utilized', 'description', 'owner', 'comments', 'tags'},
    'ip_addresses': {'address', 'vrf', 'tenant', 'status', 'role', 'device', 'virtual_machine', 'interface',
                     'fhrp_group', 'is_primary', 'is_oob', 'dns_name', 'description', 'owner', 'comments', 'tags'},
}
REQUIRED = {
    'tags': {'name', 'slug'}, 'sites': {'name', 'slug', 'status'}, 'manufacturers': {'name', 'slug'},
    'device_roles': {'name', 'slug'}, 'device_types': {'manufacturer', 'model', 'slug'},
    'devices': {'role', 'manufacturer', 'device_type', 'status', 'site'},
    'virtual_machines': {'name', 'status'}, 'vlans': {'vid', 'name', 'status'},
    'prefixes': {'prefix', 'status'}, 'ip_addresses': {'address', 'status'},
}


def _zip_tables(client, qs=''):
    resp = client.get(f'/api/export/netbox{qs}')
    assert resp.mimetype == 'application/zip'
    zf = zipfile.ZipFile(io.BytesIO(resp.data))
    files = {k: f for k, f, _w in NETBOX_FILES}
    out = {}
    for key, filename in files.items():
        if filename in zf.namelist():
            out[key] = list(csv.DictReader(io.StringIO(zf.read(filename).decode())))
    return out, zf


def test_netbox_columns_match_netbox_import_forms():
    for key, cols in NETBOX_COLUMNS.items():
        assert set(cols) <= NETBOX_FORM_FIELDS[key], (key, set(cols) - NETBOX_FORM_FIELDS[key])
        assert REQUIRED[key] <= set(cols), key


def test_netbox_zip_contents(client, lab):
    t, zf = _zip_tables(client)
    assert 'README.txt' in zf.namelist()
    for key, rows in t.items():
        for row in rows:
            for col in REQUIRED[key]:
                assert row[col], (key, col, row)

    assert {r['name'] for r in t['sites']} == {'Basement Rack', 'Homelab'}
    assert {r['name'] for r in t['manufacturers']} == {'Supermicro', 'Generic'}
    assert {(r['manufacturer'], r['model']) for r in t['device_types']} == {
        ('Supermicro', 'X11SCL-F'), ('Generic', 'Unknown')}

    devices = {r['name']: r for r in t['devices']}
    assert set(devices) == {'pve01', 'core-sw', f"core-sw ({lab['dup']})", 'nas'}  # no URL, no VMs
    assert devices['pve01']['site'] == 'Basement Rack' and devices['pve01']['tags'] == 'prod'
    assert devices['nas']['manufacturer'] == 'Generic' and devices['nas']['site'] == 'Homelab'

    vms = {r['name']: r for r in t['virtual_machines']}
    assert vms['web 01']['device'] == 'pve01' and vms['web 01']['site'] == 'Basement Rack'
    assert vms['lonely-vm']['device'] == '' and vms['lonely-vm']['site'] == 'Homelab'

    # every referenced role/tag/site is defined in an earlier file
    roles = {r['name'] for r in t['device_roles']}
    tags = {r['slug'] for r in t['tags']}
    sites = {r['name'] for r in t['sites']}
    for row in t['devices'] + t['virtual_machines']:
        assert row['role'] in roles and row['site'] in sites
    for row in t['devices'] + t['virtual_machines'] + t['ip_addresses']:
        assert all(tag in tags for tag in filter(None, row['tags'].split(','))), row

    assert t['vlans'] == [{'vid': '10', 'name': 'LAN', 'status': 'active'}]
    prefixes = {r['prefix']: r for r in t['prefixes']}
    assert prefixes['192.168.1.0/24']['vlan'] == '10'
    assert prefixes['192.168.1.0/24']['scope_type'] == 'dcim.site'
    assert prefixes['192.168.1.0/24']['scope_name'] == 'Basement Rack'
    assert prefixes['10.9.0.0/16']['scope_type'] == ''

    ips = {r['address']: r for r in t['ip_addresses']}
    # masked with the subnet's prefix, deduplicated, gateway included, hostnames skipped
    assert set(ips) == {'192.168.1.1/24', '192.168.1.2/24', '192.168.1.10/24', '192.168.1.50/24', '10.9.9.9/16'}
    assert ips['192.168.1.2/24']['description'] == 'core-sw'
    assert 'Gateway' in ips['192.168.1.1/24']['description']


def test_netbox_single_file_summary_and_default_site(client, lab):
    resp = client.get('/api/export/netbox?file=devices&default_site=Garage')
    assert resp.mimetype == 'text/csv'
    rows = list(csv.DictReader(io.StringIO(resp.get_data(as_text=True))))
    assert next(r for r in rows if r['name'] == 'nas')['site'] == 'Garage'
    assert client.get('/api/export/netbox?file=nope').status_code == 400
    summary = {s['key']: s['rows'] for s in client.get('/api/export/netbox?summary=true').get_json()}
    assert summary['devices'] == 4 and summary['virtual_machines'] == 2 and summary['ip_addresses'] == 5


def test_netbox_names_stable_under_filters(client, lab):
    t, _ = _zip_tables(client, '?monitoring_enabled=true')
    assert f"core-sw ({lab['dup']})" in {r['name'] for r in t['devices']}


def test_netbox_tag_filter(client, lab):
    t, _ = _zip_tables(client, '?tag=web-tier')
    assert [r['name'] for r in t.get('virtual_machines', [])] == ['web 01']
    assert 'devices' not in t  # empty files are left out of the zip
