#!/bin/bash

#############################################################################
# setup-gcp-project.sh
#
# Purpose: Set up GCP infrastructure for AI Resume Review v2 Platform
# Usage: ./setup-gcp-project.sh [--dry-run]
#
# What it creates:
#   - Service Accounts (backend, frontend, github-actions)
#   - IAM Roles assignments
#   - Artifact Registry repository
#   - VPC Network with private subnet
#   - Billing alerts
#
# Prerequisites:
#   - gcloud CLI authenticated
#   - Project: ytgrs-464303
#   - Billing enabled
#   - Required APIs enabled (Cloud Run, Cloud SQL, etc.)
#
# Author: Cloud Engineering Team
# Date: 2025-10-06
#############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project configuration
PROJECT_ID="ytgrs-464303"
PROJECT_NUMBER="864523342928"
REGION="us-central1"
VPC_SUBNET_CIDR="10.0.0.0/24"

# Resource naming (v2 convention)
# Note: Service account names must be 6-30 chars (GCP limitation)
BACKEND_SA="arr-v2-backend-prod"
FRONTEND_SA="arr-v2-frontend-prod"
GITHUB_SA="arr-v2-github-actions"
ARTIFACT_REPO="ai-resume-review-v2"
VPC_NETWORK="ai-resume-review-v2-vpc"
VPC_SUBNET="ai-resume-review-v2-subnet"

# Budget configuration
BUDGET_AMOUNT=180  # USD per month
ALERT_THRESHOLD_1=50  # 50%
ALERT_THRESHOLD_2=80  # 80%
ALERT_THRESHOLD_3=100 # 100%

# Parse arguments
DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}🔍 DRY RUN MODE - No resources will be created${NC}"
    echo ""
fi

#############################################################################
# Helper Functions
#############################################################################

log_info() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

log_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

#############################################################################
# Prerequisite Checks
#############################################################################

check_prerequisites() {
    echo "=========================================="
    echo "📋 Checking Prerequisites"
    echo "=========================================="

    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Please install it first."
        exit 1
    fi
    log_info "gcloud CLI found"

    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        log_error "Not authenticated with gcloud. Run 'gcloud auth login'"
        exit 1
    fi
    local active_account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    log_info "Authenticated as: $active_account"

    # Check project
    local current_project=$(gcloud config get-value project 2>/dev/null)
    if [ "$current_project" != "$PROJECT_ID" ]; then
        log_warning "Current project is $current_project, setting to $PROJECT_ID"
        gcloud config set project "$PROJECT_ID"
    fi
    log_info "Project set to: $PROJECT_ID"

    # Check billing enabled
    if [ "$DRY_RUN" = false ]; then
        if ! gcloud artifacts repositories list --project="$PROJECT_ID" &>/dev/null; then
            log_error "Billing not enabled on project. Please enable billing first."
            exit 1
        fi
        log_info "Billing is enabled"
    fi

    echo ""
}

#############################################################################
# Service Account Setup
#############################################################################

create_service_accounts() {
    echo "=========================================="
    echo "1. Creating Service Accounts"
    echo "=========================================="

    local service_accounts=(
        "$BACKEND_SA:Backend service account for Cloud Run"
        "$FRONTEND_SA:Frontend service account for Cloud Run"
        "$GITHUB_SA:GitHub Actions deployment service account"
    )

    for sa_config in "${service_accounts[@]}"; do
        local sa_name=$(echo "$sa_config" | cut -d: -f1)
        local sa_description=$(echo "$sa_config" | cut -d: -f2)
        local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"

        log_step "Creating service account: $sa_name"

        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}[DRY RUN] Would create: $sa_email${NC}"
        else
            # Check if already exists
            if gcloud iam service-accounts describe "$sa_email" --project="$PROJECT_ID" &>/dev/null; then
                log_warning "Service account already exists: $sa_email"
            else
                gcloud iam service-accounts create "$sa_name" \
                    --display-name="$sa_description" \
                    --project="$PROJECT_ID" \
                    --quiet
                log_info "Created service account: $sa_email"
            fi
        fi
    done

    echo ""
}

#############################################################################
# IAM Role Assignments
#############################################################################

