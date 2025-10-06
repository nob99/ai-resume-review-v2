#!/bin/bash

#############################################################################
# setup-secrets.sh
#
# Purpose: Create and store secrets in Google Secret Manager
# Usage: ./setup-secrets.sh [--dry-run]
#
# What it creates:
#   - openai-api-key-prod (OpenAI GPT-4 API key)
#   - jwt-secret-key-prod (JWT token signing secret)
#   - db-password-prod (PostgreSQL database password)
#
# Prerequisites:
#   - Secret Manager API enabled
#   - Service accounts created (arr-v2-backend-prod)
#   - Database password from setup-cloud-sql.sh
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
REGION="us-central1"

# Service account that needs access
BACKEND_SA="arr-v2-backend-prod@ytgrs-464303.iam.gserviceaccount.com"

# Secret names
SECRETS=(
    "openai-api-key-prod"
    "jwt-secret-key-prod"
    "db-password-prod"
)

# Parse arguments
DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}🔍 DRY RUN MODE - No secrets will be created${NC}"
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

generate_jwt_secret() {
    # Generate a secure random JWT secret (64 characters, 256-bit)
    openssl rand -hex 32
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

    # Check if backend service account exists
    if [ "$DRY_RUN" = false ]; then
        if ! gcloud iam service-accounts describe "$BACKEND_SA" --project="$PROJECT_ID" &>/dev/null; then
            log_error "Backend service account not found: $BACKEND_SA"
            log_error "Please run setup-gcp-project.sh first"
            exit 1
        fi
        log_info "Backend service account exists"
    fi

    # Check for database password file
    if [ "$DRY_RUN" = false ]; then
        if [ -f "/tmp/db-password-prod.txt" ]; then
            log_info "Database password file found: /tmp/db-password-prod.txt"
        else
            log_warning "Database password file not found: /tmp/db-password-prod.txt"
            log_warning "You'll need to enter the database password manually"
        fi
    fi

    echo ""
}

#############################################################################
# Create Secrets
#############################################################################

create_secrets() {
    echo "=========================================="
    echo "1. Creating Secrets in Secret Manager"
    echo "=========================================="

    for secret_name in "${SECRETS[@]}"; do
        log_step "Processing secret: $secret_name"

        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}[DRY RUN] Would create secret: $secret_name${NC}"
            continue
        fi

        # Check if secret already exists
        if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Secret already exists: $secret_name"

            # Ask if user wants to update
            read -p "Update existing secret? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Skipped: $secret_name"
                continue
            fi
        else
            # Create the secret
            gcloud secrets create "$secret_name" \
                --replication-policy="automatic" \
                --project="$PROJECT_ID" \
                --quiet
            log_info "Created secret: $secret_name"
        fi

        # Get secret value based on secret name
        local secret_value=""

        case "$secret_name" in
            "db-password-prod")
                # Try to read from file first
                if [ -f "/tmp/db-password-prod.txt" ]; then
                    secret_value=$(cat /tmp/db-password-prod.txt)
                    log_info "Using database password from /tmp/db-password-prod.txt"
                else
                    echo ""
                    echo -e "${YELLOW}Enter database password (hidden):${NC}"
                    read -s secret_value
                    echo ""
                fi
                ;;

            "jwt-secret-key-prod")
                # Generate JWT secret automatically
                secret_value=$(generate_jwt_secret)
                log_info "Generated JWT secret (256-bit)"
                ;;

            "openai-api-key-prod")
                echo ""
                echo -e "${YELLOW}Enter OpenAI API key (starts with sk-):${NC}"
                read -s secret_value
                echo ""

                # Validate format
                if [[ ! "$secret_value" =~ ^sk- ]]; then
                    log_error "Invalid OpenAI API key format (should start with 'sk-')"
                    continue
                fi
                ;;
        esac

        # Add secret version
        if [ -n "$secret_value" ]; then
            echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
                --data-file=- \
                --project="$PROJECT_ID" \
                --quiet
            log_info "Added secret value to: $secret_name"
        else
            log_warning "No value provided for: $secret_name"
        fi

        echo ""
    done
}

#############################################################################
# Grant IAM Permissions
#############################################################################

grant_iam_permissions() {
    echo "=========================================="
    echo "2. Granting IAM Permissions"
    echo "=========================================="

    log_step "Granting secretAccessor role to backend service account"

    for secret_name in "${SECRETS[@]}"; do
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}[DRY RUN] Would grant access to: $secret_name${NC}"
            continue
        fi

        # Check if secret exists
        if ! gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Secret not found, skipping: $secret_name"
            continue
        fi

        # Grant access
        gcloud secrets add-iam-policy-binding "$secret_name" \
            --member="serviceAccount:$BACKEND_SA" \
            --role="roles/secretmanager.secretAccessor" \
            --project="$PROJECT_ID" \
            --quiet &>/dev/null

        log_info "Granted access to: $secret_name"
    done

    echo ""
}

