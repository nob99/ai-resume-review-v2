#!/bin/bash

#############################################################################
# setup-cloud-sql.sh
#
# Purpose: Create and configure Cloud SQL PostgreSQL instance for AI Resume Review v2
# Usage: ./setup-cloud-sql.sh [--dry-run]
#
# What it creates:
#   - Cloud SQL PostgreSQL 15 instance (db-f1-micro)
#   - Private IP configuration (connected to VPC)
#   - Database: ai_resume_review_prod
#   - Daily automated backups (7-day retention)
#
# Prerequisites:
#   - VPC network created (ai-resume-review-v2-vpc)
#   - Service Networking API enabled
#   - setup-gcp-project.sh completed
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
ZONE="us-central1-c"

# Database configuration
INSTANCE_NAME="ai-resume-review-v2-db-prod"
DATABASE_VERSION="POSTGRES_15"
TIER="db-f1-micro"
STORAGE_SIZE="10"  # GB
DATABASE_NAME="ai_resume_review_prod"
VPC_NETWORK="ai-resume-review-v2-vpc"

# Backup configuration
BACKUP_START_TIME="02:00"  # 2:00 AM
BACKUP_RETENTION_DAYS="7"

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

generate_password() {
    # Generate a secure random password (24 characters)
    openssl rand -base64 24 | tr -d "=+/" | cut -c1-24
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

    # Check project
    local current_project=$(gcloud config get-value project 2>/dev/null)
    if [ "$current_project" != "$PROJECT_ID" ]; then
        log_warning "Current project is $current_project, setting to $PROJECT_ID"
        gcloud config set project "$PROJECT_ID"
    fi
    log_info "Project set to: $PROJECT_ID"

    # Check if VPC exists
    if [ "$DRY_RUN" = false ]; then
        if ! gcloud compute networks describe "$VPC_NETWORK" --project="$PROJECT_ID" &>/dev/null; then
            log_error "VPC network not found: $VPC_NETWORK"
            log_error "Please run setup-gcp-project.sh first"
            exit 1
        fi
        log_info "VPC network exists: $VPC_NETWORK"
    fi

    # Check Service Networking API
    if [ "$DRY_RUN" = false ]; then
        if ! gcloud services list --enabled --filter="name:servicenetworking.googleapis.com" --format="value(name)" | grep -q "servicenetworking"; then
            log_warning "Service Networking API not enabled, enabling now..."
            gcloud services enable servicenetworking.googleapis.com --project="$PROJECT_ID"
            log_info "Service Networking API enabled"
        else
            log_info "Service Networking API enabled"
        fi
    fi

    echo ""
}

#############################################################################
# VPC Peering Setup
#############################################################################

setup_vpc_peering() {
    echo "=========================================="
    echo "1. Setting up VPC Peering for Private IP"
    echo "=========================================="

    log_step "Allocating IP range for Cloud SQL private services"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would allocate IP range: 10.1.0.0/16 for google-managed-services${NC}"
        echo -e "${YELLOW}[DRY RUN] Would create VPC peering connection${NC}"
    else
        # Check if IP range already allocated
        local existing_range=$(gcloud compute addresses list \
            --global \
            --filter="purpose:VPC_PEERING AND network:$VPC_NETWORK" \
            --format="value(name)" \
            --project="$PROJECT_ID" 2>/dev/null | head -1)

        if [ -n "$existing_range" ]; then
            log_warning "IP range already allocated: $existing_range"
        else
            # Allocate IP range for private services
            gcloud compute addresses create google-managed-services-$VPC_NETWORK \
                --global \
                --purpose=VPC_PEERING \
                --prefix-length=16 \
                --network=$VPC_NETWORK \
                --project="$PROJECT_ID" \
                --quiet
            log_info "Allocated IP range for private services"
        fi

        # Create VPC peering connection
        log_step "Creating VPC peering connection"

        # Check if peering already exists
        if gcloud services vpc-peerings list \
            --network=$VPC_NETWORK \
            --project="$PROJECT_ID" 2>/dev/null | grep -q "servicenetworking"; then
            log_warning "VPC peering already exists"
        else
            gcloud services vpc-peerings connect \
                --service=servicenetworking.googleapis.com \
                --ranges=google-managed-services-$VPC_NETWORK \
                --network=$VPC_NETWORK \
                --project="$PROJECT_ID" \
                --quiet
            log_info "VPC peering connection created"
        fi
    fi

    echo ""
}

