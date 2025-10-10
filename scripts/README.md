# Scripts Directory

This directory contains utility scripts for local development and GCP deployment management.

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

#### One-Command Deployment
```bash
# Deploy everything (migrations + backend + frontend)
./scripts/gcp/deploy/deploy-all.sh
```

#### Step-by-Step Deployment
```bash
# Step 1: Verify prerequisites
./scripts/gcp/deploy/1-verify-prerequisites.sh

# Step 2: Run database migrations
./scripts/gcp/deploy/2-run-migrations.sh

# Step 3: Deploy backend to Cloud Run
./scripts/gcp/deploy/3-deploy-backend.sh

# Step 4: Deploy frontend to Cloud Run
./scripts/gcp/deploy/4-deploy-frontend.sh
```

**What these scripts do:**
1. Build Docker images for production
2. Push images to Google Artifact Registry
3. Deploy containers to Cloud Run
4. Configure secrets, environment variables, VPC
5. Run health checks

### Setup Scripts (`gcp/setup/`)

Initial infrastructure setup (run once per environment):

```bash
# Complete GCP project setup
./scripts/gcp/setup/setup-gcp-project.sh

# Setup Cloud SQL database
./scripts/gcp/setup/setup-cloud-sql.sh

# Configure secrets in Secret Manager
./scripts/gcp/setup/setup-secrets.sh

# Clean up old resources
./scripts/gcp/setup/cleanup-old-resources.sh
```

### Monitoring Scripts (`gcp/monitoring/`)

```bash
# Setup all monitoring at once
./scripts/gcp/monitoring/run-all-setup.sh

# Or setup individually:
./scripts/gcp/monitoring/1-setup-notification-channels.sh
./scripts/gcp/monitoring/2-setup-uptime-checks.sh
./scripts/gcp/monitoring/3-setup-critical-alerts.sh
./scripts/gcp/monitoring/4-setup-log-metrics.sh
./scripts/gcp/monitoring/5-setup-budget-alert.sh

# Verify monitoring setup
./scripts/gcp/monitoring/verify-setup.sh
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
