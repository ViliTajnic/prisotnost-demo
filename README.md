# TimeTracker Pro - Comprehensive Time Management System

A full-featured workforce time management and scheduling application built with Python Flask and Oracle 23ai Free database.

## Features

### Core Functionality
- **Staff Scheduling** - Interactive calendar-based scheduling with drag-and-drop interface
- **Time Clock System** - Cloud-based time tracking with mobile and web support
- **Attendance Management** - Comprehensive tracking with break time monitoring
- **Absence Tracking** - Leave request workflow with automated approvals
- **Overtime Tracking** - Automatic calculations with real-time alerts
- **Geofencing** - GPS-based location verification for clock-ins
- **Project Time Tracking** - Task-based time allocation and profitability analysis
- **Reporting & Analytics** - Customizable reports with data visualization
- **Access Control** - Role-based permissions with audit logging

### Technical Features
- **Responsive Design** - Mobile-friendly interface using Bootstrap 5
- **Real-time Updates** - Live status tracking and notifications
- **RESTful API** - Complete API with JWT authentication
- **Database Integration** - Oracle 23ai Free with optimized schema
- **Docker Support** - Containerized deployment with docker-compose
- **Security** - Input validation, CSRF protection, secure authentication

## Technology Stack

### Backend
- **Python 3.11** - Core application language
- **Flask** - Web framework with extensions
- **SQLAlchemy** - Database ORM
- **Oracle 23ai Free** - Database system
- **JWT** - Authentication tokens
- **Gunicorn** - WSGI server

### Frontend
- **HTML5/CSS3/JavaScript** - Core web technologies
- **Bootstrap 5** - Responsive UI framework
- **Chart.js** - Data visualization
- **FullCalendar.js** - Interactive calendar
- **Font Awesome** - Icons

### Infrastructure
- **Docker** - Containerization
- **Nginx** - Reverse proxy and load balancer
- **Redis** - Session management and caching
- **Prometheus/Grafana** - Monitoring (optional)

## Installation

### Prerequisites
- **Python 3.8+**
- **Docker Desktop** (for Oracle Database 23ai)
- **Git**

### Step 1: Clone the Repository

```bash
git clone https://github.com/ViliTajnic/prisotnost-demo.git
cd prisotnost-demo
```

### Step 2: Set Up Oracle Database 23ai

Start Oracle Database using Docker:

```bash
# Pull and run Oracle Database 23ai Free
docker run -d \
  --name oracle-23ai-free \
  -p 1521:1521 \
  -e ORACLE_PWD=OraclePassword123 \
  container-registry.oracle.com/database/free:latest

# Wait for database to fully initialize (this may take 5-10 minutes)
docker logs -f oracle-23ai-free
```

Wait until you see the message: `DATABASE IS READY TO USE!`

### Step 3: Create Database User

Connect to Oracle and create the application user:

```bash
# Option 1: Using Docker exec
docker exec -it oracle-23ai-free sqlplus system/OraclePassword123@FREEPDB1

# Option 2: Using Oracle SQL command line (if installed)
sqlplus system/OraclePassword123@localhost:1521/FREEPDB1
```

Run these SQL commands:
```sql
-- Create timetracker user
CREATE USER timetracker IDENTIFIED BY TimeTracker123 DEFAULT TABLESPACE USERS;
GRANT CONNECT, RESOURCE, CREATE SESSION TO timetracker;
GRANT UNLIMITED TABLESPACE TO timetracker;
GRANT CREATE TABLE, CREATE VIEW, CREATE SEQUENCE TO timetracker;
EXIT;
```

### Step 4: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Configure Environment

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env` file with your settings:
```bash
# Basic Configuration
SECRET_KEY=your-secret-key-here-generate-a-random-string
JWT_SECRET_KEY=your-jwt-secret-key-here-generate-a-random-string

# Oracle Database Configuration
DATABASE_URL=oracle+oracledb://timetracker:TimeTracker123@localhost:1521/?service_name=FREEPDB1
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE=FREEPDB1
ORACLE_USERNAME=timetracker
ORACLE_PASSWORD=TimeTracker123

# Organization Configuration
ALLOWED_EMAIL_DOMAINS=yourdomain.com
ORGANIZATION_NAME=Your Organization
REQUIRE_ADMIN_APPROVAL=false
ALLOW_SELF_REGISTRATION=true

# Google OAuth (optional - get from Google Cloud Console)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Application Configuration
FLASK_ENV=development
FLASK_DEBUG=True
```

### Step 6: Run the Application

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the Flask application
python app.py
```

The application will be available at: **http://localhost:5000**

### Step 7: Create Admin User (Optional)

```bash
# Run the admin setup script (if available)
python reset_admin.py
```

## Google OAuth Setup (Optional)

To enable Google Sign-In:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set authorized redirect URIs:
   - `http://localhost:5000/auth/google/callback`
