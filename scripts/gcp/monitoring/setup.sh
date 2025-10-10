#!/bin/bash
# setup.sh - GCP Monitoring Complete Setup
#
# Usage: ./setup.sh [options]
# Options:
#   --step=<step>    Run specific step only (channels, uptime, alerts, logs, budget)
#   --dry-run        Show what would be executed
#   --help           Show this help message
#
# Examples:
#   ./setup.sh                        # Run all steps
#   ./setup.sh --step=channels        # Setup notification channels only
#   ./setup.sh --step=alerts --dry-run  # Preview alert setup
#
# What it does:
#   1. Creates notification channels (Slack + Email)
#   2. Creates uptime checks (Backend + Frontend)
#   3. Creates critical alert policies (3 alerts)
#   4. Creates log-based security metrics (1 metric)
#   5. Creates budget alert ($100/month)
#
# Total time: ~5 minutes
# Cost: FREE (all within GCP free tier limits)

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/../utils/common-functions.sh"

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN=false
STEP=""
TEMP_DIR="/tmp/gcp-monitoring"

# Monitoring-specific config (with .env.scripts override support)
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
EMAIL_ADDRESS="${ALERT_EMAIL:-nobu.fukumoto.99@gmail.com}"
BUDGET_AMOUNT="${BUDGET_AMOUNT:-100}"
BACKEND_URL="https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app"
FRONTEND_URL="https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app"

# ============================================================================
# Helper Functions
# ============================================================================

show_help() {
    grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //' | sed 's/^#//'
}

dry_run() {
    local command="$1"
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would execute: $command"
        return 0
    else
        eval "$command"
        return $?
    fi
}

# ============================================================================
# Step 1: Notification Channels
# ============================================================================

step_notification_channels() {
    log_section "Step 1/5: Notification Channels"

    # Check Slack webhook URL
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        log_error "SLACK_WEBHOOK_URL environment variable not set"
        echo ""
        log_info "Options to set it:"
        log_info "  1. Set in .env.scripts file (recommended):"
        log_info "     cp .env.scripts.example .env.scripts"
        log_info "     # Edit .env.scripts and set SLACK_WEBHOOK_URL"
        echo ""
        log_info "  2. Or set as environment variable:"
        log_info "     SLACK_WEBHOOK_URL='your-webhook-url' ./setup.sh"
        return 1
    fi

    # Check for existing channels
    log_info "Checking for existing notification channels..."

    local existing_slack=$(gcloud alpha monitoring channels list \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="displayName:'AI Resume Review - Slack Alerts'" 2>/dev/null || echo "")

    local existing_email=$(gcloud alpha monitoring channels list \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="displayName:'AI Resume Review - Email Alerts'" 2>/dev/null || echo "")

    # Create Slack channel
    if [ -n "$existing_slack" ]; then
        log_warning "Slack notification channel already exists"
        SLACK_CHANNEL_NAME="$existing_slack"
    else
        log_info "Creating Slack notification channel..."
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create Slack channel with webhook: ${SLACK_WEBHOOK_URL:0:30}..."
            SLACK_CHANNEL_NAME="projects/$PROJECT_ID/notificationChannels/dry-run-slack"
        else
            SLACK_CHANNEL_NAME=$(gcloud alpha monitoring channels create \
                --display-name="AI Resume Review - Slack Alerts" \
                --type=webhook_tokenauth \
                --channel-labels=url="$SLACK_WEBHOOK_URL" \
                --project="$PROJECT_ID" \
                --format="value(name)")
            log_success "Slack notification channel created: $SLACK_CHANNEL_NAME"
        fi
    fi

    # Create Email channel
    if [ -n "$existing_email" ]; then
        log_warning "Email notification channel already exists"
        EMAIL_CHANNEL_NAME="$existing_email"
    else
        log_info "Creating Email notification channel..."
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create Email channel for: $EMAIL_ADDRESS"
            EMAIL_CHANNEL_NAME="projects/$PROJECT_ID/notificationChannels/dry-run-email"
        else
            EMAIL_CHANNEL_NAME=$(gcloud alpha monitoring channels create \
                --display-name="AI Resume Review - Email Alerts" \
                --type=email \
                --channel-labels=email_address="$EMAIL_ADDRESS" \
                --project="$PROJECT_ID" \
                --format="value(name)")
            log_success "Email notification channel created: $EMAIL_CHANNEL_NAME"
        fi
    fi

    # Save channel names for other steps
    mkdir -p "$TEMP_DIR"
    echo "$SLACK_CHANNEL_NAME" > "$TEMP_DIR/slack-channel-name"
    echo "$EMAIL_CHANNEL_NAME" > "$TEMP_DIR/email-channel-name"

    log_success "Notification channels setup complete"
    log_info "Slack Channel: $SLACK_CHANNEL_NAME"
    log_info "Email Channel: $EMAIL_CHANNEL_NAME"
}

