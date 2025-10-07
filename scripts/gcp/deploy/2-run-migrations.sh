#!/bin/bash
# 2-run-migrations.sh - Run database migrations via Cloud SQL Proxy
#
# This script:
# - Downloads Cloud SQL Proxy if not exists
# - Connects to Cloud SQL via proxy
# - Runs SQL migrations from database/migrations/
# - Verifies migration status

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/../utils/common-functions.sh"

# Project root (3 levels up from this script)
PROJECT_ROOT="$SCRIPT_DIR/../../.."

# Cloud SQL Proxy configuration
PROXY_BINARY="$SCRIPT_DIR/cloud-sql-proxy"
PROXY_VERSION="v2.8.0"

# Migration tracking table
MIGRATION_TABLE="schema_migrations"

# ============================================================================
# Download Cloud SQL Proxy
# ============================================================================

download_proxy() {
    log_section "Cloud SQL Proxy Setup"

    if [ -f "$PROXY_BINARY" ]; then
        log_success "Cloud SQL Proxy already exists"
        return 0
    fi

    log_info "Downloading Cloud SQL Proxy $PROXY_VERSION..."

    # Detect OS
    local os_type=""
    case "$(uname -s)" in
        Darwin*)
            os_type="darwin"
            ;;
        Linux*)
            os_type="linux"
            ;;
        *)
            die "Unsupported OS: $(uname -s)"
            ;;
    esac

    # Detect architecture
    local arch_type=""
    case "$(uname -m)" in
        x86_64)
            arch_type="amd64"
            ;;
        arm64|aarch64)
            arch_type="arm64"
            ;;
        *)
            die "Unsupported architecture: $(uname -m)"
            ;;
    esac

    local download_url="https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/${PROXY_VERSION}/cloud-sql-proxy.${os_type}.${arch_type}"

    log_info "Downloading from: $download_url"

    if ! curl -o "$PROXY_BINARY" -L "$download_url"; then
        die "Failed to download Cloud SQL Proxy"
    fi

    chmod +x "$PROXY_BINARY"
    log_success "Cloud SQL Proxy downloaded and ready"
}

# ============================================================================
# Create Migration Tracking Table
# ============================================================================

create_migration_table() {
    local db_password=$1

    log_info "Ensuring migration tracking table exists..."

    PGPASSWORD="$db_password" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" << 'EOF' 2>/dev/null || true
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF

    log_success "Migration tracking table ready"
}

# ============================================================================
# Check if Migration Already Applied
# ============================================================================

