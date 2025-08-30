variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "frontend_developer_email" {
  description = "Email of the frontend developer"
  type        = string
  default     = ""
}

variable "backend_developer_email" {
  description = "Email of the backend developer"
  type        = string
  default     = ""
}

variable "ai_ml_engineer_email" {
  description = "Email of the AI/ML engineer"
  type        = string
  default     = ""
}

variable "devops_engineer_email" {
  description = "Email of the DevOps engineer"
  type        = string
  default     = ""
}

variable "qa_engineer_email" {
  description = "Email of the QA engineer"
  type        = string
  default     = ""
}

variable "app_service_account_email" {
  description = "Email of the application service account"
  type        = string
}

variable "cloudsql_service_account_email" {
  description = "Email of the Cloud SQL service account"
  type        = string
}