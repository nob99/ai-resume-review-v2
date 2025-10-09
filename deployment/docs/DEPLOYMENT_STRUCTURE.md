# GCP Deployment Structure Overview

**Purpose**: Help engineers understand the deployment architecture and file organization.

---

## 📁 Complete Deployment File Structure

```
ai-resume-review-v2/
│
├── 📄 GCP_CLOUD_ARCHITECTURE.md        ← High-level cloud architecture doc
│
├── 📁 .github/workflows/               ← CI/CD Automation
│   ├── test.yml                        ← Run tests on every PR
│   ├── deploy-staging.yml              ← Auto-deploy to staging
│   ├── deploy-production.yml           ← Manual deploy to production
│   └── rollback.yml                    ← Rollback failed deployments
│
├── 📁 deployment/                      ← Deployment configurations
│   │
│   ├── 📄 README.md                    ← Deployment guide (you are here)
│   ├── 📄 DEPLOYMENT_STRUCTURE.md      ← This file (structure overview)
│   │
│   ├── 📁 configs/                     ← Configuration files
│   │   │
│   │   ├── .env.staging.example        ← Staging environment variables (TEMPLATE)
│   │   ├── .env.production.example     ← Production environment variables (TEMPLATE)
│   │   ├── .env.staging                ← Actual staging values (NOT in git)
│   │   ├── .env.production             ← Actual production values (NOT in git)
│   │   │
│   │   ├── cloud-run-backend-staging.yaml
│   │   ├── cloud-run-backend-production.yaml
│   │   ├── cloud-run-frontend-staging.yaml
│   │   └── cloud-run-frontend-production.yaml
│   │
│   └── 📁 docs/                        ← Additional documentation
│       └── (future docs will go here)
│
└── 📁 scripts/gcp/                     ← Deployment scripts
    ├── setup-gcp-project.sh            ← Initial GCP setup
    ├── setup-cloud-sql.sh              ← Database setup
    ├── setup-secrets.sh                ← Secrets management
    ├── deploy-to-staging.sh            ← Deploy to staging
    ├── deploy-to-production.sh         ← Deploy to production
    ├── rollback.sh                     ← Rollback deployments
    └── run-migrations.sh               ← Database migrations
```

---

## 🎯 Design Principles

### 1. Separation of Concerns

**GitHub Actions** (.github/workflows/):
- **Purpose**: Automated CI/CD workflows
- **Who uses**: GitHub Actions runner (automated)
- **Contains**: YAML workflow definitions

**Deployment Configs** (deployment/configs/):
- **Purpose**: Environment-specific configurations
- **Who uses**: Deployment scripts and GitHub Actions
- **Contains**: Environment variables, Cloud Run configs

**Deployment Scripts** (scripts/gcp/):
- **Purpose**: Manual deployment and setup tasks
- **Who uses**: Engineers running deployments manually
- **Contains**: Bash scripts with gcloud commands

### 2. Template vs Actual Values

**Template Files** (committed to git):
- `.env.staging.example`
- `.env.production.example`
- `*.yaml` files with placeholders

**Actual Files** (NOT committed to git):
- `.env.staging`
- `.env.production`
- Service account keys

### 3. Security First

**In Git** (safe to commit):
- ✅ Configuration templates
- ✅ Non-sensitive environment variables
- ✅ Documentation
- ✅ Scripts (no hardcoded secrets)

**NOT in Git** (added to .gitignore):
- ❌ Actual API keys
- ❌ Actual passwords
- ❌ Service account keys
- ❌ Environment files with secrets

---

## 🔄 File Relationships

### How Files Work Together

```
Developer wants to deploy to staging:
    ↓
1. Run: ./scripts/gcp/deploy-to-staging.sh
    ↓
2. Script reads: deployment/configs/.env.staging
    ↓
3. Script uses: deployment/configs/cloud-run-backend-staging.yaml
    ↓
4. Script executes: gcloud run deploy ...
    ↓
5. Cloud Run pulls: Docker image from Artifact Registry
    ↓
6. Cloud Run injects: Environment variables from .env.staging
    ↓
7. Application starts with staging configuration
```

### How GitHub Actions Works

```
Developer pushes to 'staging' branch:
    ↓
1. GitHub triggers: .github/workflows/deploy-staging.yml
    ↓
2. Workflow builds: Docker images
    ↓
3. Workflow pushes: Images to Artifact Registry
    ↓
4. Workflow reads: deployment/configs/.env.staging (from secrets)
    ↓
5. Workflow deploys: Using gcloud commands
    ↓
6. Workflow tests: Smoke tests
    ↓
7. Workflow notifies: Team in Slack
```

---

## 📝 File-by-File Purpose

### GitHub Actions Workflows

| File | Purpose | Trigger | Output |
|------|---------|---------|--------|
| `test.yml` | Run tests on PR | Every PR | Pass/Fail status |
| `deploy-staging.yml` | Deploy to staging | Push to `staging` branch | Staging URL |
| `deploy-production.yml` | Deploy to production | Manual trigger | Production URL |
| `rollback.yml` | Rollback deployment | Manual trigger | Previous version |

### Configuration Files

| File | Purpose | Used By | Contains |
|------|---------|---------|----------|
| `.env.staging.example` | Template for staging | Engineers (copy to .env.staging) | Non-sensitive defaults |
| `.env.production.example` | Template for production | Engineers (copy to .env.production) | Non-sensitive defaults |
| `cloud-run-backend-staging.yaml` | Backend config (staging) | gcloud deploy command | Memory, CPU, scaling |
| `cloud-run-backend-production.yaml` | Backend config (production) | gcloud deploy command | Memory, CPU, scaling |
| `cloud-run-frontend-staging.yaml` | Frontend config (staging) | gcloud deploy command | Memory, CPU, scaling |
| `cloud-run-frontend-production.yaml` | Frontend config (production) | gcloud deploy command | Memory, CPU, scaling |

