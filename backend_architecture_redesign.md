# Backend Architecture Redesign Plan

## Executive Summary

This document outlines a comprehensive redesign of the AI Resume Review Platform's backend architecture. The redesign addresses current architectural limitations and establishes a scalable, maintainable foundation for future growth.

### Key Problems Being Solved

1. **Poor Feature Discovery**: Current structure scatters feature code across technical layers
2. **Missing Domain Models**: Database tables exist without corresponding SQLAlchemy models
3. **Tight AI Coupling**: AI logic intertwined with business logic
4. **No Infrastructure Abstraction**: Direct dependencies on PostgreSQL, Redis, and storage

### Redesign Goals

- **Feature-Based Organization**: Group all related code by business feature
- **AI Separation**: Complete isolation of AI capabilities behind interfaces
- **Infrastructure Layer**: Abstract all external dependencies
- **Developer Experience**: Make codebase self-documenting and intuitive

## Current vs. Proposed Architecture

### Current Structure (Problems)
```
backend/app/
├── api/auth.py              # Only auth endpoints (where are others?)
├── models/                  # Only auth models (missing business models)
├── services/                # Single service file
├── ai/                      # AI tightly coupled with business logic
└── database/                # Direct database access
```

### Proposed Structure (Solutions)
```
backend/
├── app/
│   ├── core/                    # Shared utilities
│   ├── features/                # Business features (vertical slices)
│   │   ├── auth/               # Complete auth feature
│   │   ├── upload/             # Complete upload feature
│   │   └── resume_review/      # Complete review feature
│   ├── ai_agents/              # Isolated AI module
│   │   ├── interface.py        # Public contracts only
│   │   └── prompts/            # Externalized prompt management
│   └── infrastructure/         # External service abstractions
│       ├── persistence/        # Database & cache
│       └── storage/           # File storage
└── tests/                       # Cross-cutting tests only
    ├── e2e/                    # End-to-end tests
    └── performance/            # Performance tests
```

## Detailed Architecture Design

### 1. Feature-Based Architecture

Each feature is a self-contained module with all related code AND tests in one place:

```python
features/resume_review/
├── __init__.py      # Public exports
├── api.py           # FastAPI routes
├── models.py        # SQLAlchemy models
├── schemas.py       # Pydantic schemas
├── service.py       # Business logic
├── repository.py    # Data access
└── tests/           # Feature-specific tests
    ├── __init__.py
    ├── unit/        # Pure unit tests
    │   ├── test_service.py
    │   ├── test_repository.py
    │   └── test_schemas.py
    ├── integration/ # Tests with real DB/Redis
    │   ├── test_api.py
    │   └── test_workflow.py
    └── fixtures/    # Test data and mocks
        ├── sample_resumes.py
        └── mock_responses.py
```

**Benefits:**
- Tests are co-located with the code they test
- Developers instantly know where to find feature code AND tests
- Easy to understand feature boundaries
- Natural code coverage tracking per feature
- Supports feature team ownership

### 2. AI Agents Module (Separated)

Complete separation of AI concerns with pluggable architecture:

```python
ai_agents/
├── interface.py              # Public contracts (Protocol classes)
├── client.py                 # Main AI service facade
├── prompts/
│   ├── templates/           # YAML prompt files
│   │   ├── resume/
│   │   │   ├── structure_v1.yaml
│   │   │   └── appeal_v1.yaml
│   ├── loader.py            # Prompt loading system
│   └── versioning.py        # A/B testing support
├── agents/                  # Agent implementations
├── providers/               # LLM providers (OpenAI, Anthropic)
└── workflows/              # LangGraph orchestration
```

**Key Design Decisions:**

1. **Prompts as Configuration**: All prompts in YAML files, not code
2. **Provider Agnostic**: Easy switching between LLM providers
3. **Version Control**: Built-in prompt versioning and A/B testing
4. **Interface-Based**: Features depend only on interfaces, not implementations

#### Example Prompt File (YAML):
```yaml
# ai_agents/prompts/templates/resume/structure_v2.yaml
metadata:
  name: structure_analysis
  version: 2.0.0
  model: gpt-4
  temperature: 0.3

prompts:
  system: |
    You are an expert resume analyst specializing in document structure.
    Focus on formatting, organization, and visual presentation.
    
  user: |
    Analyze this resume for structural quality:
    Industry: {industry}
    Resume: {resume_text}

variables:
  - industry: required
  - resume_text: required
```

### 3. Infrastructure Layer

All external dependencies abstracted behind interfaces:

