"""
"Add to monitoring" from IPAM: probe an address for known exporter ports and
suggest monitors, then create (or enable) monitoring in one transaction.
"""
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from services import netprobe

# TCP ports we can test with a plain connect. UDP-only services (SNMP 161,
# IPMI 623) can't be detected this way and are left for the user to pick.
PROBE_PORTS = [
    # (port, monitor_type, label)
    (9100, 'node_exporter', 'node_exporter'),
    (9633, 'smartctl_exporter', 'smartctl_exporter'),
    (80, 'http', 'HTTP'),
    (443, 'https', 'HTTPS'),
    (53, 'dns', 'DNS'),
    (3493, 'nut', 'NUT'),
    (8090, 'docker', 'Docker / cAdvisor'),
]
CONNECT_TIMEOUT = 0.8


def tcp_open(ip: str, port: int, timeout: float = CONNECT_TIMEOUT) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def probe_address(ip: str) -> dict:
    """Ping + PTR + TCP connect to known exporter ports, concurrently."""
    def check(entry):
        port, monitor_type, label = entry
        return {'port': port, 'monitor_type': monitor_type, 'label': label, 'open': tcp_open(ip, port)}

    with ThreadPoolExecutor(max_workers=len(PROBE_PORTS) + 1) as pool:
        ping_future = pool.submit(netprobe.ping, ip, netprobe.DEFAULT_TIMEOUT)
        ports = list(pool.map(check, PROBE_PORTS))
        reachable, rtt, _err = ping_future.result()
    ptr, _status = netprobe.reverse_lookup(ip)
    return {'ip': ip, 'reachable': reachable, 'rtt_ms': rtt, 'ptr': ptr, 'ports': ports}


def suggest(probe: dict) -> dict:
    """Monitors and a device type to pre-select, with reasons."""
    suggestions = []
    if probe['reachable']:
        suggestions.append({'monitor_type': 'icmp', 'port': None, 'reason': 'answers ping'})
    for p in probe['ports']:
        if p['open']:
            suggestions.append({'monitor_type': p['monitor_type'], 'port': None,
                                'reason': f"port {p['port']} open"})
    open_types = {p['monitor_type'] for p in probe['ports'] if p['open']}
    if 'nut' in open_types:
        device_type = 'ups_nut'
    elif 'node_exporter' in open_types:
        device_type = 'linux_server_physical'
    elif 'dns' in open_types:
        device_type = 'dns_record'
    else:
        device_type = 'icmp_only'
    if not suggestions:
        # Nothing answered: ICMP is still the sensible default to start watching it
        suggestions.append({'monitor_type': 'icmp', 'port': None, 'reason': 'default'})
    return {'monitors': suggestions, 'device_type': device_type}


def subnet_containing(ip_text: str, subnets) -> Optional[object]:
    ip = ipaddress.ip_address(ip_text)
    best = None
    for s in subnets:
        try:
            net = ipaddress.ip_network(s.cidr, strict=False)
        except ValueError:
            continue
        if net.version == ip.version and ip in net and (best is None or net.prefixlen > best[1].prefixlen):
            best = (s, net)
    return best[0] if best else None


def default_name(ip: str, ptr: Optional[str], hostname: Optional[str]) -> str:
    """Short hostname if we have one, else the IP with dashes."""
    for candidate in (hostname, ptr):
        if candidate:
            short = candidate.split('.')[0].strip()
            if short:
                return short[:100]
    return ip.replace('.', '-').replace(':', '-')


def dedupe_monitors(monitors: List[dict]) -> List[dict]:
    seen, out = set(), []
    for m in monitors:
        key = (m['monitor_type'], m.get('port'), m.get('endpoint'))
        if key not in seen:
            seen.add(key)
            out.append(m)
    return out
