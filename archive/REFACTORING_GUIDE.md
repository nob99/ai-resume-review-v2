# Backend Refactoring Guide: Simplifying Architecture

## 📋 Overview

This guide provides a pragmatic approach to simplifying our backend architecture while maintaining code quality and testability. We follow the principle: **"Simple is best"** - use the right level of abstraction for each operation's complexity.

## 🎯 Refactoring Philosophy

**Before**: Every endpoint goes through all layers (API → Service → Repository)
```
API Layer → Service Layer → Repository Layer → Database
  (HTTP)    (Business Logic)    (SQL Queries)
```

**After**: Use layers based on complexity
```
Simple CRUD:   API Layer → Repository Layer → Database
Complex Logic: API Layer → Service Layer → Repository Layer → Database
```

## 📊 Decision Matrix: When to Use Each Layer

| Operation Type | Architecture | Use Service Layer? | Example |
|---------------|--------------|-------------------|---------|
| **Simple Read** | API → Repository | ❌ No | Get user by ID, List candidates |
| **Simple Create** | API → Repository | ❌ No | Create candidate (basic validation only) |
| **Simple Update** | API → Repository | ❌ No | Update candidate name |
| **Simple Delete** | API → Repository | ❌ No | Soft delete candidate |
| **Business Logic** | API → Service → Repository | ✅ Yes | Login (tokens + session), Password change |
| **Multi-step Operations** | API → Service → Repository | ✅ Yes | Resume upload (validate + extract + store) |
| **Multiple Tables** | API → Service → Repository | ✅ Yes | Create candidate + assign to user |
| **External Services** | API → Service → Repository | ✅ Yes | AI analysis, file storage, email |

## 🔍 How to Identify Candidates for Simplification

### Red Flags (Service Layer Not Adding Value)

1. **Pass-through methods** - Service just calls repository:
```python
# ❌ BAD: Service adds no value
class CandidateService:
    async def get_candidate_by_id(self, id: UUID) -> Candidate:
        return await self.repository.get_by_id(id)  # Just passing through!
```

2. **No business logic** - Only data transformation:
```python
# ❌ BAD: No validation, no rules, just data fetch
class CandidateService:
    async def list_candidates(self, user_id: UUID) -> List[Candidate]:
        return await self.repository.list_by_user(user_id)
```

3. **Single repository call** - No coordination needed:
```python
# ❌ BAD: One operation, no transaction management needed
class CandidateService:
    async def delete_candidate(self, id: UUID) -> bool:
        return await self.repository.delete(id)
```

### Green Flags (Service Layer Provides Value)

1. **Multiple operations in transaction**:
```python
# ✅ GOOD: Coordinates multiple operations
class ResumeUploadService:
    async def upload_resume(self, file: UploadFile, candidate_id: UUID):
        # 1. Validate file
        await self._validate_file(file)
        # 2. Extract text
        text = await self._extract_text(file)
        # 3. Save to DB
        resume = await self.resume_repo.create(...)
        # 4. Create analysis request
        await self.analysis_repo.create(...)
        return resume
```

2. **Business rules enforcement**:
```python
# ✅ GOOD: Implements business logic
class AuthService:
    async def login(self, credentials: LoginRequest):
        user = await self.user_repo.get_by_email(credentials.email)

        # Business rules
        if not user.is_active:
            raise SecurityError("Account deactivated")
        if user.is_account_locked():
            raise SecurityError("Account locked")
        if not user.check_password(credentials.password):
            raise SecurityError("Invalid credentials")

        # Create session and tokens (complex logic)
        return await self._create_session(user)
```

3. **Reusable across multiple endpoints**:
```python
# ✅ GOOD: Used by both API and background jobs
class AnalysisService:
    async def analyze_resume(self, resume_id: UUID):
        # Called by: POST /analyze, background worker, admin tools
        ...
```

## 📝 Refactoring Steps

### Step 1: Identify Simple CRUD Operations

Review your feature's API endpoints and mark them:
- ✅ Simple (can bypass service layer)
- ⚠️ Complex (keep service layer)