```python
infrastructure/
├── persistence/
│   ├── postgres/
│   │   ├── connection.py    # Connection pool management
│   │   ├── base.py          # Base repository class
│   │   └── migrations/      # Alembic migrations
│   └── redis/
│       ├── cache.py         # Caching service
│       ├── session_store.py # JWT token storage
│       └── rate_limiter.py  # Rate limiting
└── storage/
    ├── interface.py         # Storage protocol
    ├── manager.py           # Storage orchestration
    └── providers/
        ├── local.py         # Local filesystem
        ├── gcs.py          # Google Cloud Storage
        └── s3.py           # AWS S3
```

**Design Patterns Used:**
- **Repository Pattern**: Abstract data access
- **Strategy Pattern**: Swappable storage providers
- **Dependency Injection**: All dependencies injected via FastAPI

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
**Goal**: Establish new structure without breaking existing code

1. Create new directory structure
2. Implement infrastructure layer
3. Create AI agents interface
4. Set up dependency injection

**Deliverables:**
- [ ] `infrastructure/` module complete
- [ ] `ai_agents/interface.py` defined
- [ ] Base repository classes implemented
- [ ] DI container configured

### Phase 2: Auth Migration (Week 2)
**Goal**: Migrate authentication to new structure as proof of concept

1. Create `features/auth/` module
2. Move existing auth code
3. Implement repository pattern
4. Update tests

**Deliverables:**
- [ ] Auth feature fully migrated
- [ ] All auth tests passing
- [ ] Documentation updated

### Phase 3: Upload Implementation (Week 3)
**Goal**: Implement missing upload functionality in new structure

1. Create `features/upload/` module
2. Implement file upload API
3. Add text extraction service
4. Create storage integration

**Deliverables:**
- [ ] Upload API endpoints working
- [ ] File storage integrated
- [ ] Text extraction implemented
- [ ] Tests with 80% coverage

### Phase 4: Resume Review Migration (Week 4)
**Goal**: Migrate analysis functionality to resume_review feature

1. Create `features/resume_review/` module
2. Implement missing SQLAlchemy models
3. Integrate with AI agents module
4. Add caching layer

**Deliverables:**
- [ ] Review feature complete
- [ ] AI integration working
- [ ] Caching implemented
- [ ] End-to-end tests passing

### Phase 5: AI Agents Completion (Week 5)
**Goal**: Finalize AI separation and prompt management

1. Migrate all prompts to YAML
2. Implement prompt versioning
3. Add provider abstraction
4. Create mock provider for testing

**Deliverables:**
- [ ] All prompts in YAML format
- [ ] Versioning system working
- [ ] Mock provider for tests
- [ ] AI module fully isolated

### Phase 6: Cleanup & Documentation (Week 6)
**Goal**: Remove old code and update all documentation

1. Remove deprecated code
2. Update API documentation
3. Create architecture diagrams
4. Write migration guide

**Deliverables:**
- [ ] Old structure removed
- [ ] README updated
- [ ] API docs complete
- [ ] Architecture diagrams created

## Migration Strategy

### Incremental Migration Approach

1. **Parallel Structure**: Build new structure alongside existing code
2. **Feature by Feature**: Migrate one feature at a time
3. **Backwards Compatible**: Maintain API compatibility throughout
4. **Test Coverage**: Ensure tests pass at each step

### Migration Checklist for Each Feature

- [ ] Create feature directory structure with tests folder
- [ ] Define SQLAlchemy models matching database
- [ ] Implement repository with base class
- [ ] Create service with business logic
- [ ] Define Pydantic schemas for API
- [ ] Implement API routes
- [ ] Write unit tests in `feature/tests/unit/`
- [ ] Write integration tests in `feature/tests/integration/`
- [ ] Create test fixtures in `feature/tests/fixtures/`
- [ ] Update dependency injection
- [ ] Achieve 80% test coverage for the feature
- [ ] Remove old implementation
- [ ] Update documentation

## Code Examples

### 1. Feature Module Example

```python
# features/resume_review/service.py
from typing import Optional
from uuid import UUID
from app.ai_agents import AIAnalyzer
from app.infrastructure.storage import StorageManager
from app.infrastructure.persistence.redis import CacheService

class ResumeReviewService:
    """Resume review business logic"""
    
    def __init__(
        self,
        repository: ResumeReviewRepository,
        ai_service: AIAnalyzer,
        storage: StorageManager,
        cache: CacheService
    ):
        self.repository = repository
        self.ai = ai_service
        self.storage = storage
        self.cache = cache
    
    async def analyze_resume(
        self,
        file: UploadFile,
        user_id: UUID,
        industry: str
    ) -> AnalysisResult:
        # Store file
        stored_file = await self.storage.store_resume(file, user_id)
        
        # Extract text (with caching)
        text = await self._extract_text_cached(stored_file)
        
        # Create analysis request
        request = await self.repository.create_request(
            user_id=user_id,
            filename=file.filename,
            storage_key=stored_file.key
        )
        
        # Run AI analysis
        ai_result = await self.ai.analyze_resume(
            text=text,
            industry=industry
        )
        
        # Store and return results
        return await self.repository.store_result(
            request_id=request.id,
            analysis=ai_result
        )
```

