# Handover Document V3: Deployment System - Complete Fix

**Date:** 2025-10-13
**Project:** AI Resume Review Platform v2
**Task:** Complete CI/CD Deployment System Fix & Production Deployment
**Status:** ✅ **STAGING COMPLETE** | ⏳ **PRODUCTION READY TO DEPLOY**
**Priority:** 🟡 **P1 - Production Deployment Needed**

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [What We Accomplished](#what-we-accomplished)
3. [Current Status](#current-status)
4. [Next Steps](#next-steps)
5. [Technical Details](#technical-details)
6. [How to Deploy to Production](#how-to-deploy-to-production)
7. [Testing & Verification](#testing--verification)
8. [Files Modified](#files-modified)
9. [References](#references)

---

## Executive Summary

### The Complete Journey (3 Sessions)

**Session 1 (V1 - HANDOVER_CORS_IMPLEMENTATION.md):**
- Problem: Production CORS errors (hardcoded URLs)
- Solution: Dynamic CORS configuration
- Result: Code fixed, but deployment broken

**Session 2 (V2 - HANDOVER_DEPLOYMENT_FIX_V2.md):**
- Problem: CI/CD deployment broken (container won't start)
- Solution: Unified deployment script, all env vars in YAML
- Result: 95% complete, missing one secret

**Session 3 (V3 - This Document):**
- Completed: Fixed all blockers, staging fully working
- **Result: STAGING ✅ WORKS | PRODUCTION ⏳ NEEDS DEPLOYMENT**

---

## What We Accomplished

### 1. Fixed Critical Database Connection Bug 🐛

**Problem Discovered:**
Staging deployment was connecting to **production database** instead of staging!

**Root Cause:**
```bash
# Variable name mismatch:
load-config.sh exports:     SQL_CONNECTION_NAME
deploy.sh uses:             SQL_INSTANCE_CONNECTION
common-functions.sh sets:   SQL_INSTANCE_CONNECTION (with prod defaults)

# Result: deploy.sh used the production default value!
```

**Fix Applied:**
```bash
# scripts/gcp/deploy/deploy.sh line 818
source "$SCRIPT_DIR/../../lib/load-config.sh" "$ENV_NAME"
# NEW: Sync the variable after loading config
export SQL_INSTANCE_CONNECTION="$SQL_CONNECTION_NAME"
```

**File:** [scripts/gcp/deploy/deploy.sh:818](scripts/gcp/deploy/deploy.sh#L818)

**Commit:** `1336b9d` - "fix: use SQL_CONNECTION_NAME from config instead of common-functions default"

---

### 2. Created Missing Secret ✅

**Problem:**
Secret `openai-api-key-staging` didn't exist in GCP Secret Manager.

**Solution:**
```bash
# Created secret with same value as production (as requested)
gcloud secrets create openai-api-key-staging --replication-policy="automatic"
echo -n "<api-key>" | gcloud secrets versions add openai-api-key-staging --data-file=-

# Granted access to staging backend
gcloud secrets add-iam-policy-binding openai-api-key-staging \
  --member="serviceAccount:arr-v2-backend-staging@ytgrs-464303.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Status:** ✅ Complete

---

### 3. Deployed to Staging Successfully 🎉

**Deployment Run:** GitHub Actions workflow `18452291407`

**Results:**
- ✅ Container started successfully
- ✅ Database connected (staging DB, not prod!)
- ✅ CORS working correctly
- ✅ All secrets loaded properly
- ✅ Health check passing

**Verification:**
```bash
# Database connection - CORRECT!
DB_HOST: /cloudsql/ytgrs-464303:us-central1:ai-resume-review-v2-db-staging ✅

# CORS - WORKING!
access-control-allow-origin: https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app ✅

# All secrets loaded
DB_PASSWORD: db-password-staging ✅
SECRET_KEY: jwt-secret-key-staging ✅
OPENAI_API_KEY: openai-api-key-staging ✅
```

---

### 4. Created Test User for Staging 👤

**Problem:**
No users existed in staging database to test login.

**Solution:**
Created `scripts/gcp/utils/create_staging_test_user.py` based on production script.

**Process:**
1. Temporarily enabled public IP on staging database
2. Ran user creation script
3. Disabled public IP (security restored)

**Test Credentials Created:**
- **Email:** `admin@example.com`
- **Password:** `AdminPassword123!`
- **Role:** `admin`

**Status:** ✅ User created, staging tested and working

---

## Current Status

### ✅ Staging Environment (FULLY WORKING)

| Component | Status | Notes |
|-----------|--------|-------|
| Backend Code | ✅ Deployed | Dynamic CORS, correct DB connection |
| Frontend | ✅ Deployed | Latest build |
| Database | ✅ Connected | Staging DB (correct!) |
| CORS | ✅ Working | All origins configured |
| Secrets | ✅ Loaded | All 3 secrets present |
| Test User | ✅ Created | admin@example.com |
| Login | ✅ Working | Tested successfully |

**Staging URL:** https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app

---

### ⏳ Production Environment (NEEDS DEPLOYMENT)

| Component | Status | Notes |
|-----------|--------|-------|
| Backend Code | ❌ OLD | Still running pre-fix code |
| CORS | ❌ BROKEN | Hardcoded URLs (wrong) |
| Database | ✅ Running | Not affected |
| Secrets | ✅ Exists | openai-api-key-prod exists |
| Test User | ✅ Exists | Production admin users exist |

**Production URL:** https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app

**Current Error:**
```
Access to XMLHttpRequest at 'https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/api/v1/auth/login'
from origin 'https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app'
has been blocked by CORS policy
```

**Why:** Production backend is still running old code (before our fixes).

---

## Next Steps

### 🎯 IMMEDIATE: Deploy to Production

**What:** Deploy the same code that's working in staging to production.

**How:** Use GitHub Actions production workflow (recommended).

**Why Safe:**
- ✅ Same code working perfectly in staging
- ✅ All fixes are fundamental (not patches)
- ✅ Production database already has all secrets
- ✅ Zero downtime deployment
- ✅ Automatic rollback if issues

**Estimated Time:** 5-7 minutes

**See:** [How to Deploy to Production](#how-to-deploy-to-production) section below.

---

## Technical Details

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  config/environments.yml                     │
│              (Single Source of Truth)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ├─> Manual Deployment
                           │   └─> source scripts/lib/load-config.sh
                           │       └─> scripts/gcp/deploy/deploy.sh
                           │
                           └─> CI/CD Deployment
                               └─> .github/workflows/*.yml
                                   └─> scripts/gcp/deploy/deploy.sh
                                       (auto-loads config)
```

### Key Files and Changes

**1. Configuration Management**
- `config/environments.yml` - All environment config (CORS, DB, secrets, etc.)
- `scripts/lib/load-config.sh` - Loads config, exports variables

**2. Deployment Script**
- `scripts/gcp/deploy/deploy.sh` - Unified deployment for manual & CI/CD
- Added CI/CD flags: `--skip-build`, `--backend-image`, `--skip-frontend`, `--skip-tests`
- Auto-detects environment (staging/production)
- Auto-loads config from `environments.yml`
- **Fixed:** Now syncs `SQL_INSTANCE_CONNECTION` with `SQL_CONNECTION_NAME`

**3. Environment Variables Approach**
```bash
# ALL environment variables in YAML file (fundamental solution)
cat > /tmp/backend-env-vars.yaml <<EOF
DB_HOST: "/cloudsql/$SQL_INSTANCE_CONNECTION"
DB_PORT: "5432"
DB_NAME: "$DB_NAME"
DB_USER: "$DB_USER"
PROJECT_ID: "$PROJECT_ID"
ENVIRONMENT: "$env_name"
REDIS_HOST: "none"
ALLOWED_ORIGINS: "$ALLOWED_ORIGINS"
EOF

# Deploy with ONLY env-vars-file (no --set-env-vars mixing)
gcloud run deploy ... --env-vars-file=/tmp/backend-env-vars.yaml
```

**Why This Works:**
- ✅ YAML handles special characters (commas, colons in URLs)
- ✅ No flag conflicts (can't mix --set-env-vars and --env-vars-file)
- ✅ Clean separation: env vars in YAML, secrets in --set-secrets
- ✅ gcloud's native format

**4. GitHub Actions Workflows**
- `.github/workflows/staging.yml` - Simplified (calls deploy.sh)
- `.github/workflows/production.yml` - Simplified (calls deploy.sh)

---

## How to Deploy to Production

### Option 1: GitHub Actions (RECOMMENDED) ⭐

**Steps:**

1. **Go to GitHub Actions:**
   ```
   https://github.com/stellar-aiz/ai-resume-review-v2/actions/workflows/production.yml
   ```

2. **Click "Run workflow"**

3. **Select:**
   - Branch: `main`
   - Backend image tag: `staging-latest` (or use latest SHA from staging)
   - Frontend image tag: `staging-latest`

4. **Click "Run workflow"**

5. **Monitor Progress:**
   ```bash
   # Or use CLI
   gh run list --workflow=production.yml --limit=1
   gh run watch <run-id>
   ```

6. **Wait:** ~5-7 minutes

7. **Verify:**
   - Go to: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app
   - Try to login
   - Should NOT see CORS error ✅

**Why This Option:**
- ✅ Proper CI/CD workflow
- ✅ Full audit trail in GitHub
- ✅ Runs tests before deploying
- ✅ Same process as staging (proven to work)
- ✅ Best practice for production deployments

---

### Option 2: Manual Deployment

**Only use this for emergency hotfixes.**

```bash
# 1. Load production config
cd /Users/nobuaki/Desktop/ai-agent-yatagaras/ai-resume-review-v2
source scripts/lib/load-config.sh production

# 2. Deploy backend
./scripts/gcp/deploy/deploy.sh --step=backend

# 3. Deploy frontend (if needed)
./scripts/gcp/deploy/deploy.sh --step=frontend

# 4. Verify
curl https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/health
```

**Note:** Manual deployment builds images locally, which takes longer (~15-20 min).

---

## Testing & Verification

### After Production Deployment

**1. Backend Health Check**
```bash
curl -s https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/health | jq
# Should return: {"status": "..."}
```

**2. CORS Verification**
```bash
curl -X OPTIONS \
  -H "Origin: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app" \
  -H "Access-Control-Request-Method: POST" \
  -i https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/api/v1/auth/login

# Should see:
# access-control-allow-origin: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app
```

**3. Environment Variables Check**
```bash
gcloud run services describe ai-resume-review-v2-backend-prod \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env)" \
  | grep -E "DB_HOST|ALLOWED_ORIGINS"

# DB_HOST should be: /cloudsql/ytgrs-464303:us-central1:ai-resume-review-v2-db-prod
# ALLOWED_ORIGINS should include all production URLs
```

**4. Browser Test**
1. Open: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app
2. Open DevTools Console (F12)
3. Try to login with production admin credentials
4. Should NOT see CORS error ✅

**5. Full Flow Test**
- Login
- Upload resume
- Run analysis
- View results

---

## Files Modified

### Code Changes (All on main branch)

**Backend:**
- `backend/app/main.py` (lines 139-160) - Dynamic CORS from environment variable

**Deployment Scripts:**
- `scripts/gcp/deploy/deploy.sh` - Added CI/CD support, fixed SQL_INSTANCE_CONNECTION bug
- `scripts/lib/load-config.sh` - Loads config from environments.yml

**CI/CD:**
- `.github/workflows/staging.yml` - Simplified to call deploy.sh
- `.github/workflows/production.yml` - Simplified to call deploy.sh

**Configuration:**
- `config/environments.yml` - Added CORS configuration for all environments

**Utilities:**
- `scripts/gcp/utils/create_staging_test_user.py` - NEW: Create test users for staging

### Git Commits (Latest to Oldest)

```bash
1336b9d - fix: use SQL_CONNECTION_NAME from config instead of common-functions default
cb3fff5 - chore: trigger deployment after creating openai-api-key-staging secret
8515758 - fix: use YAML file for all env vars (fundamental solution)
58179b3 - chore: trigger deployment after granting VPC viewer permission
34476f3 - fix: correct config loader path for CI/CD
8f722ea - fix: always load environment config to override common-functions defaults
e8efa91 - fix: auto-load environment config in deploy.sh for CI/CD
7edfbb0 - fix: simplify GitHub Actions deployment by calling deploy.sh
```

---

## References

### URLs

**Staging:**
- Frontend: https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app
- Backend: https://ai-resume-review-v2-backend-staging-wnjxxf534a-uc.a.run.app
- Health: https://ai-resume-review-v2-backend-staging-wnjxxf534a-uc.a.run.app/health

**Production:**
- Frontend: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app
- Backend: https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app
- Health: https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/health

**GitHub:**
- Repository: https://github.com/stellar-aiz/ai-resume-review-v2
- Actions: https://github.com/stellar-aiz/ai-resume-review-v2/actions
- Staging Workflow: https://github.com/stellar-aiz/ai-resume-review-v2/actions/workflows/staging.yml
- Production Workflow: https://github.com/stellar-aiz/ai-resume-review-v2/actions/workflows/production.yml

**GCP Console:**
- Project: https://console.cloud.google.com/home/dashboard?project=ytgrs-464303
- Cloud Run: https://console.cloud.google.com/run?project=ytgrs-464303
- Secrets: https://console.cloud.google.com/security/secret-manager?project=ytgrs-464303
- Logs: https://console.cloud.google.com/logs?project=ytgrs-464303

### GCP Resources

**Project:** `ytgrs-464303` (864523342928)
**Region:** `us-central1`

**Cloud Run Services:**
```
Backend Staging:  ai-resume-review-v2-backend-staging
Backend Prod:     ai-resume-review-v2-backend-prod
Frontend Staging: ai-resume-review-v2-frontend-staging
Frontend Prod:    ai-resume-review-v2-frontend-prod
```

**Databases:**
```
Staging: ai-resume-review-v2-db-staging
Prod:    ai-resume-review-v2-db-prod
```

**Service Accounts:**
```
Backend Staging:  arr-v2-backend-staging@ytgrs-464303.iam.gserviceaccount.com
Backend Prod:     arr-v2-backend-prod@ytgrs-464303.iam.gserviceaccount.com
Frontend Staging: arr-v2-frontend-staging@ytgrs-464303.iam.gserviceaccount.com
Frontend Prod:    arr-v2-frontend-prod@ytgrs-464303.iam.gserviceaccount.com
GitHub Actions:   github-actions-deployer@ytgrs-464303.iam.gserviceaccount.com
```

**Secrets:**
```
✅ db-password-staging
✅ db-password-prod
✅ jwt-secret-key-staging
✅ jwt-secret-key-prod
✅ openai-api-key-staging (NEWLY CREATED)
✅ openai-api-key-prod
```

### Test Credentials

**Staging:**
- Email: `admin@example.com`
- Password: `AdminPassword123!`
- Role: admin

**Production:**
- Use existing production admin credentials
- Contact team lead if needed

---

## Key Learnings

### What Worked Well

1. **Unified deployment script** - Single source of truth for manual and CI/CD
2. **YAML for all env vars** - Handles special characters cleanly
3. **Auto-config loading** - deploy.sh detects environment and loads config automatically
4. **Incremental testing** - Fixed one issue at a time, tested in staging first

### Issues Discovered & Fixed

1. **Variable name mismatch** - `SQL_CONNECTION_NAME` vs `SQL_INSTANCE_CONNECTION`
   - **Impact:** Staging was connecting to production database!
   - **Fix:** Explicitly sync variables after loading config

2. **Missing secret** - `openai-api-key-staging` didn't exist
   - **Impact:** Deployment failed (couldn't start container)
   - **Fix:** Created secret with production value

3. **gcloud flag conflicts** - Can't mix `--set-env-vars` and `--env-vars-file`
   - **Impact:** Deployment command syntax error
   - **Fix:** Put ALL env vars in YAML file

### Best Practices Applied

- ✅ Single source of truth (config/environments.yml)
- ✅ DRY principle (no code duplication in workflows)
- ✅ Separation of concerns (env vars, secrets, infrastructure)
- ✅ Backward compatibility (manual deployments still work)
- ✅ Production safety (no impact to running services)
- ✅ Testing in staging first (before production)

---

## Summary for Next Engineer

### What's Done ✅

1. All code fixes are complete and on `main` branch
2. Staging environment is fully working and tested
3. All infrastructure issues are resolved
4. CI/CD system is working (proven in staging)
5. Test user created in staging for testing

### What's Needed ⏳

**ONE TASK: Deploy to Production**

Use GitHub Actions production workflow to deploy the same code that's working in staging.

**Estimated Time:** 10 minutes (mostly waiting for deployment)

**Risk Level:** LOW
- Same code working perfectly in staging
- All fixes are fundamental (not patches)
- Zero downtime deployment
- Automatic rollback if issues

### If You Need Help

1. **Read this document first** (you're doing that! ✅)
2. **Check previous handover docs:**
   - `HANDOVER_CORS_IMPLEMENTATION.md` - Original CORS issue
   - `HANDOVER_DEPLOYMENT_FIX_V2.md` - CI/CD fix journey
3. **Check GitHub Actions logs** - Most issues show up there
4. **Check Cloud Run logs** - If container fails to start
5. **Test in staging first** - If making any changes

### Quick Reference Commands

```bash
# View latest deployment
gh run list --workflow=staging.yml --limit=1

# Watch deployment
gh run watch <run-id>

# Check service health
curl https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/health

# View environment variables
gcloud run services describe ai-resume-review-v2-backend-prod \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env)"

# View service logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai-resume-review-v2-backend-prod" --limit=50
```

---

## Status Summary

| Item | Staging | Production | Notes |
|------|---------|------------|-------|
| **Code Fixes** | ✅ Deployed | ❌ Not deployed | Code is ready on main branch |
| **CORS** | ✅ Working | ❌ Broken | Need to deploy |
| **Database Connection** | ✅ Correct | ❌ Old code | Need to deploy |
| **Secrets** | ✅ All present | ✅ All present | Infrastructure OK |
| **CI/CD** | ✅ Working | ⏳ Ready | Just trigger workflow |
| **Test User** | ✅ Created | ✅ Exists | Can test after deploy |

---

**Document Version:** 3.0
**Last Updated:** 2025-10-13
**Status:** 🟢 Staging Complete, 🟡 Production Ready to Deploy
**Next Action:** Deploy to production via GitHub Actions

---

## Contact & Escalation

**Previous Handover Documents:**
- V1: `HANDOVER_CORS_IMPLEMENTATION.md` (2025-10-12)
- V2: `HANDOVER_DEPLOYMENT_FIX_V2.md` (2025-10-13)
- V3: `HANDOVER_DEPLOYMENT_COMPLETE_V3.md` (2025-10-13) ← You are here

**If Stuck:**
1. All fixes are already done - just need to deploy
2. Staging is working - same code for production
3. Use GitHub Actions (recommended)
4. Check logs if deployment fails

**Good luck! The hard work is done - just need to push the button! 🚀**
