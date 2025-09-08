# Backend Refactoring Plan - Feature-Based Architecture

## Executive Summary

This document outlines the refactoring plan to migrate the backend from a service-based architecture to a feature-based architecture, following Domain-Driven Design (DDD) principles and maintaining isolation of the AI agents module for future microservice extraction.

## Current State

### Problems Identified
1. **Architectural Inconsistency**: Only `auth` follows the feature-based pattern while resume analysis logic sits in a standalone `services/` folder
2. **Import Errors**: `services/analysis_service.py:26` references non-existent `app.ai.orchestrator` 
3. **Missing Endpoints**: Frontend expects `/api/v1/files/upload` and `/api/v1/analysis/*` which don't exist
4. **Redundant Orchestration**: Two `ResumeAnalysisOrchestrator` classes intended (old vs new)

### Current Structure
```
backend/app/
├── features/
│   └── auth/              # ✅ Follows best practice
│       ├── api.py
│       ├── service.py
│       ├── repository.py
│       └── models.py
├── services/              # ❌ Inconsistent pattern
│   └── analysis_service.py
└── ai_agents/             # ✅ Isolated, ready for extraction
    └── orchestrator.py
```

## Target Architecture

### Proposed Structure
```
backend/app/
├── features/              # Domain features (DDD)
│   ├── auth/             # Existing
│   ├── file_upload/      # NEW
│   │   ├── api.py        # POST /api/v1/files/upload
│   │   ├── service.py    # Validation, virus scan, text extraction
│   │   ├── repository.py # File metadata persistence
│   │   └── models.py     # UploadedFileV2 schema
│   └── resume_analysis/  # NEW
│       ├── api.py        # POST /api/v1/analysis/analyze
│       ├── service.py    # Business logic from current services/
│       ├── repository.py # Analysis results persistence
│       └── models.py     # AnalysisRequest/Response schemas
├── ai_agents/            # UNCHANGED - Isolated AI module
│   ├── orchestrator.py   # LangGraph workflow
│   ├── agents/          # AI agents
│   └── interface.py     # Clean contract
└── services/            # DELETE after migration
```

## Implementation Plan

### Phase 1: File Upload Feature (Week 1)

#### 1.1 Create Feature Structure
```bash
backend/app/features/file_upload/
├── __init__.py
├── api.py           # FastAPI router
├── service.py       # Business logic
├── repository.py    # Database operations
├── models.py        # SQLAlchemy + Pydantic
└── tests/
    ├── unit/
    └── integration/
```

#### 1.2 API Endpoints
```python
# api.py
POST /api/v1/files/upload
- Accept: multipart/form-data
- Returns: UploadedFileV2
- Features: Progress tracking, cancellation

POST /api/v1/files/batch
- Accept: multiple files
- Returns: List[UploadedFileV2]
```

#### 1.3 Service Layer
```python
# service.py
class FileUploadService:
    - validate_file(file: UploadFile) -> bool
    - scan_for_virus(file: bytes) -> bool
    - extract_text(file: bytes) -> str
    - process_upload(file: UploadFile) -> UploadedFileV2
```

#### 1.4 Data Models
```python
# models.py
class FileUpload(Base):  # SQLAlchemy
    id: UUID
    filename: str
    file_type: str
    file_size: int
    extracted_text: str
    upload_status: str
    user_id: UUID
    created_at: datetime

class UploadedFileV2(BaseModel):  # Pydantic
    id: str
    file: FileInfo
    status: UploadStatus
    progress: int
    extractedText: Optional[str]
    error: Optional[str]
```

### Phase 2: Resume Analysis Feature (Week 2)

#### 2.1 Create Feature Structure
```bash
backend/app/features/resume_analysis/
├── __init__.py
├── api.py           # FastAPI router
├── service.py       # Migrated from services/analysis_service.py
├── repository.py    # Database operations
├── models.py        # Analysis models
└── tests/
```

#### 2.2 API Endpoints
```python
# api.py
POST /api/v1/analysis/analyze
- Accept: AnalysisRequest
- Returns: AnalysisResult

GET /api/v1/analysis/{analysis_id}
- Returns: AnalysisResult

GET /api/v1/analysis/history
- Returns: List[AnalysisSummary]
```

#### 2.3 Service Integration
```python
# service.py
class AnalysisService:
    def __init__(self):
        # Use ai_agents as a utility module
        from app.ai_agents.orchestrator import ResumeAnalysisOrchestrator
        self.ai_orchestrator = ResumeAnalysisOrchestrator()
    
    async def analyze(self, request: AnalysisRequest):
        # 1. Validate request (from old service)
        # 2. Check rate limits (from old service)
        # 3. Call AI orchestrator (delegation)
        # 4. Store results (repository)
        # 5. Track usage (from old service)
        return formatted_response
```

