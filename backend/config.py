"""
Application configuration
"""
import os
from pathlib import Path


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
        pass


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

