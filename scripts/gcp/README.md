# GCP Deployment Scripts - AI Resume Review v2

This directory contains scripts for setting up and deploying the AI Resume Review v2 platform to Google Cloud Platform.

## 🎯 Quick Start Guide

### Step 1: Cleanup Old Resources (One-time)

Delete old `ai-resume` and `resume` named resources:

```bash
# Preview what will be deleted (safe)
./scripts/gcp/cleanup-old-resources.sh --dry-run

# Actually delete old resources
./scripts/gcp/cleanup-old-resources.sh
```

**What it deletes:**
- Cloud Run services: `ai-resume-backend`, `ai-resume-frontend`
- Cloud SQL instances: `ai-resume-db`, `resume-review-db`
- Service accounts: `ai-resume-*`, `resume-*`
- Artifact Registry: `ai-resume-review`
- VPC Network: `ai-resume-vpc`

### Step 2: Setup New Infrastructure

Create fresh v2 infrastructure:

```bash
# Preview what will be created (safe)
./scripts/gcp/setup-gcp-project.sh --dry-run

# Actually create resources
./scripts/gcp/setup-gcp-project.sh
```

**What it creates:**
- ✅ Service Accounts (shortened due to GCP 30-char limit):
  - `arr-v2-backend-prod@ytgrs-464303.iam.gserviceaccount.com`
  - `arr-v2-frontend-prod@ytgrs-464303.iam.gserviceaccount.com`
  - `arr-v2-github-actions@ytgrs-464303.iam.gserviceaccount.com`

- ✅ IAM Roles:
  - Backend: Cloud SQL Client, Secret Accessor, Log Writer
  - Frontend: Log Writer
  - GitHub Actions: Cloud Run Admin, Artifact Registry Writer, Service Account User

- ✅ Artifact Registry:
  - `us-central1-docker.pkg.dev/ytgrs-464303/ai-resume-review-v2`

- ✅ VPC Network:
  - Network: `ai-resume-review-v2-vpc`
  - Subnet: `ai-resume-review-v2-subnet` (10.0.0.0/24, us-central1)

### Step 3: Next Steps

After setup completes:

1. **Set up secrets**: Run `./scripts/gcp/setup-secrets.sh`
2. **Create Cloud SQL database**: Run `./scripts/gcp/setup-cloud-sql.sh`
3. **Deploy application**: Run `./scripts/gcp/deploy-to-production.sh`

## 📋 Script Reference

### cleanup-old-resources.sh

**Purpose**: Delete old infrastructure from previous deployments

**Usage**:
```bash
./scripts/gcp/cleanup-old-resources.sh [--dry-run]
```

**Options**:
- `--dry-run`: Preview deletions without actually deleting

**Features**:
- ✅ Dry-run mode for safety
- ✅ Confirmation prompts before each deletion
- ✅ Colored output (red for deletions)
- ✅ Safe error handling (continues even if resource already deleted)

---

### setup-gcp-project.sh

**Purpose**: Set up fresh GCP infrastructure for AI Resume Review v2

**Usage**:
```bash
./scripts/gcp/setup-gcp-project.sh [--dry-run]
```

**Options**:
- `--dry-run`: Preview what will be created without actually creating

**Features**:
- ✅ Idempotent (safe to run multiple times)
- ✅ Dry-run mode for testing
- ✅ Prerequisite checks (gcloud, billing, project)
- ✅ Validation after creation
- ✅ Detailed summary output

**Prerequisites**:
- gcloud CLI installed and authenticated
- Project: `ytgrs-464303`
- Billing enabled
- APIs already enabled (Cloud Run, Cloud SQL, Secret Manager, etc.)

---

## 🏗️ Architecture

### Resource Naming Convention (v2)

**Service Accounts** (shortened to "arr-v2-*" due to GCP 30-char limit):
- `arr-v2-backend-prod`
- `arr-v2-frontend-prod`
- `arr-v2-github-actions`

