"""Unit tests for resume analysis models."""

import pytest
from datetime import datetime
from app.features.resume_analysis.models import (
    Industry,
    AnalysisStatus,
    MarketTier,
    AnalysisRequest,
    ScoreDetails,
    AnalysisResult,
    CompleteAnalysisResult
)


class TestModels:
    """Test resume analysis models."""
    
    def test_analysis_request_validation(self):
        """Test analysis request validation."""
        # Valid request
        request = AnalysisRequest(
            text="John Doe is a software engineer with 5 years of experience in Python and React.",
            industry=Industry.STRATEGY_TECH
        )
        
        assert request.text is not None
        assert request.industry == Industry.STRATEGY_TECH
    
    def test_score_details(self):
        """Test score details model."""
        scores = ScoreDetails(
            overall=85.5,
            formatting=80.0,
            content=90.0
        )
        
        assert scores.overall == 85.5
        assert scores.formatting == 80.0
        assert scores.content == 90.0
    
    def test_analysis_result(self):
        """Test analysis result model."""
        result = AnalysisResult(
            analysis_id="test-123",
            overall_score=85.5,
            market_tier=MarketTier.TIER_1,
            industry=Industry.STRATEGY_TECH,
            created_at=datetime.now()
        )
        
        assert result.analysis_id == "test-123"
        assert result.overall_score == 85.5
        assert result.market_tier == MarketTier.TIER_1
        assert result.industry == Industry.STRATEGY_TECH
    
    def test_legacy_compatibility(self):
        """Test legacy format compatibility."""
        modern_result = AnalysisResult(
            analysis_id="test-123",
            overall_score=85.5,
            market_tier=MarketTier.TIER_1,
            industry=Industry.STRATEGY_TECH,
            analysis_summary="Great resume!",
            created_at=datetime.now()
        )
        
        legacy_result = CompleteAnalysisResult.from_analysis_result(modern_result)
        
        assert legacy_result.analysis_id == "test-123"
        assert legacy_result.overall_score == 85.5
        assert legacy_result.market_tier == "tier_1"
        assert legacy_result.summary == "Great resume!"