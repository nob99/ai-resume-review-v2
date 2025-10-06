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
# Phase 1: Initial GCP Setup (one-time)
./scripts/gcp/setup-gcp-project.sh      # Set up GCP project
./scripts/gcp/setup-cloud-sql.sh        # Create database
./scripts/gcp/setup-secrets.sh          # Store secrets

# Phase 2: Deploy to Staging
./scripts/gcp/deploy-to-staging.sh      # Deploy to staging

# Phase 3: Test Staging
# Manually test all features in staging environment

# Phase 4: Deploy to Production
./scripts/gcp/deploy-to-production.sh   # Deploy to production (requires approval)
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

### Setup Scripts

Located in `scripts/gcp/`:

1. **`setup-gcp-project.sh`**
   - **Purpose**: Initialize GCP project with required APIs and services
   - **Run once**: Before first deployment
   - **What it does**:
     - Create GCP project
     - Enable Cloud Run, Cloud SQL, Secret Manager APIs
     - Create service accounts
     - Set up Workload Identity (GitHub ↔ GCP)
     - Create Artifact Registry

2. **`setup-cloud-sql.sh`**
   - **Purpose**: Create PostgreSQL database instances
   - **Run once**: Before first deployment
   - **What it does**:
     - Create Cloud SQL instance (staging + production)
     - Configure private IP
     - Set up automated backups
     - Create databases and users

3. **`setup-secrets.sh`**
   - **Purpose**: Store sensitive values in Secret Manager
   - **Run once**: Before first deployment (and when rotating secrets)
   - **What it does**:
     - Create secrets (OpenAI API key, DB password, JWT secret)
     - Set IAM permissions
     - Store secret values securely

### Deployment Scripts

4. **`deploy-to-staging.sh`**
   - **Purpose**: Deploy to staging environment
   - **Run**: Whenever you want to test changes
   - **What it does**:
     - Build Docker images
     - Push to Artifact Registry
     - Deploy to Cloud Run (staging)
     - Run smoke tests

5. **`deploy-to-production.sh`**
   - **Purpose**: Deploy to production environment
   - **Run**: After staging is tested and approved
   - **What it does**:
     - Verify staging is healthy
     - Prompt for manual approval
     - Deploy to Cloud Run (production)
     - Run smoke tests
     - Monitor for 5 minutes

6. **`rollback.sh`**
   - **Purpose**: Rollback to previous version
   - **Run**: When production deployment has issues
   - **What it does**:
     - List available revisions
     - Route traffic to previous revision
     - Verify rollback successful

7. **`run-migrations.sh`**
   - **Purpose**: Run database migrations
   - **Run**: When database schema changes
   - **What it does**:
     - Connect to Cloud SQL
     - Run Alembic migrations
     - Verify schema updated

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
# Run the setup-secrets script
./scripts/gcp/setup-secrets.sh staging

# Or manually:
echo -n "YOUR_SECRET_VALUE" | gcloud secrets create SECRET_NAME \
  --data-file=- \
  --replication-policy="automatic"
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
