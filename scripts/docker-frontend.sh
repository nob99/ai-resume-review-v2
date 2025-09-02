#!/bin/bash

# Frontend Docker Management Script
# Provides easy commands for managing the frontend container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[Frontend]${NC} $1"
}

print_error() {
    echo -e "${RED}[Error]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[Warning]${NC} $1"
}

# Change to project root
cd "$PROJECT_ROOT"

case "$1" in
    build)
        print_status "Building frontend container..."
        docker-compose -f docker-compose.dev.yml build frontend
        ;;
    
    start)
        print_status "Starting frontend container..."
        docker-compose -f docker-compose.dev.yml up -d frontend
        print_status "Frontend is running at http://localhost:3000"
        ;;
    
    stop)
        print_status "Stopping frontend container..."
        docker-compose -f docker-compose.dev.yml stop frontend
        ;;
    
    restart)
        print_status "Restarting frontend container..."
        docker-compose -f docker-compose.dev.yml restart frontend
        ;;
    
    logs)
        print_status "Showing frontend logs..."
        docker-compose -f docker-compose.dev.yml logs -f frontend
        ;;
    
    shell)
        print_status "Opening shell in frontend container..."
        docker-compose -f docker-compose.dev.yml exec frontend sh
        ;;
    
    status)
        print_status "Frontend container status:"
        docker-compose -f docker-compose.dev.yml ps frontend
        ;;
    
    clean)
        print_warning "Cleaning frontend container and volumes..."
        docker-compose -f docker-compose.dev.yml down frontend -v
        ;;
    
    test)
        print_status "Running frontend tests in container..."
        docker-compose -f docker-compose.dev.yml exec frontend npm test
        ;;
    
    lint)
        print_status "Running frontend linter in container..."
        docker-compose -f docker-compose.dev.yml exec frontend npm run lint
        ;;
    
    *)
        echo "Usage: $0 {build|start|stop|restart|logs|shell|status|clean|test|lint}"
        echo ""
        echo "Commands:"
        echo "  build    - Build the frontend Docker image"
        echo "  start    - Start the frontend container"
        echo "  stop     - Stop the frontend container"
        echo "  restart  - Restart the frontend container"
        echo "  logs     - Show frontend container logs"
        echo "  shell    - Open shell in frontend container"
        echo "  status   - Show frontend container status"
        echo "  clean    - Remove frontend container and volumes"
        echo "  test     - Run tests in frontend container"
        echo "  lint     - Run linter in frontend container"
        exit 1
        ;;
esac