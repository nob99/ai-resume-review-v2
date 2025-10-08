#!/bin/bash

###############################################################################
# GCP Monitoring - Setup Budget Alert
###############################################################################
# This script creates a budget alert for GCP spending
#
# Usage:
#   ./5-setup-budget-alert.sh
#
# What it does:
#   1. Creates budget of $100/month
#   2. Sends email alert at 80% ($80) and 100% ($100)
#   3. Alerts go to email only (GCP limitation)
#
# Cost: FREE (budget alerts have no cost)
#
# Note: Budget alerts can ONLY send to email, not Slack
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ytgrs-464303"
BUDGET_AMOUNT=100
EMAIL_ADDRESS="nobu.fukumoto.99@gmail.com"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setting Up Budget Alert${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get billing account ID
echo "Retrieving billing account..."
BILLING_ACCOUNT=$(gcloud beta billing projects describe "$PROJECT_ID" \
  --format="value(billingAccountName)" 2>/dev/null | sed 's|billingAccounts/||')

if [ -z "$BILLING_ACCOUNT" ]; then
  echo -e "${RED}Error: No billing account found for project${NC}"
  echo "Please enable billing for the project first"
  exit 1
fi

echo "Billing Account: $BILLING_ACCOUNT"
echo ""

# Check if budget already exists
echo "Checking for existing budget..."
EXISTING_BUDGET=$(gcloud billing budgets list \
  --billing-account="$BILLING_ACCOUNT" \
  --format="value(name)" \
  --filter="displayName:'AI Resume Review - Production Budget'" 2>/dev/null || echo "")

if [ -n "$EXISTING_BUDGET" ]; then
  echo -e "${YELLOW}✓ Budget alert already exists${NC}"
  echo "Budget ID: $EXISTING_BUDGET"
else
  echo "Creating budget alert..."

  # Create budget with email notifications
  gcloud billing budgets create \
    --billing-account="$BILLING_ACCOUNT" \
    --display-name="AI Resume Review - Production Budget" \
    --budget-amount=USD$BUDGET_AMOUNT \
    --threshold-rule=percent=80 \
    --threshold-rule=percent=100 \
    --notification-channel-emails="$EMAIL_ADDRESS" \
    --project="$PROJECT_ID"

  echo -e "${GREEN}✓ Budget alert created${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Budget Alert Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Budget: \$$BUDGET_AMOUNT per month"
echo "Email alerts at:"
echo "  - 80% (\$80)"
echo "  - 100% (\$100)"
echo ""
echo "Email: $EMAIL_ADDRESS"
echo ""
echo -e "${YELLOW}Note: Budget alerts go to email only (GCP limitation)${NC}"
echo ""
echo "Next step: Run ./run-all-setup.sh to execute all scripts, or review README.md"
echo ""
