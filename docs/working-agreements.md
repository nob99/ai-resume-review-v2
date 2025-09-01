# Team Working Agreements (Draft - v2.0)

## 📋 Table of Contents
1. [Overview & Purpose](#overview)
2. [Cross-Functional Team Agreements](#cross-functional)
3. [Frontend Team Guidelines](#frontend-team)
4. [Backend Team Guidelines](#backend-team)
5. [DevOps Team Guidelines](#devops-team)
6. [AI/ML Team Guidelines](#aiml-team)

---

## 🎯 Overview & Purpose {#overview}

This document defines the shared agreements and practices our team follows to ensure smooth collaboration, high-quality code, and successful project delivery. Each team has specific guidelines while maintaining cross-functional standards.

### Document Structure
- **Cross-Functional**: Practices that apply to ALL team members
- **Team-Specific**: Guidelines for specialized teams (Frontend, Backend, DevOps, AI/ML)
- **Project Management**: Sprint and process management

### Quick Links for New Team Members
1. **Product Vision** (`docs/design/product_vision.md`)
2. **Architecture** (`docs/design/architecture.md`)
3. **Sprint Plan** (`docs/backlog/sprint-0-plan.md`)
4. **Current Sprint** (`docs/backlog/sprint-XXX-backlog.md`)
5. **Team-Specific Section** (see your team's section below)

---

## 🤝 Cross-Functional Team Agreements {#cross-functional}

### 1. Onboarding Process
All new team members MUST:
- [ ] Read required documentation in order (see Quick Links above)
- [ ] Set up development environment per team guidelines
- [ ] Complete team-specific onboarding checklist
- [ ] Attend sprint ceremonies within first week

### 2. Communication Standards

#### Daily Standup
- **Time**: 9:30 AM daily
- **Format**: Yesterday, Today, Blockers
- **Duration**: Max 15 minutes
- **Preparation**: Update tickets before standup

#### Slack Etiquette
- Use threads for discussions
- Update status when unavailable
- Response time: within 2 hours during work hours
- Channels:
  - `#dev-general` - Technical discussions
  - `#dev-frontend` - Frontend specific
  - `#dev-backend` - Backend specific
  - `#dev-devops` - Infrastructure/DevOps
  - `#dev-aiml` - AI/ML discussions
  - `#dev-help` - Ask for assistance

### 3. Git Workflow

#### Branch Naming
- Sprint: `sprint-XXX` (main development branch)
- Feature: `feature/STORY-ID-short-description`
- Bugfix: `bugfix/STORY-ID-short-description`
- Hotfix: `hotfix/description` (production only)

#### Commit Messages
```
<type>: <subject>

<body>

<footer>
```
Types: feat, fix, docs, style, refactor, test, chore

### 4. Code Review Process
- All code requires review before merge
- Use PR template
- Checklist:
  - [ ] Follows team coding standards
  - [ ] Tests included and passing
  - [ ] Documentation updated
  - [ ] No security vulnerabilities
  - [ ] Performance considered

### 5. Definition of Done
A story is DONE when:
- [ ] Code complete and follows standards
- [ ] Unit tests written and passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Deployed to development environment
- [ ] Acceptance criteria verified by PO

### 6. Security Standards
- Never commit secrets or credentials
- Use environment variables for configuration
- Follow OWASP guidelines
- Regular dependency updates
- Security review for sensitive features

### 7. Meeting Culture
- Have agenda prepared
- Start and end on time
- Document decisions and action items
- Record when appropriate

### 8. Sprint Management

#### Sprint Planning
- **MANDATORY before starting any sprint**
- Includes:
  - Previous sprint review
  - Story selection and estimation
  - Team capacity planning
  - Risk identification
  - Sprint goal definition

#### Sprint Ceremonies
- **Planning**: First day of sprint
- **Daily Standup**: Every day at 9:30 AM
- **Sprint Review**: Last day with PO
- **Retrospective**: After review
- **NO development between sprints**

#### Sprint Branches
- Create `sprint-XXX` for each sprint
- All features branch from sprint branch
- Merge to main after sprint completion
- Tag release: `sprint-XXX-complete`

### 9. Technical Debt Management
- Document all tech debt in backlog
- Allocate 20% sprint capacity for debt
- Prioritize security and performance debt
- Regular refactoring

### 10. Definition of Ready
A story is ready when:
- [ ] Acceptance criteria clear
- [ ] Technical approach discussed
- [ ] Dependencies identified
- [ ] PO approved understanding

---

## 🎨 Frontend Team Guidelines {#frontend-team}

### ⚠️ MANDATORY: Architecture Patterns
**All frontend engineers MUST follow the patterns documented in `frontend/README.md`**

### Critical Rules

#### 1. Separation of Concerns
**✅ API Layer (`src/lib/api.ts`)**:
- Make HTTP requests
- Handle token refresh
- Transform errors to typed classes
- Return `ApiResult<T>` pattern
- **NEVER handle navigation or UI logic**

**✅ UI Layer (Components/Context)**:
- Handle navigation decisions
- Display appropriate UI feedback
- Manage local state
- Use auth context for auth state

**❌ FORBIDDEN**:
```typescript
// NEVER do this in api.ts
window.location.href = '/login'  // VIOLATES separation of concerns
```

#### 2. Error Handling
Use custom error types:
- `AuthExpiredError` - Session expired
- `AuthInvalidError` - Invalid credentials
- `NetworkError` - Connection issues

#### 3. Technology Stack
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS
- **Forms**: React Hook Form
- **Testing**: Jest + React Testing Library
- **API Client**: Axios with interceptors

### Development Standards

#### TypeScript
- No `any` types
- Define interfaces for all data
- Use strict null checks
- Proper error boundaries

#### Component Guidelines
- Use design system components (`src/components/ui/`)
- Follow existing patterns
- Handle loading states
- Implement proper accessibility

#### Testing Requirements
- Unit tests for logic
- Integration tests for user flows
- Minimum 80% coverage
- Mock API layer properly

#### Performance Standards
- Page load < 3 seconds
- No unnecessary re-renders
- Optimize bundle size
- Lazy load when appropriate

---

## ⚡ Backend Team Guidelines {#backend-team}

### Technology Stack
- **Framework**: FastAPI
- **Database**: PostgreSQL + Redis
- **ORM**: SQLAlchemy
- **Testing**: pytest
- **Documentation**: OpenAPI 3.0

### API Development Standards

#### 1. API Design
- **MUST follow OpenAPI 3.0 specification**
- Document in `docs/api/openapi.yaml` BEFORE implementation
- REST endpoints: `/api/v1/resource-name`
- Use kebab-case for URLs
- Use camelCase for JSON properties

#### 2. FastAPI Patterns
```python
@router.post("/resource", response_model=ResourceResponse)
async def create_resource(
    resource_data: ResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Always include docstring with endpoint description."""
    pass
```

### Database Standards

#### 1. Development Process
- **MUST create ER diagrams** before database changes
- **📖 Database Documentation**: See `database/README.md` for complete schema, setup, and migration guide
- Use migration scripts for all changes
- Never modify database directly in production

#### 2. Configuration Management
- **🔐 NEVER hardcode credentials**
- Use centralized config from `app.core.config`
- Required setup:
  ```bash
  cp backend/.env.example backend/.env
  # Edit .env with your local values
  ```

#### 3. Timezone Handling
- **🌍 ALWAYS use timezone-aware datetimes**
- **❌ NEVER use `datetime.utcnow()`**
- **✅ Use `app.core.datetime_utils.utc_now()`**
- Store ALL timestamps in UTC
- Use `DateTime(timezone=True)` in models

### Python Standards
- Follow PEP 8
- Use type hints
- Format with Black
- Lint with pylint/flake8
- Docstrings for all public functions

### Testing Requirements
- pytest for all tests
- Minimum 80% coverage
- Unit tests with mocking
- Integration tests with real database
- Organize by user story: `tests/auth/AUTH-001_user_login/`

### Security Patterns
- Bcrypt for password hashing (12 rounds)
- JWT tokens with proper expiration
- Rate limiting on sensitive endpoints
- Input validation and sanitization

---

## 🚀 DevOps Team Guidelines {#devops-team}

### Infrastructure Standards

#### 1. Infrastructure as Code
- **MUST use Terraform** for all infrastructure
- Store in `infrastructure/` directory
- Use workspaces for environments
- Tag all resources appropriately

#### 2. Container Standards
- Docker for all services
- Multi-stage builds for production
- Security scanning on all images
- Use official base images

### Environment Management
- Development: Local Docker Compose
- Staging: GCP with Terraform
- Production: GCP with Terraform
- Use secrets management (GCP Secret Manager)

### CI/CD Pipeline
- GitHub Actions for automation
- Run tests on every PR
- Security scanning included
- Automated deployment to staging

### Monitoring & Logging
- Structured logging (JSON format)
- Centralized log aggregation
- Application performance monitoring
- Alert on critical metrics

### Database Operations
- Automated backups (daily)
- Point-in-time recovery capability
- Migration scripts in CI/CD
- Performance monitoring

### Deployment Process
1. PR merged to sprint branch
2. CI runs tests and security checks
3. Deploy to staging automatically
4. Manual approval for production
5. Automated rollback capability

---

## 🤖 AI/ML Team Guidelines {#aiml-team}

### AI Framework Standards

#### 1. LangChain Integration
- Use official LangChain patterns
- Version pin all dependencies
- Document prompt templates
- Test with multiple models

#### 2. Model Management
- Version all model artifacts
- Document model performance
- A/B testing framework
- Rollback capability

### Development Process

#### 1. Data Pipeline
- Validate all input data
- Handle edge cases gracefully
- Log all transformations
- Performance monitoring

#### 2. Prompt Engineering
```python
# Store prompts in separate files
RESUME_ANALYSIS_PROMPT = """
Analyze the following resume and provide structured feedback:
...
"""
```

### Testing AI Components
- Unit tests for data processing
- Integration tests with mock LLMs
- Performance benchmarks
- Quality evaluation metrics

### Ethical AI Considerations
- No bias in resume screening
- Transparent scoring criteria
- User data privacy
- Explainable AI decisions

### Performance Standards
- Response time < 5 seconds
- Concurrent request handling
- Graceful degradation
- Cost optimization

---

---

*Last Updated: Sprint 002 - Team-based reorganization*