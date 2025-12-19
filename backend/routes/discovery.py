"""
Discovery routes for probing hosts via ICMP and reverse DNS lookups.
"""
import ipaddress
import logging
import platform
import re
import socket
import subprocess
from typing import List, Tuple

from flask import Blueprint, request

from utils.response import success_response, validation_error_response

discovery_bp = Blueprint('discovery', __name__)

# Guardrails to avoid runaway scans
MAX_TARGETS = 256
DEFAULT_TIMEOUT = 1.5  # seconds


def register_discovery_routes(app, limiter):
    """Register discovery routes with the app."""
    app.register_blueprint(discovery_bp, url_prefix='/api/discovery')

    limiter.limit("20 per minute")(run_discovery)


def _normalize_targets(raw_targets) -> List[str]:
    """Accept string/array and return a cleaned list of targets."""
    if not raw_targets:
        return []

    targets = []
    if isinstance(raw_targets, str):
        candidates = re.split(r'[,\s]+', raw_targets)
        targets.extend([c.strip() for c in candidates if c.strip()])
    elif isinstance(raw_targets, list):
        for item in raw_targets:
            if item is None:
                continue
            if isinstance(item, str):
                cleaned = item.strip()
                if cleaned:
                    targets.append(cleaned)
    return targets


def _expand_cidr(cidr_value: str) -> List[str]:
    """Expand a CIDR into a list of host addresses."""
    network = ipaddress.ip_network(cidr_value, strict=False)
    hosts = list(network.hosts())
    # For /32 return the single address
    if not hosts:
        hosts = [network.network_address]
    return [str(ip) for ip in hosts]


def _expand_range(range_value: str) -> List[str]:
    """
    Expand a dashed IP range (start-end) into a list of addresses.
    Example: 192.168.1.10-192.168.1.20
    """
    if '-' not in range_value:
        raise ValueError("Range must be in start-end format")

    start_str, end_str = [part.strip() for part in range_value.split('-', 1)]
    start_ip = ipaddress.ip_address(start_str)
    end_ip = ipaddress.ip_address(end_str)

    if start_ip.version != end_ip.version:
        raise ValueError("Range start and end must be the same IP version")

    if int(end_ip) < int(start_ip):
        raise ValueError("Range end must be greater than or equal to start")

    count = int(end_ip) - int(start_ip) + 1
    return [str(ipaddress.ip_address(int(start_ip) + offset)) for offset in range(count)]


def _build_ping_command(target: str, timeout: float) -> List[str]:
    """Build a platform-aware ping command."""
    system = platform.system().lower()
    count_flag = "-c" if system != "windows" else "-n"
    timeout_flag = "-W" if system != "windows" else "-w"

    if system in ("windows", "darwin"):
        timeout_value = str(int(timeout * 1000))  # milliseconds
    else:
        timeout_value = str(max(1, int(round(timeout))))  # seconds (Linux)

    return ["ping", count_flag, "1", timeout_flag, timeout_value, target]


def _ping_target(target: str) -> Tuple[bool, float, str]:
    """
    Run an ICMP ping to the target.
    Returns: (reachable, rtt_ms, error_message)
    """
    cmd = _build_ping_command(target, DEFAULT_TIMEOUT)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT + 1,
            check=False
        )
        output = (result.stdout or "") + (result.stderr or "")
        reachable = result.returncode == 0

        rtt_ms = None
        match = re.search(r'time[=<]([\d\.]+)\s*ms', output)
        if match:
            try:
                rtt_ms = float(match.group(1))
            except ValueError:
                rtt_ms = None

        error_msg = None if reachable else (output.strip()[:200] or "No response")
        return reachable, rtt_ms, error_msg
    except subprocess.TimeoutExpired:
        return False, None, "Ping timed out"
    except FileNotFoundError:
        return False, None, "Ping utility not available on server"
    except Exception as exc:  # pragma: no cover - defensive
        logging.warning(f"Ping failed for {target}: {exc}")
        return False, None, str(exc)


def _resolve_ip(target: str) -> str:
    """Resolve a hostname/IP string to an IPv4 address string."""
    try:
        ip_obj = ipaddress.ip_address(target)
        return str(ip_obj)
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(target, None, family=socket.AF_INET)
        if infos:
            return infos[0][4][0]
    except socket.gaierror:
        return None
    except Exception as exc:  # pragma: no cover - defensive
        logging.debug(f"Resolution error for {target}: {exc}")
        return None
    return None


def _reverse_dns(ip_str: str) -> str:
    """Attempt reverse DNS lookup for an IP address."""
    try:
        return socket.gethostbyaddr(ip_str)[0]
    except Exception:
        return None


def _discover_target(target: str) -> dict:
    """Probe a single target and return discovery metadata."""
    resolved_ip = _resolve_ip(target)
    if not resolved_ip:
        return {
            'input': target,
            'ip': None,
            'hostname': None,
            'reachable': False,
            'rtt_ms': None,
            'error': 'Unable to resolve hostname or IP'
        }

    reachable, rtt_ms, ping_error = _ping_target(resolved_ip)
    hostname = _reverse_dns(resolved_ip)

    return {
        'input': target,
        'ip': resolved_ip,
        'hostname': hostname,
        'reachable': reachable,
        'rtt_ms': rtt_ms,
        'error': ping_error if not reachable else None
    }


@discovery_bp.route('', methods=['POST'])
def run_discovery():
    """
    Run ICMP-based discovery for provided targets.

    Expected payload:
    {
        "targets": ["1.1.1.1", "host.local"],        # optional list or comma/newline-separated string
        "range": "192.168.1.10-192.168.1.20",        # optional dashed range
        "cidr": "192.168.1.0/28"                     # optional CIDR
    }
    """
    if not request.is_json:
        return validation_error_response({'body': ['Request body must be JSON']})

    payload = request.get_json() or {}
    targets = _normalize_targets(payload.get('targets'))
    range_value = payload.get('range')
    cidr_value = payload.get('cidr')

    # Expand range inputs
    try:
        if range_value:
            targets.extend(_expand_range(range_value.strip()))
    except ValueError as exc:
        return validation_error_response({'range': [str(exc)]})

    try:
        if cidr_value:
            targets.extend(_expand_cidr(cidr_value.strip()))
    except ValueError as exc:
        return validation_error_response({'cidr': [str(exc)]})

    # De-duplicate while preserving order
    seen = set()
    unique_targets = []
    for t in targets:
        if t not in seen:
            unique_targets.append(t)
            seen.add(t)

    if not unique_targets:
        return validation_error_response({'targets': ['Provide at least one IP/hostname or range']})

    if len(unique_targets) > MAX_TARGETS:
        return validation_error_response({'targets': [f"Too many targets requested ({len(unique_targets)}). Limit is {MAX_TARGETS}."]})

    results = [_discover_target(target) for target in unique_targets]
    reachable_count = sum(1 for r in results if r.get('reachable'))

    return success_response({
        'summary': {
            'requested': len(unique_targets),
            'reachable': reachable_count,
        },
        'results': results
    })

