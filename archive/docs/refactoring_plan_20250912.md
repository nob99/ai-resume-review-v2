# Backend Refactoring Plan: MVP-First with Future-Ready Architecture

**Date**: September 12, 2025  
**Version**: 1.0  
**Author**: Backend Architecture Team  

## Executive Summary

This document outlines a pragmatic refactoring approach that balances **speed to market** (MVP) with **future architectural flexibility**. Instead of implementing complex section-based text extraction immediately, we'll start with raw text storage but design the database schema to support future enhancements without breaking changes.

## Strategic Approach: Progressive Enhancement

### Current Challenge
- Users expect two distinct experiences: **"Upload Resume"** and **"Request AI Analysis"**
- Current architecture has 3 confusing services with duplicate code and text storage
- Future requirement: Source attribution (link AI feedback to specific resume sections)
- MVP constraint: Complex section extraction requires AI/ML investment

### Solution Philosophy
1. **MVP Now**: Store raw text, ship quickly
2. **Design for Future**: Schema supports sections from day one  
3. **Progressive Enhancement**: Gradually add section detection without breaking changes
4. **User Experience First**: Match backend architecture to user mental model

---

## Detailed MVP Implementation Plan (Immediate - Weeks 1-4)

### **Week 1: Foundation & Cleanup**

#### 1.1 Create Shared Text Processing Utilities

```python
# Create: app/core/text_extraction.py
from typing import NamedTuple, Optional
import hashlib
import logging
from pathlib import Path

class TextExtractionResult(NamedTuple):
    text: str
    success: bool
    error_message: Optional[str]
    metadata: dict
    extraction_method: str

class TextExtractor:
    """
    Centralized text extraction utility.
    Eliminates code duplication between File Upload and Resume services.
    """
    
    @staticmethod
    def extract_text(content: bytes, filename: str) -> TextExtractionResult:
        """
        Extract text from file content.
        MVP: Basic extraction only, extensible for future AI enhancement.
        """
        try:
            file_ext = Path(filename).suffix.lower()
            
            if file_ext == '.pdf':
                text = TextExtractor._extract_pdf_text(content)
                method = 'pdf_basic'
            elif file_ext in ['.docx', '.doc']:
                text = TextExtractor._extract_docx_text(content)
                method = 'docx_basic'
            elif file_ext == '.txt':
                text = content.decode('utf-8')
                method = 'plain_text'
            else:
                return TextExtractionResult(
                    text="",
                    success=False,
                    error_message=f"Unsupported file type: {file_ext}",
                    metadata={},
                    extraction_method='unsupported'
                )
            
            # Basic text cleanup
            cleaned_text = TextExtractor._clean_extracted_text(text)
            
            return TextExtractionResult(
                text=cleaned_text,
                success=True,
                error_message=None,
                metadata={
                    'original_length': len(text),
                    'cleaned_length': len(cleaned_text),
                    'file_extension': file_ext,
                    'confidence': 'basic'
                },
                extraction_method=method
            )
            
        except Exception as e:
            logging.error(f"Text extraction failed for {filename}: {str(e)}")
            return TextExtractionResult(
                text="",
                success=False,
                error_message=f"Extraction failed: {str(e)}",
                metadata={},
                extraction_method='failed'
            )
    
    @staticmethod
    def _extract_pdf_text(content: bytes) -> str:
        """Extract text from PDF using PyPDF2."""
        import PyPDF2
        import io
        
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text_parts = []
        
        for page in pdf_reader.pages:
            text_parts.append(page.extract_text())
        
        return "\n".join(text_parts)
    
    @staticmethod
    def _extract_docx_text(content: bytes) -> str:
        """Extract text from DOCX using python-docx."""
        from docx import Document
        import io
        
        doc = Document(io.BytesIO(content))
        paragraphs = [paragraph.text for paragraph in doc.paragraphs]
        
        return "\n".join(paragraphs)
    
    @staticmethod
    def _clean_extracted_text(text: str) -> str:
        """Basic text cleanup for better AI processing."""
        import re
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Limit excessive whitespace (max 2 consecutive newlines)
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text

# Create: app/core/file_validation.py
from typing import List, Dict, Any

class FileValidationResult(NamedTuple):
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]

class FileValidator:
    """
    Centralized file validation utility.
    """
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'text/plain'
    }
    
    @staticmethod
    def validate_resume_file(
        content: bytes, 
        filename: str,
        declared_mime_type: Optional[str] = None
    ) -> FileValidationResult:
        """
        Validate uploaded resume file.
        MVP: Basic validation, extensible for virus scanning, etc.
        """
        errors = []
        warnings = []
        
        # Size validation
        if len(content) > FileValidator.MAX_FILE_SIZE:
            errors.append(f"File too large. Maximum size: {FileValidator.MAX_FILE_SIZE // (1024*1024)}MB")
        
        if len(content) == 0:
            errors.append("File is empty")
        
        # Extension validation
        file_ext = Path(filename).suffix.lower()
        if file_ext not in FileValidator.ALLOWED_EXTENSIONS:
            errors.append(f"Unsupported file type: {file_ext}")
        
        # Basic content validation
        if file_ext == '.pdf' and not content.startswith(b'%PDF'):
            errors.append("Invalid PDF file format")
        
        # MIME type validation (if provided)
        if declared_mime_type and declared_mime_type not in FileValidator.ALLOWED_MIME_TYPES:
            warnings.append(f"Unusual MIME type: {declared_mime_type}")
        
        return FileValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata={
                'file_size': len(content),
                'file_extension': file_ext,
                'declared_mime_type': declared_mime_type
            }
        )
```

