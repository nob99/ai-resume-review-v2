#!/bin/bash

# Development Docker Management Script
# Manages all services (frontend, backend, database, redis)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source shared Docker utilities
source "$SCRIPT_DIR/../lib/docker.sh"

# Change to project root
cd "$PROJECT_ROOT"

case "$1" in
    up)
        print_status "Starting all services..."
        docker-compose -f docker-compose.dev.yml up -d
        print_info "Services are starting up..."
        sleep 5
        print_status "Services status:"
        docker-compose -f docker-compose.dev.yml ps
        print_info ""
        print_info "Access points:"
        print_info "  Frontend:  http://localhost:3000"
        print_info "  Backend:   http://localhost:8000"
        print_info "  PgAdmin:   http://localhost:8080"
        print_info "  PostgreSQL: localhost:5432"
        print_info "  Redis:     localhost:6379"
        ;;
    
    down)
        print_status "Stopping all services..."
        docker-compose -f docker-compose.dev.yml down
        ;;
    
    restart)
        print_status "Restarting all services..."
        docker-compose -f docker-compose.dev.yml restart
        ;;
    
    build)
        print_status "Building all services..."
        docker-compose -f docker-compose.dev.yml build
        ;;
    
    logs)
        if [ -z "$2" ]; then
            print_status "Showing logs for all services..."
            docker-compose -f docker-compose.dev.yml logs -f
        else
            print_status "Showing logs for $2..."
            docker-compose -f docker-compose.dev.yml logs -f "$2"
        fi
        ;;
    
    status)
        print_status "Services status:"
        docker-compose -f docker-compose.dev.yml ps
        ;;
    
    clean)
        print_warning "This will remove all containers and volumes!"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Cleaning up all services..."
            docker-compose -f docker-compose.dev.yml down -v
            print_status "Cleanup complete!"
        else
            print_info "Cleanup cancelled."
        fi
        ;;
    
    shell)
        if [ -z "$2" ]; then
            print_error "Please specify a service: frontend, backend, postgres, or redis"
            exit 1
        fi
        print_status "Opening shell in $2..."
        case "$2" in
            frontend)
                docker-compose -f docker-compose.dev.yml exec frontend sh
                ;;
            backend)
                docker-compose -f docker-compose.dev.yml exec backend bash
                ;;
            postgres)
                docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d ai_resume_review_dev
                ;;
            redis)
                docker-compose -f docker-compose.dev.yml exec redis redis-cli
                ;;
            *)
                print_error "Unknown service: $2"
                exit 1
                ;;
        esac
        ;;
    
    *)
        echo "Usage: $0 {up|down|restart|build|logs|status|clean|shell} [service]"
        echo ""
        echo "Commands:"
        echo "  up       - Start all services"
        echo "  down     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  build    - Build all service images"
        echo "  logs     - Show logs (optionally specify service)"
        echo "  status   - Show status of all services"
        echo "  clean    - Remove all containers and volumes"
        echo "  shell    - Open shell in a service (frontend|backend|postgres|redis)"
        echo ""
        echo "Examples:"
        echo "  $0 up              # Start all services"
        echo "  $0 logs backend    # Show backend logs"
        echo "  $0 shell frontend  # Open shell in frontend container"
        exit 1
        ;;
esac