# AI Resume Review Platform

An AI-powered resume analysis platform designed for recruitment consultants to provide industry-specific feedback and improve candidate quality. The system uses specialized AI agents to evaluate resumes across different consulting industries (Strategy/Tech/M&A/Financial Advisory/Full Service Consulting, System Integrator).

## What This Platform Does

The AI Resume Review Platform helps recruitment consultants:

- **Analyze Resumes with AI**: Upload candidate resumes and receive detailed, industry-specific feedback
- **Industry Specialization**: Different AI agents trained for specific consulting sectors
- **Structured Evaluation**: Consistent scoring across resume structure, content quality, and industry appeal
- **Manage Candidates**: Track candidates, resumes, and review history
- **Team Collaboration**: Multi-user system with role-based access control

## Quick Start

### Prerequisites

- **Docker Desktop** installed and running
- **Node.js 18+** (for local frontend development)
- **Git** for version control
- Ports available: 3000 (frontend), 8000 (backend), 5432 (postgres), 6379 (redis), 8080 (pgadmin)

### Get Up and Running in 2 Minutes

```bash
# 1. Clone the repository
git clone <repository-url>
cd ai-resume-review-v2

# 2. Start all services with Docker
./scripts/docker/dev.sh up

# 3. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# PgAdmin: http://localhost:8080
```

That's it! The platform is now running locally with all services.

## Technology Stack

### Frontend
- **Next.js 15.5.2** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **React Hook Form** - Form management
- **Jest + React Testing Library** - Testing

### Backend
- **FastAPI 0.104.1** - Modern Python API framework
- **PostgreSQL 15** - Primary database
- **Redis 5.0** - Caching and session storage
- **SQLAlchemy 2.0** - Async ORM
- **LangChain/LangGraph** - AI agent orchestration
- **OpenAI & Anthropic** - LLM providers

### Infrastructure
- **Terraform** - Infrastructure as Code (manages all GCP resources)
- **Google Cloud Platform** - Production hosting (Cloud Run, Cloud SQL, VPC)
- **Docker & Docker Compose** - Containerized development
- **GitHub Actions** - CI/CD automation
- **pytest** - Backend testing
- **Alembic** - Database migrations

> **Note:** All GCP infrastructure is managed by Terraform. See [terraform/README.md](terraform/README.md) for details.

## Architecture Overview

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Browser   │ ──────> │   Next.js    │ ──────> │   FastAPI   │
│  (Client)   │ <────── │  Frontend    │ <────── │   Backend   │
└─────────────┘         └──────────────┘         └─────────────┘
                                                         │
                                                         ├──> PostgreSQL
                                                         ├──> Redis
                                                         └──> AI Agents
                                                              (LangChain)
```

### Key Design Principles

- **Feature-based Architecture**: Code organized by business features, not technical layers
- **Separation of Concerns**: Clear boundaries between API, business logic, and data layers
- **Type Safety**: Full TypeScript (frontend) and type hints (backend)
- **Test-Driven**: 80% minimum code coverage requirement
- **Security First**: JWT authentication, rate limiting, input validation

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
│
├── backend/            # FastAPI Python API
│   ├── app/
│   │   ├── core/       # Core utilities (config, security, database, cache)
│   │   ├── features/   # Feature modules (auth, candidate, resume_upload, etc.)
│   │   └── ...
│   └── ai_agents/      # LangChain/LangGraph AI agents
│       ├── agents/     # Agent implementations (base, structure, appeal)
│       ├── config/     # Industry configurations
│       ├── prompts/    # Prompt templates
│       ├── services/   # Agent orchestration services
│       └── workflows/  # LangGraph workflows
│
├── database/           # Database layer
│   ├── models/         # SQLAlchemy models
│   ├── migrations/     # Alembic migrations
│   └── ...
│
├── config/             # Environment configuration
│   ├── environments.yml # Single source of truth for all environments
│   └── README.md       # Configuration guide
│
├── terraform/          # Infrastructure as Code
│   ├── bootstrap/      # GCS state bucket setup
│   ├── modules/        # Reusable Terraform modules
│   ├── environments/   # Staging and production configs
│   └── README.md       # Terraform setup and usage guide
│
├── scripts/            # Deployment and utilities
│   ├── docker/         # Docker development scripts
│   ├── gcp/            # GCP deployment scripts (deploy, setup, monitoring)
│   └── lib/            # Shared utilities (config loader)
│
├── .github/workflows/  # CI/CD pipelines
│   ├── staging.yml     # Auto-deploy to staging
│   └── production.yml  # Manual deploy to production
│
├── knowledge/          # Product management docs and backlogs
└── archive/            # Archived documents and old implementations
```

## Development Guide

## Contributor Resources

- See [`AGENTS.md`](AGENTS.md) for contributor guidelines, coding standards, and PR expectations specific to this repository.

### Running the Development Environment

```bash
# Start all services
./scripts/docker/dev.sh up

# Check service status
./scripts/docker/dev.sh status

# View logs
./scripts/docker/dev.sh logs [service]

# Access service shell
./scripts/docker/dev.sh shell frontend
./scripts/docker/dev.sh shell backend

# Stop all services
./scripts/docker/dev.sh down
```

### Frontend Development

```bash
cd frontend

# Install dependencies (if not using Docker)
npm install

# Run development server
npm run dev

# Run tests
npm run test
npm run test:coverage

# Lint and format
npm run lint
npm run build
```

### Backend Development

```bash
cd backend

# Run tests
pytest
pytest -m "not integration"  # Unit tests only

# Code quality
black app tests              # Format code
flake8 app tests            # Lint code
mypy app                    # Type checking

# Coverage
pytest --cov=app --cov-report=term-missing
```

