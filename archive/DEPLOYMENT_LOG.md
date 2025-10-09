# GCP Deployment Log

This file tracks manual deployment actions performed on the GCP infrastructure.

## 2025-10-06: Phase 1 - Initial Setup Complete

### Actions Performed

#### 1. Cleanup of Old Resources
**Date**: 2025-10-06
**Executed by**: Cloud Engineering Team

**Deleted Cloud Run Services:**
- `ai-resume-frontend` (us-central1) - Old frontend deployment

**Deleted Cloud SQL Instances:**
- `resume-review-db` (us-central1) - Old database with private IP
- `ai-resume-db` (us-central1) - Old database with public IP (insecure)
  - Note: Had deletion protection enabled, disabled before deletion

**Deleted Service Accounts:**
- `ai-resume-frontend@ytgrs-464303.iam.gserviceaccount.com`
- `resume-frontend@ytgrs-464303.iam.gserviceaccount.com`

**Deleted VPC Resources:**
- `ai-resume-subnet` (us-central1 subnet)

**Deleted Secrets from Secret Manager (8 total):**
- `OPENAI_API_KEY` (duplicate, old naming)
- `SECRET_KEY` (generic old secret)
- `database-password` (old database credential)
- `database-url` (old connection string)
- `jwt-secret` (duplicate, old naming)
- `jwt-secret-key` (old JWT secret)
- `nextauth-secret` (old NextAuth secret)
- `openai-api-key` (duplicate, old naming)

**Reason**: Clean slate for v2 deployment. Old resources used inconsistent naming and some had security issues (public IPs).

---

#### 2. Created v2 Infrastructure
**Date**: 2025-10-06
**Script**: `scripts/gcp/setup/setup-gcp-project.sh`
**Executed by**: Automated script

**Created Service Accounts:**
- `arr-v2-backend-prod@ytgrs-464303.iam.gserviceaccount.com`
  - Purpose: Backend Cloud Run service identity
  - Roles: `cloudsql.client`, `secretmanager.secretAccessor`, `logging.logWriter`

- `arr-v2-frontend-prod@ytgrs-464303.iam.gserviceaccount.com`
  - Purpose: Frontend Cloud Run service identity
  - Roles: `logging.logWriter`

- `arr-v2-github-actions@ytgrs-464303.iam.gserviceaccount.com`
  - Purpose: CI/CD deployment via GitHub Actions
  - Roles: `run.admin`, `iam.serviceAccountUser`, `artifactregistry.writer`, `cloudbuild.builds.editor`

**Note**: Service account names shortened to "arr-v2-*" due to GCP 30-character limit.

**Created Artifact Registry:**
- Repository: `ai-resume-review-v2`
- Location: `us-central1`
- Format: Docker
- URL: `us-central1-docker.pkg.dev/ytgrs-464303/ai-resume-review-v2`

**Created VPC Network:**
- Network: `ai-resume-review-v2-vpc`
- Mode: Custom
- Subnet: `ai-resume-review-v2-subnet`
  - Region: `us-central1`
  - CIDR: `10.0.0.0/24`
  - Purpose: Private IP connectivity for Cloud SQL

---

### Current Infrastructure State

**Project**: `ytgrs-464303`
**Region**: `us-central1`
**Environment**: Production only (no staging for MVP)

**Active Resources:**
- ✅ 3 Service Accounts (v2 naming)
- ✅ 1 Artifact Registry repository
- ✅ 1 VPC network with 1 subnet
- ✅ IAM roles properly assigned
- ❌ 0 Secrets (ready for fresh setup)
- ❌ 0 Cloud SQL instances (ready for fresh database)
- ❌ 0 Cloud Run services (ready for deployment)

---

### Next Steps

**Pending Manual Task:**
- [ ] Set up billing alerts via GCP Console
  - Budget: $180/month
  - Alert thresholds: 50%, 80%, 100%
  - URL: https://console.cloud.google.com/billing/budgets

**Completed in Phase 2:**
- [x] `scripts/gcp/setup/setup-secrets.sh` - Secrets created ✅
- [x] `scripts/gcp/setup/setup-cloud-sql.sh` - Database created ✅

**Ready for Phase 3:**
- [ ] `scripts/gcp/deploy/1-verify-prerequisites.sh` - Verify prerequisites
- [ ] `scripts/gcp/deploy/2-run-migrations.sh` - Run database migrations
- [ ] `scripts/gcp/deploy/3-deploy-backend.sh` - Deploy backend to Cloud Run
- [ ] `scripts/gcp/deploy/4-deploy-frontend.sh` - Deploy frontend to Cloud Run

---

### Notes

**Design Decisions:**
1. **Single environment (prod only)**: Following "Simple is Best" - no staging for MVP
2. **Private IP for database**: Security best practice, no public access
3. **Shortened service account names**: GCP limitation (6-30 chars)
4. **Clean slate approach**: Deleted all old resources for consistency

**Security Improvements over old setup:**
- ✅ No public IP on database
- ✅ Proper IAM role separation
- ✅ Consistent v2 naming convention
- ✅ Deletion protection awareness

---

**Last Updated**: 2025-10-06
**Maintained By**: Cloud Engineering Team