is_migration_applied() {
    local migration_name=$1
    local db_password=$2

    local count=$(PGPASSWORD="$db_password" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM $MIGRATION_TABLE WHERE version = '$migration_name';" 2>/dev/null || echo "0")

    if [ "$count" -gt 0 ]; then
        return 0  # Already applied
    else
        return 1  # Not applied
    fi
}

# ============================================================================
# Record Migration
# ============================================================================

record_migration() {
    local migration_name=$1
    local db_password=$2

    PGPASSWORD="$db_password" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -c \
        "INSERT INTO $MIGRATION_TABLE (version) VALUES ('$migration_name');" >/dev/null 2>&1

    check_status "Failed to record migration: $migration_name"
}

# ============================================================================
# Run Migrations
# ============================================================================

run_migrations() {
    log_section "Database Migration"

    # Get database password from Secret Manager
    log_info "Retrieving database password from Secret Manager..."
    local db_password=$(get_secret "$SECRET_DB_PASSWORD")
    if [ -z "$db_password" ]; then
        die "Failed to retrieve database password from Secret Manager"
    fi
    log_success "Database password retrieved"

    # Start Cloud SQL Proxy in background
    log_info "Starting Cloud SQL Proxy..."
    log_info "Connecting to: $SQL_INSTANCE_CONNECTION"

    "$PROXY_BINARY" "$SQL_INSTANCE_CONNECTION" &
    local proxy_pid=$!

    # Ensure proxy is killed on exit
    trap "kill $proxy_pid 2>/dev/null || true" EXIT

    # Wait for proxy to be ready
    log_info "Waiting for proxy to be ready..."
    sleep 5

    # Check if proxy is still running
    if ! kill -0 $proxy_pid 2>/dev/null; then
        die "Cloud SQL Proxy failed to start"
    fi
    log_success "Cloud SQL Proxy is running (PID: $proxy_pid)"

    # Check if psql is available
    if ! command -v psql &> /dev/null; then
        log_error "psql command not found"
        log_info "Install PostgreSQL client:"
        log_info "  macOS: brew install postgresql"
        log_info "  Ubuntu: sudo apt-get install postgresql-client"
        die "psql is required to run migrations"
    fi

    # Create migration tracking table
    create_migration_table "$db_password"

    # Find all SQL migration files
    local migration_dir="$PROJECT_ROOT/database/migrations"

    if [ ! -d "$migration_dir" ]; then
        die "Migration directory not found: $migration_dir"
    fi

    # Get list of migration files (only forward migrations, not rollbacks)
    local migration_files=$(find "$migration_dir" -name "*.sql" ! -name "*rollback*" | sort)

    if [ -z "$migration_files" ]; then
        log_warning "No migration files found in $migration_dir"
        return 0
    fi

    local total_migrations=$(echo "$migration_files" | wc -l | tr -d ' ')
    local applied_count=0
    local skipped_count=0

    log_info "Found $total_migrations migration files"
    echo ""

    # Run each migration
    while IFS= read -r migration_file; do
        local migration_name=$(basename "$migration_file")

        log_info "Checking migration: $migration_name"

        if is_migration_applied "$migration_name" "$db_password"; then
            log_info "  ↳ Already applied, skipping"
            skipped_count=$((skipped_count + 1))
            continue
        fi

        log_info "  ↳ Applying migration..."

        # Run the migration
        if PGPASSWORD="$db_password" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -f "$migration_file" > /dev/null 2>&1; then
            # Record successful migration
            record_migration "$migration_name" "$db_password"
            log_success "  ✓ Applied: $migration_name"
            applied_count=$((applied_count + 1))
        else
            log_error "  ✗ Failed: $migration_name"
            log_info "Check the SQL file for errors: $migration_file"

            # Show error details
            log_info "Attempting to run with error output:"
            PGPASSWORD="$db_password" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -f "$migration_file" || true

            die "Migration failed: $migration_name"
        fi

    done <<< "$migration_files"

    echo ""
    log_info "Migration summary:"
    log_info "  Applied: $applied_count"
    log_info "  Skipped: $skipped_count"
    log_info "  Total:   $total_migrations"

    if [ $applied_count -gt 0 ]; then
        log_success "Migrations completed successfully"
    else
        log_success "Database already up to date"
    fi

    # Kill proxy
    log_info "Stopping Cloud SQL Proxy..."
    kill $proxy_pid 2>/dev/null || true
    wait $proxy_pid 2>/dev/null || true
    log_success "Cloud SQL Proxy stopped"
}

# ============================================================================
# Verify Migration
# ============================================================================

verify_migrations() {
    log_section "Migration Verification"

    # Get database password
    local db_password=$(get_secret "$SECRET_DB_PASSWORD")

    # Start proxy again for verification
    log_info "Starting Cloud SQL Proxy for verification..."
    "$PROXY_BINARY" "$SQL_INSTANCE_CONNECTION" &
    local proxy_pid=$!
    trap "kill $proxy_pid 2>/dev/null || true" EXIT

    sleep 3

    # Check tables exist
    log_info "Verifying database tables..."

    if command -v psql &> /dev/null; then
        log_info "Database tables:"
        echo ""
        PGPASSWORD="$db_password" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -c "\dt" 2>/dev/null || {
            log_warning "Could not list tables (this might be normal if tables use a different schema)"
        }

        echo ""
        log_info "Applied migrations:"
        PGPASSWORD="$db_password" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -c \
            "SELECT version, applied_at FROM $MIGRATION_TABLE ORDER BY applied_at;" 2>/dev/null || {
            log_warning "Could not list migrations"
        }
    fi

    # Kill proxy
    kill $proxy_pid 2>/dev/null || true
    wait $proxy_pid 2>/dev/null || true
    log_success "Verification complete"
}

# ============================================================================
# Main Function
# ============================================================================

main() {
    log_section "Phase 3 - Step 2: Database Migrations"

    # Initialize checks
    init_checks || die "Environment checks failed"

    # Check Cloud SQL instance exists
    log_info "Verifying Cloud SQL instance..."
    if ! check_sql_instance_exists; then
        die "Cloud SQL instance not found: $SQL_INSTANCE_NAME"
    fi
    log_success "Cloud SQL instance exists"

    # Download proxy if needed
    download_proxy

    # Run migrations
    run_migrations

    # Verify migrations
    verify_migrations

    # Summary
    log_section "Migration Complete"
    log_success "✓ Database migrations completed successfully"
    echo ""
    log_info "Next steps:"
    log_info "  1. Run: ./3-deploy-backend.sh (deploy backend to Cloud Run)"
    log_info "  2. Run: ./4-deploy-frontend.sh (deploy frontend to Cloud Run)"
    echo ""
}

# Run main function
main "$@"
