# ============================================================================
# Production Environment Variables
# ============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "ytgrs-464303"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}