6. Copy Client ID and Client Secret to your `.env` file

## Quick Start Commands

```bash
# Full setup from scratch
git clone https://github.com/ViliTajnic/prisotnost-demo.git
cd prisotnost-demo
docker run -d --name oracle-23ai-free -p 1521:1521 -e ORACLE_PWD=OraclePassword123 container-registry.oracle.com/database/free:latest
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env file
python app.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `dev-secret-key` |
| `JWT_SECRET_KEY` | JWT signing key | `jwt-secret-key` |
| `DATABASE_URL` | Oracle database URL | Local Oracle |
| `ORACLE_HOST` | Oracle database host | `localhost` |
| `ORACLE_PORT` | Oracle database port | `1521` |
| `ORACLE_SERVICE` | Oracle service name | `FREEPDB1` |

### Database Setup

The application uses Oracle 23ai Free database. The schema is automatically created on first run.

**Manual Setup:**
```bash
# Connect to Oracle database
sqlplus system/password@localhost:1521/FREEPDB1

# Run the setup script
@database_setup.sql
```

## Development

### Local Development Setup

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Oracle Instant Client**
   - Download Oracle Instant Client
   - Set LD_LIBRARY_PATH environment variable

3. **Configure database**
   ```bash
   # Start Oracle database
   docker run -d --name oracle-db \
     -p 1521:1521 \
     -e ORACLE_PWD=MyPassword123 \
     container-registry.oracle.com/database/free:latest
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

### API Documentation

The application provides a comprehensive REST API:

#### Authentication Endpoints
- `POST /login` - User authentication
- `POST /logout` - User logout

#### Time Tracking Endpoints
- `POST /api/clock-in` - Clock in with geolocation
- `POST /api/clock-out` - Clock out with break time
- `GET /api/current-status` - Current clock status
- `GET /api/time-entries` - Time entry history

#### Scheduling Endpoints
- `GET /api/schedules` - Get schedules
- `POST /api/schedules` - Create schedule
- `PUT /api/schedules/{id}` - Update schedule
- `DELETE /api/schedules/{id}` - Delete schedule

#### Reporting Endpoints
- `GET /api/reports` - Generate reports
- `POST /api/export-report` - Export report data

### Database Schema

The application uses a comprehensive database schema with the following main tables:

- **users** - User accounts and profiles
- **departments** - Organizational structure
- **time_entries** - Clock in/out records
- **schedules** - Work schedules
- **projects** - Project definitions
- **leave_requests** - Time-off requests
- **geofences** - Location boundaries
- **audit_logs** - Security audit trail

## Deployment

### Production Deployment

1. **Configure production environment**
   ```bash
   # Update docker-compose.yml for production
   # Set secure passwords and secrets
   # Configure SSL certificates
   ```

2. **Deploy with Docker Compose**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Enable monitoring** (optional)
   ```bash
   docker-compose --profile monitoring up -d
   ```

### Security Considerations

- Change all default passwords
- Use HTTPS in production
- Configure firewall rules
- Regular security updates
- Enable audit logging
- Implement backup strategy

### Backup and Recovery

**Database Backup:**
```bash
# Export Oracle database
expdp system/password@localhost:1521/FREEPDB1 \
  directory=backup_dir \
  dumpfile=timetracker_backup.dmp \
  schemas=SYSTEM
```

**Application Backup:**
```bash
# Backup configuration and data
tar -czf timetracker_backup.tar.gz \
  .env docker-compose.yml logs/ data/
```

## Monitoring and Maintenance

### Health Checks
- Application: `GET /health`
- Database: Oracle Enterprise Manager
- System: Docker health checks

### Log Files
- Application logs: `logs/app.log`
- Nginx logs: `nginx_logs/access.log`
- Database logs: Oracle alert logs

### Performance Tuning
- Database connection pooling
- Redis caching for sessions
- Nginx static file caching
- Query optimization

## Troubleshooting

### Common Issues

**Oracle Connection Issues:**
```bash
# Check Oracle service status
docker logs oracle-23ai-free

# Test connection
sqlplus system/password@localhost:1521/FREEPDB1
```

**Application Startup Issues:**
```bash
# Check application logs
docker logs timetracker-app

# Check environment variables
docker exec timetracker-app env
```

**Permission Issues:**
```bash
# Check file permissions
ls -la logs/
chown -R appuser:appuser /app
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- **Issues**: [GitHub Issues](https://github.com/ViliTajnic/prisotnost-demo/issues)
- **Email**: vili.tajnic@gmail.com
- **Author**: Vili Tajnic

## Roadmap

### Version 2.0 (Planned)
- Mobile app (React Native)
- Advanced reporting with ML insights
- Integration with popular payroll systems
- Multi-tenant architecture
- Advanced workflow automation

### Version 1.1 (Current)
- Enhanced geofencing features
- Improved mobile responsiveness
- Additional report formats
- Performance optimizations