#!/bin/bash

# Firefly Station Deployment Script
# Automates system deployment and configuration

set -e  # Exit on any error

# Configuration
PROJECT_NAME="firefly-station"
BACKUP_DIR="backups"
LOG_DIR="logs"
FRONTEND_DIR="frontend"
BACKEND_DIR="backend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Prerequisites check
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Python
    if ! command_exists python3; then
        log_error "Python 3 is not installed"
        exit 1
    fi

    # Check Node.js
    if ! command_exists node; then
        log_error "Node.js is not installed"
        exit 1
    fi

    # Check SQLite3
    if ! command_exists sqlite3; then
        log_error "SQLite3 is not installed"
        exit 1
    fi

    log_success "All prerequisites are met"
}

# Create directories
create_directories() {
    log_info "Creating necessary directories..."

    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$FRONTEND_DIR/build"

    log_success "Directories created"
}

# Backup existing installation
backup_existing() {
    if [ -f "meshtastic_llm.db" ] || [ -f "config.yaml" ]; then
        log_info "Creating backup of existing installation..."

        BACKUP_FILE="$BACKUP_DIR/$(date +%Y%m%d_%H%M%S)_backup.tar.gz"

        tar -czf "$BACKUP_FILE" \
            --exclude="$BACKUP_DIR" \
            --exclude="$LOG_DIR" \
            --exclude="node_modules" \
            --exclude="__pycache__" \
            --exclude=".git" \
            . 2>/dev/null || true

        if [ -f "$BACKUP_FILE" ]; then
            log_success "Backup created: $BACKUP_FILE"
        fi
    fi
}

# Setup backend
setup_backend() {
    log_info "Setting up backend..."

    # Install Python dependencies
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        log_success "Python dependencies installed"
    else
        log_error "requirements.txt not found"
        exit 1
    fi

    # Initialize database
    python3 -c "from backend import database; database.init_db()"
    log_success "Database initialized"

    # Validate backend setup
    python3 -c "from backend.main import app; print('Backend validation successful')"
    log_success "Backend validation passed"
}

# Setup frontend
setup_frontend() {
    log_info "Setting up frontend..."

    cd "$FRONTEND_DIR"

    # Install Node dependencies
    if [ -f "package.json" ]; then
        npm install
        log_success "Node dependencies installed"
    else
        log_error "package.json not found"
        exit 1
    fi

    # Build frontend
    npm run build
    log_success "Frontend built successfully"

    cd ..
}

# Configure system
configure_system() {
    log_info "Configuring system..."

    # Check if config.yaml exists
    if [ ! -f "config.yaml" ]; then
        log_warning "config.yaml not found, creating from template..."

        if [ -f "config.yaml.example" ]; then
            cp config.yaml.example config.yaml
            log_info "Created config.yaml from template"
            log_warning "Please edit config.yaml with your settings before starting the system"
        else
            log_error "No config template found"
            exit 1
        fi
    fi

    # Validate configuration
    python3 -c "
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    print('Configuration validation successful')
"
    log_success "Configuration validated"
}

# Create systemd service (Linux only)
create_systemd_service() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_info "Creating systemd service..."

        SERVICE_FILE="/tmp/firefly-station.service"

        cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Firefly Station Emergency Response System
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment=PATH=$(python3 -c "import sys; print(':'.join(sys.path))")
ExecStart=$(which python3) main.py
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$(pwd)/logs $(pwd)/backups

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=firefly-station

[Install]
WantedBy=multi-user.target
EOF

        sudo mv "$SERVICE_FILE" /etc/systemd/system/firefly-station.service
        sudo systemctl daemon-reload

        log_success "Systemd service created"
        log_info "Enable with: sudo systemctl enable firefly-station"
        log_info "Start with: sudo systemctl start firefly-station"
    else
        log_info "Skipping systemd service creation (not on Linux)"
    fi
}

# Run validation
run_validation() {
    log_info "Running system validation..."

    python3 validate_system.py

    if [ $? -eq 0 ]; then
        log_success "System validation passed"
    else
        log_warning "System validation found issues - please review"
    fi
}

# Main deployment function
main() {
    echo "🚀 Firefly Station Deployment Script"
    echo "===================================="

    # Parse command line arguments
    SKIP_FRONTEND=false
    SKIP_BACKEND=false
    SKIP_VALIDATION=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-frontend)
                SKIP_FRONTEND=true
                shift
                ;;
            --skip-backend)
                SKIP_BACKEND=true
                shift
                ;;
            --skip-validation)
                SKIP_VALIDATION=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --skip-frontend    Skip frontend setup"
                echo "  --skip-backend     Skip backend setup"
                echo "  --skip-validation  Skip system validation"
                echo "  --help            Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Run deployment steps
    check_prerequisites
    create_directories
    backup_existing

    if [ "$SKIP_BACKEND" = false ]; then
        setup_backend
    fi

    if [ "$SKIP_FRONTEND" = false ]; then
        setup_frontend
    fi

    configure_system

    if [ "$SKIP_VALIDATION" = false ]; then
        run_validation
    fi

    create_systemd_service

    # Final instructions
    echo ""
    log_success "Deployment completed!"
    echo ""
    echo "Next steps:"
    echo "1. Edit config.yaml with your specific settings"
    echo "2. Start the system:"
    echo "   - Development: python main.py"
    echo "   - Production: sudo systemctl start firefly-station"
    echo "3. Access the web interface at http://localhost:8000"
    echo ""
    echo "For production deployment, consider:"
    echo "- Setting up SSL certificates"
    echo "- Configuring firewall rules"
    echo "- Setting up log rotation"
    echo "- Configuring backup schedules"
}

# Run main function with all arguments
main "$@"