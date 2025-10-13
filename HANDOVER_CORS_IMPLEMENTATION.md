# Handover Document: CORS Configuration Implementation

**Date:** 2025-10-12
**Project:** AI Resume Review Platform v2
**Task:** Dynamic CORS Configuration Implementation
**Status:** ⚠️ **INCOMPLETE - REQUIRES COMPLETION**
**Priority:** 🔴 **P0 - PRODUCTION BLOCKER**

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current Status](#current-status)
3. [What Was Accomplished](#what-was-accomplished)
4. [What Needs to Be Done](#what-needs-to-be-done)
5. [Technical Context](#technical-context)
6. [Step-by-Step Resolution Guide](#step-by-step-resolution-guide)
7. [Files Modified](#files-modified)
8. [Testing Checklist](#testing-checklist)
9. [Rollback Plan](#rollback-plan)
10. [References](#references)

---

## Executive Summary

### **The Problem**
Production frontend cannot communicate with backend due to CORS policy error:
```
Access to XMLHttpRequest at 'https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/api/v1/auth/login'
from origin 'https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app'
has been blocked by CORS policy
```

**Root Cause:** Hardcoded incorrect CORS origins in `backend/app/main.py`

### **The Solution**
Implement dynamic CORS configuration using environment variables, with single source of truth in `config/environments.yml`.

### **Current State**
✅ **Architecture implemented** - Code changes complete
❌ **Deployment broken** - GitHub Actions workflows incomplete
🔴 **Production still broken** - CORS error persists

---

## Current Status

### **✅ Completed**
- [x] Backend code reads CORS from `ALLOWED_ORIGINS` environment variable
- [x] CORS configuration added to `config/environments.yml`
- [x] Local development (Docker) configured
- [x] Deployment scripts updated with env-vars-file approach
- [x] GitHub Actions workflows updated (but incomplete)
- [x] Documentation added to CLAUDE.md
- [x] All changes committed to main branch

### **❌ Blocked/Failed**
- [ ] Staging deployment fails (container won't start)
- [ ] Production deployment not attempted
- [ ] GitHub Actions workflows missing Cloud Run configuration
- [ ] CORS still not working in production

### **🟡 Needs Attention**
- Manual CORS fix required for production (immediate)
- Complete GitHub Actions workflows (next sprint)
- Test full CI/CD pipeline

---

## What Was Accomplished

### **1. Code Architecture** ✅

**File:** `backend/app/main.py` (lines 139-160)

Changed from hardcoded CORS origins:
```python
# OLD (WRONG)
allow_origins=[
    "http://localhost:3000",
    "https://ai-resume-review-v2-frontend-prod-864523342928.us-central1.run.app",  # Wrong URL!
    ...
]
```

To dynamic environment variable:
```python
# NEW (CORRECT)
import os

allowed_origins_str = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000"
)
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

logger.info(f"CORS enabled for {len(allowed_origins)} origins")
logger.debug(f"Allowed CORS origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    ...
)
```

### **2. Configuration** ✅

**File:** `config/environments.yml` (added CORS sections)

```yaml
staging:
  cors:
    allowed_origins:
      - https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app
      - https://ai-resume-review-v2-backend-staging-wnjxxf534a-uc.a.run.app
      - http://localhost:3000
      - http://localhost:8000

production:
  cors:
    allowed_origins:
      - https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app
      - https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app
      - https://airesumereview.com
      - https://www.airesumereview.com
      - https://api.airesumereview.com
```

### **3. Local Development** ✅

**File:** `docker-compose.dev.yml` (line 92)

```yaml
backend:
  environment:
    ALLOWED_ORIGINS: "http://localhost:3000,http://localhost:8000,http://frontend:3000"
```

**File:** `backend/.env.example` (lines 35-38)

```bash
# CORS Configuration
# Comma-separated list of allowed origins for CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### **4. Deployment Scripts** ✅

**File:** `scripts/lib/load-config.sh` (lines 118-120)

```bash
# Export environment-specific settings - CORS
export ALLOWED_ORIGINS=$(yq ".$ENV.cors.allowed_origins | join(\",\")" "$CONFIG_FILE")
```

**File:** `scripts/gcp/deploy/deploy.sh` (lines 506-523)

```bash
# Create env vars YAML file for gcloud
ENV_VARS_FILE="/tmp/backend-env-vars-$$.yaml"
cat > "$ENV_VARS_FILE" <<EOF
ALLOWED_ORIGINS: "${ALLOWED_ORIGINS}"
EOF

gcloud run deploy "$BACKEND_SERVICE_NAME" \
  --image="$BACKEND_IMAGE_REMOTE" \
  --env-vars-file="$ENV_VARS_FILE" \
  ...
```

### **5. GitHub Actions** ⚠️ (Incomplete)

**Files:** `.github/workflows/staging.yml`, `.github/workflows/production.yml`

```yaml
- name: Deploy Backend to Staging/Production
  run: |
    CORS_ORIGINS=$(yq eval '.staging.cors.allowed_origins | join(",")' config/environments.yml)

    cat > /tmp/backend-env-vars.yaml <<EOF
    ALLOWED_ORIGINS: "${CORS_ORIGINS}"
    EOF

    gcloud run deploy ${{ env.BACKEND_SERVICE }} \
      --image=${{ env.ARTIFACT_REGISTRY }}/backend:${{ github.sha }} \
      --region=${{ env.GCP_REGION }} \
      --platform=managed \
      --env-vars-file=/tmp/backend-env-vars.yaml \
      --quiet
```

**⚠️ PROBLEM:** This configuration is **incomplete**. It's missing critical flags.

---

## What Needs to Be Done

### **🔴 IMMEDIATE (Today) - Fix Production**

**Task:** Manually set ALLOWED_ORIGINS in production backend

**Method 1: GCP Console (Recommended)**
1. Go to: https://console.cloud.google.com/run?project=ytgrs-464303
2. Click on `ai-resume-review-v2-backend-prod`
3. Click **"EDIT & DEPLOY NEW REVISION"**
4. Go to **"Variables & Secrets"** tab
5. Find existing `ALLOWED_ORIGINS` or click **"+ ADD VARIABLE"**
6. Set value to:
   ```
   https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app,https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app,https://airesumereview.com,https://www.airesumereview.com,https://api.airesumereview.com
   ```
7. Click **"DEPLOY"**
8. Wait 2-3 minutes for deployment
9. Test login at: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app

**Method 2: Command Line**
```bash
# Create YAML file
cat > /tmp/prod-cors.yaml <<'EOF'
ALLOWED_ORIGINS: "https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app,https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app,https://airesumereview.com,https://www.airesumereview.com,https://api.airesumereview.com"
EOF

# Update service (THIS WILL UPDATE OTHER ENV VARS TOO - BE CAREFUL)
gcloud run services update ai-resume-review-v2-backend-prod \
  --region=us-central1 \
  --update-env-vars ALLOWED_ORIGINS="https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app,https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app,https://airesumereview.com,https://www.airesumereview.com,https://api.airesumereview.com"
```

**⚠️ WARNING:** Method 2 might fail due to gcloud comma parsing issues. Use GCP Console instead.

**Repeat for Staging:**
```
https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app,https://ai-resume-review-v2-backend-staging-wnjxxf534a-uc.a.run.app,http://localhost:3000,http://localhost:8000
```

**Estimated Time:** 10-15 minutes
**Risk:** Low (only updates one environment variable)

---

### **🟡 NEXT SPRINT - Complete GitHub Actions Workflows**

**Task:** Add complete Cloud Run configuration to workflows

**Problem:** Current workflows only set `--env-vars-file` but miss critical configuration:

**Missing Configuration:**
- Cloud SQL instance connection
- Service account
- VPC connector
- Secrets (DB_PASSWORD, SECRET_KEY, OPENAI_API_KEY)
- Other environment variables (DB_HOST, DB_NAME, DB_USER, etc.)
- Resource limits (memory, CPU, concurrency, timeout)
- Min/max instances

**Solution:** Read full configuration from `config/environments.yml`

**Files to Update:**
1. `.github/workflows/staging.yml` (Deploy Backend step, lines 151-171)
2. `.github/workflows/production.yml` (Deploy Backend step, lines 97-118)

**Required Changes:**

```yaml
- name: Deploy Backend to Staging
  run: |
    # Read all configuration from environments.yml
    CORS_ORIGINS=$(yq eval '.staging.cors.allowed_origins | join(",")' config/environments.yml)
    SERVICE_ACCOUNT=$(yq eval '.staging.backend.service_account' config/environments.yml)
    VPC_CONNECTOR=$(yq eval '.staging.network.vpc_connector' config/environments.yml)
    SQL_INSTANCE=$(yq eval '.staging.database.instance_name' config/environments.yml)
    DB_NAME=$(yq eval '.staging.database.database_name' config/environments.yml)
    DB_USER=$(yq eval '.staging.database.user' config/environments.yml)
    MEMORY=$(yq eval '.staging.backend.memory' config/environments.yml)
    CPU=$(yq eval '.staging.backend.cpu' config/environments.yml)
    MIN_INSTANCES=$(yq eval '.staging.backend.min_instances' config/environments.yml)
    MAX_INSTANCES=$(yq eval '.staging.backend.max_instances' config/environments.yml)
    TIMEOUT=$(yq eval '.staging.backend.timeout' config/environments.yml)
    CONCURRENCY=$(yq eval '.staging.backend.concurrency' config/environments.yml)

    # Get secret names
    SECRET_DB_PASSWORD=$(yq eval '.staging.secrets.db_password' config/environments.yml)
    SECRET_JWT_KEY=$(yq eval '.staging.secrets.jwt_secret_key' config/environments.yml)
    SECRET_OPENAI_KEY=$(yq eval '.staging.secrets.openai_api_key' config/environments.yml)

    # Create env vars file
    cat > /tmp/backend-env-vars.yaml <<EOF
    ALLOWED_ORIGINS: "${CORS_ORIGINS}"
    EOF

    # Deploy with complete configuration
    gcloud run deploy ${{ env.BACKEND_SERVICE }} \
      --image=${{ env.ARTIFACT_REGISTRY }}/backend:${{ github.sha }} \
      --region=${{ env.GCP_REGION }} \
      --platform=managed \
      --service-account="${SERVICE_ACCOUNT}" \
      --vpc-connector="${VPC_CONNECTOR}" \
      --vpc-egress=private-ranges-only \
      --add-cloudsql-instances="${{ env.GCP_PROJECT_ID }}:${{ env.GCP_REGION }}:${SQL_INSTANCE}" \
      --set-secrets="DB_PASSWORD=${SECRET_DB_PASSWORD}:latest,SECRET_KEY=${SECRET_JWT_KEY}:latest,OPENAI_API_KEY=${SECRET_OPENAI_KEY}:latest" \
      --set-env-vars="DB_HOST=/cloudsql/${{ env.GCP_PROJECT_ID }}:${{ env.GCP_REGION }}:${SQL_INSTANCE},DB_PORT=5432,DB_NAME=${DB_NAME},DB_USER=${DB_USER},PROJECT_ID=${{ env.GCP_PROJECT_ID }},ENVIRONMENT=staging,REDIS_HOST=none" \
      --env-vars-file=/tmp/backend-env-vars.yaml \
      --memory="${MEMORY}" \
      --cpu="${CPU}" \
      --min-instances="${MIN_INSTANCES}" \
      --max-instances="${MAX_INSTANCES}" \
      --concurrency="${CONCURRENCY}" \
      --timeout="${TIMEOUT}" \
      --allow-unauthenticated \
      --quiet
```

**Estimated Time:** 2-3 hours (including testing)
**Risk:** Medium (requires careful testing in staging first)

---

## Technical Context

### **Why the Current Approach Fails**

**The Issue with `--env-vars-file`:**

When you use `gcloud run deploy --env-vars-file=file.yaml`, it **REPLACES** all environment variables, not merges them.

**Current workflow:**
```yaml
gcloud run deploy ... --env-vars-file=/tmp/backend-env-vars.yaml
```

This file only contains:
```yaml
ALLOWED_ORIGINS: "..."
```

**Result:** All other environment variables are removed, including database configuration, which causes:
```
ERROR: PostgreSQL not available after 30 attempts
Container called exit(1)
```

**The Fix:**

Use `--env-vars-file` together with `--set-env-vars` and other flags:
```yaml
gcloud run deploy ... \
  --set-env-vars="DB_HOST=...,DB_NAME=..." \     # Standard env vars
  --set-secrets="DB_PASSWORD=...,SECRET_KEY=..." \  # Secrets from Secret Manager
  --env-vars-file=/tmp/backend-env-vars.yaml \   # Just ALLOWED_ORIGINS
  --add-cloudsql-instances="..." \               # Database connection
  --service-account="..." \                      # IAM
  --vpc-connector="..."                          # Networking
```

### **Why gcloud Has Trouble with CORS URLs**

CORS URLs contain special characters:
- `,` (commas) - gcloud treats these as field separators
- `:` (colons) - part of URL scheme
- `/` (slashes) - path separators

When you try:
```bash
--update-env-vars=ALLOWED_ORIGINS="https://example.com,https://another.com"
```

gcloud interprets this as:
- Key 1: `ALLOWED_ORIGINS`
- Value 1: `"https` (incomplete!)
- Error: Bad syntax

**Solution:** Use `--env-vars-file` with YAML format, which properly handles special characters.

---

## Step-by-Step Resolution Guide

### **Phase 1: Immediate Production Fix** (Today)

**Goal:** Get production working with manual CORS configuration

1. **Backup current configuration** (safety):
   ```bash
   gcloud run services describe ai-resume-review-v2-backend-prod \
     --region=us-central1 \
     --format=yaml > /tmp/prod-backup.yaml
   ```

2. **Update ALLOWED_ORIGINS via GCP Console:**
   - Follow steps in "IMMEDIATE" section above
   - Use GCP Console web UI (safest method)

3. **Verify deployment:**
   ```bash
   # Check service is healthy
   curl -s https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/health

   # Should return: {"status":"healthy",...}
   ```

4. **Test CORS:**
   ```bash
   # Test CORS preflight
   curl -X OPTIONS \
     -H "Origin: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app" \
     -H "Access-Control-Request-Method: POST" \
     -i https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/api/v1/auth/login

   # Should see: access-control-allow-origin header
   ```

5. **Test login in browser:**
   - Go to: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app
   - Open DevTools Console
   - Try to login
   - Should NOT see CORS error

6. **Repeat for staging:**
   - Service: `ai-resume-review-v2-backend-staging`
   - URL: from `config/environments.yml`

7. **Document manual change:**
   - Add note to README.md about manual CORS setup
   - Create ticket to automate this

**Success Criteria:**
- ✅ Production login works without CORS errors
- ✅ Staging login works without CORS errors
- ✅ No other functionality broken

---

### **Phase 2: Fix GitHub Actions Workflows** (Next Sprint)

**Goal:** Complete automation for smooth CI/CD

1. **Create feature branch:**
   ```bash
   git checkout -b fix/complete-cors-deployment
   ```

2. **Update `.github/workflows/staging.yml`:**
   - Add all configuration reads from `config/environments.yml`
   - Include complete `gcloud run deploy` command
   - See example in "NEXT SPRINT" section above

3. **Update `.github/workflows/production.yml`:**
   - Same changes as staging
   - Use `.production.*` paths in config

4. **Update `scripts/gcp/deploy/deploy.sh`:**
   - Already has the env-vars-file approach
   - Verify it includes all necessary flags
   - Test with: `./scripts/gcp/deploy/deploy.sh --dry-run`

5. **Test in staging:**
   ```bash
   # Push to feature branch
   git push origin fix/complete-cors-deployment

   # Manually trigger staging workflow to test
   gh workflow run staging.yml --ref fix/complete-cors-deployment

   # Monitor deployment
   gh run watch
   ```

6. **Verify staging deployment:**
   - Check Cloud Run logs for errors
   - Test backend health endpoint
   - Test CORS with curl
   - Test login in browser
   - Check all environment variables are set:
     ```bash
     gcloud run services describe ai-resume-review-v2-backend-staging \
       --region=us-central1 \
       --format="value(spec.template.spec.containers[0].env)"
     ```

7. **Merge to main:**
   ```bash
   git checkout main
   git merge fix/complete-cors-deployment
   git push origin main
   ```

8. **Verify auto-deployment to staging:**
   - Push should trigger automatic staging deployment
   - Monitor at: https://github.com/stellar-aiz/ai-resume-review-v2/actions

9. **Deploy to production:**
   - Go to: https://github.com/stellar-aiz/ai-resume-review-v2/actions/workflows/production.yml
   - Click "Run workflow"
   - Select main branch
   - Use `staging-latest` backend image tag
   - Monitor deployment

10. **Verify production:**
    - Test backend health
    - Test CORS
    - Test login
    - Verify all environment variables

**Success Criteria:**
- ✅ Staging deploys automatically on push to main
- ✅ Production deploys successfully via manual trigger
- ✅ CORS works in both environments
- ✅ No manual configuration needed
- ✅ All config comes from `config/environments.yml`

---

### **Phase 3: Validation & Documentation** (After deployment works)

1. **End-to-end testing:**
   - Test full user flow (register, login, upload, analyze)
   - Test in multiple browsers
   - Test CORS from different origins

2. **Update documentation:**
   - Update CLAUDE.md with complete deployment instructions
   - Update README.md with CORS configuration notes
   - Add troubleshooting section for CORS issues

3. **Create runbook:**
   - Document how to add new CORS origins
   - Document how to troubleshoot CORS errors
   - Document rollback procedure

4. **Clean up:**
   - Remove this handover document once complete
   - Archive deployment logs
   - Update project status

---

## Files Modified

### **Configuration**
- ✅ `config/environments.yml` - Added CORS configuration sections

### **Backend Code**
- ✅ `backend/app/main.py` - Dynamic CORS loading from environment variable
- ✅ `backend/.env.example` - Documented ALLOWED_ORIGINS variable

### **Local Development**
- ✅ `docker-compose.dev.yml` - Added ALLOWED_ORIGINS to backend environment

### **Deployment**
- ⚠️ `.github/workflows/staging.yml` - Updated but incomplete
- ⚠️ `.github/workflows/production.yml` - Updated but incomplete
- ✅ `scripts/lib/load-config.sh` - Added ALLOWED_ORIGINS export
- ⚠️ `scripts/gcp/deploy/deploy.sh` - Updated with env-vars-file approach

### **Documentation**
- ✅ `CLAUDE.md` - Added CORS Configuration section
- ✅ `README.md` - Added GitHub Actions status URL
- ✅ `HANDOVER_CORS_IMPLEMENTATION.md` - This document

### **Git History**
```bash
# View commits related to CORS implementation
git log --oneline --grep="CORS\|cors" --all

# Latest commits:
# d33de62 fix: implement env-vars-file approach for CORS configuration
# 61f5bcd fix: use gcloud ^@^ delimiter syntax for ALLOWED_ORIGINS
# b08e0b4 fix: properly escape ALLOWED_ORIGINS in gcloud deploy command
# 1a45b19 fix: implement dynamic CORS configuration from environment variables
```

---

## Testing Checklist

### **Local Development Testing**
- [ ] `./scripts/docker/dev.sh up` - All services start
- [ ] Backend shows CORS origins in logs: `CORS enabled for X origins`
- [ ] Frontend can communicate with backend (no CORS errors)
- [ ] Login works at http://localhost:3000

### **Staging Testing**
- [ ] GitHub Actions workflow completes successfully
- [ ] Backend service is healthy: `curl https://ai-resume-review-v2-backend-staging-wnjxxf534a-uc.a.run.app/health`
- [ ] CORS headers present in response
- [ ] Frontend can login without CORS errors
- [ ] Cloud Run environment variables are correct:
  ```bash
  gcloud run services describe ai-resume-review-v2-backend-staging \
    --region=us-central1 --format="value(spec.template.spec.containers[0].env)" \
    | grep ALLOWED_ORIGINS
  ```

### **Production Testing**
- [ ] Production workflow completes successfully
- [ ] Backend health check passes
- [ ] CORS headers include correct origins
- [ ] Login works at https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app
- [ ] No CORS errors in browser console
- [ ] File upload works
- [ ] Resume analysis works

### **CORS Specific Tests**
```bash
# Test staging CORS
curl -X OPTIONS \
  -H "Origin: https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i https://ai-resume-review-v2-backend-staging-wnjxxf534a-uc.a.run.app/api/v1/auth/login

# Should see:
# access-control-allow-origin: https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app
# access-control-allow-methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
# access-control-allow-credentials: true

# Test production CORS
curl -X OPTIONS \
  -H "Origin: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/api/v1/auth/login

# Test with unauthorized origin (should be blocked)
curl -X OPTIONS \
  -H "Origin: https://malicious-site.com" \
  -H "Access-Control-Request-Method: POST" \
  -i https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/api/v1/auth/login

# Should see: Disallowed CORS origin (or no access-control-allow-origin header)
```

---

## Rollback Plan

### **If Manual CORS Update Breaks Production:**

1. **Quick rollback via GCP Console:**
   - Go to: https://console.cloud.google.com/run?project=ytgrs-464303
   - Click on `ai-resume-review-v2-backend-prod`
   - Click **"REVISIONS"** tab
   - Find previous working revision
   - Click **"..."** → **"MANAGE TRAFFIC"**
   - Route 100% traffic to old revision

2. **Or rollback via command:**
   ```bash
   # List revisions
   gcloud run revisions list \
     --service=ai-resume-review-v2-backend-prod \
     --region=us-central1

   # Route traffic to previous revision
   gcloud run services update-traffic ai-resume-review-v2-backend-prod \
     --region=us-central1 \
     --to-revisions=PREVIOUS_REVISION=100
   ```

### **If GitHub Actions Deployment Fails:**

1. **Deployment will automatically fail** - no impact to running services

2. **Previous revision continues serving traffic**

3. **To investigate:**
   ```bash
   # Check workflow logs
   gh run view WORKFLOW_RUN_ID --log

   # Check Cloud Run deployment logs
   gcloud logging read "resource.type=cloud_run_revision" --limit=50
   ```

4. **Fix and retry:**
   - Fix the workflow configuration
   - Commit and push
   - Deployment will retry automatically

### **If Complete Failure:**

**Nuclear option** - Redeploy from known good state:

```bash
# Get last known good image
LAST_GOOD_IMAGE="us-central1-docker.pkg.dev/ytgrs-464303/ai-resume-review-v2/backend:staging-latest"

# Deploy manually with minimal config
gcloud run deploy ai-resume-review-v2-backend-prod \
  --image="${LAST_GOOD_IMAGE}" \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated

# Then set ALLOWED_ORIGINS via GCP Console
```

---

## References

### **URLs**
- **Production Frontend:** https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app
- **Production Backend:** https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app
- **Staging Frontend:** https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app
- **Staging Backend:** https://ai-resume-review-v2-backend-staging-wnjxxf534a-uc.a.run.app
- **GitHub Actions:** https://github.com/stellar-aiz/ai-resume-review-v2/actions
- **GCP Console (Cloud Run):** https://console.cloud.google.com/run?project=ytgrs-464303
- **GCP Console (Logs):** https://console.cloud.google.com/logs?project=ytgrs-464303

### **Documentation**
- **Project README:** [README.md](README.md)
- **Claude Instructions:** [CLAUDE.md](CLAUDE.md)
- **Config Documentation:** [config/README.md](config/README.md)
- **Terraform Documentation:** [terraform/README.md](terraform/README.md)

### **Key Configuration Files**
- **Environments Config:** `config/environments.yml`
- **Backend CORS Code:** `backend/app/main.py` (lines 139-160)
- **Docker Compose:** `docker-compose.dev.yml`
- **Staging Workflow:** `.github/workflows/staging.yml`
- **Production Workflow:** `.github/workflows/production.yml`
- **Deployment Script:** `scripts/gcp/deploy/deploy.sh`
- **Config Loader:** `scripts/lib/load-config.sh`

### **GCP Resources**
```bash
# Project
PROJECT_ID=ytgrs-464303
REGION=us-central1

# Services
BACKEND_STAGING=ai-resume-review-v2-backend-staging
BACKEND_PROD=ai-resume-review-v2-backend-prod
FRONTEND_STAGING=ai-resume-review-v2-frontend-staging
FRONTEND_PROD=ai-resume-review-v2-frontend-prod

# Database
SQL_STAGING=ai-resume-review-v2-db-staging
SQL_PROD=ai-resume-review-v2-db-prod

# Secrets
db-password-staging
db-password-prod
jwt-secret-key-staging
jwt-secret-key-prod
openai-api-key-prod
```

### **Helpful Commands**
```bash
# Check service status
gcloud run services list --project=ytgrs-464303

# View service details
gcloud run services describe SERVICE_NAME --region=us-central1

# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=SERVICE_NAME" --limit=50

# List revisions
gcloud run revisions list --service=SERVICE_NAME --region=us-central1

# Check environment variables
gcloud run services describe SERVICE_NAME --region=us-central1 --format="value(spec.template.spec.containers[0].env)"

# GitHub CLI commands
gh run list --workflow=staging.yml --limit=5
gh run view RUN_ID
gh run watch RUN_ID
```

---

## Contact & Support

### **Team**
- **Project Lead:** [Name]
- **Backend Engineer:** [Name]
- **DevOps Engineer:** [Name]
- **QA Engineer:** [Name]

### **Communication Channels**
- **Slack:** #ai-resume-review-v2
- **Email:** team@example.com
- **Incidents:** [PagerDuty/Incident tracking tool]

### **Escalation Path**
1. Check this handover document
2. Check CLAUDE.md for architecture details
3. Check GitHub Actions logs
4. Check Cloud Run logs in GCP Console
5. Ask in Slack #ai-resume-review-v2
6. Escalate to DevOps team

---

## Appendix: Error Messages & Solutions

### **Error: "Disallowed CORS origin"**
**Symptom:** Browser console shows CORS policy error
**Cause:** ALLOWED_ORIGINS not set or has wrong URL
**Solution:** Update ALLOWED_ORIGINS environment variable in Cloud Run

### **Error: "Container failed to start"**
**Symptom:** Deployment fails, Cloud Run shows container exit(1)
**Cause:** Missing database configuration or other env vars
**Solution:** Ensure all required env vars are set (DB_HOST, DB_NAME, etc.)

### **Error: "PostgreSQL not available"**
**Symptom:** Backend logs show database connection failures
**Cause:** Missing Cloud SQL instance configuration
**Solution:** Add `--add-cloudsql-instances` flag to deployment

### **Error: "Bad syntax for dict arg"**
**Symptom:** gcloud command fails with parsing error
**Cause:** Commas in URL are treated as field separators
**Solution:** Use `--env-vars-file` instead of `--update-env-vars`

### **Error: "Revision is not ready"**
**Symptom:** Deployment fails after "Creating Revision..." step
**Cause:** Container won't start (check logs for actual reason)
**Solution:** Check Cloud Run logs, fix underlying issue

---

## Timeline

| Date | Event | Status |
|------|-------|--------|
| 2025-10-12 | Discovered CORS error in production | ❌ Issue |
| 2025-10-12 | Implemented dynamic CORS architecture | ✅ Done |
| 2025-10-12 | Updated all code and config files | ✅ Done |
| 2025-10-12 | Attempted deployment via GitHub Actions | ❌ Failed |
| 2025-10-12 | Identified incomplete workflow configuration | 🔍 Root cause |
| 2025-10-12 | Created handover document | ✅ Done |
| TBD | Manual CORS fix in production | ⏳ Pending |
| TBD | Complete GitHub Actions workflows | ⏳ Pending |
| TBD | Test end-to-end CI/CD | ⏳ Pending |
| TBD | Close CORS implementation task | ⏳ Pending |

---

## Success Criteria

### **Phase 1 Complete When:**
- [ ] Production login works without CORS errors
- [ ] Staging login works without CORS errors
- [ ] Manual CORS configuration documented
- [ ] Ticket created for automation

### **Phase 2 Complete When:**
- [ ] GitHub Actions staging workflow deploys successfully
- [ ] GitHub Actions production workflow deploys successfully
- [ ] All configuration read from `config/environments.yml`
- [ ] No manual configuration needed
- [ ] Full CI/CD pipeline working

### **Phase 3 Complete When:**
- [ ] End-to-end testing passed
- [ ] Documentation updated
- [ ] Runbook created
- [ ] Handover document archived
- [ ] Team trained on new process

---

## Final Notes

**Good Luck!** 🚀

This implementation is 80% complete. The architecture is solid, the code is ready, and the approach is sound. The remaining work is to complete the deployment automation.

**Key Takeaway:** Always verify the complete Cloud Run configuration before changing deployment scripts. The `--env-vars-file` flag replaces variables, so you need to include all necessary configuration flags in the deployment command.

**Questions?** Check CLAUDE.md, ping the team in Slack, or refer to this document.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-12
**Next Review:** After Phase 1 completion
**Status:** 🟡 Active Handover
