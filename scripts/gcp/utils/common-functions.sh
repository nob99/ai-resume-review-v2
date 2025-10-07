#!/bin/bash
# common-functions.sh - Shared utility functions for GCP deployment scripts
#
# Usage: source this file at the beginning of your scripts:
#   source "$(dirname "$0")/../utils/common-functions.sh"

# Color codes for output
export COLOR_RED='\033[0;31m'
export COLOR_GREEN='\033[0;32m'
export COLOR_YELLOW='\033[1;33m'
export COLOR_BLUE='\033[0;34m'
export COLOR_CYAN='\033[0;36m'
export COLOR_RESET='\033[0m'

# GCP Configuration
export PROJECT_ID="ytgrs-464303"
export REGION="us-central1"
export ZONE="us-central1-c"

# Service Names
export BACKEND_SERVICE_NAME="ai-resume-review-v2-backend-prod"
export FRONTEND_SERVICE_NAME="ai-resume-review-v2-frontend-prod"

# Service Accounts
export BACKEND_SERVICE_ACCOUNT="arr-v2-backend-prod@${PROJECT_ID}.iam.gserviceaccount.com"
export FRONTEND_SERVICE_ACCOUNT="arr-v2-frontend-prod@${PROJECT_ID}.iam.gserviceaccount.com"

# Infrastructure
export VPC_NAME="ai-resume-review-v2-vpc"
export VPC_CONNECTOR="ai-resume-connector-v2"
export SQL_INSTANCE_NAME="ai-resume-review-v2-db-prod"
export SQL_INSTANCE_CONNECTION="$PROJECT_ID:$REGION:$SQL_INSTANCE_NAME"
export ARTIFACT_REGISTRY="us-central1-docker.pkg.dev/$PROJECT_ID/ai-resume-review-v2"

# Database
export DB_NAME="ai_resume_review_prod"
export DB_USER="postgres"

# Secret Names
export SECRET_OPENAI_KEY="openai-api-key-prod"
export SECRET_JWT_KEY="jwt-secret-key-prod"
export SECRET_DB_PASSWORD="db-password-prod"

# ============================================================================
# Logging Functions
# ============================================================================

# Print info message
log_info() {
    echo -e "${COLOR_BLUE}ℹ ${COLOR_RESET}$1"
}

# Print success message
log_success() {
    echo -e "${COLOR_GREEN}✓ ${COLOR_RESET}$1"
}

# Print warning message
log_warning() {
    echo -e "${COLOR_YELLOW}⚠ ${COLOR_RESET}$1"
}

# Print error message
log_error() {
    echo -e "${COLOR_RED}✗ ${COLOR_RESET}$1"
}

# Print section header
log_section() {
    echo ""
    echo -e "${COLOR_CYAN}========================================${COLOR_RESET}"
    echo -e "${COLOR_CYAN}$1${COLOR_RESET}"
    echo -e "${COLOR_CYAN}========================================${COLOR_RESET}"
}

# ============================================================================
# Validation Functions
# ============================================================================

# Check if gcloud is installed
check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed"
        log_info "Install from: https://cloud.google.com/sdk/docs/install"
        return 1
    fi
    log_success "gcloud CLI is installed"
    return 0
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        log_info "Install from: https://docs.docker.com/get-docker/"
        return 1
    fi
    log_success "Docker is installed"
    return 0
}

# Check if authenticated with GCP
check_gcp_auth() {
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        log_error "Not authenticated with GCP"
        log_info "Run: gcloud auth login"
        return 1
    fi
    local account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
    log_success "Authenticated as: $account"
    return 0
}

# Check if correct GCP project is set
check_gcp_project() {
    local current_project=$(gcloud config get-value project 2>/dev/null)
    if [ "$current_project" != "$PROJECT_ID" ]; then
        log_warning "Current project: $current_project"
        log_info "Setting project to: $PROJECT_ID"
        gcloud config set project "$PROJECT_ID"
    else
        log_success "Using project: $PROJECT_ID"
    fi
    return 0
}

