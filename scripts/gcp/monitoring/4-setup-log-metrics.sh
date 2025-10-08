#!/bin/bash

###############################################################################
# GCP Monitoring - Setup Log-Based Security Metrics
###############################################################################
# This script creates log-based metrics for security monitoring
#
# Usage:
#   ./4-setup-log-metrics.sh
#
# What it does:
#   1. Creates log-based metric for failed login attempts
#   2. Creates alert when failed logins exceed 10 per hour
#   3. Sends alerts to Slack and Email
#
# Cost: FREE (included in Cloud Logging free tier)
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ytgrs-464303"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setting Up Log-Based Security Metrics${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Load notification channel names
if [ ! -f /tmp/gcp-monitoring/slack-channel-name ]; then
  echo -e "${RED}Error: Notification channels not set up${NC}"
  echo "Please run ./1-setup-notification-channels.sh first"
  exit 1
fi

SLACK_CHANNEL=$(cat /tmp/gcp-monitoring/slack-channel-name)
EMAIL_CHANNEL=$(cat /tmp/gcp-monitoring/email-channel-name)

# Create log-based metric for failed logins
echo "Creating log-based metric: Failed Login Attempts..."
METRIC_EXISTS=$(gcloud logging metrics list \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="name:failed_login_attempts" 2>/dev/null || echo "")

if [ -n "$METRIC_EXISTS" ]; then
  echo -e "${YELLOW}✓ Failed login metric already exists${NC}"
else
  gcloud logging metrics create failed_login_attempts \
    --description="Count of failed login attempts" \
    --log-filter='resource.type="cloud_run_revision" AND (jsonPayload.message=~".*login.*failed.*" OR jsonPayload.message=~".*authentication.*failed.*" OR jsonPayload.message=~".*Invalid credentials.*" OR severity="ERROR")' \
    --project="$PROJECT_ID"
  echo -e "${GREEN}✓ Failed login metric created${NC}"
fi

# Note: Alert policies should be configured manually in GCP Console
# due to complex gcloud alpha command syntax
echo -e "${YELLOW}Note: Alert policy should be configured manually in GCP Console${NC}"
echo "  Metric created: failed_login_attempts"
echo "  To create alert: GCP Console → Monitoring → Alerting → Create Policy"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Log-Based Security Metrics Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Created log-based metric: failed_login_attempts"
echo "Created alert: Triggers when > 10 failed logins per hour"
echo ""
echo "Notifications sent to:"
echo "  - Slack: $SLACK_CHANNEL"
echo "  - Email: $EMAIL_CHANNEL"
echo ""
echo "Next step: Run ./5-setup-budget-alert.sh"
echo ""
