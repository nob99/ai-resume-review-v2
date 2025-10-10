#!/bin/bash
# verify.sh - Verify GCP Monitoring Setup
#
# Usage: ./verify.sh
#
# What it checks:
#   1. Notification channels exist
#   2. Uptime checks are configured
#   3. Alert policies are active
#   4. Log metrics are created
#   5. Budget alerts are set

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/../utils/common-functions.sh"

# ============================================================================
# Main Verification
# ============================================================================

main() {
    log_section "GCP Monitoring - Verification"

    # Initialize checks
    init_checks || die "Environment checks failed"

    local total_checks=5
    local passed_checks=0

    # Check 1: Notification Channels
    log_info "[1/5] Checking Notification Channels..."
    local channel_count=$(gcloud alpha monitoring channels list \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="displayName~'AI Resume Review'" 2>/dev/null | wc -l | tr -d ' ')

    if [ "$channel_count" -ge 2 ]; then
        log_success "Notification channels configured ($channel_count channels)"
        gcloud alpha monitoring channels list \
            --project="$PROJECT_ID" \
            --filter="displayName~'AI Resume Review'" \
            --format="table(displayName,type)" 2>/dev/null
        ((passed_checks++))
    else
        log_warning "Notification channels not found"
        log_info "  Run: ./setup.sh --step=channels"
    fi
    echo ""

    # Check 2: Uptime Checks
    log_info "[2/5] Checking Uptime Checks..."
    local uptime_count=$(gcloud monitoring uptime-checks list \
        --project="$PROJECT_ID" \
        --format="value(name)" 2>/dev/null | wc -l | tr -d ' ')

    if [ "$uptime_count" -ge 2 ]; then
        log_success "Uptime checks configured ($uptime_count checks)"
        gcloud monitoring uptime-checks list \
            --project="$PROJECT_ID" \
            --format="table(displayName,period)" 2>/dev/null
        ((passed_checks++))
    else
        log_warning "Uptime checks not found"
        log_info "  Run: ./setup.sh --step=uptime"
    fi
    echo ""

    # Check 3: Alert Policies
    log_info "[3/5] Checking Alert Policies..."
    local alert_count=$(gcloud alpha monitoring policies list \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="displayName~'Critical|Security'" 2>/dev/null | wc -l | tr -d ' ')

    if [ "$alert_count" -ge 3 ]; then
        log_success "Alert policies configured ($alert_count policies)"
        gcloud alpha monitoring policies list \
            --project="$PROJECT_ID" \
            --filter="displayName~'Critical|Security'" \
            --format="table(displayName,enabled)" 2>/dev/null
        ((passed_checks++))
    else
        log_warning "Alert policies not found or incomplete"
        log_info "  Run: ./setup.sh --step=alerts"
    fi
    echo ""

    # Check 4: Log Metrics
    log_info "[4/5] Checking Log-Based Metrics..."
    local log_metric=$(gcloud logging metrics list \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="name:failed_login_attempts" 2>/dev/null || echo "")

    if [ -n "$log_metric" ]; then
        log_success "Log-based metric configured"
        gcloud logging metrics list \
            --project="$PROJECT_ID" \
            --filter="name:failed_login_attempts" \
            --format="table(name,description)" 2>/dev/null
        ((passed_checks++))
    else
        log_warning "Log-based metric not found"
        log_info "  Run: ./setup.sh --step=logs"
    fi
    echo ""

    # Check 5: Budget Alert
    log_info "[5/5] Checking Budget Alert..."
    local billing_account=$(gcloud beta billing projects describe "$PROJECT_ID" \
        --format="value(billingAccountName)" 2>/dev/null | sed 's|billingAccounts/||' || echo "")

    if [ -n "$billing_account" ]; then
        local budget_count=$(gcloud billing budgets list \
            --billing-account="$billing_account" \
            --format="value(name)" \
            --filter="displayName~'AI Resume Review'" 2>/dev/null | wc -l | tr -d ' ')

        if [ "$budget_count" -ge 1 ]; then
            log_success "Budget alert configured"
            gcloud billing budgets list \
                --billing-account="$billing_account" \
                --filter="displayName~'AI Resume Review'" \
                --format="table(displayName,budgetAmount)" 2>/dev/null
            ((passed_checks++))
        else
            log_warning "Budget alert not found"
            log_info "  Run: ./setup.sh --step=budget"
        fi
    else
        log_warning "Billing account not found"
        log_info "  Billing may not be enabled for this project"
    fi
    echo ""

    # Summary
    log_section "Verification Summary"

    if [ "$passed_checks" -eq "$total_checks" ]; then
        log_success "✅ All monitoring components configured! ($passed_checks/$total_checks)"
        echo ""
        log_info "Your production monitoring is fully active."
        log_info "Check Slack and email for any alerts."
    elif [ "$passed_checks" -gt 0 ]; then
        log_warning "⚠ Partial setup complete ($passed_checks/$total_checks)"
        echo ""
        log_info "Run missing setup steps or execute:"
        log_info "  ./setup.sh"
    else
        log_error "❌ No monitoring components found"
        echo ""
        log_info "Run the complete setup:"
        log_info "  ./setup.sh"
    fi
    echo ""
}

# Run main function
main "$@"