#############################################################################
# Validation
#############################################################################

validate_setup() {
    echo "=========================================="
    echo "3. Validating Setup"
    echo "=========================================="

    if [ "$DRY_RUN" = true ]; then
        log_info "Dry run complete - skipping validation"
        return
    fi

    local validation_failed=false

    # Validate secrets exist
    log_step "Validating secrets..."
    for secret_name in "${SECRETS[@]}"; do
        if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
            # Check if has at least one version
            local version_count=$(gcloud secrets versions list "$secret_name" \
                --project="$PROJECT_ID" \
                --format="value(name)" | wc -l)

            if [ "$version_count" -gt 0 ]; then
                log_info "Secret exists with $version_count version(s): $secret_name"
            else
                log_warning "Secret exists but has no versions: $secret_name"
                validation_failed=true
            fi
        else
            log_error "Secret not found: $secret_name"
            validation_failed=true
        fi
    done

    # Validate IAM permissions
    log_step "Validating IAM permissions..."
    local has_permission=true
    for secret_name in "${SECRETS[@]}"; do
        if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
            if gcloud secrets get-iam-policy "$secret_name" \
                --project="$PROJECT_ID" \
                --format="value(bindings.members)" 2>/dev/null | grep -q "$BACKEND_SA"; then
                log_info "Backend SA has access to: $secret_name"
            else
                log_warning "Backend SA missing access to: $secret_name"
                has_permission=false
            fi
        fi
    done

    if [ "$has_permission" = false ]; then
        validation_failed=true
    fi

    if [ "$validation_failed" = true ]; then
        echo ""
        log_error "Validation failed! Some secrets are missing or misconfigured."
        exit 1
    fi

    echo ""
}

#############################################################################
# Cleanup
#############################################################################

cleanup_temp_files() {
    if [ "$DRY_RUN" = false ]; then
        if [ -f "/tmp/db-password-prod.txt" ]; then
            log_step "Cleaning up temporary password file..."
            rm -f /tmp/db-password-prod.txt
            log_info "Deleted: /tmp/db-password-prod.txt"
        fi
    fi
}

#############################################################################
# Summary Output
#############################################################################

print_summary() {
    echo "=========================================="
    echo "✅ Secrets Setup Complete!"
    echo "=========================================="
    echo ""
    echo "📦 Created Secrets:"
    echo ""

    for secret_name in "${SECRETS[@]}"; do
        if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
            local version_count=$(gcloud secrets versions list "$secret_name" \
                --project="$PROJECT_ID" \
                --format="value(name)" | wc -l)
            echo "  • $secret_name ($version_count version(s))"
        fi
    done

    echo ""
    echo "🔐 IAM Permissions:"
    echo "  • Backend SA has secretAccessor role on all secrets"
    echo "  • Service Account: $BACKEND_SA"
    echo ""
    echo "📋 Secret Access from Backend:"
    echo ""
    echo "  Python example:"
    echo "  from google.cloud import secretmanager"
    echo ""
    echo "  client = secretmanager.SecretManagerServiceClient()"
    echo "  name = f\"projects/$PROJECT_ID/secrets/openai-api-key-prod/versions/latest\""
    echo "  response = client.access_secret_version(request={\"name\": name})"
    echo "  api_key = response.payload.data.decode(\"UTF-8\")"
    echo ""
    echo "📋 Next Steps:"
    echo "  1. Update backend configuration to read from Secret Manager"
    echo "  2. Deploy backend: ./scripts/gcp/deploy-to-production.sh"
    echo "  3. Test secret access from Cloud Run"
    echo ""
    echo "🔄 Secret Rotation:"
    echo "  To rotate a secret, add a new version:"
    echo "  echo \"new-value\" | gcloud secrets versions add SECRET_NAME --data-file=-"
    echo ""
    echo "=========================================="
}

#############################################################################
# Main Execution
#############################################################################

main() {
    echo ""
    echo "=========================================="
    echo "🔐 Secrets Setup - AI Resume Review v2"
    echo "=========================================="
    echo "Project: $PROJECT_ID"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Running in DRY RUN mode - no secrets will be created${NC}"
        echo ""
    fi

    # Execute setup steps
    check_prerequisites
    create_secrets
    grant_iam_permissions
    validate_setup
    cleanup_temp_files

    if [ "$DRY_RUN" = false ]; then
        print_summary
    else
        echo ""
        log_info "Dry run complete! Run without --dry-run to create secrets."
        echo ""
    fi
}

# Run main function
main