#### 1.2 Future-Ready Database Schema

```sql
-- Migration: Add future-ready schema while maintaining MVP simplicity
-- This migration creates the foundation for both MVP and future enhancements

-- Enhanced resumes table (MVP + future ready)
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS extraction_method VARCHAR(50) DEFAULT 'basic';
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS extraction_metadata JSONB DEFAULT '{}';
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS processing_status VARCHAR(50) DEFAULT 'completed';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_resumes_candidate_version 
ON resumes (candidate_id, version_number DESC);

CREATE INDEX IF NOT EXISTS idx_resumes_extraction_method 
ON resumes (extraction_method) 
WHERE extraction_method != 'basic';

-- Future-ready tables (create now, use later)
CREATE TABLE IF NOT EXISTS resume_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    section_type VARCHAR(50) NOT NULL, -- 'contact', 'summary', 'experience', 'education', 'skills', etc.
    section_order INTEGER NOT NULL,
    title VARCHAR(200),
    content TEXT NOT NULL,
    start_position INTEGER, -- Character position in original text
    end_position INTEGER,   -- Character position end
    confidence_score FLOAT, -- AI extraction confidence (0.0-1.0)
    extraction_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_resume_section_order UNIQUE(resume_id, section_order)
);

CREATE INDEX IF NOT EXISTS idx_resume_sections_resume_order 
ON resume_sections (resume_id, section_order);

CREATE INDEX IF NOT EXISTS idx_resume_sections_type 
ON resume_sections (section_type);

-- Enhanced analysis tables for future source attribution
CREATE TABLE IF NOT EXISTS analysis_feedback_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES resume_analyses(id) ON DELETE CASCADE,
    feedback_text TEXT NOT NULL,
    feedback_type VARCHAR(50) NOT NULL, -- 'strength', 'improvement', 'concern', 'suggestion'
    category VARCHAR(50), -- 'experience', 'skills', 'format', 'content'
    importance_level INTEGER DEFAULT 3, -- 1-5 priority level
    confidence_score FLOAT, -- AI confidence in this feedback
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback_source_sections (
    feedback_id UUID REFERENCES analysis_feedback_items(id) ON DELETE CASCADE,
    section_id UUID REFERENCES resume_sections(id) ON DELETE CASCADE,
    relevance_score FLOAT NOT NULL DEFAULT 1.0, -- How relevant this section is (0.0-1.0)
    highlighted_text TEXT, -- Specific excerpt that triggered feedback
    character_start INTEGER, -- Position within section
    character_end INTEGER,
    
    PRIMARY KEY (feedback_id, section_id)
);

-- Comments for future reference
COMMENT ON TABLE resume_sections IS 'Future enhancement: Structured resume sections for source attribution';
COMMENT ON TABLE analysis_feedback_items IS 'Future enhancement: Detailed feedback with source linking';
COMMENT ON COLUMN resumes.extraction_method IS 'Tracks extraction evolution: basic -> structured -> ai_enhanced';
```

### **Week 2: Service Consolidation**

#### 2.1 Unified Resume Service (Merge File Upload + Resume)