#### 2.4 Repository Layer
```python
# repository.py
class AnalysisRepository(BaseRepository):
    async def create_analysis(analysis: AnalysisModel) -> AnalysisModel
    async def get_analysis(analysis_id: UUID) -> Optional[AnalysisModel]
    async def list_user_analyses(user_id: UUID) -> List[AnalysisModel]
```

### Phase 3: Integration & Migration (Week 3)

#### 3.1 Update main.py
```python
# main.py
# Feature flags for gradual rollout
if settings.USE_NEW_FILE_UPLOAD:
    from app.features.file_upload.api import router as file_router
    app.include_router(file_router, prefix="/api/v1/files", tags=["files"])
    logger.info("✅ New file upload feature enabled")

if settings.USE_NEW_ANALYSIS:
    from app.features.resume_analysis.api import router as analysis_router
    app.include_router(analysis_router, prefix="/api/v1/analysis", tags=["analysis"])
    logger.info("✅ New analysis feature enabled")
```

#### 3.2 Environment Configuration
```env
# .env
USE_NEW_FILE_UPLOAD=false  # Enable after testing
USE_NEW_ANALYSIS=false     # Enable after testing
USE_NEW_AI=true            # Already using new AI agents
```

#### 3.3 Database Migrations
```sql
-- Create file_uploads table
CREATE TABLE file_uploads (
    id UUID PRIMARY KEY,
    filename VARCHAR(255),
    file_type VARCHAR(50),
    file_size INTEGER,
    extracted_text TEXT,
    upload_status VARCHAR(50),
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP
);

-- Create analysis_results table
CREATE TABLE analysis_results (
    id UUID PRIMARY KEY,
    file_id UUID REFERENCES file_uploads(id),
    industry VARCHAR(100),
    overall_score FLOAT,
    analysis_data JSONB,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP
);
```

### Phase 4: Cleanup (Week 4)

#### 4.1 Remove Legacy Code
- [ ] Delete `backend/app/services/` folder
- [ ] Remove old imports from codebase
- [ ] Update documentation

#### 4.2 Testing & Validation
- [ ] Run full test suite
- [ ] Verify all endpoints work
- [ ] Check frontend integration
- [ ] Performance testing

#### 4.3 Documentation
- [ ] Update API documentation
- [ ] Update README files
- [ ] Create migration guide

## Benefits

### 1. **Clean Architecture** ✅
- Each feature is self-contained with clear boundaries
- Follows established project patterns
- Easy to understand and maintain

### 2. **Microservice Ready** ✅
- AI agents module remains isolated
- Clean interfaces between features
- Easy to extract into separate services

### 3. **No Redundancy** ✅
- Single source of truth for each domain
- Clear separation of concerns
- Eliminates duplicate orchestrator classes

### 4. **Frontend Compatibility** ✅
- Matches expected API endpoints
- Maintains existing contracts
- No breaking changes

### 5. **Gradual Migration** ✅
- Feature flags for safe rollout
- Can revert if issues arise
- Zero downtime deployment

## Risk Mitigation

### Risks & Mitigations
1. **Data Migration**: Use feature flags to run old/new in parallel
2. **Frontend Breaking**: Maintain exact API contracts from frontend expectations
3. **AI Integration Issues**: Keep ai_agents interface stable
4. **Performance Degradation**: Load test before switching flags

## Success Criteria

- [ ] All tests passing (>80% coverage)
- [ ] Frontend upload flow working end-to-end
- [ ] Analysis results match old system output
- [ ] No increase in response times
- [ ] Clean dependency graph with no circular imports
- [ ] Successfully delete services/ folder

## Timeline

| Week | Phase | Description | Status |
|------|-------|-------------|--------|
| 1 | File Upload | Implement file upload feature | 🔄 Pending |
| 2 | Analysis | Implement analysis feature | 🔄 Pending |
| 3 | Integration | Testing & feature flag rollout | 🔄 Pending |
| 4 | Cleanup | Remove old code, documentation | 🔄 Pending |

## Team Communication

This refactoring follows our established patterns from the `auth` feature and maintains the isolation of `ai_agents` for future microservice extraction. The gradual migration approach using feature flags ensures zero downtime and safe rollback capabilities.

**Key Points for Team:**
- No breaking changes to frontend
- AI agents module remains unchanged
- Feature flags control rollout
- Services folder will be deleted after migration

## Questions/Concerns?

Please raise any concerns in the team channel or create an issue in the repository. This plan is designed to be flexible and can be adjusted based on team feedback.

---

*Last Updated: 2025-09-08*
*Author: Backend Architecture Team*
*Status: Ready for Review*