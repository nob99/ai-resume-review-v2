#!/bin/bash

# Frontend Docker Management Script
# Provides easy commands for managing the frontend container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source shared Docker utilities
source "$SCRIPT_DIR/../lib/docker.sh"

# Override print_status to show [Frontend] prefix
print_status() {
    echo -e "${DOCKER_GREEN}[Frontend]${DOCKER_NC} $1"
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