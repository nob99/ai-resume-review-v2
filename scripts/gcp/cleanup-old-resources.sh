#!/bin/bash

#############################################################################
# cleanup-old-resources.sh
#
# Purpose: Delete old "ai-resume" and "resume" named resources from GCP
# Usage: ./cleanup-old-resources.sh [--dry-run]
#
# What it deletes:
#   - Cloud Run services (ai-resume-backend, ai-resume-frontend)
#   - Cloud SQL databases (ai-resume-db, resume-review-db)
#   - Service Accounts (ai-resume-*, resume-*)
#   - Artifact Registry (ai-resume-review)
#   - VPC Network (ai-resume-vpc)
#
# Author: Cloud Engineering Team
# Date: 2025-10-06
#############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Project configuration
PROJECT_ID="ytgrs-464303"
REGION="us-central1"

# Parse arguments
DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}🔍 DRY RUN MODE - No resources will be deleted${NC}"
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

confirm_deletion() {
    local resource_type=$1
    local resource_name=$2

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would delete $resource_type: $resource_name${NC}"
        return 0
    fi

    echo -e "${RED}About to delete $resource_type: $resource_name${NC}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        log_warning "Skipped deletion of $resource_name"
        return 1
    fi
}

#############################################################################
# Main Cleanup Functions
#############################################################################

cleanup_cloud_run_services() {
    echo ""
    echo "=========================================="
    echo "1. Cleaning up Cloud Run Services"
    echo "=========================================="

    local services=("ai-resume-backend" "ai-resume-frontend")

    for service in "${services[@]}"; do
        # Check if service exists
        if gcloud run services describe "$service" --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
            if confirm_deletion "Cloud Run Service" "$service"; then
                if [ "$DRY_RUN" = false ]; then
                    gcloud run services delete "$service" \
                        --region="$REGION" \
                        --project="$PROJECT_ID" \
                        --quiet
                    log_info "Deleted Cloud Run service: $service"
                fi
            fi
        else
            log_warning "Cloud Run service not found: $service (already deleted?)"
        fi
    done
}

cleanup_cloud_sql_instances() {
    echo ""
    echo "=========================================="
    echo "2. Cleaning up Cloud SQL Instances"
    echo "=========================================="

    local instances=("ai-resume-db" "resume-review-db")

    for instance in "${instances[@]}"; do
        # Check if instance exists
        if gcloud sql instances describe "$instance" --project="$PROJECT_ID" &>/dev/null; then
            if confirm_deletion "Cloud SQL Instance" "$instance"; then
                if [ "$DRY_RUN" = false ]; then
                    log_warning "Deleting Cloud SQL instance (this may take a few minutes)..."
                    gcloud sql instances delete "$instance" \
                        --project="$PROJECT_ID" \
                        --quiet
                    log_info "Deleted Cloud SQL instance: $instance"
                fi
            fi
        else
            log_warning "Cloud SQL instance not found: $instance (already deleted?)"
        fi
    done
}

cleanup_service_accounts() {
    echo ""
    echo "=========================================="
    echo "3. Cleaning up Service Accounts"
    echo "=========================================="

    local service_accounts=(
        "ai-resume-backend@ytgrs-464303.iam.gserviceaccount.com"
        "ai-resume-frontend@ytgrs-464303.iam.gserviceaccount.com"
        "resume-backend@ytgrs-464303.iam.gserviceaccount.com"
        "resume-frontend@ytgrs-464303.iam.gserviceaccount.com"
    )

    for sa in "${service_accounts[@]}"; do
        # Check if service account exists
        if gcloud iam service-accounts describe "$sa" --project="$PROJECT_ID" &>/dev/null; then
            if confirm_deletion "Service Account" "$sa"; then
                if [ "$DRY_RUN" = false ]; then
                    gcloud iam service-accounts delete "$sa" \
                        --project="$PROJECT_ID" \
                        --quiet
                    log_info "Deleted service account: $sa"
                fi
            fi
        else
            log_warning "Service account not found: $sa (already deleted?)"
        fi
    done
}

cleanup_artifact_registry() {
    echo ""
    echo "=========================================="
    echo "4. Cleaning up Artifact Registry"
    echo "=========================================="

    local repo_name="ai-resume-review"
    local repo_location="us-central1"

    # Check if repository exists
    if gcloud artifacts repositories describe "$repo_name" \
        --location="$repo_location" \
        --project="$PROJECT_ID" &>/dev/null; then

        if confirm_deletion "Artifact Registry Repository" "$repo_name (us-central1)"; then
            if [ "$DRY_RUN" = false ]; then
                gcloud artifacts repositories delete "$repo_name" \
                    --location="$repo_location" \
                    --project="$PROJECT_ID" \
                    --quiet
                log_info "Deleted Artifact Registry repository: $repo_name"
            fi
        fi
    else
        log_warning "Artifact Registry repository not found: $repo_name (already deleted?)"
    fi
}

cleanup_vpc_network() {
    echo ""
    echo "=========================================="
    echo "5. Cleaning up VPC Network"
    echo "=========================================="

    local vpc_name="ai-resume-vpc"
    local subnet_name="ai-resume-subnet"

    # Delete subnet first (dependency)
    if gcloud compute networks subnets describe "$subnet_name" \
        --region="$REGION" \
        --project="$PROJECT_ID" &>/dev/null; then

        if confirm_deletion "VPC Subnet" "$subnet_name"; then
            if [ "$DRY_RUN" = false ]; then
                gcloud compute networks subnets delete "$subnet_name" \
                    --region="$REGION" \
                    --project="$PROJECT_ID" \
                    --quiet
                log_info "Deleted VPC subnet: $subnet_name"
            fi
        fi
    else
        log_warning "VPC subnet not found: $subnet_name (already deleted?)"
    fi

    # Delete VPC network
    if gcloud compute networks describe "$vpc_name" --project="$PROJECT_ID" &>/dev/null; then
        if confirm_deletion "VPC Network" "$vpc_name"; then
            if [ "$DRY_RUN" = false ]; then
                gcloud compute networks delete "$vpc_name" \
                    --project="$PROJECT_ID" \
                    --quiet
                log_info "Deleted VPC network: $vpc_name"
            fi
        fi
    else
        log_warning "VPC network not found: $vpc_name (already deleted?)"
    fi
}

#############################################################################
# Main Execution
#############################################################################

main() {
    echo ""
    echo "=========================================="
    echo "🗑️  GCP Cleanup Script"
    echo "=========================================="
    echo "Project: $PROJECT_ID"
    echo "Region: $REGION"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Running in DRY RUN mode - no resources will be deleted${NC}"
    else
        echo -e "${RED}⚠️  WARNING: This will DELETE resources!${NC}"
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cleanup cancelled."
            exit 0
        fi
    fi

    # Execute cleanup functions in order
    cleanup_cloud_run_services
    cleanup_cloud_sql_instances
    cleanup_service_accounts
    cleanup_artifact_registry
    cleanup_vpc_network

    echo ""
    echo "=========================================="
    if [ "$DRY_RUN" = true ]; then
        echo -e "${GREEN}✓ Dry run complete - no resources were deleted${NC}"
    else
        echo -e "${GREEN}✓ Cleanup complete!${NC}"
    fi
    echo "=========================================="
    echo ""
    echo "Next step: Run setup-gcp-project.sh to create new v2 resources"
    echo ""
}

# Run main function
main
