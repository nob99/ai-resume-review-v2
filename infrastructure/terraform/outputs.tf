output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "app_service_account_email" {
  description = "Email of the application service account"
  value       = google_service_account.app_service_account.email
}

output "cloudsql_service_account_email" {
  description = "Email of the Cloud SQL service account"
  value       = google_service_account.cloudsql_service_account.email
}

output "artifact_registry_url" {
  description = "URL of the Artifact Registry repository"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}"
}

output "log_bucket_name" {
  description = "Name of the log storage bucket"
  value       = google_storage_bucket.log_bucket.name
}