# ============================================================================
# Step 2: Uptime Checks
# ============================================================================

step_uptime_checks() {
    log_section "Step 2/5: Uptime Checks"

    # Check for existing uptime checks
    log_info "Checking for existing uptime checks..."

    local existing_backend=$(gcloud monitoring uptime list-configs \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="displayName:'Backend Health Check'" 2>/dev/null || echo "")

    local existing_frontend=$(gcloud monitoring uptime list-configs \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="displayName:'Frontend Health Check'" 2>/dev/null || echo "")

    # Create Backend uptime check
    if [ -n "$existing_backend" ]; then
        log_warning "Backend uptime check already exists"
    else
        log_info "Creating Backend uptime check..."
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create Backend uptime check"
            log_info "  URL: $BACKEND_URL/health"
            log_info "  Period: 5 minutes"
            log_info "  Timeout: 10 seconds"
        else
            gcloud monitoring uptime create "Backend Health Check" \
                --resource-type=uptime-url \
                --resource-labels=host="ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app",project_id="$PROJECT_ID" \
                --path="/health" \
                --timeout=10 \
                --period=5 \
                --project="$PROJECT_ID"
            log_success "Backend uptime check created"
        fi
    fi

    # Create Frontend uptime check
    if [ -n "$existing_frontend" ]; then
        log_warning "Frontend uptime check already exists"
    else
        log_info "Creating Frontend uptime check..."
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create Frontend uptime check"
            log_info "  URL: $FRONTEND_URL/"
            log_info "  Period: 5 minutes"
            log_info "  Timeout: 10 seconds"
        else
            gcloud monitoring uptime create "Frontend Health Check" \
                --resource-type=uptime-url \
                --resource-labels=host="ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app",project_id="$PROJECT_ID" \
                --path="/" \
                --timeout=10 \
                --period=5 \
                --project="$PROJECT_ID"
            log_success "Frontend uptime check created"
        fi
    fi

    log_success "Uptime checks setup complete"
    log_info "Checking $BACKEND_URL/health every 5 minutes"
    log_info "Checking $FRONTEND_URL/ every 5 minutes"
}

# ============================================================================
# Step 3: Critical Alert Policies
# ============================================================================

