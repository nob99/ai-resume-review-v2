# Scripts Directory

**Version:** 3.0 (Refactored - Oct 2025)

This directory contains utility scripts for local development and GCP deployment management.

## ✨ Recent Updates (v3.0 - Oct 2025)

**Major GCP scripts consolidation:**
- **Before:** 21 GCP scripts
- **After:** 8 GCP scripts (62% reduction!)
- All scripts support `--dry-run`, `--step=<name>`, `--help`
- 40-61% code reduction (removed duplication)
- Better error handling and consistency

See [gcp/REFACTORING_PLAN.md](gcp/REFACTORING_PLAN.md) for full details.

## Directory Structure

```
scripts/
├── docker/          # Local development (Docker Compose wrappers)
├── gcp/             # GCP deployment & management
│   ├── deploy/      # Deployment scripts
│   ├── monitoring/  # Monitoring and alerting setup
│   ├── setup/       # Initial GCP infrastructure setup
│   ├── utils/       # Shared utilities for GCP scripts
│   └── verify/      # Health checks and integration tests
└── lib/             # Shared utilities for all scripts
```

## Local Development Scripts (`docker/`)

Wrapper scripts for managing local Docker Compose environment.

### Prerequisites
- Docker Desktop installed and running
- All services defined in `docker-compose.dev.yml`

### Main Commands

#### `./docker/dev.sh` - Manage All Services
```bash
# Start all services (frontend, backend, postgres, redis, pgadmin)
./scripts/docker/dev.sh up

# Check service status
./scripts/docker/dev.sh status

# View logs (all services or specific service)
./scripts/docker/dev.sh logs [service]

# Stop all services
./scripts/docker/dev.sh down

# Restart all services
./scripts/docker/dev.sh restart

# Build all service images
./scripts/docker/dev.sh build

# Remove all containers and volumes (clean slate)
./scripts/docker/dev.sh clean

# Open shell in a service
./scripts/docker/dev.sh shell [frontend|backend|postgres|redis]
```

**Service URLs** (when running):
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000 (docs at /docs)
- PgAdmin: http://localhost:8080 (dev@airesumereview.com / dev_pgadmin_123)
- PostgreSQL: localhost:5432 (postgres / dev_password_123)
- Redis: localhost:6379

#### `./docker/frontend.sh` - Frontend-Specific Management
```bash
# Start/stop frontend only
./scripts/docker/frontend.sh start
./scripts/docker/frontend.sh stop
./scripts/docker/frontend.sh restart

# View frontend logs
./scripts/docker/frontend.sh logs

# Run tests/linting in container
./scripts/docker/frontend.sh test
./scripts/docker/frontend.sh lint

# Open shell
./scripts/docker/frontend.sh shell
```

### When to Use Docker Scripts

- **Local development**: Testing changes before pushing to GitHub
- **Debugging**: Investigating issues in isolated environment
- **Database access**: Using pgAdmin or psql shell
- **Testing**: Running full stack locally

### Notes

- Docker scripts are **NOT used in production/GCP**
- They use `docker-compose.dev.yml` (development configuration)
- Completely separate from GCP deployment pipeline

---

## GCP Deployment Scripts (`gcp/`)

Scripts for deploying and managing the application on Google Cloud Platform.

### Prerequisites
- `gcloud` CLI installed and authenticated
- Docker installed (for building images)
- Required GCP APIs enabled
- Appropriate IAM permissions

### Deployment Scripts (`gcp/deploy/`)

**✨ NEW: Consolidated into one script**

#### Complete Deployment
```bash
# Deploy everything (verify + migrate + backend + frontend)
./scripts/gcp/deploy/deploy.sh

# Preview what would happen
./scripts/gcp/deploy/deploy.sh --dry-run

# Skip health checks (faster)
./scripts/gcp/deploy/deploy.sh --skip-tests
```

#### Step-by-Step Deployment
```bash
# Individual steps
./scripts/gcp/deploy/deploy.sh --step=verify      # Prerequisites check
./scripts/gcp/deploy/deploy.sh --step=migrate     # Database migrations
./scripts/gcp/deploy/deploy.sh --step=backend     # Backend only
./scripts/gcp/deploy/deploy.sh --step=frontend    # Frontend only

# Preview individual steps
./scripts/gcp/deploy/deploy.sh --step=backend --dry-run
```

**What it does:**
1. Verifies prerequisites (gcloud, Docker, GCP resources)
2. Runs database migrations
3. Builds Docker images for production
4. Pushes images to Google Artifact Registry
5. Deploys containers to Cloud Run
6. Configures secrets, environment variables, VPC
7. Runs health checks

### Setup Scripts (`gcp/setup/`)

**✨ NEW: Consolidated into one script**

Initial infrastructure setup (run once per environment):