```python
# app/features/resume/service.py (COMPLETE REFACTOR)
from typing import Optional, List
from uuid import UUID
import hashlib
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text_extraction import TextExtractor, TextExtractionResult
from app.core.file_validation import FileValidator, FileValidationResult
from app.features.candidate.service import CandidateService
from .repository import ResumeRepository
from .schemas import (
    ResumeUploadResponse, ResumeListItem, ResumeDetailsResponse,
    ResumeStatus
)
from .exceptions import (
    ResumeValidationError, DuplicateResumeError, ResumeNotFoundError
)

logger = logging.getLogger(__name__)

class ResumeService:
    """
    Unified Resume Service - handles complete resume upload experience.
    
    Replaces both FileUploadService and current ResumeService.
    Matches user mental model: "Upload Resume" as single operation.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ResumeRepository(session, Resume)
        self.candidate_service = CandidateService(session)
    
    async def upload_resume(
        self, 
        candidate_id: UUID, 
        file_content: bytes,
        filename: str,
        user_id: UUID
    ) -> ResumeUploadResponse:
        """
        Complete resume upload experience - MVP version.
        
        Flow:
        1. Validate candidate access (RBAC)
        2. Validate file format and size
        3. Extract text using shared utility
        4. Check for duplicates (same file hash)
        5. Store in single location (resumes table)
        6. Return upload success with analysis readiness
        
        Args:
            candidate_id: Target candidate for this resume
            file_content: Raw file bytes
            filename: Original filename
            user_id: User performing the upload
            
        Returns:
            ResumeUploadResponse with upload status and metadata
            
        Raises:
            CandidateAccessDeniedError: User cannot access candidate
            ResumeValidationError: File validation failed
            DuplicateResumeError: Exact same file already exists
        """
        logger.info(f"Resume upload started: candidate={candidate_id}, user={user_id}, file={filename}")
        
        try:
            # Step 1: Validate candidate access (reuse candidate service RBAC)
            await self.candidate_service.validate_candidate_access(candidate_id, user_id)
            logger.debug(f"Candidate access validated for user {user_id}")
            
            # Step 2: Validate file
            validation: FileValidationResult = FileValidator.validate_resume_file(
                file_content, filename
            )
            if not validation.is_valid:
                raise ResumeValidationError(
                    f"File validation failed: {', '.join(validation.errors)}",
                    validation_errors=validation.errors
                )
            
            # Log warnings but don't fail
            if validation.warnings:
                logger.warning(f"File validation warnings: {validation.warnings}")
            
            # Step 3: Extract text using shared utility (MVP: basic extraction)
            extraction: TextExtractionResult = TextExtractor.extract_text(file_content, filename)
            if not extraction.success:
                raise ResumeValidationError(
                    f"Text extraction failed: {extraction.error_message}",
                    extraction_error=extraction.error_message
                )
            
            logger.debug(f"Text extracted: {len(extraction.text)} characters")
            
            # Step 4: Check for duplicates (same file hash for this candidate)
            file_hash = hashlib.sha256(file_content).hexdigest()
            existing = await self.repository.find_by_hash_and_candidate(file_hash, candidate_id)
            if existing:
                logger.info(f"Duplicate resume detected: {existing.id}")
                return ResumeUploadResponse(
                    id=existing.id,
                    status="duplicate_detected",
                    message=f"This resume already exists as version {existing.version_number}",
                    version=existing.version_number,
                    can_analyze=True,
                    duplicate_of=existing.id
                )
            
            # Step 5: Get next version number for this candidate
            next_version = await self.repository.get_next_version_for_candidate(candidate_id)
            
            # Step 6: Store resume (single source of truth for MVP)
            resume = await self.repository.create(
                candidate_id=candidate_id,
                uploaded_by_user_id=user_id,
                version_number=next_version,
                original_filename=filename,
                file_hash=file_hash,
                file_size=len(file_content),
                mime_type=validation.metadata.get('declared_mime_type'),
                
                # MVP: Store raw text in single location
                extracted_text=extraction.text,
                extraction_method=extraction.extraction_method,
                extraction_metadata={
                    **extraction.metadata,
                    **validation.metadata
                },
                
                processing_status='completed',
                status=ResumeStatus.READY_FOR_ANALYSIS
            )
            
            logger.info(f"Resume uploaded successfully: {resume.id} (version {next_version})")
            
            return ResumeUploadResponse(
                id=resume.id,
                status="uploaded_successfully",
                version=next_version,
                text_preview=extraction.text[:500],  # First 500 chars for preview
                word_count=len(extraction.text.split()),
                character_count=len(extraction.text),
                extraction_quality=extraction.metadata.get('confidence', 'basic'),
                can_analyze=True,
                message=f"Resume uploaded as version {next_version}. Ready for analysis."
            )
            
        except Exception as e:
            logger.error(f"Resume upload failed: {str(e)}")
            # Re-raise known exceptions
            if isinstance(e, (ResumeValidationError, DuplicateResumeError)):
                raise
            # Wrap unknown exceptions
            raise ResumeValidationError(f"Upload failed: {str(e)}")
    
    async def get_resume_text_for_analysis(
        self, 
        resume_id: UUID, 
        user_id: UUID
    ) -> str:
        """
        Get resume text for analysis service.
        Validates access through candidate assignments.
        
        This method bridges Resume Service and Analysis Service
        while maintaining proper access control.
        """
        resume = await self.repository.get_with_candidate(resume_id)
        if not resume:
            raise ResumeNotFoundError(f"Resume {resume_id} not found")
        
        # Validate access via candidate service
        await self.candidate_service.validate_candidate_access(
            resume.candidate_id, user_id
        )
        
        return resume.extracted_text
    
    async def list_candidate_resumes(
        self, 
        candidate_id: UUID, 
        user_id: UUID
    ) -> List[ResumeListItem]:
        """
        List all resume versions for a candidate.
        Ordered by version (newest first).
        """
        await self.candidate_service.validate_candidate_access(candidate_id, user_id)
        
        resumes = await self.repository.get_by_candidate_id(
            candidate_id, 
            order_by=Resume.version_number.desc()
        )
        
        return [
            ResumeListItem(
                id=resume.id,
                filename=resume.original_filename,
                version=resume.version_number,
                uploaded_at=resume.uploaded_at,
                file_size=resume.file_size,
                extraction_method=resume.extraction_method,
                can_analyze=resume.status == ResumeStatus.READY_FOR_ANALYSIS,
                text_preview=resume.extracted_text[:200] if resume.extracted_text else ""
            ) for resume in resumes
        ]
    
    async def get_resume_details(
        self, 
        resume_id: UUID, 
        user_id: UUID
    ) -> ResumeDetailsResponse:
        """
        Get detailed resume information including full text.
        Used by frontend for resume review before analysis.
        """
        resume = await self.repository.get_with_candidate(resume_id)
        if not resume:
            raise ResumeNotFoundError(f"Resume {resume_id} not found")
        
        await self.candidate_service.validate_candidate_access(
            resume.candidate_id, user_id
        )
        
        return ResumeDetailsResponse(
            id=resume.id,
            candidate_id=resume.candidate_id,
            filename=resume.original_filename,
            version=resume.version_number,
            uploaded_at=resume.uploaded_at,
            uploaded_by_user_id=resume.uploaded_by_user_id,
            file_size=resume.file_size,
            extracted_text=resume.extracted_text,
            extraction_method=resume.extraction_method,
            word_count=len(resume.extracted_text.split()) if resume.extracted_text else 0,
            character_count=len(resume.extracted_text) if resume.extracted_text else 0,
            can_analyze=resume.status == ResumeStatus.READY_FOR_ANALYSIS,
            
            # Future enhancement indicators
            sections_available=False,  # MVP: Always false
            enhancement_available=True  # Could be enhanced with AI section detection
        )
```

