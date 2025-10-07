#!/bin/bash
# 4-deploy-frontend.sh - Deploy frontend to Cloud Run
#
# This script:
# - Gets backend URL from deployed service
# - Builds frontend Docker image with backend URL
# - Pushes to Artifact Registry
# - Deploys to Cloud Run
# - Tests the deployment

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/../utils/common-functions.sh"

# Project root (3 levels up from this script)
PROJECT_ROOT="$SCRIPT_DIR/../../.."

# Image configuration
FRONTEND_IMAGE_LOCAL="ai-resume-frontend:latest"
FRONTEND_IMAGE_REMOTE="$ARTIFACT_REGISTRY/frontend:latest"

# ============================================================================
# Get Backend URL
# ============================================================================

get_backend_url() {
    log_section "Getting Backend URL"

    log_info "Retrieving backend service URL..."

    local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")

    if [ -z "$backend_url" ]; then
        die "Backend service not found. Deploy backend first: ./3-deploy-backend.sh"
    fi

    log_success "Backend URL: $backend_url"

    # Verify backend is healthy
    log_info "Verifying backend health..."

    if curl -f -s "$backend_url/health" > /dev/null 2>&1; then
        log_success "Backend is healthy"
    else
        log_warning "Backend health check failed"
        if ! confirm "Continue anyway?" "n"; then
            die "Deploy backend successfully first"
        fi
    fi

    echo "$backend_url"
}

# ============================================================================
# Build Frontend Image
# ============================================================================

build_frontend() {
    local backend_url=$1

    log_section "Building Frontend Docker Image"

    cd "$PROJECT_ROOT"

    log_info "Building image from: ./frontend"
    log_info "Backend URL: $backend_url"
    log_info "Platform: linux/amd64 (required for Cloud Run)"

    # Build with backend URL as build arg
    build_docker_image "./frontend" "$FRONTEND_IMAGE_LOCAL" "--build-arg NEXT_PUBLIC_API_URL=$backend_url"

    log_success "Frontend image built successfully"
}

# ============================================================================
# Push to Artifact Registry
# ============================================================================

push_frontend() {
    log_section "Pushing to Artifact Registry"

    # Configure Docker authentication
    configure_docker_auth

    # Tag image
    tag_docker_image "$FRONTEND_IMAGE_LOCAL" "$FRONTEND_IMAGE_REMOTE"

    # Push image
    push_docker_image "$FRONTEND_IMAGE_REMOTE"

    log_success "Frontend image available at: $FRONTEND_IMAGE_REMOTE"
}

# ============================================================================
# Deploy to Cloud Run
# ============================================================================

deploy_frontend() {
    local backend_url=$1

    log_section "Deploying Frontend to Cloud Run"

    log_info "Service: $FRONTEND_SERVICE_NAME"
    log_info "Image: $FRONTEND_IMAGE_REMOTE"
    log_info "Region: $REGION"
    log_info "Service Account: $FRONTEND_SERVICE_ACCOUNT"

    # Build Cloud Run deployment command
    log_info "Deploying to Cloud Run..."

    gcloud run deploy "$FRONTEND_SERVICE_NAME" \
        --image="$FRONTEND_IMAGE_REMOTE" \
        --region="$REGION" \
        --platform=managed \
        --service-account="$FRONTEND_SERVICE_ACCOUNT" \
        --set-env-vars="NEXT_PUBLIC_API_URL=$backend_url,NODE_ENV=production,NEXT_TELEMETRY_DISABLED=1" \
        --memory=512Mi \
        --cpu=1 \
        --min-instances=0 \
        --max-instances=5 \
        --concurrency=80 \
        --timeout=300 \
        --allow-unauthenticated \
        --project="$PROJECT_ID" \
        --quiet

    check_status "Cloud Run deployment failed"
    log_success "Frontend deployed successfully"
}

# ============================================================================
# Test Deployment
# ============================================================================

