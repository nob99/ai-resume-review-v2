#!/bin/bash
# deploy.sh - GCP Complete Deployment Pipeline
#
# Usage: ./deploy.sh [options]
# Options:
#   --step=<step>    Run specific step only (verify, migrate, backend, frontend, all)
#   --dry-run        Show what would be executed
#   --skip-tests     Skip health checks and tests
#   --help           Show this help message
#
# Examples:
#   ./deploy.sh                      # Run all steps
#   ./deploy.sh --step=verify        # Prerequisites check only
#   ./deploy.sh --step=backend       # Deploy backend only
#   ./deploy.sh --dry-run            # Preview all steps
#   ./deploy.sh --step=migrate --dry-run  # Preview migrations
#
# What it does:
#   1. Verifies prerequisites (gcloud, Docker, GCP resources)
#   2. Runs database migrations (via Cloud SQL Proxy)
#   3. Deploys backend to Cloud Run (FastAPI)
#   4. Deploys frontend to Cloud Run (Next.js)
#
# Total time: ~15-30 minutes
# Cost: Deployment is free, ongoing costs ~$45-65/month

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/../utils/common-functions.sh"

# Project root (3 levels up from this script)
PROJECT_ROOT="$SCRIPT_DIR/../../.."

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN=false
STEP=""
SKIP_TESTS=false

# Cloud SQL Proxy configuration
PROXY_BINARY="$SCRIPT_DIR/cloud-sql-proxy"
PROXY_VERSION="v2.8.0"
MIGRATION_TABLE="schema_migrations"

# Image configuration
BACKEND_IMAGE_LOCAL="ai-resume-backend:latest"
BACKEND_IMAGE_REMOTE="$ARTIFACT_REGISTRY/backend:latest"
FRONTEND_IMAGE_LOCAL="ai-resume-frontend:latest"
FRONTEND_IMAGE_REMOTE="$ARTIFACT_REGISTRY/frontend:latest"

# ============================================================================
# Helper Functions
# ============================================================================

show_help() {
    grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //' | sed 's/^#//'
}

dry_run() {
    local command="$1"
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would execute: $command"
        return 0
    else
        eval "$command"
        return $?
    fi
}

# ============================================================================
# Step 1: Verify Prerequisites
# ============================================================================