# Check if a GCP service is enabled
check_service_enabled() {
    local service=$1
    if gcloud services list --enabled --filter="name:$service" --format="value(name)" 2>/dev/null | grep -q "$service"; then
        return 0
    else
        return 1
    fi
}

# Check if secret exists
check_secret_exists() {
    local secret_name=$1
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check if Cloud SQL instance exists
check_sql_instance_exists() {
    if gcloud sql instances describe "$SQL_INSTANCE_NAME" --project="$PROJECT_ID" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check if VPC connector exists
check_vpc_connector_exists() {
    if gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" \
        --region="$REGION" --project="$PROJECT_ID" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# GCP Helper Functions
# ============================================================================

# Get secret value from Secret Manager
get_secret() {
    local secret_name=$1
    gcloud secrets versions access latest --secret="$secret_name" --project="$PROJECT_ID" 2>/dev/null
}

# Get Cloud Run service URL
get_service_url() {
    local service_name=$1
    gcloud run services describe "$service_name" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.url)" 2>/dev/null
}

# Get Cloud SQL instance IP
get_sql_instance_ip() {
    gcloud sql instances describe "$SQL_INSTANCE_NAME" \
        --project="$PROJECT_ID" \
        --format="value(ipAddresses[0].ipAddress)" 2>/dev/null
}

# ============================================================================
# Confirmation Functions
# ============================================================================

# Ask for user confirmation
confirm() {
    local message=$1
    local default=${2:-"n"}  # Default to "n" if not specified

    if [ "$default" = "y" ]; then
        local prompt="[Y/n]"
    else
        local prompt="[y/N]"
    fi

    echo -e -n "${COLOR_YELLOW}? ${COLOR_RESET}$message $prompt: "
    read -r response

    # If empty response, use default
    if [ -z "$response" ]; then
        response=$default
    fi

    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# ============================================================================
# Error Handling
# ============================================================================

# Exit with error message
die() {
    log_error "$1"
    exit 1
}

# Check last command status and exit if failed
check_status() {
    if [ $? -ne 0 ]; then
        die "$1"
    fi
}

# ============================================================================
# Docker Functions
# ============================================================================

# Configure Docker for Artifact Registry
configure_docker_auth() {
    log_info "Configuring Docker authentication for Artifact Registry..."
    gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
    check_status "Failed to configure Docker authentication"
    log_success "Docker authentication configured"
}

# Build Docker image with platform
build_docker_image() {
    local dockerfile_dir=$1
    local image_name=$2
    local build_args=${3:-""}

    log_info "Building Docker image: $image_name"
    log_info "From directory: $dockerfile_dir"

    if [ -n "$build_args" ]; then
        docker build --platform linux/amd64 $build_args -t "$image_name" "$dockerfile_dir"
    else
        docker build --platform linux/amd64 -t "$image_name" "$dockerfile_dir"
    fi

    check_status "Docker build failed"
    log_success "Docker image built: $image_name"
}

# Tag Docker image for Artifact Registry
tag_docker_image() {
    local source_tag=$1
    local target_tag=$2

    log_info "Tagging image: $source_tag → $target_tag"
    docker tag "$source_tag" "$target_tag"
    check_status "Failed to tag Docker image"
    log_success "Image tagged"
}

# Push Docker image to Artifact Registry
push_docker_image() {
    local image_tag=$1

    log_info "Pushing image to Artifact Registry: $image_tag"
    docker push "$image_tag"
    check_status "Failed to push Docker image"
    log_success "Image pushed successfully"
}

# ============================================================================
# Initialization
# ============================================================================

# Run basic checks when sourced (optional, can be called explicitly)
init_checks() {
    log_section "Environment Checks"
    check_gcloud || return 1
    check_gcp_auth || return 1
    check_gcp_project || return 1
    return 0
}