#### 2.2 Streamlined Analysis Service (On-Demand Only)

```python
# app/features/resume_analysis/service.py (REFACTORED)
from typing import Optional
from uuid import UUID
import asyncio
import logging

from .repository import AnalysisRepository
from ..resume.service import ResumeService
from .schemas import (
    AnalysisRequestResponse, AnalysisStatusResponse, 
    AnalysisDepth, AnalysisStatus
)
from .exceptions import AnalysisValidationError, AnalysisNotFoundError

logger = logging.getLogger(__name__)

class AnalysisService:
    """
    Pure AI analysis service - on-demand only.
    
    MVP: Works with raw text, no file processing.
    Future: Will support section-based analysis when available.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = AnalysisRepository(session, ResumeAnalysis)
        self.resume_service = ResumeService(session)  # For text retrieval
    
    async def request_analysis(
        self,
        resume_id: UUID,
        industry: Industry,
        user_id: UUID,
        analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD
    ) -> AnalysisRequestResponse:
        """
        Request on-demand analysis for a resume.
        
        MVP Flow:
        1. Get raw text from Resume Service (validates access)
        2. Check for recent analysis (avoid duplicate work) 
        3. Queue analysis job (async processing)
        4. Return immediately with job ID for polling
        
        Args:
            resume_id: Resume to analyze
            industry: Target industry for analysis
            user_id: User requesting analysis
            analysis_depth: Analysis complexity level
            
        Returns:
            AnalysisRequestResponse with job ID and polling info
        """
        logger.info(f"Analysis requested: resume={resume_id}, industry={industry}, user={user_id}")
        
        try:
            # Step 1: Get resume text (validates access internally)
            resume_text = await self.resume_service.get_resume_text_for_analysis(
                resume_id, user_id
            )
            
            if not resume_text or len(resume_text.strip()) < 100:
                raise AnalysisValidationError("Resume text too short for meaningful analysis")
            
            # Step 2: Check for recent analysis (avoid duplicate work)
            recent_analysis = await self.repository.find_recent_analysis(
                resume_id=resume_id,
                industry=industry,
                max_age_hours=24  # Cache analysis for 24 hours
            )
            
            if recent_analysis and recent_analysis.status == AnalysisStatus.COMPLETED:
                logger.info(f"Using cached analysis: {recent_analysis.id}")
                return AnalysisRequestResponse(
                    analysis_id=recent_analysis.id,
                    status=AnalysisStatus.COMPLETED,
                    message="Using recent analysis (less than 24 hours old)",
                    result=self._format_analysis_result(recent_analysis),
                    from_cache=True,
                    processing_time_seconds=0
                )
            
            # Step 3: Create new analysis record
            analysis = await self.repository.create_analysis(
                resume_id=resume_id,
                user_id=user_id,
                industry=industry,
                analysis_depth=analysis_depth,
                status=AnalysisStatus.PENDING
            )
            
            # Step 4: Queue analysis job (async processing)
            await self._queue_analysis_job(
                analysis_id=analysis.id,
                resume_text=resume_text,
                industry=industry,
                analysis_depth=analysis_depth
            )
            
            logger.info(f"Analysis queued: {analysis.id}")
            
            return AnalysisRequestResponse(
                analysis_id=analysis.id,
                status=AnalysisStatus.PROCESSING,
                estimated_completion_seconds=30,
                poll_url=f"/api/v1/analysis/{analysis.id}/status",
                message="Analysis started. Poll for results using the provided URL."
            )
            
        except Exception as e:
            logger.error(f"Analysis request failed: {str(e)}")
            if isinstance(e, AnalysisValidationError):
                raise
            raise AnalysisValidationError(f"Analysis request failed: {str(e)}")
    
    async def get_analysis_status(
        self, 
        analysis_id: UUID, 
        user_id: UUID
    ) -> AnalysisStatusResponse:
        """
        Poll analysis status and get results when ready.
        
        Used by frontend to check analysis progress and retrieve results.
        """
        analysis = await self.repository.get_analysis_with_access_check(
            analysis_id, user_id
        )
        if not analysis:
            raise AnalysisNotFoundError(f"Analysis {analysis_id} not found or not accessible")
        
        if analysis.status == AnalysisStatus.COMPLETED:
            return AnalysisStatusResponse(
                status=AnalysisStatus.COMPLETED,
                result=self._format_analysis_result(analysis),
                processing_time_seconds=analysis.processing_time_seconds,
                message="Analysis completed successfully"
            )
        elif analysis.status == AnalysisStatus.ERROR:
            return AnalysisStatusResponse(
                status=AnalysisStatus.ERROR,
                error_message=analysis.error_message or "Analysis failed",
                can_retry=True,
                message="Analysis failed. You can retry the request."
            )
        else:
            # Still processing
            return AnalysisStatusResponse(
                status=analysis.status,
                progress_percentage=self._calculate_progress(analysis),
                estimated_remaining_seconds=self._estimate_remaining_time(analysis),
                message="Analysis in progress. Please check back in a few seconds."
            )
    
    async def _queue_analysis_job(
        self, 
        analysis_id: UUID,
        resume_text: str,
        industry: Industry,
        analysis_depth: AnalysisDepth
    ):
        """
        Queue background analysis job.
        MVP: Simple async processing. Future: Redis queue/Celery.
        """
        # For MVP: Simple background task
        # Future: Replace with proper job queue (Redis/Celery)
        asyncio.create_task(
            self._process_analysis_background(
                analysis_id, resume_text, industry, analysis_depth
            )
        )
    
    async def _process_analysis_background(
        self,
        analysis_id: UUID,
        resume_text: str, 
        industry: Industry,
        analysis_depth: AnalysisDepth
    ):
        """
        Background analysis processing.
        MVP: Direct AI call. Future: More sophisticated workflow.
        """
        try:
            # Update status to processing
            await self.repository.update_status(analysis_id, AnalysisStatus.PROCESSING)
            
            # Call AI orchestrator (existing code)
            ai_result = await self.ai_orchestrator.analyze(
                resume_text=resume_text,
                industry=industry.value,
                analysis_id=str(analysis_id)
            )
            
            # Store results
            await self.repository.save_results(
                analysis_id=analysis_id,
                overall_score=ai_result.get("overall_score", 0),
                analysis_results=ai_result,  # Store full AI response as JSONB
                processing_time_seconds=ai_result.get("processing_time_seconds", 0)
            )
            
            # Mark as completed
            await self.repository.update_status(analysis_id, AnalysisStatus.COMPLETED)
            
            logger.info(f"Analysis completed successfully: {analysis_id}")
            
        except Exception as e:
            logger.error(f"Background analysis failed: {analysis_id}: {str(e)}")
            await self.repository.update_status(
                analysis_id, 
                AnalysisStatus.ERROR, 
                error_message=str(e)
            )
```

