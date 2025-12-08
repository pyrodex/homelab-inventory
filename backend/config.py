"""
Application configuration
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_environment():
    """Validate required environment variables and paths"""
    errors = []
    warnings = []
    
    # Check database path
    db_path = os.environ.get('DATABASE_PATH', 'homelab.db')
    db_dir = Path(db_path).parent
    if not db_dir.exists():
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
        except Exception as e:
            errors.append(f"Cannot create database directory {db_dir}: {e}")
    
    # Check Prometheus export path
    prom_path = os.environ.get('PROMETHEUS_EXPORT_PATH', '/app/prometheus_targets')
    prom_dir = Path(prom_path)
    if not prom_dir.exists():
        try:
            prom_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created Prometheus export directory: {prom_dir}")
        except Exception as e:
            warnings.append(f"Cannot create Prometheus export directory {prom_dir}: {e}")
    
    # Check backup directory if specified
    backup_dir = os.environ.get('BACKUP_DIRECTORY')
    if backup_dir:
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            try:
                backup_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created backup directory: {backup_path}")
            except Exception as e:
                warnings.append(f"Cannot create backup directory {backup_path}: {e}")
    
    # Security warnings
    if os.environ.get('FLASK_ENV') == 'production':
        if os.environ.get('SECRET_KEY') == 'dev-secret-key-change-in-production':
            warnings.append("SECRET_KEY is using default value. Change it in production!")
        
        if os.environ.get('CORS_ORIGINS') == '*':
            warnings.append("CORS_ORIGINS is set to '*' (all origins). Consider restricting in production.")
    
    # Log warnings
    for warning in warnings:
        logger.warning(warning)
    
    # Raise errors if any
    if errors:
        error_msg = "Environment validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if warnings:
        logger.info(f"Environment validation completed with {len(warnings)} warning(s)")


class Config:
    """Base configuration"""
    # Database
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'homelab.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Prometheus Export
    PROMETHEUS_EXPORT_PATH = os.environ.get('PROMETHEUS_EXPORT_PATH', '/app/prometheus_targets')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT_LIMITS = ["200 per hour", "50 per minute"]
    
    # Flask
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        # Validate environment on app initialization
        try:
            validate_environment()
        except ValueError as e:
            # In production, we might want to fail fast
            # In development, we can be more lenient
            if app.config.get('FLASK_ENV') == 'production':
                raise
            else:
                logger.warning(f"Environment validation failed: {e}")
        # Warn if rate limiting storage is non-persistent in production
        if app.config.get('FLASK_ENV') == 'production' and app.config.get('RATELIMIT_STORAGE_URL', '').startswith('memory://'):
            logger.warning("RATELIMIT_STORAGE_URL is memory:// in production; use Redis/Memcached for durability.")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'INFO'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}

