"""Resume upload API endpoints with candidate-centric architecture."""

import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from sqlalchemy.orm import Session

from database.connection import get_db
from app.features.auth.api import get_current_user
from .service import ResumeUploadService
from .schemas import (
    ResumeUploadResponse,
    ResumeInfo,
    ResumeContent,
    ResumeListResponse,
    ResumeStatsResponse,
    ProcessingStatus,
    ResumeErrorResponse
)
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.models.auth import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    summary="Upload a resume for a candidate"
)
async def upload_resume(
    candidate_id: uuid.UUID = Form(..., description="ID of the candidate this resume belongs to"),
    file: UploadFile = File(..., description="Resume file to upload"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a resume for a specific candidate.
    
    This endpoint:
    - Validates user has access to the candidate (role-based)
    - Processes the uploaded file (PDF, DOCX, DOC, TXT)
    - Extracts text content for analysis
    - Handles versioning automatically
    - Prevents duplicate uploads
    """
    
    try:
        service = ResumeUploadService(db)
        
        resume = await service.upload_resume_for_candidate(
            candidate_id=candidate_id,
            file=file,
            uploaded_by_user_id=current_user.id
        )
        
        return ResumeUploadResponse(
            success=True,
            message=f"Resume uploaded successfully (version {resume.version_number})",
            resume=ResumeInfo.from_orm(resume)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during upload")


@router.get(
    "/candidate/{candidate_id}",
    response_model=ResumeListResponse,
    summary="Get all resumes for a candidate"
)
async def get_candidate_resumes(
    candidate_id: uuid.UUID,
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all resumes for a specific candidate.
    
    Access control:
    - Junior recruiters: Only assigned candidates
    - Senior recruiters/Admin: All candidates
    """
    
    try:
        service = ResumeUploadService(db)
        
        resumes = await service.get_candidate_resumes(
            candidate_id=candidate_id,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        # Get total count for pagination
        stats = await service.get_candidate_resume_stats(candidate_id, current_user.id)
        
        return ResumeListResponse(
            resumes=[ResumeInfo.from_orm(resume) for resume in resumes],
            total_count=stats["total_resumes"],
            candidate_id=candidate_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get candidate resumes: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve resumes")


@router.get(
    "/{resume_id}",
    response_model=ResumeContent,
    summary="Get a specific resume with content"
)
async def get_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific resume by ID with extracted text content.
    
    Includes access control validation.
    """
    
    try:
        service = ResumeUploadService(db)
        
        resume = await service.get_resume_by_id(resume_id, current_user.id)
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        return ResumeContent.from_orm(resume)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resume {resume_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve resume")


@router.get(
    "/candidate/{candidate_id}/latest",
    response_model=ResumeContent,
    summary="Get the latest resume for a candidate"
)
async def get_latest_resume(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the most recent resume version for a candidate.
    """
    
    try:
        service = ResumeUploadService(db)
        
        resume = await service.get_latest_resume_for_candidate(
            candidate_id=candidate_id,
            user_id=current_user.id
        )
        
        if not resume:
            raise HTTPException(
                status_code=404, 
                detail="No resumes found for this candidate"
            )
        
        return ResumeContent.from_orm(resume)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest resume for candidate {candidate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve latest resume")


@router.get(
    "/candidate/{candidate_id}/stats",
    response_model=ResumeStatsResponse,
    summary="Get resume statistics for a candidate"
)
async def get_candidate_resume_stats(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics about resumes for a candidate.
    
    Returns counts, sizes, versions, etc.
    """
    
    try:
        service = ResumeUploadService(db)
        
        stats = await service.get_candidate_resume_stats(
            candidate_id=candidate_id,
            user_id=current_user.id
        )
        
        return ResumeStatsResponse(
            stats=stats
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resume stats for candidate {candidate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve resume statistics")


@router.get(
    "/{resume_id}/status",
    response_model=ProcessingStatus,
    summary="Get processing status for a resume"
)
async def get_resume_processing_status(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current processing status of a resume upload.
    
    Useful for tracking upload progress and debugging issues.
    """
    
    try:
        service = ResumeUploadService(db)
        
        resume = await service.get_resume_by_id(resume_id, current_user.id)
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        return ProcessingStatus(
            resume_id=resume.id,
            status=resume.status,
            progress=resume.progress,
            started_at=resume.uploaded_at,
            completed_at=resume.processed_at,
            message=f"Resume processing {resume.status}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get processing status for resume {resume_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve processing status")


# Note: Exception handlers should be registered at the app level, not router level