"""
Candidate management API endpoints.

Architecture:
- Simple read operations: API → Repository (list, get by ID)
- Complex operations: API → Service → Repository (create, assign)
"""

import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import get_current_user
from .service import CandidateService
from .repository import CandidateRepository
from .schemas import (
    CandidateCreate,
    CandidateCreateResponse,
    CandidateInfo,
    CandidateListResponse,
    CandidateWithStats
)
from database.models.auth import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["candidates"])


# Dependency injection
async def get_candidate_repository(
    session: AsyncSession = Depends(get_async_session)
) -> CandidateRepository:
    """Dependency to get candidate repository (for simple reads)."""
    return CandidateRepository(session)


async def get_candidate_service(
    session: AsyncSession = Depends(get_async_session)
) -> CandidateService:
    """Dependency to get candidate service (for complex operations)."""
    return CandidateService(session)


@router.post(
    "/",
    response_model=CandidateCreateResponse,
    summary="Create a new candidate"
)
async def create_candidate(
    candidate_data: CandidateCreate,
    current_user: User = Depends(get_current_user),
    service: CandidateService = Depends(get_candidate_service)
):
    """
    Create a new candidate and auto-assign to the creator.

    The candidate will automatically be assigned to the user who creates them.

    Architecture: Complex operation → Uses service layer for multi-table transaction
    """
    try:
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
    repo: CandidateRepository = Depends(get_candidate_repository)
):
    """
    Get candidates based on user role and assignments.

    - Junior recruiters: Only assigned candidates
    - Senior recruiters/Admin: All candidates

    Architecture: Simple read with role-based filtering → Repository
    """
    try:
        # Get candidates from repository (role-based filtering)
        candidates = await repo.list_for_user(
            user_id=current_user.id,
            user_role=current_user.role,
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
    repo: CandidateRepository = Depends(get_candidate_repository)
):
    """
    Get a specific candidate by ID.

    Access control applies based on user role and assignments:
    - Admin/Senior recruiters: Access all candidates
    - Junior recruiters: Access only assigned candidates

    Architecture: Simple read with access check → Repository
    """
    try:
        # Get candidate from repository (access check handled by repository)
        candidate = await repo.get_for_user(
            candidate_id=candidate_id,
            user_id=current_user.id,
            user_role=current_user.role
        )

        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found or access denied")

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
    service: CandidateService = Depends(get_candidate_service)
):
    """
    Assign a candidate to a user.

    Only admin and senior recruiters can assign candidates.

    Architecture: Complex operation → Uses service layer for permission checks
    """
    try:
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