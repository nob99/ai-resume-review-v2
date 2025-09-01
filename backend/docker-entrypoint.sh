#!/bin/bash
# Docker entrypoint script for AI Resume Review Backend
# Handles database migration and proper startup sequencing

set -e

echo "Starting AI Resume Review Backend..."

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    while ! nc -z $DB_HOST $DB_PORT; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 1
    done
    echo "PostgreSQL is up and running on $DB_HOST:$DB_PORT"
}

# Function to wait for Redis
wait_for_redis() {
    echo "Waiting for Redis to be ready..."
    while ! nc -z $REDIS_HOST $REDIS_PORT; do
        echo "Redis is unavailable - sleeping"
        sleep 1
    done
    echo "Redis is up and running on $REDIS_HOST:$REDIS_PORT"
}

# Wait for services
wait_for_postgres
wait_for_redis

# Run database migrations if needed
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    cd /app/database && ./scripts/migrate.sh
    cd /app
fi

# Execute the main command
echo "Starting application..."
exec "$@"