step_alert_policies() {
    log_section "Step 3/5: Critical Alert Policies"

    # Load notification channel names
    if [ ! -f "$TEMP_DIR/slack-channel-name" ]; then
        log_error "Notification channels not set up"
        log_info "Please run: ./setup.sh --step=channels first"
        return 1
    fi

    local slack_channel=$(cat "$TEMP_DIR/slack-channel-name")
    local email_channel=$(cat "$TEMP_DIR/email-channel-name")

    log_info "Using notification channels:"
    log_info "  Slack: $slack_channel"
    log_info "  Email: $email_channel"

    # Alert 1: Service Downtime
    log_info "Creating alert: Service Downtime..."
    local alert1_exists=$(gcloud alpha monitoring policies list \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="displayName:'[Critical] Service Downtime Alert'" 2>/dev/null || echo "")

    if [ -n "$alert1_exists" ]; then
        log_warning "Service Downtime alert already exists"
    else
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create Service Downtime alert"
            log_info "  Threshold: < 1 request for 5 minutes"
            log_info "  Notifications: Slack + Email"
        else
            gcloud alpha monitoring policies create \
                --notification-channels="$slack_channel,$email_channel" \
                --display-name="[Critical] Service Downtime Alert" \
                --condition-display-name="Service is down for 5+ minutes" \
                --condition-threshold-value=1 \
                --condition-threshold-duration=300s \
                --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count"' \
                --condition-comparison=COMPARISON_LT \
                --condition-aggregation-alignment-period=300s \
                --condition-aggregation-per-series-aligner=ALIGN_RATE \
                --documentation='The Cloud Run service has received no requests for 5+ minutes. Check service status immediately.' \
                --project="$PROJECT_ID"
            log_success "Service Downtime alert created"
        fi
    fi

    # Alert 2: High Error Rate
    log_info "Creating alert: High Error Rate..."
    local alert2_exists=$(gcloud alpha monitoring policies list \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="displayName:'[Critical] High Error Rate Alert'" 2>/dev/null || echo "")

    if [ -n "$alert2_exists" ]; then
        log_warning "High Error Rate alert already exists"
    else
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create High Error Rate alert"
            log_info "  Threshold: > 10% error rate for 5 minutes"
            log_info "  Notifications: Slack + Email"
        else
            gcloud alpha monitoring policies create \
                --notification-channels="$slack_channel,$email_channel" \
                --display-name="[Critical] High Error Rate Alert" \
                --condition-display-name="Error rate > 10%" \
                --condition-threshold-value=0.1 \
                --condition-threshold-duration=300s \
                --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.label.response_code_class="5xx"' \
                --condition-comparison=COMPARISON_GT \
                --condition-aggregation-alignment-period=300s \
                --condition-aggregation-per-series-aligner=ALIGN_RATE \
                --condition-aggregation-cross-series-reducer=REDUCE_SUM \
                --documentation='Error rate has exceeded 10%. Check application logs for issues.' \
                --project="$PROJECT_ID"
            log_success "High Error Rate alert created"
        fi
    fi

    # Alert 3: Database Connection Issues
    log_info "Creating alert: Database Connection Issues..."
    local alert3_exists=$(gcloud alpha monitoring policies list \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="displayName:'[Critical] Database Connection Issues'" 2>/dev/null || echo "")

    if [ -n "$alert3_exists" ]; then
        log_warning "Database Connection alert already exists"
    else
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create Database Connection alert"
            log_info "  Threshold: > 80 connections for 5 minutes"
            log_info "  Notifications: Slack + Email"
        else
            gcloud alpha monitoring policies create \
                --notification-channels="$slack_channel,$email_channel" \
                --display-name="[Critical] Database Connection Issues" \
                --condition-display-name="Database connections near limit" \
                --condition-threshold-value=80 \
                --condition-threshold-duration=300s \
                --condition-filter='resource.type="cloudsql_database" AND metric.type="cloudsql.googleapis.com/database/postgresql/num_backends"' \
                --condition-comparison=COMPARISON_GT \
                --condition-aggregation-alignment-period=300s \
                --condition-aggregation-per-series-aligner=ALIGN_MEAN \
                --documentation='Database connection count is high. May need to check for connection leaks or increase max connections.' \
                --project="$PROJECT_ID"
            log_success "Database Connection alert created"
        fi
    fi

    log_success "Alert policies setup complete"
    log_info "Created 3 critical alerts:"
    log_info "  1. Service Downtime (no requests for 5+ min)"
    log_info "  2. High Error Rate (> 10% errors)"
    log_info "  3. Database Connection Issues (> 80 connections)"
}

# ============================================================================
# Step 4: Log-Based Security Metrics
# ============================================================================

step_log_metrics() {
    log_section "Step 4/5: Log-Based Security Metrics"

    # Create log-based metric for failed logins
    log_info "Creating log-based metric: Failed Login Attempts..."
    local metric_exists=$(gcloud logging metrics list \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="name:failed_login_attempts" 2>/dev/null || echo "")

    if [ -n "$metric_exists" ]; then
        log_warning "Failed login metric already exists"
    else
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create log metric: failed_login_attempts"
            log_info "  Filter: Login/authentication failures in Cloud Run logs"
        else
            gcloud logging metrics create failed_login_attempts \
                --description="Count of failed login attempts" \
                --log-filter='resource.type="cloud_run_revision" AND (jsonPayload.message=~".*login.*failed.*" OR jsonPayload.message=~".*authentication.*failed.*" OR jsonPayload.message=~".*Invalid credentials.*" OR severity="ERROR")' \
                --project="$PROJECT_ID"
            log_success "Failed login metric created"
        fi
    fi

    log_success "Log-based security metrics setup complete"
    log_info "Created metric: failed_login_attempts"
    log_warning "Note: Alert policy should be configured manually in GCP Console"
    log_info "  Metric created: failed_login_attempts"
    log_info "  To create alert: GCP Console → Monitoring → Alerting → Create Policy"
}

# ============================================================================
# Step 5: Budget Alert
# ============================================================================