step_verify_prerequisites() {
    log_section "Step 1/4: Verify Prerequisites"

    local all_checks_passed=true

    # Development Tools
    log_info "Checking development tools..."

    if ! check_gcloud; then
        all_checks_passed=false
    fi

    if ! check_docker; then
        all_checks_passed=false
    fi

    # Check Docker daemon
    if [ "$DRY_RUN" = false ]; then
        if ! docker ps &> /dev/null; then
            log_error "Docker daemon is not running"
            log_info "Start Docker Desktop and try again"
            all_checks_passed=false
        else
            log_success "Docker daemon is running"
        fi
    else
        log_info "[DRY-RUN] Would check if Docker daemon is running"
    fi

    # GCP Authentication
    log_info "Checking GCP authentication..."

    if ! check_gcp_auth; then
        all_checks_passed=false
    fi

    if ! check_gcp_project; then
        all_checks_passed=false
    fi

    # Infrastructure Components
    log_info "Checking infrastructure components..."

    # VPC Network
    if [ "$DRY_RUN" = false ]; then
        if gcloud compute networks describe "$VPC_NAME" --project="$PROJECT_ID" &> /dev/null; then
            log_success "VPC Network exists: $VPC_NAME"
        else
            log_error "VPC Network not found: $VPC_NAME"
            log_info "Run: scripts/gcp/setup/setup-gcp-project.sh"
            all_checks_passed=false
        fi
    else
        log_info "[DRY-RUN] Would check VPC Network: $VPC_NAME"
    fi

    # VPC Connector
    if [ "$DRY_RUN" = false ]; then
        if check_vpc_connector_exists; then
            local connector_state=$(gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" \
                --region="$REGION" --project="$PROJECT_ID" --format="value(state)" 2>/dev/null)

            if [ "$connector_state" = "READY" ]; then
                log_success "VPC Connector is READY: $VPC_CONNECTOR"
            else
                log_warning "VPC Connector state: $connector_state (expected: READY)"
                all_checks_passed=false
            fi
        else
            log_warning "VPC Connector not found (will be created if needed): $VPC_CONNECTOR"
        fi
    else
        log_info "[DRY-RUN] Would check VPC Connector: $VPC_CONNECTOR"
    fi

    # Cloud SQL Instance
    if [ "$DRY_RUN" = false ]; then
        if check_sql_instance_exists; then
            local sql_state=$(gcloud sql instances describe "$SQL_INSTANCE_NAME" \
                --project="$PROJECT_ID" --format="value(state)" 2>/dev/null)

            if [ "$sql_state" = "RUNNABLE" ]; then
                log_success "Cloud SQL instance is RUNNABLE: $SQL_INSTANCE_NAME"
            else
                log_warning "Cloud SQL state: $sql_state (expected: RUNNABLE)"
                all_checks_passed=false
            fi
        else
            log_error "Cloud SQL instance not found: $SQL_INSTANCE_NAME"
            log_info "Run: scripts/gcp/setup/setup-cloud-sql.sh"
            all_checks_passed=false
        fi
    else
        log_info "[DRY-RUN] Would check Cloud SQL instance: $SQL_INSTANCE_NAME"
    fi

    # Artifact Registry
    if [ "$DRY_RUN" = false ]; then
        if gcloud artifacts repositories describe ai-resume-review-v2 \
            --location="$REGION" --project="$PROJECT_ID" &> /dev/null; then
            log_success "Artifact Registry repository exists"
        else
            log_error "Artifact Registry repository not found"
            log_info "Run: scripts/gcp/setup/setup-gcp-project.sh"
            all_checks_passed=false
        fi
    else
        log_info "[DRY-RUN] Would check Artifact Registry repository"
    fi

    # Secrets
    log_info "Checking secrets..."
    local secrets=("$SECRET_OPENAI_KEY" "$SECRET_JWT_KEY" "$SECRET_DB_PASSWORD")

    if [ "$DRY_RUN" = false ]; then
        for secret in "${secrets[@]}"; do
            if check_secret_exists "$secret"; then
                log_success "Secret exists: $secret"
            else
                log_error "Secret not found: $secret"
                log_info "Run: scripts/gcp/setup/setup-secrets.sh"
                all_checks_passed=false
            fi
        done
    else
        log_info "[DRY-RUN] Would check secrets: ${secrets[*]}"
    fi

    # Service Accounts
    log_info "Checking service accounts..."

    if [ "$DRY_RUN" = false ]; then
        if gcloud iam service-accounts describe "$BACKEND_SERVICE_ACCOUNT" \
            --project="$PROJECT_ID" &> /dev/null; then
            log_success "Backend service account exists"
        else
            log_error "Backend service account not found"
            all_checks_passed=false
        fi

        if gcloud iam service-accounts describe "$FRONTEND_SERVICE_ACCOUNT" \
            --project="$PROJECT_ID" &> /dev/null; then
            log_success "Frontend service account exists"
        else
            log_error "Frontend service account not found"
            all_checks_passed=false
        fi
    else
        log_info "[DRY-RUN] Would check service accounts"
    fi

    # Application Files
    log_info "Checking application files..."

    if [ ! -f "$PROJECT_ROOT/backend/Dockerfile" ]; then
        log_error "Backend Dockerfile not found"
        all_checks_passed=false
    else
        log_success "Backend Dockerfile exists"
    fi

    if [ ! -f "$PROJECT_ROOT/frontend/Dockerfile" ]; then
        log_error "Frontend Dockerfile not found"
        all_checks_passed=false
    else
        log_success "Frontend Dockerfile exists"
    fi

    # Summary
    if [ "$all_checks_passed" = true ]; then
        log_success "✓ All prerequisites verified"
        return 0
    else
        log_error "✗ Some prerequisites are missing"
        log_info "Fix the issues above before proceeding"
        return 1
    fi
}

# ============================================================================
# Step 2: Database Migrations
# ============================================================================

download_proxy() {
    if [ -f "$PROXY_BINARY" ]; then
        log_success "Cloud SQL Proxy already exists"
        return 0
    fi

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would download Cloud SQL Proxy $PROXY_VERSION"
        return 0
    fi

    log_info "Downloading Cloud SQL Proxy $PROXY_VERSION..."

    local os_type=""
    case "$(uname -s)" in
        Darwin*) os_type="darwin" ;;
        Linux*) os_type="linux" ;;
        *) die "Unsupported OS: $(uname -s)" ;;
    esac

    local arch_type=""
    case "$(uname -m)" in
        x86_64) arch_type="amd64" ;;
        arm64|aarch64) arch_type="arm64" ;;
        *) die "Unsupported architecture: $(uname -m)" ;;
    esac

    local download_url="https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/${PROXY_VERSION}/cloud-sql-proxy.${os_type}.${arch_type}"

    if ! curl -o "$PROXY_BINARY" -L "$download_url"; then
        die "Failed to download Cloud SQL Proxy"
    fi

    chmod +x "$PROXY_BINARY"
    log_success "Cloud SQL Proxy downloaded"
}

