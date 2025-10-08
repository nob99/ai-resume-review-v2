#!/bin/bash

###############################################################################
# GCP Monitoring - Verify Setup
###############################################################################
# This script verifies that monitoring components are properly configured
#
# Usage:
#   ./verify-setup.sh
#
# What it checks:
#   1. Notification channels exist
#   2. Uptime checks are configured
#   3. Alert policies are active
#   4. Log metrics are created
#   5. Budget alerts are set
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ID="ytgrs-464303"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}GCP Monitoring - Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check 1: Notification Channels
echo -e "${BLUE}[1/5] Checking Notification Channels...${NC}"
CHANNEL_COUNT=$(gcloud alpha monitoring channels list \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="displayName~'AI Resume Review'" 2>/dev/null | wc -l)

if [ "$CHANNEL_COUNT" -ge 2 ]; then
  echo -e "${GREEN}✓ Notification channels configured ($CHANNEL_COUNT channels)${NC}"
  gcloud alpha monitoring channels list \
    --project="$PROJECT_ID" \
    --filter="displayName~'AI Resume Review'" \
    --format="table(displayName,type)" 2>/dev/null
else
  echo -e "${YELLOW}⚠ Notification channels not found${NC}"
  echo "  Run: ./1-setup-notification-channels.sh"
fi
echo ""

# Check 2: Uptime Checks
echo -e "${BLUE}[2/5] Checking Uptime Checks...${NC}"
UPTIME_COUNT=$(gcloud monitoring uptime-checks list \
  --project="$PROJECT_ID" \
  --format="value(name)" 2>/dev/null | wc -l)

if [ "$UPTIME_COUNT" -ge 2 ]; then
  echo -e "${GREEN}✓ Uptime checks configured ($UPTIME_COUNT checks)${NC}"
  gcloud monitoring uptime-checks list \
    --project="$PROJECT_ID" \
    --format="table(displayName,period)" 2>/dev/null
else
  echo -e "${YELLOW}⚠ Uptime checks not found${NC}"
  echo "  Run: ./2-setup-uptime-checks.sh"
fi
echo ""

# Check 3: Alert Policies
echo -e "${BLUE}[3/5] Checking Alert Policies...${NC}"
ALERT_COUNT=$(gcloud alpha monitoring policies list \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="displayName~'Critical|Security'" 2>/dev/null | wc -l)

if [ "$ALERT_COUNT" -ge 3 ]; then
  echo -e "${GREEN}✓ Alert policies configured ($ALERT_COUNT policies)${NC}"
  gcloud alpha monitoring policies list \
    --project="$PROJECT_ID" \
    --filter="displayName~'Critical|Security'" \
    --format="table(displayName,enabled)" 2>/dev/null
else
  echo -e "${YELLOW}⚠ Alert policies not found or incomplete${NC}"
  echo "  Run: ./3-setup-critical-alerts.sh"
fi
echo ""

# Check 4: Log Metrics
echo -e "${BLUE}[4/5] Checking Log-Based Metrics...${NC}"
LOG_METRIC=$(gcloud logging metrics list \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="name:failed_login_attempts" 2>/dev/null || echo "")

if [ -n "$LOG_METRIC" ]; then
  echo -e "${GREEN}✓ Log-based metric configured${NC}"
  gcloud logging metrics list \
    --project="$PROJECT_ID" \
    --filter="name:failed_login_attempts" \
    --format="table(name,description)" 2>/dev/null
else
  echo -e "${YELLOW}⚠ Log-based metric not found${NC}"
  echo "  Run: ./4-setup-log-metrics.sh"
fi
echo ""

# Check 5: Budget Alert
echo -e "${BLUE}[5/5] Checking Budget Alert...${NC}"
BILLING_ACCOUNT=$(gcloud beta billing projects describe "$PROJECT_ID" \
  --format="value(billingAccountName)" 2>/dev/null | sed 's|billingAccounts/||' || echo "")

if [ -n "$BILLING_ACCOUNT" ]; then
  BUDGET_COUNT=$(gcloud billing budgets list \
    --billing-account="$BILLING_ACCOUNT" \
    --format="value(name)" \
    --filter="displayName~'AI Resume Review'" 2>/dev/null | wc -l)

  if [ "$BUDGET_COUNT" -ge 1 ]; then
    echo -e "${GREEN}✓ Budget alert configured${NC}"
    gcloud billing budgets list \
      --billing-account="$BILLING_ACCOUNT" \
      --filter="displayName~'AI Resume Review'" \
      --format="table(displayName,budgetAmount)" 2>/dev/null
  else
    echo -e "${YELLOW}⚠ Budget alert not found${NC}"
    echo "  Run: ./5-setup-budget-alert.sh"
  fi
else
  echo -e "${YELLOW}⚠ Billing account not found${NC}"
  echo "  Billing may not be enabled for this project"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

TOTAL_CHECKS=5
PASSED_CHECKS=0

[ "$CHANNEL_COUNT" -ge 2 ] && ((PASSED_CHECKS++))
[ "$UPTIME_COUNT" -ge 2 ] && ((PASSED_CHECKS++))
[ "$ALERT_COUNT" -ge 3 ] && ((PASSED_CHECKS++))
[ -n "$LOG_METRIC" ] && ((PASSED_CHECKS++))
[ -n "$BILLING_ACCOUNT" ] && [ "$BUDGET_COUNT" -ge 1 ] && ((PASSED_CHECKS++))

if [ "$PASSED_CHECKS" -eq "$TOTAL_CHECKS" ]; then
  echo -e "${GREEN}✅ All monitoring components configured! ($PASSED_CHECKS/$TOTAL_CHECKS)${NC}"
  echo ""
  echo "Your production monitoring is fully active."
  echo "Check Slack and email for any alerts."
elif [ "$PASSED_CHECKS" -gt 0 ]; then
  echo -e "${YELLOW}⚠ Partial setup complete ($PASSED_CHECKS/$TOTAL_CHECKS)${NC}"
  echo ""
  echo "Run missing setup scripts or execute:"
  echo "  ./run-all-setup.sh"
else
  echo -e "${RED}❌ No monitoring components found${NC}"
  echo ""
  echo "Run the complete setup:"
  echo "  ./run-all-setup.sh"
fi
echo ""
