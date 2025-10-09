# CI/CD Setup Guide

## Overview

This project uses GitHub Actions for continuous integration and deployment to Google Cloud Platform (GCP).

**Architecture:**
- **Staging**: Auto-deploys on merge to `main` branch
- **Production**: Manual deployment via GitHub Actions UI

**Workflows:**
1. `staging.yml` - CI tests + auto-deploy to staging
2. `production.yml` - Manual deployment to production

---

## Prerequisites Completed ✅

The following infrastructure has been set up:

- ✅ Workload Identity Federation Pool: `github-actions`
- ✅ Workload Identity Provider: `github`
- ✅ Service Account: `github-actions-deployer@ytgrs-464303.iam.gserviceaccount.com`
- ✅ IAM Permissions: Cloud Run Admin, Artifact Registry Writer, Service Account User
- ✅ Repository Binding: `nob99/ai-resume-review-v2`

---

## GitHub Secrets Configuration

You need to configure the following secrets in your GitHub repository.

### How to Add Secrets:

1. Go to your GitHub repository: https://github.com/nob99/ai-resume-review-v2
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret below

### Required Secrets:

**None required!**

The workflows use hardcoded values that are already public:
- Project ID: `ytgrs-464303`
- Project Number: `864523342928`
- Service Account: `github-actions-deployer@ytgrs-464303.iam.gserviceaccount.com`
- Workload Identity Provider: `projects/864523342928/locations/global/workloadIdentityPools/github-actions/providers/github`

These are not sensitive and can be committed to the repository.

### Optional Secrets (for future enhancements):

| Secret Name | Description | How to Get |
|------------|-------------|------------|
| `SLACK_WEBHOOK_URL` | Slack notifications | Create webhook in Slack workspace |

---

## GitHub Environment Setup (Optional)

For production approval gates:

1. Go to **Settings** → **Environments**
2. Click **New environment**
3. Name: `production`
4. Add required reviewers (yourself or team members)
5. Save

**Without this:** Production workflow will run immediately when triggered
**With this:** Production workflow will wait for approval before deploying

---

## How to Use CI/CD

### Workflow 1: Development → Staging (Automatic)

```bash
# 1. Create feature branch
git checkout -b feature/my-new-feature

# 2. Develop and commit
git add .
git commit -m "feat: add new feature"
git push origin feature/my-new-feature

# 3. Create Pull Request to main
# - Go to GitHub and create PR
# - CI tests run automatically
# - Wait for tests to pass

# 4. Merge PR to main
# - Click "Merge pull request"
# - Staging deployment starts automatically!
# - Wait ~8-10 minutes for deployment to complete

# 5. Test on staging
# - Backend: https://ai-resume-review-v2-backend-staging-wnjxxf534a-uc.a.run.app
# - Frontend: https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app
```

**Timeline:**
- Tests run: ~3-5 minutes
- Build + Deploy: ~5-8 minutes
- **Total: ~8-13 minutes** from merge to staging live

---

### Workflow 2: Staging → Production (Manual)

```bash
# 1. Test thoroughly on staging
# - Verify all features work
# - Check backend health: /health endpoint
# - Test frontend functionality

# 2. Go to GitHub Actions
# - Navigate to: https://github.com/nob99/ai-resume-review-v2/actions
# - Click on "Deploy to Production" workflow
# - Click "Run workflow" button

# 3. Configure deployment
Backend image tag: staging-latest  (or specific git SHA)
Build new frontend: ✓ checked  (required for production API URL)

# 4. Click "Run workflow"
# - If environment protection is enabled, approve the deployment
# - Wait ~5-8 minutes for deployment

# 5. Verify production
# - Backend: https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app
# - Frontend: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app
```

**Timeline:**
- Build frontend: ~3-4 minutes
- Deploy: ~2-3 minutes
- Health checks: ~1 minute
- **Total: ~6-8 minutes**

---

## Workflow Details

### Staging Workflow (`staging.yml`)

**Triggers:**
- Push to `main` branch (auto-deploy)
- Pull request to `main` (tests only, no deploy)

**Steps:**
1. **Test Job:**
   - Checkout code
   - Run ESLint (frontend)
   - Run Jest tests (frontend)
   - Run Black (backend format check)
   - Run Flake8 (backend linting)
   - Run pytest (backend unit tests)

