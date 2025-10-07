#!/bin/bash
# Database Migration Script for Cloud SQL
# Runs all SQL migration files in order using Cloud SQL Proxy
#
# Usage:
#   ./scripts/gcp/migrate-database.sh
#
# Prerequisites:
#   - Cloud SQL Proxy installed (brew install cloud-sql-proxy)
#   - gcloud CLI authenticated
#   - psql installed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ytgrs-464303"
REGION="us-central1"
INSTANCE_NAME="ai-resume-review-v2-db-prod"
DB_NAME="ai_resume_review_prod"
DB_USER="postgres"
SECRET_NAME="db-password-prod"
PROXY_PORT="5433"
CONNECTION_NAME="$PROJECT_ID:$REGION:$INSTANCE_NAME"

# Migration files directory
MIGRATIONS_DIR="database/migrations"

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Cloud SQL Database Migration${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"

    # Check Cloud SQL Proxy
    if ! command -v cloud-sql-proxy &> /dev/null; then
        echo -e "${RED}✗ Cloud SQL Proxy not found${NC}"
        echo -e "${YELLOW}Install with: brew install cloud-sql-proxy${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Cloud SQL Proxy installed${NC}"

    # Check psql
    if ! command -v psql &> /dev/null; then
        echo -e "${RED}✗ psql not found${NC}"
        echo -e "${YELLOW}Install PostgreSQL client with: brew install postgresql${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ psql installed${NC}"

    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}✗ gcloud CLI not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ gcloud CLI installed${NC}"

    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        echo -e "${RED}✗ Not authenticated with gcloud${NC}"
        echo -e "${YELLOW}Run: gcloud auth login${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Authenticated with gcloud${NC}"

    echo ""
}