### **Week 3: API Redesign & Integration**

#### 3.1 New Resume API (Unified Upload Experience)

```python
# app/features/resume/api.py (COMPLETE REDESIGN)
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List
from uuid import UUID

from app.features.auth.api import get_current_user
from database.models.auth import User
from .service import ResumeService
from .schemas import (
    ResumeUploadResponse, ResumeListItem, ResumeDetailsResponse
)
from .exceptions import (
    ResumeValidationError, DuplicateResumeError, ResumeNotFoundError
)

router = APIRouter()

def get_resume_service(db: Session = Depends(get_db)) -> ResumeService:
    return ResumeService(db)

@router.post(
    "/candidates/{candidate_id}/resumes",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Resume",
    description="Complete resume upload experience - replaces separate file upload + resume creation"
)
async def upload_resume(
    candidate_id: UUID,
    file: UploadFile = File(..., description="Resume file (PDF, DOCX, DOC, TXT)"),
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service)
) -> ResumeUploadResponse:
    """
    Upload a resume for a specific candidate.
    
    This endpoint handles the complete "upload resume" user experience:
    - File validation and text extraction
    - Duplicate detection 
    - Storage with version management
    - Returns readiness for analysis
    
    Replaces the previous two-step process of file upload + resume creation.
    """
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Validate file size (FastAPI doesn't enforce this automatically)
        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file not allowed"
            )
        
        if len(file_content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum size: 10MB"
            )
        
        # Process upload using unified service
        result = await service.upload_resume(
            candidate_id=candidate_id,
            file_content=file_content,
            filename=file.filename or "unknown.pdf",
            user_id=current_user.id
        )
        
        return result
        
    except ResumeValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DuplicateResumeError as e:
        # Return 200 for duplicates with special status
        return ResumeUploadResponse(
            status="duplicate_detected",
            message=str(e)
        )
    except Exception as e:
        logger.error(f"Resume upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Resume upload failed. Please try again."
        )

@router.get(
    "/candidates/{candidate_id}/resumes",
    response_model=List[ResumeListItem],
    summary="List Candidate Resumes",
    description="Get all resume versions for a specific candidate"
)
async def list_candidate_resumes(
    candidate_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service)
) -> List[ResumeListItem]:
    """List all resume versions for a candidate, ordered by version (newest first)."""
    
    try:
        return await service.list_candidate_resumes(candidate_id, current_user.id)
    except Exception as e:
        logger.error(f"Failed to list resumes for candidate {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resumes"
        )

@router.get(
    "/resumes/{resume_id}",
    response_model=ResumeDetailsResponse,
    summary="Get Resume Details",
    description="Get detailed resume information including extracted text"
)
async def get_resume_details(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service)
) -> ResumeDetailsResponse:
    """Get detailed resume information including full text for review before analysis."""
    
    try:
        return await service.get_resume_details(resume_id, current_user.id)
    except ResumeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found or not accessible"
        )
    except Exception as e:
        logger.error(f"Failed to get resume details {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resume details"
        )

@router.delete(
    "/resumes/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Resume",
    description="Delete a specific resume version"
)
async def delete_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service)
):
    """Delete a resume version. Only the uploader or admin can delete."""
    
    try:
        await service.delete_resume(resume_id, current_user.id)
    except ResumeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found or not accessible"
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this resume"
        )

# Health check for resume service
@router.get(
    "/resumes/health",
    summary="Resume Service Health Check"
)
async def resume_service_health():
    """Check health of resume service and dependencies."""
    return {
        "status": "healthy",
        "service": "resume",
        "features": {
            "text_extraction": "basic",
            "section_detection": "future_enhancement",
            "analysis_ready": True
        }
    }
```

#### 3.2 Simplified Analysis API (On-Demand Only)

