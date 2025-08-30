#!/bin/bash
# Database Test Runner
# Runs comprehensive tests on the database schema and functionality

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

# Default values
ENVIRONMENT="${1:-dev}"
TEST_TYPE="${2:-all}"

# Load database configuration
load_db_config() {
    case "$ENVIRONMENT" in
        "dev")
            DB_HOST="localhost"
            DB_PORT="5432"
            DB_NAME="ai_resume_review_dev"
            DB_USER="postgres"
            DB_PASSWORD="${DB_PASSWORD:-dev_password_123}"
            ;;
        "test")
            DB_HOST="localhost"
            DB_PORT="5432"
            DB_NAME="ai_resume_review_test"
            DB_USER="postgres"
            DB_PASSWORD="${DB_PASSWORD:-dev_password_123}"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT. Use 'dev' or 'test'."
            exit 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking test prerequisites..."
    
    # Check PostgreSQL client
    if ! command -v psql &> /dev/null; then
        log_error "PostgreSQL client (psql) is not installed"
        exit 1
    fi
    
    # Check database connection
    if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
        log_error "Cannot connect to database. Is the database running?"
        log_info "For dev environment, run: ./database/scripts/setup-dev-db.sh"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Run schema integrity tests
run_schema_tests() {
    log_info "Running database schema tests..."
    
    local test_output
    test_output=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SCRIPT_DIR/schema_tests.sql" 2>&1)
    
    if [[ $? -eq 0 ]]; then
        log_success "Schema tests completed"
        
        # Extract and display results
        echo "$test_output" | tail -n 50
        
        # Check for failures
        local fail_count
        fail_count=$(echo "$test_output" | grep -c "FAIL" || echo "0")
        
        if [[ $fail_count -gt 0 ]]; then
            log_error "Found $fail_count failed tests"
            return 1
        else
            log_success "All schema tests passed"
            return 0
        fi
    else
        log_error "Schema tests failed to run"
        echo "$test_output"
        return 1
    fi
}

# Run migration tests
run_migration_tests() {
    log_info "Running migration tests..."
    
    # Test migration script syntax
    if ! bash -n "$PROJECT_DIR/database/scripts/migrate.sh"; then
        log_error "Migration script has syntax errors"
        return 1
    fi
    
    log_success "Migration script syntax is valid"
    
    # Test migration dry-run (if test database exists)
    if [[ "$ENVIRONMENT" == "test" ]]; then
        log_info "Testing migrations on test database..."
        
        # Create test database if it doesn't exist
        PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null || true
        
        # Run migrations
        if DB_PASSWORD="$DB_PASSWORD" "$PROJECT_DIR/database/scripts/migrate.sh" test up; then
            log_success "Migration test passed"
            
            # Drop test database
            PGPASSWORD="$DB_PASSWORD" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null || true
            return 0
        else
            log_error "Migration test failed"
            return 1
        fi
    fi
    
    return 0
}

# Run performance tests
run_performance_tests() {
    log_info "Running performance tests..."
    
    local perf_test_sql="
    -- Performance test queries
    \\timing on
    
    -- Test 1: User lookup by email (should be fast with index)
    SELECT id FROM users WHERE email = 'nonexistent@example.com';
    
    -- Test 2: Analysis requests by user (should be fast with index)
    SELECT COUNT(*) FROM analysis_requests WHERE user_id = uuid_generate_v4();
    
    -- Test 3: Join performance test
    SELECT COUNT(*) 
    FROM analysis_requests ar 
    JOIN analysis_results res ON ar.id = res.request_id 
    WHERE ar.status = 'completed';
    
    -- Test 4: Prompt lookup by type (should be fast with index)
    SELECT COUNT(*) FROM prompts WHERE prompt_type = 'system' AND is_active = true;
    
    \\timing off
    "
    
    local perf_output
    perf_output=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$perf_test_sql" 2>&1)
    
    if [[ $? -eq 0 ]]; then
        log_success "Performance tests completed"
        echo "$perf_output" | grep "Time:"
        return 0
    else
        log_error "Performance tests failed"
        echo "$perf_output"
        return 1
    fi
}

