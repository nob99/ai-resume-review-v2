# Hierarchical Access Control - Future Design (Post-MVP)

**Document Type**: Future Requirements & Technical Design
**Created**: 2025-10-06
**Status**: PLANNED - For implementation after MVP
**Priority**: High (Enterprise Feature)
**Estimated Effort**: 4-6 weeks

---

## Executive Summary

This document outlines the **hierarchical access control system** for the AI Resume Review platform, enabling **granular team management** where Senior Recruiters manage Junior Recruiters within organizational boundaries.

**Current MVP Approach (Approach 1)**:
- Seniors see ALL data (same as Admin)
- No Senior-Junior relationship tracking
- Simple role-based access: `if role in ['admin', 'senior_recruiter']: see_all`

**Future Approach (Approach 2)**:
- Seniors see ONLY their assigned Juniors' data
- Explicit team assignments with audit trail
- Supports matrix organizations and reassignments

---

## Business Requirements

### User Roles & Responsibilities

#### **Admin**
- **Scope**: Organization-wide access
- **Can**:
  - View all users, candidates, resumes, analyses
  - Create/edit/delete any user
  - Assign Juniors to Seniors
  - Reassign team members
  - Access system configuration

#### **Senior Recruiter**
- **Scope**: Team-level access (assigned Juniors only)
- **Can**:
  - View candidates assigned to their Juniors
  - View resumes uploaded by their Juniors
  - View analysis results from their Juniors
  - View their own data
  - Upload resumes for team candidates
  - Request analyses for team candidates
- **Cannot**:
  - View other Seniors' team data
  - Create/edit users (Admin only)
  - Reassign Juniors (Admin only)

#### **Junior Recruiter**
- **Scope**: Personal assignments only
- **Can**:
  - Create candidates (auto-assigned to self)
  - View assigned candidates only
  - Upload resumes for assigned candidates
  - Request analyses for own resumes
  - View own analysis results
- **Cannot**:
  - View unassigned candidates
  - View other Juniors' data
  - Assign candidates to others

### Access Control Matrix

| Resource | Admin | Senior (Own) | Senior (Junior's) | Junior (Own) | Junior (Other's) |
|----------|-------|--------------|-------------------|--------------|------------------|
| **Users - View** | All | Self | Team | Self | ❌ Denied |
| **Users - Edit** | All | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied |
| **Candidates - View** | All | Own | Team's | Assigned | ❌ Denied |
| **Candidates - Create** | All | All | - | All | - |
| **Candidates - Assign** | All | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied |
| **Resumes - View** | All | Own | Team's | Own | ❌ Denied |
| **Resumes - Upload** | All | Own + Team | Team's candidates | Assigned candidates | ❌ Denied |
| **Analysis - View** | All | Own | Team's | Own | ❌ Denied |
| **Analysis - Request** | All | Own + Team | Team's resumes | Own resumes | ❌ Denied |
| **Team - Manage** | All | ❌ Denied | ❌ Denied | ❌ Denied | ❌ Denied |

---

## Technical Design

### Architecture Choice: **Option B - Team Assignments Table** ✅

**Why Option B over Option A**:
- ✅ Supports **many-to-many** relationships (Junior can have multiple Seniors)
- ✅ Full **audit trail** (who assigned, when, why)
- ✅ **Reassignment history** preserved
- ✅ Supports **matrix organizations** (common in consulting firms)
- ✅ Enables **temporary assignments** (e.g., vacation coverage)
- ✅ **Zero data loss** on team structure changes

**Trade-offs**:
- ❌ Additional JOIN in queries (minimal performance impact with indexes)
- ❌ Slightly more complex queries
- ✅ Better for enterprise scalability

---

## Database Schema Design

### New Table: `team_assignments`

