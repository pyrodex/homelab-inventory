"""
ICMP + reverse DNS probing shared by ad-hoc discovery and IPAM sweeps.
"""
import logging
import math
import platform
import re
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:  # optional pure-Python fallback when no ping binary exists
    import ping3  # type: ignore

    ping3.verbosity(0)
    PING3_AVAILABLE = True
except Exception:  # pragma: no cover - depends on environment
    ping3 = None
    PING3_AVAILABLE = False

DEFAULT_TIMEOUT = 1.0  # seconds per probe
DEFAULT_WORKERS = 32


def build_ping_command(target: str, timeout: float, system: Optional[str] = None) -> List[str]:
    """
    One-packet ping with a per-reply timeout, in each platform's own unit:
      Linux (iputils / busybox) -W <seconds>
      macOS / *BSD              -W <milliseconds>
      Windows                   -n 1 -w <milliseconds>
    """
    system = (system or platform.system()).lower()
    timeout_ms = max(1, int(timeout * 1000))
    if system == 'windows':
        return ['ping', '-n', '1', '-w', str(timeout_ms), target]
    if system == 'linux':
        return ['ping', '-c', '1', '-W', str(max(1, math.ceil(timeout))), target]
    # darwin, freebsd, openbsd, netbsd
    return ['ping', '-c', '1', '-W', str(timeout_ms), target]


def _ping3(target: str, timeout: float) -> Tuple[bool, Optional[float], Optional[str]]:
    if not PING3_AVAILABLE:
        return False, None, 'Ping utility not available on server'
    try:
        rtt = ping3.ping(target, timeout=timeout, unit='s', privileged=False)
        if rtt is None or rtt is False:
            return False, None, 'No response'
        return True, float(rtt) * 1000.0, None
    except Exception as exc:  # pragma: no cover - depends on environment
        logger.debug(f"ping3 failed for {target}: {exc}")
        return False, None, 'Ping failed (ping3)'


def ping(target: str, timeout: float = DEFAULT_TIMEOUT) -> Tuple[bool, Optional[float], Optional[str]]:
    """Return (reachable, rtt_ms, error)."""
    cmd = build_ping_command(target, timeout)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2, check=False)
    except subprocess.TimeoutExpired:
        return False, None, 'Ping timed out'
    except FileNotFoundError:
        return _ping3(target, timeout)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"Ping failed for {target}: {exc}")
        return _ping3(target, timeout)

    output = (result.stdout or '') + (result.stderr or '')
    reachable = result.returncode == 0
    rtt = None
    match = re.search(r'time[=<]\s*([\d.]+)\s*ms', output)
    if match:
        try:
            rtt = float(match.group(1))
        except ValueError:
            rtt = None
    error = None if reachable else (output.strip()[:200] or 'No response')
    return reachable, rtt, error


PTR_FOUND = 'found'
PTR_NONE = 'none'      # resolver answered: no PTR record
PTR_ERROR = 'error'    # resolver failed / timed out: result unknown


def reverse_lookup(ip: str) -> Tuple[Optional[str], str]:
    """
    PTR lookup that distinguishes "no record" from "couldn't ask".
    Returns (hostname | None, PTR_FOUND | PTR_NONE | PTR_ERROR).
    """
    try:
        name = socket.gethostbyaddr(ip)[0]
        return (name, PTR_FOUND) if name else (None, PTR_NONE)
    except socket.herror as exc:
        # h_errno 1 = HOST_NOT_FOUND (authoritative no), 4 = NO_DATA; 2 = TRY_AGAIN
        return (None, PTR_NONE) if exc.errno in (1, 4) else (None, PTR_ERROR)
    except (socket.gaierror, OSError):
        return None, PTR_ERROR


def reverse_dns(ip: str) -> Optional[str]:
    return reverse_lookup(ip)[0]


def sweep(ips: Iterable[str], timeout: float = DEFAULT_TIMEOUT, workers: int = DEFAULT_WORKERS,
          resolve: str = 'alive') -> Dict[str, dict]:
    """
    Ping many addresses concurrently.
    Returns {ip: {reachable, rtt_ms, hostname, ptr_status, error}}.

    resolve:
      'alive' - PTR lookup only for addresses that answered (default)
      'all'   - PTR lookup for every address, so DNS-only entries show up
      'none'  - no lookups (ptr_status is None)
    """
    ips = list(ips)
    if not ips:
        return {}
    if resolve is True:  # backwards compatibility with the old boolean flag
        resolve = 'alive'
    elif resolve is False:
        resolve = 'none'

    def probe(ip):
        reachable, rtt, error = ping(ip, timeout)
        hostname, ptr_status = None, None
        if resolve == 'all' or (resolve == 'alive' and reachable):
            hostname, ptr_status = reverse_lookup(ip)
        return ip, {'reachable': reachable, 'rtt_ms': rtt, 'hostname': hostname,
                    'ptr_status': ptr_status, 'error': error}

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(ips)))) as pool:
        return dict(pool.map(probe, ips))
