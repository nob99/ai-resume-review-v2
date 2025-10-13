# Terraform Infrastructure

This directory contains Terraform configurations for managing GCP infrastructure as code.

## Status: ✅ Migration Complete

**Both staging and production environments are now fully managed by Terraform.**

| Environment | Status | Resources | Imported | Last Updated |
|-------------|--------|-----------|----------|--------------|
| **Staging** | ✅ Complete | 11 resources | Oct 13, 2025 | V5 |
| **Production** | ✅ Complete | 11 resources | Oct 13, 2025 | V6 |

**Achievements:**
- ✅ Zero downtime migration
- ✅ Drift detection enabled (`terraform plan`)
- ✅ Single source of truth established
- ✅ Both environments reproducible from code

**Documentation:**
- [HANDOVER_TERRAFORM_MIGRATION_V5.md](../archive/20251013/HANDOVER_TERRAFORM_MIGRATION_V5.md) - Staging import
- [HANDOVER_TERRAFORM_COMPLETE_V6.md](../archive/20251013/HANDOVER_TERRAFORM_COMPLETE_V6.md) - Production import & complete journey

---

## Overview

Our Terraform setup follows a **minimal, pragmatic approach** to avoid over-engineering:

- **Single module** (`modules/gcp-environment/`) - Creates complete environment
- **Two environments** (`environments/staging/`, `environments/production/`) - Separate state files
- **YAML-driven config** (`config/environments.yml`) - Single source of truth
- **~600 lines total** - Simple enough to understand, powerful enough to manage everything

## Directory Structure

```
terraform/
├── bootstrap/                   # One-time state bucket setup
│   ├── main.tf
│   └── README.md
│
├── modules/
│   └── gcp-environment/        # Single module for complete environment
│       ├── main.tf             # VPC, Cloud SQL, IAM, etc.
│       ├── variables.tf        # Input parameters
│       ├── outputs.tf          # Exported values
│       ├── versions.tf         # Provider requirements
│       └── README.md
│
└── environments/
    ├── staging/                # Staging environment
    │   ├── main.tf            # Uses gcp-environment module
    │   ├── backend.tf         # Remote state config
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── versions.tf
    │
    └── production/             # Production environment
        ├── main.tf            # Uses gcp-environment module
        ├── backend.tf         # Separate state file
        ├── variables.tf
        ├── outputs.tf
        └── versions.tf
```

## Prerequisites

### 1. Install Required Tools

```bash
# Terraform (>= 1.5.0)
brew install terraform
terraform version

# yq (YAML parser for bash scripts)
brew install yq
yq --version

# gcloud CLI (already installed)
gcloud auth login
gcloud config set project ytgrs-464303
```

### 2. Verify GCP Authentication

```bash
# Check current user
gcloud auth list

# Check project
gcloud config get-value project

# Should output: ytgrs-464303
```

### 3. Enable Required GCP APIs

```bash
gcloud services enable compute.googleapis.com
gcloud services enable servicenetworking.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable vpcaccess.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable storage-api.googleapis.com
```

## Quick Start

### Step 1: Bootstrap (One-Time Setup)

Create the GCS bucket for Terraform state storage:

```bash
cd terraform/bootstrap
terraform init
terraform plan
terraform apply

# Expected output: bucket created at gs://ytgrs-464303-terraform-state
```

### Step 2: Working with Existing Infrastructure

**Note:** Both staging and production have already been imported (Oct 13, 2025). You can start using Terraform immediately:

```bash
# Staging
cd terraform/environments/staging
terraform init
terraform plan  # Should show "No changes"

# Production
cd terraform/environments/production
terraform init
terraform plan  # Should show "No changes"
```

If you need to import new resources in the future, use the import scripts:
- [scripts/terraform/import-staging.sh](../scripts/terraform/import-staging.sh)
- [scripts/terraform/import-production.sh](../scripts/terraform/import-production.sh)

## What Terraform Manages

### ✅ Managed by Terraform

- **Networking:** VPC, subnets, VPC peering, VPC connectors
- **Database:** Cloud SQL instances, databases (not migrations!)
- **IAM:** Service accounts, IAM bindings
- **Storage:** Artifact Registry repositories
- **Secrets:** References to Secret Manager (not values!)

### ❌ NOT Managed by Terraform