2. **Build and Deploy Job** (only on push to main):
   - Authenticate to GCP via Workload Identity
   - Build backend Docker image
   - Build frontend Docker image (with staging API URL)
   - Push images to Artifact Registry
   - Deploy backend to Cloud Run staging
   - Deploy frontend to Cloud Run staging
   - Run health checks
   - Display deployment summary

**Image Tags:**
- Backend: `<git-sha>`, `staging-latest`
- Frontend: `<git-sha>-staging`, `staging-latest`

---

### Production Workflow (`production.yml`)

**Triggers:**
- Manual trigger only (`workflow_dispatch`)

**Inputs:**
- `backend_image_tag`: Which backend image to deploy (default: `staging-latest`)
- `frontend_build_from_staging`: Whether to build new frontend image (default: `true`)

**Steps:**
1. Checkout code (if building frontend)
2. Authenticate to GCP via Workload Identity
3. Build frontend Docker image (with production API URL)
4. Push frontend image to Artifact Registry
5. Verify backend image exists
6. Deploy backend to Cloud Run production
7. Deploy frontend to Cloud Run production
8. Run health checks (5 retries, 10s between attempts)
9. Display deployment summary with rollback instructions

**Image Tags:**
- Backend: `<user-specified-tag>` (usually `staging-latest` or specific git SHA)
- Frontend: `<git-sha>-production`, `production-latest`

---

## Image Tagging Strategy

### Backend Images:
```
backend:abc1234                # Specific commit (from staging deploy)
backend:staging-latest         # Latest staging deployment
backend:production-latest      # Latest production deployment (if deployed)
```

### Frontend Images:
```
frontend:abc1234-staging       # Staging build with staging API URL
frontend:abc1234-production    # Production build with production API URL
frontend:staging-latest        # Latest staging deployment
frontend:production-latest     # Latest production deployment
```

**Why different frontend images?**
- Frontend builds bake in the API URL at build time (`NEXT_PUBLIC_API_URL`)
- Staging needs: `https://ai-resume-review-v2-backend-staging-xxx.run.app`
- Production needs: `https://ai-resume-review-v2-backend-prod-xxx.run.app`

---

## Troubleshooting

### Workflow fails on authentication

**Error:** `Unable to get workload identity token`

**Solution:**
1. Verify service account exists:
   ```bash
   gcloud iam service-accounts list | grep github-actions
   ```

2. Verify Workload Identity binding:
   ```bash
   gcloud iam service-accounts get-iam-policy \
     github-actions-deployer@ytgrs-464303.iam.gserviceaccount.com
   ```

3. Check repository name in binding matches: `nob99/ai-resume-review-v2`

---

### Tests fail but code works locally

**Common causes:**
- Environment variables missing in CI
- Dependencies not installed correctly
- Tests rely on local services (database, Redis)

**Solutions:**
- Skip integration tests in CI: `pytest -m "not integration"`
- Mock external dependencies
- Use in-memory alternatives for tests

---

### Docker build fails

**Error:** `COPY failed: file not found`

**Solution:**
- Ensure Dockerfile is in correct location: `frontend/Dockerfile`, `backend/Dockerfile`
- Build from project root: `docker build -f backend/Dockerfile .`
- Check `.dockerignore` isn't excluding needed files

---

### Health checks fail after deployment

**Backend health check fails:**
1. Check Cloud Run logs:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND \
     resource.labels.service_name=ai-resume-review-v2-backend-staging" --limit=50
   ```

2. Common issues:
   - Database connection failed (check Cloud SQL connection)
   - Missing environment variables
   - Port not matching (should be 8000)

**Frontend health check fails:**
1. Check if frontend can reach backend
2. Verify `NEXT_PUBLIC_API_URL` is correct
3. Check Cloud Run logs

---

### Deployment succeeds but app doesn't work

**Checklist:**
1. ✅ Health endpoint returns 200
2. ✅ Cloud Run service is allocated traffic
3. ✅ Environment variables are set correctly
4. ✅ Secrets are accessible
5. ✅ Database connection works
6. ✅ Frontend can call backend API

**Debug commands:**
```bash
# Check backend environment variables
gcloud run services describe ai-resume-review-v2-backend-staging \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env)"

# Check recent logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=ai-resume-review-v2-backend-staging" \
  --limit=100 \
  --format="table(timestamp,severity,textPayload)"
