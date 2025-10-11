# ============================================================================
# Module Outputs
# ============================================================================

# ----------------------------------------------------------------------------
# Networking Outputs
# ----------------------------------------------------------------------------

output "vpc_name" {
  description = "VPC network name"
  value       = google_compute_network.vpc.name
}

output "vpc_id" {
  description = "VPC network ID"
  value       = google_compute_network.vpc.id
}

output "vpc_self_link" {
  description = "VPC network self link"
  value       = google_compute_network.vpc.self_link
}

output "subnet_name" {
  description = "Subnet name"
  value       = google_compute_subnetwork.subnet.name
}

output "subnet_cidr" {
  description = "Subnet CIDR range"
  value       = google_compute_subnetwork.subnet.ip_cidr_range
}

output "vpc_connector_id" {
  description = "VPC Connector ID"
  value       = google_vpc_access_connector.connector.id
}

output "vpc_connector_name" {
  description = "VPC Connector name"
  value       = google_vpc_access_connector.connector.name
}

# ----------------------------------------------------------------------------
# Cloud SQL Outputs
# ----------------------------------------------------------------------------

output "sql_instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.postgres.name
}

output "sql_connection_name" {
  description = "Cloud SQL connection name (project:region:instance)"
  value       = google_sql_database_instance.postgres.connection_name
}

output "sql_private_ip" {
  description = "Cloud SQL private IP address"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "sql_instance_self_link" {
  description = "Cloud SQL instance self link"
  value       = google_sql_database_instance.postgres.self_link
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.database.name
}

# ----------------------------------------------------------------------------
# Service Account Outputs
# ----------------------------------------------------------------------------

output "backend_service_account_email" {
  description = "Backend service account email"
  value       = google_service_account.backend.email
}

output "backend_service_account_id" {
  description = "Backend service account ID"
  value       = google_service_account.backend.account_id
}

output "frontend_service_account_email" {
  description = "Frontend service account email"
  value       = google_service_account.frontend.email
}

output "frontend_service_account_id" {
  description = "Frontend service account ID"
  value       = google_service_account.frontend.account_id
}

# ----------------------------------------------------------------------------
# Artifact Registry Outputs
# ----------------------------------------------------------------------------

output "artifact_registry_id" {
  description = "Artifact Registry repository ID"
  value       = google_artifact_registry_repository.docker.repository_id
}

output "artifact_registry_url" {
  description = "Artifact Registry URL for docker push/pull"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

# ----------------------------------------------------------------------------
# Secret Manager Outputs
# ----------------------------------------------------------------------------

output "secret_openai_key_id" {
  description = "OpenAI API key secret ID"
  value       = data.google_secret_manager_secret.openai_key.id
}

output "secret_jwt_key_id" {
  description = "JWT secret key ID"
  value       = data.google_secret_manager_secret.jwt_key.id
}

output "secret_db_password_id" {
  description = "Database password secret ID"
  value       = data.google_secret_manager_secret.db_password.id
}

# ----------------------------------------------------------------------------
# Summary Output (for convenience)
# ----------------------------------------------------------------------------

output "summary" {
  description = "Summary of created resources"
  value = {
    environment = var.environment
    project_id  = var.project_id
    region      = var.region

    networking = {
      vpc_name           = google_compute_network.vpc.name
      subnet_cidr        = google_compute_subnetwork.subnet.ip_cidr_range
      vpc_connector      = google_vpc_access_connector.connector.name
    }

    database = {
      instance_name    = google_sql_database_instance.postgres.name
      connection_name  = google_sql_database_instance.postgres.connection_name
      private_ip       = google_sql_database_instance.postgres.private_ip_address
      database_name    = google_sql_database.database.name
    }

    service_accounts = {
      backend_email  = google_service_account.backend.email
      frontend_email = google_service_account.frontend.email
    }

    artifact_registry = {
      repository_id = google_artifact_registry_repository.docker.repository_id
      url           = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
    }
  }
}
