# Terraform State Storage Bootstrap

This directory contains the **one-time setup** for Terraform state storage in Google Cloud Storage.

## Purpose

Creates a GCS bucket to store Terraform state files for all environments. This enables:
- **Remote state storage** - Team members can share state
- **State locking** - Prevents concurrent modifications
- **State versioning** - Keep history of infrastructure changes
- **Secure storage** - Encrypted and access-controlled

## Prerequisites

1. **gcloud CLI** installed and authenticated
   ```bash
   gcloud auth login
   gcloud config set project ytgrs-464303
   ```

2. **Terraform** installed
   ```bash
   brew install terraform
   terraform version  # Should be >= 1.5.0
   ```

3. **Permissions**
   - Your GCP user needs `Storage Admin` role
   - Or at minimum: `storage.buckets.create` permission

## Usage

### One-Time Setup (Run Once)

```bash
# Navigate to bootstrap directory
cd terraform/bootstrap

# Initialize Terraform (downloads providers)
terraform init

# Preview what will be created
terraform plan

# Create the state bucket
terraform apply
```

**Expected output:**
```
Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:

bucket_name = "ytgrs-464303-terraform-state"
bucket_url = "gs://ytgrs-464303-terraform-state"
backend_config = <<EOT

    Add this to your environment backend.tf files:

    terraform {
      backend "gcs" {
        bucket = "ytgrs-464303-terraform-state"
        prefix = "environments/<environment-name>"
      }
    }
    ...
EOT
```

### After Creation

1. **Verify the bucket exists:**
   ```bash
   gsutil ls -L gs://ytgrs-464303-terraform-state
   ```

2. **Grant access to your team members:**
   ```bash
   # Replace with actual email
   gsutil iam ch user:teammate@example.com:objectAdmin \
     gs://ytgrs-464303-terraform-state
   ```

3. **Clean up local state (optional):**
   ```bash
   # The bootstrap state is stored locally
   # You can safely delete it after bucket creation
   rm terraform.tfstate terraform.tfstate.backup
   ```

## What Gets Created

| Resource | Name | Purpose |
|----------|------|---------|
| **GCS Bucket** | `ytgrs-464303-terraform-state` | Stores all Terraform state files |
| **Versioning** | Enabled | Keeps 30 days of state history |
| **IAM Binding** | GitHub Actions SA | Allows CI/CD to read/write state |

## Security

- **Versioning enabled** - Recover from accidental state corruption
- **Force destroy disabled** - Prevents accidental bucket deletion
- **Uniform bucket-level access** - Modern IAM-only permissions
- **Lifecycle rules** - Auto-delete old state versions after 30 days

## State Organization

The bucket will contain state files organized by environment:

```
gs://ytgrs-464303-terraform-state/
├── environments/
│   ├── staging/
│   │   └── default.tfstate
│   └── production/
│       └── default.tfstate
└── (future environments)
```

## Troubleshooting

### Error: "Bucket already exists"

If the bucket already exists (from previous setup):

```bash
# Import existing bucket
terraform import google_storage_bucket.terraform_state ytgrs-464303-terraform-state

# Then run plan to verify
terraform plan
```

### Error: "Permission denied"

Ensure your GCP user has the necessary permissions:

```bash
# Check current user
gcloud auth list

# Check project
gcloud config get-value project

# Grant yourself Storage Admin (if you have project Owner/Editor role)
gcloud projects add-iam-policy-binding ytgrs-464303 \
  --member="user:$(gcloud config get-value account)" \
  --role="roles/storage.admin"
```

### Error: "API not enabled"

Enable required APIs:

```bash
gcloud services enable storage-api.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

## Next Steps

After the state bucket is created:

1. ✅ Proceed to [terraform/environments/staging/](../environments/staging/)
2. ✅ Initialize staging environment with remote state
3. ✅ Import existing GCP resources
4. ✅ Repeat for production environment

## See Also

- [Terraform GCS Backend Documentation](https://developer.hashicorp.com/terraform/language/settings/backends/gcs)
- [Main Terraform README](../README.md)
- [Environment Configuration](../../config/README.md)
