# AI Resume Review Platform - Backend

## 🎯 Overview

FastAPI-based backend service for the AI Resume Review Platform, providing secure authentication, AI-powered resume analysis, and comprehensive user management for recruitment consultants.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Start Development Environment
```bash
# Clone and navigate to backend
cd backend

# Start all services
docker-compose up --build

# Services will be available at:
# - Backend API: http://localhost:8000
# - API Documentation: http://localhost:8000/docs
# - PgAdmin: http://localhost:8080
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
```

## 🛠 Technology Stack

- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL 15 + Redis 5.0
- **ORM**: SQLAlchemy 2.0 (async)
- **Authentication**: JWT with bcrypt (12 rounds)
- **AI/ML**: LangChain 0.3+ with LangGraph, OpenAI & Anthropic
- **Testing**: pytest 7.4+ with async support
- **Security**: Rate limiting, CORS, input validation
- **Container**: Docker with multi-service orchestration

## 📁 Directory Structure

```
backend/
├── app/                          # Main application code
│   ├── features/                # Feature-based architecture (vertical slices)
│   │   ├── auth/                # Authentication feature
│   │   │   ├── api.py           # HTTP endpoints
│   │   │   ├── repository.py    # Data access layer
│   │   │   ├── schemas.py       # Pydantic request/response models
│   │   │   ├── service.py       # Business logic
│   │   │   └── tests/           # Feature-specific tests
│   │   ├── admin/               # Admin management feature
│   │   ├── candidate/           # Candidate management feature
│   │   ├── profile/             # User profile feature
│   │   ├── resume_upload/       # Resume upload feature
│   │   └── resume_analysis/     # Resume analysis feature
│   ├── core/                    # Shared infrastructure utilities
│   │   ├── database/            # Database connection & base repository
│   │   ├── cache/               # Redis connection & cache service
│   │   ├── config.py            # Configuration management
│   │   ├── datetime_utils.py    # UTC datetime handling
│   │   ├── rate_limiter.py      # Distributed rate limiting
│   │   ├── security.py          # Security utilities
│   │   └── dependencies.py      # FastAPI dependencies
│   └── main.py                  # FastAPI application entry point
├── ai_agents/                   # AI agents system (LangChain/LangGraph)
│   ├── agents/                  # Agent implementations
│   ├── config/                  # Industry configurations
│   ├── prompts/                 # Prompt templates & management
│   ├── services/                # Agent orchestration services
│   ├── workflows/               # LangGraph workflows
│   └── tests/                   # AI agent tests
├── scripts/                     # Utility scripts
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Test configuration
├── Dockerfile                   # Container definition
├── docker-entrypoint.sh         # Container startup script
├── .env.example                 # Environment template
└── README-CONFIG.md             # Configuration documentation
```

## 📚 Documentation

### Core Documentation
- **[Configuration Management](README-CONFIG.md)** - Environment variables, security, and setup
- **[Root README](../README.md)** - Project overview and quick start guide
- **[CLAUDE.md](../CLAUDE.md)** - AI coding assistant instructions

### Specialized Documentation  
- **[AI Agents](app/agents/README.md)** - AI/ML integration and LangChain setup
- **[Test Organization](tests/README.md)** - Test structure and organization by user stories

## 🧪 Testing

### Running Tests

```bash
# Using the project's docker development script (recommended)
./scripts/docker-dev.sh up
./scripts/docker-dev.sh shell backend
pytest

# Run specific test categories
pytest -m "not integration"        # Unit tests only
pytest app/features/auth/tests/     # Authentication tests
pytest app/ai_agents/tests/         # AI agent tests

# Coverage reports
pytest --cov=app --cov-report=term-missing
pytest --cov=app --cov-report=html

# Using the test runner script
python run_tests.py
```

### Test Architecture
- **Feature-based organization**: Tests organized by feature (auth, ai_agents)
- **User story structure**: Tests grouped by user stories (AUTH-001, AUTH-002, etc.)
- **Multiple test types**: Unit, integration, and functional tests
- **Async testing**: Full async/await support with pytest-asyncio
- **Real databases**: Integration tests use real PostgreSQL for reliability
- **Coverage target**: Minimum 80% coverage required

## 🔐 Authentication System

**Status**: ✅ **Production Ready** - Modern feature-based architecture

- **JWT Authentication**: Access tokens (30min) + refresh tokens (7 days)
- **Password Security**: Bcrypt hashing with 12 rounds minimum
- **Rate Limiting**: 5 login attempts per 15 minutes per IP
- **Session Management**: Multi-session support with selective revocation
- **Security Features**: Account lockout, admin management, input validation
- **New Architecture**: Feature-based design with repository pattern