### 2. Repository Pattern Example

```python
# features/resume_review/repository.py
from app.infrastructure.persistence.postgres import BaseRepository

class ResumeReviewRepository(BaseRepository[AnalysisRequest]):
    """Data access for resume reviews"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, AnalysisRequest)
    
    async def get_user_requests(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[AnalysisRequest]:
        query = select(AnalysisRequest).where(
            AnalysisRequest.user_id == user_id
        ).order_by(
            AnalysisRequest.created_at.desc()
        ).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def create_request(
        self,
        user_id: UUID,
        filename: str,
        storage_key: str
    ) -> AnalysisRequest:
        return await self.create(
            user_id=user_id,
            original_filename=filename,
            file_path=storage_key,
            status="pending"
        )
```

### 3. AI Interface Example

```python
# ai_agents/interface.py
from typing import Protocol
from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    """Input for AI analysis"""
    text: str
    industry: str
    role: str = "consultant"

class AnalysisResult(BaseModel):
    """Output from AI analysis"""
    overall_score: int
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]

class AIAnalyzer(Protocol):
    """Interface that features depend on"""
    async def analyze_resume(
        self,
        request: AnalysisRequest
    ) -> AnalysisResult:
        ...
```

## Testing Strategy

### Test Organization - Co-located with Code

Tests are organized alongside the code they test, following the principle of high cohesion:

```
backend/
├── app/
│   ├── features/
│   │   ├── auth/
│   │   │   ├── api.py
│   │   │   ├── service.py
│   │   │   ├── repository.py
│   │   │   └── tests/              # Auth-specific tests
│   │   │       ├── unit/
│   │   │       │   ├── test_service.py
│   │   │       │   └── test_repository.py
│   │   │       └── integration/
│   │   │           └── test_api.py
│   │   │
│   │   ├── upload/
│   │   │   └── tests/              # Upload-specific tests
│   │   │
│   │   └── resume_review/
│   │       └── tests/              # Review-specific tests
│   │
│   ├── ai_agents/
│   │   └── tests/                  # AI module tests
│   │       ├── test_agents.py
│   │       ├── test_prompt_loader.py
│   │       └── test_providers.py
│   │
│   └── infrastructure/
│       └── tests/                  # Infrastructure tests
│           ├── test_postgres.py
│           ├── test_redis.py
│           └── test_storage.py
│
└── tests/                          # Only cross-cutting tests
    ├── e2e/                       # End-to-end scenarios
    │   ├── test_full_upload_flow.py
    │   └── test_resume_analysis_flow.py
    ├── performance/               # Load and stress tests
    │   └── test_load.py
    └── contract/                  # API contract tests
        └── test_api_contracts.py
```

### Test Categories

1. **Unit Tests** (`unit/`): 
   - Pure unit tests with all dependencies mocked
   - Fast execution (< 100ms per test)
   - Run on every commit
   - Located in `feature/tests/unit/`

2. **Integration Tests** (`integration/`):
   - Test with real database and Redis
   - Test API endpoints with dependencies
   - Run on pull requests
   - Located in `feature/tests/integration/`

3. **E2E Tests** (`tests/e2e/`):
   - Complete user workflows
   - Full system validation
   - Run before deployment
   - Located in root `tests/e2e/`

4. **Performance Tests** (`tests/performance/`):
   - Load testing and benchmarks
   - Run nightly or on-demand
   - Located in root `tests/performance/`

### Test Configuration

```ini
# backend/pytest.ini
[tool:pytest]
testpaths = app tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Pure unit tests (no external dependencies)
    integration: Tests requiring database/redis
    e2e: End-to-end tests
    slow: Tests that take > 1 second
    
addopts = 
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

### Running Tests

```bash
# Run all tests
pytest

# Run only unit tests (fast)
pytest -m unit

# Run specific feature tests
pytest app/features/resume_review/tests/

# Run with coverage for specific feature
pytest app/features/resume_review/ --cov=app/features/resume_review

# Run integration tests
pytest -m integration

