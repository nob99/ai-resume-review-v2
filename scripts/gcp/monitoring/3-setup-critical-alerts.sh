#!/bin/bash

###############################################################################
# GCP Monitoring - Setup Critical Alert Policies
###############################################################################
# This script creates critical alert policies for production monitoring
#
# Usage:
#   ./3-setup-critical-alerts.sh
#
# What it does:
#   1. Creates alert for service downtime (> 5 minutes)
#   2. Creates alert for high error rate (> 10%)
#   3. Creates alert for database connection issues
#   All alerts send to both Slack and Email
#
# Cost: FREE (first 150 MB of monitoring data per month is free)
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
echo -e "${GREEN}Setting Up Critical Alert Policies${NC}"
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

echo "Using notification channels:"
echo "  Slack: $SLACK_CHANNEL"
echo "  Email: $EMAIL_CHANNEL"
echo ""

# Alert 1: Service Downtime
echo "Creating alert policy: Service Downtime..."
ALERT_1_EXISTS=$(gcloud alpha monitoring policies list \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="displayName:'[Critical] Service Downtime Alert'" 2>/dev/null || echo "")

if [ -n "$ALERT_1_EXISTS" ]; then
  echo -e "${YELLOW}✓ Service Downtime alert already exists${NC}"
else
  gcloud alpha monitoring policies create \
    --notification-channels="$SLACK_CHANNEL,$EMAIL_CHANNEL" \
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
  echo -e "${GREEN}✓ Service Downtime alert created${NC}"
fi

# Alert 2: High Error Rate
echo "Creating alert policy: High Error Rate..."
ALERT_2_EXISTS=$(gcloud alpha monitoring policies list \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="displayName:'[Critical] High Error Rate Alert'" 2>/dev/null || echo "")

if [ -n "$ALERT_2_EXISTS" ]; then
  echo -e "${YELLOW}✓ High Error Rate alert already exists${NC}"
else
  gcloud alpha monitoring policies create \
    --notification-channels="$SLACK_CHANNEL,$EMAIL_CHANNEL" \
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
  echo -e "${GREEN}✓ High Error Rate alert created${NC}"
fi

# Alert 3: Database Connection Issues
echo "Creating alert policy: Database Connection Issues..."
ALERT_3_EXISTS=$(gcloud alpha monitoring policies list \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="displayName:'[Critical] Database Connection Issues'" 2>/dev/null || echo "")

if [ -n "$ALERT_3_EXISTS" ]; then
  echo -e "${YELLOW}✓ Database Connection alert already exists${NC}"
else
  gcloud alpha monitoring policies create \
    --notification-channels="$SLACK_CHANNEL,$EMAIL_CHANNEL" \
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
  echo -e "${GREEN}✓ Database Connection alert created${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Critical Alert Policies Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Created 3 alert policies:"
echo "  1. Service Downtime (no requests for 5+ min)"
echo "  2. High Error Rate (> 10% errors)"
echo "  3. Database Connection Issues (> 80 connections)"
echo ""
echo "All alerts will notify:"
echo "  - Slack: $SLACK_CHANNEL"
echo "  - Email: $EMAIL_CHANNEL"
echo ""
echo "Next step: Run ./4-setup-log-metrics.sh"
echo ""
