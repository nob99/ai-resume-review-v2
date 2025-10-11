#!/bin/bash
# ============================================================================
# Load Environment Configuration from YAML
# ============================================================================
# This script loads environment configuration from config/environments.yml
# and exports variables for use in bash scripts.
#
# Usage:
#   source scripts/lib/load-config.sh <environment>
#
# Example:
#   source scripts/lib/load-config.sh staging
#   echo $BACKEND_SERVICE_NAME
#   echo $SQL_INSTANCE_NAME
#
# Arguments:
#   $1 - Environment name (staging or production)
#
# Requirements:
#   - yq (YAML parser): brew install yq
#
# Exported Variables:
#   Global:
#     PROJECT_ID, REGION, ZONE, ARTIFACT_REGISTRY
#
#   Environment-specific:
#     BACKEND_SERVICE_NAME, FRONTEND_SERVICE_NAME
#     BACKEND_SERVICE_ACCOUNT, FRONTEND_SERVICE_ACCOUNT
#     SQL_INSTANCE_NAME, SQL_CONNECTION_NAME, DB_NAME, DB_USER
#     VPC_NAME, VPC_CONNECTOR
#     SECRET_OPENAI_KEY, SECRET_JWT_KEY, SECRET_DB_PASSWORD

set -e

# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------

# Check environment argument
if [ -z "$1" ]; then
    echo "ERROR: Environment not specified"
    echo "Usage: source scripts/lib/load-config.sh <environment>"
    echo "Example: source scripts/lib/load-config.sh staging"
    return 1 2>/dev/null || exit 1
fi

ENV=$1

# Validate environment name
if [ "$ENV" != "staging" ] && [ "$ENV" != "production" ]; then
    echo "ERROR: Invalid environment: $ENV"
    echo "Valid environments: staging, production"
    return 1 2>/dev/null || exit 1
fi

# Find project root (assumes this script is in scripts/lib/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/config/environments.yml"

# Check config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Config file not found: $CONFIG_FILE"
    return 1 2>/dev/null || exit 1
fi

# Check yq is installed
if ! command -v yq &> /dev/null; then
    echo "ERROR: yq is not installed"
    echo "Install with: brew install yq"
    echo ""
    echo "yq is a YAML parser required to read config/environments.yml"
    return 1 2>/dev/null || exit 1
fi

# ----------------------------------------------------------------------------
# Load Configuration
# ----------------------------------------------------------------------------

# Export global settings
export PROJECT_ID=$(yq ".global.project_id" "$CONFIG_FILE")
export REGION=$(yq ".global.region" "$CONFIG_FILE")
export ZONE=$(yq ".global.zone" "$CONFIG_FILE")

# Export environment-specific settings - Backend
export BACKEND_SERVICE_NAME=$(yq ".$ENV.backend.name" "$CONFIG_FILE")
export BACKEND_SERVICE_ACCOUNT=$(yq ".$ENV.backend.service_account" "$CONFIG_FILE")
export BACKEND_MEMORY=$(yq ".$ENV.backend.memory" "$CONFIG_FILE")
export BACKEND_CPU=$(yq ".$ENV.backend.cpu" "$CONFIG_FILE")
export BACKEND_MIN_INSTANCES=$(yq ".$ENV.backend.min_instances" "$CONFIG_FILE")
export BACKEND_MAX_INSTANCES=$(yq ".$ENV.backend.max_instances" "$CONFIG_FILE")

# Export environment-specific settings - Frontend
export FRONTEND_SERVICE_NAME=$(yq ".$ENV.frontend.name" "$CONFIG_FILE")
export FRONTEND_SERVICE_ACCOUNT=$(yq ".$ENV.frontend.service_account" "$CONFIG_FILE")
export FRONTEND_MEMORY=$(yq ".$ENV.frontend.memory" "$CONFIG_FILE")
export FRONTEND_CPU=$(yq ".$ENV.frontend.cpu" "$CONFIG_FILE")
export FRONTEND_MIN_INSTANCES=$(yq ".$ENV.frontend.min_instances" "$CONFIG_FILE")
export FRONTEND_MAX_INSTANCES=$(yq ".$ENV.frontend.max_instances" "$CONFIG_FILE")

# Export environment-specific settings - Database
export SQL_INSTANCE_NAME=$(yq ".$ENV.database.instance_name" "$CONFIG_FILE")
export DB_NAME=$(yq ".$ENV.database.database_name" "$CONFIG_FILE")
export DB_USER=$(yq ".$ENV.database.user" "$CONFIG_FILE")
export DB_VERSION=$(yq ".$ENV.database.version" "$CONFIG_FILE")
export DB_TIER=$(yq ".$ENV.database.tier" "$CONFIG_FILE")

# Export environment-specific settings - Networking
export VPC_NAME=$(yq ".$ENV.network.vpc_name" "$CONFIG_FILE")
export VPC_SUBNET=$(yq ".$ENV.network.subnet_name" "$CONFIG_FILE")
export VPC_CONNECTOR=$(yq ".$ENV.network.vpc_connector" "$CONFIG_FILE")

# Export environment-specific settings - Secrets
export SECRET_OPENAI_KEY=$(yq ".$ENV.secrets.openai_api_key" "$CONFIG_FILE")
export SECRET_JWT_KEY=$(yq ".$ENV.secrets.jwt_secret_key" "$CONFIG_FILE")
export SECRET_DB_PASSWORD=$(yq ".$ENV.secrets.db_password" "$CONFIG_FILE")

# Derived values
export SQL_CONNECTION_NAME="$PROJECT_ID:$REGION:$SQL_INSTANCE_NAME"
export ARTIFACT_REGISTRY=$(yq '.global.artifact_registry.url' "$CONFIG_FILE")

# ----------------------------------------------------------------------------
# Confirmation
# ----------------------------------------------------------------------------

echo "✓ Loaded $ENV configuration from $CONFIG_FILE"
echo ""
echo "Environment: $ENV"
echo "Project ID:  $PROJECT_ID"
echo "Region:      $REGION"
echo "Backend:     $BACKEND_SERVICE_NAME"
echo "Frontend:    $FRONTEND_SERVICE_NAME"
echo "Database:    $SQL_INSTANCE_NAME"
echo ""
