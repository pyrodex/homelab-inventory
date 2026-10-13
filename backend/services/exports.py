"""
Inventory exports: Ansible dynamic inventory and NetBox CSV bulk import.

Both formats only ever *read* inventory data; nothing here mutates the DB.
"""
import csv
import io
import ipaddress
import re
import zipfile
from collections import OrderedDict
from typing import Dict, Iterable, List, Optional

import yaml

from services.ipam import extract_ip

DEVICE_TYPE_LABELS = {
    'linux_server_physical': 'Linux Server (Physical)',
    'linux_server_virtual': 'Linux Server (Virtual)',
    'freebsd_server': 'FreeBSD Server',
    'network_switch': 'Network Switch',
    'wireless_ap': 'Wireless Access Point',
    'icmp_only': 'ICMP Only Device',
    'ip_camera': 'IP Camera',
    'video_streamer': 'Video Streamer',
    'iot_device': 'IoT Device',
    'url': 'URL',
    'dns_record': 'DNS Record',
    'ipmi_console': 'IPMI Console',
    'ups_nut': 'UPS (NUT)',
}

# Not hosts you'd manage or rack: endpoints and records
NON_HOST_TYPES = {'url', 'dns_record'}
VIRTUAL_TYPES = {'linux_server_virtual'}


def _runs_on(device) -> Optional[object]:
    return next((l.target for l in device.outgoing_links if l.link_type == 'runs_on'), None)


def _ansible_host(device) -> Optional[str]:
    """IP or hostname with any :port removed."""
    raw = (device.ip_address or '').strip()
    if not raw:
        return None
    ip = extract_ip(raw)
    if ip is not None:
        return str(ip)
    return raw.rsplit(':', 1)[0] if raw.count(':') == 1 else raw


def _subnet_for(ip_text, networks):
    ip = extract_ip(ip_text)
    if ip is None:
        return None
    best = None
    for subnet, net in networks:
        if net.version == ip.version and ip in net and (best is None or net.prefixlen > best[1].prefixlen):
            best = (subnet, net)
    return best


def _parse_networks(subnets):
    out = []
    for s in subnets:
        try:
            out.append((s, ipaddress.ip_network(s.cidr, strict=False)))
        except ValueError:
            continue
    return out


# --- Ansible ----------------------------------------------------------------

def ansible_group_name(prefix: str, value: str) -> str:
    """Ansible-safe group name: [a-z0-9_], never starting with a digit."""
    slug = re.sub(r'[^a-z0-9]+', '_', str(value).lower()).strip('_') or 'unknown'
    return f"{prefix}_{slug}"


def _ansible_hostnames(devices) -> Dict[int, str]:
    """
    Inventory hostname per device: the device name if it's a clean token,
    else a slug; duplicates get a numeric suffix so every host is unique.
    """
    names: Dict[int, str] = {}
    used = set()
    for device in sorted(devices, key=lambda d: d.id):
        base = device.name.strip()
        if not re.match(r'^[A-Za-z0-9._-]+$', base):
            base = re.sub(r'[^A-Za-z0-9._-]+', '-', base).strip('-') or f'device-{device.id}'
        name = base
        if name.lower() in used:
            name = f"{base}-{device.id}"
        used.add(name.lower())
        names[device.id] = name
    return names


