# Resume Analysis Refactoring Plan

## Current Problems

### ❌ Critical Issues
1. **API Misalignment**: Takes raw text instead of resume reference
2. **User Experience Broken**: Upload → Copy/Paste → Analyze (3 steps instead of 2)
3. **No Integration**: Disconnected from resume_upload feature
4. **Missing Access Control**: No candidate-based permissions
5. **Legacy References**: Still uses `file_upload_id` instead of `resume_id`

### ⚠️ Secondary Issues
- Duplicate industry enums (in both schemas and database models)
- Missing resume version awareness
- No caching for duplicate analysis requests

## Target Architecture (Two-Feature Concept)

### ✅ Desired User Flow
```
1. Upload Resume   → POST /api/v1/candidates/{id}/resumes
2. Analyze Resume  → POST /api/v1/resumes/{id}/analyze
                  → GET  /api/v1/analysis/{id}/results
```

### ✅ Desired API Design

#### Analysis Request API
```python
# Request Analysis
POST /api/v1/resumes/{resume_id}/analyze
{
    "industry": "strategy_tech",
    "analysis_depth": "standard|deep|quick",
    "focus_areas": ["structure", "content", "formatting"]  # Optional
}

# Response (Immediate)
{
    "analysis_id": "uuid",
    "status": "processing",
    "estimated_completion": "30s",
    "poll_url": "/api/v1/analysis/{id}/status"
}
```

#### Analysis Results API
```python
# Poll for Results
GET /api/v1/analysis/{analysis_id}/status

# Response (When Complete)
{
    "status": "completed",
    "resume_id": "uuid",
    "analysis": {
        "overall_score": 85,
        "detailed_scores": {...},
        "feedback": {...}
    },
    "processing_time": "28s"
}
```

#### Analysis History API
```python
# Get Analysis History for Resume
GET /api/v1/resumes/{resume_id}/analyses

# Response
{
    "analyses": [
        {
            "id": "uuid",
            "industry": "strategy_tech",
            "status": "completed",
            "overall_score": 85,
            "analyzed_at": "2025-09-24T10:30:00Z"
        }
    ]
}
```

## Implementation Plan

### Phase 1: API Refactoring (Week 1)

#### 1.1 Update Analysis Request Schema
```python
# OLD
class AnalysisRequest(BaseModel):
    text: str  # ← Remove this!
    industry: Industry
    file_upload_id: Optional[str]  # ← Remove this!

# NEW
class AnalysisRequest(BaseModel):
    industry: Industry
    analysis_depth: AnalysisDepth = "standard"
    focus_areas: Optional[List[str]] = None
```

#### 1.2 Update API Endpoints
```python
# Change endpoint structure
@router.post("/resumes/{resume_id}/analyze")
async def request_analysis(
    resume_id: uuid.UUID,  # ← Key change!
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    # 1. Validate resume access via candidate permissions
    # 2. Get resume text from resume_upload service
    # 3. Queue analysis job
    # 4. Return job ID for polling
```

#### 1.3 Add Polling Endpoints
```python
@router.get("/analysis/{analysis_id}/status")
async def get_analysis_status(analysis_id: uuid.UUID):
    # Return current status + results when ready

@router.get("/resumes/{resume_id}/analyses")
async def get_resume_analysis_history(resume_id: uuid.UUID):
    # Return all analyses for this resume
```

### Phase 2: Service Integration (Week 1)

#### 2.1 Update Analysis Service
```python
class AnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.resume_service = ResumeUploadService(db)  # ← Add integration

    async def request_analysis(
        self,
        resume_id: uuid.UUID,
        industry: Industry,
        user_id: uuid.UUID,
        analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD
    ) -> AnalysisResponse:
        # 1. Get resume text via resume service (validates access)
        resume_text = await self.resume_service.get_resume_text(
            resume_id, user_id
        )

        # 2. Check for recent analysis (caching)
        recent = await self.check_recent_analysis(resume_id, industry)
        if recent:
            return recent

        # 3. Queue new analysis
        analysis = await self.create_analysis_record(
            resume_id=resume_id,  # ← Link to resume, not file_upload
            industry=industry,
            requested_by=user_id
        )

        # 4. Start background processing
        await self.queue_analysis_job(analysis.id, resume_text)

        return AnalysisResponse(
            analysis_id=analysis.id,
            status="processing",
            poll_url=f"/api/v1/analysis/{analysis.id}/status"
        )
```

#### 2.2 Update Database Model Usage
```python
# Update ResumeAnalysis creation
analysis = ResumeAnalysis(
    resume_id=resume_id,  # ← Use resume_id (not file_upload_id)
    requested_by_user_id=user_id,
    industry=industry,
    status=AnalysisStatus.PENDING
)
```

### Phase 3: Access Control Integration (Week 2)

#### 3.1 Add Candidate Access Validation
```python
class AnalysisService:
    async def _validate_resume_access(self, resume_id: uuid.UUID, user_id: uuid.UUID):
        # Use candidate service to validate access
        resume = await self.resume_service.get_resume_details(resume_id, user_id)
        if not resume:
            raise HTTPException(403, "Access denied to this resume")
        return resume
```

#### 3.2 Role-Based Analysis Permissions
```python
# Different analysis depths based on user role
if user.role == "junior_recruiter":
    max_depth = AnalysisDepth.STANDARD
elif user.role in ["senior_recruiter", "admin"]:
    max_depth = AnalysisDepth.DEEP
```

### Phase 4: Enhanced Features (Week 2-3)

#### 4.1 Analysis Caching
```python
async def check_recent_analysis(
    self,
    resume_id: uuid.UUID,
    industry: Industry,
    max_age_hours: int = 24
) -> Optional[AnalysisResult]:
    # Return cached analysis if recent enough
```

#### 4.2 Bulk Analysis Support
```python
@router.post("/candidates/{candidate_id}/analyze-all")
async def analyze_all_resumes(candidate_id: uuid.UUID):
    # Analyze all resume versions for a candidate
```

#### 4.3 Analysis Comparison
```python
@router.get("/analysis/compare")
async def compare_analyses(
    analysis_ids: List[uuid.UUID]
):
    # Compare multiple analyses side-by-side
```

## Migration Strategy

### 1. Backward Compatibility (Temporary)
- Keep old `/analyze` endpoint active during transition
- Add deprecation warnings
- Gradually migrate frontend to new endpoints

### 2. Data Migration
- Update existing `ResumeAnalysis` records to link to resumes
- Migrate `file_upload_id` references to `resume_id`

### 3. Testing Strategy
- Unit tests for new service integration
- Integration tests for complete upload→analyze flow
- Performance tests for analysis caching

## Success Metrics

✅ **User Experience**: Upload → Analyze (2 steps, no copy/paste)
✅ **Integration**: Resume analysis directly references uploaded resumes
✅ **Performance**: Cached analysis results for duplicate requests
✅ **Security**: Proper candidate-based access control
✅ **Scalability**: Async processing with polling for results

## Timeline

- **Week 1**: API refactoring and service integration
- **Week 2**: Access control and enhanced features
- **Week 3**: Testing, migration, and deployment

This refactoring will complete our two-feature architecture vision!