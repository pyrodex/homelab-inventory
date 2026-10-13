"""
IPAM helpers: work out which addresses in a subnet are in use by inventoried
devices, which are reserved, and which are free for new assignments.

Address sources considered "in use":
  * Device.ip_address (plain IP, or IP:port; hostnames are ignored)
  * Monitor.endpoint when it contains a literal IP (bare, IP:port, or a URL)

A device counts as "monitored" when its monitoring_enabled flag is on and it
has at least one enabled monitor (or no monitors at all, since many device
types export from the device record itself). Devices with monitoring turned
off are reported as "unmonitored" so they still block the address.
"""
import ipaddress
import re
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

# Largest subnet for which we will return a per-address listing. Beyond this
# only summary counts and compressed free ranges are returned.
MAX_ADDRESS_LISTING = 4096

STATUS_NETWORK = 'network'
STATUS_BROADCAST = 'broadcast'
STATUS_GATEWAY = 'gateway'
STATUS_RESERVED = 'reserved'
STATUS_MONITORED = 'monitored'
STATUS_UNMONITORED = 'unmonitored'
STATUS_FREE = 'free'
# Not in inventory, but the network says the address is in use
STATUS_DHCP = 'dhcp'      # active DHCP lease
STATUS_SEEN = 'seen'      # answered a ping sweep recently


def normalize_cidr(value: str) -> str:
    """Return canonical CIDR text (host bits cleared). Raises ValueError."""
    if not value or not str(value).strip():
        raise ValueError("CIDR is required")
    value = str(value).strip()
    if '/' not in value:
        raise ValueError("CIDR must include a prefix length, e.g. 192.168.1.0/24")
    return str(ipaddress.ip_network(value, strict=False))


def extract_ip(value: Optional[str]):
    """
    Pull a literal IP address out of an inventory value.
    Accepts '10.0.0.5', '10.0.0.5:9100', '[fd00::1]:443', 'http://10.0.0.5:8080/x'.
    Returns an ipaddress object or None (e.g. for hostnames).
    """
    if not value or not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None

    if '://' in candidate:
        try:
            candidate = urlparse(candidate).hostname or ''
        except ValueError:
            return None

    candidate = candidate.strip('[]')
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        pass

    # [v6]:port or v4:port
    match = re.match(r'^\[([0-9a-fA-F:.]+)\](?::\d+)?$', value.strip())
    if match:
        candidate = match.group(1)
    elif candidate.count(':') == 1:
        candidate = candidate.split(':', 1)[0]
    else:
        return None
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        return None


def parse_reserved(text: Optional[str], network) -> List[Tuple[int, int]]:
    """
    Parse reserved-range text into a list of (start_int, end_int) inclusive
    tuples clipped to the network. Raises ValueError on malformed input or
    entries that fall outside the subnet.

    Supported tokens (comma, whitespace or newline separated):
      192.168.1.10                 single address
      192.168.1.100-192.168.1.199  full range
      192.168.1.100-199            IPv4 shorthand (last octet)
      192.168.1.128/26             CIDR block
    """
    if not text:
        return []
    ranges = []
    tokens = [t for t in re.split(r'[,\s]+', text.strip()) if t]
    net_start = int(network.network_address)
    net_end = int(network.broadcast_address)

    for token in tokens:
        if '/' in token:
            block = ipaddress.ip_network(token, strict=False)
            if block.version != network.version or not block.subnet_of(network):
                raise ValueError(f"Reserved block {token} is not inside {network}")
            ranges.append((int(block.network_address), int(block.broadcast_address)))
            continue

        if '-' in token:
            start_s, end_s = token.split('-', 1)
            start = ipaddress.ip_address(start_s)
            if network.version == 4 and end_s.isdigit() and '.' not in end_s:
                end = ipaddress.ip_address('.'.join(start_s.split('.')[:3] + [end_s]))
            else:
                end = ipaddress.ip_address(end_s)
            if int(end) < int(start):
                raise ValueError(f"Reserved range {token} ends before it starts")
        else:
            start = end = ipaddress.ip_address(token)

        if start.version != network.version or start not in network or end not in network:
            raise ValueError(f"Reserved entry {token} is not inside {network}")
        ranges.append((max(int(start), net_start), min(int(end), net_end)))

    return ranges


def usable_bounds(network) -> Tuple[int, int]:
    """Inclusive int bounds of assignable host addresses."""
    first = int(network.network_address)
    last = int(network.broadcast_address)
    if network.version == 4:
        if network.prefixlen < 31:
            return first + 1, last - 1
        return first, last
    # IPv6: the subnet-router anycast (network address) is not assignable
    if network.prefixlen < 127:
        return first + 1, last
    return first, last