**Other Resources** (full naming):
- Cloud Run: `ai-resume-review-v2-backend-prod` (to be created later)
- Cloud SQL: `ai-resume-review-v2-db-prod` (to be created later)
- Artifact Registry: `ai-resume-review-v2`
- VPC: `ai-resume-review-v2-vpc`

### Project Configuration

- **Project ID**: `ytgrs-464303`
- **Project Number**: `864523342928`
- **Region**: `us-central1` (Iowa)
- **VPC Subnet CIDR**: `10.0.0.0/24`

### Budget & Billing

- **Monthly Budget**: $180 USD
- **Alert Thresholds**:
  - 50% ($90) → Email warning
  - 80% ($144) → Email urgent
  - 100% ($180) → Email critical

**Note**: Billing alerts must be set up manually via [GCP Console](https://console.cloud.google.com/billing/budgets)

---

## 🔐 Security

### Service Account Permissions

**Backend Service Account** (`arr-v2-backend-prod`):
- `roles/cloudsql.client` - Connect to Cloud SQL
- `roles/secretmanager.secretAccessor` - Read secrets
- `roles/logging.logWriter` - Write logs

**Frontend Service Account** (`arr-v2-frontend-prod`):
- `roles/logging.logWriter` - Write logs

**GitHub Actions Service Account** (`arr-v2-github-actions`):
- `roles/run.admin` - Deploy Cloud Run services
- `roles/iam.serviceAccountUser` - Use service accounts
- `roles/artifactregistry.writer` - Push Docker images
- `roles/cloudbuild.builds.editor` - Create Cloud Build jobs

### VPC Network

- **Network**: `ai-resume-review-v2-vpc` (custom mode)
- **Subnet**: `ai-resume-review-v2-subnet`
  - Region: `us-central1`
  - CIDR: `10.0.0.0/24`
  - Purpose: Private IP for Cloud SQL instances

---

## 🛠️ Troubleshooting

### Common Issues

**1. "Billing not enabled" error**
```bash
# Check billing status
gcloud beta billing projects describe ytgrs-464303

# If disabled, enable billing via:
# https://console.cloud.google.com/billing/enable?project=ytgrs-464303
```

**2. "Permission denied" error**
```bash
# Check your permissions
gcloud projects get-iam-policy ytgrs-464303 --filter="bindings.members:$(gcloud config get-value account)"

# You need at least:
# - roles/owner OR roles/editor
# - roles/iam.securityAdmin
```

**3. "Resource already exists" warning**
- This is normal if running setup multiple times
- Script will skip creating existing resources
- Check validation output to confirm resources exist

**4. Cleanup fails on resource deletion**
- Check if resource is still in use
- Check if you have permission to delete
- Some resources may already be deleted (script continues)

### Validation

After running setup, validate manually:

```bash
# Check service accounts
gcloud iam service-accounts list | grep "arr-v2"

# Check Artifact Registry
gcloud artifacts repositories list --location=us-central1

# Check VPC
gcloud compute networks list | grep "ai-resume-review-v2"
gcloud compute networks subnets list --network=ai-resume-review-v2-vpc

# Check IAM roles (example for backend SA)
gcloud projects get-iam-policy ytgrs-464303 \
  --flatten="bindings[].members" \
  --filter="bindings.members:arr-v2-backend-prod@ytgrs-464303.iam.gserviceaccount.com"
```

---

## 📚 Related Documentation

- [GCP Cloud Architecture](../../GCP_CLOUD_ARCHITECTURE.md) - Complete architecture design
- [Implementation Sequence](../../GCP_CLOUD_IMPLEMENTATION_SEQUENCE.md) - Step-by-step deployment guide
- [Deployment Configs](../../deployment/configs/) - Cloud Run configuration files

---

## 🎯 Design Principles

1. **Simple is Best**: Minimal, focused scripts that do one thing well
2. **Safety First**: Dry-run mode, confirmations, validation
3. **Idempotent**: Safe to run multiple times
4. **Best Practices**: Follow GCP recommendations for security and cost
5. **Clear Output**: Colored, structured output for easy understanding

---

**Last Updated**: 2025-10-06
**Maintained By**: Cloud Engineering Team
