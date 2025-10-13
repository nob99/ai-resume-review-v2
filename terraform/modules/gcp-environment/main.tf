# ============================================================================
# GCP Environment Module - Complete Infrastructure
# ============================================================================
# This module creates ALL infrastructure for one environment (staging/prod):
#   - VPC Network + Subnets + VPC Peering
#   - Cloud SQL PostgreSQL Instance + Database
#   - VPC Connector (for Cloud Run → Cloud SQL)
#   - Service Accounts + IAM Bindings
#   - Artifact Registry
#   - Secret Manager References (not values!)
#
# Usage:
#   module "staging_environment" {
#     source = "../../modules/gcp-environment"
#     environment = "staging"
#     ...
#   }

# ----------------------------------------------------------------------------
# Networking - VPC
# ----------------------------------------------------------------------------

resource "google_compute_network" "vpc" {
  name                    = var.vpc_name
  auto_create_subnetworks = false
  project                 = var.project_id
}

resource "google_compute_subnetwork" "subnet" {
  name          = var.subnet_name
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id
  project       = var.project_id
}

# ----------------------------------------------------------------------------
# Networking - VPC Peering for Cloud SQL
# ----------------------------------------------------------------------------

# Allocate IP range for private services (Cloud SQL)
resource "google_compute_global_address" "private_ip" {
  name          = "google-managed-services-${var.vpc_name}"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
  project       = var.project_id
}

# Create VPC peering connection
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]
}

# ----------------------------------------------------------------------------
# Networking - VPC Connector (Cloud Run → Cloud SQL)
# ----------------------------------------------------------------------------

resource "google_vpc_access_connector" "connector" {
  name          = var.vpc_connector_name
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = var.vpc_connector_cidr
  project       = var.project_id

  # Use throughput-based configuration (matches actual GCP setup)
  # GCP uses either instances OR throughput, not both
  machine_type   = var.vpc_connector_machine_type
  min_throughput = 200  # Mbps
  max_throughput = 1000 # Mbps
}

# ----------------------------------------------------------------------------
# Cloud SQL - PostgreSQL Instance
# ----------------------------------------------------------------------------

resource "google_sql_database_instance" "postgres" {
  name             = var.sql_instance_name
  database_version = var.sql_database_version
  region           = var.region
  project          = var.project_id

  deletion_protection = var.sql_deletion_protection

  settings {
    tier              = var.sql_tier
    disk_size         = var.sql_storage_size_gb
    disk_type         = var.sql_storage_type
    disk_autoresize   = true
    availability_type = var.sql_availability_type

    # Private IP only (no public IP)
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }

    # Automated backups
    backup_configuration {
      enabled            = var.sql_backup_enabled
      start_time         = var.sql_backup_start_time
      backup_retention_settings {
        retained_backups = var.sql_backup_retention_days
      }
      # Transaction log retention for point-in-time recovery
      transaction_log_retention_days = var.sql_backup_retention_days
    }

    # Maintenance window (Sunday 2am)
    maintenance_window {
      day          = 7  # Sunday
      hour         = 2
      update_track = "stable"
    }

    # Additional settings for performance and security
    database_flags {
      name  = "max_connections"
      value = "100"
    }

    # Enable query insights for production debugging
    insights_config {
      query_insights_enabled  = true
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = true
    }
  }

  # Ensure VPC peering is created before SQL instance
  depends_on = [google_service_networking_connection.private_vpc_connection]
}

# ----------------------------------------------------------------------------
# Cloud SQL - Database
# ----------------------------------------------------------------------------

resource "google_sql_database" "database" {
  name     = var.database_name
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
}

# Note: Database password is managed via Secret Manager, not Terraform
# Set password manually using:
#   gcloud sql users set-password postgres \
#     --instance=<instance-name> \
#     --password=<password-from-secret-manager>

# ----------------------------------------------------------------------------
# Artifact Registry
# ----------------------------------------------------------------------------

resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.artifact_registry_name
  description   = "Docker images for ${var.environment} environment"
  format        = "DOCKER"
  project       = var.project_id

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ----------------------------------------------------------------------------
# Service Accounts
# ----------------------------------------------------------------------------

# Backend Service Account
resource "google_service_account" "backend" {
  account_id   = var.backend_service_account_name
  display_name = "Backend Cloud Run Service (${var.environment})"
  description  = "Service account for backend Cloud Run service in ${var.environment}"
  project      = var.project_id
}

# Frontend Service Account
resource "google_service_account" "frontend" {
  account_id   = var.frontend_service_account_name
  display_name = "Frontend Cloud Run Service (${var.environment})"
  description  = "Service account for frontend Cloud Run service in ${var.environment}"
  project      = var.project_id
}

# ----------------------------------------------------------------------------
# IAM Bindings - Backend Service Account
# ----------------------------------------------------------------------------

# Backend → Cloud SQL Client (connect to database)
resource "google_project_iam_member" "backend_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Backend → Secret Manager Accessor (read secrets)
resource "google_project_iam_member" "backend_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Backend → Logging Writer (write logs)
resource "google_project_iam_member" "backend_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# ----------------------------------------------------------------------------
# IAM Bindings - Frontend Service Account
# ----------------------------------------------------------------------------

# Frontend → Logging Writer (write logs)
resource "google_project_iam_member" "frontend_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.frontend.email}"
}

# ----------------------------------------------------------------------------
# Secret Manager - Data Sources (reference existing secrets)
# ----------------------------------------------------------------------------

# Note: Secrets must already exist in Secret Manager
# These are data sources (read-only) - Terraform does not create or manage secret values

data "google_secret_manager_secret" "openai_key" {
  secret_id = var.secret_openai_key_name
  project   = var.project_id
}

data "google_secret_manager_secret" "jwt_key" {
  secret_id = var.secret_jwt_key_name
  project   = var.project_id
}

data "google_secret_manager_secret" "db_password" {
  secret_id = var.secret_db_password_name
  project   = var.project_id
}

# ----------------------------------------------------------------------------
# Secret Manager - IAM Bindings
# ----------------------------------------------------------------------------

# Grant backend service account access to OpenAI API key
resource "google_secret_manager_secret_iam_member" "backend_openai" {
  secret_id = data.google_secret_manager_secret.openai_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
  project   = var.project_id
}

# Grant backend service account access to JWT secret
resource "google_secret_manager_secret_iam_member" "backend_jwt" {
  secret_id = data.google_secret_manager_secret.jwt_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
  project   = var.project_id
}

# Grant backend service account access to database password
resource "google_secret_manager_secret_iam_member" "backend_db_password" {
  secret_id = data.google_secret_manager_secret.db_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
  project   = var.project_id
}