step_run_migrations() {
    log_section "Step 2/4: Database Migrations"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would download Cloud SQL Proxy"
        log_info "[DRY-RUN] Would connect to: $SQL_INSTANCE_CONNECTION"
        log_info "[DRY-RUN] Would run migrations from: database/migrations/"
        log_info "[DRY-RUN] Would create migration tracking table: $MIGRATION_TABLE"
        return 0
    fi

    # Check Cloud SQL instance
    if ! check_sql_instance_exists; then
        die "Cloud SQL instance not found: $SQL_INSTANCE_NAME"
    fi

    # Download proxy
    download_proxy

    # Get database password
    log_info "Retrieving database password..."
    local db_password=$(get_secret "$SECRET_DB_PASSWORD")
    if [ -z "$db_password" ]; then
        die "Failed to retrieve database password"
    fi
    log_success "Database password retrieved"

    # Start Cloud SQL Proxy
    log_info "Starting Cloud SQL Proxy..."
    "$PROXY_BINARY" "$SQL_INSTANCE_CONNECTION" &
    local proxy_pid=$!
    trap "kill $proxy_pid 2>/dev/null || true" EXIT

    sleep 5

    if ! kill -0 $proxy_pid 2>/dev/null; then
        die "Cloud SQL Proxy failed to start"
    fi
    log_success "Cloud SQL Proxy running (PID: $proxy_pid)"

    # Check psql
    if ! command -v psql &> /dev/null; then
        log_error "psql command not found"
        log_info "Install: brew install postgresql (macOS) or apt-get install postgresql-client (Ubuntu)"
        die "psql is required"
    fi

    # Create migration table
    log_info "Creating migration tracking table..."
    PGPASSWORD="$db_password" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" << 'EOF' 2>/dev/null || true
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF
    log_success "Migration tracking table ready"

    # Find migrations
    local migration_dir="$PROJECT_ROOT/database/migrations"
    if [ ! -d "$migration_dir" ]; then
        die "Migration directory not found: $migration_dir"
    fi

    local migration_files=$(find "$migration_dir" -name "*.sql" ! -name "*rollback*" | sort)

    if [ -z "$migration_files" ]; then
        log_warning "No migration files found"
        kill $proxy_pid 2>/dev/null || true
        return 0
    fi

    local total_migrations=$(echo "$migration_files" | wc -l | tr -d ' ')
    local applied_count=0
    local skipped_count=0

    log_info "Found $total_migrations migration files"
    echo ""

    # Run migrations
    while IFS= read -r migration_file; do
        local migration_name=$(basename "$migration_file")
        log_info "Checking: $migration_name"

        local count=$(PGPASSWORD="$db_password" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -t -c \
            "SELECT COUNT(*) FROM $MIGRATION_TABLE WHERE version = '$migration_name';" 2>/dev/null | tr -d ' ')

        if [ "$count" -gt 0 ]; then
            log_info "  ↳ Already applied, skipping"
            skipped_count=$((skipped_count + 1))
            continue
        fi

        log_info "  ↳ Applying..."

        if PGPASSWORD="$db_password" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -f "$migration_file" > /dev/null 2>&1; then
            PGPASSWORD="$db_password" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -c \
                "INSERT INTO $MIGRATION_TABLE (version) VALUES ('$migration_name');" >/dev/null 2>&1
            log_success "  ✓ Applied: $migration_name"
            applied_count=$((applied_count + 1))
        else
            log_error "  ✗ Failed: $migration_name"
            die "Migration failed"
        fi
    done <<< "$migration_files"

    echo ""
    log_info "Summary: Applied=$applied_count, Skipped=$skipped_count, Total=$total_migrations"

    if [ $applied_count -gt 0 ]; then
        log_success "Migrations completed"
    else
        log_success "Database already up to date"
    fi

    # Cleanup
    kill $proxy_pid 2>/dev/null || true
    wait $proxy_pid 2>/dev/null || true
}

