#!/bin/bash
# Migration Script Unit Tests
# Tests the migration framework functionality and edge cases

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MIGRATION_SCRIPT="$PROJECT_DIR/database/scripts/migrate.sh"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TEST_DETAILS=()

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

# Test result functions
test_pass() {
    local test_name="$1"
    local description="$2"
    log_success "PASS: $test_name - $description"
    TEST_DETAILS+=("PASS: $test_name - $description")
    ((TESTS_PASSED++))
}

test_fail() {
    local test_name="$1"
    local description="$2"
    local error="$3"
    log_error "FAIL: $test_name - $description"
    log_error "Error: $error"
    TEST_DETAILS+=("FAIL: $test_name - $description - Error: $error")
    ((TESTS_FAILED++))
}

# Test 1: Script exists and is executable
test_script_executable() {
    local test_name="script_executable"
    
    if [[ -f "$MIGRATION_SCRIPT" ]]; then
        if [[ -x "$MIGRATION_SCRIPT" ]]; then
            test_pass "$test_name" "Migration script is executable"
        else
            test_fail "$test_name" "Migration script should be executable" "File is not executable"
        fi
    else
        test_fail "$test_name" "Migration script should exist" "File not found: $MIGRATION_SCRIPT"
    fi
}

# Test 2: Script syntax validation
test_script_syntax() {
    local test_name="script_syntax"
    
    if bash -n "$MIGRATION_SCRIPT" 2>/dev/null; then
        test_pass "$test_name" "Migration script has valid syntax"
    else
        local syntax_error=$(bash -n "$MIGRATION_SCRIPT" 2>&1)
        test_fail "$test_name" "Migration script should have valid syntax" "$syntax_error"
    fi
}

# Test 3: Help flag functionality
test_help_flag() {
    local test_name="help_flag"
    
    local help_output
    help_output=$("$MIGRATION_SCRIPT" --help 2>&1)
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]] && [[ "$help_output" == *"Usage:"* ]]; then
        test_pass "$test_name" "Help flag works correctly"
    else
        test_fail "$test_name" "Help flag should work" "Exit code: $exit_code, Output: $help_output"
    fi
}

# Test 4: Invalid environment handling
test_invalid_environment() {
    local test_name="invalid_environment"
    
    local error_output
    error_output=$("$MIGRATION_SCRIPT" "invalid_env" 2>&1)
    local exit_code=$?
    
    if [[ $exit_code -ne 0 ]] && [[ "$error_output" == *"Invalid environment"* ]]; then
        test_pass "$test_name" "Invalid environment is rejected"
    else
        test_fail "$test_name" "Invalid environment should be rejected" "Exit code: $exit_code, Output: $error_output"
    fi
}

# Test 5: Invalid direction handling
test_invalid_direction() {
    local test_name="invalid_direction"
    
    local error_output
    error_output=$("$MIGRATION_SCRIPT" "dev" "invalid_direction" 2>&1)
    local exit_code=$?
    
    if [[ $exit_code -ne 0 ]] && [[ "$error_output" == *"Invalid direction"* ]]; then
        test_pass "$test_name" "Invalid direction is rejected"
    else
        test_fail "$test_name" "Invalid direction should be rejected" "Exit code: $exit_code, Output: $error_output"
    fi
}

# Test 6: Missing DB_PASSWORD environment variable
test_missing_password() {
    local test_name="missing_password"
    
    # Temporarily unset DB_PASSWORD if it exists
    local original_password="$DB_PASSWORD"
    unset DB_PASSWORD
    
    local error_output
    error_output=$("$MIGRATION_SCRIPT" "dev" "up" 2>&1)
    local exit_code=$?
    
    # Restore original password
    if [[ -n "$original_password" ]]; then
        export DB_PASSWORD="$original_password"
    fi
    
    if [[ $exit_code -ne 0 ]] && [[ "$error_output" == *"DB_PASSWORD"* ]]; then
        test_pass "$test_name" "Missing DB_PASSWORD is handled"
    else
        test_fail "$test_name" "Missing DB_PASSWORD should be handled" "Exit code: $exit_code, Output: $error_output"
    fi
}

