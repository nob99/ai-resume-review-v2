# GCP Cloud Deployment Guide

**Version**: 1.0
**Last Updated**: 2025-10-06
**Status**: Ready for Implementation

---

## 📋 Overview

This directory contains all configuration files, scripts, and documentation needed to deploy the AI Resume Review Platform to Google Cloud Platform (GCP).

**Key Principle**: Simple, production-ready deployment following GCP best practices.

---

## 📁 Directory Structure

```
deployment/
├── README.md                           ← This file (deployment guide)
├── configs/                            ← Configuration files
│   ├── .env.staging.example            ← Staging environment variables
│   ├── .env.production.example         ← Production environment variables
│   ├── cloud-run-backend-staging.yaml  ← Backend staging Cloud Run config
│   ├── cloud-run-backend-production.yaml
│   ├── cloud-run-frontend-staging.yaml
│   └── cloud-run-frontend-production.yaml
│
└── docs/                               ← Additional documentation
    └── (will be added as needed)
```

---

## 🚀 Quick Start Guide

### Prerequisites

Before deploying, ensure you have:

1. ✅ **GCP Account** with billing enabled
2. ✅ **gcloud CLI** installed and authenticated
3. ✅ **Docker** installed (for building images)
4. ✅ **GitHub repository** set up with code
5. ✅ **OpenAI API key** (for AI agents)

### Deployment Steps (High-Level)

```bash
# Phase 1 & 2: Initial GCP Setup (one-time) - COMPLETED ✅
./scripts/gcp/setup/setup-gcp-project.sh      # Set up GCP project
./scripts/gcp/setup/setup-cloud-sql.sh        # Create database
./scripts/gcp/setup/setup-secrets.sh          # Store secrets

# Phase 3: Deploy Application
cd scripts/gcp/deploy/
./1-verify-prerequisites.sh   # Verify everything is ready
./2-run-migrations.sh         # Initialize database schema
./3-deploy-backend.sh         # Deploy backend to Cloud Run
./4-deploy-frontend.sh        # Deploy frontend to Cloud Run

# Or deploy all at once:
./deploy-all.sh               # Runs all steps with confirmations
```

---

## 📂 Configuration Files Explained

### Environment Variables (`.env.*.example`)

**Purpose**: Define non-sensitive configuration for each environment.

**Files**:
- `.env.staging.example` → Copy to `.env.staging`
- `.env.production.example` → Copy to `.env.production`

**What goes here**:
- ✅ Database connection details (host, port, database name)
- ✅ Application settings (log level, environment)
- ✅ AI model configuration (model name, timeout)

**What DOES NOT go here**:
- ❌ API keys (use Secret Manager)
- ❌ Passwords (use Secret Manager)
- ❌ JWT secrets (use Secret Manager)

### Cloud Run Configurations (`cloud-run-*.yaml`)

**Purpose**: Define Cloud Run service settings (memory, CPU, scaling).

**Files**:
- `cloud-run-backend-staging.yaml`
- `cloud-run-backend-production.yaml`
- `cloud-run-frontend-staging.yaml`
- `cloud-run-frontend-production.yaml`

**Key Settings**:
| Service | Memory | CPU | Min Instances | Max Instances |
|---------|--------|-----|---------------|---------------|
| Backend (Staging) | 2GB | 2 | 0 | 10 |
| Backend (Production) | 2GB | 2 | 1 | 20 |
| Frontend (Staging) | 512MB | 1 | 0 | 5 |
| Frontend (Production) | 512MB | 1 | 0 | 10 |

---

## 🔧 Deployment Scripts Explained

### Setup Scripts (Phase 1 & 2) - ✅ COMPLETED

Located in `scripts/gcp/setup/`:

1. **`setup-gcp-project.sh`** ✅
   - **Purpose**: Initialize GCP project with required APIs and services
   - **Status**: Completed (Phase 1)
   - **What it created**:
     - Service accounts (backend, frontend, GitHub Actions)
     - Artifact Registry
     - VPC network and subnet
     - IAM roles

2. **`setup-cloud-sql.sh`** ✅
   - **Purpose**: Create PostgreSQL database instance
   - **Status**: Completed (Phase 2)
   - **What it created**:
     - Cloud SQL instance (production only, no staging for MVP)
     - Private IP configuration
     - Automated backups
     - Production database

3. **`setup-secrets.sh`** ✅
   - **Purpose**: Store sensitive values in Secret Manager
   - **Status**: Completed (Phase 2)
   - **What it created**:
     - Secrets (OpenAI API key, DB password, JWT secret)
     - IAM permissions for service accounts
     - Secret values securely stored

