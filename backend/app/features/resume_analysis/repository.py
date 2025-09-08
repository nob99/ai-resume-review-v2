"""Resume analysis repository for database operations."""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, func

from app.infrastructure.persistence.postgres.base import BaseRepository
from app.core.datetime_utils import utc_now
from .models import ResumeAnalysis, AnalysisStatus, Industry, MarketTier


class AnalysisRepository(BaseRepository[ResumeAnalysis]):
    """Repository for resume analysis database operations."""
    
    def __init__(self, db: Session):
        """Initialize repository with database session."""
        super().__init__(ResumeAnalysis, db)
    
    async def create_analysis(
        self,
        user_id: uuid.UUID,
        industry: Industry,
        file_upload_id: Optional[uuid.UUID] = None
    ) -> ResumeAnalysis:
        """Create a new analysis record."""
        analysis = ResumeAnalysis(
            user_id=user_id,
            industry=industry.value,
            file_upload_id=file_upload_id,
            status=AnalysisStatus.PENDING,
            analysis_started_at=utc_now()
        )
        
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        
        return analysis
    
    async def update_status(
        self,
        analysis_id: uuid.UUID,
        status: AnalysisStatus,
        error_message: Optional[str] = None
    ) -> Optional[ResumeAnalysis]:
        """Update analysis status."""
        analysis = self.get(analysis_id)
        if not analysis:
            return None
        
        analysis.status = status
        analysis.updated_at = utc_now()
        
        if error_message:
            analysis.error_message = error_message
        
        if status == AnalysisStatus.COMPLETED:
            analysis.analysis_completed_at = utc_now()
            if analysis.analysis_started_at:
                delta = analysis.analysis_completed_at - analysis.analysis_started_at
                analysis.processing_time_seconds = delta.total_seconds()
        
        self.db.commit()
        self.db.refresh(analysis)
        
        return analysis
    
    async def save_results(
        self,
        analysis_id: uuid.UUID,
        overall_score: float,
        market_tier: MarketTier,
        structure_scores: Optional[Dict[str, Any]] = None,
        appeal_scores: Optional[Dict[str, Any]] = None,
        confidence_metrics: Optional[Dict[str, Any]] = None,
        structure_feedback: Optional[str] = None,
        appeal_feedback: Optional[str] = None,
        analysis_summary: Optional[str] = None,
        improvement_suggestions: Optional[str] = None,
        ai_model_version: Optional[str] = None,
        ai_tokens_used: Optional[int] = None
    ) -> Optional[ResumeAnalysis]:
        """Save analysis results."""
        analysis = self.get(analysis_id)
        if not analysis:
            return None
        
        analysis.overall_score = overall_score
        analysis.market_tier = market_tier.value
        analysis.structure_scores = structure_scores
        analysis.appeal_scores = appeal_scores
        analysis.confidence_metrics = confidence_metrics
        analysis.structure_feedback = structure_feedback
        analysis.appeal_feedback = appeal_feedback
        analysis.analysis_summary = analysis_summary
        analysis.improvement_suggestions = improvement_suggestions
        analysis.ai_model_version = ai_model_version
        analysis.ai_tokens_used = ai_tokens_used
        analysis.updated_at = utc_now()
        
        self.db.commit()
        self.db.refresh(analysis)
        
        return analysis
    
    async def get_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[AnalysisStatus] = None,
        industry: Optional[Industry] = None,
        limit: int = 10,
        offset: int = 0,
        include_file_info: bool = False
    ) -> List[ResumeAnalysis]:
        """Get analyses by user with optional filtering."""
        query = self.db.query(ResumeAnalysis).filter(ResumeAnalysis.user_id == user_id)
        
        if status:
            query = query.filter(ResumeAnalysis.status == status)
        
        if industry:
            query = query.filter(ResumeAnalysis.industry == industry.value)
        
        if include_file_info:
            query = query.options(joinedload(ResumeAnalysis.file_upload))
        
        return query.order_by(desc(ResumeAnalysis.created_at)).limit(limit).offset(offset).all()
    
    async def get_recent_analyses(
        self,
        user_id: uuid.UUID,
        hours: int = 24,
        limit: int = 10
    ) -> List[ResumeAnalysis]:
        """Get recent analyses within specified hours."""
        cutoff_time = utc_now() - timedelta(hours=hours)
        
        return self.db.query(ResumeAnalysis).filter(
            and_(
                ResumeAnalysis.user_id == user_id,
                ResumeAnalysis.created_at >= cutoff_time
            )
        ).order_by(desc(ResumeAnalysis.created_at)).limit(limit).all()
    
    async def get_analysis_with_file(
        self,
        analysis_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[ResumeAnalysis]:
        """Get analysis with file upload information."""
        return self.db.query(ResumeAnalysis).options(
            joinedload(ResumeAnalysis.file_upload)
        ).filter(
            and_(
                ResumeAnalysis.id == analysis_id,
                ResumeAnalysis.user_id == user_id
            )
        ).first()
    
    async def get_user_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get analysis statistics for a user."""
        analyses = self.db.query(ResumeAnalysis).filter(ResumeAnalysis.user_id == user_id).all()
        
        total_count = len(analyses)
        completed_count = sum(1 for a in analyses if a.status == AnalysisStatus.COMPLETED)
        failed_count = sum(1 for a in analyses if a.status == AnalysisStatus.ERROR)
        
        # Calculate average score for completed analyses
        completed_analyses = [a for a in analyses if a.status == AnalysisStatus.COMPLETED and a.overall_score is not None]
        average_score = sum(a.overall_score for a in completed_analyses) / len(completed_analyses) if completed_analyses else None
        
        # Industry breakdown
        industry_breakdown = {}
        for analysis in analyses:
            industry = analysis.industry
            industry_breakdown[industry] = industry_breakdown.get(industry, 0) + 1
        
        # Tier breakdown
        tier_breakdown = {}
        for analysis in completed_analyses:
            if analysis.market_tier:
                tier = analysis.market_tier
                tier_breakdown[tier] = tier_breakdown.get(tier, 0) + 1
        
        return {
            "total_analyses": total_count,
            "completed_analyses": completed_count,
            "failed_analyses": failed_count,
            "average_score": round(average_score, 2) if average_score else None,
            "industry_breakdown": industry_breakdown,
            "tier_breakdown": tier_breakdown
        }
    
    async def increment_retry_count(self, analysis_id: uuid.UUID) -> Optional[ResumeAnalysis]:
        """Increment retry count for failed analysis."""
        analysis = self.get(analysis_id)
        if not analysis:
            return None
        
        analysis.retry_count = (analysis.retry_count or 0) + 1
        analysis.updated_at = utc_now()
        
        self.db.commit()
        self.db.refresh(analysis)
        
        return analysis
    
    async def mark_cancelled(self, analysis_id: uuid.UUID) -> Optional[ResumeAnalysis]:
        """Mark an analysis as cancelled."""
        return await self.update_status(analysis_id, AnalysisStatus.CANCELLED)
    
    async def get_pending_analyses(self, user_id: uuid.UUID) -> List[ResumeAnalysis]:
        """Get all pending analyses for a user."""
        return self.db.query(ResumeAnalysis).filter(
            and_(
                ResumeAnalysis.user_id == user_id,
                ResumeAnalysis.status.in_([
                    AnalysisStatus.PENDING,
                    AnalysisStatus.PROCESSING
                ])
            )
        ).all()
    
    async def delete_old_analyses(
        self,
        days: int = 90,
        status: Optional[AnalysisStatus] = None
    ) -> int:
        """Delete old analyses older than specified days."""
        cutoff_time = utc_now() - timedelta(days=days)
        
        query = self.db.query(ResumeAnalysis).filter(ResumeAnalysis.created_at < cutoff_time)
        
        if status:
            query = query.filter(ResumeAnalysis.status == status)
        
        count = query.count()
        query.delete()
        self.db.commit()
        
        return count
    
    async def get_analyses_by_score_range(
        self,
        user_id: uuid.UUID,
        min_score: float = 0,
        max_score: float = 100
    ) -> List[ResumeAnalysis]:
        """Get analyses within a score range."""
        return self.db.query(ResumeAnalysis).filter(
            and_(
                ResumeAnalysis.user_id == user_id,
                ResumeAnalysis.overall_score >= min_score,
                ResumeAnalysis.overall_score <= max_score,
                ResumeAnalysis.status == AnalysisStatus.COMPLETED
            )
        ).order_by(desc(ResumeAnalysis.overall_score)).all()
    
    async def get_top_analyses(
        self,
        user_id: uuid.UUID,
        limit: int = 5
    ) -> List[ResumeAnalysis]:
        """Get top analyses by score for a user."""
        return self.db.query(ResumeAnalysis).filter(
            and_(
                ResumeAnalysis.user_id == user_id,
                ResumeAnalysis.status == AnalysisStatus.COMPLETED,
                ResumeAnalysis.overall_score.isnot(None)
            )
        ).order_by(desc(ResumeAnalysis.overall_score)).limit(limit).all()