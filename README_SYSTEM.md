# Firefly Station - Emergency Response System

## Overview

Firefly Station is a comprehensive emergency response and coordination system built for mesh networking environments. It integrates Светлячок devices, real-time geolocation tracking, zone management, alert systems, and AI-powered bot responses to provide robust emergency coordination capabilities.

## Architecture

### System Components

- **Backend**: FastAPI-based REST API with real-time WebSocket support
- **Frontend**: React.js application with modern UI components
- **Database**: SQLite database with comprehensive data models
- **External Integration**: Светлячок mesh networking devices
- **AI Integration**: LLM models with MCP server support
- **Real-time Features**: WebSocket communication, live geolocation tracking

### Key Features

- **Real-time Geolocation Tracking**: Live user/device location monitoring
- **Zone Management**: Configurable geographic zones with alert triggers
- **Alert System**: Multi-level alert creation, escalation, and management
- **User Management**: Role-based access control with group permissions
- **Bot Integration**: AI-powered response system with contextual awareness
- **Message Management**: Светлячок message processing and storage
- **Audit Logging**: Comprehensive system activity tracking

## Installation

### Prerequisites

- Python 3.8+
- Node.js 16+
- SQLite3
- Светлячок device (optional, for full functionality)

### Backend Setup

1. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure System**
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml with your settings
   ```

3. **Initialize Database**
   ```bash
   python -c "from backend import database; database.init_db()"
   ```

4. **Start Backend Server**
   ```bash
   python main.py
   ```

### Frontend Setup

1. **Install Node Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start Development Server**
   ```bash
   npm start
   ```

3. **Build for Production**
   ```bash
   npm run build
   ```

## Configuration

### Main Configuration (config.yaml)

```yaml
# Web Server Configuration
web_server:
  host: 0.0.0.0
  port: 8000
  cors_origins:
    - http://localhost:3000

# LLM Provider Settings
llm_provider: ollama
model:
  ollama:
    name: gemma3:latest
    tool_use: true
  openrouter:
    api_key: your_api_key_here
    name: openai/gpt-4

# Светлячок Connection
meshtastic:
  device: /dev/ttyUSB0  # or TCP: 192.168.1.245
  interface: serial  # or tcp

# Emergency Response Settings
emergency:
  default_response_time: 300  # seconds
  escalation_levels:
    - low
    - medium
    - high
    - critical
```

## API Documentation

### Authentication Endpoints

- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User authentication
- `GET /api/auth/me` - Get current user info

### User Management

- `GET /api/users/` - List all users
- `POST /api/users/` - Create new user
- `GET /api/users/{user_id}` - Get user details
- `PUT /api/users/{user_id}` - Update user
- `DELETE /api/users/{user_id}` - Delete user

### Zone Management

- `GET /api/zones/` - List all zones
- `POST /api/zones/` - Create new zone
- `GET /api/zones/{zone_id}` - Get zone details
- `PUT /api/zones/{zone_id}` - Update zone
- `DELETE /api/zones/{zone_id}` - Delete zone

### Alert Management

- `GET /api/alerts/` - List all alerts
- `POST /api/alerts/` - Create new alert
- `GET /api/alerts/{alert_id}` - Get alert details
- `PUT /api/alerts/{alert_id}` - Update alert status
- `DELETE /api/alerts/{alert_id}` - Delete alert

### Geolocation

- `GET /api/geolocation/test` - Test geolocation service
- `POST /api/geolocation/process` - Process location update
- `GET /api/geolocation/users/{user_id}/history` - Get user location history

### WebSocket Endpoints

- `GET /api/websocket/test` - Test WebSocket connectivity
- WebSocket URL: `ws://localhost:8000/api/websocket/connect`

## Testing

### Test Suites

The system includes comprehensive testing suites:

1. **System Integration Tests** (`test_system_integration.py`)
   - Tests all components working together
   - Validates end-to-end functionality

2. **Component Integration Tests** (`test_component_integration.py`)
   - Tests individual component interactions
   - Validates component dependencies

3. **End-to-End Workflow Tests** (`test_end_to_end_workflows.py`)
   - Tests complete user workflows
   - Validates business processes

4. **Cross-Component Communication Tests** (`test_cross_component_communication.py`)
   - Tests inter-component communication
   - Validates real-time features

5. **Performance and Load Tests** (`test_performance_load.py`)
   - Tests system performance under load
   - Validates scalability

6. **System Validation** (`validate_system.py`)
   - Validates system state and configuration
   - Checks for common issues

