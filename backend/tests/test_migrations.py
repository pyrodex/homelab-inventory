"""
Startup / migration regression tests.

On a brand-new install the app runs Alembic migrations *before* creating the
core tables, and in production a failed migration exits the process. These
tests boot the app in a subprocess exactly like the container does.
"""
import os
import sqlite3
import subprocess
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_TABLES = {
    'device', 'vendor', 'model', 'location', 'monitor', 'device_history', 'subnet',
    'tag', 'device_tag', 'device_link', 'ip_observation', 'webhook', 'webhook_delivery', 'alembic_version',
}


def _boot(db_path, tmp_path):
    env = dict(os.environ,
               DATABASE_PATH=str(db_path),
               PROMETHEUS_EXPORT_PATH=str(tmp_path / 'prom'),
               FLASK_ENV='production',
               SECRET_KEY='test-secret',
               IPAM_BACKGROUND_WORKERS='false')
    return subprocess.run([sys.executable, '-c', 'import app'], cwd=BACKEND, env=env,
                          capture_output=True, text=True, timeout=120)


def _head():
    versions = os.path.join(BACKEND, 'migrations', 'versions')
    revs, downs = set(), set()
    for name in os.listdir(versions):
        if not name.endswith('.py'):
            continue
        text = open(os.path.join(versions, name)).read()
        for line in text.splitlines():
            if line.startswith('revision = '):
                revs.add(line.split('=', 1)[1].strip().strip('"\''))
            elif line.startswith('down_revision = '):
                downs.add(line.split('=', 1)[1].strip().strip('"\''))
    heads = revs - downs
    assert len(heads) == 1, f"expected one migration head, found {heads}"
    return heads.pop()


def test_fresh_install_boots_in_production(tmp_path):
    db_path = tmp_path / 'fresh.db'
    result = _boot(db_path, tmp_path)
    assert result.returncode == 0, result.stderr[-2000:]
    assert 'Automatic migration failed' not in result.stderr
    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
    assert EXPECTED_TABLES <= tables
    assert conn.execute('select version_num from alembic_version').fetchone()[0] == _head()
    subnet_cols = {r[1] for r in conn.execute('pragma table_info(subnet)')}
    assert {'scan_enabled', 'scan_interval_minutes', 'last_scan_at'} <= subnet_cols
    obs_cols = {r[1] for r in conn.execute('pragma table_info(ip_observation)')}
    assert {'ptr_hostname', 'ptr_checked_at'} <= obs_cols


def test_reboot_is_idempotent(tmp_path):
    db_path = tmp_path / 'again.db'
    assert _boot(db_path, tmp_path).returncode == 0
    second = _boot(db_path, tmp_path)
    assert second.returncode == 0, second.stderr[-2000:]
    assert 'Automatic migration failed' not in second.stderr
