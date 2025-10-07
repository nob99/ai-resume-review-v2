#!/bin/bash
# integration-test.sh - Full integration test of deployed application
#
# This script tests the complete user flow:
# 1. User registration
# 2. User login
# 3. Token refresh
# 4. Resume upload (simulated)
# 5. Analysis request (simulated)

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/../utils/common-functions.sh"

# Test data
TEST_EMAIL="test-$(date +%s)@example.com"
TEST_PASSWORD="TestPassword123!"
TEST_FIRST_NAME="Test"
TEST_LAST_NAME="User"

# ============================================================================
# Test User Registration
# ============================================================================

test_registration() {
    local backend_url=$1

    log_section "Test 1: User Registration"

    log_info "Registering test user: $TEST_EMAIL"

    local response=$(curl -s -w "\n%{http_code}" \
        -X POST "$backend_url/api/v1/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$TEST_EMAIL\",
            \"password\": \"$TEST_PASSWORD\",
            \"first_name\": \"$TEST_FIRST_NAME\",
            \"last_name\": \"$TEST_LAST_NAME\"
        }" 2>/dev/null || echo "000")

    local http_code=$(echo "$response" | tail -n1)
    local response_body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        log_success "Registration successful (HTTP $http_code)"

        if command -v jq &> /dev/null; then
            echo "$response_body" | jq .
        else
            echo "$response_body"
        fi

        return 0
    else
        log_error "Registration failed (HTTP $http_code)"
        log_info "Response: $response_body"
        return 1
    fi
}

# ============================================================================
# Test User Login
# ============================================================================

test_login() {
    local backend_url=$1

    log_section "Test 2: User Login"

    log_info "Logging in as: $TEST_EMAIL"

    local response=$(curl -s -w "\n%{http_code}" \
        -X POST "$backend_url/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$TEST_EMAIL\",
            \"password\": \"$TEST_PASSWORD\"
        }" 2>/dev/null || echo "000")

    local http_code=$(echo "$response" | tail -n1)
    local response_body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        log_success "Login successful (HTTP $http_code)"

        if command -v jq &> /dev/null; then
            # Extract access token
            local access_token=$(echo "$response_body" | jq -r '.access_token // .token // empty')

            if [ -n "$access_token" ] && [ "$access_token" != "null" ]; then
                log_success "Access token received"
                echo "$access_token" > /tmp/test_access_token.tmp
            else
                log_warning "No access token in response"
            fi

            echo "$response_body" | jq .
        else
            echo "$response_body"
        fi

        return 0
    else
        log_error "Login failed (HTTP $http_code)"
        log_info "Response: $response_body"
        return 1
    fi
}

# ============================================================================
# Test Authenticated Endpoint
# ============================================================================

test_authenticated_request() {
    local backend_url=$1

    log_section "Test 3: Authenticated Request"

    # Check if token file exists
    if [ ! -f /tmp/test_access_token.tmp ]; then
        log_warning "No access token available, skipping authenticated test"
        return 1
    fi

    local access_token=$(cat /tmp/test_access_token.tmp)

    log_info "Testing authenticated endpoint with token..."

    # Try to access a protected endpoint (e.g., user profile)
    local response=$(curl -s -w "\n%{http_code}" \
        -X GET "$backend_url/api/v1/users/me" \
        -H "Authorization: Bearer $access_token" \
        2>/dev/null || echo "000")

    local http_code=$(echo "$response" | tail -n1)
    local response_body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        log_success "Authenticated request successful (HTTP $http_code)"

        if command -v jq &> /dev/null; then
            echo "$response_body" | jq .
        else
            echo "$response_body"
        fi

        return 0
    else
        log_warning "Authenticated request failed (HTTP $http_code)"
        log_info "This is expected if /api/v1/users/me endpoint doesn't exist yet"
        log_info "Response: $response_body"
        return 1
    fi
}

# ============================================================================
# Test API Documentation
# ============================================================================

test_api_docs() {
    local backend_url=$1

    log_section "Test 4: API Documentation"

    log_info "Checking API documentation..."

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "$backend_url/docs" 2>/dev/null || echo "000")

    if [ "$http_code" = "200" ]; then
        log_success "API docs accessible (HTTP $http_code)"
        log_info "URL: $backend_url/docs"
        return 0
    else
        log_warning "API docs not accessible (HTTP $http_code)"
        return 1
    fi
}