def build_address_index(devices: Iterable) -> Dict[int, Dict[int, List[dict]]]:
    """
    Map ip version -> {ip_int: [device refs]} across devices and their monitors.
    Each ref: {device_id, name, device_type, monitored, source}.
    """
    index: Dict[int, Dict[int, List[dict]]] = {4: {}, 6: {}}

    for device in devices:
        monitors = list(getattr(device, 'monitors', []) or [])
        has_enabled_monitor = any(m.enabled for m in monitors) or not monitors
        monitored = bool(device.monitoring_enabled) and has_enabled_monitor

        seen = set()
        sources = [(device.ip_address, 'device')]
        sources += [(m.endpoint, f'monitor:{m.monitor_type}') for m in monitors]
        for raw, source in sources:
            ip = extract_ip(raw)
            if ip is None:
                continue
            key = (ip.version, int(ip))
            if key in seen:
                continue
            seen.add(key)
            index[ip.version].setdefault(int(ip), []).append({
                'device_id': device.id,
                'name': device.name,
                'device_type': device.device_type,
                'monitored': monitored,
                'source': source,
            })
    return index


def _range_dict(start: int, end: int, version: int) -> dict:
    to_ip = ipaddress.IPv4Address if version == 4 else ipaddress.IPv6Address
    return {'start': str(to_ip(start)), 'end': str(to_ip(end)), 'size': end - start + 1}


def build_observation_index(observations, now=None, stale_after=None) -> Dict[int, Dict[int, dict]]:
    """
    ip version -> {ip_int: info} for addresses the network reports in use:
    an active DHCP lease, or a ping reply within `stale_after`.
    """
    from datetime import datetime, timedelta
    now = now or datetime.utcnow()
    stale_after = stale_after if stale_after is not None else timedelta(hours=72)
    index: Dict[int, Dict[int, dict]] = {4: {}, 6: {}}
    for obs in observations:
        try:
            ip = ipaddress.ip_address(obs.ip)
        except ValueError:
            continue
        dhcp = bool(obs.dhcp_active)
        seen = bool(obs.ping_last_seen and obs.ping_last_seen >= now - stale_after)
        if not (dhcp or seen):
            continue
        index[ip.version][int(ip)] = {
            'status': STATUS_DHCP if dhcp else STATUS_SEEN,
            'dhcp': dhcp,
            'seen': seen,
            'reachable_now': bool(obs.ping_reachable),
            'hostname': obs.dhcp_hostname or obs.ping_hostname or obs.hostname,
            'mac': obs.mac,
            'last_seen': (obs.ping_last_seen.isoformat() + 'Z') if obs.ping_last_seen else None,
            'dhcp_expires': (obs.dhcp_expires.isoformat() + 'Z') if obs.dhcp_expires else None,
        }
    return index


