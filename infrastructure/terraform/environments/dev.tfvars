# Development environment configuration
project_id            = "ytgrs-464303"
region                = "us-central1"
environment           = "dev"
# billing_account_id managed by Infra Team head - skip billing setup
monthly_budget_amount = "500"
budget_alert_email    = "hiromu.ochiai@stellar-incubation.com"

# Database configuration
db_tier = "db-f1-micro"
# db_password should be set via environment variable TF_VAR_db_password