def build_ansible_inventory(devices, subnets=(), include_non_hosts=False, all_devices=None) -> dict:
    """
    Ansible dynamic inventory (the `--list` JSON shape):
      {"_meta": {"hostvars": {...}}, "all": {"children": [...]}, "<group>": {"hosts": [...]}}
    Hostnames are derived from `all_devices` (default: `devices`) so a device
    keeps the same inventory name no matter which filter is applied.
    """
    devices = [d for d in devices if include_non_hosts or d.device_type not in NON_HOST_TYPES]
    hostnames = _ansible_hostnames(all_devices if all_devices is not None else devices)
    networks = _parse_networks(subnets)
    groups: Dict[str, set] = {}
    hostvars: Dict[str, dict] = OrderedDict()

    def add(group, host):
        groups.setdefault(group, set()).add(host)

    for device in sorted(devices, key=lambda d: hostnames[d.id].lower()):
        host = hostnames[device.id]
        host_device = _runs_on(device)
        ansible_host = _ansible_host(device)
        subnet_hit = _subnet_for(device.ip_address, networks)
        net_list = [n.strip() for n in (device.networks or '').split(',') if n.strip()]

        vars_ = OrderedDict()
        if ansible_host:
            vars_['ansible_host'] = ansible_host
        vars_.update({
            'homelab_id': device.id,
            'homelab_name': device.name,
            'homelab_type': device.device_type,
            'homelab_function': device.device_function,
            'homelab_vendor': device.vendor_obj.name if device.vendor_obj else None,
            'homelab_model': device.model_obj.name if device.model_obj else None,
            'homelab_location': device.location_obj.name if device.location_obj else None,
            'homelab_serial': device.serial_number,
            'homelab_networks': net_list,
            'homelab_tags': [t.name for t in device.tags],
            'homelab_runs_on': hostnames.get(host_device.id, host_device.name) if host_device else None,
            'homelab_monitoring_enabled': bool(device.monitoring_enabled),
            'homelab_monitors': sorted({m.monitor_type for m in device.monitors if m.enabled}),
            'homelab_subnet': subnet_hit[0].cidr if subnet_hit else None,
            'homelab_vlan': subnet_hit[0].vlan_id if subnet_hit else None,
        })
        hostvars[host] = vars_

        add(ansible_group_name('type', device.device_type), host)
        if device.location_obj:
            add(ansible_group_name('location', device.location_obj.name), host)
        if device.vendor_obj:
            add(ansible_group_name('vendor', device.vendor_obj.name), host)
        for tag in device.tags:
            add(ansible_group_name('tag', tag.name), host)
        for net in net_list:
            add(ansible_group_name('network', net), host)
        if host_device:
            add(ansible_group_name('runs_on', hostnames.get(host_device.id, host_device.name)), host)
        add('monitoring_enabled' if device.monitoring_enabled else 'monitoring_disabled', host)

    inventory: Dict[str, object] = OrderedDict()
    inventory['_meta'] = {'hostvars': hostvars}
    inventory['all'] = {'children': ['ungrouped'] + sorted(groups)}
    inventory['ungrouped'] = {'hosts': []}
    for name in sorted(groups):
        inventory[name] = {'hosts': sorted(groups[name], key=str.lower)}
    return inventory


def ansible_inventory_yaml(inventory: dict) -> str:
    """Static YAML inventory equivalent of build_ansible_inventory()."""
    hostvars = inventory['_meta']['hostvars']
    children = OrderedDict()
    for name in inventory['all']['children']:
        if name == 'ungrouped':
            continue
        children[name] = {'hosts': {h: None for h in inventory[name]['hosts']}}

    def clean(vars_):
        return {k: v for k, v in vars_.items() if v not in (None, [], '')}

    doc = {'all': {
        'hosts': {h: clean(v) for h, v in hostvars.items()},
        'children': children,
    }}

    class _Dumper(yaml.SafeDumper):
        pass

    # Keep insertion order and render "None" host entries as bare keys
    _Dumper.add_representer(OrderedDict, lambda d, data: d.represent_dict(data.items()))
    _Dumper.add_representer(type(None), lambda d, _: d.represent_scalar('tag:yaml.org,2002:null', ''))
    header = "# Generated by Homelab Inventory — static Ansible inventory\n"
    return header + yaml.dump(doc, Dumper=_Dumper, sort_keys=False, default_flow_style=False, allow_unicode=True)


# --- NetBox -----------------------------------------------------------------

NETBOX_FILES = [
    # (key, filename, description)
    ('tags', '01_tags.csv', 'Customization → Tags'),
    ('sites', '02_sites.csv', 'Organization → Sites'),
    ('manufacturers', '03_manufacturers.csv', 'Devices → Manufacturers'),
    ('device_roles', '04_device_roles.csv', 'Devices → Device Roles'),
    ('device_types', '05_device_types.csv', 'Devices → Device Types'),
    ('devices', '06_devices.csv', 'Devices → Devices'),
    ('virtual_machines', '07_virtual_machines.csv', 'Virtualization → Virtual Machines'),
    ('vlans', '08_vlans.csv', 'IPAM → VLANs'),
    ('prefixes', '09_prefixes.csv', 'IPAM → Prefixes'),
    ('ip_addresses', '10_ip_addresses.csv', 'IPAM → IP Addresses'),
]

PLACEHOLDER_MANUFACTURER = 'Generic'
PLACEHOLDER_MODEL = 'Unknown'


def netbox_slug(value: str) -> str:
    """NetBox slugs: [-a-z0-9_], max 100."""
    slug = re.sub(r'[^a-z0-9_-]+', '-', str(value).lower()).strip('-')
    return (slug or 'item')[:100]


