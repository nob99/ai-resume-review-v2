#!/bin/bash
# 3-deploy-backend.sh - Deploy backend to Cloud Run
#
# This script:
# - Builds backend Docker image
# - Pushes to Artifact Registry
# - Deploys to Cloud Run
# - Configures secrets, database connection, and VPC
# - Tests health endpoint

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/../utils/common-functions.sh"

# Project root (3 levels up from this script)
PROJECT_ROOT="$SCRIPT_DIR/../../.."

# Image configuration
BACKEND_IMAGE_LOCAL="ai-resume-backend:latest"
BACKEND_IMAGE_REMOTE="$ARTIFACT_REGISTRY/backend:latest"

# ============================================================================
# Build Backend Image
# ============================================================================

build_backend() {
    log_section "Building Backend Docker Image"

    cd "$PROJECT_ROOT"

    log_info "Building image from project root with backend/Dockerfile"
    log_info "Platform: linux/amd64 (required for Cloud Run)"

    # Build from project root so we can access both backend/ and database/
    docker build --platform linux/amd64 -f backend/Dockerfile -t "$BACKEND_IMAGE_LOCAL" .

    check_status "Docker build failed"
    log_success "Backend image built successfully"
}

# ============================================================================
# Push to Artifact Registry
# ============================================================================

push_backend() {
    log_section "Pushing to Artifact Registry"

    # Configure Docker authentication
    configure_docker_auth

    # Tag image
    tag_docker_image "$BACKEND_IMAGE_LOCAL" "$BACKEND_IMAGE_REMOTE"

    # Push image
    push_docker_image "$BACKEND_IMAGE_REMOTE"

    log_success "Backend image available at: $BACKEND_IMAGE_REMOTE"
}

# ============================================================================
# Create VPC Connector (if needed)
# ============================================================================

