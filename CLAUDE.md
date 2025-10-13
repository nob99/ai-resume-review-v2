# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered resume review platform for recruitment consultants. The system uses specialized AI agents to analyze resumes for different industries (Strategy/Tech/M&A/Financial Advisory/Full Service Consulting, System Integrator).

**Tech Stack**: Next.js 15.5.2 (frontend), FastAPI 0.104.1 (backend), PostgreSQL 15, Redis, LangChain/LangGraph, Docker, Google Cloud Platform

## Essential Commands

### Local Development
```bash
# Start all services (frontend, backend, postgres, redis, pgadmin)
./scripts/docker/dev.sh up

# Check service status before starting any local servers
./scripts/docker/dev.sh status

# View logs
./scripts/docker/dev.sh logs [service]

# Stop all services
./scripts/docker/dev.sh down

# Access service shell
./scripts/docker/dev.sh shell [service]
```

### Frontend Development
```bash
cd frontend
npm run dev          # Development server (port 3000)
npm run test         # Run tests
npm run test:coverage # Test with coverage (80% required)
npm run lint         # Run ESLint
npm run build        # Production build
```

### Backend Development
```bash
cd backend
pytest              # Run all tests
pytest -m "not integration"  # Unit tests only
pytest --cov=app --cov-report=term-missing  # Coverage report
black app tests     # Format code
flake8 app tests    # Lint code
mypy app           # Type checking
```

### Service URLs
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000 (docs at /docs)
- PgAdmin: http://localhost:8080 (dev@airesumereview.com / dev_pgadmin_123)
- PostgreSQL: localhost:5432 (postgres / dev_password_123)
- Redis: localhost:6379

## Critical Architecture Rules

### Frontend Architecture
- **API Layer**: `src/lib/api.ts` handles all API calls - NEVER handle navigation here
- **Auth Context**: `src/contexts/AuthContext.tsx` handles all navigation decisions
- **Error Types**: Use typed errors (AuthExpiredError, AuthInvalidError, NetworkError)
- **Testing**: Use MSW for API mocking, avoid direct fetch mocks

### Backend Architecture
- **Datetime**: ALWAYS use `app.core.datetime_utils.utc_now()`, never `datetime.utcnow()`
- **Config**: Use `app.core.config` for all configuration, no hardcoded values
- **File Processing**: No persistent file storage - process in memory only
- **Testing**: Real database for integration tests, fakeredis for unit tests

### Security Requirements
- JWT tokens with refresh mechanism (access: 30min, refresh: 7 days)
- Bcrypt password hashing (12 rounds minimum)
- Rate limiting on auth endpoints (5 attempts per 15 minutes)
- File upload virus scanning required
- No secrets in code - use environment variables

### Infrastructure Management (Terraform)
- **All GCP infrastructure is managed by Terraform** - Both staging and production environments
- **Single Source of Truth**: `config/environments.yml` drives all infrastructure configuration
- **What Terraform Manages**:
  - ✅ VPC Networks, Subnets, VPC Connectors
  - ✅ Cloud SQL Instances and Databases
  - ✅ Service Accounts and IAM Bindings
  - ✅ Artifact Registry Repositories
  - ✅ Secret Manager References (not values)
- **What Terraform does NOT manage**:
  - ❌ Cloud Run Services (use deployment scripts)
  - ❌ Docker Images (application artifacts)
  - ❌ Secret Values (set manually/scripted)
  - ❌ Database Data (use migrations)
- **Making Infrastructure Changes**:
  1. Edit `config/environments.yml`
  2. Run `terraform plan` to preview changes
  3. Run `terraform apply` to execute
  4. Commit configuration to Git
- **Never make manual changes in GCP Console** - Always use Terraform
- **Check for drift**: Run `terraform plan` regularly to detect manual changes

### CORS Configuration
- **Dynamic Configuration**: CORS origins loaded from `ALLOWED_ORIGINS` environment variable
- **Single Source of Truth**: Defined in `config/environments.yml` under each environment's `cors.allowed_origins`
- **Automatic Deployment**: GitHub Actions and deployment scripts read from config and set environment variable
- **Local Development**: Set in `docker-compose.dev.yml` or `.env` file
- **Format**: Comma-separated list (e.g., `"https://example.com,https://www.example.com"`)
- **Never hardcode**: CORS origins should never be hardcoded in `backend/app/main.py`

## Project Structure

