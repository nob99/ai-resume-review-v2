#!/bin/bash
# docker-common.sh - Shared utilities for Docker management scripts
#
# Usage: source this file at the beginning of your Docker scripts:
#   source "$(dirname "$0")/utils/docker-common.sh"

# Detect script directory and project root
DOCKER_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_PROJECT_ROOT="$(dirname "$DOCKER_SCRIPT_DIR")"

# Colors for output
export DOCKER_RED='\033[0;31m'
export DOCKER_GREEN='\033[0;32m'
export DOCKER_YELLOW='\033[1;33m'
export DOCKER_BLUE='\033[0;34m'
export DOCKER_NC='\033[0m' # No Color

# Docker Compose file path
export DOCKER_COMPOSE_FILE="docker-compose.dev.yml"

# ============================================================================
# Print Functions
# ============================================================================

# Print status message (green)
print_status() {
    echo -e "${DOCKER_GREEN}[Docker]${DOCKER_NC} $1"
}

# Print error message (red)
print_error() {
    echo -e "${DOCKER_RED}[Error]${DOCKER_NC} $1"
}

# Print warning message (yellow)
print_warning() {
    echo -e "${DOCKER_YELLOW}[Warning]${DOCKER_NC} $1"
}

# Print info message (blue)
print_info() {
    echo -e "${DOCKER_BLUE}[Info]${DOCKER_NC} $1"
}

# ============================================================================
# Docker Compose Helper Functions
# ============================================================================

# Run docker-compose command with the dev compose file
dc() {
    docker-compose -f "$DOCKER_COMPOSE_FILE" "$@"
}

# Check if Docker daemon is running
check_docker_running() {
    if ! docker ps &> /dev/null; then
        print_error "Docker daemon is not running"
        print_info "Please start Docker Desktop and try again"
        return 1
    fi
    return 0
}
