# Setup Scripts - Phase 1 & 2

**Status**: ✅ **COMPLETED**

This folder contains infrastructure setup scripts that were already executed during Phase 1 & 2.

---

## 📋 What Was Created

These scripts created the following GCP resources:

✅ **Service Accounts**:
- `arr-v2-backend-prod@ytgrs-464303.iam.gserviceaccount.com`
- `arr-v2-frontend-prod@ytgrs-464303.iam.gserviceaccount.com`
- `arr-v2-github-actions@ytgrs-464303.iam.gserviceaccount.com`

✅ **VPC Network**:
- Network: `ai-resume-review-v2-vpc`
- Subnet: `ai-resume-review-v2-subnet` (10.0.0.0/24)

✅ **Cloud SQL Database**:
- Instance: `ai-resume-review-v2-db-prod`
- Type: PostgreSQL 15
- Tier: db-f1-micro
- Private IP only (no public access)

✅ **Secrets**:
- `openai-api-key-prod`
- `jwt-secret-key-prod`
- `db-password-prod`

✅ **Artifact Registry**:
- Repository: `ai-resume-review-v2`
- Location: us-central1

---

## 📜 Scripts in This Folder

### cleanup-old-resources.sh
**Purpose**: Delete old v1 resources before creating v2 infrastructure

**Status**: Already executed ✅

**What it did**:
- Removed old Cloud Run services
- Removed old Cloud SQL instances
- Removed old service accounts
- Removed old secrets

---

### setup-gcp-project.sh
**Purpose**: Create GCP project infrastructure

**Status**: Already executed ✅

**What it did**:
- Created service accounts
- Assigned IAM roles
- Created Artifact Registry
- Created VPC network

---

### setup-cloud-sql.sh
**Purpose**: Create Cloud SQL database instance

**Status**: Already executed ✅

**What it did**:
- Created Cloud SQL PostgreSQL instance
- Configured private IP
- Set up automated backups
- Created production database

---

### setup-secrets.sh
**Purpose**: Store secrets in Secret Manager

**Status**: Already executed ✅

**What it did**:
- Created secrets for OpenAI API key
- Created secrets for JWT signing key
- Created secrets for database password

---

## ⚠️ Important Notes

**DO NOT re-run these scripts unless**:
- You are setting up a new GCP project
- You want to reset the entire infrastructure
- A Cloud Engineer has instructed you to do so

**These scripts are idempotent** (safe to re-run), but re-running them is unnecessary since infrastructure already exists.

---

## ✅ Next Steps

Since setup is complete, proceed to deployment:

```bash
cd ../deploy/
./1-verify-prerequisites.sh
```

---

**For More Information**:
- [../README.md](../README.md) - Main deployment guide
- [../../../deployment/DEPLOYMENT_LOG.md](../../../deployment/DEPLOYMENT_LOG.md) - Execution log
- [../../../GCP_CLOUD_ARCHITECTURE.md](../../../GCP_CLOUD_ARCHITECTURE.md) - Architecture details
