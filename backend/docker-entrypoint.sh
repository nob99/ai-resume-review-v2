#!/bin/bash
# Docker entrypoint script for AI Resume Review Backend
# Handles both local development and Cloud Run production environments

set -e

echo "Starting AI Resume Review Backend..."
echo "Environment: ${ENVIRONMENT:-development}"

# Function to wait for PostgreSQL (handles both TCP and Unix socket)
wait_for_postgres() {
    # If DB_HOST is a unix socket path (Cloud SQL), skip network check
    if [[ "$DB_HOST" == /cloudsql/* ]]; then
        echo "✓ Using Cloud SQL Unix socket: $DB_HOST"
        echo "  (Skipping network connectivity check for socket connection)"
        return 0
    fi

    # Otherwise do network check for local PostgreSQL
    echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
    local max_attempts=30
    local attempt=0

    while ! nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo "ERROR: PostgreSQL not available after $max_attempts attempts"
            exit 1
        fi
        echo "  PostgreSQL is unavailable - attempt $attempt/$max_attempts"
        sleep 1
    done
    echo "✓ PostgreSQL is ready at $DB_HOST:$DB_PORT"
}

# Function to wait for Redis (optional - skip if not configured)
wait_for_redis() {
    # Skip if Redis host not set or explicitly disabled
    if [ -z "$REDIS_HOST" ] || [ "$REDIS_HOST" = "none" ] || [ "$REDIS_HOST" = "disabled" ]; then
        echo "✓ Redis not configured (skipping - rate limiting will be disabled)"
        return 0
    fi

    echo "Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
    local max_attempts=15
    local attempt=0

    while ! nc -z "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo "⚠ WARNING: Redis not available after $max_attempts attempts"
            echo "  Continuing without Redis (rate limiting will be disabled)"
            return 0
        fi
        echo "  Redis is unavailable - attempt $attempt/$max_attempts"
        sleep 1
    done
    echo "✓ Redis is ready at $REDIS_HOST:$REDIS_PORT"
}

# Wait for services
echo ""
echo "Checking service dependencies..."
wait_for_postgres
wait_for_redis
echo ""

# Execute the main command
echo "Starting FastAPI application..."
echo "Command: $@"
echo ""
exec "$@"
