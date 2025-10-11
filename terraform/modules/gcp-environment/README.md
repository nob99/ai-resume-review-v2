# GCP Environment Terraform Module

This module creates a complete GCP environment (staging or production) with all required infrastructure.

## Resources Created

### Networking
- **VPC Network** - Private network for all resources
- **Subnet** - Regional subnet with custom CIDR
- **VPC Peering** - Private connection to Cloud SQL
- **VPC Connector** - Allows Cloud Run to access Cloud SQL privately

### Database
- **Cloud SQL PostgreSQL** - Managed database instance
- **Database** - Application database
- **Backups** - Automated daily backups with configurable retention

### Compute
- **Service Accounts** - Separate accounts for backend and frontend
- **IAM Bindings** - Least-privilege permissions

### Storage
- **Artifact Registry** - Docker image repository

### Secrets
- **Secret Manager References** - Links to existing secrets (does not create secret values)

## Usage

```hcl
module "staging_environment" {
  source = "../../modules/gcp-environment"

  # Required variables
  project_id  = "ytgrs-464303"
  region      = "us-central1"
  environment = "staging"

  # Networking
  vpc_name           = "ai-resume-review-v2-vpc"
  subnet_name        = "ai-resume-review-v2-subnet"
  subnet_cidr        = "10.0.0.0/24"
  vpc_connector_name = "ai-resume-connector-v2-staging"

  # Cloud SQL
  sql_instance_name         = "ai-resume-review-v2-db-staging"
  sql_tier                  = "db-f1-micro"
  sql_storage_size_gb       = 10
  sql_deletion_protection   = false
  database_name             = "ai_resume_review_staging"

  # Service Accounts
  backend_service_account_name  = "arr-v2-backend-staging"
  frontend_service_account_name = "arr-v2-frontend-staging"

  # Artifact Registry
  artifact_registry_name = "ai-resume-review-v2"

  # Secrets (must already exist in Secret Manager)
  secret_openai_key_name   = "openai-api-key-staging"
  secret_jwt_key_name      = "jwt-secret-key-staging"
  secret_db_password_name  = "db-password-staging"
}
```

## Variables

### Required Variables

| Variable | Type | Description |
|----------|------|-------------|
| `project_id` | string | GCP Project ID |
| `region` | string | GCP Region |
| `environment` | string | Environment name (staging/production) |
| `vpc_name` | string | VPC network name |
| `subnet_name` | string | Subnet name |
| `subnet_cidr` | string | Subnet CIDR range |
| `vpc_connector_name` | string | VPC Connector name |
| `sql_instance_name` | string | Cloud SQL instance name |
| `sql_tier` | string | Cloud SQL tier (e.g., db-f1-micro) |
| `sql_storage_size_gb` | number | Storage size in GB |
| `database_name` | string | Database name |
| `backend_service_account_name` | string | Backend service account ID |
| `frontend_service_account_name` | string | Frontend service account ID |
| `artifact_registry_name` | string | Artifact Registry repository name |
| `secret_openai_key_name` | string | OpenAI API key secret name |
| `secret_jwt_key_name` | string | JWT secret key name |
| `secret_db_password_name` | string | Database password secret name |

### Optional Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `vpc_connector_cidr` | string | "10.8.0.0/28" | VPC Connector CIDR |
| `vpc_connector_min_instances` | number | 2 | Min VPC Connector instances |
| `vpc_connector_max_instances` | number | 3 | Max VPC Connector instances |
| `sql_database_version` | string | "POSTGRES_15" | PostgreSQL version |
| `sql_storage_type` | string | "PD_SSD" | Storage type |
| `sql_availability_type` | string | "ZONAL" | Availability type |
| `sql_backup_enabled` | bool | true | Enable backups |
| `sql_backup_retention_days` | number | 7 | Backup retention days |
| `sql_deletion_protection` | bool | true | Deletion protection |

## Outputs

### Networking
- `vpc_name` - VPC network name
- `vpc_id` - VPC network ID
- `subnet_cidr` - Subnet CIDR range
- `vpc_connector_id` - VPC Connector ID

### Database
- `sql_instance_name` - Cloud SQL instance name
- `sql_connection_name` - Connection name (project:region:instance)
- `sql_private_ip` - Private IP address
- `database_name` - Database name

### Service Accounts
- `backend_service_account_email` - Backend SA email
- `frontend_service_account_email` - Frontend SA email

### Artifact Registry
- `artifact_registry_url` - Docker registry URL

### Summary
- `summary` - Complete summary of all resources

## Prerequisites

1. **GCP APIs must be enabled:**
   ```bash
   gcloud services enable compute.googleapis.com
   gcloud services enable servicenetworking.googleapis.com
   gcloud services enable sqladmin.googleapis.com
   gcloud services enable vpcaccess.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   ```

2. **Secrets must exist in Secret Manager:**
   ```bash
   # Create secrets first (values not shown)
   gcloud secrets create openai-api-key-staging --replication-policy=automatic
   gcloud secrets create jwt-secret-key-staging --replication-policy=automatic
   gcloud secrets create db-password-staging --replication-policy=automatic
   ```

3. **Sufficient GCP quotas:**
   - VPC networks: 1 per environment
   - Cloud SQL instances: 1 per environment
   - VPC Connectors: 1 per environment

## Important Notes

### Database Password
This module does NOT set the Cloud SQL postgres user password. After creating the instance, set it manually:

```bash
# Get password from Secret Manager
DB_PASS=$(gcloud secrets versions access latest --secret=db-password-staging)

# Set postgres password
gcloud sql users set-password postgres \
  --instance=ai-resume-review-v2-db-staging \
  --password="$DB_PASS"
```

### VPC Sharing
By default, staging and production share the same VPC network. This is common for small setups but can be changed by using different `vpc_name` values.

### Deletion Protection
- **Production:** `sql_deletion_protection = true` (prevents accidental deletion)
- **Staging:** `sql_deletion_protection = false` (allows cleanup)

### Cost Optimization
- VPC Connector: ~$10/month (always running)
- Cloud SQL db-f1-micro: ~$15/month
- Artifact Registry: Pay for storage (~$0.10/GB/month)

## See Also

- [Terraform Google Provider Docs](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Main Terraform README](../../README.md)
- [Environment Configuration](../../../config/README.md)