# ============================================================================
# Step 3: Deploy Backend
# ============================================================================

step_deploy_backend() {
    log_section "Step 3/4: Deploy Backend"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would build backend Docker image"
        log_info "  Context: $PROJECT_ROOT"
        log_info "  Dockerfile: backend/Dockerfile"
        log_info "  Platform: linux/amd64"
        log_info "[DRY-RUN] Would push to: $BACKEND_IMAGE_REMOTE"
        log_info "[DRY-RUN] Would deploy to Cloud Run: $BACKEND_SERVICE_NAME"
        log_info "  Memory: 2GB"
        log_info "  CPU: 2"
        log_info "  Min instances: 0"
        log_info "  Max instances: 5"
        return 0
    fi

    # Verify Docker is running
    check_docker || die "Docker is required"

    # Build backend image
    log_info "Building backend Docker image..."
    cd "$PROJECT_ROOT"

    docker build --platform linux/amd64 -f backend/Dockerfile -t "$BACKEND_IMAGE_LOCAL" .
    check_status "Docker build failed"
    log_success "Backend image built"

    # Configure Docker auth
    configure_docker_auth

    # Tag and push
    tag_docker_image "$BACKEND_IMAGE_LOCAL" "$BACKEND_IMAGE_REMOTE"
    push_docker_image "$BACKEND_IMAGE_REMOTE"

    # Ensure VPC connector exists (create if needed)
    log_info "Checking VPC Connector..."
    if check_vpc_connector_exists; then
        log_success "VPC Connector exists"
    else
        log_warning "VPC Connector not found, creating..."
        log_info "This will take 3-5 minutes and costs ~$10/month"

        if ! confirm "Create VPC Connector?" "y"; then
            die "VPC Connector required for Cloud SQL access"
        fi

        gcloud compute networks vpc-access connectors create "$VPC_CONNECTOR" \
            --region="$REGION" \
            --network="$VPC_NAME" \
            --range="10.8.0.0/28" \
            --min-instances=2 \
            --max-instances=3 \
            --machine-type=f1-micro \
            --project="$PROJECT_ID"

        check_status "Failed to create VPC Connector"
        log_success "VPC Connector created"
    fi

    # Deploy to Cloud Run
    log_info "Deploying to Cloud Run..."

    # Load CORS origins from config (fallback to hardcoded if not available)
    if [ -z "$ALLOWED_ORIGINS" ]; then
        log_warning "ALLOWED_ORIGINS not set, using fallback configuration"
        # Try to load from config
        CONFIG_FILE="$PROJECT_ROOT/config/environments.yml"
        if command -v yq &> /dev/null && [ -f "$CONFIG_FILE" ]; then
            # Determine environment from service name
            if [[ "$BACKEND_SERVICE_NAME" == *"-staging"* ]]; then
                ALLOWED_ORIGINS=$(yq ".staging.cors.allowed_origins | join(\",\")" "$CONFIG_FILE" 2>/dev/null || echo "")
            else
                ALLOWED_ORIGINS=$(yq ".production.cors.allowed_origins | join(\",\")" "$CONFIG_FILE" 2>/dev/null || echo "")
            fi
        fi
        # Final fallback if config loading failed
        if [ -z "$ALLOWED_ORIGINS" ]; then
            ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8000"
        fi
    fi
    log_info "CORS origins: $ALLOWED_ORIGINS"

    gcloud run deploy "$BACKEND_SERVICE_NAME" \
        --image="$BACKEND_IMAGE_REMOTE" \
        --region="$REGION" \
        --platform=managed \
        --service-account="$BACKEND_SERVICE_ACCOUNT" \
        --vpc-connector="$VPC_CONNECTOR" \
        --vpc-egress=private-ranges-only \
        --add-cloudsql-instances="$SQL_INSTANCE_CONNECTION" \
        --set-secrets="DB_PASSWORD=$SECRET_DB_PASSWORD:latest,SECRET_KEY=$SECRET_JWT_KEY:latest,OPENAI_API_KEY=$SECRET_OPENAI_KEY:latest" \
        --set-env-vars="DB_HOST=/cloudsql/$SQL_INSTANCE_CONNECTION,DB_PORT=5432,DB_NAME=$DB_NAME,DB_USER=$DB_USER,PROJECT_ID=$PROJECT_ID,ENVIRONMENT=production,REDIS_HOST=none,ALLOWED_ORIGINS=$ALLOWED_ORIGINS" \
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
    log_success "Backend deployed"

    # Test backend
    if [ "$SKIP_TESTS" = false ]; then
        log_info "Testing backend..."
        local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")

        sleep 5

        local max_retries=5
        local retry=0

        while [ $retry -lt $max_retries ]; do
            log_info "Health check attempt $((retry + 1))/$max_retries..."

            if curl -f -s "$backend_url/health" > /dev/null 2>&1; then
                log_success "Backend health check passed!"
                log_info "Backend URL: $backend_url"
                return 0
            fi

            retry=$((retry + 1))
            if [ $retry -lt $max_retries ]; then
                sleep 10
            fi
        done

        log_warning "Backend health check failed (may still be starting)"
    fi
}