def analyze_subnet(subnet, address_index, observation_index=None) -> dict:
    """
    Compute utilization for a Subnet model instance.
    Returns summary counts, used addresses, free ranges and (for small
    subnets) a per-address status listing.
    """
    network = ipaddress.ip_network(subnet.cidr, strict=False)
    version = network.version
    first, last = usable_bounds(network)
    net_lo, net_hi = int(network.network_address), int(network.broadcast_address)

    gateway_int = None
    gateway_ip = extract_ip(subnet.gateway)
    if gateway_ip is not None and gateway_ip.version == version and gateway_ip in network:
        gateway_int = int(gateway_ip)

    try:
        reserved_ranges = parse_reserved(subnet.reserved_ranges, network)
        reserved_error = None
    except ValueError as exc:
        reserved_ranges, reserved_error = [], str(exc)

    # Devices in this subnet (anywhere in the block, including net/broadcast)
    used: Dict[int, List[dict]] = {
        ip: refs for ip, refs in address_index.get(version, {}).items()
        if net_lo <= ip <= net_hi
    }

    # Live on the network but not inventoried (gateway excluded: expected to answer)
    observed = {
        ip: info for ip, info in (observation_index or {}).get(version, {}).items()
        if net_lo <= ip <= net_hi
    }
    unknown = {
        ip: info for ip, info in observed.items()
        if ip not in used and ip != gateway_int and first <= ip <= last
    }

    def is_reserved(ip_int: int) -> bool:
        return any(lo <= ip_int <= hi for lo, hi in reserved_ranges)

    usable_total = max(0, last - first + 1)

    # Blocked intervals (inclusive) inside the usable range: used addresses,
    # the gateway, and reserved ranges. Interval math keeps this cheap even
    # for very large (IPv6) reservations.
    point_blocks = set(ip for ip in used if first <= ip <= last) | set(unknown)
    if gateway_int is not None and first <= gateway_int <= last:
        point_blocks.add(gateway_int)
    intervals = [(ip, ip) for ip in point_blocks]
    for lo, hi in reserved_ranges:
        lo, hi = max(lo, first), min(hi, last)
        if hi >= lo:
            intervals.append((lo, hi))
    intervals.sort()
    merged: List[Tuple[int, int]] = []
    for lo, hi in intervals:
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))

    # Free ranges = gaps between blocked intervals inside usable bounds
    free_ranges = []
    cursor = first
    for lo, hi in merged:
        if lo > cursor:
            free_ranges.append(_range_dict(cursor, lo - 1, version))
        cursor = max(cursor, hi + 1)
    if usable_total and cursor <= last:
        free_ranges.append(_range_dict(cursor, last, version))
    free_total = sum(r['size'] for r in free_ranges)

    used_in_usable = len([ip for ip in used if first <= ip <= last])
    # Everything blocked that isn't an inventoried device: gateway + reservations
    reserved_total = (usable_total - free_total) - used_in_usable - len(unknown)

    monitored_count = sum(1 for refs in used.values() if any(r['monitored'] for r in refs))
    unmonitored_count = len(used) - monitored_count
    conflicts = [
        {'ip': _range_dict(ip, ip, version)['start'], 'devices': refs}
        for ip, refs in sorted(used.items())
        if len({r['device_id'] for r in refs}) > 1
    ]

    to_ip = ipaddress.IPv4Address if version == 4 else ipaddress.IPv6Address
    used_list = []
    for ip_int, refs in sorted(used.items()):
        notes = []
        if ip_int == gateway_int:
            notes.append('gateway')
        if is_reserved(ip_int):
            notes.append('reserved')
        if not (first <= ip_int <= last):
            notes.append('network/broadcast address')
        used_list.append({
            'ip': str(to_ip(ip_int)),
            'status': STATUS_MONITORED if any(r['monitored'] for r in refs) else STATUS_UNMONITORED,
            'devices': refs,
            'notes': notes,
            'observed': observed.get(ip_int),
        })

    unknown_list = [
        {'ip': str(to_ip(ip_int)), 'status': info['status'], 'in_reserved_range': is_reserved(ip_int), **info}
        for ip_int, info in sorted(unknown.items())
    ]

    result = {
        'subnet': subnet.to_dict(),
        'version': version,
        'prefix_length': network.prefixlen,
        'network_address': str(network.network_address),
        'broadcast_address': str(network.broadcast_address) if version == 4 else None,
        'first_usable': str(to_ip(first)) if usable_total else None,
        'last_usable': str(to_ip(last)) if usable_total else None,
        'summary': {
            'total_addresses': network.num_addresses,
            'usable': usable_total,
            'used': used_in_usable,
            'monitored': monitored_count,
            'unmonitored': unmonitored_count,
            'reserved': reserved_total,
            'unknown_active': len(unknown),
            'dhcp': sum(1 for i in unknown.values() if i['status'] == STATUS_DHCP),
            'seen': sum(1 for i in unknown.values() if i['status'] == STATUS_SEEN),
            'free': free_total,
            'utilization_percent': round(100.0 * (usable_total - free_total) / usable_total, 1) if usable_total else 0.0,
        },
        'used_addresses': used_list,
        'unknown_addresses': unknown_list,
        'free_ranges': free_ranges,
        'conflicts': conflicts,
        'reserved_error': reserved_error,
        'addresses': None,
        'address_listing_limit': MAX_ADDRESS_LISTING,
    }

    if network.num_addresses <= MAX_ADDRESS_LISTING:
        addresses = []
        for ip_int in range(net_lo, net_hi + 1):
            entry = {'ip': str(to_ip(ip_int))}
            if ip_int in used:
                refs = used[ip_int]
                entry['status'] = STATUS_MONITORED if any(r['monitored'] for r in refs) else STATUS_UNMONITORED
                entry['devices'] = refs
            elif ip_int < first:
                entry['status'] = STATUS_NETWORK
            elif ip_int > last:
                entry['status'] = STATUS_BROADCAST
            elif ip_int == gateway_int:
                entry['status'] = STATUS_GATEWAY
            elif ip_int in unknown:
                info = unknown[ip_int]
                entry['status'] = info['status']
                entry['observed'] = info
            elif is_reserved(ip_int):
                entry['status'] = STATUS_RESERVED
            else:
                entry['status'] = STATUS_FREE
            addresses.append(entry)
        result['addresses'] = addresses

    return result


def next_free(analysis: dict, count: int = 1) -> List[str]:
    """Return up to `count` free addresses from an analyze_subnet() result."""
    out = []
    version = analysis['version']
    to_ip = ipaddress.IPv4Address if version == 4 else ipaddress.IPv6Address
    for block in analysis['free_ranges']:
        start = int(ipaddress.ip_address(block['start']))
        for offset in range(min(block['size'], count - len(out))):
            out.append(str(to_ip(start + offset)))
        if len(out) >= count:
            break
    return out


def find_unassigned(devices: Iterable, subnets: Iterable) -> List[dict]:
    """Devices with a literal IP that is not covered by any defined subnet."""
    networks = []
    for s in subnets:
        try:
            networks.append(ipaddress.ip_network(s.cidr, strict=False))
        except ValueError:
            continue
    orphans = []
    for device in devices:
        ip = extract_ip(device.ip_address)
        if ip is None:
            continue
        if not any(ip.version == n.version and ip in n for n in networks):
            orphans.append({
                'device_id': device.id,
                'name': device.name,
                'ip_address': str(ip),
                'device_type': device.device_type,
                'monitoring_enabled': device.monitoring_enabled,
            })
    orphans.sort(key=lambda d: (ipaddress.ip_address(d['ip_address']).version,
                                int(ipaddress.ip_address(d['ip_address']))))
    return orphans
