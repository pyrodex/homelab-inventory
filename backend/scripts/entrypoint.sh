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
    echo "${BACKUP_SCHEDULE} python /app/scripts/backup_db.py >> /proc/1/fd/1 2>&1"
} | crontab -

# Start cron daemon
cron

# Execute the main application command
exec "$@"

