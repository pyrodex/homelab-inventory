# Database Backup Guide

The Homelab Inventory application includes automated database backup functionality to protect your data.

## Backup Script

The backup script (`backend/scripts/backup_db.py`) creates timestamped SQLite database backups with automatic cleanup of old backups.

### Features

- **Timestamped Backups**: Each backup includes a timestamp in the filename (e.g., `homelab_backup_20241120_143022.db`)
- **Automatic Cleanup**: Removes backups older than the retention period (default: 30 days)
- **SQLite Backup API**: Uses SQLite's native backup API for consistency
- **Statistics**: Reports backup count, total size, oldest and newest backups

### Environment Variables

- `DATABASE_PATH`: Path to the database file (default: `/app/data/homelab.db`)
- `BACKUP_DIRECTORY`: Directory for backups (default: `/app/data/backups`)
- `BACKUP_RETENTION_DAYS`: Number of days to keep backups (default: `30`)
- `BACKUP_SCHEDULE`: Cron schedule for automatic backups (default: `0 2 * * *` - daily at 2 AM)

### Manual Backup

Run the backup script manually:

```bash
# Inside Docker container
docker exec homelab-inventory-backend python3 /app/scripts/backup_db.py

# Or if running locally
python3 backend/scripts/backup_db.py
```

### Automated Scheduling

#### Automatic Daily Backups (Default - Docker Compose)

**Backups are automatically configured when using Docker Compose!** The container includes a cron daemon that runs daily backups automatically.

Configure via environment variables in your `docker-compose.yaml`:

```yaml
services:
  backend:
    environment:
      - BACKUP_DIRECTORY=/app/data/backups
      - BACKUP_RETENTION_DAYS=30
      - BACKUP_SCHEDULE=0 2 * * *  # Daily at 2 AM (cron format)
```

**Cron Schedule Format:**
- `0 2 * * *` - Daily at 2:00 AM (default)
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 0` - Weekly on Sunday at midnight
- `*/30 * * * *` - Every 30 minutes

The backup runs automatically in the background. Check logs with:
```bash
docker compose logs backend | grep -i backup
```

#### Alternative: Manual Cron Setup (Inside Container)

If you need to manually add a cron job:
```bash
docker exec -it homelab-inventory-backend bash
echo "0 2 * * * python3 /app/scripts/backup_db.py" | crontab -
```

#### Alternative: Using Systemd Timer (Host System)

Create `/etc/systemd/system/homelab-backup.service`:
```ini
[Unit]
Description=Homelab Inventory Database Backup
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/docker exec homelab-inventory-backend python3 /app/scripts/backup_db.py
```

Create `/etc/systemd/system/homelab-backup.timer`:
```ini
[Unit]
Description=Daily backup for Homelab Inventory
Requires=homelab-backup.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable homelab-backup.timer
sudo systemctl start homelab-backup.timer
```

#### Alternative: External Cron Service (Not Needed)

**Note:** This is no longer necessary as backups are automatic. The main backend container handles backups internally via cron.

### Restoring from Backup

1. **Stop the application:**
   ```bash
   docker compose stop backend
   ```

2. **Backup current database (safety):**
   ```bash
   cp data/homelab.db data/homelab.db.current
   ```

3. **Restore from backup:**
   ```bash
   cp data/backups/homelab_backup_YYYYMMDD_HHMMSS.db data/homelab.db
   ```

4. **Set correct permissions:**
   ```bash
   chmod 644 data/homelab.db
   ```

5. **Start the application:**
   ```bash
   docker compose start backend
   ```

### Backup Verification

The backup script logs:
- Backup creation success/failure
- Backup file size
- Cleanup operations
- Statistics (count, total size, oldest/newest)

Check logs:
```bash
docker compose logs backend | grep -i backup
```

### Best Practices

1. **Regular Backups**: Schedule daily backups during low-traffic hours
2. **Offsite Storage**: Copy backups to external storage or cloud storage
3. **Test Restores**: Periodically test restoring from backups
4. **Monitor Disk Space**: Ensure backup directory has sufficient space
5. **Retention Policy**: Adjust `BACKUP_RETENTION_DAYS` based on your needs

### Troubleshooting

**Backup fails:**
- Check database path is correct
- Verify write permissions on backup directory
- Check disk space availability
- Review application logs

**Backups not being cleaned up:**
- Verify `BACKUP_RETENTION_DAYS` is set correctly
- Check backup directory permissions
- Review script logs for errors

**Cannot restore backup:**
- Ensure application is stopped before restoring
- Verify backup file is not corrupted
- Check file permissions after restore