def _unique_names(devices) -> Dict[int, str]:
    """NetBox requires unique device/VM names per site; suffix duplicates."""
    seen, names = set(), {}
    for d in sorted(devices, key=lambda d: d.id):
        name = d.name.strip()[:64]
        if name.lower() in seen:
            name = f"{name[:56]} ({d.id})"
        seen.add(name.lower())
        names[d.id] = name
    return names


def _tag_cell(tags) -> str:
    return ','.join(t.name for t in tags)


def build_netbox_tables(devices, subnets, default_site='Homelab', all_devices=None) -> Dict[str, List[dict]]:
    """
    Rows for each NetBox import, keyed like NETBOX_FILES. Names are made
    unique across `all_devices` (default: `devices`) so they're stable
    between filtered and unfiltered exports.
    """
    hosts = [d for d in devices if d.device_type not in NON_HOST_TYPES]
    vms = [d for d in hosts if d.device_type in VIRTUAL_TYPES]
    physical = [d for d in hosts if d.device_type not in VIRTUAL_TYPES]
    scope = all_devices if all_devices is not None else devices
    names = _unique_names([d for d in scope if d.device_type not in NON_HOST_TYPES])
    networks = _parse_networks(subnets)
    physical_ids = {d.id for d in physical}

    def site_of(device):
        return device.location_obj.name if device.location_obj else default_site

    # Sites: every location used by an exported device or subnet
    site_names = OrderedDict()
    for d in hosts:
        site_names[site_of(d)] = True
    for s in subnets:
        if s.location:
            site_names[s.location.name] = True

    # Manufacturers and device types (physical only); placeholder when unset
    manufacturers = OrderedDict()
    device_types = OrderedDict()
    for d in physical:
        mfr = d.vendor_obj.name if d.vendor_obj else PLACEHOLDER_MANUFACTURER
        model = d.model_obj.name if (d.model_obj and d.vendor_obj) else PLACEHOLDER_MODEL
        manufacturers[mfr] = True
        device_types[(mfr, model)] = True

    roles = OrderedDict()
    for d in hosts:
        roles[DEVICE_TYPE_LABELS.get(d.device_type, d.device_type)] = True

    tags = OrderedDict()
    for d in devices:  # all devices: IP rows for URL/DNS entries carry tags too
        for t in d.tags:
            tags[t.name] = True

    tables: Dict[str, List[dict]] = {key: [] for key, _f, _d in NETBOX_FILES}
    tables['tags'] = [{'name': n, 'slug': n, 'color': '9e9e9e'} for n in tags]
    tables['sites'] = [{'name': n, 'slug': netbox_slug(n), 'status': 'active'} for n in site_names]
    tables['manufacturers'] = [{'name': n, 'slug': netbox_slug(n)} for n in manufacturers]
    tables['device_roles'] = [
        {'name': n, 'slug': netbox_slug(n), 'color': '9e9e9e', 'vm_role': 'true'} for n in roles
    ]
    tables['device_types'] = [
        {'manufacturer': m, 'model': model, 'slug': netbox_slug(f"{m}-{model}")} for m, model in device_types
    ]

    for d in sorted(physical, key=lambda d: names[d.id].lower()):
        mfr = d.vendor_obj.name if d.vendor_obj else PLACEHOLDER_MANUFACTURER
        tables['devices'].append({
            'name': names[d.id],
            'role': DEVICE_TYPE_LABELS.get(d.device_type, d.device_type),
            'manufacturer': mfr,
            'device_type': d.model_obj.name if (d.model_obj and d.vendor_obj) else PLACEHOLDER_MODEL,
            'status': 'active',
            'site': site_of(d),
            'serial': d.serial_number or '',
            'description': (d.device_function or '')[:200],
            'tags': _tag_cell(d.tags),
            'comments': f"Imported from Homelab Inventory (id {d.id})",
        })

    for d in sorted(vms, key=lambda d: names[d.id].lower()):
        host = _runs_on(d)
        # A VM may point at a standalone host device directly; it must then
        # share the host's site. Hosts that aren't exported fall back to site only.
        host_name = names.get(host.id) if host is not None and host.id in physical_ids else ''
        tables['virtual_machines'].append({
            'name': names[d.id],
            'role': DEVICE_TYPE_LABELS.get(d.device_type, d.device_type),
            'status': 'active',
            'site': site_of(host) if host_name else site_of(d),
            'device': host_name,
            'serial': d.serial_number or '',
            'description': (d.device_function or '')[:200],
            'tags': _tag_cell(d.tags),
            'comments': f"Imported from Homelab Inventory (id {d.id})",
        })

    vlans = OrderedDict()
    for s in subnets:
        if s.vlan_id and s.vlan_id not in vlans:
            vlans[s.vlan_id] = {'vid': s.vlan_id, 'name': (s.name or f"VLAN {s.vlan_id}")[:64], 'status': 'active'}
    tables['vlans'] = list(vlans.values())

    for s, net in sorted(networks, key=lambda x: (x[1].version, int(x[1].network_address), x[1].prefixlen)):
        tables['prefixes'].append({
            'prefix': str(net),
            'status': 'active',
            'vlan': s.vlan_id or '',
            'scope_type': 'dcim.site' if s.location else '',
            'scope_name': s.location.name if s.location else '',
            'description': (s.name or s.description or '')[:200],
        })

    # IP addresses: one row per address (NetBox enforces global uniqueness by
    # default), masked with the containing subnet's prefix length.
    ip_rows: Dict[str, dict] = OrderedDict()

    def add_ip(ip_obj, description, tag_cell=''):
        hit = _subnet_for(str(ip_obj), networks)
        prefixlen = hit[1].prefixlen if hit else (32 if ip_obj.version == 4 else 128)
        address = f"{ip_obj}/{prefixlen}"
        if address in ip_rows:
            existing = ip_rows[address]
            if description not in existing['description']:
                existing['description'] = f"{existing['description']}, {description}"[:200]
            return
        ip_rows[address] = {'address': address, 'status': 'active', 'description': description[:200], 'tags': tag_cell}

    for d in sorted(devices, key=lambda d: d.id):
        ip = extract_ip(d.ip_address)
        if ip is not None:
            add_ip(ip, d.name, _tag_cell(d.tags))
    for s, net in networks:
        gw = extract_ip(s.gateway)
        if gw is not None and gw in net:
            add_ip(gw, f"Gateway ({s.name or s.cidr})")
    tables['ip_addresses'] = sorted(
        ip_rows.values(),
        key=lambda r: (ipaddress.ip_interface(r['address']).version, int(ipaddress.ip_interface(r['address']).ip)),
    )
    return tables