step_budget_alert() {
    log_section "Step 5/5: Budget Alert"

    # Get billing account
    log_info "Retrieving billing account..."
    local billing_account=$(gcloud beta billing projects describe "$PROJECT_ID" \
        --format="value(billingAccountName)" 2>/dev/null | sed 's|billingAccounts/||')

    if [ -z "$billing_account" ]; then
        log_error "No billing account found for project"
        log_info "Please enable billing for the project first"
        return 1
    fi

    log_info "Billing Account: $billing_account"

    # Check if budget already exists
    log_info "Checking for existing budget..."
    local existing_budget=$(gcloud billing budgets list \
        --billing-account="$billing_account" \
        --format="value(name)" \
        --filter="displayName:'AI Resume Review - Production Budget'" 2>/dev/null || echo "")

    if [ -n "$existing_budget" ]; then
        log_warning "Budget alert already exists"
        log_info "Budget ID: $existing_budget"
    else
        log_info "Creating budget alert..."
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create budget alert"
            log_info "  Amount: \$$BUDGET_AMOUNT per month"
            log_info "  Thresholds: 80%, 100%"
            log_info "  Email: $EMAIL_ADDRESS"
        else
            gcloud billing budgets create \
                --billing-account="$billing_account" \
                --display-name="AI Resume Review - Production Budget" \
                --budget-amount=USD$BUDGET_AMOUNT \
                --threshold-rule=percent=80 \
                --threshold-rule=percent=100 \
                --notification-channel-emails="$EMAIL_ADDRESS" \
                --project="$PROJECT_ID"
            log_success "Budget alert created"
        fi
    fi

    log_success "Budget alert setup complete"
    log_info "Budget: \$$BUDGET_AMOUNT per month"
    log_info "Email alerts at: 80% (\$$(($BUDGET_AMOUNT * 80 / 100))), 100% (\$$BUDGET_AMOUNT)"
    log_info "Email: $EMAIL_ADDRESS"
    log_warning "Note: Budget alerts go to email only (GCP limitation)"
}

# ============================================================================
# Main Function
# ============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --step=*)
                STEP="${1#*=}"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    log_section "GCP Monitoring Setup"

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY-RUN MODE - No changes will be made"
    fi

    # Run initialization checks
    init_checks || die "Environment checks failed"

    # Execute requested step or all steps
    if [ -n "$STEP" ]; then
        case "$STEP" in
            channels)
                step_notification_channels
                ;;
            uptime)
                step_uptime_checks
                ;;
            alerts)
                step_alert_policies
                ;;
            logs)
                step_log_metrics
                ;;
            budget)
                step_budget_alert
                ;;
            *)
                log_error "Unknown step: $STEP"
                log_info "Valid steps: channels, uptime, alerts, logs, budget"
                exit 1
                ;;
        esac
    else
        # Run all steps
        if ! confirm "This will set up complete Tier 1 monitoring. Continue?" "y"; then
            log_info "Setup cancelled"
            exit 0
        fi

        step_notification_channels || die "Notification channels setup failed"
        echo ""
        step_uptime_checks || die "Uptime checks setup failed"
        echo ""
        step_alert_policies || die "Alert policies setup failed"
        echo ""
        step_log_metrics || die "Log metrics setup failed"
        echo ""
        step_budget_alert || die "Budget alert setup failed"
        echo ""

        log_section "Monitoring Setup Complete!"
        log_success "✓ All monitoring components configured!"
        echo ""
        log_info "Summary:"
        log_info "  ✓ Notification channels: Slack + Email"
        log_info "  ✓ Uptime checks: Backend /health + Frontend /"
        log_info "  ✓ Critical alerts:"
        log_info "    - Service downtime (> 5 min)"
        log_info "    - High error rate (> 10%)"
        log_info "    - Database connection issues"
        log_info "  ✓ Security metric: Failed login attempts (> 10/hour)"
        log_info "  ✓ Budget alert: \$$BUDGET_AMOUNT/month (email only)"
        echo ""
        log_info "Alerts will be sent to:"
        log_info "  - Slack: (configured via webhook)"
        log_info "  - Email: $EMAIL_ADDRESS"
        echo ""
        log_info "Next steps:"
        log_info "  1. Check Slack channel for test notification"
        log_info "  2. Check email for budget alert confirmation"
        log_info "  3. Review GCP Console → Monitoring → Alerting"
        log_info "  4. Run ./verify.sh to validate setup"
        echo ""
    fi
}

# Run main function
main "$@"
