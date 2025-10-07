#!/bin/bash
# Create Admin Users Script
# Creates 3 admin users in Cloud SQL production database via Cloud SQL Proxy

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ytgrs-464303"
REGION="us-central1"
INSTANCE_NAME="ai-resume-review-v2-db-prod"
SECRET_NAME="db-password-prod"
CONNECTION_NAME="$PROJECT_ID:$REGION:$INSTANCE_NAME"
PROXY_PORT="5432"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Cloud SQL Proxy binary
PROXY_BINARY="$SCRIPT_DIR/deploy/cloud-sql-proxy"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Create Admin Users${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"

    # Check if Cloud SQL Proxy exists
    if [ ! -f "$PROXY_BINARY" ]; then
        echo -e "${RED}✗ Cloud SQL Proxy not found at: $PROXY_BINARY${NC}"
        echo -e "${YELLOW}Please run the migration script first to download it${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Cloud SQL Proxy found${NC}"

    # Check if Python script exists
    if [ ! -f "$SCRIPT_DIR/create_admin_user.py" ]; then
        echo -e "${RED}✗ Python script not found: create_admin_user.py${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python script found${NC}"

    # Check if python3 is available
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ python3 not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ python3 installed${NC}"

    # Check if gcloud is available
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}✗ gcloud CLI not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ gcloud CLI installed${NC}"

    echo ""
}

# Get database password from Secret Manager
get_db_password() {
    echo -e "${BLUE}Retrieving database password from Secret Manager...${NC}"
    DB_PASSWORD=$(gcloud secrets versions access latest \
        --secret="$SECRET_NAME" \
        --project="$PROJECT_ID" 2>/dev/null)

    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${RED}✗ Failed to retrieve database password${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Database password retrieved${NC}"
    echo ""
}

# Start Cloud SQL Proxy
start_proxy() {
    echo -e "${BLUE}Starting Cloud SQL Proxy...${NC}"
    echo -e "${BLUE}Connection: $CONNECTION_NAME${NC}"
    echo -e "${BLUE}Port: $PROXY_PORT${NC}"

    # Check if proxy is already running
    if lsof -Pi :$PROXY_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Port $PROXY_PORT already in use${NC}"
        echo -e "${YELLOW}Stopping existing process...${NC}"
        kill $(lsof -t -i:$PROXY_PORT) 2>/dev/null || true
        sleep 2
    fi

    # Start proxy in background
    "$PROXY_BINARY" \
        --address 0.0.0.0 \
        --port $PROXY_PORT \
        "$CONNECTION_NAME" > /tmp/cloud-sql-proxy.log 2>&1 &

    PROXY_PID=$!
    echo -e "${BLUE}Proxy PID: $PROXY_PID${NC}"

    # Wait for proxy to be ready
    echo -e "${BLUE}Waiting for proxy to be ready...${NC}"
    sleep 5

    if ! kill -0 $PROXY_PID 2>/dev/null; then
        echo -e "${RED}✗ Cloud SQL Proxy failed to start${NC}"
        cat /tmp/cloud-sql-proxy.log
        exit 1
    fi

    echo -e "${GREEN}✓ Cloud SQL Proxy running (PID: $PROXY_PID)${NC}"
    echo ""
}

# Stop Cloud SQL Proxy
stop_proxy() {
    if [ ! -z "$PROXY_PID" ]; then
        echo -e "${BLUE}Stopping Cloud SQL Proxy (PID: $PROXY_PID)...${NC}"
        kill $PROXY_PID 2>/dev/null || true
        wait $PROXY_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Proxy stopped${NC}"
    fi
}

# Cleanup on exit
cleanup() {
    echo ""
    echo -e "${BLUE}Cleaning up...${NC}"
    stop_proxy
}
trap cleanup EXIT

# Run Python script to create admin users
create_admin_users() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}Running Admin User Creation Script${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""

    cd "$PROJECT_ROOT"

    # Export database password for Python script
    export DB_PASSWORD="$DB_PASSWORD"

    # Run Python script
    if python3 "$SCRIPT_DIR/create_admin_user.py"; then
        echo -e "${GREEN}✓ Admin users created successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Admin user creation failed${NC}"
        return 1
    fi
}

# Main execution
main() {
    check_prerequisites
    get_db_password
    start_proxy

    if ! create_admin_users; then
        echo -e "${RED}Admin user creation failed!${NC}"
        exit 1
    fi

    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${GREEN}✓ Admin User Creation Complete!${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}IMPORTANT SECURITY NOTES:${NC}"
    echo -e "${YELLOW}1. Save the admin credentials displayed above${NC}"
    echo -e "${YELLOW}2. Store them in a secure password manager${NC}"
    echo -e "${YELLOW}3. Consider changing passwords after first login${NC}"
    echo -e "${YELLOW}4. These credentials grant full system access${NC}"
    echo ""
}

# Run main function
main