```python
# app/features/resume_analysis/api.py (SIMPLIFIED)
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from .service import AnalysisService
from .schemas import (
    AnalysisRequestBody, AnalysisRequestResponse, AnalysisStatusResponse,
    AnalysisHistoryResponse
)

router = APIRouter()

@router.post(
    "/resumes/{resume_id}/analysis",
    response_model=AnalysisRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request Resume Analysis",
    description="Request on-demand AI analysis for a specific resume"
)
async def request_analysis(
    resume_id: UUID,
    request: AnalysisRequestBody,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisRequestResponse:
    """
    Request on-demand analysis for a resume.
    
    Returns immediately with job ID - use polling endpoint to get results.
    This matches the user experience: "Analyze this resume" → "Check results when ready"
    """
    
    try:
        return await service.request_analysis(
            resume_id=resume_id,
            industry=request.industry,
            user_id=current_user.id,
            analysis_depth=request.analysis_depth or AnalysisDepth.STANDARD
        )
        
    except AnalysisValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Analysis request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis request failed. Please try again."
        )

@router.get(
    "/analysis/{analysis_id}/status",
    response_model=AnalysisStatusResponse,
    summary="Get Analysis Status",
    description="Poll analysis status and get results when ready"
)
async def get_analysis_status(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisStatusResponse:
    """
    Poll analysis status and get results when ready.
    
    Frontend should poll this endpoint every 2-3 seconds until status is 'completed' or 'error'.
    """
    
    try:
        return await service.get_analysis_status(analysis_id, current_user.id)
    except AnalysisNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found or not accessible"
        )

@router.get(
    "/resumes/{resume_id}/analyses",
    response_model=List[AnalysisHistoryResponse],
    summary="Get Analysis History",
    description="Get analysis history for a specific resume"
)
async def get_resume_analysis_history(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> List[AnalysisHistoryResponse]:
    """Get all analyses performed on this resume, ordered by date (newest first)."""
    
    return await service.list_resume_analyses(resume_id, current_user.id)
```

#### 3.3 Complete Router Integration

```python
# app/main.py (UPDATED)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all feature routers (including updated ones)
from app.features.auth.api import router as auth_router
from app.features.candidate.api import router as candidate_router
from app.features.resume.api import router as resume_router  # Updated unified service
from app.features.resume_analysis.api import router as analysis_router  # Simplified
from app.features.review.api import router as review_router  # If still needed

app = FastAPI(
    title="AI Resume Review Platform - MVP",
    description="Backend API for AI-powered resume analysis with candidate-centric architecture",
    version="2.0.0"  # Version bump for major refactor
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers with consistent prefixes
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(candidate_router, prefix="/api/v1/candidates", tags=["Candidates"]) 
app.include_router(resume_router, prefix="/api/v1", tags=["Resumes"])  # Note: prefix includes candidates/{id}/resumes
app.include_router(analysis_router, prefix="/api/v1", tags=["Analysis"])
app.include_router(review_router, prefix="/api/v1/reviews", tags=["Reviews"])  # If keeping

@app.get("/")
async def root():
    return {"message": "AI Resume Review Platform - MVP Ready"}

@app.get("/health")
async def health_check():
    """Global health check endpoint."""
    return {
        "status": "healthy", 
        "message": "AI Resume Review Platform API - MVP Version",
        "services": {
            "auth": "healthy",
            "candidates": "healthy", 
            "resumes": "healthy",
            "analysis": "healthy"
        }
    }
```

### **Week 4: Data Migration & Testing**

#### 4.1 Data Migration Script