```sql
CREATE TABLE team_assignments (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationship
    senior_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    junior_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Assignment metadata
    assignment_type VARCHAR(20) DEFAULT 'direct',  -- direct, temporary, backup
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    assigned_by_user_id UUID NOT NULL REFERENCES users(id),

    -- Unassignment tracking
    unassigned_at TIMESTAMP WITH TIME ZONE,
    unassigned_by_user_id UUID REFERENCES users(id),
    unassigned_reason TEXT,

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_different_users CHECK (senior_user_id != junior_user_id),
    CONSTRAINT chk_valid_assignment_type CHECK (
        assignment_type IN ('direct', 'temporary', 'backup')
    ),

    -- Unique: One active assignment per senior-junior pair
    UNIQUE(senior_user_id, junior_user_id, is_active)
        WHERE is_active = TRUE
);

-- Performance indexes
CREATE INDEX idx_team_senior_active
    ON team_assignments(senior_user_id, is_active)
    WHERE is_active = TRUE;

CREATE INDEX idx_team_junior_active
    ON team_assignments(junior_user_id, is_active)
    WHERE is_active = TRUE;

CREATE INDEX idx_team_assigned_at
    ON team_assignments(assigned_at DESC);

CREATE INDEX idx_team_assigned_by
    ON team_assignments(assigned_by_user_id);

-- Trigger to update updated_at
CREATE TRIGGER update_team_assignments_updated_at
    BEFORE UPDATE ON team_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### Assignment Types

| Type | Use Case | Example |
|------|----------|---------|
| `direct` | Primary reporting relationship | Junior reports to this Senior |
| `temporary` | Temporary coverage (vacation, leave) | Senior A covers Senior B's team |
| `backup` | Secondary supervisor | Shared responsibility for specific projects |

---

## Database Model

### SQLAlchemy Model

```python
# database/models/team.py

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates

from . import Base
from app.core.datetime_utils import utc_now


class AssignmentType:
    """Team assignment type constants."""
    DIRECT = "direct"
    TEMPORARY = "temporary"
    BACKUP = "backup"

    @classmethod
    def all(cls) -> list:
        return [cls.DIRECT, cls.TEMPORARY, cls.BACKUP]


