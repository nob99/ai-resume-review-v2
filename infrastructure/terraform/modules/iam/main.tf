# IAM roles and permissions for team members

locals {
  # Define standard roles for different team members
  developer_roles = [
    "roles/viewer",
    "roles/cloudsql.client",
    "roles/run.developer",
    "roles/secretmanager.secretAccessor",
    "roles/logging.viewer",
    "roles/monitoring.viewer"
  ]

  devops_roles = [
    "roles/editor",
    "roles/resourcemanager.projectIamAdmin",
    "roles/iam.serviceAccountAdmin",
    "roles/run.admin",
    "roles/cloudsql.admin",
    "roles/secretmanager.admin",
    "roles/logging.admin",
    "roles/monitoring.admin"
  ]

  qa_roles = [
    "roles/viewer",
    "roles/run.invoker",
    "roles/logging.viewer",
    "roles/monitoring.viewer"
  ]
}

# Frontend Developer
resource "google_project_iam_member" "frontend_developer" {
  for_each = var.frontend_developer_email != "" ? toset(local.developer_roles) : []

  project = var.project_id
  role    = each.value
  member  = "user:${var.frontend_developer_email}"
}

# Backend Developer
resource "google_project_iam_member" "backend_developer" {
  for_each = var.backend_developer_email != "" ? toset(local.developer_roles) : []

  project = var.project_id
  role    = each.value
  member  = "user:${var.backend_developer_email}"
}

# AI/ML Engineer
resource "google_project_iam_member" "ai_ml_engineer" {
  for_each = var.ai_ml_engineer_email != "" ? toset(local.developer_roles) : []

  project = var.project_id
  role    = each.value
  member  = "user:${var.ai_ml_engineer_email}"
}

# DevOps Engineer
resource "google_project_iam_member" "devops_engineer" {
  for_each = var.devops_engineer_email != "" ? toset(local.devops_roles) : []

  project = var.project_id
  role    = each.value
  member  = "user:${var.devops_engineer_email}"
}

# QA Engineer
resource "google_project_iam_member" "qa_engineer" {
  for_each = var.qa_engineer_email != "" ? toset(local.qa_roles) : []

  project = var.project_id
  role    = each.value
  member  = "user:${var.qa_engineer_email}"
}

# Service account IAM bindings
resource "google_project_iam_member" "app_sa_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${var.app_service_account_email}"
}

resource "google_project_iam_member" "cloudsql_sa_roles" {
  for_each = toset([
    "roles/cloudsql.editor",
    "roles/logging.logWriter"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${var.cloudsql_service_account_email}"
}