### Deployment Scripts

| File | Purpose | When to Run | Prerequisites |
|------|---------|-------------|---------------|
| `setup-gcp-project.sh` | Initialize GCP project | Once (initial setup) | GCP account, billing |
| `setup-cloud-sql.sh` | Create database | Once (initial setup) | GCP project created |
| `setup-secrets.sh` | Store secrets | Once (initial setup) | API keys ready |
| `deploy-to-staging.sh` | Deploy to staging | Anytime (testing) | Docker, gcloud |
| `deploy-to-production.sh` | Deploy to production | After staging tested | Staging verified |
| `rollback.sh` | Rollback deployment | When issues occur | Know target revision |
| `run-migrations.sh` | Run DB migrations | When schema changes | Cloud SQL running |

---

## 🔐 Secrets vs Environment Variables

### Non-Sensitive (in `.env.*` files)

Can be stored in environment variables:
- Database host (connection string format)
- Database port
- Database name
- Log level
- Environment name (staging/production)
- AI model name (gpt-4)
- Timeout values

### Sensitive (in Secret Manager)

MUST be stored in Secret Manager:
- OpenAI API key
- Database password
- JWT secret key
- Any API keys
- Encryption keys

---

## 🚀 Common Workflows

### Workflow 1: Initial Setup

```bash
# Step 1: Set up GCP project
./scripts/gcp/setup-gcp-project.sh

# Step 2: Create databases
./scripts/gcp/setup-cloud-sql.sh both

# Step 3: Store secrets
./scripts/gcp/setup-secrets.sh both

# Step 4: Copy and configure environment files
cp deployment/configs/.env.staging.example deployment/configs/.env.staging
cp deployment/configs/.env.production.example deployment/configs/.env.production
# Edit .env.staging and .env.production with actual values

# Step 5: Deploy to staging
./scripts/gcp/deploy-to-staging.sh

# Step 6: Test staging, then deploy to production
./scripts/gcp/deploy-to-production.sh
```

### Workflow 2: Regular Development

```bash
# Make code changes
git add .
git commit -m "feat: add new feature"

# Push to feature branch
git push origin feature/new-feature

# Create PR → Tests run automatically (.github/workflows/test.yml)

# After approval, merge to staging
git checkout staging
git merge feature/new-feature
git push origin staging

# GitHub Actions deploys to staging automatically
# (.github/workflows/deploy-staging.yml)

# Test staging manually

# Deploy to production (manual)
# Trigger .github/workflows/deploy-production.yml from GitHub UI
```

### Workflow 3: Emergency Rollback

```bash
# Production has issues!
./scripts/gcp/rollback.sh production

# Or use GitHub Actions
# Trigger .github/workflows/rollback.yml from GitHub UI
```

---

## 📊 Decision Tree: Which File to Use?

```
Need to deploy?
├─ Automated deployment? → Use .github/workflows/deploy-*.yml
└─ Manual deployment? → Use scripts/gcp/deploy-to-*.sh

Need to configure environment?
├─ Staging? → Edit deployment/configs/.env.staging
└─ Production? → Edit deployment/configs/.env.production

Need to configure Cloud Run resources?
├─ Backend staging? → Edit cloud-run-backend-staging.yaml
├─ Backend production? → Edit cloud-run-backend-production.yaml
├─ Frontend staging? → Edit cloud-run-frontend-staging.yaml
└─ Frontend production? → Edit cloud-run-frontend-production.yaml

Need to store secrets?
└─ Run scripts/gcp/setup-secrets.sh

Need to run migrations?
└─ Run scripts/gcp/run-migrations.sh [env] [direction]
```

---

## 🎓 For New Engineers

### Getting Started Checklist

- [ ] Read `GCP_CLOUD_ARCHITECTURE.md` (understand overall architecture)
- [ ] Read `deployment/README.md` (understand deployment process)
- [ ] Read this file (understand file structure)
- [ ] Review `.github/workflows/` files (understand CI/CD)
- [ ] Review `scripts/gcp/` files (understand deployment scripts)
- [ ] Ask team for access to:
  - [ ] GCP project
  - [ ] GitHub repository
  - [ ] Slack notifications
  - [ ] OpenAI API key

### Common Questions

**Q: Where do I find the production URL?**
A: Run `gcloud run services describe ai-resume-review-frontend-prod --region=us-central1`

**Q: How do I check if staging is deployed?**
A: Check GitHub Actions tab, or run `gcloud run services list`

**Q: Where are secrets stored?**
A: Secret Manager in GCP, run `gcloud secrets list`

**Q: How do I run database migrations?**
A: Use `scripts/gcp/run-migrations.sh [env] up`

**Q: What if deployment fails?**
A: Check logs in Cloud Logging, or rollback with `scripts/gcp/rollback.sh [env]`

---

## 🔗 Related Documentation

- [GCP_CLOUD_ARCHITECTURE.md](../GCP_CLOUD_ARCHITECTURE.md) - Full architecture
- [deployment/README.md](./README.md) - Deployment guide
- [CLAUDE.md](../CLAUDE.md) - Development guidelines

---

**Last Updated**: 2025-10-06
**Maintained By**: DevOps Team
