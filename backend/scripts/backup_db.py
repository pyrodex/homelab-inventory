#!/usr/bin/env python3
"""
Database backup script for Homelab Inventory
Creates timestamped backups with retention policy
"""
import os
import sys
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_path():
    """Get database path from environment or use default"""
    db_path = os.environ.get('DATABASE_PATH', '/app/data/homelab.db')
    return Path(db_path)


def get_backup_directory():
    """Get backup directory from environment or use default"""
    backup_dir = os.environ.get('BACKUP_DIRECTORY', '/app/data/backups')
    return Path(backup_dir)


def create_backup(db_path, backup_dir):
    """Create a timestamped backup of the database"""
    try:
        # Ensure backup directory exists
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'homelab_backup_{timestamp}.db'
        backup_path = backup_dir / backup_filename
        
        # Verify source database exists
        if not db_path.exists():
            logger.error(f"Database not found at {db_path}")
            return False
        
        # Create backup using SQLite backup API for consistency
        logger.info(f"Creating backup from {db_path} to {backup_path}")
        
        source_conn = sqlite3.connect(str(db_path))
        backup_conn = sqlite3.connect(str(backup_path))
        
        source_conn.backup(backup_conn)
        
        source_conn.close()
        backup_conn.close()
        
        # Verify backup was created
        if backup_path.exists():
            backup_size = backup_path.stat().st_size
            logger.info(f"Backup created successfully: {backup_path} ({backup_size} bytes)")
            return True
        else:
            logger.error("Backup file was not created")
            return False
            
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return False


def cleanup_old_backups(backup_dir, retention_days=30):
    """Remove backups older than retention period"""
    try:
        if not backup_dir.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        
        for backup_file in backup_dir.glob('homelab_backup_*.db'):
            try:
                # Extract timestamp from filename
                timestamp_str = backup_file.stem.replace('homelab_backup_', '')
                file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                
                if file_date < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {backup_file.name}")
            except (ValueError, Exception) as e:
                logger.warning(f"Could not parse or delete {backup_file.name}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old backup(s)")
            
    except Exception as e:
        logger.error(f"Error cleaning up old backups: {e}")


def get_backup_stats(backup_dir):
    """Get statistics about backups"""
    if not backup_dir.exists():
        return {
            'count': 0,
            'total_size': 0,
            'oldest': None,
            'newest': None
        }
    
    backups = list(backup_dir.glob('homelab_backup_*.db'))
    if not backups:
        return {
            'count': 0,
            'total_size': 0,
            'oldest': None,
            'newest': None
        }
    
    total_size = sum(f.stat().st_size for f in backups)
    timestamps = []
    
    for backup_file in backups:
        try:
            timestamp_str = backup_file.stem.replace('homelab_backup_', '')
            file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            timestamps.append((file_date, backup_file))
        except ValueError:
            continue
    
    if timestamps:
        timestamps.sort()
        oldest = timestamps[0][1].name
        newest = timestamps[-1][1].name
    else:
        oldest = newest = None
    
    return {
        'count': len(backups),
        'total_size': total_size,
        'oldest': oldest,
        'newest': newest
    }


def main():
    """Main backup function"""
    db_path = get_database_path()
    backup_dir = get_backup_directory()
    retention_days = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
    
    logger.info("Starting database backup process")
    logger.info(f"Database: {db_path}")
    logger.info(f"Backup directory: {backup_dir}")
    logger.info(f"Retention: {retention_days} days")
    
    # Create backup
    success = create_backup(db_path, backup_dir)
    
    if success:
        # Cleanup old backups
        cleanup_old_backups(backup_dir, retention_days)
        
        # Print stats
        stats = get_backup_stats(backup_dir)
        logger.info(f"Backup statistics: {stats['count']} backups, "
                   f"{stats['total_size'] / 1024 / 1024:.2f} MB total")
        
        sys.exit(0)
    else:
        logger.error("Backup failed")
        sys.exit(1)


if __name__ == '__main__':
    main()