### Deployment Scripts (Phase 3) - 🚀 READY TO USE

Located in `scripts/gcp/deploy/`:

4. **`1-verify-prerequisites.sh`** 🆕
   - **Purpose**: Verify all prerequisites before deployment
   - **Run**: Before first deployment (and troubleshooting)
   - **What it checks**:
     - Development tools (gcloud, docker)
     - GCP authentication and project
     - Infrastructure (VPC, Cloud SQL, Secrets)
     - Service accounts and IAM
     - Application files (Dockerfiles, migrations)

5. **`2-run-migrations.sh`** 🆕
   - **Purpose**: Run database migrations via Cloud SQL Proxy
   - **Run**: Before first deployment, or when database schema changes
   - **What it does**:
     - Downloads Cloud SQL Proxy
     - Connects to Cloud SQL database
     - Runs Alembic migrations
     - Verifies migration status

6. **`3-deploy-backend.sh`** 🆕
   - **Purpose**: Deploy backend to Cloud Run
   - **Run**: Every time backend code changes
   - **What it does**:
     - Builds Docker image
     - Pushes to Artifact Registry
     - Creates VPC Connector (if needed)
     - Deploys to Cloud Run with secrets and database connection
     - Tests health endpoint

7. **`4-deploy-frontend.sh`** 🆕
   - **Purpose**: Deploy frontend to Cloud Run
   - **Run**: Every time frontend code changes
   - **What it does**:
     - Gets backend URL
     - Builds Docker image with backend URL
     - Pushes to Artifact Registry
     - Deploys to Cloud Run
     - Tests frontend accessibility

8. **`deploy-all.sh`** 🆕
   - **Purpose**: Run complete deployment pipeline
   - **Run**: For quick redeployments
   - **What it does**:
     - Runs scripts 1-4 in sequence
     - Asks for confirmation between steps
     - Stops if any step fails

### Utility Scripts

Located in `scripts/gcp/utils/`:

9. **`common-functions.sh`** 🆕
   - **Purpose**: Shared bash functions for all scripts
   - **Used by**: All deployment and verification scripts
   - **Contains**: Configuration variables, logging functions, validation functions

10. **`rollback.sh`**
   - **Purpose**: Rollback to previous Cloud Run revision
   - **Run**: When deployment has issues
   - **What it does**:
     - Lists available revisions
     - Routes traffic to previous revision
     - Verifies rollback successful

### Verification Scripts

Located in `scripts/gcp/verify/`:

11. **`health-check.sh`** 🆕
   - **Purpose**: Quick smoke test of deployed services
   - **Run**: After every deployment
   - **What it tests**:
     - Backend health endpoint
     - Frontend accessibility
     - Database connectivity
     - API documentation

12. **`integration-test.sh`** 🆕
   - **Purpose**: Full integration test of user flow
   - **Run**: After first deployment, or major changes
   - **What it tests**:
     - User registration
     - User login
     - Authenticated requests
     - Frontend loading

---

## 🔐 Secrets Management

### What are Secrets?

Sensitive values that should never be committed to code:
- OpenAI API key
- Database passwords
- JWT signing secret

### How Secrets are Stored

```
Local Development:
  .env files (in .gitignore)

GCP Cloud:
  Secret Manager (encrypted, access-controlled)
```

### How to Add/Update Secrets

```bash
# Secrets are already created (Phase 2) ✅
# To update a secret value:
echo -n "NEW_SECRET_VALUE" | gcloud secrets versions add SECRET_NAME \
  --data-file=-

# Or run the setup-secrets script again (idempotent):
./scripts/gcp/setup/setup-secrets.sh
```

### How Code Accesses Secrets

```python
# Backend code (backend/app/core/config.py)
from google.cloud import secretmanager

def get_secret(secret_name: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Usage
OPENAI_API_KEY = get_secret("openai-api-key-prod")
```

---

## 🌐 Environment Overview

### Staging Environment

**Purpose**: Pre-production testing

**URL**:
- Frontend: `https://ai-resume-review-frontend-staging-xxx.run.app`
- Backend: `https://ai-resume-review-backend-staging-xxx.run.app`

**Characteristics**:
- Lower resource limits (save costs)
- Scale to zero (both frontend and backend)
- Automated deployment (on push to `staging` branch)
- Can use test OpenAI API key (cheaper)

**When to use**:
- Testing new features
- QA testing
- Integration testing
- Pre-production verification

### Production Environment

**Purpose**: Live production for real users

**URL** (MVP):
- Frontend: `https://ai-resume-review-frontend-prod-xxx.run.app`
- Backend: `https://ai-resume-review-backend-prod-xxx.run.app`