```

---

## Rollback Procedure

### If production deployment fails:

**Option 1: Rollback to previous revision**
```bash
# List recent revisions
gcloud run revisions list \
  --service=ai-resume-review-v2-backend-prod \
  --region=us-central1

# Rollback backend
gcloud run services update-traffic \
  ai-resume-review-v2-backend-prod \
  --to-revisions=PREVIOUS_REVISION_NAME=100 \
  --region=us-central1

# Rollback frontend
gcloud run services update-traffic \
  ai-resume-review-v2-frontend-prod \
  --to-revisions=PREVIOUS_REVISION_NAME=100 \
  --region=us-central1
```

**Option 2: Redeploy previous working image**
```bash
# Go to GitHub Actions
# Run "Deploy to Production" workflow
# Use earlier git SHA or "production-latest" tag
```

---

## Database Migrations

**⚠️ Database migrations are NOT automated in CI/CD**

**Manual migration process:**

1. Create migration SQL file locally
2. Test migration on local database
3. Merge to main (deploys application code to staging)
4. **Before testing on staging**, run migration on staging database:
   ```bash
   # Temporarily add public IP
   gcloud sql instances patch ai-resume-review-v2-db-staging --assign-ip

   # Run migration
   PGPASSWORD=$(gcloud secrets versions access latest --secret=db-password-staging) \
   psql -h STAGING_IP -U postgres -d ai_resume_review_staging -f migration.sql

   # Remove public IP
   gcloud sql instances patch ai-resume-review-v2-db-staging --no-assign-ip
   ```
5. Test application on staging
6. Repeat for production database before production deployment

**Why manual?**
- Database changes are risky and hard to rollback
- Need human verification before applying
- Migrations are infrequent (once per week in MVP)

---

## Monitoring Deployments

### View workflow runs:
- GitHub Actions: https://github.com/nob99/ai-resume-review-v2/actions

### View deployed services:
```bash
# List all Cloud Run services
gcloud run services list --region=us-central1

# Get service details
gcloud run services describe ai-resume-review-v2-backend-staging \
  --region=us-central1
```

### View deployed images:
```bash
# List backend images
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/ytgrs-464303/ai-resume-review-v2/backend

# List frontend images
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/ytgrs-464303/ai-resume-review-v2/frontend
```

### View logs:
```bash
# Staging backend logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=ai-resume-review-v2-backend-staging" \
  --limit=50

# Production backend logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=ai-resume-review-v2-backend-prod" \
  --limit=50
```

---

## Cost Optimization

### Current CI/CD Costs:

**GitHub Actions:**
- Free tier: 2000 minutes/month
- Current usage estimate: ~300-400 minutes/month
- **Cost: $0/month** (within free tier)

**Artifact Registry:**
- Storage: ~2-5GB for Docker images
- **Cost: ~$1-2/month**

**Total CI/CD Cost: ~$1-2/month** ✅

### Optimization tips:
- Clean up old images: Keep only last 10 images per service
- Use Docker layer caching (already implemented)
- Don't run integration tests in CI (too slow, use staging)

---

## Next Steps

### Immediate (Required for workflows to work):
1. ✅ Workload Identity configured
2. ✅ Workflows created
3. ⏸️ Test workflows (push to main to trigger staging deploy)

### Optional Enhancements:
- [ ] Add GitHub Environment protection for production
- [ ] Add Slack notifications on deployment success/failure
- [ ] Add automatic image cleanup (delete images older than 30 days)
- [ ] Add deployment metrics dashboard
- [ ] Add automated integration tests on staging after deployment

---

## Support

**Documentation:**
- GitHub Actions: https://docs.github.com/en/actions
- Workload Identity: https://cloud.google.com/iam/docs/workload-identity-federation
- Cloud Run: https://cloud.google.com/run/docs

**Commands:**
```bash
# View workflow file
cat .github/workflows/staging.yml

# Test Docker builds locally
docker build -f backend/Dockerfile -t backend:test .
docker build -f frontend/Dockerfile -t frontend:test .

# Check GCP authentication
gcloud auth list
gcloud config list

# Verify service account permissions
gcloud projects get-iam-policy ytgrs-464303 \
  --flatten="bindings[].members" \
  --filter="bindings.members:github-actions-deployer@ytgrs-464303.iam.gserviceaccount.com"
```

---

**Last Updated:** 2025-10-09
**Version:** 1.0
**Status:** Production Ready