# Run e2e tests
pytest tests/e2e/
```

### Test Guidelines

1. **Co-location**: Keep tests next to the code they test
2. **Isolation**: Each test should be independent
3. **Coverage**: Minimum 80% per feature
4. **Naming**: Test names should describe the scenario
5. **Fixtures**: Share fixtures within feature, not globally
6. **Mocking**: Mock at the boundary (repositories, external services)

### Migration from User Story Tests

Current user story tests (e.g., `AUTH-001_user_login`) will be:
1. Kept temporarily as acceptance criteria
2. Gradually migrated to feature test directories
3. Test names will preserve story references:

```python
# app/features/auth/tests/integration/test_api.py
class TestAuthAPI:
    @pytest.mark.integration
    async def test_AUTH_001_user_login_valid_credentials(self):
        """AUTH-001: User should be able to login with valid credentials"""
        # Test implementation
```

## Performance Considerations

### Optimization Strategies

1. **Connection Pooling**: PostgreSQL and Redis connection pools
2. **Caching Layer**: Redis caching for expensive operations
3. **Async Operations**: Full async/await support
4. **Lazy Loading**: Load AI models on demand
5. **Request Batching**: Batch AI requests when possible

### Scalability Planning

- **Horizontal Scaling**: Stateless design supports multiple instances
- **Queue Integration**: Ready for Celery/RabbitMQ integration
- **Microservices Ready**: Each feature can become a service
- **Database Sharding**: Repository pattern supports sharding

## Security Considerations

### Security Measures

1. **Dependency Injection**: No hardcoded credentials
2. **Interface Segregation**: Features only access what they need
3. **Input Validation**: Pydantic schemas validate all inputs
4. **SQL Injection Prevention**: SQLAlchemy parameterized queries
5. **File Upload Security**: Virus scanning and type validation

## Success Metrics

### Technical Metrics

- [ ] 80% test coverage achieved
- [ ] All features follow new structure
- [ ] API response time < 200ms (p95)
- [ ] Zero breaking changes to API
- [ ] Documentation coverage 100%

### Developer Experience Metrics

- [ ] New developer onboarding < 1 day
- [ ] Feature location obvious from requirements
- [ ] Clear separation of concerns
- [ ] Consistent patterns across features

## Team Responsibilities

### Suggested Task Distribution

- **Backend Lead**: Infrastructure layer, migration strategy
- **Feature Developer 1**: Auth and upload features
- **Feature Developer 2**: Resume review feature
- **AI Engineer**: AI agents module and prompt management
- **DevOps**: Docker, CI/CD updates

## Risk Mitigation

### Identified Risks and Mitigations

1. **Risk**: Breaking existing functionality
   - **Mitigation**: Incremental migration with full test coverage

2. **Risk**: Performance degradation
   - **Mitigation**: Load testing at each phase

3. **Risk**: Team knowledge gaps
   - **Mitigation**: Pair programming and documentation

4. **Risk**: Scope creep
   - **Mitigation**: Strict phase boundaries

## Questions for Team Discussion

1. Should we implement event-driven architecture now or later?
2. Do we need multi-tenancy support in the initial design?
3. Should we add GraphQL alongside REST API?
4. What monitoring/observability tools should we integrate?
5. Do we need a separate service for file processing?

## Appendix

### A. Technology Stack

- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL 15 + SQLAlchemy 2.0
- **Cache**: Redis 7.0
- **AI/ML**: LangChain, LangGraph, OpenAI
- **Storage**: Google Cloud Storage / Local
- **Testing**: pytest, pytest-asyncio
- **Documentation**: OpenAPI/Swagger

### B. Coding Standards

- **Python**: PEP 8 with Black formatter
- **Type Hints**: Required for all public functions
- **Docstrings**: Google style
- **Testing**: AAA pattern (Arrange, Act, Assert)
- **Git**: Conventional commits

### C. References

- [Domain-Driven Design](https://martinfowler.com/tags/domain%20driven%20design.html)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Dependency Injection in FastAPI](https://fastapi.tiangolo.com/tutorial/dependencies/)

---

## Next Steps

1. **Review**: Team review and feedback on this plan
2. **Approval**: Get stakeholder sign-off
3. **Kickoff**: Schedule implementation kickoff meeting
4. **Sprint Planning**: Break down Phase 1 into sprint tasks
5. **Begin**: Start with infrastructure layer implementation

**Document Version**: 1.1.0  
**Last Updated**: 2025-01-07  
**Author**: Backend Architecture Team  
**Status**: DRAFT - Awaiting Review

### Changelog
- v1.1.0 (2025-01-07): Added co-located testing strategy with tests alongside feature code
- v1.0.0 (2025-01-07): Initial architecture redesign proposal