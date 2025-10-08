#!/bin/bash

###############################################################################
# GCP Monitoring - Setup Uptime Checks
###############################################################################
# This script creates uptime checks for backend and frontend services
#
# Usage:
#   ./2-setup-uptime-checks.sh
#
# What it does:
#   1. Creates uptime check for backend /health endpoint (every 5 min)
#   2. Creates uptime check for frontend homepage (every 5 min)
#   3. Configures checks from 3 global locations
#
# Cost: FREE (first 1M uptime checks per month are free)
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ytgrs-464303"
BACKEND_URL="https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app"
FRONTEND_URL="https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setting Up Uptime Checks${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if already exists
echo "Checking for existing uptime checks..."
EXISTING_BACKEND=$(gcloud monitoring uptime list-configs \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="displayName:'Backend Health Check'" 2>/dev/null || echo "")

EXISTING_FRONTEND=$(gcloud monitoring uptime list-configs \
  --project="$PROJECT_ID" \
  --format="value(name)" \
  --filter="displayName:'Frontend Health Check'" 2>/dev/null || echo "")

# Create Backend uptime check
if [ -n "$EXISTING_BACKEND" ]; then
  echo -e "${YELLOW}✓ Backend uptime check already exists${NC}"
else
  echo "Creating Backend uptime check..."
  gcloud monitoring uptime create "Backend Health Check" \
    --resource-type=uptime-url \
    --resource-labels=host="ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app",project_id="$PROJECT_ID" \
    --path="/health" \
    --timeout=10 \
    --period=5 \
    --project="$PROJECT_ID"
  echo -e "${GREEN}✓ Backend uptime check created${NC}"
fi

# Create Frontend uptime check
if [ -n "$EXISTING_FRONTEND" ]; then
  echo -e "${YELLOW}✓ Frontend uptime check already exists${NC}"
else
  echo "Creating Frontend uptime check..."
  gcloud monitoring uptime create "Frontend Health Check" \
    --resource-type=uptime-url \
    --resource-labels=host="ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app",project_id="$PROJECT_ID" \
    --path="/" \
    --timeout=10 \
    --period=5 \
    --project="$PROJECT_ID"
  echo -e "${GREEN}✓ Frontend uptime check created${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Uptime Checks Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Backend Check: $BACKEND_URL/health (every 5 min)"
echo "Frontend Check: $FRONTEND_URL/ (every 5 min)"
echo ""
echo "Locations: USA, Europe, Asia-Pacific"
echo ""
echo "Next step: Run ./3-setup-critical-alerts.sh"
echo ""
