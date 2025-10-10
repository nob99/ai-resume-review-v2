# GCP Deployment Scripts

**Version**: 3.0 (Refactored)
**Last Updated**: 2025-10-10
**Project**: AI Resume Review Platform v2

---

## 📁 Directory Structure

```
scripts/gcp/
├── README.md              ← You are here (navigation guide)
│
├── setup/                 ← Phase 1 & 2: One-time infrastructure setup
│   ├── README.md
│   ├── setup.sh           ✨ NEW: All-in-one setup (replaces 3 scripts)
│   └── cleanup.sh         ← Cleanup old resources (dangerous!)
│
├── deploy/                ← Phase 3: Application deployment (repeatable)
│   ├── README.md
│   └── deploy.sh          ✨ NEW: Complete deployment pipeline (replaces 5 scripts)
│
├── monitoring/            ← Cloud Monitoring setup
│   ├── README.md
│   ├── setup.sh           ✨ NEW: Complete monitoring setup (replaces 6 scripts)
│   └── verify.sh          ← Verify monitoring configuration
│
├── verify/                ← Post-deployment testing
│   ├── README.md
│   ├── health-check.sh
│   └── integration-test.sh
│
└── utils/                 ← Shared utilities
    ├── common-functions.sh
    └── rollback.sh
```

**Note:** Old scripts retained for backward compatibility (marked as deprecated).

---

## 🚀 Quick Start

### **For First-Time Deployment**

If this is your first time deploying the application:

```bash
# 1. Set up infrastructure (one-time)
cd setup/
./setup.sh                    # Complete GCP infrastructure setup
# Or step-by-step:
./setup.sh --step=project     # GCP project setup
./setup.sh --step=database    # Cloud SQL setup
./setup.sh --step=secrets     # Secrets setup

# 2. Deploy application
cd ../deploy/
./deploy.sh                   # Complete deployment pipeline
# Or step-by-step:
./deploy.sh --step=verify     # Prerequisites check
./deploy.sh --step=migrate    # Database migrations
./deploy.sh --step=backend    # Backend deployment
./deploy.sh --step=frontend   # Frontend deployment

# 3. Set up monitoring (recommended)
cd ../monitoring/
./setup.sh                    # Complete monitoring setup
./verify.sh                   # Verify setup
```

### **For Subsequent Deployments**

If infrastructure is already set up and you just want to redeploy:

```bash
# Quick redeploy
cd deploy/
./deploy.sh                   # Complete deployment pipeline

# Or deploy specific components:
./deploy.sh --step=backend    # Backend only
./deploy.sh --step=frontend   # Frontend only

# Skip health checks for faster deployment:
./deploy.sh --skip-tests
```

---

## 📚 Folder Descriptions

### **setup/** - Infrastructure Setup (One-Time)

**Status**: ✅ **COMPLETED** (Phase 1 & 2)

Contains scripts for setting up GCP infrastructure. These scripts are **run once** when first setting up the project.

**What's included**:
- Service accounts and IAM roles
- VPC network and subnets
- Cloud SQL database
- Secrets in Secret Manager
- Artifact Registry

**When to use**: Only when setting up a new GCP project or resetting infrastructure.

📖 [Read setup/README.md](setup/README.md) for details

---

### **deploy/** - Application Deployment (Repeatable)

**Status**: 🚀 **READY TO USE** (Phase 3)

Contains scripts for deploying the application to Cloud Run. These scripts can be **run repeatedly** whenever you want to deploy updates.

**What's included**:
- Prerequisites verification
- Database migrations
- Backend deployment
- Frontend deployment
- All-in-one deployment script

**When to use**: Every time you want to deploy code changes.

📖 [Read deploy/README.md](deploy/README.md) for step-by-step guide

---

### **verify/** - Testing & Verification

**Status**: ✅ **READY TO USE**

Contains scripts for testing deployed services.

**What's included**:
- Health check (quick smoke test)
- Integration test (full user flow)

**When to use**: After deployment to verify everything works.

📖 [Read verify/README.md](verify/README.md) for testing guide

---

### **utils/** - Shared Utilities

**Status**: ✅ **READY TO USE**

Contains shared utilities used by other scripts.

**What's included**:
- `common-functions.sh` - Shared bash functions (sourced by all scripts)
- `rollback.sh` - Emergency rollback script

**When to use**:
- `common-functions.sh` is automatically sourced by other scripts
- `rollback.sh` when you need to rollback a failed deployment

---

## 📖 Common Tasks

### Deploy Application

```bash
cd deploy/
./deploy.sh                   # Complete deployment
./deploy.sh --dry-run         # Preview what would happen
./deploy.sh --skip-tests      # Faster deployment
```

