# Phase 3: Deployment Guide - AI Resume Review v2

**Version**: 1.0
**Date**: 2025-10-06
**Status**: Ready to Implement
**Estimated Time**: 4-5 hours (Quick path) or 2-3 days (Full automation)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites Check](#prerequisites-check)
3. [Recommended Implementation Order](#recommended-implementation-order)
4. [Detailed Step-by-Step Guide](#detailed-step-by-step-guide)
5. [Alternative Approaches](#alternative-approaches)
6. [Troubleshooting](#troubleshooting)
7. [Next Steps After Deployment](#next-steps-after-deployment)

---

## 🎯 Overview

**Goal**: Deploy the AI Resume Review application to Google Cloud Run with full connectivity to Cloud SQL database and Secret Manager.

### What We're Deploying

**Backend (FastAPI)**:
- Service: `ai-resume-review-v2-backend-prod`
- Container: Python FastAPI application
- Resources: 2GB RAM, 2 CPU
- Min instances: 1 (avoid cold starts)
- Connects to: Cloud SQL (private IP), Secret Manager

**Frontend (Next.js)**:
- Service: `ai-resume-review-v2-frontend-prod`
- Container: Next.js React application
- Resources: 512MB RAM, 1 CPU
- Min instances: 0 (scale to zero for cost savings)
- Connects to: Backend API

### Current Infrastructure (Completed in Phase 1 & 2)

✅ Service Accounts with proper IAM roles
✅ Artifact Registry for Docker images
✅ VPC Network with private subnet
✅ Cloud SQL PostgreSQL database (private IP)
✅ Secrets in Secret Manager (OpenAI key, JWT secret, DB password)

---

## ✅ Prerequisites Check

Before starting Phase 3, verify these items:

### 1. Backend Configuration

**Check**: Does `backend/app/core/config.py` read from Secret Manager?

**Current state**: Likely uses environment variables
**Required state**: Must read from Secret Manager

**Example code needed**:
```python
# backend/app/core/config.py
from google.cloud import secretmanager

def get_secret(secret_name: str) -> str:
    """Fetch secret from Google Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/ytgrs-464303/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Configuration
OPENAI_API_KEY = get_secret("openai-api-key-prod")
JWT_SECRET_KEY = get_secret("jwt-secret-key-prod")
DB_PASSWORD = get_secret("db-password-prod")

# Database connection (Unix socket for Cloud Run)
DB_HOST = "/cloudsql/ytgrs-464303:us-central1:ai-resume-review-v2-db-prod"
DB_PORT = 5432
DB_NAME = "ai_resume_review_prod"
DB_USER = "postgres"
```

**Action**: Update backend configuration if needed

---

### 2. Dockerfiles

**Check**: Do `frontend/Dockerfile` and `backend/Dockerfile` exist?

**Location**:
- `frontend/Dockerfile`
- `backend/Dockerfile`

**Test locally**:
```bash
# Test backend Docker build
cd backend
docker build -t backend-test .

# Test frontend Docker build
cd frontend
docker build -t frontend-test .
```

**Action**: Create or fix Dockerfiles if needed

---

### 3. Database Migrations

**Check**: Are Alembic migrations ready?

**Location**: `backend/alembic/versions/`

**Verify**:
```bash
cd backend
alembic current  # Should show current revision
alembic upgrade head --sql  # Preview SQL without running
```

**Action**: Ensure migrations exist and are tested

---

### 4. Dependencies

**Install required tools**:
```bash
# gcloud CLI (already installed ✓)
# Docker (verify)
docker --version

# Cloud SQL Proxy (for migrations)
# Will download in migration script
```

---

## 🚀 Recommended Implementation Order

Follow this sequence for fastest results (MVP approach):

```
Step 1: Create VPC Connector          → 10 minutes
Step 2: Run Database Migrations       → 30 minutes
Step 3: Deploy Backend to Cloud Run   → 2 hours
Step 4: Deploy Frontend to Cloud Run  → 1 hour
Step 5: Test End-to-End               → 30 minutes
```

**Total time**: ~4-5 hours

---

## 📝 Detailed Step-by-Step Guide

### **Step 1: Create VPC Connector** (Required)

**Why**: Cloud Run needs VPC Access Connector to reach Cloud SQL private IP

**Script**: Add to `setup-gcp-project.sh` or run manually

```bash
# Create VPC Access Connector
gcloud compute networks vpc-access connectors create arr-v2-connector \
    --region=us-central1 \
    --network=ai-resume-review-v2-vpc \
    --range=10.8.0.0/28 \
    --min-instances=2 \
    --max-instances=3 \
    --project=ytgrs-464303

# Verify creation
gcloud compute networks vpc-access connectors describe arr-v2-connector \
    --region=us-central1 \
    --project=ytgrs-464303
```

**Cost**: ~$10/month (always running, necessary for Cloud SQL access)

**Validation**:
```bash
# Should show STATE: READY
gcloud compute networks vpc-access connectors list --region=us-central1
```

---

### **Step 2: Run Database Migrations**

**Purpose**: Initialize database schema with Alembic migrations

#### **Option A: Local with Cloud SQL Proxy** (Recommended for MVP)

**Create script**: `scripts/gcp/run-migrations.sh`

```bash
#!/bin/bash
# run-migrations.sh - Run database migrations via Cloud SQL Proxy

set -e

PROJECT_ID="ytgrs-464303"
INSTANCE_CONNECTION_NAME="ytgrs-464303:us-central1:ai-resume-review-v2-db-prod"
DB_NAME="ai_resume_review_prod"
DB_USER="postgres"

echo "=========================================="
echo "Running Database Migrations"
echo "=========================================="

# Download Cloud SQL Proxy if not exists
if [ ! -f "./cloud-sql-proxy" ]; then
    echo "Downloading Cloud SQL Proxy..."
    curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.amd64
    chmod +x cloud-sql-proxy
fi

# Get database password from Secret Manager
DB_PASSWORD=$(gcloud secrets versions access latest --secret="db-password-prod" --project="$PROJECT_ID")

# Start Cloud SQL Proxy in background
echo "Starting Cloud SQL Proxy..."
./cloud-sql-proxy $INSTANCE_CONNECTION_NAME &
PROXY_PID=$!

# Wait for proxy to be ready
sleep 3

# Set connection string
export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@127.0.0.1:5432/$DB_NAME"

# Run migrations
echo "Running Alembic migrations..."
cd backend
alembic upgrade head

# Check migration status
echo "Current migration version:"
alembic current

# Kill proxy
kill $PROXY_PID

echo "✓ Migrations completed successfully!"
```

**Run**:
```bash
chmod +x scripts/gcp/run-migrations.sh
./scripts/gcp/run-migrations.sh
```

#### **Option B: Cloud Run Job** (More production-ready, but complex)

Skip for MVP. Can implement later.

---

### **Step 3: Deploy Backend to Cloud Run**

**Create script**: `scripts/gcp/deploy-backend.sh`

```bash
#!/bin/bash
# deploy-backend.sh - Deploy backend to Cloud Run

set -e

PROJECT_ID="ytgrs-464303"
REGION="us-central1"
SERVICE_NAME="ai-resume-review-v2-backend-prod"
SERVICE_ACCOUNT="arr-v2-backend-prod@ytgrs-464303.iam.gserviceaccount.com"
IMAGE_NAME="us-central1-docker.pkg.dev/$PROJECT_ID/ai-resume-review-v2/backend:latest"
VPC_CONNECTOR="arr-v2-connector"
SQL_INSTANCE="ytgrs-464303:us-central1:ai-resume-review-v2-db-prod"

echo "=========================================="
echo "Deploying Backend to Cloud Run"
echo "=========================================="

# Build Docker image
echo "Building Docker image..."
cd backend
docker build --platform linux/amd64 -t backend:latest .

# Tag for Artifact Registry
docker tag backend:latest $IMAGE_NAME

# Configure Docker auth for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

# Push to Artifact Registry
echo "Pushing image to Artifact Registry..."
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_NAME \
    --region=$REGION \
    --platform=managed \
    --service-account=$SERVICE_ACCOUNT \
    --vpc-connector=$VPC_CONNECTOR \
    --vpc-egress=private-ranges-only \
    --add-cloudsql-instances=$SQL_INSTANCE \
    --set-env-vars="DB_HOST=/cloudsql/$SQL_INSTANCE,DB_PORT=5432,DB_NAME=ai_resume_review_prod,DB_USER=postgres,PROJECT_ID=$PROJECT_ID,ENVIRONMENT=production" \
    --memory=2Gi \
    --cpu=2 \
    --min-instances=1 \
    --max-instances=20 \
    --concurrency=20 \
    --timeout=600 \
    --allow-unauthenticated \
    --project=$PROJECT_ID \
    --quiet

# Get service URL
BACKEND_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(status.url)")

echo ""
echo "=========================================="
echo "✓ Backend Deployed Successfully!"
echo "=========================================="
echo "Service URL: $BACKEND_URL"
echo "Health check: $BACKEND_URL/health"
echo ""

# Test health endpoint
echo "Testing health endpoint..."
curl -s $BACKEND_URL/health | jq .

echo ""
echo "Next: Deploy frontend with NEXT_PUBLIC_API_URL=$BACKEND_URL"
```

**Run**:
```bash
chmod +x scripts/gcp/deploy-backend.sh
./scripts/gcp/deploy-backend.sh
```

**Expected output**:
```
✓ Backend Deployed Successfully!
Service URL: https://ai-resume-review-v2-backend-prod-xxxxx-uc.a.run.app
```

---

### **Step 4: Deploy Frontend to Cloud Run**

**Create script**: `scripts/gcp/deploy-frontend.sh`

```bash
#!/bin/bash
# deploy-frontend.sh - Deploy frontend to Cloud Run

set -e

PROJECT_ID="ytgrs-464303"
REGION="us-central1"
SERVICE_NAME="ai-resume-review-v2-frontend-prod"
SERVICE_ACCOUNT="arr-v2-frontend-prod@ytgrs-464303.iam.gserviceaccount.com"
IMAGE_NAME="us-central1-docker.pkg.dev/$PROJECT_ID/ai-resume-review-v2/frontend:latest"

# Get backend URL (from previous deployment)
BACKEND_URL=$(gcloud run services describe ai-resume-review-v2-backend-prod \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(status.url)")

echo "=========================================="
echo "Deploying Frontend to Cloud Run"
echo "=========================================="
echo "Backend URL: $BACKEND_URL"
echo ""

# Build Docker image with backend URL
echo "Building Docker image..."
cd frontend
docker build \
    --platform linux/amd64 \
    --build-arg NEXT_PUBLIC_API_URL=$BACKEND_URL \
    -t frontend:latest .

# Tag for Artifact Registry
docker tag frontend:latest $IMAGE_NAME

# Configure Docker auth for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

# Push to Artifact Registry
echo "Pushing image to Artifact Registry..."
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_NAME \
    --region=$REGION \
    --platform=managed \
    --service-account=$SERVICE_ACCOUNT \
    --set-env-vars="NEXT_PUBLIC_API_URL=$BACKEND_URL,NODE_ENV=production,NEXT_TELEMETRY_DISABLED=1" \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=10 \
    --concurrency=80 \
    --timeout=300 \
    --allow-unauthenticated \
    --project=$PROJECT_ID \
    --quiet

# Get service URL
FRONTEND_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(status.url)")

echo ""
echo "=========================================="
echo "✓ Frontend Deployed Successfully!"
echo "=========================================="
echo "Frontend URL: $FRONTEND_URL"
echo "Backend URL:  $BACKEND_URL"
echo ""
echo "🎉 Application is now live!"
echo "Visit: $FRONTEND_URL"
echo ""
```

**Run**:
```bash
chmod +x scripts/gcp/deploy-frontend.sh
./scripts/gcp/deploy-frontend.sh
```

---

### **Step 5: Test End-to-End**

**Manual Testing Checklist**:

```bash
# 1. Test backend health
curl https://ai-resume-review-v2-backend-prod-xxxxx-uc.a.run.app/health

# 2. Test backend API docs
# Visit: https://ai-resume-review-v2-backend-prod-xxxxx-uc.a.run.app/docs

# 3. Test frontend
# Visit: https://ai-resume-review-v2-frontend-prod-xxxxx-uc.a.run.app

# 4. Test database connection
# Check backend logs:
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai-resume-review-v2-backend-prod" \
    --limit=50 \
    --format=json

# 5. Test secret access
# Check if backend can read secrets (check logs for errors)

# 6. Test full user flow
# Register → Login → Upload Resume → Get Analysis
```

**Validation**:
- ✅ Backend responds to /health endpoint
- ✅ Frontend loads without errors
- ✅ Backend can connect to database
- ✅ Backend can read secrets
- ✅ Frontend can call backend API
- ✅ Full user flow works end-to-end

---

## 🔄 Alternative Approaches

### **Approach A: Quick & Simple** (Recommended above)

**Pros**:
- Fastest to implement (4-5 hours)
- Easy to understand and debug
- Good for MVP

**Cons**:
- Some manual steps
- Less automated

---

### **Approach B: Fully Automated**

**Additional scripts to create**:

1. `scripts/gcp/build-and-push.sh` - Automate Docker builds
2. `scripts/gcp/deploy-to-production.sh` - One script for both services
3. `scripts/gcp/run-migrations.sh` - Cloud Run Job approach
4. `scripts/gcp/rollback.sh` - Rollback to previous version

**Pros**:
- Fully repeatable
- Production-ready CI/CD foundation
- Less manual work after initial setup

**Cons**:
- More upfront work (2-3 days)
- More complex to debug initially

**Time**: 2-3 days

---

## 🛠️ Troubleshooting

### Issue: "VPC connector not found"

**Solution**:
```bash
# Verify connector exists
gcloud compute networks vpc-access connectors list --region=us-central1

# If not found, create it (Step 1)
```

---

### Issue: "Failed to connect to Cloud SQL"

**Check**:
1. VPC connector is in READY state
2. Cloud Run has `--add-cloudsql-instances` flag
3. Service account has `roles/cloudsql.client` role
4. Connection string is correct: `/cloudsql/PROJECT:REGION:INSTANCE`

**Debug**:
```bash
# Check Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai-resume-review-v2-backend-prod" \
    --limit=20
```

---

### Issue: "Cannot read secrets"

**Check**:
1. Service account has `roles/secretmanager.secretAccessor`
2. Secrets exist: `gcloud secrets list`
3. Secret names match in code

**Debug**:
```bash
# Test secret access manually
gcloud secrets versions access latest --secret="openai-api-key-prod"
```

---

### Issue: "Docker build fails"

**Solution**:
```bash
# Check Dockerfile exists
ls -la frontend/Dockerfile backend/Dockerfile

# Test build locally
cd backend
docker build -t test .

# Check build logs for errors
```

---

### Issue: "Cloud Run deployment fails"

**Common causes**:
1. Image not pushed to Artifact Registry
2. Service account doesn't exist
3. Invalid environment variables
4. Insufficient memory/CPU

**Debug**:
```bash
# Check Cloud Run deployment logs
gcloud run services describe SERVICE_NAME --region=us-central1

# Check build logs
gcloud builds list --limit=5
```

---

## 📋 Next Steps After Deployment

### 1. Set Up Monitoring

```bash
# Create uptime checks
# Visit: https://console.cloud.google.com/monitoring/uptime

# Set up alerts
# Visit: https://console.cloud.google.com/monitoring/alerting
```

---

### 2. Set Up Custom Domain (Optional)

```bash
# Map custom domain to Cloud Run
gcloud run domain-mappings create \
    --service=ai-resume-review-v2-frontend-prod \
    --domain=app.yourdomain.com \
    --region=us-central1
```

---

### 3. Set Up CI/CD (Optional)

**GitHub Actions workflow** (`.github/workflows/deploy-production.yml`):

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          workload_identity_provider: '...'
          service_account: 'arr-v2-github-actions@ytgrs-464303.iam.gserviceaccount.com'

      - name: Deploy Backend
        run: ./scripts/gcp/deploy-backend.sh

      - name: Deploy Frontend
        run: ./scripts/gcp/deploy-frontend.sh
```

---

### 4. Performance Optimization

**After deployment, monitor and optimize**:

- Adjust CPU/Memory based on actual usage
- Tune min/max instances based on traffic
- Add caching (Redis) if needed
- Enable Cloud CDN for static assets

---

### 5. Security Hardening

**Post-deployment security tasks**:

- Enable Cloud Armor (DDoS protection)
- Set up WAF rules
- Enable audit logging
- Review IAM permissions
- Rotate secrets regularly

---

## 📊 Estimated Costs (After Phase 3)

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| Cloud Run (Frontend) | 512MB, avg 1 instance | $5-15 |
| Cloud Run (Backend) | 2GB, min 1 instance | $30-50 |
| Cloud SQL | db-f1-micro, 10GB | $25-35 |
| VPC Connector | 2-3 instances | $10 |
| Secret Manager | 3 secrets | $0.06 |
| Artifact Registry | Docker images | $1-2 |
| **Total** | | **$71-112/month** |

**Plus variable costs**:
- OpenAI API: $50-200/month (depends on usage)
- Egress bandwidth: $5-10/month

**Grand total**: $126-322/month

---

## ✅ Success Criteria

**Phase 3 is complete when**:

- ✅ VPC connector created and READY
- ✅ Database migrations run successfully
- ✅ Backend deployed and responding to /health
- ✅ Frontend deployed and loading
- ✅ Backend can connect to Cloud SQL
- ✅ Backend can read from Secret Manager
- ✅ Frontend can call backend API
- ✅ Full user registration → login → resume upload flow works
- ✅ All scripts committed to git

---

## 📚 Reference Documentation

**Scripts created in Phase 1 & 2**:
- [scripts/gcp/cleanup-old-resources.sh](scripts/gcp/cleanup-old-resources.sh)
- [scripts/gcp/setup-gcp-project.sh](scripts/gcp/setup-gcp-project.sh)
- [scripts/gcp/setup-cloud-sql.sh](scripts/gcp/setup-cloud-sql.sh)
- [scripts/gcp/setup-secrets.sh](scripts/gcp/setup-secrets.sh)
- [scripts/gcp/README.md](scripts/gcp/README.md)

**Architecture docs**:
- [GCP_CLOUD_ARCHITECTURE.md](GCP_CLOUD_ARCHITECTURE.md)
- [GCP_CLOUD_IMPLEMENTATION_SEQUENCE.md](GCP_CLOUD_IMPLEMENTATION_SEQUENCE.md)
- [deployment/DEPLOYMENT_LOG.md](deployment/DEPLOYMENT_LOG.md)

**GCP Documentation**:
- [Cloud Run](https://cloud.google.com/run/docs)
- [Cloud SQL](https://cloud.google.com/sql/docs)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [VPC Access](https://cloud.google.com/vpc/docs/configure-serverless-vpc-access)

---

## 🤝 Team Handover Notes

**For the next engineer**:

1. **Start here**: Read this document top to bottom
2. **Check prerequisites**: Verify all items in "Prerequisites Check" section
3. **Follow steps in order**: Don't skip VPC connector or migrations
4. **Test incrementally**: Deploy backend first, verify, then frontend
5. **Use dry-run**: Test deployment commands before running
6. **Check logs**: Always verify Cloud Run logs after deployment
7. **Ask questions**: If stuck, check Troubleshooting section first

**Important files to review**:
- `backend/app/core/config.py` - Needs Secret Manager integration
- `backend/Dockerfile` - Must work for Cloud Run
- `frontend/Dockerfile` - Must work for Cloud Run
- `backend/alembic/versions/*` - Database migrations

**Estimated time commitment**:
- First-time: 8-10 hours (learning + implementation)
- With experience: 4-5 hours

---

**Document Version**: 1.0
**Last Updated**: 2025-10-06
**Next Review**: After Phase 3 completion
**Maintained By**: Cloud Engineering Team