class TeamAssignment(Base):
    """
    Team assignment model for Senior-Junior relationships.

    Enables hierarchical access control where Seniors manage Juniors.
    Supports many-to-many relationships with full audit trail.

    Business Rules:
    - Juniors can have multiple Seniors (matrix org)
    - Seniors manage multiple Juniors
    - Assignment history is preserved (soft deletes)
    - Only one active assignment per Senior-Junior pair
    """

    __tablename__ = 'team_assignments'

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationship
    senior_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    junior_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Assignment metadata
    assignment_type = Column(
        String(20),
        nullable=False,
        default=AssignmentType.DIRECT
    )
    assigned_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True
    )
    assigned_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False
    )

    # Unassignment tracking
    unassigned_at = Column(DateTime(timezone=True), nullable=True)
    unassigned_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=True
    )
    unassigned_reason = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Audit timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now
    )

    # Relationships
    senior = relationship(
        "User",
        foreign_keys=[senior_user_id],
        backref="managed_juniors_assignments"
    )
    junior = relationship(
        "User",
        foreign_keys=[junior_user_id],
        backref="senior_assignments"
    )
    assigned_by = relationship(
        "User",
        foreign_keys=[assigned_by_user_id]
    )
    unassigned_by = relationship(
        "User",
        foreign_keys=[unassigned_by_user_id]
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            'senior_user_id != junior_user_id',
            name='chk_different_users'
        ),
        CheckConstraint(
            f"assignment_type IN ('{AssignmentType.DIRECT}', "
            f"'{AssignmentType.TEMPORARY}', '{AssignmentType.BACKUP}')",
            name='chk_valid_assignment_type'
        ),
    )

    @validates('assignment_type')
    def validate_assignment_type(self, key, assignment_type):
        """Validate assignment type."""
        if assignment_type not in AssignmentType.all():
            raise ValueError(
                f"Invalid assignment type. Must be one of: {AssignmentType.all()}"
            )
        return assignment_type

    @property
    def is_currently_active(self) -> bool:
        """Check if assignment is currently active."""
        return self.is_active and self.unassigned_at is None

    @property
    def assignment_duration_days(self) -> Optional[int]:
        """Calculate assignment duration in days."""
        if not self.unassigned_at:
            # Active assignment - duration until now
            delta = utc_now() - self.assigned_at
        else:
            # Completed assignment
            delta = self.unassigned_at - self.assigned_at
        return delta.days

    def unassign(
        self,
        reason: Optional[str] = None,
        unassigned_by_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Mark assignment as inactive.

        Args:
            reason: Reason for unassignment (optional)
            unassigned_by_user_id: User ID who performed unassignment
        """
        self.is_active = False
        self.unassigned_at = utc_now()
        self.unassigned_reason = reason
        self.unassigned_by_user_id = unassigned_by_user_id

    def __repr__(self) -> str:
        """String representation."""
        status = "Active" if self.is_currently_active else "Inactive"
        return (
            f"<TeamAssignment("
            f"senior={self.senior_user_id}, "
            f"junior={self.junior_user_id}, "
            f"type='{self.assignment_type}', "
            f"status='{status}')>"
        )
```

---

## Repository Layer Implementation

### Team Assignment Repository

```python
# backend/app/features/admin/team_repository.py

import uuid
from typing import List, Optional, Tuple
from datetime import datetime

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import BaseRepository
from app.core.datetime_utils import utc_now
from database.models.team import TeamAssignment, AssignmentType
from database.models.auth import User


class TeamAssignmentRepository(BaseRepository[TeamAssignment]):
    """Repository for team assignment operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, TeamAssignment)

    async def assign_junior_to_senior(
        self,
        senior_user_id: uuid.UUID,
        junior_user_id: uuid.UUID,
        assigned_by_user_id: uuid.UUID,
        assignment_type: str = AssignmentType.DIRECT
    ) -> TeamAssignment:
        """
        Assign a junior to a senior.

        Args:
            senior_user_id: Senior user ID
            junior_user_id: Junior user ID
            assigned_by_user_id: User ID who performed the assignment
            assignment_type: Type of assignment

        Returns:
            Created team assignment

        Raises:
            ValueError: If assignment already exists or invalid users
        """
        # Validate users exist and have correct roles
        senior = await self._validate_senior_role(senior_user_id)
        junior = await self._validate_junior_role(junior_user_id)

        # Check for existing active assignment
        existing = await self.get_active_assignment(
            senior_user_id=senior_user_id,
            junior_user_id=junior_user_id
        )

        if existing:
            raise ValueError(
                f"Active assignment already exists between "
                f"senior {senior_user_id} and junior {junior_user_id}"
            )

        # Create assignment
        assignment = TeamAssignment(
            senior_user_id=senior_user_id,
            junior_user_id=junior_user_id,
            assignment_type=assignment_type,
            assigned_by_user_id=assigned_by_user_id,
            is_active=True
        )

        self.session.add(assignment)
        await self.session.commit()
        await self.session.refresh(assignment)

        return assignment

    async def get_active_assignment(
        self,
        senior_user_id: uuid.UUID,
        junior_user_id: uuid.UUID
    ) -> Optional[TeamAssignment]:
        """Get active assignment between senior and junior."""
        query = select(TeamAssignment).where(
            and_(
                TeamAssignment.senior_user_id == senior_user_id,
                TeamAssignment.junior_user_id == junior_user_id,
                TeamAssignment.is_active == True
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_managed_juniors(
        self,
        senior_user_id: uuid.UUID,
        include_inactive: bool = False
    ) -> List[User]:
        """
        Get all juniors managed by a senior.

        Args:
            senior_user_id: Senior user ID
            include_inactive: Include inactive assignments

        Returns:
            List of junior User objects
        """
        query = (
            select(User)
            .join(TeamAssignment, TeamAssignment.junior_user_id == User.id)
            .where(TeamAssignment.senior_user_id == senior_user_id)
        )

        if not include_inactive:
            query = query.where(TeamAssignment.is_active == True)

        query = query.order_by(User.last_name, User.first_name)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_managed_junior_ids(
        self,
        senior_user_id: uuid.UUID
    ) -> List[uuid.UUID]:
        """
        Get list of junior IDs managed by a senior.

        Optimized for access control queries.

        Args:
            senior_user_id: Senior user ID

        Returns:
            List of junior user IDs
        """
        query = select(TeamAssignment.junior_user_id).where(
            and_(
                TeamAssignment.senior_user_id == senior_user_id,
                TeamAssignment.is_active == True
            )
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_senior_managers(
        self,
        junior_user_id: uuid.UUID,
        include_inactive: bool = False
    ) -> List[User]:
        """
        Get all seniors managing a junior.

        Args:
            junior_user_id: Junior user ID
            include_inactive: Include inactive assignments

        Returns:
            List of senior User objects
        """
        query = (
            select(User)
            .join(TeamAssignment, TeamAssignment.senior_user_id == User.id)
            .where(TeamAssignment.junior_user_id == junior_user_id)
        )

        if not include_inactive:
            query = query.where(TeamAssignment.is_active == True)

        query = query.order_by(User.last_name, User.first_name)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def unassign_junior(
        self,
        senior_user_id: uuid.UUID,
        junior_user_id: uuid.UUID,
        unassigned_by_user_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> bool:
        """
        Unassign a junior from a senior.

        Args:
            senior_user_id: Senior user ID
            junior_user_id: Junior user ID
            unassigned_by_user_id: User ID who performed unassignment
            reason: Reason for unassignment

        Returns:
            True if unassigned, False if no active assignment found
        """
        assignment = await self.get_active_assignment(
            senior_user_id=senior_user_id,
            junior_user_id=junior_user_id
        )

        if not assignment:
            return False

        assignment.unassign(
            reason=reason,
            unassigned_by_user_id=unassigned_by_user_id
        )

        await self.session.commit()
        return True

    async def get_team_statistics(
        self,
        senior_user_id: uuid.UUID
    ) -> dict:
        """
        Get team statistics for a senior.

        Returns:
            Dictionary with team stats (total juniors, active assignments, etc.)
        """
        # Count active assignments
        active_query = select(func.count(TeamAssignment.id)).where(
            and_(
                TeamAssignment.senior_user_id == senior_user_id,
                TeamAssignment.is_active == True
            )
        )
        active_result = await self.session.execute(active_query)
        active_count = active_result.scalar() or 0

        # Count total assignments (including inactive)
        total_query = select(func.count(TeamAssignment.id)).where(
            TeamAssignment.senior_user_id == senior_user_id
        )
        total_result = await self.session.execute(total_query)
        total_count = total_result.scalar() or 0

        return {
            "active_juniors": active_count,
            "total_assignments": total_count,
            "inactive_assignments": total_count - active_count
        }

    async def is_junior_managed_by_senior(
        self,
        junior_user_id: uuid.UUID,
        senior_user_id: uuid.UUID
    ) -> bool:
        """
        Check if a junior is managed by a specific senior.

        Optimized for access control checks.

        Args:
            junior_user_id: Junior user ID
            senior_user_id: Senior user ID

        Returns:
            True if active assignment exists
        """
        query = select(TeamAssignment.id).where(
            and_(
                TeamAssignment.senior_user_id == senior_user_id,
                TeamAssignment.junior_user_id == junior_user_id,
                TeamAssignment.is_active == True
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    # Helper methods

    async def _validate_senior_role(self, user_id: uuid.UUID) -> User:
        """Validate user exists and has senior or admin role."""
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        if user.role not in ['senior_recruiter', 'admin']:
            raise ValueError(
                f"User {user_id} must have senior_recruiter or admin role"
            )

        return user

    async def _validate_junior_role(self, user_id: uuid.UUID) -> User:
        """Validate user exists and has junior role."""
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        if user.role != 'junior_recruiter':
            raise ValueError(
                f"User {user_id} must have junior_recruiter role"
            )

        return user
```

---

## Analysis Repository with Hierarchical Access

```python
# backend/app/features/resume_analysis/repository.py

class AnalysisRepository:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.request_repo = ReviewRequestRepository(session)
        self.result_repo = ReviewResultRepository(session)
        self.team_repo = TeamAssignmentRepository(session)  # NEW

    async def get_analysis_for_user(
        self,
        analysis_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str
    ) -> Optional[Tuple[ReviewRequest, Optional[ReviewResult]]]:
        """
        Get analysis with hierarchical access control.

        Access Rules:
        - Admin: All analyses
        - Senior: Own + managed juniors' analyses
        - Junior: Own analyses only
        """
        # Get the analysis
        analysis_data = await self.get_analysis_with_results(analysis_id)
        if not analysis_data:
            return None

        request, result = analysis_data

        # Admin sees everything
        if user_role == 'admin':
            return analysis_data

        # Senior sees own + managed juniors' analyses
        if user_role == 'senior_recruiter':
            # Check if user owns this analysis
            if request.requested_by_user_id == user_id:
                return analysis_data

            # Check if analysis belongs to a managed junior
            is_managed = await self.team_repo.is_junior_managed_by_senior(
                junior_user_id=request.requested_by_user_id,
                senior_user_id=user_id
            )

            if is_managed:
                return analysis_data

            return None  # Access denied

        # Junior sees only own analyses
        if request.requested_by_user_id == user_id:
            return analysis_data

        return None  # Access denied

    async def list_analyses_for_user(
        self,
        user_id: uuid.UUID,
        user_role: str,
        limit: int = 10,
        offset: int = 0,
        status: Optional[str] = None,
        industry: Optional[str] = None
    ) -> List[ReviewRequest]:
        """
        List analyses with hierarchical access control.

        Access Rules:
        - Admin: All analyses
        - Senior: Own + managed juniors' analyses
        - Junior: Own analyses only
        """
        if user_role == 'admin':
            # Admin sees all analyses
            query = select(ReviewRequest)

        elif user_role == 'senior_recruiter':
            # Senior sees own + managed juniors' analyses
            junior_ids = await self.team_repo.get_managed_junior_ids(user_id)

            # Include user's own ID for their own analyses
            allowed_user_ids = [user_id] + junior_ids

            query = select(ReviewRequest).where(
                ReviewRequest.requested_by_user_id.in_(allowed_user_ids)
            )

        else:  # junior_recruiter
            # Junior sees only own analyses
            query = select(ReviewRequest).where(
                ReviewRequest.requested_by_user_id == user_id
            )

        # Apply additional filters
        if status:
            query = query.where(ReviewRequest.status == status)

        if industry:
            query = query.where(ReviewRequest.target_industry == industry)

        # Apply pagination and ordering
        query = query.order_by(ReviewRequest.requested_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_analyses_for_user(
        self,
        user_id: uuid.UUID,
        user_role: str,
        status: Optional[str] = None,
        industry: Optional[str] = None
    ) -> int:
        """Count analyses accessible to user (for pagination)."""
        if user_role == 'admin':
            query = select(func.count(ReviewRequest.id))

        elif user_role == 'senior_recruiter':
            junior_ids = await self.team_repo.get_managed_junior_ids(user_id)
            allowed_user_ids = [user_id] + junior_ids

            query = select(func.count(ReviewRequest.id)).where(
                ReviewRequest.requested_by_user_id.in_(allowed_user_ids)
            )

        else:
            query = select(func.count(ReviewRequest.id)).where(
                ReviewRequest.requested_by_user_id == user_id
            )

        # Apply filters
        if status:
            query = query.where(ReviewRequest.status == status)

        if industry:
            query = query.where(ReviewRequest.target_industry == industry)

        result = await self.session.execute(query)
        return result.scalar() or 0
```

---

## Admin API Endpoints

```python
# backend/app/features/admin/team_api.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid

from app.core.dependencies import require_admin, get_current_user
from app.core.database import get_async_session
from database.models.auth import User
from .team_repository import TeamAssignmentRepository
from .team_schemas import (
    TeamAssignmentCreate,
    TeamAssignmentResponse,
    TeamMemberResponse,
    TeamStatsResponse
)

router = APIRouter(prefix="/api/v1/admin/teams", tags=["admin-teams"])


async def get_team_repo(
    session: AsyncSession = Depends(get_async_session)
) -> TeamAssignmentRepository:
    return TeamAssignmentRepository(session)


@router.post("/assign")
async def assign_junior_to_senior(
    assignment_data: TeamAssignmentCreate,
    current_user: User = Depends(require_admin),
    repo: TeamAssignmentRepository = Depends(get_team_repo)
):
    """
    Assign a junior to a senior (Admin only).

    Creates a team assignment relationship.
    """
    try:
        assignment = await repo.assign_junior_to_senior(
            senior_user_id=assignment_data.senior_user_id,
            junior_user_id=assignment_data.junior_user_id,
            assigned_by_user_id=current_user.id,
            assignment_type=assignment_data.assignment_type
        )

        return TeamAssignmentResponse.from_orm(assignment)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/unassign/{senior_id}/{junior_id}")
async def unassign_junior_from_senior(
    senior_id: uuid.UUID,
    junior_id: uuid.UUID,
    reason: str = None,
    current_user: User = Depends(require_admin),
    repo: TeamAssignmentRepository = Depends(get_team_repo)
):
    """
    Unassign a junior from a senior (Admin only).
    """
    success = await repo.unassign_junior(
        senior_user_id=senior_id,
        junior_user_id=junior_id,
        unassigned_by_user_id=current_user.id,
        reason=reason
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="No active assignment found"
        )

    return {"message": "Junior unassigned successfully"}


@router.get("/senior/{senior_id}/juniors", response_model=List[TeamMemberResponse])
async def get_senior_team(
    senior_id: uuid.UUID,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    repo: TeamAssignmentRepository = Depends(get_team_repo)
):
    """
    Get all juniors managed by a senior.

    Authorization:
    - Admins can view any senior's team
    - Seniors can view their own team only
    """
    # Authorization check
    if current_user.role != 'admin' and current_user.id != senior_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: Can only view your own team"
        )

    juniors = await repo.get_managed_juniors(
        senior_user_id=senior_id,
        include_inactive=include_inactive
    )

    return [TeamMemberResponse.from_orm(junior) for junior in juniors]


@router.get("/junior/{junior_id}/seniors", response_model=List[TeamMemberResponse])
async def get_junior_managers(
    junior_id: uuid.UUID,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    repo: TeamAssignmentRepository = Depends(get_team_repo)
):
    """
    Get all seniors managing a junior.

    Authorization:
    - Admins can view any junior's managers
    - Juniors can view their own managers only
    """
    # Authorization check
    if current_user.role != 'admin' and current_user.id != junior_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: Can only view your own managers"
        )

    seniors = await repo.get_senior_managers(
        junior_user_id=junior_id,
        include_inactive=include_inactive
    )

    return [TeamMemberResponse.from_orm(senior) for senior in seniors]


@router.get("/senior/{senior_id}/stats", response_model=TeamStatsResponse)
async def get_team_statistics(
    senior_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    repo: TeamAssignmentRepository = Depends(get_team_repo)
):
    """
    Get team statistics for a senior.

    Authorization: Admin or the senior themselves.
    """
    # Authorization check
    if current_user.role != 'admin' and current_user.id != senior_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    stats = await repo.get_team_statistics(senior_id)

    return TeamStatsResponse(**stats)
```

---

## Migration Plan

### Phase 1: Database Migration (Week 1)

**Tasks**:
1. Create `team_assignments` table
2. Add indexes for performance
3. Create database constraints
4. Add trigger for `updated_at`

**Migration Script**:
```bash
# Create migration
alembic revision -m "add_team_assignments_table"

# Apply migration
alembic upgrade head

# Verify
psql -d ai_resume_review_dev -c "SELECT * FROM team_assignments LIMIT 1;"
```

**Rollback Plan**:
```bash
# Rollback migration if issues occur
alembic downgrade -1
```

### Phase 2: Model & Repository (Week 2)

**Tasks**:
1. Create `TeamAssignment` model
2. Create `TeamAssignmentRepository`
3. Unit tests for repository methods
4. Integration tests for team operations

**Deliverables**:
- `database/models/team.py`
- `backend/app/features/admin/team_repository.py`
- Test coverage: 80%+

### Phase 3: Access Control Integration (Week 3)

**Tasks**:
1. Update `AnalysisRepository` with team-aware methods
2. Update `ResumeRepository` with team-aware methods
3. Update `CandidateRepository` (if needed)
4. Update service layers to pass `user_role`
5. Integration tests for access control

**Files Modified**:
- `backend/app/features/resume_analysis/repository.py`
- `backend/app/features/resume_upload/repository.py`
- `backend/app/features/resume_analysis/service.py`
- `backend/app/features/resume_upload/service.py`

### Phase 4: Admin API (Week 4)

**Tasks**:
1. Create team management API endpoints
2. Create Pydantic schemas for team operations
3. Add authorization decorators
4. API integration tests
5. OpenAPI documentation

**Deliverables**:
- `backend/app/features/admin/team_api.py`
- `backend/app/features/admin/team_schemas.py`
- Postman collection for testing

### Phase 5: Frontend Integration (Week 5-6)

**Tasks**:
1. Team management UI for admins
2. Team view dashboard for seniors
3. "My Managers" view for juniors
4. Update access control in frontend
5. E2E tests

**Components**:
- `frontend/src/features/admin/TeamManagement.tsx`
- `frontend/src/features/team/TeamDashboard.tsx`
- `frontend/src/features/team/MyManagers.tsx`

---

## Testing Strategy

### Unit Tests

```python
# backend/app/features/admin/tests/test_team_repository.py

class TestTeamAssignmentRepository:

    async def test_assign_junior_to_senior(self):
        """Test assigning a junior to a senior."""
        senior = create_user(role='senior_recruiter')
        junior = create_user(role='junior_recruiter')
        admin = create_user(role='admin')

        assignment = await repo.assign_junior_to_senior(
            senior_user_id=senior.id,
            junior_user_id=junior.id,
            assigned_by_user_id=admin.id
        )

        assert assignment.is_active
        assert assignment.senior_user_id == senior.id
        assert assignment.junior_user_id == junior.id

    async def test_duplicate_assignment_raises_error(self):
        """Test that duplicate assignments raise error."""
        # Create first assignment
        await repo.assign_junior_to_senior(...)

        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await repo.assign_junior_to_senior(...)

    async def test_get_managed_juniors(self):
        """Test getting juniors managed by a senior."""
        senior = create_user(role='senior_recruiter')
        junior1 = create_user(role='junior_recruiter')
        junior2 = create_user(role='junior_recruiter')

        await repo.assign_junior_to_senior(senior.id, junior1.id, admin.id)
        await repo.assign_junior_to_senior(senior.id, junior2.id, admin.id)

        juniors = await repo.get_managed_juniors(senior.id)

        assert len(juniors) == 2
        assert junior1 in juniors
        assert junior2 in juniors
```

### Integration Tests

```python
# backend/app/features/resume_analysis/tests/test_hierarchical_access.py

class TestHierarchicalAccessControl:

    async def test_senior_can_view_junior_analysis(self):
        """Senior can view analysis from their junior."""
        senior = create_user(role='senior_recruiter')
        junior = create_user(role='junior_recruiter')

        # Assign junior to senior
        await team_repo.assign_junior_to_senior(senior.id, junior.id, admin.id)

        # Junior creates analysis
        candidate = create_candidate(created_by=junior.id)
        resume = create_resume(candidate_id=candidate.id, uploaded_by=junior.id)
        analysis = create_analysis(resume_id=resume.id, requested_by=junior.id)

        # Senior retrieves analysis
        result = await service.get_analysis_result(
            request_id=analysis.id,
            user_id=senior.id,
            user_role='senior_recruiter'
        )

        assert result is not None

    async def test_senior_cannot_view_other_team_analysis(self):
        """Senior cannot view analysis from another senior's junior."""
        senior_a = create_user(role='senior_recruiter')
        senior_b = create_user(role='senior_recruiter')
        junior_b = create_user(role='junior_recruiter')

        # Junior B assigned to Senior B
        await team_repo.assign_junior_to_senior(senior_b.id, junior_b.id, admin.id)

        # Junior B creates analysis
        analysis = create_analysis(requested_by=junior_b.id)

        # Senior A tries to access
        with pytest.raises(ValueError, match="access denied"):
            await service.get_analysis_result(
                request_id=analysis.id,
                user_id=senior_a.id,
                user_role='senior_recruiter'
            )

    async def test_reassignment_updates_access(self):
        """Access changes when junior is reassigned to different senior."""
        senior_a = create_user(role='senior_recruiter')
        senior_b = create_user(role='senior_recruiter')
        junior = create_user(role='junior_recruiter')

        # Initially assigned to Senior A
        await team_repo.assign_junior_to_senior(senior_a.id, junior.id, admin.id)

        # Junior creates analysis
        analysis = create_analysis(requested_by=junior.id)

        # Senior A can access
        result = await service.get_analysis_result(
            analysis.id, senior_a.id, 'senior_recruiter'
        )
        assert result is not None

        # Reassign to Senior B
        await team_repo.unassign_junior(senior_a.id, junior.id, admin.id)
        await team_repo.assign_junior_to_senior(senior_b.id, junior.id, admin.id)

        # Senior A loses access
        with pytest.raises(ValueError, match="access denied"):
            await service.get_analysis_result(
                analysis.id, senior_a.id, 'senior_recruiter'
            )

        # Senior B gains access
        result = await service.get_analysis_result(
            analysis.id, senior_b.id, 'senior_recruiter'
        )
        assert result is not None
```

---

## Performance Considerations

### Query Optimization

**Problem**: Hierarchical access checks require JOINs
**Solution**: Strategic indexing + query optimization

**Indexes**:
```sql
-- Critical for team lookups
CREATE INDEX idx_team_senior_active
    ON team_assignments(senior_user_id, is_active)
    WHERE is_active = TRUE;

-- Critical for junior lookups
CREATE INDEX idx_team_junior_active
    ON team_assignments(junior_user_id, is_active)
    WHERE is_active = TRUE;

-- For analysis access checks
CREATE INDEX idx_review_requests_user
    ON review_requests(requested_by_user_id, requested_at DESC);
```

**Query Performance**:
- Simple role check (Admin): O(1)
- Senior access check: O(log n) with index
- Junior access check: O(1)

**Caching Strategy**:
```python
# Cache managed junior IDs for 5 minutes
from app.core.cache import cache_service

async def get_managed_junior_ids_cached(senior_id: UUID) -> List[UUID]:
    cache_key = f"team:senior:{senior_id}:juniors"

    cached = await cache_service.get(cache_key)
    if cached:
        return cached

    junior_ids = await team_repo.get_managed_junior_ids(senior_id)
    await cache_service.set(cache_key, junior_ids, ttl=300)  # 5 min

    return junior_ids
```

---

## Security Considerations

### Authorization Checks

**Principle**: Defense in depth - check at multiple layers

1. **API Layer**: Route-level authorization
2. **Service Layer**: Business logic validation
3. **Repository Layer**: Data access filtering
4. **Database Layer**: Row-level security (optional)

### Audit Trail

All team operations are logged:
- Who assigned/unassigned
- When the change occurred
- Reason for change
- Full history preserved

### Data Privacy

**Concern**: Seniors gain access to juniors' data
**Solution**:
- Clearly document in privacy policy
- Audit logs for data access
- Optional: Notify junior when senior views their data

---

## Future Enhancements

### Multi-Level Hierarchies

**Scenario**: VP → Senior Directors → Seniors → Juniors

**Solution**: Recursive CTE query
```sql
WITH RECURSIVE team_hierarchy AS (
    -- Base case: Direct reports
    SELECT senior_user_id, junior_user_id, 1 as level
    FROM team_assignments
    WHERE senior_user_id = :user_id AND is_active = TRUE

    UNION ALL

    -- Recursive case: Reports of reports
    SELECT ta.senior_user_id, ta.junior_user_id, th.level + 1
    FROM team_assignments ta
    JOIN team_hierarchy th ON ta.senior_user_id = th.junior_user_id
    WHERE ta.is_active = TRUE AND th.level < 5  -- Limit depth
)
SELECT DISTINCT junior_user_id FROM team_hierarchy;
```

### Team-Based Candidate Pools

**Scenario**: Candidates shared across team
**Solution**: Add `team_id` to `user_candidate_assignments`

### Analytics Dashboard

**Features**:
- Team performance metrics
- Candidate pipeline by team
- Analysis volume by team
- Success rates comparison

---

## Success Metrics

### Technical Metrics
- Query performance: < 100ms for access checks
- Test coverage: > 85%
- Zero security incidents
- API response time: < 200ms (p95)

### Business Metrics
- Team assignment accuracy: 99%+
- Data access errors: < 0.1%
- Admin time saved: 50%+ (vs manual CSV tracking)
- User satisfaction: 4.5/5+

---

## Rollout Strategy

### Phase 1: Internal Testing (Week 1)
- Deploy to staging environment
- Admin team tests team assignment
- Create test hierarchies

### Phase 2: Pilot (Week 2-3)
- Select 1-2 teams for pilot
- Assign juniors to seniors
- Monitor access control
- Gather feedback

### Phase 3: Gradual Rollout (Week 4-6)
- Roll out to 25% of users
- Monitor performance and errors
- Fix issues
- Roll out to 100%

### Phase 4: Monitoring (Ongoing)
- Track access control errors
- Monitor query performance
- User feedback surveys

---

## Dependencies

### Technical Dependencies
- PostgreSQL 15+ (for partial indexes)
- SQLAlchemy 2.0+ (for async support)
- FastAPI 0.104+ (for dependency injection)
- Alembic (for migrations)

### Feature Dependencies
**Prerequisites**:
- User authentication system ✅
- Role-based authorization ✅
- Candidate management ✅
- Resume upload ✅
- Analysis system ✅

**Blockers**: None (all prerequisites met)

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-06 | Backend Team | Initial design |

**Reviewers**:
- [ ] Product Manager
- [ ] Tech Lead
- [ ] Security Team
- [ ] Engineering Manager

**Approval**:
- [ ] CTO
- [ ] VP Engineering

---

## References

- [Database Schema v1.1](../database/docs/schema_v1.1.md)
- [Access Control Current Implementation](../backend/app/features/candidate/repository.py)
- [User Model Documentation](../database/models/auth.py)
- [Sprint 004 Backlog](../knowledge/backlog/sprint-004-backlog.md)

---

**END OF DOCUMENT**
