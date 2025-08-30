#!/bin/bash
# Database Migration Script for AI Resume Review Platform
# Usage: ./migrate.sh [environment] [direction]
#   environment: dev, staging, prod
#   direction: up (default), down

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MIGRATIONS_DIR="$PROJECT_DIR/database/migrations"

# Default values
ENVIRONMENT="${1:-dev}"
DIRECTION="${2:-up}"

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

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod."
    exit 1
fi

# Validate direction
if [[ ! "$DIRECTION" =~ ^(up|down)$ ]]; then
    log_error "Invalid direction: $DIRECTION. Must be up or down."
    exit 1
fi

# Load database connection info
load_db_config() {
    case "$ENVIRONMENT" in
        "dev")
            DB_HOST="localhost"
            DB_PORT="5432"
            DB_NAME="ai_resume_review_dev"
            DB_USER="postgres"
            ;;
        "staging"|"prod")
            # For Cloud SQL, use connection name
            PROJECT_ID=$(grep 'project_id' "$PROJECT_DIR/infrastructure/terraform/environments/${ENVIRONMENT}.tfvars" | cut -d'"' -f2)
            DB_INSTANCE="ai-resume-review-${ENVIRONMENT}"
            DB_NAME="ai_resume_review"
            DB_USER="app_user"
            DB_CONNECTION_NAME="$PROJECT_ID:us-central1:$DB_INSTANCE"
            
            # Check if cloud_sql_proxy is available
            if ! command -v cloud_sql_proxy &> /dev/null; then
                log_error "cloud_sql_proxy is required for $ENVIRONMENT environment"
                log_info "Install with: gcloud components install cloud_sql_proxy"
                exit 1
            fi
            ;;
    esac
}

# Start cloud SQL proxy if needed
start_proxy() {
    if [[ "$ENVIRONMENT" != "dev" ]]; then
        log_info "Starting Cloud SQL Proxy for $ENVIRONMENT..."
        cloud_sql_proxy -instances="$DB_CONNECTION_NAME"=tcp:5432 &
        PROXY_PID=$!
        sleep 3
        
        # Cleanup function
        cleanup() {
            if [[ -n "$PROXY_PID" ]]; then
                log_info "Stopping Cloud SQL Proxy..."
                kill $PROXY_PID
            fi
        }
        trap cleanup EXIT
    fi
}

# Execute SQL file
execute_sql() {
    local sql_file="$1"
    local description="$2"
    
    log_info "Executing: $description"
    
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$sql_file"
    else
        PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -p 5432 -U "$DB_USER" -d "$DB_NAME" -f "$sql_file"
    fi
}

# Check if migration table exists
check_migration_table() {
    local query="SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'schema_migrations');"
    
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        result=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "$query")
    else
        result=$(PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -p 5432 -U "$DB_USER" -d "$DB_NAME" -t -c "$query")
    fi
    
    echo "$result" | tr -d '[:space:]'
}

# Get applied migrations
get_applied_migrations() {
    local query="SELECT version FROM schema_migrations ORDER BY version;"
    
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "$query" | grep -v '^$'
    else
        PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -p 5432 -U "$DB_USER" -d "$DB_NAME" -t -c "$query" | grep -v '^$'
    fi
}

# Run migrations up
migrate_up() {
    log_info "Running migrations UP for $ENVIRONMENT environment..."
    
    # Check if migrations table exists
    if [[ "$(check_migration_table)" != "t" ]]; then
        log_warning "Migration table doesn't exist. Creating it with first migration."
    fi
    
    # Get list of migration files
    migration_files=($(ls "$MIGRATIONS_DIR"/*.sql | sort))
    
    if [[ ${#migration_files[@]} -eq 0 ]]; then
        log_warning "No migration files found in $MIGRATIONS_DIR"
        return
    fi
    
    # Get applied migrations
    applied_migrations=()
    if [[ "$(check_migration_table)" == "t" ]]; then
        while IFS= read -r line; do
            applied_migrations+=("$line")
        done < <(get_applied_migrations)
    fi
    
    # Apply pending migrations
    for migration_file in "${migration_files[@]}"; do
        migration_name=$(basename "$migration_file" .sql)
        
        # Check if migration is already applied
        if [[ " ${applied_migrations[@]} " =~ " ${migration_name} " ]]; then
            log_info "Skipping $migration_name (already applied)"
            continue
        fi
        
        log_info "Applying migration: $migration_name"
        execute_sql "$migration_file" "Migration $migration_name"
        log_success "Applied migration: $migration_name"
    done
    
    log_success "All migrations completed successfully!"
}

# Run migrations down (rollback)
migrate_down() {
    log_info "Running migrations DOWN for $ENVIRONMENT environment..."
    log_error "Migration rollback not yet implemented"
    exit 1
}

# Main execution
main() {
    log_info "Starting database migration for $ENVIRONMENT environment (direction: $DIRECTION)"
    
    # Validate migrations directory
    if [[ ! -d "$MIGRATIONS_DIR" ]]; then
        log_error "Migrations directory not found: $MIGRATIONS_DIR"
        exit 1
    fi
    
    # Load configuration
    load_db_config
    
    # Check for required environment variables
    if [[ -z "$DB_PASSWORD" ]]; then
        log_error "DB_PASSWORD environment variable is required"
        exit 1
    fi
    
    # Start proxy if needed
    start_proxy
    
    # Run migrations
    case "$DIRECTION" in
        "up")
            migrate_up
            ;;
        "down")
            migrate_down
            ;;
    esac
}

# Help function
show_help() {
    echo "Database Migration Script for AI Resume Review Platform"
    echo ""
    echo "Usage: $0 [environment] [direction]"
    echo ""
    echo "Arguments:"
    echo "  environment    Target environment (dev|staging|prod) - default: dev"
    echo "  direction      Migration direction (up|down) - default: up"
    echo ""
    echo "Environment Variables:"
    echo "  DB_PASSWORD    Database password (required)"
    echo ""
    echo "Examples:"
    echo "  $0 dev up              # Run pending migrations on dev"
    echo "  $0 staging up          # Run pending migrations on staging"
    echo "  $0 prod down           # Rollback last migration on prod"
    echo ""
    echo "Prerequisites:"
    echo "  - PostgreSQL client (psql)"
    echo "  - For staging/prod: gcloud SDK with cloud_sql_proxy"
    echo "  - Proper database credentials"
}

# Check for help flag
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function
main