### Running Tests

```bash
# Run all tests
python test_comprehensive_suite.py

# Run specific test suite
python test_system_integration.py

# Run system validation
python validate_system.py

# Run performance tests
python test_performance_load.py

# Quick test run
python test_comprehensive_suite.py --quick
```

## Deployment

### Production Deployment

1. **Environment Setup**
   ```bash
   export NODE_ENV=production
   export PYTHONPATH=/path/to/firefly-station
   ```

2. **Build Frontend**
   ```bash
   cd frontend
   npm run build
   ```

3. **Configure Production Settings**
   - Update `config.yaml` for production
   - Set secure API keys
   - Configure proper CORS origins
   - Set up SSL certificates

4. **Start Services**
   ```bash
   # Using systemd (recommended)
   sudo cp deploy/firefly-station.service /etc/systemd/system/
   sudo systemctl enable firefly-station
   sudo systemctl start firefly-station

   # Or using Docker
   docker-compose -f deploy/docker-compose.yml up -d
   ```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN cd frontend && npm install && npm run build

EXPOSE 8000
CMD ["python", "main.py"]
```

## Monitoring and Maintenance

### Health Checks

```bash
# System validation
python validate_system.py

# Database integrity check
python -c "from backend import database; print(database.get_bot_stats())"

# API health check
curl http://localhost:8000/
```

### Log Monitoring

- Application logs: `/var/log/firefly-station/`
- Database logs: SQLite maintains internal logs
- System logs: Check with `journalctl -u firefly-station`

### Backup Procedures

```bash
# Database backup
cp meshtastic_llm.db backups/db_$(date +%Y%m%d_%H%M%S).backup

# Configuration backup
cp config.yaml backups/

# Full system backup
tar -czf firefly-station-$(date +%Y%m%d).tar.gz . --exclude=backups/*
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check file permissions on `meshtastic_llm.db`
   - Verify SQLite3 is installed
   - Check available disk space

2. **Светлячок Connection Problems**
   - Verify device is connected and powered
   - Check USB permissions for serial devices
   - Validate TCP connection settings

3. **Frontend Issues**
   - Clear browser cache and cookies
   - Check browser console for JavaScript errors
   - Verify API endpoints are accessible

4. **Performance Issues**
   - Monitor memory usage with `ps aux | grep python`
   - Check database query performance
   - Validate network connectivity

### Debug Mode

Enable debug logging in `config.yaml`:

```yaml
logging:
  level: DEBUG
  file: /var/log/firefly-station/debug.log
```

## Security Considerations

### Authentication and Authorization

- All API endpoints require authentication
- Role-based access control (RBAC) implemented
- JWT tokens with configurable expiration
- Password hashing with bcrypt

### Data Protection

- Sensitive data encrypted in database
- API keys stored securely
- CORS properly configured
- Input validation and sanitization

### Network Security

- HTTPS recommended for production
- Firewall configuration for API ports
- Rate limiting on API endpoints
- WebSocket connection validation

## Development

### Code Structure

```
firefly-station/
├── backend/                 # FastAPI backend
│   ├── routers/            # API route handlers
│   ├── database.py         # Database operations
│   ├── geolocation.py      # Location processing
│   └── main.py            # Application entry point
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── contexts/       # React contexts
│   │   └── i18n/          # Internationalization
├── model/                  # AI/LLM integration
├── session/               # User session management
├── tests/                 # Test files
└── docs/                  # Documentation
```

### Adding New Features

1. **Backend API**
   - Add router in `backend/routers/`
   - Implement business logic
   - Add database models if needed
   - Update API documentation

2. **Frontend Components**
   - Create React component in `frontend/src/components/`
   - Add routing if needed
   - Update internationalization
   - Add tests

3. **Database Changes**
   - Update database schema
   - Create migration scripts
   - Update database operations

### Testing New Features

```bash
# Add unit tests
python -m pytest tests/test_new_feature.py -v

# Add integration tests
python test_component_integration.py

# Validate system
python validate_system.py
```

## Support

### Getting Help

- Check the troubleshooting section
- Review system logs
- Run validation scripts
- Check test outputs

### Reporting Issues

1. Run system validation: `python validate_system.py`
2. Include validation report in issue
3. Provide relevant log excerpts
4. Describe steps to reproduce

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Changelog

### Version 1.0.0

- Initial release
- Core emergency response functionality
- Светлячок integration
- Real-time geolocation tracking
- Zone and alert management
- User management and authentication
- Comprehensive test suite