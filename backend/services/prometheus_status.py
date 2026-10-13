"""
Live device status from a Prometheus server.

For every enabled monitor we compute the same target string the exporter
uses, then look for a matching series in Prometheus:

  1. probe_success (blackbox-style probes: icmp/http/https/dns), else
  2. up (regular exporters).

A series matches a monitor by, in order of preference:
  * inventory_device_id + monitor_type labels (set by our exports/SD)
  * device_name + monitor_type labels (older file exports)
  * instance == target

`probe_success` wins over `up` for the same key, because for blackbox jobs
`up` only says the blackbox exporter answered, not whether the probe passed.
"""
import base64
import json
import logging
import os
import ssl
import threading
import time
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from services.prometheus_service import iter_enabled_targets

logger = logging.getLogger(__name__)

STATE_UP = 'up'
STATE_DOWN = 'down'
STATE_DEGRADED = 'degraded'
STATE_UNKNOWN = 'unknown'
STATE_DISABLED = 'disabled'

_cache_lock = threading.Lock()
_cache: Dict[str, object] = {'at': 0.0, 'series': None, 'error': None}


def get_settings() -> dict:
    return {
        'url': (os.environ.get('PROMETHEUS_URL') or '').rstrip('/'),
        'bearer_token': os.environ.get('PROMETHEUS_BEARER_TOKEN') or None,
        'username': os.environ.get('PROMETHEUS_USERNAME') or None,
        'password': os.environ.get('PROMETHEUS_PASSWORD') or None,
        'verify_tls': (os.environ.get('PROMETHEUS_VERIFY_TLS', 'true').lower()
                       not in ('false', '0', 'no', 'off')),
        'cache_seconds': max(0, int(os.environ.get('PROMETHEUS_STATUS_CACHE_SECONDS', '15') or 15)),
        'timeout': float(os.environ.get('PROMETHEUS_TIMEOUT_SECONDS', '5') or 5),
    }


def is_configured() -> bool:
    return bool(get_settings()['url'])


def _query(expr: str, settings: dict) -> List[dict]:
    """Run an instant query and return the result vector."""
    url = f"{settings['url']}/api/v1/query?{urlencode({'query': expr})}"
    req = Request(url, headers={'Accept': 'application/json'})
    if settings['bearer_token']:
        req.add_header('Authorization', f"Bearer {settings['bearer_token']}")
    elif settings['username']:
        raw = f"{settings['username']}:{settings['password'] or ''}".encode()
        req.add_header('Authorization', 'Basic ' + base64.b64encode(raw).decode())

    context = None
    if url.startswith('https://') and not settings['verify_tls']:
        context = ssl._create_unverified_context()  # noqa: S323 - explicit opt-out

    with urlopen(req, timeout=settings['timeout'], context=context) as resp:  # noqa: S310
        body = json.loads(resp.read().decode('utf-8'))
    if body.get('status') != 'success':
        raise RuntimeError(body.get('error') or 'Prometheus query failed')
    return body.get('data', {}).get('result', [])


def fetch_series(force: bool = False) -> Tuple[Optional[dict], Optional[str]]:
    """
    Return ({'up': [...], 'probe_success': [...]}, error) using a short cache
    so a page full of devices doesn't hammer Prometheus.
    """
    settings = get_settings()
    if not settings['url']:
        return None, 'PROMETHEUS_URL is not configured'

    with _cache_lock:
        fresh = time.time() - float(_cache['at']) < settings['cache_seconds']
        if fresh and not force and (_cache['series'] is not None or _cache['error']):
            return _cache['series'], _cache['error']

    series, error = None, None
    try:
        series = {
            'up': _query('up', settings),
            'probe_success': _query('probe_success', settings),
        }
    except HTTPError as exc:
        error = f"Prometheus returned HTTP {exc.code}"
    except URLError as exc:
        error = f"Cannot reach Prometheus: {exc.reason}"
    except Exception as exc:  # malformed JSON, timeouts, etc.
        error = f"Prometheus query failed: {exc}"
    if error:
        logger.warning(error)

    with _cache_lock:
        _cache.update({'at': time.time(), 'series': series, 'error': error})
    return series, error


def clear_cache():
    with _cache_lock:
        _cache.update({'at': 0.0, 'series': None, 'error': None})


def _index_series(results: List[dict]) -> Dict[tuple, dict]:
    """Index a result vector by every key we can match on."""
    index: Dict[tuple, dict] = {}
    for item in results or []:
        metric = item.get('metric', {})
        try:
            value = float(item.get('value', [0, 'nan'])[1])
        except (TypeError, ValueError):
            continue
        entry = {
            'value': value,
            'job': metric.get('job'),
            'instance': metric.get('instance'),
            'timestamp': item.get('value', [None])[0],
        }
        mtype = metric.get('monitor_type')
        keys = []
        if metric.get('inventory_device_id') and mtype:
            keys.append(('id', metric['inventory_device_id'], mtype))
        if metric.get('device_name') and mtype:
            keys.append(('name', metric['device_name'], mtype))
        if metric.get('instance'):
            keys.append(('instance', metric['instance']))
        for key in keys:
            # If several series share a key, a failing one should win so
            # problems are never hidden.
            if key not in index or value < index[key]['value']:
                index[key] = entry
    return index


def _lookup(indexes: List[Dict[tuple, dict]], device, monitor, target):
    keys = [
        ('id', str(device.id), monitor.monitor_type),
        ('name', device.name, monitor.monitor_type),
        ('instance', target),
    ]
    for key in keys:
        for metric_name, index in indexes:
            if key in index:
                return metric_name, index[key]
    return None, None


def compute_status(devices, series: dict) -> Dict[int, dict]:
    """Per-device status from fetched series."""
    probe_index = _index_series(series.get('probe_success', []))
    up_index = _index_series(series.get('up', []))
    indexes = [('probe_success', probe_index), ('up', up_index)]

    by_device: Dict[int, dict] = {}
    for device in devices:
        by_device[device.id] = {
            'device_id': device.id,
            'state': STATE_DISABLED if not device.monitoring_enabled else STATE_UNKNOWN,
            'monitors': [],
        }

    for device, monitor, _group, target in iter_enabled_targets(devices):
        if not device.monitoring_enabled:
            continue
        metric_name, hit = _lookup(indexes, device, monitor, target)
        if hit is None:
            state = STATE_UNKNOWN
        else:
            state = STATE_UP if hit['value'] >= 1 else STATE_DOWN
        by_device[device.id]['monitors'].append({
            'monitor_id': monitor.id,
            'monitor_type': monitor.monitor_type,
            'target': target,
            'state': state,
            'metric': metric_name,
            'job': hit['job'] if hit else None,
        })

    for status in by_device.values():
        if status['state'] == STATE_DISABLED:
            continue
        states = {m['state'] for m in status['monitors'] if m['state'] != STATE_UNKNOWN}
        if not states:
            status['state'] = STATE_UNKNOWN
        elif states == {STATE_UP}:
            status['state'] = STATE_UP
        elif states == {STATE_DOWN}:
            status['state'] = STATE_DOWN
        else:
            status['state'] = STATE_DEGRADED
    return by_device


def summarize(status_by_device: Dict[int, dict]) -> dict:
    counts = {STATE_UP: 0, STATE_DOWN: 0, STATE_DEGRADED: 0, STATE_UNKNOWN: 0, STATE_DISABLED: 0}
    for status in status_by_device.values():
        counts[status['state']] += 1
    return counts
