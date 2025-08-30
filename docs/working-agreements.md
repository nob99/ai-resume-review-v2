# Team Working Agreements

## Purpose
This document defines the shared agreements and practices our team follows to ensure smooth collaboration, high-quality code, and successful project delivery.

## 1. Onboarding & Documentation

### Required Reading for New Team Members
All new team members MUST read the following documents in order:
1. **Product Vision** (`docs/design/product_vision.md`) - Understand what we're building and why
2. **Architecture** (`docs/design/architecture.md`) - Understand technical decisions and system design
3. **Sprint Plan** (`docs/backlog/sprint-plan.md`) - Understand the implementation roadmap
4. **Current Sprint Backlog** (`docs/backlog/sprint-backlog-XXX.md`) - Understand current work
5. **This Working Agreements document** - Understand team practices

### Sprint 1 Deliverables Available 
**🏗️ Infrastructure Ready to Use**:
- **Database**: PostgreSQL + Redis setup via Docker (`./database/scripts/setup-dev-db.sh`)
- **Schema**: Complete user authentication tables with migrations
- **Backend**: FastAPI with JWT authentication, rate limiting, password security
- **AI Framework**: LangChain integration ready for resume analysis
- **Terraform**: GCP infrastructure as code setup
- **Documentation**: Complete database ER diagrams and API specifications

**📋 What This Means**:
- No need to set up basic infrastructure from scratch
- Database schema and authentication already working
- Focus on building features, not foundational setup
- All Sprint 1 code is production-ready and tested

### Documentation Maintenance
- Keep documentation up-to-date as the system evolves
- Document decisions in Architecture Decision Records (ADRs)
- Update README files when setup procedures change

## 2. Development Process

### Before Starting Any Coding Task
1. **ALWAYS discuss with Product Owner** before starting implementation
   - Clarify requirements and acceptance criteria
   - Confirm understanding of the user story
   - Discuss any technical concerns or alternatives
   
2. **Create/Update Technical Documentation**:
   - For database work: Create/update ER diagrams
   - For API work: Update OpenAPI specification
   - For infrastructure: Update architecture diagrams

### Definition of Ready
A story is ready for development when:
- [ ] Acceptance criteria are clear and agreed upon
- [ ] Technical approach discussed with team
- [ ] Dependencies identified
- [ ] Product Owner has approved the understanding

## 3. Technical Standards

### API Development
- **MUST follow OpenAPI 3.0 specification**
- All APIs must be documented in `docs/api/openapi.yaml` BEFORE implementation
- **📄 Current API Documentation**: Complete OpenAPI specification exists at `docs/api/openapi.yaml`
  - View at: http://localhost:8000/docs (when backend is running)
  - Updated through Sprint 2 with authentication endpoints
- Use consistent naming conventions:
  - REST endpoints: `/api/v1/resource-name`
  - Use kebab-case for URLs
  - Use camelCase for JSON properties

### Database Development
- **MUST create ER diagrams** before implementing database changes
- Store diagrams in `docs/database/` directory
- Use migration scripts for all schema changes
- Never modify database directly in production

### Database Testing Setup (Sprint 1 Infrastructure)
- **🗄️ Database Infrastructure Available**: Complete PostgreSQL + Redis setup from Sprint 1
- **Quick Start for Testing**: 
  ```bash
  # Start database and Redis (required for integration tests)
  ./database/scripts/setup-dev-db.sh
  
  # Verify database is running
  psql -h localhost -p 5432 -U postgres -d ai_resume_review_dev
  ```
- **Database Connection Details**:
  - Host: localhost, Port: 5432
  - Database: `ai_resume_review_dev` 
  - Username: postgres, Password: dev_password_123
  - Redis: localhost:6379 (no password)
- **Integration Tests**: Use real `ai_resume_review_dev` database (not separate test DB)
- **Test Data Management**: Tests create and clean up their own data
- **Required Services**: Both PostgreSQL AND Redis must be running for integration tests

### Infrastructure as Code
- **MUST use Terraform** for all infrastructure
- Store Terraform files in `infrastructure/` directory
- Follow Terraform best practices:
  - Use workspaces for environments
  - Store state in remote backend
  - Use modules for reusable components
  - Tag all resources appropriately

## 4. Code Quality Standards

### General Principles
- Write clean, readable code
- Follow SOLID principles
- Keep functions small and focused
- Write self-documenting code

### Language-Specific Standards

#### Python (Backend)
- Follow PEP 8
- Use type hints
- Format with Black
- Lint with pylint/flake8
- Minimum 80% test coverage

#### TypeScript (Frontend)
- Use strict mode
- Define interfaces for all data structures
- Use ESLint + Prettier
- Follow React best practices
- Write unit tests for logic, integration tests for components

### Testing Standards
#### Unit Tests
- **Coverage**: Minimum 80% test coverage for new code
- **Python**: Use pytest with comprehensive mocking
- **TypeScript**: Use Jest + React Testing Library
- **Fast Execution**: Unit tests should run without external dependencies