# Test 7: Migration directory validation
test_migration_directory() {
    local test_name="migration_directory"
    
    local migrations_dir="$PROJECT_DIR/database/migrations"
    
    if [[ -d "$migrations_dir" ]]; then
        # Check if there are migration files
        local migration_count=$(ls "$migrations_dir"/*.sql 2>/dev/null | wc -l)
        if [[ $migration_count -gt 0 ]]; then
            test_pass "$test_name" "Migration directory exists with files"
        else
            test_fail "$test_name" "Migration directory should contain SQL files" "No .sql files found"
        fi
    else
        test_fail "$test_name" "Migration directory should exist" "Directory not found: $migrations_dir"
    fi
}

# Test 8: Migration file naming convention
test_migration_naming() {
    local test_name="migration_naming"
    
    local migrations_dir="$PROJECT_DIR/database/migrations"
    local valid_naming=true
    local invalid_files=()
    
    for file in "$migrations_dir"/*.sql; do
        if [[ -f "$file" ]]; then
            local basename=$(basename "$file")
            # Check if file follows pattern: NNN_description.sql
            if [[ ! "$basename" =~ ^[0-9]{3}_[a-zA-Z0-9_]+\.sql$ ]]; then
                valid_naming=false
                invalid_files+=("$basename")
            fi
        fi
    done
    
    if [[ "$valid_naming" == true ]]; then
        test_pass "$test_name" "All migration files follow naming convention"
    else
        test_fail "$test_name" "Migration files should follow naming convention" "Invalid files: ${invalid_files[*]}"
    fi
}

# Test 9: SQL syntax validation in migration files
test_migration_sql_syntax() {
    local test_name="migration_sql_syntax"
    
    local migrations_dir="$PROJECT_DIR/database/migrations"
    local syntax_valid=true
    local invalid_files=()
    
    # Create temporary database for syntax checking
    local temp_db="syntax_check_$$"
    
    # We'll do basic checks for common SQL syntax issues
    for file in "$migrations_dir"/*.sql; do
        if [[ -f "$file" ]]; then
            local basename=$(basename "$file")
            
            # Basic syntax checks
            if ! grep -q "CREATE\|INSERT\|UPDATE\|DELETE\|ALTER" "$file"; then
                syntax_valid=false
                invalid_files+=("$basename - No SQL statements found")
                continue
            fi
            
            # Check for common syntax errors
            if grep -q "CREATE TABLE.*(" "$file" && ! grep -q ");" "$file"; then
                syntax_valid=false
                invalid_files+=("$basename - Incomplete CREATE TABLE statement")
            fi
            
            # Check for proper migration tracking
            if ! grep -q "schema_migrations" "$file"; then
                syntax_valid=false
                invalid_files+=("$basename - Missing migration tracking")
            fi
        fi
    done
    
    if [[ "$syntax_valid" == true ]]; then
        test_pass "$test_name" "All migration files have valid SQL syntax"
    else
        test_fail "$test_name" "Migration files should have valid SQL syntax" "${invalid_files[*]}"
    fi
}

# Test 10: Function definitions in script
test_script_functions() {
    local test_name="script_functions"
    
    local required_functions=(
        "load_db_config"
        "start_proxy"
        "execute_sql"
        "migrate_up"
        "main"
    )
    
    local missing_functions=()
    
    for func in "${required_functions[@]}"; do
        if ! grep -q "^$func()" "$MIGRATION_SCRIPT"; then
            missing_functions+=("$func")
        fi
    done
    
    if [[ ${#missing_functions[@]} -eq 0 ]]; then
        test_pass "$test_name" "All required functions are defined"
    else
        test_fail "$test_name" "All required functions should be defined" "Missing: ${missing_functions[*]}"
    fi
}

# Test 11: Proper error handling
test_error_handling() {
    local test_name="error_handling"
    
    # Check for 'set -e' at the beginning
    if grep -q "^set -e" "$MIGRATION_SCRIPT"; then
        test_pass "$test_name" "Script has proper error handling (set -e)"
    else
        test_fail "$test_name" "Script should have error handling" "Missing 'set -e'"
    fi
}

# Test 12: Color output functions
test_color_functions() {
    local test_name="color_functions"
    
    local color_functions=(
        "log_info"
        "log_success" 
        "log_warning"
        "log_error"
    )
    
    local missing_color_functions=()
    
    for func in "${color_functions[@]}"; do
        if ! grep -q "$func()" "$MIGRATION_SCRIPT"; then
            missing_color_functions+=("$func")
        fi
    done
    
    if [[ ${#missing_color_functions[@]} -eq 0 ]]; then
        test_pass "$test_name" "All color logging functions are defined"
    else
        test_fail "$test_name" "All color logging functions should be defined" "Missing: ${missing_color_functions[*]}"
    fi
}

# Run all tests
run_all_tests() {
    log_info "Running migration script unit tests..."
    echo ""
    
    test_script_executable
    test_script_syntax
    test_help_flag
    test_invalid_environment
    test_invalid_direction
    test_missing_password
    test_migration_directory
    test_migration_naming
    test_migration_sql_syntax
    test_script_functions
    test_error_handling
    test_color_functions
    
    echo ""
    log_info "Migration Unit Test Summary:"
    echo "============================"
    log_success "Passed: $TESTS_PASSED"
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        log_error "Failed: $TESTS_FAILED"
        echo ""
        log_error "Failed test details:"
        for detail in "${TEST_DETAILS[@]}"; do
            if [[ "$detail" == FAIL* ]]; then
                echo "  $detail"
            fi
        done
        return 1
    else
        log_success "All tests passed!"
        return 0
    fi
}

# Show help
show_help() {
    echo "Migration Script Unit Tests"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "This script tests:"
    echo "  - Script existence and permissions"
    echo "  - Syntax validation"
    echo "  - Command line argument handling"
    echo "  - Function definitions"
    echo "  - Migration file validation"
    echo "  - Error handling"
}

# Main execution
main() {
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        show_help
        exit 0
    fi
    
    run_all_tests
    exit $?
}

# Run main function
main "$@"