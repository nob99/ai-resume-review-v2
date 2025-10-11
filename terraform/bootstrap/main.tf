# ============================================================================
# Terraform State Storage - Bootstrap
# ============================================================================
# This creates the GCS bucket for storing Terraform state files.
#
# IMPORTANT: This is a one-time setup and uses LOCAL state.
# After creating the bucket, all other Terraform configurations will use
# remote state stored in this bucket.
#
# Usage:
#   cd terraform/bootstrap
#   terraform init
#   terraform plan
#   terraform apply
#
# After this runs successfully, you can safely delete the local state file:
#   rm terraform.tfstate terraform.tfstate.backup

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Bootstrap uses LOCAL state (no remote backend yet)
  # After the bucket is created, other environments will use remote state
}

# ----------------------------------------------------------------------------
# Variables
# ----------------------------------------------------------------------------

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "ytgrs-464303"
}

variable "region" {
  description = "GCP Region for the bucket"
  type        = string
  default     = "us-central1"
}

variable "bucket_name" {
  description = "Name of the GCS bucket for Terraform state"
  type        = string
  default     = "ytgrs-464303-terraform-state"
}

# ----------------------------------------------------------------------------
# Provider Configuration
# ----------------------------------------------------------------------------

provider "google" {
  project = var.project_id
  region  = var.region
}

# ----------------------------------------------------------------------------
# GCS Bucket for Terraform State
# ----------------------------------------------------------------------------

resource "google_storage_bucket" "terraform_state" {
  name     = var.bucket_name
  location = var.region
  project  = var.project_id

  # Prevent accidental deletion of state bucket
  force_destroy = false

  # Enable versioning to maintain state history
  versioning {
    enabled = true
  }

  # Lifecycle management
  lifecycle_rule {
    # Keep state file versions for 30 days
    condition {
      age = 30
      with_state = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  # Uniform bucket-level access (recommended for security)
  uniform_bucket_level_access = true

  # Encryption (Google-managed by default)
  # For customer-managed encryption, add:
  # encryption {
  #   default_kms_key_name = "projects/${var.project_id}/locations/${var.region}/keyRings/terraform/cryptoKeys/state"
  # }

  # Labels for organization
  labels = {
    managed_by  = "terraform"
    purpose     = "terraform-state"
    environment = "all"
  }
}

# ----------------------------------------------------------------------------
# IAM Permissions
# ----------------------------------------------------------------------------

# Grant GitHub Actions service account access to the state bucket
resource "google_storage_bucket_iam_member" "github_actions_admin" {
  bucket = google_storage_bucket.terraform_state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:github-actions-deployer@${var.project_id}.iam.gserviceaccount.com"
}

# Grant your own user account access (for local development)
# Replace with your actual GCP user email
# Uncomment and update after first run:
# resource "google_storage_bucket_iam_member" "developer_admin" {
#   bucket = google_storage_bucket.terraform_state.name
#   role   = "roles/storage.objectAdmin"
#   member = "user:your-email@example.com"
# }

# ----------------------------------------------------------------------------
# Outputs
# ----------------------------------------------------------------------------

output "bucket_name" {
  description = "Name of the Terraform state bucket"
  value       = google_storage_bucket.terraform_state.name
}

output "bucket_url" {
  description = "GCS URL of the Terraform state bucket"
  value       = google_storage_bucket.terraform_state.url
}

output "backend_config" {
  description = "Backend configuration for other Terraform environments"
  value = <<-EOT

    Add this to your environment backend.tf files:

    terraform {
      backend "gcs" {
        bucket = "${google_storage_bucket.terraform_state.name}"
        prefix = "environments/<environment-name>"
      }
    }

    Example for staging:
      prefix = "environments/staging"

    Example for production:
      prefix = "environments/production"
  EOT
}