```bash
# Complete infrastructure setup
./scripts/gcp/setup/setup.sh

# Preview what would be created
./scripts/gcp/setup/setup.sh --dry-run

# Step-by-step setup
./scripts/gcp/setup/setup.sh --step=project      # Service accounts, IAM, VPC
./scripts/gcp/setup/setup.sh --step=database     # Cloud SQL
./scripts/gcp/setup/setup.sh --step=secrets      # Secret Manager

# Clean up old resources (dangerous!)
./scripts/gcp/setup/cleanup.sh --dry-run
./scripts/gcp/setup/cleanup.sh
```

### Monitoring Scripts (`gcp/monitoring/`)

**✨ NEW: Consolidated into one script**

```bash
# Setup all monitoring at once
./scripts/gcp/monitoring/setup.sh

# Preview what would be created
./scripts/gcp/monitoring/setup.sh --dry-run

# Step-by-step setup
./scripts/gcp/monitoring/setup.sh --step=channels    # Slack + Email
./scripts/gcp/monitoring/setup.sh --step=uptime      # Uptime checks
./scripts/gcp/monitoring/setup.sh --step=alerts      # Alert policies
./scripts/gcp/monitoring/setup.sh --step=logs        # Log metrics
./scripts/gcp/monitoring/setup.sh --step=budget      # Budget alert

# Verify monitoring setup
./scripts/gcp/monitoring/verify.sh
```

### Verification Scripts (`gcp/verify/`)

```bash
# Check service health
./scripts/gcp/verify/health-check.sh

# Run integration tests against deployed services
./scripts/gcp/verify/integration-test.sh
```

### Utility Scripts (`gcp/utils/`)

```bash
# Create admin user in production database
./scripts/gcp/utils/create-admin-user.sh

# Rollback to previous deployment
./scripts/gcp/utils/rollback.sh
```

### When to Use GCP Scripts

- **Manual deployments**: When you need to deploy outside of CI/CD
- **Initial setup**: Setting up new GCP environment
- **Troubleshooting**: Manual deployment to test changes
- **One-off tasks**: Creating admin users, rollbacks, etc.

### Notes

- GCP scripts use production Dockerfiles (`backend/Dockerfile`, `frontend/Dockerfile`)
- They deploy to Cloud Run (managed containers)
- Use Cloud SQL for database (not local PostgreSQL)
- **Alternative to GitHub Actions** - same result, manual trigger

---

## GitHub Actions (Automated Deployment)

Located in `.github/workflows/`:
- `staging.yml` - Auto-deploys to staging on push to `main`
- `production.yml` - Deploys to production (manual approval)

**Workflow:**
1. Push code to GitHub → GitHub Actions triggered
2. Runs tests and linting
3. Builds Docker images
4. Deploys to Cloud Run
5. Runs health checks

This is the **primary deployment method** for the project.

---

## Shared Utilities (`lib/`)

- `docker.sh` - Common functions for Docker scripts (colors, helpers)

---

## Deployment Flow Summary

### Local Development Flow
```
Developer → scripts/docker/dev.sh up → Local Docker Compose → Test on laptop
```

### Production Deployment Flow (Automated)
```
Developer → git push → GitHub Actions → Build images → Deploy to Cloud Run
```

### Production Deployment Flow (Manual)
```
Developer → scripts/gcp/deploy/deploy-all.sh → Build images → Deploy to Cloud Run
```

---

## Key Differences: Local vs Production

| Aspect | Local (docker/) | Production (gcp/) |
|--------|----------------|-------------------|
| **Orchestration** | Docker Compose | Cloud Run |
| **Database** | Local PostgreSQL container | Cloud SQL (managed) |
| **Redis** | Local Redis container | Memorystore Redis (or disabled) |
| **Config** | docker-compose.dev.yml | gcloud commands |
| **Secrets** | .env files | Secret Manager |
| **Trigger** | Manual (dev.sh up) | Git push (or manual script) |
| **Purpose** | Development/testing | Production environment |

---

## Quick Reference

### "I want to test my code changes"
```bash
./scripts/docker/dev.sh up
```

### "I want to deploy to staging manually"
```bash
./scripts/gcp/deploy/deploy-all.sh
```

### "I want to deploy to production"
- Use GitHub Actions (production.yml)
- Or run GCP deploy scripts with production environment variables

### "I need to set up a new GCP environment"
```bash
./scripts/gcp/setup/setup-gcp-project.sh
./scripts/gcp/setup/setup-cloud-sql.sh
./scripts/gcp/setup/setup-secrets.sh
```

### "I want to check if production is healthy"
```bash
./scripts/gcp/verify/health-check.sh
```

---

## Contributing

When adding new scripts:
- Add to appropriate subdirectory (docker/, gcp/, lib/)
- Follow existing naming conventions
- Include usage instructions in this README
- Make scripts executable: `chmod +x script.sh`
- Use shared utilities from `lib/` and `gcp/utils/common-functions.sh`