**Example for `candidate` feature**:
```python
# ✅ Simple CRUD - Refactor
GET    /candidates/{id}          # Just fetch and return
GET    /candidates               # List with filters
POST   /candidates               # Create with basic validation
PATCH  /candidates/{id}          # Update fields
DELETE /candidates/{id}          # Soft delete

# ⚠️ Complex - Keep Service Layer
POST   /candidates/{id}/assign   # Assign to user + create relationship
POST   /candidates/{id}/bulk-assign  # Multiple operations
```

### Step 2: Refactor Simple Endpoints

#### Before (with unnecessary service layer):
```python
# api.py
@router.get("/candidates/{id}")
async def get_candidate(
    id: UUID,
    service: CandidateService = Depends(get_candidate_service)
):
    candidate = await service.get_candidate_by_id(id)
    if not candidate:
        raise HTTPException(404, "Not found")
    return CandidateResponse.model_validate(candidate)

# service.py
class CandidateService:
    async def get_candidate_by_id(self, id: UUID) -> Optional[Candidate]:
        return await self.repository.get_by_id(id)  # Just passing through!

# repository.py
class CandidateRepository(BaseRepository[Candidate]):
    async def get_by_id(self, id: UUID) -> Optional[Candidate]:
        return await super().get_by_id(id)
```

#### After (simplified):
```python
# api.py
@router.get("/candidates/{id}")
async def get_candidate(
    id: UUID,
    repo: CandidateRepository = Depends(get_candidate_repository)
):
    """Get candidate by ID."""
    candidate = await repo.get_by_id(id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    return CandidateResponse.model_validate(candidate)

# repository.py (unchanged - inherits from BaseRepository)
class CandidateRepository(BaseRepository[Candidate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Candidate)
```

### Step 3: Update Dependency Injection

Add repository dependencies in `api.py`:

```python
# Add this function
async def get_candidate_repository(
    session: AsyncSession = Depends(get_async_session)
) -> CandidateRepository:
    """Dependency to get candidate repository."""
    return CandidateRepository(session)

# Keep service dependency only for complex operations
async def get_candidate_service(
    session: AsyncSession = Depends(get_async_session)
) -> CandidateService:
    """Dependency to get candidate service (for complex operations)."""
    return CandidateService(CandidateRepository(session))
```

### Step 4: Handle Common Patterns

#### Pattern 1: Simple List with Filters
```python
@router.get("/candidates", response_model=List[CandidateResponse])
async def list_candidates(
    user_id: Optional[UUID] = None,
    status: Optional[str] = None,
    repo: CandidateRepository = Depends(get_candidate_repository)
):
    """List candidates with optional filters."""
    filters = {}
    if user_id:
        filters["created_by_user_id"] = user_id
    if status:
        filters["status"] = status

    candidates = await repo.list(filters=filters)
    return [CandidateResponse.model_validate(c) for c in candidates]
```

#### Pattern 2: Simple Create
```python
@router.post("/candidates", response_model=CandidateResponse, status_code=201)
async def create_candidate(
    data: CandidateCreate,
    current_user: User = Depends(get_current_user),
    repo: CandidateRepository = Depends(get_candidate_repository)
):
    """Create a new candidate."""
    # Pydantic handles validation
    candidate = await repo.create(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        created_by_user_id=current_user.id
    )
    return CandidateResponse.model_validate(candidate)
```

#### Pattern 3: Simple Update
```python
@router.patch("/candidates/{id}", response_model=CandidateResponse)
async def update_candidate(
    id: UUID,
    data: CandidateUpdate,
    repo: CandidateRepository = Depends(get_candidate_repository)
):
    """Update candidate information."""
    # Check exists
    candidate = await repo.get_by_id(id)
    if not candidate:
        raise HTTPException(404, "Candidate not found")

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    updated = await repo.update(id, **update_data)

    return CandidateResponse.model_validate(updated)
```

### Step 5: Keep Service Layer for Complex Operations

```python
# Complex operation - KEEP service layer
@router.post("/candidates/{id}/resumes", response_model=UploadedFileV2)
async def upload_resume(
    id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: ResumeUploadService = Depends(get_resume_upload_service)
):
    """
    Upload resume (complex operation).

    Service handles:
    - File validation (size, type, virus scan)
    - Text extraction (PDF, DOCX parsing)
    - Version management (increment version number)
    - Database transaction (resume + metadata)
    """
    return await service.upload_resume(
        candidate_id=id,
        file=file,
        user_id=current_user.id
    )
```