### Set Up Monitoring

```bash
cd monitoring/
./setup.sh                    # Complete monitoring setup
./setup.sh --step=alerts      # Just alerts
./verify.sh                   # Verify configuration
```

### Check if Deployment is Healthy

```bash
cd verify/
./health-check.sh
```

### Run Full Integration Test

```bash
cd verify/
./integration-test.sh
```

### View Deployment Logs

```bash
# Backend logs
gcloud logging read "resource.labels.service_name=ai-resume-review-v2-backend-prod" --limit=50

# Frontend logs
gcloud logging read "resource.labels.service_name=ai-resume-review-v2-frontend-prod" --limit=50
```

### Rollback Deployment

```bash
cd utils/
./rollback.sh backend  # or 'frontend' or 'both'
```

---

## 🔧 Configuration

All scripts use configuration from `utils/common-functions.sh`:

| Variable | Value | Description |
|----------|-------|-------------|
| `PROJECT_ID` | ytgrs-464303 | GCP project ID |
| `REGION` | us-central1 | Deployment region |
| `BACKEND_SERVICE_NAME` | ai-resume-review-v2-backend-prod | Backend Cloud Run service |
| `FRONTEND_SERVICE_NAME` | ai-resume-review-v2-frontend-prod | Frontend Cloud Run service |
| `SQL_INSTANCE_NAME` | ai-resume-review-v2-db-prod | Cloud SQL instance |
| `VPC_CONNECTOR` | arr-v2-connector | VPC connector name |

To change configuration, edit `utils/common-functions.sh`.

---

## 🆘 Troubleshooting

### Common Issues

**1. "Permission Denied" errors**
```bash
# Re-authenticate
gcloud auth login

# Set correct project
gcloud config set project ytgrs-464303
```

**2. "Docker build failed"**
```bash
# Check Docker is running
docker ps

# If not, start Docker Desktop
```

**3. "VPC connector not found"**
```bash
# VPC connector will be created automatically during backend deployment
# Or create manually:
cd setup/
./setup-gcp-project.sh  # Includes VPC connector creation
```

**4. "Cloud SQL connection failed"**
```bash
# Check SQL instance is running
gcloud sql instances list

# Check VPC connector is READY
gcloud compute networks vpc-access connectors describe arr-v2-connector --region=us-central1
```

**5. "Secrets not found"**
```bash
# Check secrets exist
gcloud secrets list

# If missing, run:
cd setup/
./setup-secrets.sh
```

---

## 📊 Cost Estimate

After deployment, ongoing costs are approximately:

| Service | Monthly Cost |
|---------|--------------|
| Cloud Run (Backend) | $5-10 (min=0) |
| Cloud Run (Frontend) | $5-10 (min=0) |
| Cloud SQL | $25-35 |
| VPC Connector | $10 |
| **Total** | **~$45-65/month** |

Plus variable costs:
- OpenAI API: $50-200/month (usage-based)
- Egress bandwidth: $1-5/month

---

## 🔗 Related Documentation

- [../deployment/README.md](../../deployment/README.md) - High-level deployment guide
- [../../GCP_CLOUD_ARCHITECTURE.md](../../GCP_CLOUD_ARCHITECTURE.md) - Architecture overview
- [../../PHASE3_DEPLOYMENT_GUIDE.md](../../PHASE3_DEPLOYMENT_GUIDE.md) - Detailed Phase 3 guide
- [../../CLAUDE.md](../../CLAUDE.md) - Development guidelines

---

## 📞 Support

**For deployment issues**:
1. Check the troubleshooting section above
2. Review logs: `gcloud logging read ...`
3. Check Cloud Console: https://console.cloud.google.com
4. Refer to [PHASE3_DEPLOYMENT_GUIDE.md](../../PHASE3_DEPLOYMENT_GUIDE.md)

**For code issues**:
1. Refer to [CLAUDE.md](../../CLAUDE.md)
2. Check local development setup: `./scripts/docker/dev.sh status`

---

**Version**: 3.0 (Refactored)
**Last Updated**: 2025-10-10
**Maintained By**: Cloud Engineering Team

---

## ✨ What's New in Version 3.0

**Major Refactoring (Oct 2025):**
- Consolidated 21 scripts → 8 scripts (62% reduction!)
- All scripts now support `--dry-run` mode
- All scripts have `--step=<name>` for granular control
- All scripts have `--help` documentation
- 40-61% code reduction (removed duplication)
- Better error handling and consistency

**Benefits:**
- Easier to use (one command vs many)
- Safer (dry-run before execution)
- More flexible (step-by-step or all-at-once)
- Better documented (built-in help)

See [REFACTORING_PLAN.md](REFACTORING_PLAN.md) for full details.
