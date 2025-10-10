#!/bin/bash
# rollback.sh - Rollback Cloud Run services to previous revision
#
# Usage:
#   ./rollback.sh [backend|frontend|both]
#
# This script:
# - Lists available revisions with timestamps
# - Allows selecting which revision to rollback to
# - Routes 100% traffic to selected revision
# - Verifies rollback succeeded
#
# Safety features:
# - Confirmation prompt before rollback
# - Shows current vs target revision
# - Displays deployment timestamps

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/common-functions.sh"

# ============================================================================
# Helper Functions
# ============================================================================

# Get current serving revision for a service
get_current_revision() {
    local service_name=$1
    gcloud run services describe "$service_name" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.traffic[0].revisionName)" 2>/dev/null
}

# List all revisions for a service
list_revisions() {
    local service_name=$1

    log_info "Available revisions for $service_name:"
    echo ""

    gcloud run revisions list \
        --service="$service_name" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="table(
            metadata.name,
            status.conditions[0].lastTransitionTime.date('%Y-%m-%d %H:%M:%S'),
            metadata.labels.version,
            status.conditions[0].status
        )" 2>/dev/null

    echo ""
}

# Get revision names as array
get_revision_names() {
    local service_name=$1
    gcloud run revisions list \
        --service="$service_name" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(metadata.name)" 2>/dev/null
}

# Rollback a single service
rollback_service() {
    local service_name=$1

    log_section "Rolling Back: $service_name"

    # Get current revision
    local current_revision=$(get_current_revision "$service_name")

    if [ -z "$current_revision" ]; then
        log_error "Could not determine current revision for $service_name"
        return 1
    fi

    log_info "Current revision: $current_revision"
    echo ""

    # List available revisions
    list_revisions "$service_name"

    # Get all revision names
    local revisions=($(get_revision_names "$service_name"))

    if [ ${#revisions[@]} -lt 2 ]; then
        log_error "Only one revision exists. Cannot rollback."
        return 1
    fi

    # Find previous revision (second in list, since first is current)
    local previous_revision=""
    for rev in "${revisions[@]}"; do
        if [ "$rev" != "$current_revision" ]; then
            previous_revision="$rev"
            break
        fi
    done

    if [ -z "$previous_revision" ]; then
        log_error "Could not determine previous revision"
        return 1
    fi

    log_warning "Rollback plan:"
    log_info "  FROM: $current_revision (current)"
    log_info "  TO:   $previous_revision (previous)"
    echo ""

    if ! confirm "Proceed with rollback?" "n"; then
        log_info "Rollback cancelled"
        return 0
    fi

    # Execute rollback
    log_info "Routing 100% traffic to $previous_revision..."

    gcloud run services update-traffic "$service_name" \
        --to-revisions="$previous_revision=100" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --quiet

    check_status "Failed to update traffic routing"

    log_success "Rollback completed!"

    # Verify rollback
    echo ""
    log_info "Verifying rollback..."
    sleep 3

    local new_current=$(get_current_revision "$service_name")

    if [ "$new_current" = "$previous_revision" ]; then
        log_success "Verified: Traffic is now routed to $previous_revision"

        # Get service URL
        local service_url=$(get_service_url "$service_name")
        log_info "Service URL: $service_url"

        echo ""
        log_info "Recommend running health check:"
        log_info "  cd ../verify && ./health-check.sh"
    else
        log_warning "Current revision: $new_current"
        log_warning "Expected: $previous_revision"
        log_warning "Rollback may not have completed successfully"
        return 1
    fi

    echo ""
    return 0
}

# ============================================================================
# Main Function
# ============================================================================

main() {
    local target="${1:-}"

    log_section "Cloud Run Service Rollback"

    # Validate target
    if [ -z "$target" ]; then
        log_error "Missing target argument"
        echo ""
        echo "Usage: $0 [backend|frontend|both]"
        echo ""
        echo "Examples:"
        echo "  $0 backend   # Rollback backend only"
        echo "  $0 frontend  # Rollback frontend only"
        echo "  $0 both      # Rollback both services"
        echo ""
        exit 1
    fi

    # Initialize checks
    init_checks || die "Environment checks failed"

    echo ""

    # Execute rollback based on target
    case "$target" in
        backend)
            rollback_service "$BACKEND_SERVICE_NAME"
            ;;

        frontend)
            rollback_service "$FRONTEND_SERVICE_NAME"
            ;;

        both)
            rollback_service "$BACKEND_SERVICE_NAME"
            echo ""
            rollback_service "$FRONTEND_SERVICE_NAME"
            ;;

        *)
            log_error "Invalid target: $target"
            echo ""
            echo "Valid targets: backend, frontend, both"
            exit 1
            ;;
    esac

    # Final summary
    log_section "Rollback Complete"

    log_success "Service(s) have been rolled back to previous revision"
    echo ""
    log_warning "Important next steps:"
    log_info "  1. Run health checks to verify services are working"
    log_info "  2. Check application logs for any errors"
    log_info "  3. Monitor Cloud Run metrics for anomalies"
    echo ""
    log_info "If issues persist, you may need to:"
    log_info "  - Rollback again to an earlier revision"
    log_info "  - Redeploy from a known good commit"
    echo ""
}

# Run main function
main "$@"