```python
# migrations/consolidate_resume_storage_mvp.py
"""
Migration: Consolidate text storage for MVP launch
- Copy data from file_uploads to resumes where missing
- Ensure all resumes have extracted_text
- Clean up duplicate storage after verification
"""

import asyncio
import hashlib
import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, func, and_

from database.models.files import FileUpload
from database.models.resume import Resume
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class ResumeMigrationService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def migrate_file_uploads_to_resumes(self) -> dict:
        """
        Migrate text data from file_uploads to resumes table.
        Ensures all resumes have extracted_text for MVP launch.
        """
        logger.info("Starting resume storage migration...")
        
        # Find resumes that reference file_uploads but lack extracted_text
        resumes_without_text = await self.session.execute(
            select(Resume, FileUpload)
            .join(FileUpload, Resume.file_upload_id == FileUpload.id)
            .where(
                and_(
                    Resume.extracted_text.is_(None),
                    FileUpload.extracted_text.is_not(None)
                )
            )
        )
        
        migrated_count = 0
        for resume, file_upload in resumes_without_text:
            try:
                # Copy essential data from file_upload to resume
                resume.extracted_text = file_upload.extracted_text
                resume.file_size = file_upload.file_size or len(file_upload.file_content or b'')
                resume.mime_type = file_upload.mime_type
                
                # Set extraction metadata
                resume.extraction_method = 'basic'  # Default for legacy data
                resume.extraction_metadata = {
                    'migrated_from_file_upload': True,
                    'original_file_upload_id': str(file_upload.id),
                    'migration_timestamp': datetime.utcnow().isoformat()
                }
                
                # Generate hash if missing
                if not resume.file_hash and file_upload.file_content:
                    resume.file_hash = hashlib.sha256(file_upload.file_content).hexdigest()
                elif not resume.file_hash:
                    # Generate hash from text as fallback
                    resume.file_hash = hashlib.sha256(
                        resume.extracted_text.encode('utf-8')
                    ).hexdigest()
                
                migrated_count += 1
                
                if migrated_count % 100 == 0:
                    logger.info(f"Migrated {migrated_count} resumes...")
                    
            except Exception as e:
                logger.error(f"Failed to migrate resume {resume.id}: {str(e)}")
                continue
        
        await self.session.commit()
        logger.info(f"Successfully migrated {migrated_count} resume text records")
        
        # Verification step
        verification_result = await self.verify_migration()
        
        return {
            'migrated_count': migrated_count,
            'verification': verification_result
        }
    
    async def verify_migration(self) -> dict:
        """Verify that all resumes have extracted_text after migration."""
        
        total_resumes = await self.session.scalar(
            select(func.count(Resume.id))
        )
        
        resumes_with_text = await self.session.scalar(
            select(func.count(Resume.id))
            .where(Resume.extracted_text.is_not(None))
        )
        
        resumes_without_text = await self.session.scalar(
            select(func.count(Resume.id))
            .where(Resume.extracted_text.is_(None))
        )
        
        logger.info(f"Verification: {resumes_with_text}/{total_resumes} resumes have text")
        
        if resumes_without_text > 0:
            logger.warning(f"{resumes_without_text} resumes still missing text!")
            
        return {
            'total_resumes': total_resumes,
            'resumes_with_text': resumes_with_text,
            'resumes_without_text': resumes_without_text,
            'migration_complete': resumes_without_text == 0
        }
    
    async def cleanup_duplicate_text_storage(self) -> dict:
        """
        CAREFUL: Remove extracted_text from file_uploads after successful migration.
        Only run this after verifying all resumes have text.
        """
        verification = await self.verify_migration()
        
        if not verification['migration_complete']:
            raise Exception(
                f"Cannot cleanup: {verification['resumes_without_text']} resumes still missing text"
            )
        
        logger.info("Migration verified complete. Starting cleanup of duplicate storage...")
        
        # Count how much space we'll save
        files_with_text = await self.session.scalar(
            select(func.count(FileUpload.id))
            .where(FileUpload.extracted_text.is_not(None))
        )
        
        # Remove duplicate text storage
        result = await self.session.execute(
            update(FileUpload)
            .values(extracted_text=None)
            .where(FileUpload.extracted_text.is_not(None))
        )
        
        await self.session.commit()
        
        logger.info(f"Cleaned up duplicate text storage from {files_with_text} file_upload records")
        
        return {
            'files_cleaned': files_with_text,
            'space_saved': 'significant',  # Could calculate actual bytes saved
            'duplicate_storage_removed': True
        }

# Migration execution script
async def run_migration():
    """Execute the complete migration process."""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        migration_service = ResumeMigrationService(session)
        
        try:
            # Step 1: Migrate data
            migration_result = await migration_service.migrate_file_uploads_to_resumes()
            print(f"Migration completed: {migration_result}")
            
            # Step 2: Verify migration
            if migration_result['verification']['migration_complete']:
                print("✅ Migration successful! All resumes have text.")
                
                # Step 3: Optional cleanup (commented out for safety)
                # cleanup_result = await migration_service.cleanup_duplicate_text_storage()
                # print(f"Cleanup completed: {cleanup_result}")
                
            else:
                print("❌ Migration incomplete. Some resumes still missing text.")
                
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(run_migration())
```

#### 4.2 Integration Test Suite