assign_iam_roles() {
    echo "=========================================="
    echo "2. Assigning IAM Roles"
    echo "=========================================="

    # Backend service account roles
    log_step "Assigning roles to backend service account"
    local backend_roles=(
        "roles/cloudsql.client"
        "roles/secretmanager.secretAccessor"
        "roles/logging.logWriter"
    )

    for role in "${backend_roles[@]}"; do
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}[DRY RUN] Would assign $role to $BACKEND_SA${NC}"
        else
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
                --role="$role" \
                --quiet &>/dev/null
            log_info "Assigned $role to $BACKEND_SA"
        fi
    done

    # Frontend service account roles
    log_step "Assigning roles to frontend service account"
    local frontend_roles=(
        "roles/logging.logWriter"
    )

    for role in "${frontend_roles[@]}"; do
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}[DRY RUN] Would assign $role to $FRONTEND_SA${NC}"
        else
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:${FRONTEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
                --role="$role" \
                --quiet &>/dev/null
            log_info "Assigned $role to $FRONTEND_SA"
        fi
    done

    # GitHub Actions service account roles
    log_step "Assigning roles to GitHub Actions service account"
    local github_roles=(
        "roles/run.admin"
        "roles/iam.serviceAccountUser"
        "roles/artifactregistry.writer"
        "roles/cloudbuild.builds.editor"
    )

    for role in "${github_roles[@]}"; do
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}[DRY RUN] Would assign $role to $GITHUB_SA${NC}"
        else
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:${GITHUB_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
                --role="$role" \
                --quiet &>/dev/null
            log_info "Assigned $role to $GITHUB_SA"
        fi
    done

    echo ""
}

#############################################################################
# Artifact Registry Setup
#############################################################################

create_artifact_registry() {
    echo "=========================================="
    echo "3. Creating Artifact Registry"
    echo "=========================================="

    log_step "Creating Docker repository: $ARTIFACT_REPO"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would create Artifact Registry: $ARTIFACT_REPO in $REGION${NC}"
    else
        # Check if already exists
        if gcloud artifacts repositories describe "$ARTIFACT_REPO" \
            --location="$REGION" \
            --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Artifact Registry repository already exists: $ARTIFACT_REPO"
        else
            gcloud artifacts repositories create "$ARTIFACT_REPO" \
                --repository-format=docker \
                --location="$REGION" \
                --description="Docker images for AI Resume Review v2 platform" \
                --project="$PROJECT_ID" \
                --quiet
            log_info "Created Artifact Registry repository: $ARTIFACT_REPO"
        fi
    fi

    echo ""
}

#############################################################################
# VPC Network Setup
#############################################################################

create_vpc_network() {
    echo "=========================================="
    echo "4. Creating VPC Network"
    echo "=========================================="

    # Create VPC network
    log_step "Creating VPC network: $VPC_NETWORK"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would create VPC: $VPC_NETWORK${NC}"
    else
        # Check if already exists
        if gcloud compute networks describe "$VPC_NETWORK" --project="$PROJECT_ID" &>/dev/null; then
            log_warning "VPC network already exists: $VPC_NETWORK"
        else
            gcloud compute networks create "$VPC_NETWORK" \
                --subnet-mode=custom \
                --project="$PROJECT_ID" \
                --quiet
            log_info "Created VPC network: $VPC_NETWORK"
        fi
    fi

    # Create subnet
    log_step "Creating VPC subnet: $VPC_SUBNET ($VPC_SUBNET_CIDR)"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would create subnet: $VPC_SUBNET with CIDR $VPC_SUBNET_CIDR${NC}"
    else
        # Check if already exists
        if gcloud compute networks subnets describe "$VPC_SUBNET" \
            --region="$REGION" \
            --project="$PROJECT_ID" &>/dev/null; then
            log_warning "VPC subnet already exists: $VPC_SUBNET"
        else
            gcloud compute networks subnets create "$VPC_SUBNET" \
                --network="$VPC_NETWORK" \
                --region="$REGION" \
                --range="$VPC_SUBNET_CIDR" \
                --project="$PROJECT_ID" \
                --quiet
            log_info "Created VPC subnet: $VPC_SUBNET"
        fi
    fi

    echo ""
}

#############################################################################
# Billing Alerts Setup
#############################################################################

setup_billing_alerts() {
    echo "=========================================="
    echo "5. Setting up Billing Alerts"
    echo "=========================================="

    log_step "Budget: \$${BUDGET_AMOUNT}/month"
    log_step "Alert thresholds: ${ALERT_THRESHOLD_1}%, ${ALERT_THRESHOLD_2}%, ${ALERT_THRESHOLD_3}%"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would create billing budget with alerts${NC}"
        echo -e "${YELLOW}  - 50% threshold (\$90) → Email${NC}"
        echo -e "${YELLOW}  - 80% threshold (\$144) → Email${NC}"
        echo -e "${YELLOW}  - 100% threshold (\$180) → Email${NC}"
    else
        log_warning "Billing alerts require manual setup via GCP Console:"
        echo "  1. Go to: https://console.cloud.google.com/billing/budgets"
        echo "  2. Create budget: \$${BUDGET_AMOUNT}/month"
        echo "  3. Set alert thresholds: ${ALERT_THRESHOLD_1}%, ${ALERT_THRESHOLD_2}%, ${ALERT_THRESHOLD_3}%"
        echo ""
        log_info "Note: Billing alerts setup skipped (manual step required)"
    fi

    echo ""
}