test_frontend() {
    log_section "Testing Frontend Deployment"

    # Get service URL
    log_info "Getting service URL..."
    local frontend_url=$(get_service_url "$FRONTEND_SERVICE_NAME")

    if [ -z "$frontend_url" ]; then
        die "Failed to get frontend service URL"
    fi

    log_success "Frontend URL: $frontend_url"

    # Test frontend
    log_info "Testing frontend..."
    log_info "URL: $frontend_url"

    # Wait a bit for service to be ready
    sleep 5

    # Try to access frontend
    local max_retries=5
    local retry=0

    while [ $retry -lt $max_retries ]; do
        log_info "Attempt $((retry + 1))/$max_retries..."

        if curl -f -s "$frontend_url" > /dev/null 2>&1; then
            log_success "Frontend is accessible!"
            return 0
        fi

        retry=$((retry + 1))
        if [ $retry -lt $max_retries ]; then
            log_warning "Frontend not accessible yet, retrying in 10 seconds..."
            sleep 10
        fi
    done

    log_error "Frontend check failed after $max_retries attempts"
    log_info "Checking Cloud Run logs for errors..."

    # Show recent logs
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$FRONTEND_SERVICE_NAME" \
        --limit=20 \
        --project="$PROJECT_ID" \
        --format="table(timestamp,severity,textPayload)" 2>/dev/null || true

    return 1
}

# ============================================================================
# Display Information
# ============================================================================

display_info() {
    log_section "Deployment Information"

    local frontend_url=$(get_service_url "$FRONTEND_SERVICE_NAME")
    local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")

    echo ""
    log_success "✓ Frontend Deployed Successfully!"
    echo ""
    log_info "Frontend URL: $frontend_url"
    log_info "Backend URL:  $backend_url"
    log_info "Region: $REGION"
    echo ""

    log_section "🎉 Application is Live!"
    echo ""
    log_info "Visit your application:"
    echo "  $frontend_url"
    echo ""
    log_info "Test the API:"
    echo "  $backend_url/docs"
    echo ""

    log_info "Useful commands:"
    echo "  # View frontend logs"
    echo "  gcloud logging read \"resource.labels.service_name=$FRONTEND_SERVICE_NAME\" --limit=50"
    echo ""
    echo "  # View backend logs"
    echo "  gcloud logging read \"resource.labels.service_name=$BACKEND_SERVICE_NAME\" --limit=50"
    echo ""
    echo "  # View all Cloud Run services"
    echo "  gcloud run services list --region=$REGION"
    echo ""
}

# ============================================================================
# Main Function
# ============================================================================

main() {
    log_section "Phase 3 - Step 4: Deploy Frontend"

    # Initialize checks
    init_checks || die "Environment checks failed"

    # Verify Docker is installed
    check_docker || die "Docker is required"

    # Get backend URL
    local backend_url=$(get_backend_url)

    # Build frontend
    build_frontend "$backend_url"

    # Push to registry
    push_frontend

    # Deploy to Cloud Run
    deploy_frontend "$backend_url"

    # Test deployment
    if test_frontend; then
        display_info

        log_section "Next Steps"
        log_info "Deployment complete! Consider these next steps:"
        echo ""
        log_info "1. Test full user flow:"
        log_info "   - Register a new account"
        log_info "   - Login"
        log_info "   - Upload a resume"
        log_info "   - Get analysis results"
        echo ""
        log_info "2. Set up monitoring:"
        log_info "   - Cloud Monitoring dashboard"
        log_info "   - Uptime checks"
        log_info "   - Alert policies"
        echo ""
        log_info "3. Optional enhancements:"
        log_info "   - Custom domain (Cloud Run domain mapping)"
        log_info "   - CDN (Cloud CDN for static assets)"
        log_info "   - CI/CD (GitHub Actions automation)"
        echo ""
    else
        log_warning "Deployment completed but frontend check failed"
        log_info "Check the logs above for errors"
        log_info "The service may still be starting up - try accessing it in a few minutes"
        return 1
    fi
}

# Run main function
main "$@"
