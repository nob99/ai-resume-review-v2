# Deploy Scripts - Phase 3

**Status**: 🚀 **READY TO USE**

This folder contains scripts for deploying the AI Resume Review application to Google Cloud Run.

---

## 🚀 Quick Start

Run scripts in this order:

```bash
./1-verify-prerequisites.sh   # Verify everything is ready
./2-run-migrations.sh         # Initialize database schema
./3-deploy-backend.sh         # Deploy backend to Cloud Run
./4-deploy-frontend.sh        # Deploy frontend to Cloud Run
```

**Or run all at once**:

```bash
./deploy-all.sh              # Runs 1-4 with confirmations
```

---

## 📜 Script Reference

### 1-verify-prerequisites.sh

**Purpose**: Verify all prerequisites before deployment

**What it checks**:
- ✅ Development tools (gcloud, docker)
- ✅ GCP authentication and project settings
- ✅ Infrastructure (VPC, Cloud SQL, Secrets, Artifact Registry)
- ✅ Service accounts and IAM permissions
- ✅ Application files (Dockerfiles, migrations)
- ✅ Required GCP APIs

**Run time**: ~1 minute

**Safe to run**: Yes (read-only checks)

**Example**:
```bash
./1-verify-prerequisites.sh
```

**Expected output**: List of all checks with ✓ or ✗

---

### 2-run-migrations.sh

**Purpose**: Run database migrations via Cloud SQL Proxy

**What it does**:
- Downloads Cloud SQL Proxy (if not exists)
- Connects to Cloud SQL database
- Runs Alembic migrations
- Verifies migration status

**Run time**: ~5 minutes (first time), ~1 minute (subsequent)

**Safe to run**: Yes (Alembic migrations are versioned)

**Prerequisites**:
- Cloud SQL instance must be RUNNABLE
- Database password must be in Secret Manager
- Alembic migrations must exist in backend/alembic/versions/

**Example**:
```bash
./2-run-migrations.sh
```

**Expected output**:
```
✓ Cloud SQL Proxy downloaded
✓ Connecting to: ytgrs-464303:us-central1:ai-resume-review-v2-db-prod
✓ Running migrations...
✓ Database revision: abc123def456
```

---

### 3-deploy-backend.sh

**Purpose**: Deploy backend to Cloud Run

**What it does**:
1. Builds backend Docker image (linux/amd64)
2. Pushes image to Artifact Registry
3. Creates/updates VPC Connector (if needed)
4. Deploys to Cloud Run with:
   - Secrets mounted from Secret Manager
   - Cloud SQL connection
   - VPC network access
   - Min instances: 0 (cost optimized)
5. Tests health endpoint

**Run time**: ~15-20 minutes (first time), ~10 minutes (subsequent)

**Safe to run**: Yes (Cloud Run keeps previous revisions)

**Configuration**:
- Memory: 2GB
- CPU: 2
- Min instances: 0 (scales to zero)
- Max instances: 5
- Timeout: 600s

**Example**:
```bash
./3-deploy-backend.sh
```

**Expected output**:
```
✓ Building Docker image...
✓ Pushing to Artifact Registry...
✓ Deploying to Cloud Run...
✓ Health check passed!
  
Backend URL: https://ai-resume-review-v2-backend-prod-xxxxx-uc.a.run.app
```

---

### 4-deploy-frontend.sh

**Purpose**: Deploy frontend to Cloud Run

**What it does**:
1. Gets backend URL from deployed service
2. Builds frontend Docker image with backend URL
3. Pushes image to Artifact Registry
4. Deploys to Cloud Run
5. Tests frontend accessibility

**Run time**: ~10-15 minutes (first time), ~5-10 minutes (subsequent)

**Safe to run**: Yes (Cloud Run keeps previous revisions)

**Prerequisites**:
- Backend must be deployed first
- Backend must be healthy

**Configuration**:
- Memory: 512MB
- CPU: 1
- Min instances: 0 (scales to zero)
- Max instances: 5
- Timeout: 300s

**Example**:
```bash
./4-deploy-frontend.sh
```

