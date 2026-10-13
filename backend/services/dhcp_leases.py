"""
dnsmasq lease import.

dnsmasq's lease file (usually /var/lib/misc/dnsmasq.leases) is one lease per
line, space separated:

  IPv4:  <expiry> <mac> <ip> <hostname|*> <client-id|*>
  IPv6:  duid <server-duid>                       (header line)
         <expiry> <iaid> <ipv6> <hostname|*> <client-duid|*>

<expiry> is a Unix timestamp, or 0 for an infinite lease.

Each import is a snapshot for its *source* (a file path or an upload label):
leases from that source that are missing from the new snapshot are marked
inactive, while leases from other sources are left alone.
"""
import ipaddress
import logging
import os
import re
import threading
from datetime import datetime, timezone
from typing import List, Optional

from models import IpObservation, db

logger = logging.getLogger(__name__)

MAC_RE = re.compile(r'^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$', re.I)
MAX_LEASE_BYTES = 2 * 1024 * 1024
MAX_SOURCE_LEN = 255


class LeaseParseError(ValueError):
    pass


def _clean(value: str) -> Optional[str]:
    return None if value in ('*', '') else value


def parse_dnsmasq_leases(text: str) -> dict:
    """
    Parse lease text. Returns {'leases': [...], 'skipped': [(line_no, reason), ...]}.
    Each lease: {ip, mac, hostname, client_id, expires (aware datetime | None)}.
    """
    leases, skipped = [], []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if parts[0] == 'duid':
            continue
        if len(parts) < 4:
            skipped.append((line_no, 'too few fields'))
            continue
        expiry_s, second, ip_s, hostname = parts[:4]
        client_id = parts[4] if len(parts) > 4 else '*'
        try:
            expiry = int(expiry_s)
        except ValueError:
            skipped.append((line_no, 'expiry is not a number'))
            continue
        try:
            ip = ipaddress.ip_address(ip_s)
        except ValueError:
            skipped.append((line_no, f'invalid IP {ip_s!r}'))
            continue
        mac = second.lower().replace('-', ':') if ip.version == 4 and MAC_RE.match(second) else None
        if ip.version == 4 and mac is None:
            skipped.append((line_no, f'invalid MAC {second!r}'))
            continue
        leases.append({
            'ip': str(ip),
            'mac': mac,
            'hostname': _clean(hostname),
            'client_id': _clean(client_id),
            'expires': None if expiry == 0 else datetime.fromtimestamp(expiry, tz=timezone.utc),
        })
    return {'leases': leases, 'skipped': skipped}


def import_leases(text: str, source: str, now: Optional[datetime] = None) -> dict:
    """Apply a lease snapshot for `source`. Caller commits nothing; we commit."""
    if len(text.encode('utf-8', errors='ignore')) > MAX_LEASE_BYTES:
        raise LeaseParseError(f'Lease data is larger than {MAX_LEASE_BYTES // 1024} KiB')
    source = (source or 'upload').strip()[:MAX_SOURCE_LEN] or 'upload'
    now = now or datetime.now(timezone.utc)
    parsed = parse_dnsmasq_leases(text)

    # Last line wins if an IP appears twice in one snapshot
    by_ip = {}
    for lease in parsed['leases']:
        by_ip[lease['ip']] = lease

    rows = {o.ip: o for o in IpObservation.query.filter(IpObservation.ip.in_(list(by_ip))).all()} if by_ip else {}
    naive_now = now.astimezone(timezone.utc).replace(tzinfo=None)
    active = expired = 0
    for ip, lease in by_ip.items():
        row = rows.get(ip)
        if row is None:
            row = IpObservation(ip=ip)
            db.session.add(row)
        expires = lease['expires'].astimezone(timezone.utc).replace(tzinfo=None) if lease['expires'] else None
        is_active = expires is None or expires > naive_now
        row.dhcp_source = source
        row.dhcp_hostname = lease['hostname']
        row.dhcp_client_id = lease['client_id']
        row.dhcp_expires = expires
        row.dhcp_active = is_active
        row.dhcp_last_seen = naive_now
        if lease['mac']:
            row.mac = lease['mac']
        if lease['hostname']:
            row.hostname = lease['hostname']
        active += int(is_active)
        expired += int(not is_active)

    # Leases this source reported before but not now are gone
    stale_q = IpObservation.query.filter(IpObservation.dhcp_source == source, IpObservation.dhcp_active.is_(True))
    if by_ip:
        stale_q = stale_q.filter(~IpObservation.ip.in_(list(by_ip)))
    released = 0
    for row in stale_q.all():
        row.dhcp_active = False
        released += 1

    db.session.commit()
    return {
        'source': source,
        'leases': len(by_ip),
        'active': active,
        'expired': expired,
        'released': released,
        'skipped': [{'line': n, 'reason': r} for n, r in parsed['skipped']],
    }


def expire_leases(now: Optional[datetime] = None) -> int:
    """Flip leases whose expiry has passed to inactive."""
    naive_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(tzinfo=None)
    rows = IpObservation.query.filter(
        IpObservation.dhcp_active.is_(True),
        IpObservation.dhcp_expires.isnot(None),
        IpObservation.dhcp_expires <= naive_now,
    ).all()
    for row in rows:
        row.dhcp_active = False
    if rows:
        db.session.commit()
    return len(rows)


def configured_lease_paths() -> List[str]:
    raw = os.environ.get('DNSMASQ_LEASES_PATH', '')
    return [p.strip() for p in raw.split(',') if p.strip()]


class LeaseFileWatcher:
    """Re-imports configured lease files when their mtime changes."""

    def __init__(self, app, interval_seconds: int = 60):
        self.app = app
        self.interval = max(5, interval_seconds)
        self._mtimes = {}
        self._stop = threading.Event()
        self.last_results = {}

    def poll_once(self):
        with self.app.app_context():
            for path in configured_lease_paths():
                try:
                    mtime = os.path.getmtime(path)
                except OSError as exc:
                    self.last_results[path] = {'error': f'Cannot read lease file: {exc.strerror}'}
                    continue
                if self._mtimes.get(path) == mtime:
                    continue
                try:
                    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                        result = import_leases(fh.read(), source=f'file:{path}')
                    self._mtimes[path] = mtime
                    self.last_results[path] = result
                    logger.info(f"Imported {result['leases']} leases from {path}")
                except Exception as exc:
                    db.session.rollback()
                    self.last_results[path] = {'error': str(exc)}
                    logger.warning(f"Lease import from {path} failed: {exc}")
            try:
                expire_leases()
            except Exception as exc:  # pragma: no cover - defensive
                db.session.rollback()
                logger.warning(f"Lease expiry sweep failed: {exc}")

    def run(self):
        while not self._stop.is_set():
            self.poll_once()
            self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()
