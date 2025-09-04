# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered resume review platform for recruitment consultants. The system uses specialized AI agents to analyze resumes for different industries (Strategy/Tech/M&A/Financial Advisory/Full Service Consulting, System Integrator).

**Tech Stack**: Next.js 15.5.2 (frontend), FastAPI 0.104.1 (backend), PostgreSQL 15, Redis, LangChain/LangGraph, Docker, Google Cloud Platform

## Essential Commands

### Local Development
```bash
# Start all services (frontend, backend, postgres, redis, pgadmin)
./scripts/docker-dev.sh up

# Check service status before starting any local servers
./scripts/docker-dev.sh status

# View logs
./scripts/docker-dev.sh logs [service]

# Stop all services
./scripts/docker-dev.sh down

# Access service shell
./scripts/docker-dev.sh shell [service]
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

## Project Structure

```
/
├── frontend/       # Next.js TypeScript app
│   ├── src/
│   │   ├── app/    # App router pages
│   │   ├── components/  # React components
│   │   ├── contexts/    # React contexts
│   │   ├── hooks/       # Custom hooks
│   │   └── lib/         # Utilities and API
│   └── tests/      # Jest tests mirroring src structure
├── backend/        # FastAPI Python API
│   ├── app/
│   │   ├── api/    # API endpoints
│   │   ├── core/   # Core utilities
│   │   ├── models/ # SQLAlchemy models
│   │   └── services/  # Business logic
│   └── tests/      # Pytest tests by feature
├── database/       # Migrations and scripts
├── infrastructure/ # Terraform GCP setup
└── scripts/        # Development utilities
```

## AI Agent System

The platform uses LangChain/LangGraph to orchestrate multiple specialized agents:
- **Base Agent**: Common resume quality checks
- **Structure Agent**: General resume structure evaluation  
- **Appeal Agent**: Industry-specific appeal evaluation

Prompts are database-driven for easy updates without code changes.

## Current Sprint Status

**Sprint 003** (Sep 2-15, 2025): File Upload Pipeline
- UPLOAD-001: File upload interface ✅
- UPLOAD-002: File validation 🔄
- UPLOAD-003: Text extraction 🔄
- UPLOAD-004: Progress feedback 🔄

## Testing Standards

- **Coverage**: Minimum 80% required
- **Organization**: Tests organized by user story (e.g., `tests/auth/AUTH-001_user_login/`)
- **Frontend**: Jest + React Testing Library + MSW
- **Backend**: pytest with markers for integration/slow tests

## Development Workflow

1. Check Docker status: `./scripts/docker-dev.sh status`
2. Start services: `./scripts/docker-dev.sh up`
3. Create feature branch from sprint branch: `git checkout -b feature/STORY-ID-description`
4. Run tests before committing
5. Ensure linting passes
6. Update documentation if needed

## Common Issues

- **Port conflicts**: Always check Docker status first
- **Frontend auth errors**: Check if refresh token logic in AuthContext is working
- **Backend timezone**: Use `utc_now()` from datetime_utils
- **Test failures**: Ensure Docker services are running for integration tests