#### Integration Tests  
- **Database Required**: Must start database infrastructure before running
- **Setup Command**: `./database/scripts/setup-dev-db.sh` (starts PostgreSQL + Redis)
- **Real Database**: Use `ai_resume_review_dev` database (not mocked)
- **Test Isolation**: Each test cleans up its own data
- **API Testing**: Test full HTTP request/response cycle with real FastAPI app

#### Running Tests
```bash
# Unit tests only (fast, no database needed)
python -m pytest tests/test_*_unit.py -v

# Integration tests (requires database)
./database/scripts/setup-dev-db.sh  # Start database first
python -m pytest tests/test_*_integration.py -v

# All tests (requires database)
./database/scripts/setup-dev-db.sh
python -m pytest tests/ -v
```

### Code Review Process
- All code requires review before merge
- Use PR template for consistency
- Reviewer checklist:
  - [ ] Code follows standards
  - [ ] Tests are included
  - [ ] Documentation updated
  - [ ] No security vulnerabilities
  - [ ] Performance considered

## 5. Sprint Management

### Sprint Planning
- **Sprint planning is MANDATORY** before starting any new sprint
- **NEVER start a new sprint without proper planning**
- Sprint planning includes:
  - Review previous sprint completion
  - Select stories for new sprint
  - Team capacity planning
  - Risk identification
  - Sprint goal definition

### Sprint Branch Strategy
- **Create a new branch for each sprint**: `sprint-XXX` (e.g., `sprint-001`, `sprint-002`)
- All development for the sprint happens on the sprint branch
- Individual features branch off from the sprint branch
- **Sprint completion process**:
  1. Team and Product Owner agree on sprint completion
  2. All acceptance criteria verified
  3. Sprint branch is merged to main
  4. Tag the release (e.g., `sprint-001-complete`)
  5. Delete the sprint branch after successful merge

### Sprint Ceremonies
- **Sprint Planning**: First day of sprint (mandatory)
- **Daily Standup**: Every working day at 9:30 AM
- **Sprint Review**: Last day of sprint with PO
- **Sprint Retrospective**: After sprint review
- **NO development between sprints** - use time for planning and technical debt

## 6. Git Workflow

### Branch Naming
- Sprint: `sprint-XXX` (main development branch for the sprint)
- Feature: `feature/STORY-ID-short-description` (branches from sprint branch)
- Bugfix: `bugfix/STORY-ID-short-description`
- Hotfix: `hotfix/description` (only for production issues)

### Commit Messages
- Use conventional commits format
- Examples:
  - `feat: add user authentication`
  - `fix: resolve memory leak in file upload`
  - `docs: update API documentation`
  - `refactor: simplify agent orchestration logic`

### Pull Request Guidelines
- Keep PRs small and focused
- Include story ID in PR title
- Fill out PR template completely
- Ensure CI passes before requesting review

## 7. Communication

### Daily Standup
- Be on time (9:30 AM)
- Come prepared with updates
- Keep it under 15 minutes
- Format: Yesterday, Today, Blockers

### Slack Etiquette
- Use threads for discussions
- Update status when unavailable
- Response time expectation: within 2 hours during work hours
- Use appropriate channels:
  - `#dev-general` - Technical discussions
  - `#dev-random` - Non-work chat
  - `#dev-help` - Ask for assistance

### Meeting Culture
- Have agenda prepared
- Start and end on time
- Document decisions and action items
- Record meetings when appropriate

## 8. Definition of Done

A story/task is DONE when:
- [ ] Code is complete and follows standards
- [ ] Unit tests written and passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Code reviewed and approved
- [ ] Documentation updated (code, API, user docs)
- [ ] Deployed to development environment
- [ ] Acceptance criteria verified by PO
- [ ] No known bugs or tech debt introduced

## 9. Technical Debt Management

- Document tech debt in backlog
- Allocate 20% of sprint capacity for tech debt
- Prioritize security and performance debt
- Regular refactoring during development

## 10. Security Practices

- Never commit secrets or credentials
- Use environment variables for configuration
- Follow OWASP guidelines
- Regular dependency updates
- Security review for sensitive features

## 11. Performance Standards

- Page load time < 3 seconds
- API response time < 500ms (p95)
- Regular performance testing
- Monitor and alert on degradation

## 12. On-Call Responsibilities

(To be defined when we reach production)

## 13. Continuous Improvement

- Sprint retrospectives are mandatory
- Act on retrospective action items
- Regular team learning sessions
- Encourage experimentation and innovation

## Agreement Sign-off

By joining the team, all members agree to follow these working agreements. These agreements are living documents and can be updated through team consensus.

| Team Member | Date | Signature |
|-------------|------|-----------|
| [Name] | [Date] | [Signature] |
| [Name] | [Date] | [Signature] |
| [Name] | [Date] | [Signature] |
| [Name] | [Date] | [Signature] |
| [Name] | [Date] | [Signature] |

---

*Last Updated: December 2024 (Sprint 2 - Added database testing and API documentation details)*  
*Next Review: End of Sprint 3*