**URL** (Future with custom domain):
- Frontend: `https://app.yourcompany.com`
- Backend: `https://api.yourcompany.com`

**Characteristics**:
- Higher resource limits (handle traffic)
- Backend min instances: 1 (avoid cold starts)
- Manual deployment (requires approval)
- Production OpenAI API key

**When to use**:
- Real users
- Production traffic
- After staging verification

---

## 📊 Cost Management

### Expected Costs (Monthly)

**Staging**:
- Cloud Run: ~$10-15
- Cloud SQL: ~$25
- Secrets: ~$0.03
- **Total**: ~$35-40/month

**Production**:
- Cloud Run: ~$35-50 (min 1 backend instance)
- Cloud SQL: ~$25-35
- Load Balancer: ~$18-25
- Logging: ~$5
- **Total**: ~$83-130/month

**Variable Costs**:
- OpenAI API: ~$50-200/month (depends on usage)

### Cost Optimization Tips

1. **Scale to zero** when not in use (staging)
2. **Use db-f1-micro** for MVP (upgrade later)
3. **Monitor logs** to avoid excessive logging costs
4. **Set budget alerts** (e.g., alert when > $200/month)
5. **Review unused resources** monthly

---

## 🔄 CI/CD Workflow

### Automated Deployment (GitHub Actions)

Located in `.github/workflows/`:

1. **`test.yml`**: Run tests on every PR
2. **`deploy-staging.yml`**: Auto-deploy to staging on push to `staging` branch
3. **`deploy-production.yml`**: Manual deploy to production (requires approval)
4. **`rollback.yml`**: Rollback production deployment

### Workflow Diagram

```
Developer → Push to feature branch
    ↓
GitHub Actions runs tests (test.yml)
    ↓
Code review & approval
    ↓
Merge to staging branch
    ↓
GitHub Actions deploys to staging (deploy-staging.yml)
    ↓
QA tests staging environment
    ↓
Manual trigger production deployment
    ↓
GitHub Actions deploys to production (deploy-production.yml)
    ↓
Monitor for issues → Rollback if needed (rollback.yml)
```

---

## 🔍 Monitoring & Debugging

### Viewing Logs

```bash
# Backend logs (staging)
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=ai-resume-review-backend-staging" \
  --limit 50 --format json

# Frontend logs (production)
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=ai-resume-review-frontend-prod" \
  --limit 50
```

### Monitoring Dashboard

Access Cloud Monitoring:
```
https://console.cloud.google.com/monitoring
```

**Key Metrics**:
- Request rate (requests/second)
- Error rate (%)
- Latency (P50, P95, P99)
- CPU/Memory usage
- Instance count

### Alerts

Configured alerts:
- CPU > 80% for 5 minutes
- Memory > 90% for 5 minutes
- Error rate > 5%
- Latency P95 > 5 seconds

---

## 🆘 Troubleshooting

### Common Issues

**1. Deployment Fails: "Permission Denied"**
```bash
# Fix: Grant IAM permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT" \
  --role="roles/run.admin"
```

**2. Database Connection Errors**
```bash
# Check Cloud SQL instance is running
gcloud sql instances list

# Test connection with Cloud SQL Proxy
cloud_sql_proxy -instances=PROJECT:REGION:INSTANCE=tcp:5432
```

**3. Secret Not Found**
```bash
# Verify secret exists
gcloud secrets list

# Check IAM permissions
gcloud secrets get-iam-policy SECRET_NAME
```

**4. Cold Start Too Slow**
```bash
# Increase min instances (production)
gcloud run services update SERVICE_NAME \
  --min-instances=1
```

---

## 📚 Additional Resources

### GCP Documentation
- [Cloud Run](https://cloud.google.com/run/docs)
- [Cloud SQL](https://cloud.google.com/sql/docs)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)

### Project Documentation
- [GCP_CLOUD_ARCHITECTURE.md](../GCP_CLOUD_ARCHITECTURE.md) - Complete architecture
- [CLAUDE.md](../CLAUDE.md) - Development guidelines
- [README.md](../README.md) - Project overview

---

## 🎯 Next Steps

After setting up deployment:

1. ✅ **Set up monitoring alerts**
2. ✅ **Configure custom domain** (optional)
3. ✅ **Enable CDN** (optional, for performance)
4. ✅ **Set up error tracking** (Sentry)
5. ✅ **Document rollback procedures**
6. ✅ **Train team on deployment process**

---

## 📞 Support

For issues or questions:
- Check troubleshooting section above
- Review GCP documentation
- Contact DevOps team

---

**Last Updated**: 2025-10-06
**Maintained By**: DevOps Team