```python
# tests/integration/test_mvp_resume_workflow.py
"""
Integration tests for MVP resume workflow.
Tests the complete user journey: Upload → Analyze → Results
"""

import pytest
import asyncio
from httpx import AsyncClient
from uuid import uuid4

class TestMVPResumeWorkflow:
    """Test complete MVP workflow matching user experience."""
    
    @pytest.fixture
    async def sample_pdf_resume(self):
        """Sample PDF content for testing."""
        # In real test, would use actual PDF bytes
        return b"Sample PDF content for testing"
    
    async def test_complete_upload_and_analysis_flow(
        self,
        async_client: AsyncClient,
        authenticated_user,
        test_candidate,
        sample_pdf_resume
    ):
        """
        Test complete MVP user journey:
        1. Create candidate
        2. Upload resume (unified endpoint)
        3. Request analysis (on-demand)
        4. Poll for results
        5. Get final analysis
        """
        
        # Setup
        auth_headers = {"Authorization": f"Bearer {authenticated_user.access_token}"}
        
        # Step 1: Upload resume using new unified endpoint
        upload_response = await async_client.post(
            f"/api/v1/candidates/{test_candidate.id}/resumes",
            files={"file": ("test_resume.pdf", sample_pdf_resume, "application/pdf")},
            headers=auth_headers
        )
        
        assert upload_response.status_code == 201
        upload_data = upload_response.json()
        
        assert upload_data["status"] == "uploaded_successfully"
        assert upload_data["can_analyze"] == True
        assert len(upload_data["text_preview"]) > 0
        
        resume_id = upload_data["id"]
        
        # Step 2: Request analysis (on-demand)
        analysis_request = {
            "industry": "strategy_tech",
            "analysis_depth": "standard"
        }
        
        analysis_response = await async_client.post(
            f"/api/v1/resumes/{resume_id}/analysis",
            json=analysis_request,
            headers=auth_headers
        )
        
        assert analysis_response.status_code == 202  # Accepted for processing
        analysis_data = analysis_response.json()
        
        assert analysis_data["status"] == "processing"
        assert "analysis_id" in analysis_data
        assert "poll_url" in analysis_data
        
        analysis_id = analysis_data["analysis_id"]
        
        # Step 3: Poll for results (realistic user behavior)
        max_polls = 15  # 30 seconds max
        poll_count = 0
        
        while poll_count < max_polls:
            status_response = await async_client.get(
                f"/api/v1/analysis/{analysis_id}/status",
                headers=auth_headers
            )
            
            assert status_response.status_code == 200
            status_data = status_response.json()
            
            if status_data["status"] == "completed":
                # Success! We have results
                assert "result" in status_data
                assert status_data["result"]["overall_score"] >= 0
                assert status_data["result"]["overall_score"] <= 100
                assert len(status_data["result"]["analysis_summary"]) > 0
                break
            elif status_data["status"] == "error":
                pytest.fail(f"Analysis failed: {status_data.get('error_message', 'Unknown error')}")
            else:
                # Still processing, wait and poll again
                poll_count += 1
                await asyncio.sleep(2)  # Wait 2 seconds between polls
        else:
            pytest.fail(f"Analysis did not complete within {max_polls * 2} seconds")
        
        # Step 4: Verify we can retrieve the resume details
        resume_response = await async_client.get(
            f"/api/v1/resumes/{resume_id}",
            headers=auth_headers
        )
        
        assert resume_response.status_code == 200
        resume_data = resume_response.json()
        
        assert resume_data["id"] == resume_id
        assert resume_data["can_analyze"] == True
        assert len(resume_data["extracted_text"]) > 0
        
        # Step 5: Verify analysis history
        history_response = await async_client.get(
            f"/api/v1/resumes/{resume_id}/analyses",
            headers=auth_headers
        )
        
        assert history_response.status_code == 200
        history_data = history_response.json()
        
        assert len(history_data) >= 1
        assert any(analysis["id"] == analysis_id for analysis in history_data)
    
    async def test_duplicate_resume_detection(
        self,
        async_client: AsyncClient,
        authenticated_user,
        test_candidate,
        sample_pdf_resume
    ):
        """Test that duplicate resumes are properly detected."""
        
        auth_headers = {"Authorization": f"Bearer {authenticated_user.access_token}"}
        
        # Upload same resume twice
        for attempt in [1, 2]:
            upload_response = await async_client.post(
                f"/api/v1/candidates/{test_candidate.id}/resumes",
                files={"file": ("test_resume.pdf", sample_pdf_resume, "application/pdf")},
                headers=auth_headers
            )
            
            if attempt == 1:
                # First upload should succeed
                assert upload_response.status_code == 201
                assert upload_response.json()["status"] == "uploaded_successfully"
            else:
                # Second upload should detect duplicate
                assert upload_response.status_code == 200  # Still success, but different status
                assert upload_response.json()["status"] == "duplicate_detected"
    
    async def test_cached_analysis_reuse(
        self,
        async_client: AsyncClient,
        authenticated_user,
        test_candidate,
        sample_pdf_resume
    ):
        """Test that recent analyses are reused instead of re-processing."""
        
        auth_headers = {"Authorization": f"Bearer {authenticated_user.access_token}"}
        
        # Upload resume
        upload_response = await async_client.post(
            f"/api/v1/candidates/{test_candidate.id}/resumes",
            files={"file": ("test_resume.pdf", sample_pdf_resume, "application/pdf")},
            headers=auth_headers
        )
        resume_id = upload_response.json()["id"]
        
        # Request analysis twice with same parameters
        analysis_request = {"industry": "strategy_tech", "analysis_depth": "standard"}
        
        for attempt in [1, 2]:
            analysis_response = await async_client.post(
                f"/api/v1/resumes/{resume_id}/analysis",
                json=analysis_request,
                headers=auth_headers
            )
            
            analysis_data = analysis_response.json()
            
            if attempt == 1:
                # First request should queue processing
                assert analysis_data["status"] in ["processing", "completed"]
                
                # Wait for completion if needed
                if analysis_data["status"] == "processing":
                    analysis_id = analysis_data["analysis_id"]
                    # Poll until complete (simplified for test)
                    for _ in range(10):
                        status_response = await async_client.get(
                            f"/api/v1/analysis/{analysis_id}/status",
                            headers=auth_headers
                        )
                        if status_response.json()["status"] == "completed":
                            break
                        await asyncio.sleep(1)
                        
            else:
                # Second request should use cached result
                assert analysis_data.get("from_cache") == True
                assert analysis_data["status"] == "completed"
```

## Future Enhancement Roadmap (High-Level)

### **Short Term (Months 2-3): Smart Enhancements**
- Background section detection for new uploads
- Enhanced analysis quality with structured feedback
- A/B testing of section-aware vs raw text analysis

### **Medium Term (Months 4-6): AI-Powered Processing**
- Machine learning-based section detection
- Source attribution for analysis feedback
- Advanced document understanding (tables, formatting)

### **Long Term (Months 6+): Enterprise Features**
- OCR for scanned documents
- Real-time section highlighting in UI
- Advanced analytics and reporting
- Multi-language support

---

## Success Metrics for MVP

### **Performance Targets**
- Resume upload response time: < 3 seconds
- Analysis request response time: < 500ms (returns job ID)
- Analysis completion time: < 60 seconds
- Database storage reduction: ~40% (eliminated duplicate text)

### **Quality Targets**
- Zero code duplication between services
- 90% test coverage for critical paths
- All user flows match mental model (Upload → Analyze)

### **User Experience Validation**
- Users understand the two-step process (Upload → Request Analysis)
- Clear feedback during analysis processing
- Easy access to analysis history

This MVP plan balances immediate delivery needs with long-term architectural flexibility, ensuring you can ship quickly while building a foundation for future enhancements.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>