## 🤖 AI Agent System

**Status**: ✅ **Core Infrastructure Ready** - Database-driven prompt management

- **LangChain/LangGraph**: Multi-agent orchestration system
- **Specialized Agents**: Base, Structure, and Appeal evaluation agents
- **Database-driven Prompts**: Dynamic prompt loading and versioning
- **Industry Support**: Strategy/Tech/M&A/Financial Advisory/SI consulting
- **OpenAI & Anthropic**: Dual LLM provider support
- **Legacy Compatibility**: Smooth migration from legacy implementation

## 🚀 API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: Generated automatically by FastAPI

### Key Endpoints
```
# Authentication
POST /api/v1/auth/login           # User authentication
POST /api/v1/auth/register        # User registration
POST /api/v1/auth/refresh         # Token refresh
POST /api/v1/auth/logout          # Session termination
GET  /api/v1/auth/me              # Current user profile
GET  /api/v1/auth/sessions        # List user sessions
POST /api/v1/auth/sessions/revoke # Revoke specific session
POST /api/v1/auth/change-password # Change password

# System
GET  /health                      # Health check
GET  /                            # API information
GET  /docs                        # Swagger documentation
```

## 🔧 Development Workflow

### 1. Environment Setup
```bash
# Use the project development script (recommended)
./scripts/docker-dev.sh up

# Or manual setup:
cp backend/.env.example backend/.env
# Edit .env with your configuration
docker-compose up --build
```

### 2. Code Standards
- **Architecture**: Follow feature-based organization
- **API Design**: OpenAPI 3.0 specification with FastAPI
- **Database**: Use async SQLAlchemy 2.0, no raw SQL
- **Timezone**: ALWAYS use `app.core.datetime_utils.utc_now()`
- **Security**: No hardcoded secrets, use environment variables
- **Testing**: 80% minimum coverage, organized by feature
- **Type Hints**: Full type annotations required

### 3. Development Process
```bash
# Check Docker services status
./scripts/docker-dev.sh status

# Start development environment
./scripts/docker-dev.sh up

# Make code changes
# Run tests and linting
./scripts/docker-dev.sh shell backend
pytest
black app tests
flake8 app tests
mypy app

# Create feature branch from sprint branch
git checkout sprint-004
git checkout -b feature/UPLOAD-001-file-validation
```

## 🚦 Current Status

### ✅ **Production Ready**
- Modern feature-based architecture implemented
- Authentication system with advanced security
- AI agent infrastructure with LangChain/LangGraph
- Database-driven prompt management system
- Comprehensive async testing framework
- Docker development environment

### 🔄 **Sprint 003 In Progress** (File Upload Pipeline)
- UPLOAD-001: File upload interface ✅
- UPLOAD-002: File validation 🔄
- UPLOAD-003: Text extraction 🔄
- UPLOAD-004: Progress feedback 🔄

### 📋 **Next Priorities**
- Complete file upload and processing pipeline
- Resume analysis API endpoints
- Multi-industry AI agent specializations
- Performance monitoring and optimization

## 🛡 Security

- **Zero hardcoded secrets** - All configuration via environment variables
- **JWT security** - Access tokens (30min) + rotating refresh tokens (7 days)
- **Password security** - Bcrypt with 12+ rounds, strength validation
- **Rate limiting** - Distributed Redis-based protection (5 attempts/15min)
- **Input validation** - Comprehensive Pydantic schema validation
- **CORS protection** - Configured for specific origins only
- **Account protection** - Lockout mechanisms, admin controls
- **Security headers** - OWASP recommended headers

## 🐛 Troubleshooting

### Common Issues
1. **Port conflicts**: Use `./scripts/docker-dev.sh status` to check services
2. **Environment setup**: Copy `.env.example` to `.env` and configure
3. **Docker issues**: Use development script for consistent environment
4. **Database connection**: Ensure PostgreSQL is running before backend
5. **Test failures**: Check Redis/PostgreSQL are accessible for integration tests

### Logs and Debugging
```bash
# Using development script (recommended)
./scripts/docker-dev.sh logs backend
./scripts/docker-dev.sh logs

# Direct Docker commands
docker-compose logs backend
docker-compose logs -f  # Follow logs

# Application logs location
backend/logs/  # Application-specific logs
```

## 📊 Development Metrics

- **Architecture**: Modern feature-based organization
- **Dependencies**: 51 production + development packages
- **Test Coverage**: 80% minimum requirement
- **Code Quality**: Black + flake8 + mypy enforcement
- **Security**: Multiple layers of protection
- **Performance**: Async throughout the stack

---

*Last Updated: Sprint 003 - Modern architecture with AI agents and file upload pipeline*