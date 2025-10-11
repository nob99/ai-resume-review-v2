# ============================================================================
# Module Input Variables
# ============================================================================

# ----------------------------------------------------------------------------
# Project & Environment
# ----------------------------------------------------------------------------

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be staging or production"
  }
}

# ----------------------------------------------------------------------------
# Networking
# ----------------------------------------------------------------------------

variable "vpc_name" {
  description = "VPC network name"
  type        = string
}

variable "subnet_name" {
  description = "Subnet name"
  type        = string
}

variable "subnet_cidr" {
  description = "Subnet CIDR range"
  type        = string
}

variable "vpc_connector_name" {
  description = "VPC Connector name for Cloud Run"
  type        = string
}

variable "vpc_connector_cidr" {
  description = "CIDR range for VPC Connector (must be /28)"
  type        = string
  default     = "10.8.0.0/28"
}

variable "vpc_connector_min_instances" {
  description = "Minimum number of VPC Connector instances"
  type        = number
  default     = 2
}

variable "vpc_connector_max_instances" {
  description = "Maximum number of VPC Connector instances"
  type        = number
  default     = 3
}

variable "vpc_connector_machine_type" {
  description = "Machine type for VPC Connector"
  type        = string
  default     = "f1-micro"
}

# ----------------------------------------------------------------------------
# Cloud SQL
# ----------------------------------------------------------------------------

variable "sql_instance_name" {
  description = "Cloud SQL instance name"
  type        = string
}

variable "sql_database_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "sql_tier" {
  description = "Cloud SQL tier (e.g., db-f1-micro)"
  type        = string
}

variable "sql_storage_size_gb" {
  description = "Storage size in GB"
  type        = number
}

variable "sql_storage_type" {
  description = "Storage type (PD_SSD or PD_HDD)"
  type        = string
  default     = "PD_SSD"
}

variable "sql_availability_type" {
  description = "Availability type (ZONAL or REGIONAL)"
  type        = string
  default     = "ZONAL"
}

variable "sql_backup_enabled" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "sql_backup_retention_days" {
  description = "Backup retention in days"
  type        = number
  default     = 7
}

variable "sql_backup_start_time" {
  description = "Backup start time (HH:MM format)"
  type        = string
  default     = "02:00"
}

variable "sql_deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "database_name" {
  description = "Database name to create"
  type        = string
}

# ----------------------------------------------------------------------------
# Service Accounts
# ----------------------------------------------------------------------------

variable "backend_service_account_name" {
  description = "Backend service account ID (without @project.iam.gserviceaccount.com)"
  type        = string
}

variable "frontend_service_account_name" {
  description = "Frontend service account ID (without @project.iam.gserviceaccount.com)"
  type        = string
}

# ----------------------------------------------------------------------------
# Artifact Registry
# ----------------------------------------------------------------------------

variable "artifact_registry_name" {
  description = "Artifact Registry repository name"
  type        = string
}

# ----------------------------------------------------------------------------
# Secrets
# ----------------------------------------------------------------------------

variable "secret_openai_key_name" {
  description = "OpenAI API key secret name in Secret Manager"
  type        = string
}

variable "secret_jwt_key_name" {
  description = "JWT secret key name in Secret Manager"
  type        = string
}

variable "secret_db_password_name" {
  description = "Database password secret name in Secret Manager"
  type        = string
}