## 🧪 Testing After Refactoring

### Test Structure for Simplified Endpoints

```python
# tests/features/candidate/test_candidate_api.py

@pytest.mark.asyncio
async def test_get_candidate_success(async_client, db_session, test_user):
    """Test getting candidate by ID (API → Repository)."""
    # Arrange: Create test candidate directly in DB
    candidate = Candidate(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        created_by_user_id=test_user.id
    )
    db_session.add(candidate)
    await db_session.commit()

    # Act: Call API
    response = await async_client.get(
        f"/api/v1/candidates/{candidate.id}",
        headers={"Authorization": f"Bearer {test_user.token}"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "John"
    assert data["email"] == "john@example.com"

@pytest.mark.asyncio
async def test_get_candidate_not_found(async_client, test_user):
    """Test 404 when candidate doesn't exist."""
    fake_id = uuid4()
    response = await async_client.get(
        f"/api/v1/candidates/{fake_id}",
        headers={"Authorization": f"Bearer {test_user.token}"}
    )
    assert response.status_code == 404
```

### Test Structure for Complex Operations (Keep Service Tests)

```python
# tests/features/resume_upload/test_service.py

@pytest.mark.asyncio
async def test_upload_resume_with_text_extraction(db_session, sample_pdf):
    """Test complex upload logic (use service layer)."""
    service = ResumeUploadService(db_session)

    result = await service.upload_resume(
        candidate_id=candidate_id,
        file=sample_pdf,
        user_id=user_id
    )

    assert result.status == ResumeStatus.COMPLETED
    assert result.extracted_text is not None
    assert len(result.extracted_text) > 0
```

## 📁 File Organization After Refactoring

```
backend/app/features/candidate/
├── api.py              # API endpoints (simplified CRUD calls repo directly)
├── service.py          # Business logic (ONLY complex operations)
├── repository.py       # Database access (unchanged)
├── schemas.py          # Pydantic models (unchanged)
└── tests/
    ├── test_api.py     # API tests (for simple endpoints)
    └── test_service.py # Service tests (for complex logic only)
```

## ✅ Checklist for Each Refactoring

Before refactoring an endpoint:
- [ ] Does the service method do more than just call repository?
- [ ] Are there multiple repository calls that need coordination?
- [ ] Are there business rules being enforced?
- [ ] Is this logic reused by other endpoints or background jobs?

If all answers are NO → **Simplify by removing service layer**

After refactoring:
- [ ] Tests still pass
- [ ] API behavior unchanged (same inputs/outputs)
- [ ] Error handling maintained
- [ ] Authorization/authentication unchanged
- [ ] Update API documentation if needed

## 🚫 What NOT to Change

Keep these as-is:
1. **Repository layer** - Always keep this for database abstraction
2. **Schemas** - Required by FastAPI, provides validation
3. **Complex services** - Auth, Resume Analysis, File Upload
4. **Database models** - No changes needed
5. **Tests** - Update test structure but keep test coverage

## 📖 Examples from Codebase

### Simple CRUD (Refactor These)
- `GET /candidates/{id}` - Just fetch and return
- `GET /candidates` - List with basic filters
- `PATCH /candidates/{id}` - Update fields
- `DELETE /candidates/{id}` - Soft delete

### Complex Operations (Keep Service Layer)
- `POST /auth/login` - Token generation, session management, account locking
- `POST /candidates/{id}/resumes` - File validation, text extraction, versioning
- `POST /resumes/{id}/analyze` - AI analysis, prompt selection, result storage
- `POST /auth/change-password` - Password validation, session revocation

## 🎓 Best Practices

1. **Start with read operations** - Safest to refactor first
2. **Test after each endpoint** - Don't refactor everything at once
3. **Keep git history clean** - One feature per commit
4. **Document breaking changes** - Update API docs if needed
5. **Get code review** - Have another engineer verify the simplification

## 📚 References

- [Martin Fowler - Anemic Domain Model](https://martinfowler.com/bliki/AnemicDomainModel.html)
- [Microsoft - Layered Architecture](https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/ddd-oriented-microservice)
- [YAGNI Principle](https://martinfowler.com/bliki/Yagni.html) - You Aren't Gonna Need It

---

**Last Updated**: 2025-09-30
**Version**: 1.0
**Status**: Active Refactoring Guide