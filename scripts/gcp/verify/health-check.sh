#!/bin/bash
# health-check.sh - Quick smoke test of deployed services
#
# This script performs basic health checks on:
# - Backend service (health endpoint)
# - Frontend service (accessibility)
# - Database connectivity (via backend)

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/../utils/common-functions.sh"

# ============================================================================
# Check Backend Health
# ============================================================================

check_backend() {
    log_section "Backend Health Check"

    log_info "Checking if backend service exists..."

    local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")

    if [ -z "$backend_url" ]; then
        log_error "Backend service not found: $BACKEND_SERVICE_NAME"
        return 1
    fi

    log_success "Backend service URL: $backend_url"

    # Check health endpoint
    log_info "Testing /health endpoint..."

    local health_response=$(curl -s -w "\n%{http_code}" "$backend_url/health" 2>/dev/null || echo "000")
    local http_code=$(echo "$health_response" | tail -n1)
    local response_body=$(echo "$health_response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        log_success "Health endpoint responding (HTTP $http_code)"

        # Pretty print JSON if jq is available
        if command -v jq &> /dev/null; then
            echo "$response_body" | jq .
        else
            echo "$response_body"
        fi

        # Check database status from health response
        if echo "$response_body" | grep -q "database.*ok\|status.*healthy"; then
            log_success "Database connectivity: OK"
        else
            log_warning "Could not verify database status from health response"
        fi

        return 0
    else
        log_error "Health endpoint failed (HTTP $http_code)"
        log_info "Response: $response_body"
        return 1
    fi
}

# ============================================================================
# Check Frontend Health
# ============================================================================

check_frontend() {
    log_section "Frontend Health Check"

    log_info "Checking if frontend service exists..."

    local frontend_url=$(get_service_url "$FRONTEND_SERVICE_NAME")

    if [ -z "$frontend_url" ]; then
        log_error "Frontend service not found: $FRONTEND_SERVICE_NAME"
        return 1
    fi

    log_success "Frontend service URL: $frontend_url"

    # Check frontend accessibility
    log_info "Testing frontend accessibility..."

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "$frontend_url" 2>/dev/null || echo "000")

    if [ "$http_code" = "200" ]; then
        log_success "Frontend is accessible (HTTP $http_code)"
        return 0
    else
        log_error "Frontend check failed (HTTP $http_code)"
        return 1
    fi
}

# ============================================================================
# Check API Documentation
# ============================================================================

check_api_docs() {
    log_section "API Documentation Check"

    local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")

    if [ -z "$backend_url" ]; then
        log_warning "Backend service not found, skipping API docs check"
        return 1
    fi

    log_info "Testing /docs endpoint..."

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "$backend_url/docs" 2>/dev/null || echo "000")

    if [ "$http_code" = "200" ]; then
        log_success "API documentation accessible at: $backend_url/docs"
        return 0
    else
        log_warning "API docs not accessible (HTTP $http_code)"
        return 1
    fi
}

# ============================================================================
# Summary Report
# ============================================================================

generate_report() {
    local backend_status=$1
    local frontend_status=$2

    log_section "Health Check Summary"

    echo ""

    # Backend summary
    if [ $backend_status -eq 0 ]; then
        log_success "✓ Backend: Healthy"
    else
        log_error "✗ Backend: Unhealthy"
    fi

    # Frontend summary
    if [ $frontend_status -eq 0 ]; then
        log_success "✓ Frontend: Healthy"
    else
        log_error "✗ Frontend: Unhealthy"
    fi

    echo ""

    # Overall status
    if [ $backend_status -eq 0 ] && [ $frontend_status -eq 0 ]; then
        log_success "🎉 All services are healthy!"
        echo ""

        local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")
        local frontend_url=$(get_service_url "$FRONTEND_SERVICE_NAME")

        log_info "Service URLs:"
        log_info "  Frontend: $frontend_url"
        log_info "  Backend:  $backend_url"
        log_info "  API Docs: $backend_url/docs"
        echo ""

        return 0
    else
        log_error "⚠ Some services are unhealthy"
        echo ""
        log_info "Troubleshooting:"
        log_info "  1. Check Cloud Run logs:"
        log_info "     gcloud logging read \"resource.labels.service_name=$BACKEND_SERVICE_NAME\" --limit=50"
        log_info "  2. Check service status:"
        log_info "     gcloud run services describe $BACKEND_SERVICE_NAME --region=$REGION"
        log_info "  3. Verify secrets are accessible:"
        log_info "     gcloud secrets list"
        echo ""

        return 1
    fi
}

# ============================================================================
# Main Function
# ============================================================================

main() {
    log_section "Health Check - Deployed Services"

    # Initialize checks
    init_checks || die "Environment checks failed"

    # Check backend
    backend_status=0
    check_backend || backend_status=$?

    echo ""

    # Check frontend
    frontend_status=0
    check_frontend || frontend_status=$?

    echo ""

    # Check API docs (optional)
    check_api_docs || true

    # Generate summary report
    generate_report $backend_status $frontend_status
}

# Run main function
main "$@"
