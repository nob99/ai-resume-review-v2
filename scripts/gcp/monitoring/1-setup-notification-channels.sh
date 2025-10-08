#!/bin/bash

###############################################################################
# GCP Monitoring - Setup Notification Channels
###############################################################################
# This script creates notification channels for alerts to send to Slack and Email
#
# Usage:
#   ./1-setup-notification-channels.sh
#
# What it does:
#   1. Creates Slack notification channel
#   2. Creates Email notification channel
#   3. Verifies channels are created successfully
#
# Cost: FREE (notification channels have no cost)
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ytgrs-464303"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"  # Set via environment variable
EMAIL_ADDRESS="${EMAIL_ADDRESS:-nobu.fukumoto.99@gmail.com}"

# Check if Slack webhook URL is provided
if [ -z "$SLACK_WEBHOOK_URL" ]; then
  echo -e "${RED}Error: SLACK_WEBHOOK_URL environment variable not set${NC}"
  echo "Usage: SLACK_WEBHOOK_URL='your-webhook-url' ./1-setup-notification-channels.sh"
  exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setting Up Notification Channels${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if already exists
echo "Checking for existing notification channels..."
EXISTING_SLACK=$(gcloud alpha monitoring channels list \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="displayName:'AI Resume Review - Slack Alerts'" 2>/dev/null || echo "")

EXISTING_EMAIL=$(gcloud alpha monitoring channels list \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="displayName:'AI Resume Review - Email Alerts'" 2>/dev/null || echo "")

# Create Slack notification channel (using webhook type)
if [ -n "$EXISTING_SLACK" ]; then
  echo -e "${YELLOW}✓ Slack notification channel already exists${NC}"
  SLACK_CHANNEL_NAME="$EXISTING_SLACK"
else
  echo "Creating Slack notification channel..."
  SLACK_CHANNEL_NAME=$(gcloud alpha monitoring channels create \
    --display-name="AI Resume Review - Slack Alerts" \
    --type=webhook_tokenauth \
    --channel-labels=url="$SLACK_WEBHOOK_URL" \
    --project="$PROJECT_ID" \
    --format="value(name)")
  echo -e "${GREEN}✓ Slack notification channel created: $SLACK_CHANNEL_NAME${NC}"
fi

# Create Email notification channel
if [ -n "$EXISTING_EMAIL" ]; then
  echo -e "${YELLOW}✓ Email notification channel already exists${NC}"
  EMAIL_CHANNEL_NAME="$EXISTING_EMAIL"
else
  echo "Creating Email notification channel..."
  EMAIL_CHANNEL_NAME=$(gcloud alpha monitoring channels create \
    --display-name="AI Resume Review - Email Alerts" \
    --type=email \
    --channel-labels=email_address="$EMAIL_ADDRESS" \
    --project="$PROJECT_ID" \
    --format="value(name)")
  echo -e "${GREEN}✓ Email notification channel created: $EMAIL_CHANNEL_NAME${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Notification Channels Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Slack Channel: $SLACK_CHANNEL_NAME"
echo "Email Channel: $EMAIL_CHANNEL_NAME"
echo ""
echo "Next step: Run ./2-setup-uptime-checks.sh"
echo ""

# Save channel names to file for use by other scripts
mkdir -p /tmp/gcp-monitoring
echo "$SLACK_CHANNEL_NAME" > /tmp/gcp-monitoring/slack-channel-name
echo "$EMAIL_CHANNEL_NAME" > /tmp/gcp-monitoring/email-channel-name

echo -e "${GREEN}✓ Channel names saved to /tmp/gcp-monitoring/${NC}"
