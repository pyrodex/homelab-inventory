"""
Test configuration.

Point the app at a throwaway SQLite file *before* `app` is imported.
Flask-SQLAlchemy creates its engine during init_app(), so overriding
SQLALCHEMY_DATABASE_URI inside a fixture afterwards has no effect, and the
fixtures' drop_all() would otherwise wipe whatever DATABASE_PATH points at
(by default ./homelab.db).
"""
import os
import tempfile

_TEST_DIR = tempfile.mkdtemp(prefix='homelab-inventory-tests-')
os.environ['DATABASE_PATH'] = os.path.join(_TEST_DIR, 'test.db')
os.environ['PROMETHEUS_EXPORT_PATH'] = os.path.join(_TEST_DIR, 'prometheus_targets')
os.environ.pop('BACKUP_DIRECTORY', None)
# Deliver webhooks inline so tests are deterministic and no background
# thread outlives a test's tables
os.environ['WEBHOOKS_SYNCHRONOUS'] = 'true'
