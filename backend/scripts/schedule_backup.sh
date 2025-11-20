#!/bin/bash
# Backup scheduling script for Homelab Inventory
# This script can be run via cron or systemd timer

# Example cron entry (daily at 2 AM):
# 0 2 * * * /app/scripts/schedule_backup.sh

# Example systemd timer (daily at 2 AM):
# [Unit]
# Description=Homelab Inventory Database Backup
# 
# [Timer]
# OnCalendar=daily
# OnCalendar=02:00
# Persistent=true
# 
# [Install]
# WantedBy=timers.target

python3 /app/scripts/backup_db.py

