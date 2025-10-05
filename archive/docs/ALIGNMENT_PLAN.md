# Feature Alignment Plan: Two-Feature Architecture

## Current vs Desired State

### ❌ Current State (Misaligned)
```
file_upload/           resume_analysis/
├── Generic files      ├── Takes raw text
├── No candidate link  ├── No resume reference
└── No versioning      └── Disconnected from uploads
```

### ✅ Desired State (Two-Feature Model)
```
resume_upload/              resume_analysis/
├── Resume-specific         ├── Takes resume ID
├── Candidate-linked        ├── Gets text from resume
├── Version management      ├── Linked to uploads
└── Complete storage        └── On-demand processing
```

## Alignment Tasks

### Phase 1: Rename & Restructure (Immediate)

1. **Rename file_upload → resume_upload**
   ```bash
   mv app/features/file_upload app/features/resume_upload
   ```

2. **Update imports and references**
   - Update main.py router import
   - Update all internal imports

### Phase 2: Enhance Resume Upload Feature (Week 1)

```python
# app/features/resume_upload/service.py

class ResumeUploadService:
    """Complete resume management service."""

    async def upload_resume(
        self,
        candidate_id: UUID,  # ADD: Link to candidate
        file: UploadFile,
        user_id: UUID
    ) -> ResumeUploadResponse:
        """Upload and store resume with versioning."""
        # 1. Validate candidate access
        # 2. Extract text
        # 3. Check duplicates
        # 4. Create version
        # 5. Store in Resume table (not FileUpload)

    async def get_resume(self, resume_id: UUID) -> Resume:
        """Get resume for analysis."""

    async def list_candidate_resumes(
        self,
        candidate_id: UUID
    ) -> List[Resume]:
        """List all versions for candidate."""
```

### Phase 3: Update Resume Analysis Feature (Week 1)

```python
# app/features/resume_analysis/service.py

class ResumeAnalysisService:
    """On-demand AI analysis service."""

    async def analyze_resume(
        self,
        resume_id: UUID,  # CHANGE: Take resume ID, not text
        industry: Industry,
        user_id: UUID
    ) -> AnalysisResponse:
        """Analyze uploaded resume."""
        # 1. Get resume from ResumeUploadService
        # 2. Check cache for recent analysis
        # 3. Run AI analysis if needed
        # 4. Store and return results
```

### Phase 4: API Updates

```python
# Resume Upload (Complete Management)
POST   /api/v1/candidates/{id}/resumes     # Upload new version
GET    /api/v1/candidates/{id}/resumes     # List all versions
GET    /api/v1/resumes/{id}               # Get specific resume
DELETE /api/v1/resumes/{id}               # Delete version

# Resume Analysis (On-Demand Processing)
POST   /api/v1/resumes/{id}/analyze       # Request analysis
GET    /api/v1/analysis/{id}              # Get results
GET    /api/v1/resumes/{id}/analyses      # History
```

## Migration Checklist

- [ ] Rename file_upload to resume_upload
- [ ] Add candidate_id to upload flow
- [ ] Implement version management
- [ ] Update Resume model usage
- [ ] Change analysis to take resume_id
- [ ] Update API endpoints
- [ ] Migrate existing FileUpload data to Resume
- [ ] Update tests
- [ ] Update frontend integration

## Benefits After Alignment

✅ **Clear Separation**: Upload/Storage vs Analysis
✅ **User Mental Model**: Matches how users think
✅ **No Duplication**: Single resume storage
✅ **Proper Linking**: Resumes → Candidates → Analysis
✅ **Version Control**: Track resume iterations
✅ **Cost Control**: Analysis only when needed

## Timeline

- **Today**: Rename and basic restructure
- **Week 1**: Complete service updates
- **Week 2**: Testing and migration
- **Week 3**: Production deployment