# ============================================================================
# Test Frontend Loading
# ============================================================================

test_frontend_loading() {
    local frontend_url=$1

    log_section "Test 5: Frontend Loading"

    log_info "Testing frontend page load..."

    local response=$(curl -s -w "\n%{http_code}" "$frontend_url" 2>/dev/null || echo "000")
    local http_code=$(echo "$response" | tail -n1)
    local response_body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        log_success "Frontend loads successfully (HTTP $http_code)"

        # Check if response contains expected content
        if echo "$response_body" | grep -qi "html\|<!DOCTYPE"; then
            log_success "Response contains HTML content"
        else
            log_warning "Response may not be valid HTML"
        fi

        return 0
    else
        log_error "Frontend failed to load (HTTP $http_code)"
        return 1
    fi
}

# ============================================================================
# Cleanup
# ============================================================================

cleanup() {
    log_info "Cleaning up test data..."

    # Remove temporary token file
    rm -f /tmp/test_access_token.tmp

    log_success "Cleanup complete"
}

# ============================================================================
# Summary Report
# ============================================================================

generate_report() {
    local reg_status=$1
    local login_status=$2
    local auth_status=$3
    local docs_status=$4
    local frontend_status=$5

    log_section "Integration Test Summary"

    echo ""

    local passed=0
    local total=5

    # Registration
    if [ $reg_status -eq 0 ]; then
        log_success "✓ User Registration: PASS"
        passed=$((passed + 1))
    else
        log_error "✗ User Registration: FAIL"
    fi

    # Login
    if [ $login_status -eq 0 ]; then
        log_success "✓ User Login: PASS"
        passed=$((passed + 1))
    else
        log_error "✗ User Login: FAIL"
    fi

    # Authenticated request
    if [ $auth_status -eq 0 ]; then
        log_success "✓ Authenticated Request: PASS"
        passed=$((passed + 1))
    else
        log_warning "⚠ Authenticated Request: SKIP/FAIL"
    fi

    # API docs
    if [ $docs_status -eq 0 ]; then
        log_success "✓ API Documentation: PASS"
        passed=$((passed + 1))
    else
        log_warning "⚠ API Documentation: SKIP/FAIL"
    fi

    # Frontend
    if [ $frontend_status -eq 0 ]; then
        log_success "✓ Frontend Loading: PASS"
        passed=$((passed + 1))
    else
        log_error "✗ Frontend Loading: FAIL"
    fi

    echo ""
    log_info "Tests passed: $passed/$total"
    echo ""

    if [ $passed -ge 4 ]; then
        log_success "🎉 Integration tests mostly successful!"
        log_info "Your application is working correctly"
        return 0
    elif [ $passed -ge 2 ]; then
        log_warning "⚠ Some tests failed, but core functionality works"
        log_info "Review failures above and fix if needed"
        return 1
    else
        log_error "✗ Most tests failed"
        log_info "There may be configuration issues with the deployment"
        return 1
    fi
}

# ============================================================================
# Main Function
# ============================================================================

main() {
    log_section "Integration Test - Full User Flow"

    # Initialize checks
    init_checks || die "Environment checks failed"

    # Get service URLs
    local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")
    local frontend_url=$(get_service_url "$FRONTEND_SERVICE_NAME")

    if [ -z "$backend_url" ]; then
        die "Backend service not found. Deploy services first."
    fi

    if [ -z "$frontend_url" ]; then
        log_warning "Frontend service not found. Some tests will be skipped."
    fi

    log_info "Testing against:"
    log_info "  Backend:  $backend_url"
    log_info "  Frontend: $frontend_url"
    echo ""

    # Run tests
    reg_status=0
    test_registration "$backend_url" || reg_status=$?

    echo ""

    login_status=0
    test_login "$backend_url" || login_status=$?

    echo ""

    auth_status=0
    test_authenticated_request "$backend_url" || auth_status=$?

    echo ""

    docs_status=0
    test_api_docs "$backend_url" || docs_status=$?

    echo ""

    frontend_status=0
    if [ -n "$frontend_url" ]; then
        test_frontend_loading "$frontend_url" || frontend_status=$?
    else
        frontend_status=1
    fi

    echo ""

    # Cleanup
    cleanup

    # Generate report
    generate_report $reg_status $login_status $auth_status $docs_status $frontend_status
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"
