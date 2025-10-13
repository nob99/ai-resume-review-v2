#!/bin/bash
# ============================================================================
# GCP Infrastructure Inventory Script
# ============================================================================
# This script audits current GCP infrastructure and compares it with
# config/environments.yml to identify what needs to be imported into Terraform.
#
# Usage:
#   ./scripts/terraform/inventory.sh staging
#   ./scripts/terraform/inventory.sh production

set -euo pipefail

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/config/environments.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is required but not installed"
        exit 1
    fi
}

# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------

check_command "gcloud"
check_command "yq"

if [ $# -ne 1 ]; then
    echo "Usage: $0 <staging|production>"
    exit 1
fi

ENV_NAME="$1"

if [ "$ENV_NAME" != "staging" ] && [ "$ENV_NAME" != "production" ]; then
    log_error "Environment must be 'staging' or 'production'"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Config file not found: $CONFIG_FILE"
    exit 1
fi

# ----------------------------------------------------------------------------
# Load Configuration
# ----------------------------------------------------------------------------

log_section "Loading Configuration from $CONFIG_FILE"

PROJECT_ID=$(yq eval ".global.project_id" "$CONFIG_FILE")
REGION=$(yq eval ".global.region" "$CONFIG_FILE")

log_success "Project: $PROJECT_ID"
log_success "Region: $REGION"
log_success "Environment: $ENV_NAME"

# Verify we're authenticated
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    log_warning "Current gcloud project ($CURRENT_PROJECT) != configured project ($PROJECT_ID)"
    log_info "Setting project to $PROJECT_ID..."
    gcloud config set project "$PROJECT_ID"
fi

# ----------------------------------------------------------------------------
# Inventory: VPC Network
# ----------------------------------------------------------------------------

log_section "VPC Networks"

VPC_NAME=$(yq eval ".$ENV_NAME.network.vpc_name" "$CONFIG_FILE")
log_info "Expected VPC: $VPC_NAME"

if gcloud compute networks describe "$VPC_NAME" --format="value(name)" 2>/dev/null; then
    log_success "VPC exists: $VPC_NAME"

    # Get VPC details
    AUTO_CREATE=$(gcloud compute networks describe "$VPC_NAME" --format="value(autoCreateSubnetworks)" 2>/dev/null)
    log_info "  Auto-create subnetworks: $AUTO_CREATE"

    echo ""
    echo "Terraform import command:"
    echo "terraform import 'module.${ENV_NAME}_environment.google_compute_network.vpc' 'projects/$PROJECT_ID/global/networks/$VPC_NAME'"
else
    log_error "VPC not found: $VPC_NAME"
fi

# ----------------------------------------------------------------------------
# Inventory: Subnets
# ----------------------------------------------------------------------------

log_section "Subnets"

SUBNET_NAME=$(yq eval ".$ENV_NAME.network.subnet_name" "$CONFIG_FILE")
log_info "Expected Subnet: $SUBNET_NAME"

if gcloud compute networks subnets describe "$SUBNET_NAME" --region="$REGION" --format="value(name)" 2>/dev/null; then
    log_success "Subnet exists: $SUBNET_NAME"

    # Get subnet details
    IP_RANGE=$(gcloud compute networks subnets describe "$SUBNET_NAME" --region="$REGION" --format="value(ipCidrRange)" 2>/dev/null)
    log_info "  IP CIDR Range: $IP_RANGE"

    EXPECTED_CIDR=$(yq eval ".$ENV_NAME.network.subnet_cidr" "$CONFIG_FILE")
    if [ "$IP_RANGE" == "$EXPECTED_CIDR" ]; then
        log_success "  CIDR matches config"
    else
        log_warning "  CIDR mismatch! Config: $EXPECTED_CIDR, Actual: $IP_RANGE"
    fi

    echo ""
    echo "Terraform import command:"
    echo "terraform import 'module.${ENV_NAME}_environment.google_compute_subnetwork.subnet' 'projects/$PROJECT_ID/regions/$REGION/subnetworks/$SUBNET_NAME'"
else
    log_error "Subnet not found: $SUBNET_NAME"
fi

# ----------------------------------------------------------------------------
# Inventory: VPC Connector
# ----------------------------------------------------------------------------

log_section "VPC Connectors"

VPC_CONNECTOR=$(yq eval ".$ENV_NAME.network.vpc_connector" "$CONFIG_FILE")
log_info "Expected VPC Connector: $VPC_CONNECTOR"

if gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" --region="$REGION" --format="value(name)" 2>/dev/null; then
    log_success "VPC Connector exists: $VPC_CONNECTOR"

    # Get connector details
    STATE=$(gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" --region="$REGION" --format="value(state)" 2>/dev/null)
    IP_RANGE=$(gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" --region="$REGION" --format="value(ipCidrRange)" 2>/dev/null)
    MIN_THROUGHPUT=$(gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" --region="$REGION" --format="value(minThroughput)" 2>/dev/null)
    MAX_THROUGHPUT=$(gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" --region="$REGION" --format="value(maxThroughput)" 2>/dev/null)

    log_info "  State: $STATE"
    log_info "  IP CIDR Range: $IP_RANGE"
    log_info "  Min Throughput: $MIN_THROUGHPUT"
    log_info "  Max Throughput: $MAX_THROUGHPUT"

    echo ""
    echo "Terraform import command:"
    echo "terraform import 'module.${ENV_NAME}_environment.google_vpc_access_connector.connector' 'projects/$PROJECT_ID/locations/$REGION/connectors/$VPC_CONNECTOR'"
else
    log_error "VPC Connector not found: $VPC_CONNECTOR"
fi

# ----------------------------------------------------------------------------
# Inventory: Cloud SQL
# ----------------------------------------------------------------------------

log_section "Cloud SQL Instances"

SQL_INSTANCE=$(yq eval ".$ENV_NAME.database.instance_name" "$CONFIG_FILE")
log_info "Expected Cloud SQL Instance: $SQL_INSTANCE"

if gcloud sql instances describe "$SQL_INSTANCE" --format="value(name)" 2>/dev/null; then
    log_success "Cloud SQL instance exists: $SQL_INSTANCE"

    # Get instance details
    VERSION=$(gcloud sql instances describe "$SQL_INSTANCE" --format="value(databaseVersion)" 2>/dev/null)
    TIER=$(gcloud sql instances describe "$SQL_INSTANCE" --format="value(settings.tier)" 2>/dev/null)
    DISK_SIZE=$(gcloud sql instances describe "$SQL_INSTANCE" --format="value(settings.dataDiskSizeGb)" 2>/dev/null)
    DISK_TYPE=$(gcloud sql instances describe "$SQL_INSTANCE" --format="value(settings.dataDiskType)" 2>/dev/null)
    STATE=$(gcloud sql instances describe "$SQL_INSTANCE" --format="value(state)" 2>/dev/null)

    log_info "  Database Version: $VERSION"
    log_info "  Tier: $TIER"
    log_info "  Disk Size: ${DISK_SIZE}GB"
    log_info "  Disk Type: $DISK_TYPE"
    log_info "  State: $STATE"

    EXPECTED_TIER=$(yq eval ".$ENV_NAME.database.tier" "$CONFIG_FILE")
    if [ "$TIER" == "$EXPECTED_TIER" ]; then
        log_success "  Tier matches config"
    else
        log_warning "  Tier mismatch! Config: $EXPECTED_TIER, Actual: $TIER"
    fi

    echo ""
    echo "Terraform import command:"
    echo "terraform import 'module.${ENV_NAME}_environment.google_sql_database_instance.postgres' '$SQL_INSTANCE'"
else
    log_error "Cloud SQL instance not found: $SQL_INSTANCE"
fi

# ----------------------------------------------------------------------------
# Inventory: Database
# ----------------------------------------------------------------------------

log_section "Cloud SQL Databases"

DB_NAME=$(yq eval ".$ENV_NAME.database.database_name" "$CONFIG_FILE")
log_info "Expected Database: $DB_NAME"

if gcloud sql databases describe "$DB_NAME" --instance="$SQL_INSTANCE" --format="value(name)" 2>/dev/null; then
    log_success "Database exists: $DB_NAME"

    echo ""
    echo "Terraform import command:"
    echo "terraform import 'module.${ENV_NAME}_environment.google_sql_database.database' 'projects/$PROJECT_ID/instances/$SQL_INSTANCE/databases/$DB_NAME'"
else
    log_error "Database not found: $DB_NAME"
fi

# ----------------------------------------------------------------------------
# Inventory: Service Accounts
# ----------------------------------------------------------------------------

log_section "Service Accounts"

BACKEND_SA=$(yq eval ".$ENV_NAME.backend.service_account" "$CONFIG_FILE")
FRONTEND_SA=$(yq eval ".$ENV_NAME.frontend.service_account" "$CONFIG_FILE")

log_info "Expected Backend SA: $BACKEND_SA"
if gcloud iam service-accounts describe "$BACKEND_SA" --format="value(email)" 2>/dev/null; then
    log_success "Backend service account exists: $BACKEND_SA"

    echo ""
    echo "Terraform import command:"
    echo "terraform import 'module.${ENV_NAME}_environment.google_service_account.backend' 'projects/$PROJECT_ID/serviceAccounts/$BACKEND_SA'"
else
    log_error "Backend service account not found: $BACKEND_SA"
fi

echo ""
log_info "Expected Frontend SA: $FRONTEND_SA"
if gcloud iam service-accounts describe "$FRONTEND_SA" --format="value(email)" 2>/dev/null; then
    log_success "Frontend service account exists: $FRONTEND_SA"

    echo ""
    echo "Terraform import command:"
    echo "terraform import 'module.${ENV_NAME}_environment.google_service_account.frontend' 'projects/$PROJECT_ID/serviceAccounts/$FRONTEND_SA'"
else
    log_error "Frontend service account not found: $FRONTEND_SA"
fi

# ----------------------------------------------------------------------------
# Inventory: Artifact Registry
# ----------------------------------------------------------------------------

log_section "Artifact Registry"

ARTIFACT_REPO=$(yq eval ".global.artifact_registry.repository" "$CONFIG_FILE")
log_info "Expected Artifact Registry: $ARTIFACT_REPO"

if gcloud artifacts repositories describe "$ARTIFACT_REPO" --location="$REGION" --format="value(name)" 2>/dev/null; then
    log_success "Artifact Registry exists: $ARTIFACT_REPO"

    FORMAT=$(gcloud artifacts repositories describe "$ARTIFACT_REPO" --location="$REGION" --format="value(format)" 2>/dev/null)
    log_info "  Format: $FORMAT"

    echo ""
    echo "Terraform import command:"
    echo "terraform import 'module.${ENV_NAME}_environment.google_artifact_registry_repository.docker' 'projects/$PROJECT_ID/locations/$REGION/repositories/$ARTIFACT_REPO'"
else
    log_error "Artifact Registry not found: $ARTIFACT_REPO"
fi

# ----------------------------------------------------------------------------
# Inventory: Secrets
# ----------------------------------------------------------------------------

log_section "Secrets (Secret Manager)"

OPENAI_SECRET=$(yq eval ".$ENV_NAME.secrets.openai_api_key" "$CONFIG_FILE")
JWT_SECRET=$(yq eval ".$ENV_NAME.secrets.jwt_secret_key" "$CONFIG_FILE")
DB_SECRET=$(yq eval ".$ENV_NAME.secrets.db_password" "$CONFIG_FILE")

log_info "Expected OpenAI Secret: $OPENAI_SECRET"
if gcloud secrets describe "$OPENAI_SECRET" --format="value(name)" 2>/dev/null; then
    log_success "OpenAI secret exists: $OPENAI_SECRET"
else
    log_error "OpenAI secret not found: $OPENAI_SECRET"
fi

echo ""
log_info "Expected JWT Secret: $JWT_SECRET"
if gcloud secrets describe "$JWT_SECRET" --format="value(name)" 2>/dev/null; then
    log_success "JWT secret exists: $JWT_SECRET"
else
    log_error "JWT secret not found: $JWT_SECRET"
fi

echo ""
log_info "Expected DB Password Secret: $DB_SECRET"
if gcloud secrets describe "$DB_SECRET" --format="value(name)" 2>/dev/null; then
    log_success "DB password secret exists: $DB_SECRET"
else
    log_error "DB password secret not found: $DB_SECRET"
fi

echo ""
log_info "Note: Secrets are referenced as data sources in Terraform (not imported)"
log_info "Terraform uses: data.google_secret_manager_secret.<name>"

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------

log_section "Summary"

echo ""
echo "📋 Inventory complete for ${ENV_NAME} environment"
echo ""
echo "Next steps:"
echo "  1. Review the output above"
echo "  2. Copy the 'terraform import' commands to a script"
echo "  3. Run imports one by one in terraform/environments/${ENV_NAME}/"
echo "  4. After all imports, run: terraform plan"
echo "  5. Verify: 'No changes. Your infrastructure matches the configuration.'"
echo ""
echo "Full import script will be generated in:"
echo "  scripts/terraform/import-${ENV_NAME}.sh"