# Run connection tests
run_connection_tests() {
    log_info "Running connection tests..."
    
    # Test basic connection
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" &> /dev/null; then
        log_success "Database connection test passed"
    else
        log_error "Database connection test failed"
        return 1
    fi
    
    # Test connection pool limits (simulate multiple connections)
    log_info "Testing connection handling..."
    
    local connection_test_sql="
    SELECT 
        setting as max_connections,
        (SELECT count(*) FROM pg_stat_activity) as current_connections
    FROM pg_settings WHERE name = 'max_connections';
    "
    
    local conn_info
    conn_info=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "$connection_test_sql")
    
    log_info "Connection info: $conn_info"
    log_success "Connection tests passed"
    
    return 0
}

# Generate test report
generate_report() {
    local results_file="$SCRIPT_DIR/test_results_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "Database Test Report"
        echo "===================="
        echo "Date: $(date)"
        echo "Environment: $ENVIRONMENT"
        echo "Database: $DB_NAME"
        echo ""
        
        if [[ -n "$TEST_RESULTS" ]]; then
            echo "Test Results:"
            echo "$TEST_RESULTS"
        fi
        
    } > "$results_file"
    
    log_info "Test report saved to: $results_file"
}

# Show help
show_help() {
    echo "Database Test Runner"
    echo ""
    echo "Usage: $0 [environment] [test_type]"
    echo ""
    echo "Arguments:"
    echo "  environment    Target environment (dev|test) - default: dev"
    echo "  test_type      Type of tests to run (schema|migration|performance|connection|all) - default: all"
    echo ""
    echo "Environment Variables:"
    echo "  DB_PASSWORD    Database password (default: dev_password_123)"
    echo ""
    echo "Examples:"
    echo "  $0 dev schema              # Run only schema tests on dev"
    echo "  $0 test all                # Run all tests on test database"
    echo "  $0 dev performance         # Run performance tests only"
}

# Main execution
main() {
    local schema_result=0
    local migration_result=0
    local performance_result=0
    local connection_result=0
    
    log_info "Starting database tests (Environment: $ENVIRONMENT, Type: $TEST_TYPE)"
    
    # Load configuration
    load_db_config
    
    # Check prerequisites
    check_prerequisites
    
    # Run selected tests
    case "$TEST_TYPE" in
        "schema")
            run_schema_tests
            schema_result=$?
            ;;
        "migration")
            run_migration_tests
            migration_result=$?
            ;;
        "performance")
            run_performance_tests
            performance_result=$?
            ;;
        "connection")
            run_connection_tests
            connection_result=$?
            ;;
        "all")
            run_schema_tests
            schema_result=$?
            
            run_migration_tests
            migration_result=$?
            
            run_performance_tests
            performance_result=$?
            
            run_connection_tests
            connection_result=$?
            ;;
        *)
            log_error "Invalid test type: $TEST_TYPE"
            show_help
            exit 1
            ;;
    esac
    
    # Calculate overall result
    local overall_result=$((schema_result + migration_result + performance_result + connection_result))
    
    # Display summary
    echo ""
    log_info "Test Summary:"
    echo "============="
    
    if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "schema" ]]; then
        if [[ $schema_result -eq 0 ]]; then
            log_success "Schema tests: PASSED"
        else
            log_error "Schema tests: FAILED"
        fi
    fi
    
    if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "migration" ]]; then
        if [[ $migration_result -eq 0 ]]; then
            log_success "Migration tests: PASSED"
        else
            log_error "Migration tests: FAILED"
        fi
    fi
    
    if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "performance" ]]; then
        if [[ $performance_result -eq 0 ]]; then
            log_success "Performance tests: PASSED"
        else
            log_error "Performance tests: FAILED"
        fi
    fi
    
    if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "connection" ]]; then
        if [[ $connection_result -eq 0 ]]; then
            log_success "Connection tests: PASSED"
        else
            log_error "Connection tests: FAILED"
        fi
    fi
    
    echo ""
    if [[ $overall_result -eq 0 ]]; then
        log_success "All tests passed!"
        exit 0
    else
        log_error "Some tests failed!"
        exit 1
    fi
}

# Check for help flag
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function
main