#############################################################################
# Cloud SQL Instance Creation
#############################################################################

create_cloud_sql_instance() {
    echo "=========================================="
    echo "2. Creating Cloud SQL Instance"
    echo "=========================================="

    log_step "Instance: $INSTANCE_NAME"
    log_step "Database: $DATABASE_VERSION, Tier: $TIER"
    log_step "Storage: ${STORAGE_SIZE}GB SSD with auto-increase"
    log_step "Backups: Daily at ${BACKUP_START_TIME}, ${BACKUP_RETENTION_DAYS}-day retention"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would create Cloud SQL instance with:${NC}"
        echo -e "${YELLOW}  - Name: $INSTANCE_NAME${NC}"
        echo -e "${YELLOW}  - Version: $DATABASE_VERSION${NC}"
        echo -e "${YELLOW}  - Tier: $TIER${NC}"
        echo -e "${YELLOW}  - Region: $REGION${NC}"
        echo -e "${YELLOW}  - Private IP only (no public IP)${NC}"
        echo -e "${YELLOW}  - Network: $VPC_NETWORK${NC}"
    else
        # Check if instance already exists
        if gcloud sql instances describe "$INSTANCE_NAME" --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Cloud SQL instance already exists: $INSTANCE_NAME"
        else
            log_step "Creating instance (this takes 5-10 minutes)..."

            gcloud sql instances create "$INSTANCE_NAME" \
                --database-version="$DATABASE_VERSION" \
                --tier="$TIER" \
                --region="$REGION" \
                --network="projects/$PROJECT_ID/global/networks/$VPC_NETWORK" \
                --no-assign-ip \
                --storage-type=SSD \
                --storage-size="${STORAGE_SIZE}GB" \
                --storage-auto-increase \
                --backup \
                --backup-start-time="$BACKUP_START_TIME" \
                --retained-backups-count="$BACKUP_RETENTION_DAYS" \
                --maintenance-window-day=SUN \
                --maintenance-window-hour=2 \
                --maintenance-release-channel=production \
                --deletion-protection \
                --project="$PROJECT_ID" \
                --quiet

            log_info "Cloud SQL instance created: $INSTANCE_NAME"
        fi
    fi

    echo ""
}

#############################################################################
# Database Creation
#############################################################################

create_database() {
    echo "=========================================="
    echo "3. Creating Database"
    echo "=========================================="

    log_step "Database name: $DATABASE_NAME"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would create database: $DATABASE_NAME${NC}"
    else
        # Check if database already exists
        if gcloud sql databases describe "$DATABASE_NAME" \
            --instance="$INSTANCE_NAME" \
            --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Database already exists: $DATABASE_NAME"
        else
            gcloud sql databases create "$DATABASE_NAME" \
                --instance="$INSTANCE_NAME" \
                --project="$PROJECT_ID" \
                --quiet
            log_info "Database created: $DATABASE_NAME"
        fi
    fi

    echo ""
}

#############################################################################
# Set Root Password
#############################################################################

set_root_password() {
    echo "=========================================="
    echo "4. Setting Database Password"
    echo "=========================================="

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would generate and set root password${NC}"
        echo -e "${YELLOW}[DRY RUN] Password would be saved to: /tmp/db-password-prod.txt${NC}"
    else
        # Generate secure password
        DB_PASSWORD=$(generate_password)

        log_step "Setting postgres user password..."
        gcloud sql users set-password postgres \
            --instance="$INSTANCE_NAME" \
            --password="$DB_PASSWORD" \
            --project="$PROJECT_ID" \
            --quiet

        # Save password to temporary file (user will add to Secret Manager)
        echo "$DB_PASSWORD" > /tmp/db-password-prod.txt
        chmod 600 /tmp/db-password-prod.txt

        log_info "Password set and saved to: /tmp/db-password-prod.txt"
        log_warning "Remember to add this password to Secret Manager!"
    fi

    echo ""
}

#############################################################################
# Validation
#############################################################################

