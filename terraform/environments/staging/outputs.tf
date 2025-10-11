# ============================================================================
# Staging Environment Outputs
# ============================================================================

# ----------------------------------------------------------------------------
# Pass-through Module Outputs
# ----------------------------------------------------------------------------

output "vpc_name" {
  description = "VPC network name"
  value       = module.staging_environment.vpc_name
}

output "sql_instance_name" {
  description = "Cloud SQL instance name"
  value       = module.staging_environment.sql_instance_name
}

output "sql_connection_name" {
  description = "Cloud SQL connection name (project:region:instance)"
  value       = module.staging_environment.sql_connection_name
}

output "sql_private_ip" {
  description = "Cloud SQL private IP address"
  value       = module.staging_environment.sql_private_ip
}

output "backend_service_account_email" {
  description = "Backend service account email"
  value       = module.staging_environment.backend_service_account_email
}

output "frontend_service_account_email" {
  description = "Frontend service account email"
  value       = module.staging_environment.frontend_service_account_email
}

output "vpc_connector_id" {
  description = "VPC Connector ID"
  value       = module.staging_environment.vpc_connector_id
}

output "artifact_registry_url" {
  description = "Artifact Registry URL"
  value       = module.staging_environment.artifact_registry_url
}

# ----------------------------------------------------------------------------
# Environment Summary
# ----------------------------------------------------------------------------

output "summary" {
  description = "Complete summary of staging environment"
  value       = module.staging_environment.summary
}

# ----------------------------------------------------------------------------
# Deployment Information
# ----------------------------------------------------------------------------

output "deployment_info" {
  description = "Information for deployment scripts"
  value = {
    environment         = "staging"
    sql_connection_name = module.staging_environment.sql_connection_name
    vpc_connector       = module.staging_environment.vpc_connector_name
    backend_sa          = module.staging_environment.backend_service_account_email
    frontend_sa         = module.staging_environment.frontend_service_account_email
    artifact_registry   = module.staging_environment.artifact_registry_url
  }
}