# ============================================================================
# Step 4: Deploy Frontend
# ============================================================================

step_deploy_frontend() {
    log_section "Step 4/4: Deploy Frontend"

    # Get backend URL
    local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")

    if [ -z "$backend_url" ]; then
        die "Backend service not found. Deploy backend first."
    fi

    # Determine environment name from service name
    local env_name="prod"
    if [[ "$FRONTEND_SERVICE_NAME" == *"-staging"* ]]; then
        env_name="staging"
    fi

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Backend URL: $backend_url"
        log_info "[DRY-RUN] Environment: $env_name"
        log_info "[DRY-RUN] Would build frontend Docker image"
        log_info "  Context: $PROJECT_ROOT/frontend"
        log_info "  Build arg: NEXT_PUBLIC_API_URL=$backend_url"
        log_info "  Build arg: NEXT_PUBLIC_ENV_NAME=$env_name"
        log_info "  Platform: linux/amd64"
        log_info "[DRY-RUN] Would push to: $FRONTEND_IMAGE_REMOTE"
        log_info "[DRY-RUN] Would deploy to Cloud Run: $FRONTEND_SERVICE_NAME"
        log_info "  Memory: 512MB"
        log_info "  CPU: 1"
        log_info "  Min instances: 0"
        log_info "  Max instances: 5"
        return 0
    fi

    # Verify Docker is running
    check_docker || die "Docker is required"

    # Verify backend health
    if [ "$SKIP_TESTS" = false ]; then
        log_info "Verifying backend health..."
        if curl -f -s "$backend_url/health" > /dev/null 2>&1; then
            log_success "Backend is healthy"
        else
            log_warning "Backend health check failed"
            if ! confirm "Continue anyway?" "n"; then
                die "Deploy backend successfully first"
            fi
        fi
    fi

    # Build frontend image
    log_info "Building frontend Docker image..."
    log_info "Backend URL: $backend_url"
    log_info "Environment: $env_name"

    cd "$PROJECT_ROOT"

    docker build \
        --no-cache \
        --platform linux/amd64 \
        --build-arg "NEXT_PUBLIC_API_URL=$backend_url" \
        --build-arg "NEXT_PUBLIC_ENV_NAME=$env_name" \
        -t "$FRONTEND_IMAGE_LOCAL" \
        "./frontend"

    check_status "Docker build failed"
    log_success "Frontend image built"

    # Configure Docker auth
    configure_docker_auth

    # Tag and push
    tag_docker_image "$FRONTEND_IMAGE_LOCAL" "$FRONTEND_IMAGE_REMOTE"
    push_docker_image "$FRONTEND_IMAGE_REMOTE"

    # Deploy to Cloud Run
    log_info "Deploying to Cloud Run..."

    gcloud run deploy "$FRONTEND_SERVICE_NAME" \
        --image="$FRONTEND_IMAGE_REMOTE" \
        --region="$REGION" \
        --platform=managed \
        --service-account="$FRONTEND_SERVICE_ACCOUNT" \
        --set-env-vars="NODE_ENV=production,NEXT_TELEMETRY_DISABLED=1" \
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
    log_success "Frontend deployed"

    # Test frontend
    if [ "$SKIP_TESTS" = false ]; then
        log_info "Testing frontend..."
        local frontend_url=$(get_service_url "$FRONTEND_SERVICE_NAME")

        sleep 5

        local max_retries=5
        local retry=0

        while [ $retry -lt $max_retries ]; do
            log_info "Health check attempt $((retry + 1))/$max_retries..."

            if curl -f -s "$frontend_url" > /dev/null 2>&1; then
                log_success "Frontend is accessible!"
                log_info "Frontend URL: $frontend_url"
                return 0
            fi

            retry=$((retry + 1))
            if [ $retry -lt $max_retries ]; then
                sleep 10
            fi
        done

        log_warning "Frontend check failed (may still be starting)"
    fi
}

