# ============================================================================
# Remote State Backend Configuration - Production Environment
# ============================================================================
# Stores Terraform state in Google Cloud Storage for team collaboration.
#
# Prerequisites:
#   1. Run terraform apply in ../../bootstrap/ first to create the bucket
#   2. Ensure you have access to the state bucket
#
# State file location:
#   gs://ytgrs-464303-terraform-state/environments/production/default.tfstate
#
# IMPORTANT: Production state is stored separately from staging for safety.

terraform {
  backend "gcs" {
    bucket = "ytgrs-464303-terraform-state"
    prefix = "environments/production"
  }
}
