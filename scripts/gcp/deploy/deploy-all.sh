#!/bin/bash
# deploy-all.sh - Run complete deployment pipeline
#
# This script runs all deployment steps in sequence:
# 1. Verify prerequisites
# 2. Run migrations
# 3. Deploy backend
# 4. Deploy frontend

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/../utils/common-functions.sh"

# ============================================================================
# Main Deployment Pipeline
# ============================================================================

main() {
    log_section "Complete Deployment Pipeline"

    log_info "This script will run all deployment steps:"
    log_info "  1. Verify prerequisites"
    log_info "  2. Run database migrations"
    log_info "  3. Deploy backend to Cloud Run"
    log_info "  4. Deploy frontend to Cloud Run"
    echo ""

    log_warning "Estimated time: 15-30 minutes"
    log_warning "Estimated cost: ~\$45-65/month ongoing"
    echo ""

    if ! confirm "Continue with full deployment?" "n"; then
        log_info "Deployment cancelled"
        exit 0
    fi

    # Step 1: Verify prerequisites
    log_section "Step 1/4: Verifying Prerequisites"
    if ! "$SCRIPT_DIR/1-verify-prerequisites.sh"; then
        die "Prerequisites check failed. Please fix issues and try again."
    fi

    echo ""
    if ! confirm "Prerequisites verified. Continue to migrations?" "y"; then
        log_info "Deployment stopped after prerequisites check"
        exit 0
    fi

    # Step 2: Run migrations
    log_section "Step 2/4: Running Migrations"
    if ! "$SCRIPT_DIR/2-run-migrations.sh"; then
        die "Migration failed. Please check errors above."
    fi

    echo ""
    if ! confirm "Migrations complete. Continue to backend deployment?" "y"; then
        log_info "Deployment stopped after migrations"
        exit 0
    fi

    # Step 3: Deploy backend
    log_section "Step 3/4: Deploying Backend"
    if ! "$SCRIPT_DIR/3-deploy-backend.sh"; then
        die "Backend deployment failed. Please check errors above."
    fi

    echo ""
    if ! confirm "Backend deployed. Continue to frontend deployment?" "y"; then
        log_info "Deployment stopped after backend"
        exit 0
    fi

    # Step 4: Deploy frontend
    log_section "Step 4/4: Deploying Frontend"
    if ! "$SCRIPT_DIR/4-deploy-frontend.sh"; then
        die "Frontend deployment failed. Please check errors above."
    fi

    # Success summary
    log_section "Deployment Complete!"

    local frontend_url=$(get_service_url "$FRONTEND_SERVICE_NAME")
    local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")

    echo ""
    log_success "🎉 All services deployed successfully!"
    echo ""
    log_info "Your application is now live:"
    log_info "  Frontend: $frontend_url"
    log_info "  Backend:  $backend_url"
    echo ""
    log_info "Test your application by visiting the frontend URL"
    echo ""
}

# Run main function
main "$@"
