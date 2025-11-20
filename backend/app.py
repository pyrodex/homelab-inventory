"""
Main application entry point
"""
from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
import logging
import os
import sys

from config import config
from models import db
from exceptions import HomelabInventoryError
from routes.devices import register_device_routes
from routes.monitors import register_monitor_routes
from routes.admin import register_admin_routes
from routes.stats import register_stats_routes
from routes.prometheus import register_prometheus_routes
from routes.bulk import register_bulk_routes
from routes.search import register_search_routes
from routes.health import register_health_routes

# Initialize Flask app
app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_ENV', 'production')
app.config.from_object(config[config_name])

# Initialize app with config (validates environment)
try:
    config[config_name].init_app(app)
except ValueError as e:
    logging.error(f"Configuration error: {e}")
    logging.error("Application startup aborted due to configuration errors")
    sys.exit(1)

# Initialize logging
logging.basicConfig(
    level=getattr(logging, app.config.get('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize database
db.init_app(app)

# Enable foreign key constraints in SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Initialize migrations
migrate = Migrate(app, db)

# CORS Configuration
allowed_origins = app.config.get('CORS_ORIGINS', ['*'])
if '*' in allowed_origins:
    CORS(app)
else:
    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

# Rate Limiting Configuration
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=app.config.get('RATELIMIT_DEFAULT_LIMITS', ["200 per hour", "50 per minute"]),
    storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://')
)

# Rate limit error handler
@app.errorhandler(429)
def ratelimit_handler(e):
    from utils.response import rate_limit_response
    return rate_limit_response(f'Too many requests. Please try again later. Limit: {e.description}')

# Custom error handlers
@app.errorhandler(HomelabInventoryError)
def handle_homelab_error(error):
    """Handle custom application errors"""
    from utils.response import error_response
    return error_response(
        error.message,
        status_code=error.status_code,
        error_code=getattr(error, 'error_code', None)
    )

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    from utils.response import not_found_response
    return not_found_response()

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logging.error(f"Internal server error: {error}", exc_info=True)
    from utils.response import server_error_response
    return server_error_response("An internal error occurred")

# Register routes
register_device_routes(app, limiter)
register_monitor_routes(app, limiter)
register_admin_routes(app, limiter)
register_stats_routes(app)
register_prometheus_routes(app, limiter)
register_bulk_routes(app, limiter)
register_search_routes(app, limiter)
register_health_routes(app, limiter)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

# Initialize database
def init_database():
    """Initialize database and check/update schema"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        if existing_tables:
            logging.info(f"Found existing database with tables: {existing_tables}")
            
            required_tables = ['vendor', 'model', 'location', 'device', 'monitor']
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                logging.info(f"Missing tables detected: {missing_tables}")
                logging.info("Creating missing tables...")
                db.create_all()
                logging.info("Missing tables created successfully!")
            else:
                logging.info("All required tables exist.")
                logging.info("Checking for schema updates...")
                
                # Check Device table for new columns
                device_columns = [col['name'] for col in inspector.get_columns('device')]
                
                if 'location_id' not in device_columns:
                    logging.info("Adding location_id column to device table...")
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE device ADD COLUMN location_id INTEGER'))
                        conn.commit()
                    logging.info("location_id column added successfully!")
                
                if 'poe_standards' not in device_columns:
                    logging.info("Adding poe_standards column to device table...")
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE device ADD COLUMN poe_standards VARCHAR(200)'))
                        conn.commit()
                    logging.info("poe_standards column added successfully!")
                
                logging.info("Schema check complete.")
        else:
            logging.info("No existing database found. Creating new database...")
            db.create_all()
            logging.info("Database created successfully!")

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))
