# Homelab Inventory Backend

## Overview
Flask-based API for managing devices, monitors, stats, and bulk operations. Recent additions:
- Device change history via `device_history` table and `GET /api/devices/<id>/history`.
- Optional automatic migrations on startup (enabled by default).

## Setup
1) Install dependencies (python 3.11+ recommended):
```bash
pip install -r requirements.txt
```

2) Environment variables (common):
- `FLASK_ENV` (`development`|`production`)
- `DATABASE_PATH` (default `homelab.db`)
- `AUTO_MIGRATE` (default `true`; set to `false` to skip auto migrations)
- `CORS_ORIGINS`, `RATELIMIT_STORAGE_URL`, `SECRET_KEY`, etc. (see `config.py`)

3) Run server:
```bash
FLASK_ENV=development flask run --host 0.0.0.0 --port 5000
```
The app entrypoint is `backend/app.py`.

## Database & Migrations
- Models live in `models.py`. Change history uses `DeviceHistory`.
- Alembic/Flask-Migrate is configured; migrations reside in `migrations/versions/`.
- Auto-migration on startup: controlled by `AUTO_MIGRATE` env (default on). In production, a failed migration stops startup to avoid stale schema.
- Manual commands:
```bash
flask db migrate -m "message"
flask db upgrade
flask db downgrade
```

## Key Endpoints (summary)
- Devices CRUD: `/api/devices`
- Device history: `/api/devices/<id>/history`
- Monitors: `/api/devices/<id>/monitors`, `/api/monitors/<id>`
- Admin (vendors/models/locations): `/api/vendors`, `/api/models`, `/api/locations`
- Bulk import/export/delete: `/api/bulk/devices/*`
- Stats: `/api/stats`
- Health: `/api/health`, `/api/health/detailed`

## Frontend Notes
Frontend is in `../frontend/`. Dark mode with system auto option is available. The frontend consumes the history endpoint for per-device timelines.

