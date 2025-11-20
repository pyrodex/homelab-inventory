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
- **Mobile-Optimized**: Fully optimized for iOS and mobile devices with touch-friendly controls
- **Search & Filter**: Powerful search across all device fields and filter by device type
- **View Modes**: Switch between full detail view and condensed list view
- **Real-time Stats**: Dashboard showing total devices, monitoring status, and device type breakdowns
- **Device Cloning**: Quickly duplicate devices with similar configurations

### Network & Power Management
- **Network Segmentation**: Assign devices to specific networks (LAN, IoT, DMZ, GUEST, or ALL)
- **Interface Types**: Track network interface types from 10Base-T to 400G QSFP-DD, including Wi-Fi standards
- **PoE Support**: Track Power over Ethernet (PoE) powered devices and standards (802.3af/at/bt)
- **Serial Number Tracking**: Maintain serial number records for warranty and asset management

### Administration
- **Vendor Management**: Add, edit, and remove vendors with automatic model relationship handling
- **Model Management**: Associate models with vendors and track device counts
- **Location Management**: Create and organize locations with device count tracking
- **SQLite Web Interface**: Optional SQLite-web container for direct database access

## 🏗️ Architecture

### Technology Stack

**Frontend:**
- React 18.2 with modern hooks
- Vite for fast development and optimized builds
- Tailwind CSS for responsive, utility-first styling
- Lucide React for beautiful icons
- Mobile-optimized with iOS-specific enhancements

**Backend:**
- Flask 3.0 RESTful API
- SQLAlchemy ORM for database operations
- SQLite database (lightweight, file-based)
- Flask-CORS for cross-origin resource sharing
- PyYAML for Prometheus configuration generation

**Infrastructure:**
- Docker & Docker Compose for containerization
- Nginx for serving the frontend
- Multi-stage builds for optimized image sizes
- Volume mounts for persistent data storage

### Project Structure

```
homelab-inventory/
├── backend/
│   ├── app.py              # Flask application and API routes
│   ├── Dockerfile          # Backend container definition
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   │   ├── admin/      # Administration components
│   │   │   ├── common/     # Shared components
│   │   │   └── devices/    # Device-related components
│   │   ├── constants/      # Application constants
│   │   ├── hooks/          # Custom React hooks
│   │   ├── services/       # API service layer
│   │   ├── utils/          # Utility functions
│   │   ├── App.jsx         # Main application component
│   │   ├── index.css       # Global styles
│   │   └── main.jsx        # Application entry point
│   ├── Dockerfile          # Frontend container definition
│   ├── nginx.conf          # Nginx configuration
│   ├── package.json        # Node.js dependencies
│   ├── tailwind.config.cjs # Tailwind CSS configuration
│   └── vite.config.js     # Vite configuration
├── data/                   # Database storage (created on first run)
├── targets/                # Prometheus export directory (created on first run)
├── build.sh                # Build and deployment script
├── docker-compose.yaml.example  # Docker Compose example
└── README.md               # This file
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

#### Docker Compose

Edit `docker-compose.yaml` to customize:

- **Ports**: Change `5000:80` for frontend port mapping
- **Volumes**: Adjust `./data` and `./targets` paths as needed
- **Database Path**: Modify `DATABASE_PATH` environment variable
- **Prometheus Export Path**: Modify `PROMETHEUS_EXPORT_PATH` environment variable

### Database

The application uses SQLite by default, stored in the `data/` directory. The database is automatically created on first run. To use a different database:

1. Set the `DATABASE_PATH` environment variable
2. Ensure the directory exists and is writable
3. Restart the application

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
   - **Models**: Add models associated with vendors
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

- **Search**: Use the search box to find devices by name, IP, function, vendor, model, location, serial number, or monitor type
- **Filter**: Select a device type from the dropdown to filter devices
- **View Modes**: Toggle between full detail view and condensed list view

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
   python app.py
   ```

2. **Frontend Development:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Code Structure

- **Backend**: Follows Flask best practices with RESTful API design
- **Frontend**: Component-based React architecture with service layer for API calls
- **Styling**: Tailwind CSS utility classes with custom CSS for iOS optimizations

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

Currently, the project doesn't include automated tests. Consider adding:
- Unit tests for backend API endpoints
- Integration tests for database operations
- Frontend component tests with React Testing Library
- E2E tests with Playwright or Cypress

## 🐳 Docker Deployment

### Production Deployment

1. **Clone and configure:**
   ```bash
   git clone <repository-url>
   cd homelab-inventory
   cp docker-compose.yaml.example docker-compose.yaml
   ```

2. **Review and customize `docker-compose.yaml`** as needed

3. **Build and deploy:**
   ```bash
   ./build.sh
   ```

4. **Check logs:**
   ```bash
   docker compose logs -f
   ```

### Updating the Application

1. **Pull latest changes:**
   ```bash
   git pull
   ```

2. **Rebuild and restart:**
   ```bash
   ./build.sh
   ```

### Backup

The database is stored in the `data/` directory. To backup:

```bash
# Backup database
cp data/homelab.db data/homelab.db.backup

# Or use Docker
docker exec homelab-inventory-backend cp /app/data/homelab.db /app/data/homelab.db.backup
```

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
  - Prometheus export: 10 requests/minute
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
- Check backend logs: `docker compose logs backend`
- Ensure CORS is properly configured

**Prometheus export fails:**
- Verify the export directory exists and is writable
- Check `PROMETHEUS_EXPORT_PATH` environment variable
- Review backend logs for specific errors

**Port already in use:**
- Change the port mapping in `docker-compose.yaml`
- Or stop the service using the port

### Getting Help

- Check the logs: `docker compose logs`
- Review the [Issues](../../issues) page
- Create a new issue with:
  - Description of the problem
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment details (OS, Docker version, etc.)

## 🎯 Roadmap

Potential future enhancements:

- [ ] User authentication and authorization
- [ ] Multi-user support with role-based access
- [ ] Device templates and bulk import/export
- [ ] Advanced search and filtering options
- [ ] Device history and change tracking
- [ ] Integration with other monitoring systems (Grafana, etc.)
- [ ] API rate limiting and security enhancements
- [ ] Automated device discovery
- [ ] Health check endpoints
- [ ] Dark mode theme
- [ ] Internationalization (i18n) support

## 🙏 Acknowledgments

- Built with [React](https://react.dev/) and [Flask](https://flask.palletsprojects.com/)
- Icons provided by [Lucide](https://lucide.dev/)
- Styled with [Tailwind CSS](https://tailwindcss.com/)
- Database management with [SQLAlchemy](https://www.sqlalchemy.org/)

---

**Made with ❤️ for the homelab community**

