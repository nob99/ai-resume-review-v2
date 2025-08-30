terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # backend "gcs" {
  #   # Backend configuration will be provided via backend config file
  #   # bucket = "ai-resume-review-terraform-state"
  #   # prefix = "terraform/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com"
  ])

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

# Create service accounts
resource "google_service_account" "app_service_account" {
  account_id   = "${var.environment}-app-sa"
  display_name = "Application Service Account for ${var.environment}"
  project      = var.project_id
}

resource "google_service_account" "cloudsql_service_account" {
  account_id   = "${var.environment}-cloudsql-sa"
  display_name = "Cloud SQL Service Account for ${var.environment}"
  project      = var.project_id
}

# Budget alert - Skipped (managed by Infra Team head)
# If needed later, can be configured by Infra Team with billing account access

# Notification channel for alerts
resource "google_monitoring_notification_channel" "team_alerts" {
  display_name = "Team Alert Email"
  type         = "email"
  project      = var.project_id

  labels = {
    email_address = var.budget_alert_email
  }
}

# Log sink for centralized logging
resource "google_logging_project_sink" "app_logs" {
  name        = "${var.environment}-app-logs-sink"
  destination = "storage.googleapis.com/${google_storage_bucket.log_bucket.name}"
  project     = var.project_id

  filter = "resource.type=\"cloud_run_revision\" OR resource.type=\"cloudsql_database\""

  unique_writer_identity = true
}

# Storage bucket for logs
resource "google_storage_bucket" "log_bucket" {
  name          = "${var.project_id}-${var.environment}-logs"
  location      = var.region
  project       = var.project_id
  force_destroy = false

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = var.kms_key_name
  }
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = "ai-resume-review-${var.environment}"
  description   = "Docker repository for AI Resume Review Platform ${var.environment}"
  format        = "DOCKER"
  project       = var.project_id

  cleanup_policies {
    id     = "keep-recent-versions"
    action = "KEEP"

    most_recent_versions {
      keep_count = 10
    }
  }
}

# Cloud SQL PostgreSQL instance
resource "google_sql_database_instance" "main" {
  name             = "ai-resume-review-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region
  project          = var.project_id

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 20
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      start_time                     = "02:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.vpc_network.id
      enable_private_path_for_google_cloud_services = true
    }

    database_flags {
      name  = "log_statement"
      value = "all"
    }

    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }

    database_flags {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements"
    }
  }

  deletion_protection = true

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.required_apis
  ]
}

# Create database
resource "google_sql_database" "app_database" {
  name     = "ai_resume_review"
  instance = google_sql_database_instance.main.name
  project  = var.project_id
}

# Create database user
resource "google_sql_user" "app_user" {
  name     = "app_user"
  instance = google_sql_database_instance.main.name
  password = var.db_password
  project  = var.project_id
}

# VPC Network for private database access
resource "google_compute_network" "vpc_network" {
  name                    = "ai-resume-review-vpc-${var.environment}"
  auto_create_subnetworks = false
  project                 = var.project_id
}

# Subnet for the VPC
resource "google_compute_subnetwork" "subnet" {
  name          = "ai-resume-review-subnet-${var.environment}"
  ip_cidr_range = "10.0.0.0/16"
  region        = var.region
  network       = google_compute_network.vpc_network.id
  project       = var.project_id
}

# Reserve IP range for private services
resource "google_compute_global_address" "private_ip_address" {
  name          = "private-ip-address-${var.environment}"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
  project       = var.project_id
}

# Create private connection
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# IAM configuration
module "iam" {
  source = "./modules/iam"

  project_id                     = var.project_id
  frontend_developer_email       = var.frontend_developer_email
  backend_developer_email        = var.backend_developer_email
  ai_ml_engineer_email           = var.ai_ml_engineer_email
  devops_engineer_email          = var.devops_engineer_email
  qa_engineer_email              = var.qa_engineer_email
  app_service_account_email      = google_service_account.app_service_account.email
  cloudsql_service_account_email = google_service_account.cloudsql_service_account.email
}