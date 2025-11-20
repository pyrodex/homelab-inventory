# Homelab Inventory

A modern, web-based inventory management system for homelab infrastructure with integrated Prometheus monitoring configuration export. Built with React and Flask, this application helps you track, organize, and monitor all your homelab devices in one place.

![License](https://img.shields.io/badge/license-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![React](https://img.shields.io/badge/react-18.2-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0-green.svg)

## ✨ Features

### Device Management
- **Comprehensive Device Tracking**: Track physical and virtual servers, network switches, wireless access points, IP cameras, IoT devices, and more
- **Rich Device Information**: Store device names, IP addresses, functions, vendors, models, locations, serial numbers, and network assignments
- **Multiple Device Types**: Support for 13+ device types including Linux/FreeBSD servers, network equipment, cameras, and specialized devices
- **Location Organization**: Organize devices by physical or logical locations (e.g., Data Center, Office, Rack 1)
- **Vendor & Model Management**: Maintain a catalog of vendors and models for consistent device tracking

### Monitoring Integration
- **Prometheus Export**: Automatically generate Prometheus target configurations from your inventory
- **Multiple Monitor Types**: Support for Node Exporter, SmartProm, SNMP, ICMP, HTTP/HTTPS, DNS, IPMI, NUT, and Docker monitoring
- **Flexible Monitoring**: Enable or disable monitoring per device, with support for multiple monitors per device
- **Export Options**: Write Prometheus configs directly to disk or download as a ZIP archive
- **Organized Exports**: Automatically organize Prometheus targets by monitor type and device category

### User Interface
- **Modern React UI**: Beautiful, responsive interface built with React and Tailwind CSS
- **Mobile-Optimized**: Fully optimized for iOS and mobile devices with touch-friendly controls, safe area support, and optimized touch targets
- **Advanced Search**: Powerful multi-field search with expandable filters (vendor, model, location, monitoring status, PoE, IP address)
- **Search & Filter**: Real-time search across device fields with debouncing and filter by device type
- **View Modes**: Switch between full detail view and condensed list view
- **Real-time Stats**: Dashboard showing total devices, monitoring status, and device type breakdowns
- **Device Cloning**: Quickly duplicate devices with similar configurations
- **Bulk Operations**: Import/export devices in JSON or CSV format, bulk delete multiple devices

### Network & Power Management
- **Network Segmentation**: Assign devices to specific networks (LAN, IoT, DMZ, GUEST, or ALL)
- **Interface Types**: Track network interface types from 10Base-T to 400G QSFP-DD, including Wi-Fi standards
- **PoE Support**: Track Power over Ethernet (PoE) powered devices and standards (802.3af/at/bt)
- **Serial Number Tracking**: Maintain serial number records for warranty and asset management

### Administration
- **Vendor Management**: Add, edit, and remove vendors with automatic model relationship handling
- **Model Management**: Associate models with vendors, filter models by vendor, and track device counts
- **Location Management**: Create and organize locations with device count tracking
- **SQLite Web Interface**: Optional SQLite-web container for direct database access

### Bulk Operations
- **Import Devices**: Import multiple devices from JSON array or CSV file with validation and error reporting
- **Export Devices**: Export all devices or filtered by type in JSON or CSV format
- **Bulk Delete**: Delete multiple devices at once by ID (up to 100 at a time)
- **Error Handling**: Detailed import/export results showing successful and failed operations

### Advanced Search & Filtering
- **Multi-field Search**: Search across name, IP address, function, serial number, networks, interface types, and PoE standards
- **Advanced Filters**: Filter by device type, vendor, model, location, monitoring status, PoE powered status, and IP address presence
- **Filter Chips**: Visual representation of active filters with easy removal
- **Real-time Results**: Instant search results with debouncing for optimal performance

### Monitoring & Observability
- **Health Checks**: Basic and detailed health endpoints for monitoring application status
- **System Metrics**: CPU, memory, and disk usage metrics (requires psutil)
- **Database Statistics**: Device counts and database connectivity status

## 🏗️ Architecture

### Technology Stack

**Frontend:**
- React 18.2 with modern hooks
- Vite for fast development and optimized builds
- Tailwind CSS for responsive, utility-first styling
- Lucide React for beautiful icons
- Mobile-optimized with iOS-specific enhancements

**Backend:**
- Flask 3.0 RESTful API with modular blueprint architecture
- SQLAlchemy ORM for database operations
- Flask-Migrate for database schema versioning
- SQLite database (lightweight, file-based) with optimized indexes
- Flask-CORS for cross-origin resource sharing
- Flask-Limiter for API rate limiting
- Marshmallow for input validation and sanitization
- PyYAML for Prometheus configuration generation
- psutil for system metrics (optional)
- pytest for testing framework
- Automated database backup system
- Standardized API response format
- Environment validation on startup

**Infrastructure:**
- Docker & Docker Compose for containerization
- Nginx for serving the frontend
- Multi-stage builds for optimized image sizes
- Volume mounts for persistent data storage

### Project Structure

```
homelab-inventory/
├── backend/
│   ├── app.py              # Flask application entry point
│   ├── config.py           # Configuration classes (Development/Production/Testing)
│   ├── models.py            # SQLAlchemy database models
│   ├── validators.py        # Marshmallow schemas for input validation
│   ├── exceptions.py        # Custom exception classes
│   ├── routes/              # API route blueprints
│   │   ├── devices.py       # Device CRUD operations
│   │   ├── monitors.py      # Monitor management
│   │   ├── admin.py         # Vendor/Model/Location management
│   │   ├── stats.py         # Statistics endpoints
│   │   ├── prometheus.py    # Prometheus export
│   │   ├── bulk.py          # Bulk operations (import/export/delete)
│   │   ├── search.py        # Advanced search endpoints
│   │   └── health.py        # Health check endpoints
│   ├── services/            # Business logic services
│   │   └── prometheus_service.py  # Prometheus export logic
│   ├── tests/               # Test suite
│   │   ├── test_models.py   # Model tests
│   │   └── test_api.py     # API endpoint tests
│   ├── migrations/           # Database migration scripts (Flask-Migrate)
│   ├── pytest.ini           # Pytest configuration
│   ├── Dockerfile           # Backend container definition
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   │   ├── admin/       # Administration components
│   │   │   ├── bulk/        # Bulk operations modal
│   │   │   ├── common/      # Shared components (ErrorAlert, etc.)
│   │   │   ├── devices/     # Device-related components
│   │   │   └── search/      # Advanced search component
│   │   ├── constants/       # Application constants (device types, etc.)
│   │   ├── services/        # API service layer
│   │   ├── utils/           # Utility functions
│   │   ├── App.jsx          # Main application component
│   │   ├── index.css        # Global styles (with iOS optimizations)
│   │   └── main.jsx         # Application entry point
│   ├── Dockerfile           # Frontend container definition
│   ├── nginx.conf           # Nginx configuration
│   ├── package.json         # Node.js dependencies
│   ├── tailwind.config.cjs  # Tailwind CSS configuration
│   └── vite.config.js       # Vite configuration
├── data/                    # Database storage (created on first run)
├── targets/                 # Prometheus export directory (created on first run)
├── build.sh                 # Build and deployment script
├── docker-compose.yaml.example  # Docker Compose example
└── README.md                # This file
```

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (version 20.10 or later)
- **Docker Compose** (version 2.0 or later)
- **Git** (for cloning the repository)

For local development:
- **Node.js** (version 18 or later) and npm
- **Python** (version 3.13 or later) and pip

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd homelab-inventory
   ```

2. **Set up Docker Compose:**
   ```bash
   cp docker-compose.yaml.example docker-compose.yaml
   ```

3. **Build and start the containers:**
   ```bash
   ./build.sh
   ```
   
   Or manually:
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

4. **Access the application:**
   - **Web UI**: http://localhost:5000
   - **SQLite Web Interface** (optional): http://localhost:5001

### Manual Setup

#### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables:**
   ```bash
   export FLASK_ENV=development
   export DATABASE_PATH=./homelab.db
   export PROMETHEUS_EXPORT_PATH=./prometheus_targets
   ```

5. **Run the Flask application:**
   ```bash
   python app.py
   ```

   The backend will be available at http://localhost:5000

#### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at http://localhost:5173 (or the port Vite assigns)

4. **Build for production:**
   ```bash
   npm run build
   ```

## ⚙️ Configuration

### Environment Variables

#### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment (development/production) | `production` |
| `DATABASE_PATH` | Path to SQLite database file | `/app/data/homelab.db` |
| `PROMETHEUS_EXPORT_PATH` | Directory for Prometheus config exports | `/app/prometheus_targets` |
| `CORS_ORIGINS` | Comma-separated list of allowed CORS origins (use `*` for all) | `*` |
| `BACKUP_DIRECTORY` | Directory for database backups | `/app/data/backups` |
| `BACKUP_RETENTION_DAYS` | Number of days to keep backups before cleanup | `30` |
| `SECRET_KEY` | Flask secret key (change in production!) | `dev-secret-key-change-in-production` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

#### Docker Compose

Edit `docker-compose.yaml` to customize:

- **Ports**: Change `5000:80` for frontend port mapping
- **Volumes**: Adjust `./data` and `./targets` paths as needed
- **Database Path**: Modify `DATABASE_PATH` environment variable
- **Prometheus Export Path**: Modify `PROMETHEUS_EXPORT_PATH` environment variable

### Database

The application uses SQLite by default, stored in the `data/` directory. The database is automatically created on first run.

**Database Migrations:**
- The project uses Flask-Migrate for schema versioning
- Migrations are stored in `backend/migrations/`
- To initialize migrations: `flask db init` (if needed)
- To create a migration: `flask db migrate -m "description"`
- To apply migrations: `flask db upgrade`

**Performance Optimizations:**
- Database indexes on frequently queried fields (name, device_type, ip_address, monitoring_enabled, etc.)
- Composite indexes for common query patterns
- Foreign key indexes for faster joins

**Database Backups:**
- Automated backup script included (`backend/scripts/backup_db.py`)
- Creates timestamped backups with automatic cleanup
- Configurable retention period (default: 30 days)
- Automatic daily backups via cron (configured in Docker container)
- Uses SQLite's native backup API for consistency
- Manual backup: `docker exec homelab-inventory-backend python3 /app/scripts/backup_db.py`
- Backups stored in `data/backups/` directory
- See [Database Backup & Restore](#-database-backup--restore) section below for detailed instructions

**Environment Validation:**
- Application validates environment variables and paths on startup
- Automatically creates required directories if they don't exist
- Provides security warnings in production (default SECRET_KEY, open CORS)
- Fails fast in production if critical configuration is missing

**To use a different database:**
1. Set the `DATABASE_PATH` environment variable
2. Ensure the directory exists and is writable
3. Run migrations if needed
4. Restart the application

### Prometheus Integration

The application exports Prometheus target configurations in YAML format. Configure your Prometheus instance to scrape from the export directory:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'linux_node_exporter'
    file_sd_configs:
      - files:
        - '/path/to/prometheus_targets/linux_node_exporter/*.yaml'
```

## 📖 Usage Guide

### Adding Devices

1. Click the **"Add Device"** button in the header
2. Fill in required fields:
   - Device Name
   - Device Type
   - Address (IP address, hostname, or URL)
   - Function
   - Vendor (create new if needed)
   - Model (create new if needed)
   - Location (create new if needed)
   - Serial Number
3. Configure optional settings:
   - Networks (LAN, IoT, DMZ, GUEST, or ALL)
   - Interface Types
   - PoE Standards (if applicable)
   - PoE Powered checkbox
   - Monitoring Enabled checkbox
4. Add monitors (e.g., Node Exporter on port 9100)
5. Click **"Create Device"**

### Managing Vendors, Models, and Locations

1. Click the **"Admin"** button in the header
2. Navigate between tabs:
   - **Vendors**: Add, edit, or remove vendors
   - **Models**: 
     - Select a vendor from the dropdown to filter models (or "All Vendors" to see all)
     - Add models associated with the selected vendor
     - Models list automatically filters when a vendor is selected
   - **Locations**: Add, edit, or remove locations
3. Use inline editing for quick updates

### Exporting Prometheus Configuration

1. **Write to Disk**: Click **"Write Prometheus Files"** to generate configs in the export directory
2. **Download ZIP**: Click **"Download Config"** to download a ZIP archive of Prometheus targets

The export organizes targets by monitor type:
- `linux_node_exporter/` - Linux servers with Node Exporter
- `freebsd_node_exporter/` - FreeBSD servers with Node Exporter
- `snmp/` - SNMP-monitored devices
- `icmp/` - ICMP-only devices
- And more...

### Searching and Filtering

- **Quick Search**: Use the search box to find devices by name, IP, function, serial number, networks, interface types, or PoE standards
- **Advanced Search**: Click the "Filters" button to expand advanced filtering options:
  - Filter by device type, vendor, model, or location
  - Filter by monitoring status (enabled/disabled)
  - Filter by PoE powered status
  - Filter by IP address presence
  - Combine multiple filters for precise results
- **Filter Chips**: Active filters are displayed as removable chips above the results
- **Device Type Filter**: Select a device type from the dropdown to filter devices
- **View Modes**: Toggle between full detail view and condensed list view

### Bulk Operations

- **Bulk Import**: 
  - Import devices from JSON array or CSV file
  - CSV format: name, device_type, ip_address, function, vendor, model, location, serial_number, networks, interface_type, poe_powered, poe_standards, monitoring_enabled
  - JSON format: Array of device objects matching the API schema
  - Results show successful imports and failed items with error details
  
- **Bulk Export**:
  - Export all devices or filter by device type
  - Choose JSON or CSV format
  - Files are automatically downloaded with descriptive filenames
  
- **Bulk Delete**:
  - Delete multiple devices by entering comma-separated IDs
  - Maximum 100 devices per operation
  - Confirmation dialog prevents accidental deletions

### Device Actions

- **Edit**: Click the edit icon to modify device details
- **Clone**: Click the clone icon to duplicate a device (useful for similar devices)
- **Toggle Monitoring**: Click the check/X icon to enable/disable monitoring
- **Delete**: Click the trash icon to remove a device (with confirmation)

## 🔌 API Documentation

### Base URL

All API endpoints are prefixed with `/api`

### Endpoints

#### Devices

- `GET /api/devices` - Get all devices (optional `?type=<device_type>` filter)
- `GET /api/devices/<id>` - Get device by ID
- `POST /api/devices` - Create new device
- `PUT /api/devices/<id>` - Update device
- `DELETE /api/devices/<id>` - Delete device

#### Monitors

- `POST /api/devices/<device_id>/monitors` - Add monitor to device
- `PUT /api/monitors/<id>` - Update monitor
- `DELETE /api/monitors/<id>` - Delete monitor

#### Vendors

- `GET /api/vendors` - Get all vendors
- `POST /api/vendors` - Create vendor
- `PUT /api/vendors/<id>` - Update vendor
- `DELETE /api/vendors/<id>` - Delete vendor

#### Models

- `GET /api/models` - Get all models (optional `?vendor_id=<id>` filter)
- `POST /api/models` - Create model
- `PUT /api/models/<id>` - Update model
- `DELETE /api/models/<id>` - Delete model

#### Locations

- `GET /api/locations` - Get all locations
- `POST /api/locations` - Create location
- `PUT /api/locations/<id>` - Update location
- `DELETE /api/locations/<id>` - Delete location

#### Statistics

- `GET /api/stats` - Get dashboard statistics

#### Prometheus Export

- `GET /api/prometheus/export?mode=write` - Write Prometheus configs to disk
- `GET /api/prometheus/export?mode=download` - Download Prometheus configs as ZIP

#### Bulk Operations

- `POST /api/bulk/devices/import` - Import devices from JSON array or CSV file
  - JSON: Send array of device objects in request body
  - CSV: Send multipart/form-data with `file` field
- `GET /api/bulk/devices/export?format=json&type=<device_type>` - Export devices
  - `format`: `json` or `csv`
  - `type`: Optional device type filter
- `POST /api/bulk/devices/delete` - Bulk delete devices
  - Body: `{ "device_ids": [1, 2, 3, ...] }`
  - Maximum 100 devices per request

#### Advanced Search

- `GET /api/search/devices` - Advanced search with multiple filters
  - Query parameters:
    - `q`: Search term (searches across multiple fields)
    - `type`: Device type filter
    - `vendor_id`: Filter by vendor ID
    - `model_id`: Filter by model ID
    - `location_id`: Filter by location ID
    - `monitoring_enabled`: `true` or `false`
    - `poe_powered`: `true` or `false`
    - `has_ip`: `true` or `false`
  - Returns: `{ "results": [...], "count": N, "filters_applied": {...} }`

#### Health Checks

- `GET /api/health` - Basic health check
  - Returns: `{ "status": "healthy", "timestamp": "...", "service": "..." }`
- `GET /api/health/detailed` - Detailed health check with system metrics
  - Returns: Database status, system metrics (CPU, memory, disk), device counts
  - Requires psutil for system metrics (gracefully degrades if unavailable)

### API Response Format

All API responses follow a standardized format:

**Success Response:**
```json
{
  "success": true,
  "data": {...},
  "message": "Device created successfully"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Validation error",
  "details": {
    "name": ["Missing data for required field."],
    "device_type": ["Invalid device type."]
  },
  "error_code": "VALIDATION_ERROR"
}
```

### Example API Request

```bash
# Create a device
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Web Server 01",
    "device_type": "linux_server_physical",
    "ip_address": "192.168.1.10",
    "function": "Web Server",
    "vendor_id": 1,
    "model_id": 1,
    "location_id": 1,
    "serial_number": "SN123456",
    "networks": "LAN",
    "monitoring_enabled": true
  }'

# Response:
# {
#   "success": true,
#   "data": {
#     "id": 1,
#     "name": "Web Server 01",
#     ...
#   },
#   "message": "Device created successfully"
# }
```

## 🛠️ Development

### Setting Up Development Environment

1. **Backend Development:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   export FLASK_ENV=development
   export DATABASE_PATH=./homelab.db
   export PROMETHEUS_EXPORT_PATH=./prometheus_targets
   
   # Initialize database migrations (first time only)
   flask db upgrade
   
   # Run the application
   python app.py
   ```

2. **Frontend Development:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Code Structure

- **Backend**: Modular Flask architecture with blueprints, services, and models separation
  - Routes organized by domain (devices, monitors, admin, bulk, search, health)
  - Business logic in services layer
  - Database models in separate module
  - Input validation via Marshmallow schemas
  - Custom exception handling
- **Frontend**: Component-based React architecture with service layer for API calls
  - Components organized by feature (devices, admin, bulk, search, common)
  - Centralized API service layer
  - Utility functions for common operations
- **Styling**: Tailwind CSS utility classes with custom CSS for iOS optimizations
  - Mobile-first responsive design
  - Touch-friendly controls (44px minimum)
  - Safe area support for notched devices

### Building for Production

**Frontend:**
```bash
cd frontend
npm run build
```

**Docker:**
```bash
docker compose build --no-cache
```

### Testing

The project includes a basic test structure using pytest:

**Backend Tests:**
```bash
cd backend
pytest
```

**Test Structure:**
- `tests/test_models.py` - Unit tests for database models
- `tests/test_api.py` - Integration tests for API endpoints

**Adding Tests:**
- Follow pytest conventions
- Use pytest-flask fixtures for Flask app context
- Test both success and error cases
- Mock external dependencies when appropriate

**Future Testing Enhancements:**
- Frontend component tests with React Testing Library
- E2E tests with Playwright or Cypress
- Performance and load testing

## 🐳 Docker Deployment

### Production Deployment

1. **Clone and configure:**
   ```bash
   git clone <repository-url>
   cd homelab-inventory
   cp docker-compose.yaml.example docker-compose.yaml
   ```

2. **Review and customize `docker-compose.yaml`** as needed
   - Set `SECRET_KEY` environment variable (important for production!)
   - Configure `CORS_ORIGINS` to restrict allowed origins
   - Adjust backup retention days if needed

3. **Build and deploy:**
   ```bash
   ./build.sh
   ```

4. **Check health status:**
   ```bash
   docker compose ps
   # Should show "healthy" status for backend and frontend
   ```

5. **Check logs:**
   ```bash
   docker compose logs -f
   ```

### Health Checks

The Docker Compose configuration includes health checks for both services:
- **Backend**: Checks `/api/health` endpoint every 30 seconds
- **Frontend**: Verifies web server is responding
- Services wait for backend to be healthy before starting
- Unhealthy containers are automatically restarted

### Updating the Application

1. **Pull latest changes:**
   ```bash
   git pull
   ```

2. **Rebuild and restart:**
   ```bash
   ./build.sh
   ```

## 💾 Database Backup & Restore

The Homelab Inventory application includes comprehensive automated database backup functionality to protect your data.

> **Note:** For a standalone backup reference document, see [BACKUP_README.md](BACKUP_README.md).

### Backup Features

- **Timestamped Backups**: Each backup includes a timestamp in the filename (e.g., `homelab_backup_20241120_143022.db`)
- **Automatic Cleanup**: Removes backups older than the retention period (default: 30 days)
- **SQLite Backup API**: Uses SQLite's native backup API for consistency and reliability
- **Statistics**: Reports backup count, total size, oldest and newest backups
- **Zero Configuration**: Automatic daily backups enabled by default in Docker Compose setup

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BACKUP_DIRECTORY` | Directory for backups | `/app/data/backups` |
| `BACKUP_RETENTION_DAYS` | Number of days to keep backups | `30` |
| `BACKUP_SCHEDULE` | Cron schedule for automatic backups | `0 2 * * *` (daily at 2 AM) |

### Automated Backups

**Automatic Daily Backups (Docker Compose):**

Backups are automatically configured when using Docker Compose! The container includes a cron daemon that runs daily backups automatically.

Configure via environment variables in your `docker-compose.yaml`:

```yaml
services:
  backend:
    environment:
      - BACKUP_DIRECTORY=/app/data/backups
      - BACKUP_RETENTION_DAYS=30
      - BACKUP_SCHEDULE=0 2 * * *  # Daily at 2 AM (cron format)
```

**Cron Schedule Format Examples:**
- `0 2 * * *` - Daily at 2:00 AM (default)
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 0` - Weekly on Sunday at midnight
- `*/30 * * * *` - Every 30 minutes

The backup runs automatically in the background. Check logs with:
```bash
docker compose logs backend | grep -i backup
```

### Manual Backup

Run the backup script manually:

```bash
# Inside Docker container
docker exec homelab-inventory-backend python3 /app/scripts/backup_db.py

# Or if running locally
python3 backend/scripts/backup_db.py
```

**Alternative Manual Methods:**
```bash
# Copy database directly
cp data/homelab.db data/homelab.db.backup

# Or use Docker
docker exec homelab-inventory-backend cp /app/data/homelab.db /app/data/homelab.db.backup
```

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

### Backup Best Practices

1. **Regular Backups**: Schedule daily backups during low-traffic hours
2. **Offsite Storage**: Copy backups to external storage or cloud storage
3. **Test Restores**: Periodically test restoring from backups
4. **Monitor Disk Space**: Ensure backup directory has sufficient space
5. **Retention Policy**: Adjust `BACKUP_RETENTION_DAYS` based on your needs

### Alternative Scheduling Methods

#### Using Systemd Timer (Host System)

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

### Backup Troubleshooting

**Backup fails:**
- Check database path is correct
- Verify write permissions on backup directory
- Check disk space availability
- Review application logs: `docker compose logs backend | grep -i backup`

**Backups not being cleaned up:**
- Verify `BACKUP_RETENTION_DAYS` is set correctly
- Check backup directory permissions
- Review script logs for errors

**Cannot restore backup:**
- Ensure application is stopped before restoring
- Verify backup file is not corrupted
- Check file permissions after restore

**Backup Location:**
Backups are stored in `data/backups/` directory with timestamped filenames (e.g., `homelab_backup_20241120_143022.db`).

### Data Persistence

Ensure volumes are properly mounted:
- `./data:/app/data` - Database storage
- `./targets:/app/prometheus_targets` - Prometheus export directory

## 🔒 Security Features

### Implemented Security Measures

- **Input Validation & Sanitization**: All API endpoints use Marshmallow schemas to validate and sanitize input data
  - IP addresses and hostnames are validated
  - Port numbers are validated (1-65535)
  - String fields are sanitized to prevent injection attacks
  - Device types, monitor types, and other enums are validated against allowed values

- **Rate Limiting**: Flask-Limiter is configured to prevent abuse
  - Default limits: 200 requests/hour, 50 requests/minute per IP
  - Write operations (POST/PUT/DELETE): 20-30 requests/minute
  - Bulk operations: 5-10 requests/minute (more restrictive)
  - Prometheus export: 10 requests/minute
  - Search operations: 60 requests/minute
  - Rate limit errors return HTTP 429 with descriptive messages

- **CORS Configuration**: Configurable CORS origins via environment variable
  - Development: Set `CORS_ORIGINS=*` to allow all origins
  - Production: Set `CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com` to restrict

- **Error Handling**: Comprehensive error handling with proper HTTP status codes
  - Validation errors return 400 with detailed messages
  - Database errors are logged but don't expose sensitive information
  - Rate limit errors return 429

### Security Recommendations

- **Database**: SQLite database should be stored in a secure location with proper file permissions
- **Network**: Use a reverse proxy (nginx, Traefik) with SSL/TLS for production
- **Authentication**: Consider adding authentication for production use (not currently implemented)
- **Rate Limiting Storage**: For production with multiple instances, use Redis instead of in-memory storage
- **Secrets Management**: Use environment variables or secrets manager for sensitive configuration

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow existing code style
- Add comments for complex logic
- Update documentation as needed
- Test your changes thoroughly

## 📝 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🐛 Troubleshooting

### Common Issues

**Database is read-only:**
- Check file permissions on the database file and directory
- Ensure the Docker volume is mounted correctly
- Verify the user running the container has write permissions

**Frontend not connecting to backend:**
- Verify both containers are running: `docker compose ps`
- Check container health status: `docker compose ps` (should show "healthy")
- Check backend logs: `docker compose logs backend`
- Ensure CORS is properly configured
- Verify backend health endpoint: `curl http://localhost:5000/api/health`

**Prometheus export fails:**
- Verify the export directory exists and is writable
- Check `PROMETHEUS_EXPORT_PATH` environment variable
- Review backend logs for specific errors

**Port already in use:**
- Change the port mapping in `docker-compose.yaml`
- Or stop the service using the port

**Backup fails:**
- Verify `BACKUP_DIRECTORY` exists and is writable
- Check disk space availability
- Review backup script logs: `docker compose logs backend | grep -i backup`
- Ensure database file exists and is accessible
- See [Database Backup & Restore](#-database-backup--restore) section for detailed troubleshooting

**Environment validation errors:**
- Check application logs for specific validation errors
- Verify required directories exist or can be created
- Review environment variable values
- In production, ensure `SECRET_KEY` is set (not using default)

**API returns unexpected format:**
- All endpoints now return standardized format with `success` field
- Check for `data` field in success responses
- Check for `error` and `details` fields in error responses
- Update client code if needed to handle new format

### Getting Help

- Check the logs: `docker compose logs`
- Review the [Issues](../../issues) page
- Create a new issue with:
  - Description of the problem
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment details (OS, Docker version, etc.)

## 🎯 Roadmap

### Completed Features ✅

- [x] Input validation and sanitization (Marshmallow schemas)
- [x] API rate limiting (Flask-Limiter)
- [x] CORS configuration
- [x] Modular backend architecture (blueprints)
- [x] Database migrations (Flask-Migrate)
- [x] Comprehensive error handling
- [x] Basic test structure (pytest)
- [x] Bulk import/export operations
- [x] Advanced search and filtering
- [x] Health check endpoints
- [x] Performance optimizations (database indexes)
- [x] iOS mobile optimizations
- [x] Database backup automation
- [x] Standardized API responses
- [x] Enhanced UI error handling with field-specific validation
- [x] Docker health checks
- [x] Environment variable validation

### Future Enhancements

- [ ] User authentication and authorization
- [ ] Multi-user support with role-based access
- [ ] Device templates and presets
- [ ] Device history and change tracking
- [ ] Integration with other monitoring systems (Grafana, etc.)
- [ ] Automated device discovery
- [ ] Dark mode theme
- [ ] Internationalization (i18n) support
- [ ] Caching layer (Redis) for improved performance
- [ ] API documentation (OpenAPI/Swagger)
- [ ] WebSocket support for real-time updates

## 🙏 Acknowledgments

- Built with [React](https://react.dev/) and [Flask](https://flask.palletsprojects.com/)
- Icons provided by [Lucide](https://lucide.dev/)
- Styled with [Tailwind CSS](https://tailwindcss.com/)
- Database management with [SQLAlchemy](https://www.sqlalchemy.org/)

---

**Made with ❤️ for the homelab community**

