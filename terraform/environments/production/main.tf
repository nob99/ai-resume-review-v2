# ============================================================================
# Production Environment - Main Configuration
# ============================================================================
# This creates the complete production environment using the gcp-environment module.
#
# Configuration is loaded from: ../../../config/environments.yml
#
# IMPORTANT: Production has enhanced settings:
#   - Deletion protection enabled on Cloud SQL
#   - Higher backup retention (7 days)
#   - Minimum 1 Cloud Run instance (keep warm)
#
# Usage:
#   terraform init
#   terraform plan
#   terraform apply

# ----------------------------------------------------------------------------
# Provider Configuration
# ----------------------------------------------------------------------------

provider "google" {
  project = var.project_id
  region  = var.region
}

# ----------------------------------------------------------------------------
# Load Configuration from YAML
# ----------------------------------------------------------------------------

locals {
  # Load environment configuration from centralized YAML file
  config = yamldecode(file("${path.module}/../../../config/environments.yml"))
  env    = local.config.production
  global = local.config.global
}

# ----------------------------------------------------------------------------
# Production Environment Module
# ----------------------------------------------------------------------------

module "production_environment" {
  source = "../../modules/gcp-environment"

  # Project & Environment
  project_id  = var.project_id
  region      = var.region
  environment = "production"

  # Networking
  vpc_name                      = local.env.network.vpc_name
  subnet_name                   = local.env.network.subnet_name
  subnet_cidr                   = local.env.network.subnet_cidr
  vpc_connector_name            = local.env.network.vpc_connector
  vpc_connector_cidr            = local.env.network.vpc_connector_cidr
  vpc_connector_min_instances   = local.env.network.vpc_connector_min_instances
  vpc_connector_max_instances   = local.env.network.vpc_connector_max_instances
  vpc_connector_machine_type    = local.env.network.vpc_connector_machine_type

  # Cloud SQL
  sql_instance_name         = local.env.database.instance_name
  sql_database_version      = local.env.database.version
  sql_tier                  = local.env.database.tier
  sql_storage_size_gb       = local.env.database.storage_size_gb
  sql_storage_type          = local.env.database.storage_type
  sql_availability_type     = local.env.database.availability_type
  sql_backup_enabled        = local.env.database.backup_enabled
  sql_backup_retention_days = local.env.database.backup_retention_days
  sql_backup_start_time     = local.env.database.backup_start_time
  sql_deletion_protection   = local.env.database.deletion_protection  # true for production
  database_name             = local.env.database.database_name

  # Service Accounts (extract account ID from full email)
  backend_service_account_name  = split("@", local.env.backend.service_account)[0]
  frontend_service_account_name = split("@", local.env.frontend.service_account)[0]

  # Artifact Registry
  artifact_registry_name = local.global.artifact_registry.repository

  # Secrets (must exist in Secret Manager before running terraform apply)
  secret_openai_key_name  = local.env.secrets.openai_api_key
  secret_jwt_key_name     = local.env.secrets.jwt_secret_key
  secret_db_password_name = local.env.secrets.db_password
}
