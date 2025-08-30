#!/bin/bash
# Setup script for local development database
# This script starts the development database and runs initial migrations

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Color codes for output
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker Desktop."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Start development database
start_database() {
    log_info "Starting development database..."
    
    cd "$PROJECT_DIR"
    
    # Stop any existing containers
    docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
    
    # Start the database services
    docker-compose -f docker-compose.dev.yml up -d postgres redis
    
    log_info "Waiting for database to be ready..."
    
    # Wait for PostgreSQL to be ready
    max_attempts=30
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.dev.yml exec -T postgres pg_isready -U postgres -d ai_resume_review_dev &> /dev/null; then
            log_success "Database is ready!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "Database failed to start after $max_attempts attempts"
            docker-compose -f docker-compose.dev.yml logs postgres
            exit 1
        fi
        
        log_info "Attempt $attempt/$max_attempts: Database not ready yet, waiting..."
        sleep 2
        ((attempt++))
    done
}

# Run initial schema setup
setup_schema() {
    log_info "Setting up database schema..."
    
    # Set environment variables for migration script
    export DB_PASSWORD="dev_password_123"
    
    # Run migrations
    "$SCRIPT_DIR/migrate.sh" dev up
    
    log_success "Database schema setup complete"
}

# Start pgAdmin
start_pgadmin() {
    log_info "Starting pgAdmin..."
    
    docker-compose -f docker-compose.dev.yml up -d pgadmin
    
    log_success "pgAdmin started at http://localhost:8080"
    log_info "Login credentials:"
    log_info "  Email: dev@airesumereview.com"
    log_info "  Password: dev_pgadmin_123"
}

# Display connection information
show_connection_info() {
    log_success "Development database is ready!"
    echo ""
    log_info "Connection Information:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: ai_resume_review_dev"
    echo "  Username: postgres"
    echo "  Password: dev_password_123"
    echo ""
    log_info "Redis Information:"
    echo "  Host: localhost"
    echo "  Port: 6379"
    echo "  Password: (none)"
    echo ""
    log_info "pgAdmin: http://localhost:8080"
    echo "  Email: dev@airesumereview.com"
    echo "  Password: dev_pgadmin_123"
    echo ""
    log_info "Useful commands:"
    echo "  Stop database: docker-compose -f docker-compose.dev.yml down"
    echo "  View logs: docker-compose -f docker-compose.dev.yml logs -f postgres"
    echo "  Connect to DB: psql -h localhost -p 5432 -U postgres -d ai_resume_review_dev"
}

# Cleanup function
cleanup() {
    if [[ -n "$1" ]]; then
        log_error "Script failed. Cleaning up..."
        cd "$PROJECT_DIR"
        docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
    fi
}

# Help function
show_help() {
    echo "Development Database Setup Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --no-schema    Skip schema setup (useful for restart)"
    echo "  --no-pgadmin   Skip pgAdmin startup"
    echo ""
    echo "This script will:"
    echo "  1. Check prerequisites (Docker, Docker Compose)"
    echo "  2. Start PostgreSQL and Redis containers"
    echo "  3. Run database migrations"
    echo "  4. Start pgAdmin (optional)"
    echo "  5. Display connection information"
}

# Main execution
main() {
    local skip_schema=false
    local skip_pgadmin=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --no-schema)
                skip_schema=true
                shift
                ;;
            --no-pgadmin)
                skip_pgadmin=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Set up error handling
    trap 'cleanup error' ERR
    
    log_info "Setting up development database..."
    
    # Check prerequisites
    check_prerequisites
    
    # Start database
    start_database
    
    # Setup schema if not skipped
    if [[ "$skip_schema" != true ]]; then
        setup_schema
    fi
    
    # Start pgAdmin if not skipped
    if [[ "$skip_pgadmin" != true ]]; then
        start_pgadmin
    fi
    
    # Show connection info
    show_connection_info
    
    log_success "Development database setup complete!"
}

# Run main function
main "$@"