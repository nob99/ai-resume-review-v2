# ============================================================================
# Production Environment Outputs
# ============================================================================

# ----------------------------------------------------------------------------
# Pass-through Module Outputs
# ----------------------------------------------------------------------------

output "vpc_name" {
  description = "VPC network name"
  value       = module.production_environment.vpc_name
}

output "sql_instance_name" {
  description = "Cloud SQL instance name"
  value       = module.production_environment.sql_instance_name
}

output "sql_connection_name" {
  description = "Cloud SQL connection name (project:region:instance)"
  value       = module.production_environment.sql_connection_name
}

output "sql_private_ip" {
  description = "Cloud SQL private IP address"
  value       = module.production_environment.sql_private_ip
  sensitive   = true  # Mark as sensitive for production
}

output "backend_service_account_email" {
  description = "Backend service account email"
  value       = module.production_environment.backend_service_account_email
}

output "frontend_service_account_email" {
  description = "Frontend service account email"
  value       = module.production_environment.frontend_service_account_email
}

output "vpc_connector_id" {
  description = "VPC Connector ID"
  value       = module.production_environment.vpc_connector_id
}

output "artifact_registry_url" {
  description = "Artifact Registry URL"
  value       = module.production_environment.artifact_registry_url
}

# ----------------------------------------------------------------------------
# Environment Summary
# ----------------------------------------------------------------------------

output "summary" {
  description = "Complete summary of production environment"
  value       = module.production_environment.summary
}

# ----------------------------------------------------------------------------
# Deployment Information
# ----------------------------------------------------------------------------

output "deployment_info" {
  description = "Information for deployment scripts"
  value = {
    environment         = "production"
    sql_connection_name = module.production_environment.sql_connection_name
    vpc_connector       = module.production_environment.vpc_connector_name
    backend_sa          = module.production_environment.backend_service_account_email
    frontend_sa         = module.production_environment.frontend_service_account_email
    artifact_registry   = module.production_environment.artifact_registry_url
  }
}