```
/
├── frontend/           # Next.js TypeScript app
│   ├── src/
│   │   ├── app/        # App router pages
│   │   ├── components/ # Shared React components
│   │   ├── contexts/   # React contexts (Auth, etc.)
│   │   ├── features/   # Feature-specific components
│   │   ├── lib/        # Utilities and API client
│   │   └── types/      # TypeScript type definitions
│   └── __tests__/      # Jest tests mirroring src structure
├── backend/            # FastAPI Python API
│   ├── app/
│   │   ├── core/       # Core utilities (config, security, database, cache)
│   │   │   ├── database/  # Database connection & BaseRepository
│   │   │   └── cache/     # Redis connection & cache service
│   │   └── features/   # Feature modules
│   │       └── feature_name/
│   │           ├── api.py         # HTTP endpoints
│   │           ├── service.py     # Business logic (optional)
│   │           ├── repository.py  # Database operations
│   │           ├── schemas.py     # Pydantic models
│   │           └── tests/         # Feature tests
│   └── ai_agents/      # LangChain/LangGraph AI agents
│       ├── agents/     # Agent implementations (base, structure, appeal)
│       ├── config/     # Industry configurations
│       ├── prompts/    # Prompt templates
│       ├── services/   # Agent orchestration services
│       ├── utils/      # Utilities for agents
│       ├── workflows/  # LangGraph workflows
│       └── tests/      # Agent tests
├── database/           # Database layer
│   ├── models/         # SQLAlchemy models
│   ├── migrations/     # Alembic migrations
│   ├── docs/           # Schema documentation
│   ├── scripts/        # Database scripts
│   └── tests/          # Database tests
├── config/             # Environment configuration
│   ├── environments.yml # Single source of truth for all environments
│   └── README.md       # Configuration guide
├── terraform/          # Infrastructure as Code
│   ├── bootstrap/      # GCS state bucket setup
│   ├── modules/        # Reusable Terraform modules
│   ├── environments/   # Staging and production configs
│   └── README.md       # Terraform setup and usage guide
├── scripts/            # Development utilities
│   ├── docker/         # Docker development scripts
│   ├── gcp/            # GCP deployment scripts (deploy, setup, monitoring)
│   └── lib/            # Shared utilities (config loader)
├── .github/workflows/  # CI/CD pipelines
│   ├── staging.yml     # Auto-deploy to staging
│   └── production.yml  # Manual deploy to production
└── archive/            # Archived documents and old implementations
```

## AI Agent System

The platform uses LangChain/LangGraph to orchestrate multiple specialized agents:
- **Base Agent**: Common resume quality checks
- **Structure Agent**: General resume structure evaluation
- **Appeal Agent**: Industry-specific appeal evaluation

Prompts are database-driven for easy updates without code changes.

## Cloud Deployment

### Production Environments
- **Staging**: https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app
- **Production**: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app

### Infrastructure Management

> **Important:** All GCP infrastructure is managed by Terraform. Both staging and production environments are fully under Infrastructure as Code control.

#### Status: ✅ Complete
- **Staging**: 11 resources imported and managed (Oct 13, 2025)
- **Production**: 11 resources imported and managed (Oct 13, 2025)
- **Migration**: Zero downtime, complete documentation available

See handover documents:
- [HANDOVER_TERRAFORM_MIGRATION_V5.md](archive/20251013/HANDOVER_TERRAFORM_MIGRATION_V5.md) - Staging import
- [HANDOVER_TERRAFORM_COMPLETE_V6.md](archive/20251013/HANDOVER_TERRAFORM_COMPLETE_V6.md) - Production import & journey

#### Working with Terraform

**Check infrastructure state:**
```bash
cd terraform/environments/staging  # or production
terraform plan
# Should show: "No changes. Your infrastructure matches the configuration."
```

**Make infrastructure changes:**
```bash
# 1. Edit config/environments.yml
vim config/environments.yml

# 2. Preview changes
cd terraform/environments/staging
terraform plan

# 3. Apply changes
terraform apply

# 4. Commit to Git
git add config/environments.yml
git commit -m "feat: update infrastructure"
git push
```

**What Terraform manages vs what it doesn't:**

| Managed by Terraform ✅ | NOT Managed (use scripts) ❌ |
|-------------------------|------------------------------|
| VPC, Subnets, Connectors | Cloud Run Services |
| Cloud SQL Instances/DBs | Docker Images |
| Service Accounts, IAM | Secret Values |
| Artifact Registry | Database Migrations |

#### Deploying Applications (Separate from Infrastructure)

**Application deployments** (code changes, env vars):
```bash
# Deploy to staging
./scripts/gcp/deploy/deploy.sh --environment=staging

# Deploy to production
./scripts/gcp/deploy/deploy.sh --environment=production
```

#### Documentation
- [terraform/README.md](terraform/README.md) - Complete Terraform guide
- [config/README.md](config/README.md) - Configuration management
- [scripts/gcp/README.md](scripts/gcp/README.md) - Deployment scripts

## Testing Standards

- **Coverage**: Minimum 80% required
- **Organization**: Tests organized by user story (e.g., `tests/auth/AUTH-001_user_login/`)
- **Frontend**: Jest + React Testing Library + MSW
- **Backend**: pytest with markers for integration/slow tests

## Development Workflow

1. Check Docker status: `./scripts/docker/dev.sh status`
2. Start services: `./scripts/docker/dev.sh up`
3. Create feature branch: `git checkout -b feature/STORY-ID-description`
4. Run tests before committing
5. Ensure linting passes
6. Update documentation if needed

## Common Issues

- **Port conflicts**: Always check Docker status first
- **Frontend auth errors**: Check if refresh token logic in AuthContext is working
- **Backend timezone**: Use `utc_now()` from datetime_utils
- **Test failures**: Ensure Docker services are running for integration tests