#############################################################################
# Validation
#############################################################################

validate_setup() {
    echo "=========================================="
    echo "6. Validating Setup"
    echo "=========================================="

    if [ "$DRY_RUN" = true ]; then
        log_info "Dry run complete - skipping validation"
        return
    fi

    local validation_failed=false

    # Validate service accounts
    log_step "Validating service accounts..."
    for sa in "$BACKEND_SA" "$FRONTEND_SA" "$GITHUB_SA"; do
        local sa_email="${sa}@${PROJECT_ID}.iam.gserviceaccount.com"
        if gcloud iam service-accounts describe "$sa_email" --project="$PROJECT_ID" &>/dev/null; then
            log_info "Service account exists: $sa"
        else
            log_error "Service account missing: $sa"
            validation_failed=true
        fi
    done

    # Validate Artifact Registry
    log_step "Validating Artifact Registry..."
    if gcloud artifacts repositories describe "$ARTIFACT_REPO" \
        --location="$REGION" \
        --project="$PROJECT_ID" &>/dev/null; then
        log_info "Artifact Registry exists: $ARTIFACT_REPO"
    else
        log_error "Artifact Registry missing: $ARTIFACT_REPO"
        validation_failed=true
    fi

    # Validate VPC
    log_step "Validating VPC network..."
    if gcloud compute networks describe "$VPC_NETWORK" --project="$PROJECT_ID" &>/dev/null; then
        log_info "VPC network exists: $VPC_NETWORK"
    else
        log_error "VPC network missing: $VPC_NETWORK"
        validation_failed=true
    fi

    # Validate subnet
    if gcloud compute networks subnets describe "$VPC_SUBNET" \
        --region="$REGION" \
        --project="$PROJECT_ID" &>/dev/null; then
        log_info "VPC subnet exists: $VPC_SUBNET"
    else
        log_error "VPC subnet missing: $VPC_SUBNET"
        validation_failed=true
    fi

    if [ "$validation_failed" = true ]; then
        echo ""
        log_error "Validation failed! Some resources are missing."
        exit 1
    fi

    echo ""
}

#############################################################################
# Summary Output
#############################################################################

print_summary() {
    echo "=========================================="
    echo "✅ Setup Complete!"
    echo "=========================================="
    echo ""
    echo "📦 Created Resources:"
    echo ""
    echo "Service Accounts:"
    echo "  • ${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
    echo "  • ${FRONTEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
    echo "  • ${GITHUB_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
    echo ""
    echo "Artifact Registry:"
    echo "  • ${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}"
    echo ""
    echo "VPC Network:"
    echo "  • Network: ${VPC_NETWORK}"
    echo "  • Subnet: ${VPC_SUBNET} (${VPC_SUBNET_CIDR})"
    echo ""
    echo "🔐 IAM Roles Assigned:"
    echo "  Backend SA:"
    echo "    - roles/cloudsql.client"
    echo "    - roles/secretmanager.secretAccessor"
    echo "    - roles/logging.logWriter"
    echo ""
    echo "  Frontend SA:"
    echo "    - roles/logging.logWriter"
    echo ""
    echo "  GitHub Actions SA:"
    echo "    - roles/run.admin"
    echo "    - roles/iam.serviceAccountUser"
    echo "    - roles/artifactregistry.writer"
    echo "    - roles/cloudbuild.builds.editor"
    echo ""
    echo "📋 Next Steps:"
    echo "  1. Run: ./scripts/gcp/setup-secrets.sh"
    echo "  2. Run: ./scripts/gcp/setup-cloud-sql.sh"
    echo "  3. Run: ./scripts/gcp/deploy-to-production.sh"
    echo ""
    echo "📊 Manual Tasks (via GCP Console):"
    echo "  • Set up billing alerts: https://console.cloud.google.com/billing/budgets"
    echo "    Budget: \$${BUDGET_AMOUNT}/month, Alerts at: ${ALERT_THRESHOLD_1}%, ${ALERT_THRESHOLD_2}%, ${ALERT_THRESHOLD_3}%"
    echo ""
    echo "=========================================="
}

#############################################################################
# Main Execution
#############################################################################

main() {
    echo ""
    echo "=========================================="
    echo "🚀 GCP Setup Script - AI Resume Review v2"
    echo "=========================================="
    echo "Project: $PROJECT_ID"
    echo "Region: $REGION"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Running in DRY RUN mode - no resources will be created${NC}"
        echo ""
    fi

    # Execute setup steps
    check_prerequisites
    create_service_accounts
    assign_iam_roles
    create_artifact_registry
    create_vpc_network
    setup_billing_alerts
    validate_setup

    if [ "$DRY_RUN" = false ]; then
        print_summary
    else
        echo ""
        log_info "Dry run complete! Run without --dry-run to create resources."
        echo ""
    fi
}

# Run main function
main