- **Cloud Run Services** - Deployed via bash scripts / GitHub Actions (too dynamic)
- **Database Migrations** - Managed via SQL scripts in `database/migrations/`
- **Secret Values** - Set manually or via `scripts/gcp/setup/setup.sh`
- **Monitoring Dashboards** - Created via `scripts/gcp/monitoring/setup.sh`
- **Docker Images** - Built in GitHub Actions, pushed to Artifact Registry

## Common Operations

### View Current Infrastructure

```bash
cd terraform/environments/staging
terraform show
terraform output
```

### Make Infrastructure Changes

```bash
# 1. Edit config/environments.yml (change values)
# 2. Preview changes
terraform plan

# 3. Apply changes
terraform apply
```

### Destroy Environment (DANGEROUS!)

```bash
# Only use for staging cleanup
cd terraform/environments/staging
terraform destroy

# Production has deletion protection enabled
# Must manually disable before destroying
```

### Switch Between Environments

```bash
# Staging
cd terraform/environments/staging
terraform plan

# Production
cd terraform/environments/production
terraform plan
```

## Configuration Management

All configuration comes from **`config/environments.yml`**:

```yaml
staging:
  database:
    instance_name: ai-resume-review-v2-db-staging
    tier: db-f1-micro
    storage_size_gb: 10
```

**To change infrastructure:**
1. Edit `config/environments.yml`
2. Run `terraform plan` to preview
3. Run `terraform apply` to execute

## Integration with Bash Scripts

Bash scripts can load configuration from the same YAML file:

```bash
# Load staging config
source scripts/lib/load-config.sh staging

# Use exported variables
echo $SQL_INSTANCE_NAME
echo $BACKEND_SERVICE_NAME
```

## State Management

### State Storage

- **Backend:** Google Cloud Storage
- **Bucket:** `gs://ytgrs-464303-terraform-state`
- **Staging state:** `environments/staging/default.tfstate`
- **Production state:** `environments/production/default.tfstate`

### State Commands

```bash
# View state
terraform state list

# Show specific resource
terraform state show module.staging_environment.google_sql_database_instance.postgres

# Remove resource from state (doesn't delete resource)
terraform state rm module.staging_environment.google_compute_network.vpc
```

## Troubleshooting

### Error: "Resource already exists"

You need to import the existing resource:

```bash
terraform import <resource_address> <resource_id>
```

### Error: "Backend initialization required"

```bash
terraform init -reconfigure
```

### Error: "Secret not found"

Secrets must exist before running Terraform:

```bash
# Create secrets manually
gcloud secrets create openai-api-key-staging --replication-policy=automatic
```

### Error: "Permission denied"

Ensure your user has necessary IAM roles:

```bash
gcloud projects add-iam-policy-binding ytgrs-464303 \
  --member="user:$(gcloud config get-value account)" \
  --role="roles/editor"
```

## Best Practices

### 1. Always Run Plan First

```bash
terraform plan  # Preview changes
terraform apply # Only after reviewing plan
```

### 2. Test in Staging First

Never apply changes directly to production:

```bash
# 1. Test in staging
cd environments/staging
terraform apply

# 2. Verify it works
# 3. Then apply to production
cd ../production
terraform apply
```

### 3. Use Version Control

Commit changes to `config/environments.yml` before applying:

```bash
git add config/environments.yml
git commit -m "feat: increase Cloud SQL storage to 20GB"
git push
terraform apply
```

### 4. Review State Changes

```bash
# Before destroying resources
terraform state list

# Verify what will be deleted
terraform plan -destroy
```

## Cost Estimation

Run `terraform plan` to see estimated costs:

- VPC Network: Free
- Cloud SQL db-f1-micro: ~$15/month
- VPC Connector: ~$10/month
- Artifact Registry: ~$0.10/GB/month
- **Total:** ~$30-40/month per environment

## Migration Guide

### From Bash Scripts to Terraform

Current bash scripts in `scripts/gcp/setup/` will gradually be replaced:

1. ✅ **Phase 1:** Import existing resources into Terraform
2. ✅ **Phase 2:** Manage infrastructure changes via Terraform
3. ⏳ **Phase 3:** Deprecate infrastructure creation scripts (keep deployment scripts)

Deployment scripts remain bash-based:
- `scripts/gcp/deploy/deploy.sh` - Still used for migrations, Docker, Cloud Run

## See Also

- [Configuration Guide](../config/README.md) - Understanding environments.yml
- [Module Documentation](modules/gcp-environment/README.md) - Detailed module reference
- [Bootstrap Guide](bootstrap/README.md) - State bucket setup
- [GCP Deployment Scripts](../scripts/gcp/README.md) - Application deployment
