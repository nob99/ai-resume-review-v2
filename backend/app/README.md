# Backend Architecture Guide

## 📁 Feature Structure

Each feature follows this structure:
```
features/feature_name/
├── api.py          # HTTP endpoints
├── service.py      # Business logic (optional)
├── repository.py   # Database operations
└── schemas.py      # Request/response models
```

## 🎯 Layer Responsibilities

### **api.py** - HTTP Interface Layer
**Role**: Handle HTTP concerns only

✅ **DO**:
- Request/response handling
- HTTP status codes (200, 404, 500)
- Authentication/authorization (via Depends)
- Rate limiting
- Input validation (Pydantic)

❌ **DON'T**:
- Business logic
- Direct database queries
- Complex calculations

**Complexity**: Simple - thin layer

---

### **service.py** - Business Logic Layer (Optional)
**Role**: Orchestrate business rules

✅ **DO**:
- Multi-step operations
- Business rule enforcement
- Transaction coordination
- External service calls (AI, email, file storage)
- Integration between multiple repositories

❌ **DON'T**:
- HTTP concerns (status codes, headers)
- Direct SQL queries (use repository)

**Complexity**: Can be complex

⚠️ **When to skip**: For simple CRUD operations, call repository directly from API

---

### **repository.py** - Data Access Layer
**Role**: Database operations ONLY

✅ **DO**:
- SQL queries (SELECT, INSERT, UPDATE, DELETE)
- Query optimization
- Data mapping (DB ↔ models)

❌ **DON'T**:
- Business logic
- Business rules
- Validation (beyond SQL constraints)

**Complexity**: Can be complex for SQL optimization, but NO business decisions

---

### **schemas.py** - Data Transfer Objects
**Role**: API request/response validation

✅ **DO**:
- Define Pydantic models
- Field validation rules
- Serialization

❌ **DON'T**:
- Business logic

**Complexity**: Simple - declarative only

---

## 📊 Decision Matrix

| Concern | API | Service | Repository |
|---------|:---:|:-------:|:----------:|
| HTTP status codes | ✅ | ❌ | ❌ |
| Auth checks | ✅ | ❌ | ❌ |
| Business rules | ❌ | ✅ | ❌ |
| Multi-step workflows | ❌ | ✅ | ❌ |
| External APIs | ❌ | ✅ | ❌ |
| SQL queries | ❌ | ❌ | ✅ |
| Query optimization | ❌ | ❌ | ✅ |

---

## 🔑 Key Principle

```
Repository = "How to store/retrieve data"
Service    = "What to do with that data"
API        = "How to expose it via HTTP"
```

---

## ✅ Examples

### Simple CRUD (API → Repository)
```python
# api.py
@router.get("/candidates/{id}")
async def get_candidate(
    id: UUID,
    repo: CandidateRepository = Depends(get_repository)
):
    candidate = await repo.get_by_id(id)
    if not candidate:
        raise HTTPException(404, "Not found")
    return CandidateResponse.model_validate(candidate)

# repository.py
async def get_by_id(self, id: UUID) -> Optional[Candidate]:
    return await super().get_by_id(id)
```

### Complex Operation (API → Service → Repository)
```python
# api.py
@router.post("/candidates/{id}/resumes")
async def upload_resume(
    id: UUID,
    file: UploadFile,
    service: ResumeService = Depends(get_service)
):
    return await service.upload_resume(candidate_id=id, file=file)

# service.py
async def upload_resume(self, candidate_id: UUID, file: UploadFile):
    # Business logic: validate file
    await self._validate_file(file)

    # Business logic: extract text
    text = await self._extract_text(file)

    # Business logic: generate hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Store via repository
    return await self.repository.create_resume(
        candidate_id=candidate_id,
        file_hash=file_hash,
        extracted_text=text
    )

# repository.py
async def create_resume(self, **kwargs) -> Resume:
    """Store resume in database."""
    resume = Resume(**kwargs)
    self.session.add(resume)
    await self.session.commit()
    return resume
```

---

## 📖 Additional Resources

- See `REFACTORING_GUIDE.md` for when to use/skip service layer
- See `CLAUDE.md` for project setup and commands