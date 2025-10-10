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

# Source common functions to get PROJECT_ID and .env.scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/common-functions.sh"

# Colors for output (use common-functions colors)
RED="$COLOR_RED"
GREEN="$COLOR_GREEN"
YELLOW="$COLOR_YELLOW"
NC="$COLOR_RESET"

# Configuration (with .env.scripts override support)
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"  # Set via environment variable or .env.scripts
EMAIL_ADDRESS="${ALERT_EMAIL:-nobu.fukumoto.99@gmail.com}"

# Check if Slack webhook URL is provided
if [ -z "$SLACK_WEBHOOK_URL" ]; then
  echo -e "${RED}Error: SLACK_WEBHOOK_URL environment variable not set${NC}"
  echo ""
  echo "Options to set it:"
  echo "  1. Set in .env.scripts file (recommended):"
  echo "     cp .env.scripts.example .env.scripts"
  echo "     # Edit .env.scripts and set SLACK_WEBHOOK_URL"
  echo ""
  echo "  2. Or set as environment variable:"
  echo "     SLACK_WEBHOOK_URL='your-webhook-url' ./1-setup-notification-channels.sh"
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
