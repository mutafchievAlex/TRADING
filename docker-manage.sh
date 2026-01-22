#!/bin/bash
# Docker setup and deployment script for trading system

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
DEV_COMPOSE_FILE="docker-compose.dev.yml"
IMAGE_NAME="trading_system:latest"
CONTAINER_NAME="trading_system_xauusd"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    log_info "Docker found: $(docker --version)"
}

# Check if Docker Compose is installed
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    log_info "Docker Compose found: $(docker-compose --version)"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    docker build -t $IMAGE_NAME .
    log_info "Image built successfully"
}

# Start services (production)
start_production() {
    log_info "Starting trading system in PRODUCTION mode..."
    docker-compose -f $COMPOSE_FILE up -d
    log_info "Trading system is running in background"
    docker-compose -f $COMPOSE_FILE ps
}

# Start services (development)
start_development() {
    log_info "Starting trading system in DEVELOPMENT mode..."
    docker-compose -f $DEV_COMPOSE_FILE up
}

# Stop services
stop_services() {
    log_warn "Stopping trading system..."
    docker-compose down
    log_info "Services stopped"
}

# View logs
view_logs() {
    docker-compose logs -f --tail=50
}

# Restart services
restart_services() {
    log_warn "Restarting trading system..."
    docker-compose restart
    log_info "Services restarted"
}

# Health check
health_check() {
    log_info "Checking container health..."
    if docker-compose ps | grep -q "healthy"; then
        log_info "Container is healthy"
    elif docker-compose ps | grep -q "starting"; then
        log_warn "Container is starting..."
    else
        log_error "Container is not healthy"
    fi
}

# Enter container shell
shell_access() {
    log_info "Entering container shell..."
    docker-compose exec trading-bot bash
}

# Display usage
usage() {
    cat << EOF
Trading System Docker Management Script

Usage: $0 [COMMAND]

Commands:
    build           Build Docker image
    start           Start services (production, background)
    dev             Start services (development, foreground with UI)
    stop            Stop all services
    restart         Restart services
    logs            View real-time logs
    health          Check container health
    shell           Enter container shell for debugging
    help            Show this help message

Examples:
    $0 build           # Build the image first time
    $0 start           # Start trading system
    $0 dev             # Start with UI for development
    $0 logs            # View logs in real-time
    $0 health          # Check if container is running

Production Deployment:
    1. $0 build
    2. $0 start
    3. $0 logs         # Monitor in separate terminal
    4. $0 health       # Verify health

After host restart, container auto-starts with 'restart: always' policy.
EOF
}

# Main logic
main() {
    case "${1:-help}" in
        build)
            check_docker
            build_image
            ;;
        start)
            check_docker
            check_docker_compose
            start_production
            ;;
        dev)
            check_docker
            check_docker_compose
            start_development
            ;;
        stop)
            check_docker_compose
            stop_services
            ;;
        restart)
            check_docker_compose
            restart_services
            ;;
        logs)
            check_docker_compose
            view_logs
            ;;
        health)
            check_docker_compose
            health_check
            ;;
        shell)
            check_docker_compose
            shell_access
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            log_error "Unknown command: $1"
            usage
            exit 1
            ;;
    esac
}

main "$@"
