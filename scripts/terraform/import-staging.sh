#!/bin/bash
# ============================================================================
# Terraform Import Script - Staging Environment
# ============================================================================
# This script imports existing GCP infrastructure into Terraform state.
#
# IMPORTANT: This script does NOT modify any GCP resources!
# It only adds existing resources to Terraform's state tracking.
#
# Usage:
#   cd terraform/environments/staging
#   ../../../scripts/terraform/import-staging.sh
#
# Prerequisites:
#   - terraform init must be run first
#   - gcloud authenticated with proper permissions

set -euo pipefail

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/terraform/environments/staging"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# GCP Configuration (from inventory)
PROJECT_ID="ytgrs-464303"
REGION="us-central1"

# ----------------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

import_resource() {
    local resource_name="$1"
    local resource_address="$2"
    local resource_id="$3"

    echo ""
    log_info "Importing: $resource_name"
    log_info "  Address: $resource_address"
    log_info "  ID: $resource_id"

    # Check if already imported
    if terraform state show "$resource_address" &>/dev/null; then
        log_warning "Already imported, skipping"
        return 0
    fi

    # Import
    if terraform import "$resource_address" "$resource_id"; then
        log_success "Import successful"
        return 0
    else
        log_error "Import failed"
        return 1
    fi
}

# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------

log_section "Pre-Import Validation"

# Check we're in the right directory
if [ ! -f "$TERRAFORM_DIR/main.tf" ]; then
    log_error "Not in terraform/environments/staging directory"
    log_error "Please run: cd $TERRAFORM_DIR"
    exit 1
fi

# Change to terraform directory
cd "$TERRAFORM_DIR"
log_success "Working directory: $(pwd)"

# Check terraform is installed
if ! command -v terraform &> /dev/null; then
    log_error "terraform is not installed"
    exit 1
