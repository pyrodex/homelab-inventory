"""
Scheduled ping sweeps of IPAM subnets.

Only IPv4 subnets up to IPAM_SCAN_MAX_HOSTS usable addresses can be swept
(IPv6 subnets are far too large to enumerate). Results land in
IpObservation so IPAM can show addresses that answer but aren't in inventory.
"""
import ipaddress
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from models import IpObservation, Subnet, db
from services import netprobe

logger = logging.getLogger(__name__)

MIN_INTERVAL_MINUTES = 5
MAX_INTERVAL_MINUTES = 7 * 24 * 60

_running = set()
_running_lock = threading.Lock()


def max_scan_hosts() -> int:
    try:
        return max(1, int(os.environ.get('IPAM_SCAN_MAX_HOSTS', '1024')))
    except ValueError:
        return 1024


def stale_after() -> timedelta:
    """How long a ping-seen address stays 'in use' after it was last seen."""
    try:
        hours = float(os.environ.get('IPAM_STALE_AFTER_HOURS', '72'))
    except ValueError:
        hours = 72.0
    return timedelta(hours=max(0.0, hours))


def scan_eligibility(cidr: str) -> Optional[str]:
    """None if the subnet can be swept, else a human-readable reason."""
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return 'Invalid CIDR'
    if net.version != 4:
        return 'Ping sweeps are IPv4-only (IPv6 subnets are too large to enumerate)'
    hosts = net.num_addresses - 2 if net.prefixlen < 31 else net.num_addresses
    limit = max_scan_hosts()
    if hosts > limit:
        return f'Subnet has {hosts} hosts; sweeps are limited to {limit} (IPAM_SCAN_MAX_HOSTS)'
    return None


def is_running(subnet_id: int) -> bool:
    with _running_lock:
        return subnet_id in _running


def _hosts(cidr: str):
    net = ipaddress.ip_network(cidr, strict=False)
    if net.prefixlen >= 31:
        return [str(ip) for ip in net]
    return [str(ip) for ip in net.hosts()]


def _claim(subnet_id: int) -> bool:
    with _running_lock:
        if subnet_id in _running:
            return False
        _running.add(subnet_id)
        return True


def scan_subnet(subnet_id: int, timeout: float = netprobe.DEFAULT_TIMEOUT, _claimed: bool = False) -> dict:
    """Sweep one subnet now (blocking). Must run inside an app context."""
    if not _claimed and not _claim(subnet_id):
        return {'status': 'already_running'}
    started = time.monotonic()
    try:
        subnet = db.session.get(Subnet, subnet_id)
        if subnet is None:
            return {'status': 'missing'}
        reason = scan_eligibility(subnet.cidr)
        if reason:
            subnet.last_scan_error = reason[:255]
            db.session.commit()
            return {'status': 'ineligible', 'error': reason}

        ips = _hosts(subnet.cidr)
        results = netprobe.sweep(ips, timeout=timeout)
        now = datetime.utcnow()
        rows = {o.ip: o for o in IpObservation.query.filter(IpObservation.ip.in_(ips)).all()}
        alive = 0
        new_ips = []
        for ip, res in results.items():
            row = rows.get(ip)
            if row is None:
                if not res['reachable']:
                    continue  # don't create rows for silence
                row = IpObservation(ip=ip)
                db.session.add(row)
                new_ips.append(ip)
            row.ping_last_checked = now
            row.ping_reachable = bool(res['reachable'])
            if res['reachable']:
                alive += 1
                row.ping_last_seen = now
                row.ping_rtt_ms = res['rtt_ms']
                if res['hostname']:
                    row.ping_hostname = res['hostname'][:255]
                    row.hostname = row.hostname or row.ping_hostname

        subnet.last_scan_at = now
        subnet.last_scan_alive = alive
        subnet.last_scan_duration_ms = int((time.monotonic() - started) * 1000)
        subnet.last_scan_error = None
        db.session.commit()
        try:
            from services.webhooks import emit_discovered
            emit_discovered(new_ips, 'ping_sweep')
        except Exception as exc:  # never let notifications break a sweep
            logger.warning(f"Webhook emit after sweep failed: {exc}")
        logger.info(f"Swept {subnet.cidr}: {alive}/{len(ips)} alive in {subnet.last_scan_duration_ms} ms")
        return {'status': 'ok', 'scanned': len(ips), 'alive': alive,
                'duration_ms': subnet.last_scan_duration_ms}
    except Exception as exc:
        db.session.rollback()
        logger.warning(f"Sweep of subnet {subnet_id} failed: {exc}")
        try:
            subnet = db.session.get(Subnet, subnet_id)
            if subnet is not None:
                subnet.last_scan_error = str(exc)[:255]
                db.session.commit()
        except Exception:  # pragma: no cover - defensive
            db.session.rollback()
        return {'status': 'error', 'error': str(exc)}
    finally:
        with _running_lock:
            _running.discard(subnet_id)


def scan_in_background(app, subnet_id: int) -> bool:
    """Start a sweep on a thread. False if one is already running."""
    # Claim before starting so status reads "running" from the moment we return
    if not _claim(subnet_id):
        return False

    def worker():
        with app.app_context():
            scan_subnet(subnet_id, _claimed=True)
            db.session.remove()

    threading.Thread(target=worker, name=f'ipam-scan-{subnet_id}', daemon=True).start()
    return True


def due_subnet_ids(now: Optional[datetime] = None):
    now = now or datetime.utcnow()
    due = []
    for subnet in Subnet.query.filter_by(scan_enabled=True).all():
        interval = timedelta(minutes=subnet.scan_interval_minutes or 60)
        if subnet.last_scan_at is None or subnet.last_scan_at + interval <= now:
            if scan_eligibility(subnet.cidr) is None and not is_running(subnet.id):
                due.append(subnet.id)
    return due


class ScanScheduler:
    """Checks once a minute for subnets whose sweep is due; runs them in turn."""

    def __init__(self, app, tick_seconds: int = 60):
        self.app = app
        self.tick = max(5, tick_seconds)
        self._stop = threading.Event()

    def run_due(self):
        with self.app.app_context():
            for subnet_id in due_subnet_ids():
                if self._stop.is_set():
                    break
                scan_subnet(subnet_id)
            db.session.remove()

    def run(self):
        # Small delay so startup (migrations, first requests) isn't competing
        self._stop.wait(10)
        while not self._stop.is_set():
            try:
                self.run_due()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"IPAM scheduler tick failed: {exc}")
            self._stop.wait(self.tick)

    def stop(self):
        self._stop.set()
