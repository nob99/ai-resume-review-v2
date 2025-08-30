variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "billing_account_id" {
  description = "The billing account ID to associate with the project (optional if managed by infra team)"
  type        = string
  default     = null
}

variable "monthly_budget_amount" {
  description = "Monthly budget amount in USD"
  type        = string
  default     = "1000"
}

variable "budget_alert_email" {
  description = "Email address for budget alerts"
  type        = string
}

variable "kms_key_name" {
  description = "KMS key for encryption (optional)"
  type        = string
  default     = null
}

# Team member emails
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