# ============================================================================
# Main Function
# ============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --step=*)
                STEP="${1#*=}"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    log_section "GCP Deployment Pipeline"

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY-RUN MODE - No changes will be made"
    fi

    if [ "$SKIP_TESTS" = true ]; then
        log_warning "SKIP-TESTS MODE - Health checks will be skipped"
    fi

    # Run initialization checks
    init_checks || die "Environment checks failed"

    # Execute requested step or all steps
    if [ -n "$STEP" ]; then
        case "$STEP" in
            verify)
                step_verify_prerequisites
                ;;
            migrate)
                step_run_migrations
                ;;
            backend)
                step_deploy_backend
                ;;
            frontend)
                step_deploy_frontend
                ;;
            all)
                step_verify_prerequisites || die "Prerequisites check failed"
                echo ""
                step_run_migrations || die "Migrations failed"
                echo ""
                step_deploy_backend || die "Backend deployment failed"
                echo ""
                step_deploy_frontend || die "Frontend deployment failed"
                ;;
            *)
                log_error "Unknown step: $STEP"
                log_info "Valid steps: verify, migrate, backend, frontend, all"
                exit 1
                ;;
        esac
    else
        # Run all steps
        if [ "$DRY_RUN" = false ]; then
            if ! confirm "This will deploy the complete application. Continue?" "y"; then
                log_info "Deployment cancelled"
                exit 0
            fi
        fi

        step_verify_prerequisites || die "Prerequisites check failed"
        echo ""
        step_run_migrations || die "Migrations failed"
        echo ""
        step_deploy_backend || die "Backend deployment failed"
        echo ""
        step_deploy_frontend || die "Frontend deployment failed"
        echo ""

        # Final summary
        log_section "Deployment Complete!"

        local frontend_url=$(get_service_url "$FRONTEND_SERVICE_NAME")
        local backend_url=$(get_service_url "$BACKEND_SERVICE_NAME")

        log_success "🎉 Application deployed successfully!"
        echo ""
        log_info "Your application is now live:"
        log_info "  Frontend: $frontend_url"
        log_info "  Backend:  $backend_url/docs"
        echo ""
        log_info "Next steps:"
        log_info "  1. Test the application"
        log_info "  2. Set up monitoring (if not done): scripts/gcp/monitoring/setup.sh"
        log_info "  3. Review Cloud Run services: gcloud run services list"
        echo ""
    fi
}

# Run main function
main "$@"