validate_setup() {
    echo "=========================================="
    echo "5. Validating Setup"
    echo "=========================================="

    if [ "$DRY_RUN" = true ]; then
        log_info "Dry run complete - skipping validation"
        return
    fi

    local validation_failed=false

    # Validate instance
    log_step "Validating Cloud SQL instance..."
    if gcloud sql instances describe "$INSTANCE_NAME" --project="$PROJECT_ID" &>/dev/null; then
        local instance_state=$(gcloud sql instances describe "$INSTANCE_NAME" \
            --project="$PROJECT_ID" \
            --format="value(state)")

        if [ "$instance_state" = "RUNNABLE" ]; then
            log_info "Cloud SQL instance is RUNNABLE"
        else
            log_warning "Cloud SQL instance state: $instance_state"
        fi
    else
        log_error "Cloud SQL instance not found"
        validation_failed=true
    fi

    # Validate database
    log_step "Validating database..."
    if gcloud sql databases describe "$DATABASE_NAME" \
        --instance="$INSTANCE_NAME" \
        --project="$PROJECT_ID" &>/dev/null; then
        log_info "Database exists: $DATABASE_NAME"
    else
        log_error "Database not found: $DATABASE_NAME"
        validation_failed=true
    fi

    # Get connection info
    log_step "Getting connection information..."
    local connection_name=$(gcloud sql instances describe "$INSTANCE_NAME" \
        --project="$PROJECT_ID" \
        --format="value(connectionName)")
    local private_ip=$(gcloud sql instances describe "$INSTANCE_NAME" \
        --project="$PROJECT_ID" \
        --format="value(ipAddresses[0].ipAddress)")

    if [ -n "$connection_name" ] && [ -n "$private_ip" ]; then
        log_info "Connection name: $connection_name"
        log_info "Private IP: $private_ip"
    else
        log_error "Failed to get connection information"
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
    echo "✅ Cloud SQL Setup Complete!"
    echo "=========================================="
    echo ""
    echo "📦 Created Resources:"
    echo ""

    # Get connection details
    local connection_name=$(gcloud sql instances describe "$INSTANCE_NAME" \
        --project="$PROJECT_ID" \
        --format="value(connectionName)")
    local private_ip=$(gcloud sql instances describe "$INSTANCE_NAME" \
        --project="$PROJECT_ID" \
        --format="value(ipAddresses[0].ipAddress)")

    echo "Cloud SQL Instance:"
    echo "  • Name: $INSTANCE_NAME"
    echo "  • Version: $DATABASE_VERSION"
    echo "  • Tier: $TIER ($STORAGE_SIZE GB SSD)"
    echo "  • Region: $REGION"
    echo "  • Connection Name: $connection_name"
    echo "  • Private IP: $private_ip"
    echo ""
    echo "Database:"
    echo "  • Name: $DATABASE_NAME"
    echo "  • User: postgres"
    echo "  • Password: Saved to /tmp/db-password-prod.txt"
    echo ""
    echo "Backup Configuration:"
    echo "  • Schedule: Daily at $BACKUP_START_TIME"
    echo "  • Retention: $BACKUP_RETENTION_DAYS days"
    echo "  • Maintenance: Sunday 2:00 AM"
    echo ""
    echo "🔐 Security:"
    echo "  • Private IP only (no public access)"
    echo "  • Connected to VPC: $VPC_NETWORK"
    echo "  • Deletion protection: ENABLED"
    echo ""
    echo "🔗 Connection from Cloud Run:"
    echo "  Unix Socket: /cloudsql/$connection_name"
    echo ""
    echo "  Example backend config:"
    echo "  DB_HOST=/cloudsql/$connection_name"
    echo "  DB_PORT=5432"
    echo "  DB_NAME=$DATABASE_NAME"
    echo "  DB_USER=postgres"
    echo "  DB_PASSWORD=<from Secret Manager>"
    echo ""
    echo "📋 Next Steps:"
    echo "  1. Run: ./scripts/gcp/setup-secrets.sh"
    echo "     (This will add DB password to Secret Manager)"
    echo "  2. Update backend environment variables"
    echo "  3. Run database migrations: alembic upgrade head"
    echo "  4. Deploy backend: ./scripts/gcp/deploy-to-production.sh"
    echo ""
    echo "⚠️  IMPORTANT:"
    echo "  • Database password saved to: /tmp/db-password-prod.txt"
    echo "  • Add this password to Secret Manager (setup-secrets.sh will do this)"
    echo "  • Delete /tmp/db-password-prod.txt after adding to Secret Manager"
    echo ""
    echo "=========================================="
}

#############################################################################
# Main Execution
#############################################################################

main() {
    echo ""
    echo "=========================================="
    echo "🗄️  Cloud SQL Setup - AI Resume Review v2"
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
    setup_vpc_peering
    create_cloud_sql_instance
    create_database
    set_root_password
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
