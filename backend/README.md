# Homelab Inventory backend

Flask API behind the Homelab Inventory UI. It stores data in SQLite through SQLAlchemy and runs a few lightweight background workers in-process.

User-facing documentation lives in the [main README](../README.md): configuration, the API reference, and upgrade notes. This file is for working on the backend itself.

## Run locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export FLASK_ENV=development DATABASE_PATH=./homelab.db PROMETHEUS_EXPORT_PATH=./prometheus_targets
python app.py   # http://localhost:5000
```

On startup the backend:
1. validates paths (`config.py`)
2. applies migrations (`AUTO_MIGRATE`, on by default)
3. creates core tables on a brand-new database
4. starts the background workers

`python app.py` is also what the Docker image runs, after `scripts/entrypoint.sh` installs the backup cron job.

Background workers (not started when the app is imported by tests or tools):
- **Ping-sweep scheduler** (`services/ipam_scan.py`) and **dnsmasq lease watcher** (`services/dhcp_leases.py`). Disable both with `IPAM_BACKGROUND_WORKERS=false`.
- **Webhook dispatcher** (`services/webhooks.py`). It listens for committed `DeviceHistory` rows and delivers asynchronously; `WEBHOOKS_SYNCHRONOUS=true` delivers inline, which the tests use.

## Layout

| Path | What's there |
|---|---|
| `app.py` | App setup, CORS, rate limiter, error handlers, blueprint registration, startup |
| `config.py` | Environment configuration and startup validation |
| `models.py` | SQLAlchemy models: devices, monitors, vendors, models, locations, history, tags, links, subnets, IP observations, webhooks |
| `validators.py` | Marshmallow schemas for every write |
| `routes/` | One blueprint per area: `devices`, `monitors`, `admin`, `stats`, `search`, `bulk`, `discovery`, `health`, `links` (tags and relationships), `subnets` (IPAM and DHCP), `onboarding` (IPAM add to monitoring), `prometheus`, `exports`, `webhooks` |
| `services/` | Logic behind the routes: `ipam` (address index and utilization), `ipam_scan` (sweeps), `netprobe` (ping and PTR), `dhcp_leases`, `onboarding` (probes and suggestions), `prometheus_service` (targets and SD), `prometheus_status` (live status), `exports` (Ansible and NetBox), `webhooks` |
| `utils/` | History diffs (`history.py`), tag parsing (`tags.py`), response envelope helpers (`response.py`) |
| `migrations/` | Alembic migrations (Flask-Migrate) |
| `scripts/` | `entrypoint.sh`, `backup_db.py`, `ansible_inventory.py` (also served by `/api/export/ansible/script`) |
| `tests/` | pytest suite |

## Conventions

- **Validation:** every write goes through a Marshmallow schema in `validators.py`. Validation errors return `400` with `details`.
- **History:** device changes write a `DeviceHistory` row in the same transaction. Webhooks fire from it after commit, so anything that changes a device should record history.
- **Rate limits:** register them in each module's `register_*_routes(app, limiter)`. Routes without one get the defaults in `config.py`.
- **Network access:** code that touches the network goes through `services/netprobe.py` or `services/onboarding.py`, so tests can stub it.

## Migrations

```bash
flask db migrate -m "describe the change"   # then review the generated file
flask db upgrade
flask db downgrade
```

Keep migrations additive, and safe to run on a database that already has the change. Use plain `op.add_column` for new columns rather than batch mode, which broke fresh installs before. `tests/test_migrations.py` boots the app in production mode on an empty database to catch problems.

## Tests

```bash
pytest
```

`tests/conftest.py` sets `DATABASE_PATH` to a temporary file before the app is imported, so the suite never touches a real database.
- **Sweeps:** tests stub `netprobe.ping` and `netprobe.reverse_lookup`.
- **Port probes and webhooks:** tests use real listeners on `127.0.0.1`.
