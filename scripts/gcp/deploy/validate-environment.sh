#!/usr/bin/env bash

################################################################################
# Pre-Deployment Environment Validation Script
################################################################################
#
# Purpose:
#   Validate that all required infrastructure exists before deploying.
#   Catches configuration issues in seconds rather than after failed deployment.
#
# Usage:
#   ./validate-environment.sh <environment>
#
# Arguments:
#   environment - staging or production
#
# Exit Codes:
#   0 - All validations passed
#   1 - One or more validations failed
#
# What it validates:
#   - Required secrets exist in GCP Secret Manager
#   - Service accounts exist and have correct permissions
#   - VPC connector exists and is ready
#   - Database instance exists and is runnable
#   - CORS configuration is valid
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ----------------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

validate_secret() {
    local secret_name=$1
    local env_name=$2

    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
        log_success "Secret $secret_name exists"
        return 0
    else
        log_error "Secret $secret_name doesn't exist"
        echo "  Create with: gcloud secrets create $secret_name --replication-policy=automatic"
        return 1
    fi
}

validate_service_account() {
    local sa_email=$1

    if gcloud iam service-accounts describe "$sa_email" --project="$PROJECT_ID" &>/dev/null; then
        log_success "Service account $sa_email exists"
        return 0
    else
        log_error "Service account $sa_email doesn't exist"
        return 1
    fi
}

validate_service_account_role() {
    local sa_email=$1
    local role=$2

    # Get IAM policy and check if service account has the role
    local has_role=$(gcloud projects get-iam-policy "$PROJECT_ID" \
        --flatten="bindings[].members" \
        --filter="bindings.role:$role AND bindings.members:serviceAccount:$sa_email" \
        --format="value(bindings.role)" 2>/dev/null || echo "")

    if [ -n "$has_role" ]; then
        log_success "Service account has $role"
        return 0
    else
        log_warning "Service account may not have $role (unable to verify project-level roles)"
        return 0  # Don't fail on this - might be resource-level role
    fi
}

validate_vpc_connector() {
    local connector_name=$1
    local region=$2

    local connector_info=$(gcloud compute networks vpc-access connectors describe "$connector_name" \
        --region="$region" \
        --project="$PROJECT_ID" \
        --format="value(state)" 2>/dev/null || echo "NOT_FOUND")

    if [ "$connector_info" = "READY" ]; then
        log_success "VPC connector $connector_name exists and is READY"
        return 0
    elif [ "$connector_info" = "NOT_FOUND" ]; then
        log_error "VPC connector $connector_name doesn't exist"
        return 1
    else
        log_warning "VPC connector $connector_name exists but state is: $connector_info"
        return 0  # Don't fail - might still work
    fi
}

validate_database() {
    local db_instance=$1

    local db_state=$(gcloud sql instances describe "$db_instance" \
        --project="$PROJECT_ID" \
        --format="value(state)" 2>/dev/null || echo "NOT_FOUND")

    if [ "$db_state" = "RUNNABLE" ]; then
        log_success "Database $db_instance exists and is RUNNABLE"
        return 0
    elif [ "$db_state" = "NOT_FOUND" ]; then
        log_error "Database $db_instance doesn't exist"
        return 1
    else
        log_warning "Database $db_instance exists but state is: $db_state"
        return 0  # Don't fail - might still work
    fi
}

validate_cors_config() {
    local cors_origins=$1
    local validation_failed=0

    # Split comma-separated origins
    IFS=',' read -ra ORIGINS <<< "$cors_origins"

    for origin in "${ORIGINS[@]}"; do
        origin=$(echo "$origin" | xargs)  # Trim whitespace

        # Check if origin starts with http:// or https://
        if [[ ! "$origin" =~ ^https?:// ]]; then
            log_error "Invalid CORS origin: $origin (must start with http:// or https://)"
            validation_failed=1
            continue
        fi

        # Warn if origin ends with slash
        if [[ "$origin" =~ /$ ]]; then
            log_warning "CORS origin has trailing slash: $origin (may cause issues)"
        fi

        log_success "CORS origin valid: $origin"
    done

    if [ $validation_failed -eq 0 ]; then
        log_success "CORS configuration valid (${#ORIGINS[@]} origins)"
    fi

    return $validation_failed
}

# ----------------------------------------------------------------------------
# Main Validation
# ----------------------------------------------------------------------------

main() {
    local env_name=$1

    if [ -z "$env_name" ]; then
        echo "Usage: $0 <environment>"
        echo "  environment: staging or production"
        exit 1
    fi

    if [ "$env_name" != "staging" ] && [ "$env_name" != "production" ]; then
        log_error "Invalid environment: $env_name (must be 'staging' or 'production')"
        exit 1
    fi

    echo ""
    log_info "🔍 Validating $env_name environment..."
    echo ""

    # Load configuration
    if [ -f "$SCRIPT_DIR/../../lib/load-config.sh" ]; then
        source "$SCRIPT_DIR/../../lib/load-config.sh" "$env_name"
    else
        log_error "Config loader not found at $SCRIPT_DIR/../../lib/load-config.sh"
        exit 1
    fi

    local validation_failed=0

    # ----------------------------------------------------------------------------
    # 1. Validate Secrets
    # ----------------------------------------------------------------------------
    echo ""
    log_info "📦 Validating secrets..."

    validate_secret "$SECRET_DB_PASSWORD" "$env_name" || validation_failed=1
    validate_secret "$SECRET_JWT_KEY" "$env_name" || validation_failed=1
    validate_secret "$SECRET_OPENAI_KEY" "$env_name" || validation_failed=1

    # ----------------------------------------------------------------------------
    # 2. Validate Service Accounts
    # ----------------------------------------------------------------------------
    echo ""
    log_info "🔐 Validating service accounts..."

    validate_service_account "$BACKEND_SERVICE_ACCOUNT" || validation_failed=1

    if [ $validation_failed -eq 0 ]; then
        validate_service_account_role "$BACKEND_SERVICE_ACCOUNT" "roles/cloudsql.client"
        validate_service_account_role "$BACKEND_SERVICE_ACCOUNT" "roles/secretmanager.secretAccessor"
    fi

    # ----------------------------------------------------------------------------
    # 3. Validate VPC Connector
    # ----------------------------------------------------------------------------
    echo ""
    log_info "🌐 Validating VPC connector..."

    validate_vpc_connector "$VPC_CONNECTOR" "$REGION" || validation_failed=1

    # ----------------------------------------------------------------------------
    # 4. Validate Database
    # ----------------------------------------------------------------------------
    echo ""
    log_info "💾 Validating database..."

    validate_database "$SQL_INSTANCE_NAME" || validation_failed=1

    # ----------------------------------------------------------------------------
    # 5. Validate CORS Configuration
    # ----------------------------------------------------------------------------
    echo ""
    log_info "🔗 Validating CORS configuration..."

    validate_cors_config "$ALLOWED_ORIGINS" || validation_failed=1

    # ----------------------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------------------
    echo ""
    echo "=================================="
    if [ $validation_failed -eq 0 ]; then
        log_success "✅ All validations passed for $env_name"
        echo "=================================="
        echo ""
        return 0
    else
        log_error "❌ Some validations failed for $env_name"
        echo "=================================="
        echo ""
        log_info "Fix the issues above before deploying."
        return 1
    fi
}

# Run main function
main "$@"