# Get database password from Secret Manager
get_db_password() {
    echo -e "${BLUE}Retrieving database password from Secret Manager...${NC}"
    DB_PASSWORD=$(gcloud secrets versions access latest \
        --secret="$SECRET_NAME" \
        --project="$PROJECT_ID" 2>/dev/null)

    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${RED}✗ Failed to retrieve database password${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Database password retrieved${NC}"
    echo ""
}

# Start Cloud SQL Proxy
start_proxy() {
    echo -e "${BLUE}Starting Cloud SQL Proxy...${NC}"
    echo -e "${BLUE}Connection: $CONNECTION_NAME${NC}"
    echo -e "${BLUE}Port: $PROXY_PORT${NC}"

    # Check if proxy is already running
    if lsof -Pi :$PROXY_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Port $PROXY_PORT already in use${NC}"
        echo -e "${YELLOW}Stopping existing process...${NC}"
        kill $(lsof -t -i:$PROXY_PORT) 2>/dev/null || true
        sleep 2
    fi

    # Start proxy in background
    cloud-sql-proxy \
        --address 0.0.0.0 \
        --port $PROXY_PORT \
        "$CONNECTION_NAME" > /tmp/cloud-sql-proxy.log 2>&1 &

    PROXY_PID=$!
    echo -e "${BLUE}Proxy PID: $PROXY_PID${NC}"

    # Wait for proxy to be ready
    echo -e "${BLUE}Waiting for proxy to be ready...${NC}"
    sleep 5

    if ! kill -0 $PROXY_PID 2>/dev/null; then
        echo -e "${RED}✗ Cloud SQL Proxy failed to start${NC}"
        cat /tmp/cloud-sql-proxy.log
        exit 1
    fi

    echo -e "${GREEN}✓ Cloud SQL Proxy running (PID: $PROXY_PID)${NC}"
    echo ""
}

# Stop Cloud SQL Proxy
stop_proxy() {
    if [ ! -z "$PROXY_PID" ]; then
        echo -e "${BLUE}Stopping Cloud SQL Proxy (PID: $PROXY_PID)...${NC}"
        kill $PROXY_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Proxy stopped${NC}"
    fi
}

# Cleanup on exit
cleanup() {
    echo ""
    echo -e "${BLUE}Cleaning up...${NC}"
    stop_proxy
}
trap cleanup EXIT

# Test database connection
test_connection() {
    echo -e "${BLUE}Testing database connection...${NC}"

    if PGPASSWORD="$DB_PASSWORD" psql \
        -h localhost \
        -p $PROXY_PORT \
        -U $DB_USER \
        -d $DB_NAME \
        -c "SELECT version();" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Database connection successful${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ Database connection failed${NC}"
        return 1
    fi
}

# Run a single migration file
run_migration() {
    local migration_file=$1
    local migration_name=$(basename "$migration_file")

    echo -e "${BLUE}Running migration: $migration_name${NC}"

    if PGPASSWORD="$DB_PASSWORD" psql \
        -h localhost \
        -p $PROXY_PORT \
        -U $DB_USER \
        -d $DB_NAME \
        -f "$migration_file" > /tmp/migration_output.log 2>&1; then
        echo -e "${GREEN}✓ $migration_name completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ $migration_name failed${NC}"
        echo -e "${RED}Error output:${NC}"
        cat /tmp/migration_output.log
        return 1
    fi
}

# Run all migrations
run_migrations() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}Running Database Migrations${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""

    cd "$PROJECT_ROOT"

    # Get list of migration files in order
    local migration_files=(
        "$MIGRATIONS_DIR/001_initial_schema.sql"
        "$MIGRATIONS_DIR/002_add_password_security_columns.sql"
        "$MIGRATIONS_DIR/003_add_refresh_tokens_table.sql"
        "$MIGRATIONS_DIR/004_add_raw_ai_response_column.sql"
        "$MIGRATIONS_DIR/005_remove_file_hash_unique_constraint.sql"
        "$MIGRATIONS_DIR/006_update_industry_enum_values.sql"
    )

    local total=${#migration_files[@]}
    local current=0

    for migration_file in "${migration_files[@]}"; do
        current=$((current + 1))
        echo -e "${CYAN}[$current/$total]${NC}"

        if [ ! -f "$migration_file" ]; then
            echo -e "${YELLOW}⚠ Migration file not found: $migration_file${NC}"
            echo -e "${YELLOW}Skipping...${NC}"
            echo ""
            continue
        fi

        if ! run_migration "$migration_file"; then
            echo -e "${RED}Migration failed. Stopping.${NC}"
            return 1
        fi
        echo ""
    done

    echo -e "${GREEN}✓ All migrations completed successfully!${NC}"
    echo ""
}

# Verify migrations
verify_migrations() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}Verifying Database Schema${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""

    echo -e "${BLUE}Listing tables...${NC}"
    PGPASSWORD="$DB_PASSWORD" psql \
        -h localhost \
        -p $PROXY_PORT \
        -U $DB_USER \
        -d $DB_NAME \
        -c "\dt"

    echo ""
    echo -e "${BLUE}Counting records in key tables...${NC}"
    PGPASSWORD="$DB_PASSWORD" psql \
        -h localhost \
        -p $PROXY_PORT \
        -U $DB_USER \
        -d $DB_NAME \
        -c "
        SELECT
            'users' as table_name, COUNT(*) as count FROM users
        UNION ALL
        SELECT 'analysis_requests', COUNT(*) FROM analysis_requests
        UNION ALL
        SELECT 'analysis_results', COUNT(*) FROM analysis_results
        UNION ALL
        SELECT 'prompts', COUNT(*) FROM prompts
        UNION ALL
        SELECT 'file_uploads', COUNT(*) FROM file_uploads
        UNION ALL
        SELECT 'refresh_tokens', COUNT(*) FROM refresh_tokens;
        "

    echo ""
}

# Main execution
main() {
    check_prerequisites
    get_db_password
    start_proxy

    if ! test_connection; then
        echo -e "${RED}Cannot connect to database. Exiting.${NC}"
        exit 1
    fi

    if ! run_migrations; then
        echo -e "${RED}Migration failed!${NC}"
        exit 1
    fi

    verify_migrations

    echo -e "${CYAN}========================================${NC}"
    echo -e "${GREEN}✓ Database Migration Complete!${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Database: $DB_NAME${NC}"
    echo -e "${BLUE}Instance: $INSTANCE_NAME${NC}"
    echo -e "${BLUE}Project: $PROJECT_ID${NC}"
    echo ""
    echo -e "${GREEN}Your Cloud SQL database is now ready to use!${NC}"
    echo ""
}

# Run main function
main
