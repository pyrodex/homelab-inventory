#!/bin/bash
set -e

# Default backup schedule: daily at 2 AM
BACKUP_SCHEDULE="${BACKUP_SCHEDULE:-0 2 * * *}"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIRECTORY:-/app/data/backups}"

# Create cron job for backup with environment variables
# Cron jobs don't inherit environment, so we need to set them explicitly
{
    echo "DATABASE_PATH=${DATABASE_PATH:-/app/data/homelab.db}"
    echo "BACKUP_DIRECTORY=${BACKUP_DIRECTORY:-/app/data/backups}"
    echo "BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}"
    echo "${BACKUP_SCHEDULE} /usr/local/bin/python3 /app/scripts/backup_db.py >> /proc/1/fd/1 2>&1"
} | crontab -

# Start cron daemon
cron

# Drop to non-root for the application process (default: app:app -> UID/GID 1000)
RUN_AS_USER="${RUN_AS_USER:-app}"
RUN_AS_GROUP="${RUN_AS_GROUP:-app}"

if command -v gosu >/dev/null 2>&1; then
  exec gosu "${RUN_AS_USER}:${RUN_AS_GROUP}" "$@"
else
  # Fallback: run without dropping privileges (should not happen in our image)
  exec "$@"
fi