**Expected output**:
```
✓ Backend URL: https://...
✓ Building Docker image...
✓ Pushing to Artifact Registry...
✓ Deploying to Cloud Run...
✓ Frontend is accessible!

Frontend URL: https://ai-resume-review-v2-frontend-prod-xxxxx-uc.a.run.app
```

---

### deploy-all.sh

**Purpose**: Run complete deployment pipeline

**What it does**:
- Runs scripts 1-4 in sequence
- Asks for confirmation between steps
- Stops if any step fails

**Run time**: ~30-40 minutes total

**Safe to run**: Yes (asks for confirmation at each step)

**Example**:
```bash
./deploy-all.sh
```

**You can skip confirmations** by pressing Enter (defaults to "yes" for most prompts)

---

## 🔍 Common Scenarios

### First-Time Deployment

```bash
./1-verify-prerequisites.sh   # Check everything
# Fix any issues reported above
./2-run-migrations.sh         # Set up database
./3-deploy-backend.sh         # Deploy backend
./4-deploy-frontend.sh        # Deploy frontend
```

### Update Code (Backend Only)

```bash
./3-deploy-backend.sh         # Redeploy backend
```

### Update Code (Frontend Only)

```bash
./4-deploy-frontend.sh        # Redeploy frontend
```

### Update Both

```bash
./3-deploy-backend.sh
./4-deploy-frontend.sh
```

### Database Schema Change

```bash
# 1. Create migration locally:
cd backend/
alembic revision -m "add new table"
# Edit migration file
git add alembic/versions/
git commit -m "Add migration"

# 2. Deploy:
cd ../scripts/gcp/deploy/
./2-run-migrations.sh         # Apply migration
./3-deploy-backend.sh         # Deploy backend (if code changed)
```

---

## 🐛 Troubleshooting

### Script 1 Fails

**Issue**: Prerequisites check fails

**Solutions**:
- Check error messages - they tell you exactly what's missing
- Most common: VPC Connector not READY → wait 5 minutes
- If Cloud SQL is not RUNNABLE → check GCP Console

### Script 2 Fails

**Issue**: Migration fails

**Solutions**:
- Check if Cloud SQL instance is running: `gcloud sql instances list`
- Check if secrets exist: `gcloud secrets list`
- Check migration SQL: `cd backend && alembic upgrade head --sql`
- Check database connection manually via Cloud SQL Proxy

### Script 3 Fails

**Issue**: Backend deployment fails

**Common causes**:
1. Docker build error → Check Dockerfile syntax
2. Permission denied → Check service account IAM roles
3. Health check fails → Check backend logs
4. VPC connector issue → Will be created automatically, wait 5 mins

**Debug**:
```bash
# Check Cloud Run logs
gcloud logging read "resource.labels.service_name=ai-resume-review-v2-backend-prod" --limit=50

# Check service status
gcloud run services describe ai-resume-review-v2-backend-prod --region=us-central1
```

### Script 4 Fails

**Issue**: Frontend deployment fails

**Common causes**:
1. Backend not deployed → Run script 3 first
2. Backend unhealthy → Check backend logs
3. Docker build error → Check Dockerfile

**Debug**:
```bash
# Check frontend logs
gcloud logging read "resource.labels.service_name=ai-resume-review-v2-frontend-prod" --limit=50
```

---

## 📊 Cost Impact

Each deployment:
- **One-time cost**: ~$0 (just compute time for builds)
- **Ongoing cost**: $45-65/month (Cloud Run + Cloud SQL + VPC)

With `min-instances=0`, services scale to zero when not in use, saving costs during low traffic.

---

## ✅ Success Criteria

**Deployment is successful when**:
1. All 4 scripts complete without errors
2. Backend health endpoint returns 200 OK
3. Frontend loads in browser
4. Full user flow works (register → login → upload)

**Test with**:
```bash
cd ../verify/
./health-check.sh           # Quick test
./integration-test.sh       # Full test
```

---

## 🔗 Related Documentation

- [../README.md](../README.md) - Main deployment guide
- [../../../PHASE3_DEPLOYMENT_GUIDE.md](../../../PHASE3_DEPLOYMENT_GUIDE.md) - Detailed Phase 3 guide
- [../verify/README.md](../verify/README.md) - Testing guide

---

**Last Updated**: 2025-10-07