ensure_vpc_connector() {
    log_section "VPC Connector Setup"

    log_info "Checking VPC Connector: $VPC_CONNECTOR"

    if check_vpc_connector_exists; then
        local state=$(gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" \
            --region="$REGION" --project="$PROJECT_ID" --format="value(state)" 2>/dev/null)

        if [ "$state" = "READY" ]; then
            log_success "VPC Connector already exists and is READY"
            return 0
        else
            log_warning "VPC Connector exists but state is: $state"
            log_info "Waiting for connector to be READY..."

            # Wait up to 5 minutes for connector to be ready
            local max_wait=300
            local elapsed=0
            while [ $elapsed -lt $max_wait ]; do
                state=$(gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" \
                    --region="$REGION" --project="$PROJECT_ID" --format="value(state)" 2>/dev/null)

                if [ "$state" = "READY" ]; then
                    log_success "VPC Connector is now READY"
                    return 0
                fi

                sleep 10
                elapsed=$((elapsed + 10))
                log_info "Still waiting... ($elapsed/$max_wait seconds)"
            done

            die "VPC Connector did not become READY in time"
        fi
    fi

    # Create VPC Connector
    log_warning "VPC Connector not found. Creating..."
    log_info "This will take 3-5 minutes and costs ~\$10/month"

    if ! confirm "Create VPC Connector?" "y"; then
        die "VPC Connector is required for Cloud Run to access Cloud SQL"
    fi

    log_info "Creating VPC Connector: $VPC_CONNECTOR"

    gcloud compute networks vpc-access connectors create "$VPC_CONNECTOR" \
        --region="$REGION" \
        --network="$VPC_NAME" \
        --range="10.8.0.0/28" \
        --min-instances=2 \
        --max-instances=3 \
        --machine-type=f1-micro \
        --project="$PROJECT_ID"

    check_status "Failed to create VPC Connector"
    log_success "VPC Connector created successfully"
}

# ============================================================================
# Deploy to Cloud Run
# ============================================================================

deploy_backend() {
    log_section "Deploying Backend to Cloud Run"

    log_info "Service: $BACKEND_SERVICE_NAME"
    log_info "Image: $BACKEND_IMAGE_REMOTE"
    log_info "Region: $REGION"
    log_info "Service Account: $BACKEND_SERVICE_ACCOUNT"

    # Build Cloud Run deployment command
    log_info "Deploying to Cloud Run..."

    gcloud run deploy "$BACKEND_SERVICE_NAME" \
        --image="$BACKEND_IMAGE_REMOTE" \
        --region="$REGION" \
        --platform=managed \
        --service-account="$BACKEND_SERVICE_ACCOUNT" \
        --vpc-connector="$VPC_CONNECTOR" \
        --vpc-egress=private-ranges-only \
        --add-cloudsql-instances="$SQL_INSTANCE_CONNECTION" \
        --set-secrets="DB_PASSWORD=$SECRET_DB_PASSWORD:latest,SECRET_KEY=$SECRET_JWT_KEY:latest,OPENAI_API_KEY=$SECRET_OPENAI_KEY:latest" \
        --set-env-vars="DB_HOST=/cloudsql/$SQL_INSTANCE_CONNECTION,DB_PORT=5432,DB_NAME=$DB_NAME,DB_USER=$DB_USER,PROJECT_ID=$PROJECT_ID,ENVIRONMENT=production,REDIS_HOST=none" \
        --memory=2Gi \
        --cpu=2 \
        --min-instances=0 \
        --max-instances=5 \
        --concurrency=20 \
        --timeout=600 \
        --allow-unauthenticated \
        --project="$PROJECT_ID" \
        --quiet

    check_status "Cloud Run deployment failed"
    log_success "Backend deployed successfully"
}

# ============================================================================
# Test Deployment
# ============================================================================

test_backend() {
    log_section "Testing Backend Deployment"

    # Get service URL
    log_info "Getting service URL..."
    local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")

    if [ -z "$backend_url" ]; then
        die "Failed to get backend service URL"
    fi

    log_success "Backend URL: $backend_url"

    # Test health endpoint
    log_info "Testing health endpoint..."
    log_info "URL: $backend_url/health"

    # Wait a bit for service to be ready
    sleep 5

    # Try health check
    local max_retries=5
    local retry=0

    while [ $retry -lt $max_retries ]; do
        log_info "Attempt $((retry + 1))/$max_retries..."

        if curl -f -s "$backend_url/health" > /dev/null 2>&1; then
            log_success "Health check passed!"

            # Show health response
            log_info "Health response:"
            curl -s "$backend_url/health" | jq . 2>/dev/null || curl -s "$backend_url/health"
            return 0
        fi

        retry=$((retry + 1))
        if [ $retry -lt $max_retries ]; then
            log_warning "Health check failed, retrying in 10 seconds..."
            sleep 10
        fi
    done

    log_error "Health check failed after $max_retries attempts"
    log_info "Checking Cloud Run logs for errors..."

    # Show recent logs
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$BACKEND_SERVICE_NAME" \
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

    local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")

    echo ""
    log_success "✓ Backend Deployed Successfully!"
    echo ""
    log_info "Service URL: $backend_url"
    log_info "Health Check: $backend_url/health"
    log_info "API Docs: $backend_url/docs"
    log_info "Region: $REGION"
    log_info "Min Instances: 0 (cost optimized for MVP)"
    echo ""

    log_info "Useful commands:"
    echo "  # View logs"
    echo "  gcloud logging read \"resource.labels.service_name=$BACKEND_SERVICE_NAME\" --limit=50"
    echo ""
    echo "  # View service details"
    echo "  gcloud run services describe $BACKEND_SERVICE_NAME --region=$REGION"
    echo ""
    echo "  # Update configuration"
    echo "  gcloud run services update $BACKEND_SERVICE_NAME --region=$REGION [options]"
    echo ""
}

# ============================================================================
# Main Function
# ============================================================================

main() {
    log_section "Phase 3 - Step 3: Deploy Backend"

    # Initialize checks
    init_checks || die "Environment checks failed"

    # Verify Docker is installed
    check_docker || die "Docker is required"

    # Build backend
    build_backend

    # Push to registry
    push_backend

    # Ensure VPC connector exists
    ensure_vpc_connector

    # Deploy to Cloud Run
    deploy_backend

    # Test deployment
    if test_backend; then
        display_info

        log_section "Next Steps"
        log_info "Backend is deployed and healthy!"
        echo ""
        log_info "Next:"
        log_info "  Run: ./4-deploy-frontend.sh (deploy frontend)"
        echo ""
    else
        log_warning "Deployment completed but health check failed"
        log_info "Check the logs above for errors"
        log_info "You may need to troubleshoot before proceeding"
        return 1
    fi
}

# Run main function
main "$@"