fi
log_success "Terraform version: $(terraform version -json | grep -o '"terraform_version":"[^"]*' | cut -d'"' -f4)"

# Check gcloud authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &>/dev/null; then
    log_error "gcloud not authenticated"
    log_error "Please run: gcloud auth login"
    exit 1
fi
ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
log_success "Authenticated as: $ACCOUNT"

# Check correct project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    log_warning "Current project ($CURRENT_PROJECT) != target project ($PROJECT_ID)"
    log_info "Setting project to $PROJECT_ID..."
    gcloud config set project "$PROJECT_ID"
fi
log_success "Project: $PROJECT_ID"

# Check terraform state
if [ ! -d ".terraform" ]; then
    log_error "Terraform not initialized"
    log_error "Please run: terraform init"
    exit 1
fi
log_success "Terraform initialized"

# ----------------------------------------------------------------------------
# Import: Networking
# ----------------------------------------------------------------------------

log_section "Phase 1: Networking (VPC, Subnet, VPC Connector)"

# Import VPC Network
import_resource \
    "VPC Network" \
    "module.staging_environment.google_compute_network.vpc" \
    "projects/$PROJECT_ID/global/networks/ai-resume-review-v2-vpc"

# Import Subnet
import_resource \
    "Subnet" \
    "module.staging_environment.google_compute_subnetwork.subnet" \
    "projects/$PROJECT_ID/regions/$REGION/subnetworks/ai-resume-review-v2-subnet"

# Import VPC Peering IP Range
import_resource \
    "VPC Peering IP Range" \
    "module.staging_environment.google_compute_global_address.private_ip" \
    "projects/$PROJECT_ID/global/addresses/google-managed-services-ai-resume-review-v2-vpc"

# Import VPC Connector
import_resource \
    "VPC Connector" \
    "module.staging_environment.google_vpc_access_connector.connector" \
    "projects/$PROJECT_ID/locations/$REGION/connectors/ai-resume-connector-v2"

log_section "Phase 1 Complete - Networking Imported"
terraform state list | grep -E "(network|subnet|connector|address)" || true

# ----------------------------------------------------------------------------
# Import: Database
# ----------------------------------------------------------------------------

log_section "Phase 2: Database (Cloud SQL Instance + Database)"

# Import Cloud SQL Instance
import_resource \
    "Cloud SQL Instance" \
    "module.staging_environment.google_sql_database_instance.postgres" \
    "ai-resume-review-v2-db-staging"

# Import Database
import_resource \
    "Database" \
    "module.staging_environment.google_sql_database.database" \
    "projects/$PROJECT_ID/instances/ai-resume-review-v2-db-staging/databases/ai_resume_review_staging"

log_section "Phase 2 Complete - Database Imported"
terraform state list | grep -E "(sql_database)" || true

# ----------------------------------------------------------------------------
# Import: Service Accounts
# ----------------------------------------------------------------------------

log_section "Phase 3: Service Accounts"

# Import Backend Service Account
import_resource \
    "Backend Service Account" \
    "module.staging_environment.google_service_account.backend" \
    "projects/$PROJECT_ID/serviceAccounts/arr-v2-backend-staging@ytgrs-464303.iam.gserviceaccount.com"

# Import Frontend Service Account
import_resource \
    "Frontend Service Account" \
    "module.staging_environment.google_service_account.frontend" \
    "projects/$PROJECT_ID/serviceAccounts/arr-v2-frontend-staging@ytgrs-464303.iam.gserviceaccount.com"

log_section "Phase 3 Complete - Service Accounts Imported"
terraform state list | grep -E "(service_account)" || true

# ----------------------------------------------------------------------------
# Import: Artifact Registry
# ----------------------------------------------------------------------------

log_section "Phase 4: Artifact Registry"

# Import Artifact Registry
import_resource \
    "Artifact Registry Repository" \
    "module.staging_environment.google_artifact_registry_repository.docker" \
    "projects/$PROJECT_ID/locations/$REGION/repositories/ai-resume-review-v2"

log_section "Phase 4 Complete - Artifact Registry Imported"
terraform state list | grep -E "(artifact_registry)" || true

# ----------------------------------------------------------------------------
# Import: IAM Bindings
# ----------------------------------------------------------------------------

log_section "Phase 5: IAM Bindings (Project-Level)"

log_info "Importing project-level IAM bindings..."
log_warning "Note: IAM bindings might fail if they don't exist - this is OK"
log_warning "Terraform will create them on first apply if needed"

# Backend → Cloud SQL Client
import_resource \
    "Backend SQL Client Role" \
    "module.staging_environment.google_project_iam_member.backend_sql_client" \
    "$PROJECT_ID roles/cloudsql.client serviceAccount:arr-v2-backend-staging@ytgrs-464303.iam.gserviceaccount.com" \
    || log_warning "IAM binding might not exist - will be created on apply"

# Backend → Secret Manager Accessor
import_resource \
    "Backend Secret Accessor Role" \
    "module.staging_environment.google_project_iam_member.backend_secret_accessor" \
    "$PROJECT_ID roles/secretmanager.secretAccessor serviceAccount:arr-v2-backend-staging@ytgrs-464303.iam.gserviceaccount.com" \
    || log_warning "IAM binding might not exist - will be created on apply"

# Backend → Log Writer
import_resource \
    "Backend Log Writer Role" \
    "module.staging_environment.google_project_iam_member.backend_log_writer" \
    "$PROJECT_ID roles/logging.logWriter serviceAccount:arr-v2-backend-staging@ytgrs-464303.iam.gserviceaccount.com" \
    || log_warning "IAM binding might not exist - will be created on apply"

# Frontend → Log Writer
import_resource \
    "Frontend Log Writer Role" \
    "module.staging_environment.google_project_iam_member.frontend_log_writer" \
    "$PROJECT_ID roles/logging.logWriter serviceAccount:arr-v2-frontend-staging@ytgrs-464303.iam.gserviceaccount.com" \
    || log_warning "IAM binding might not exist - will be created on apply"

log_section "Phase 5 Complete - IAM Bindings Attempted"

# ----------------------------------------------------------------------------
# Import: Secret IAM Bindings
# ----------------------------------------------------------------------------

log_section "Phase 6: Secret Manager IAM Bindings"

log_info "Importing secret-level IAM bindings..."
log_warning "These might not exist yet - Terraform will create them"

# Note: Secret IAM bindings are harder to import due to complex IDs
# We'll let terraform plan show if these need to be created
log_info "Secret IAM bindings will be handled by terraform plan/apply"
log_info "If they don't exist, Terraform will create them (safe operation)"

# ----------------------------------------------------------------------------
# Verification
# ----------------------------------------------------------------------------

log_section "Import Complete - Running Verification"

echo ""
log_info "Listing all imported resources..."
terraform state list

echo ""
echo ""
log_section "Next Steps"

echo ""
echo "✅ Import process complete!"
echo ""
echo "📋 What to do next:"
echo ""
echo "1. Review imported resources:"
echo "   terraform state list"
echo ""
echo "2. Run terraform plan to check for differences:"
echo "   terraform plan"
echo ""
echo "3. Expected outcomes:"
echo "   ✅ BEST: 'No changes. Infrastructure matches configuration.'"
echo "   ⚠️  OK: A few IAM bindings need to be created (safe to apply)"
echo "   ❌ BAD: Many changes or deletions (DO NOT APPLY, investigate first)"
echo ""
echo "4. If only minor IAM binding additions:"
echo "   terraform apply   # Review carefully before confirming"
echo ""
echo "5. Document any issues found"
echo ""
echo "📁 Location: $(pwd)"
echo "📊 Project: $PROJECT_ID"
echo "🌍 Environment: staging"
echo ""
