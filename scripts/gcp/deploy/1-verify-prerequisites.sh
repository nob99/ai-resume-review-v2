#!/bin/bash
# 1-verify-prerequisites.sh - Verify all prerequisites before deployment
#
# This script checks:
# - Development tools (gcloud, docker)
# - GCP authentication and project
# - Infrastructure (VPC, Cloud SQL, Secrets)
# - Application files (Dockerfiles, migrations)

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/../utils/common-functions.sh"

# ============================================================================
# Main Verification
# ============================================================================

main() {
    log_section "Phase 3: Deployment Prerequisites Verification"

    local all_checks_passed=true

    # ========================================================================
    # 1. Development Tools
    # ========================================================================

    log_section "1. Development Tools"

    if ! check_gcloud; then
        all_checks_passed=false
    fi

    if ! check_docker; then
        all_checks_passed=false
    fi

    # Check Docker daemon is running
    if ! docker ps &> /dev/null; then
        log_error "Docker daemon is not running"
        log_info "Start Docker Desktop and try again"
        all_checks_passed=false
    else
        log_success "Docker daemon is running"
    fi

    # ========================================================================
    # 2. GCP Authentication
    # ========================================================================

    log_section "2. GCP Authentication & Project"

    if ! check_gcp_auth; then
        all_checks_passed=false
    fi

    if ! check_gcp_project; then
        all_checks_passed=false
    fi

    # ========================================================================
    # 3. Infrastructure Components
    # ========================================================================

    log_section "3. Infrastructure Components"

    # Check VPC Network
    log_info "Checking VPC Network: $VPC_NAME"
    if gcloud compute networks describe "$VPC_NAME" --project="$PROJECT_ID" &> /dev/null; then
        log_success "VPC Network exists: $VPC_NAME"
    else
        log_error "VPC Network not found: $VPC_NAME"
        log_info "Run: scripts/gcp/setup/setup-gcp-project.sh"
        all_checks_passed=false
    fi

    # Check VPC Connector
    log_info "Checking VPC Connector: $VPC_CONNECTOR"
    if check_vpc_connector_exists; then
        local connector_state=$(gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" \
            --region="$REGION" --project="$PROJECT_ID" --format="value(state)" 2>/dev/null)

        if [ "$connector_state" = "READY" ]; then
            log_success "VPC Connector is READY: $VPC_CONNECTOR"
        else
            log_warning "VPC Connector exists but state is: $connector_state"
            log_info "Expected: READY"
            all_checks_passed=false
        fi
    else
        log_error "VPC Connector not found: $VPC_CONNECTOR"
        log_info "This connector will be created automatically if needed"
        log_warning "Note: VPC Connector costs ~\$10/month"
    fi

    # Check Cloud SQL Instance
    log_info "Checking Cloud SQL Instance: $SQL_INSTANCE_NAME"
    if check_sql_instance_exists; then
        local sql_state=$(gcloud sql instances describe "$SQL_INSTANCE_NAME" \
            --project="$PROJECT_ID" --format="value(state)" 2>/dev/null)

        if [ "$sql_state" = "RUNNABLE" ]; then
            log_success "Cloud SQL instance is RUNNABLE: $SQL_INSTANCE_NAME"

            # Get and display private IP
            local private_ip=$(gcloud sql instances describe "$SQL_INSTANCE_NAME" \
                --project="$PROJECT_ID" --format="value(ipAddresses[0].ipAddress)" 2>/dev/null)
            log_info "  Private IP: $private_ip"
        else
            log_warning "Cloud SQL instance exists but state is: $sql_state"
            log_info "Expected: RUNNABLE"
            all_checks_passed=false
        fi
    else
        log_error "Cloud SQL instance not found: $SQL_INSTANCE_NAME"
        log_info "Run: scripts/gcp/setup/setup-cloud-sql.sh"
        all_checks_passed=false
    fi

    # Check Artifact Registry
    log_info "Checking Artifact Registry repository"
    if gcloud artifacts repositories describe ai-resume-review-v2 \
        --location="$REGION" --project="$PROJECT_ID" &> /dev/null; then
        log_success "Artifact Registry repository exists"
    else
        log_error "Artifact Registry repository not found"
        log_info "Run: scripts/gcp/setup/setup-gcp-project.sh"
        all_checks_passed=false
    fi

    # ========================================================================
    # 4. Secrets
    # ========================================================================

    log_section "4. Secrets in Secret Manager"

    # Check each secret
    local secrets=("$SECRET_OPENAI_KEY" "$SECRET_JWT_KEY" "$SECRET_DB_PASSWORD")
    for secret in "${secrets[@]}"; do
        log_info "Checking secret: $secret"
        if check_secret_exists "$secret"; then
            log_success "Secret exists: $secret"
        else
            log_error "Secret not found: $secret"
            log_info "Run: scripts/gcp/setup/setup-secrets.sh"
            all_checks_passed=false
        fi
    done

    # ========================================================================
    # 5. Service Accounts
    # ========================================================================

    log_section "5. Service Accounts & IAM"

    # Check backend service account
    log_info "Checking service account: $BACKEND_SERVICE_ACCOUNT"
    if gcloud iam service-accounts describe "$BACKEND_SERVICE_ACCOUNT" \
        --project="$PROJECT_ID" &> /dev/null; then
        log_success "Backend service account exists"
    else
        log_error "Backend service account not found"
        log_info "Run: scripts/gcp/setup/setup-gcp-project.sh"
        all_checks_passed=false
    fi

    # Check frontend service account
    log_info "Checking service account: $FRONTEND_SERVICE_ACCOUNT"
    if gcloud iam service-accounts describe "$FRONTEND_SERVICE_ACCOUNT" \
        --project="$PROJECT_ID" &> /dev/null; then
        log_success "Frontend service account exists"
    else
        log_error "Frontend service account not found"
        log_info "Run: scripts/gcp/setup/setup-gcp-project.sh"
        all_checks_passed=false
    fi

    # ========================================================================
    # 6. Application Files
    # ========================================================================

    log_section "6. Application Files"

    # Get project root (3 levels up from this script)
    local project_root="$SCRIPT_DIR/../../.."

    # Check backend Dockerfile
    log_info "Checking backend/Dockerfile"
    if [ -f "$project_root/backend/Dockerfile" ]; then
        log_success "Backend Dockerfile exists"
    else
        log_error "Backend Dockerfile not found"
        all_checks_passed=false
    fi

    # Check frontend Dockerfile
    log_info "Checking frontend/Dockerfile"
    if [ -f "$project_root/frontend/Dockerfile" ]; then
        log_success "Frontend Dockerfile exists"
    else
        log_error "Frontend Dockerfile not found"
        all_checks_passed=false
    fi

    # Check Alembic migrations
    log_info "Checking Alembic migrations"
    if [ -d "$project_root/backend/alembic/versions" ]; then
        local migration_count=$(find "$project_root/backend/alembic/versions" -name "*.py" ! -name "__*" | wc -l)
        if [ "$migration_count" -gt 0 ]; then
            log_success "Found $migration_count migration(s)"
        else
            log_warning "No migration files found in backend/alembic/versions/"
            log_info "You may need to create initial migration"
        fi
    else
        log_error "Alembic versions directory not found"
        all_checks_passed=false
    fi

    # ========================================================================
    # 7. Required APIs
    # ========================================================================

    log_section "7. Required GCP APIs"

    local required_apis=(
        "run.googleapis.com"
        "sqladmin.googleapis.com"
        "secretmanager.googleapis.com"
        "artifactregistry.googleapis.com"
        "vpcaccess.googleapis.com"
    )

    for api in "${required_apis[@]}"; do
        log_info "Checking API: $api"
        if check_service_enabled "$api"; then
            log_success "API enabled: $api"
        else
            log_error "API not enabled: $api"
            log_info "Run: gcloud services enable $api"
            all_checks_passed=false
        fi
    done

    # ========================================================================
    # Summary
    # ========================================================================

    log_section "Verification Summary"

    if [ "$all_checks_passed" = true ]; then
        log_success "✓ All prerequisites verified successfully!"
        echo ""
        log_info "Next steps:"
        log_info "  1. Run: ./2-run-migrations.sh (initialize database schema)"
        log_info "  2. Run: ./3-deploy-backend.sh (deploy backend to Cloud Run)"
        log_info "  3. Run: ./4-deploy-frontend.sh (deploy frontend to Cloud Run)"
        echo ""
        return 0
    else
        log_error "✗ Some prerequisites are missing or misconfigured"
        echo ""
        log_info "Please fix the issues above and run this script again"
        echo ""
        return 1
    fi
}

# Run main function
main "$@"