### Git Workflow

```bash
# Create feature branch from current sprint branch
git checkout sprint-XXX
git checkout -b feature/STORY-ID-description

# Make changes, commit, push
git add .
git commit -m "feat: implement feature"
git push origin feature/STORY-ID-description

# Create pull request for review
```

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | - |
| Backend API | http://localhost:8000 | - |
| API Docs (Swagger) | http://localhost:8000/docs | - |
| PgAdmin | http://localhost:8080 | dev@airesumereview.com / dev_pgadmin_123 |
| PostgreSQL | localhost:5432 | postgres / dev_password_123 |
| Redis | localhost:6379 | - |

## Testing

### Frontend Tests
- **Unit Tests**: Component logic and utilities
- **Integration Tests**: Feature flows and API integration
- **Coverage**: 80% minimum required
- **Tool**: Jest + React Testing Library + MSW

### Backend Tests
- **Unit Tests**: Business logic and utilities
- **Integration Tests**: Database operations and API endpoints
- **Coverage**: 80% minimum required
- **Tool**: pytest with async support

```bash
# Run all tests
./scripts/docker/dev.sh shell frontend
npm run test

./scripts/docker/dev.sh shell backend
pytest
```

## AI Agent System

The platform uses **LangChain** and **LangGraph** to orchestrate multiple specialized AI agents:

- **Base Agent**: Common resume quality checks (formatting, completeness, clarity)
- **Structure Agent**: Resume structure evaluation (sections, organization, flow)
- **Appeal Agent**: Industry-specific appeal evaluation (tailored per consulting sector)

### Supported Industries
- Strategy Consulting
- Tech Consulting
- M&A Consulting
- Financial Advisory
- Full Service Consulting
- System Integrator

Prompts are **database-driven**, allowing non-technical updates without code changes.

## Security Features

- **JWT Authentication**: Access tokens (30min) + refresh tokens (7 days)
- **Password Security**: Bcrypt hashing with 12 rounds minimum
- **Rate Limiting**: 5 login attempts per 15 minutes per IP
- **Input Validation**: Comprehensive Pydantic schema validation
- **CORS Protection**: Configured for specific origins only
- **No Secrets in Code**: All configuration via environment variables

## Cloud Deployment

### Production Environments
- **Staging**: https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app
- **Production**: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app

### Deployment Status
- **GitHub Actions**: https://github.com/stellar-aiz/ai-resume-review-v2/actions
  - Staging deploys automatically on push to `main`
  - Production deploys manually via workflow dispatch

### Infrastructure Management

> **Important:** All GCP infrastructure (VPC, Cloud SQL, Service Accounts, IAM, etc.) is managed by **Terraform**. Both staging and production environments are fully managed as Infrastructure as Code.

#### Single Source of Truth

All infrastructure configuration is centralized in:
- **[config/environments.yml](config/environments.yml)** - Environment settings
- **[terraform/](terraform/)** - Infrastructure definitions

#### Managing Infrastructure (Terraform)

**Check infrastructure state:**
```bash
cd terraform/environments/staging  # or production
terraform plan
# Should show: "No changes" if everything matches
```

**Make infrastructure changes:**
```bash
# 1. Edit config/environments.yml
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

**What Terraform manages:**
- ✅ VPC Networks, Subnets, VPC Connectors
- ✅ Cloud SQL Instances and Databases
- ✅ Service Accounts and IAM Bindings
- ✅ Artifact Registry Repositories
- ✅ Secret Manager References

**What Terraform does NOT manage:**
- ❌ Cloud Run Services (use deployment scripts)
- ❌ Docker Images (application artifacts)
- ❌ Secret Values (set manually/scripted)
- ❌ Database Data (use migrations)

#### Deploying Applications (Scripts)

For application deployments (code changes, env vars, etc.):

```bash
# Deploy to staging
./scripts/gcp/deploy/deploy.sh --environment=staging

# Deploy to production
./scripts/gcp/deploy/deploy.sh --environment=production
```

#### Documentation

- **[terraform/README.md](terraform/README.md)** - Complete Terraform guide
- **[config/README.md](config/README.md)** - Configuration documentation
- **[scripts/gcp/README.md](scripts/gcp/README.md)** - Deployment scripts guide

## Additional Resources

### Documentation
- **[CLAUDE.md](CLAUDE.md)** - AI coding assistant instructions (for Claude Code)
- **[Frontend README](frontend/README.md)** - Detailed frontend architecture and patterns
- **[Backend README](backend/README.md)** - Detailed backend architecture and API docs
- **[Terraform README](terraform/README.md)** - Infrastructure setup and management
- **[Configuration Guide](config/README.md)** - Environment configuration documentation


## Common Issues & Troubleshooting

### Port Conflicts
```bash
# Check what's using a port
lsof -i :3000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Docker Issues
```bash
# Clean restart
./scripts/docker/dev.sh down
./scripts/docker/dev.sh clean
./scripts/docker/dev.sh up
```

### Database Connection Issues
```bash
# Ensure PostgreSQL is running
./scripts/docker/dev.sh status

# Access database directly
./scripts/docker/dev.sh shell postgres
psql -U postgres -d ai_resume_review_dev
```

### Frontend Can't Connect to Backend
- Ensure both services are running: `./scripts/docker/dev.sh status`
- Frontend uses `http://backend:8000` internally (Docker network)
- Browser uses `http://localhost:8000` externally


---

**Built with ❤️ for recruitment consultants**

*Last Updated: October 2025*
