"""Candidate management API endpoints."""

import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from app.features.auth.api import get_current_user
from .service import CandidateService
from .schemas import (
    CandidateCreate,
    CandidateCreateResponse,
    CandidateInfo,
    CandidateListResponse,
    CandidateWithStats
)
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.models.auth import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post(
    "/",
    response_model=CandidateCreateResponse,
    summary="Create a new candidate"
)
async def create_candidate(
    candidate_data: CandidateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new candidate and auto-assign to the creator.
    
    The candidate will automatically be assigned to the user who creates them.
    """
    
    try:
        service = CandidateService(db)
        
        candidate = await service.create_candidate(
            first_name=candidate_data.first_name,
            last_name=candidate_data.last_name,
            created_by_user_id=current_user.id,
            email=candidate_data.email,
            phone=candidate_data.phone,
            current_company=candidate_data.current_company,
            current_position=candidate_data.current_position,
            years_experience=candidate_data.years_experience
        )
        
        return CandidateCreateResponse(
            success=True,
            message="Candidate created successfully",
            candidate=CandidateInfo.from_orm(candidate)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create candidate: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/",
    response_model=CandidateListResponse,
    summary="Get candidates for current user"
)
async def get_candidates(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get candidates based on user role and assignments.
    
    - Junior recruiters: Only assigned candidates
    - Senior recruiters/Admin: All candidates
    """
    
    try:
        service = CandidateService(db)
        
        candidates = await service.get_candidates_for_user(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format with basic stats
        candidate_list = []
        for candidate in candidates:
            candidate_with_stats = CandidateWithStats.from_orm(candidate)
            # TODO: Add resume stats when needed
            candidate_with_stats.total_resumes = 0
            candidate_with_stats.latest_resume_version = 0
            candidate_list.append(candidate_with_stats)
        
        return CandidateListResponse(
            candidates=candidate_list,
            total_count=len(candidates),  # TODO: Get actual count
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get candidates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve candidates")


@router.get(
    "/{candidate_id}",
    response_model=CandidateInfo,
    summary="Get a specific candidate"
)
async def get_candidate(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific candidate by ID.
    
    Access control applies based on user role and assignments.
    """
    
    try:
        service = CandidateService(db)
        
        candidate = await service.get_candidate_by_id(
            candidate_id=candidate_id,
            user_id=current_user.id
        )
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        return CandidateInfo.from_orm(candidate)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get candidate {candidate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve candidate")


@router.post(
    "/{candidate_id}/assign/{user_id}",
    summary="Assign a candidate to a user"
)
async def assign_candidate(
    candidate_id: uuid.UUID,
    user_id: uuid.UUID,
    assignment_type: str = "secondary",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign a candidate to a user.
    
    Only admin and senior recruiters can assign candidates.
    """
    
    try:
        service = CandidateService(db)
        
        success = await service.assign_candidate(
            candidate_id=candidate_id,
            user_id=user_id,
            assigned_by_user_id=current_user.id,
            assignment_type=assignment_type
        )
        
        if success:
            return {"success": True, "message": "Candidate assigned successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to assign candidate")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign candidate {candidate_id} to user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to assign candidate")