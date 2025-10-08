#!/bin/bash

###############################################################################
# GCP Monitoring - Run All Setup Scripts
###############################################################################
# This script runs all monitoring setup scripts in the correct order
#
# Usage:
#   ./run-all-setup.sh
#
# What it does:
#   1. Sets up notification channels (Slack + Email)
#   2. Creates uptime checks (Backend + Frontend)
#   3. Creates critical alert policies (3 alerts)
#   4. Creates log-based security metrics (1 metric)
#   5. Creates budget alert ($100/month)
#
# Total time: ~5 minutes
# Cost: FREE (all within GCP free tier limits)
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AI Resume Review - Monitoring Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "This will set up complete Tier 1 monitoring:"
echo "  - Notification channels (Slack + Email)"
echo "  - Uptime checks (2)"
echo "  - Critical alerts (3)"
echo "  - Security metrics (1)"
echo "  - Budget alert (\$100/month)"
echo ""
echo -e "${YELLOW}Estimated time: 5 minutes${NC}"
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Setup cancelled."
  exit 0
fi

echo ""
echo -e "${GREEN}Starting setup...${NC}"
echo ""

# Step 1: Notification Channels
echo -e "${BLUE}[1/5] Setting up notification channels...${NC}"
"$SCRIPT_DIR/1-setup-notification-channels.sh"
echo ""

# Step 2: Uptime Checks
echo -e "${BLUE}[2/5] Creating uptime checks...${NC}"
"$SCRIPT_DIR/2-setup-uptime-checks.sh"
echo ""

# Step 3: Critical Alerts
echo -e "${BLUE}[3/5] Creating critical alert policies...${NC}"
"$SCRIPT_DIR/3-setup-critical-alerts.sh"
echo ""

# Step 4: Log Metrics
echo -e "${BLUE}[4/5] Creating log-based security metrics...${NC}"
"$SCRIPT_DIR/4-setup-log-metrics.sh"
echo ""

# Step 5: Budget Alert
echo -e "${BLUE}[5/5] Creating budget alert...${NC}"
"$SCRIPT_DIR/5-setup-budget-alert.sh"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ ALL MONITORING SETUP COMPLETE!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Summary:"
echo "  ✓ Notification channels: Slack + Email"
echo "  ✓ Uptime checks: Backend /health + Frontend /"
echo "  ✓ Critical alerts:"
echo "    - Service downtime (> 5 min)"
echo "    - High error rate (> 10%)"
echo "    - Database connection issues"
echo "  ✓ Security metric: Failed login attempts (> 10/hour)"
echo "  ✓ Budget alert: \$100/month (email only)"
echo ""
echo "Alerts will be sent to:"
echo "  - Slack: (configured via webhook)"
echo "  - Email: nobu.fukumoto.99@gmail.com"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Check Slack channel for test notification"
echo "  2. Check email for budget alert confirmation"
echo "  3. Review GCP Console → Monitoring → Alerting"
echo "  4. See README.md for verification and troubleshooting"
echo ""
echo -e "${GREEN}Monitoring is now active! 🚀${NC}"
echo ""