NETBOX_COLUMNS = {
    'tags': ['name', 'slug', 'color'],
    'sites': ['name', 'slug', 'status'],
    'manufacturers': ['name', 'slug'],
    'device_roles': ['name', 'slug', 'color', 'vm_role'],
    'device_types': ['manufacturer', 'model', 'slug'],
    'devices': ['name', 'role', 'manufacturer', 'device_type', 'status', 'site', 'serial', 'description', 'tags', 'comments'],
    'virtual_machines': ['name', 'role', 'status', 'site', 'device', 'serial', 'description', 'tags', 'comments'],
    'vlans': ['vid', 'name', 'status'],
    'prefixes': ['prefix', 'status', 'vlan', 'scope_type', 'scope_name', 'description'],
    'ip_addresses': ['address', 'status', 'description', 'tags'],
}


def netbox_csv(key: str, rows: Iterable[dict]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=NETBOX_COLUMNS[key], extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return out.getvalue()


def netbox_zip(tables: Dict[str, List[dict]]) -> bytes:
    buf = io.BytesIO()
    lines = [
        'NetBox import from Homelab Inventory',
        '====================================',
        '',
        'Import these files in order (each page: Import → upload or paste the CSV).',
        'Later files reference objects created by earlier ones. Empty files are skipped.',
        '',
    ]
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for key, filename, where in NETBOX_FILES:
            rows = tables.get(key, [])
            if not rows:
                continue
            zf.writestr(filename, netbox_csv(key, rows))
            lines.append(f"  {filename:<26} {where}  ({len(rows)} rows)")
        lines += [
            '',
            'Notes',
            f'  * Devices without a vendor/model use manufacturer "{PLACEHOLDER_MANUFACTURER}" / type "{PLACEHOLDER_MODEL}".',
            '  * Devices without a location go to the default site.',
            '  * Device roles come from the inventory device type.',
            '  * Virtual machines are attached to their "runs on" host device when it is exported.',
            '  * IPs use the containing subnet\'s prefix length and are not assigned to interfaces.',
            '  * URL and DNS record entries are not exported as devices.',
        ]
        zf.writestr('README.txt', '\n'.join(lines) + '\n')
    return buf.getvalue()
