"""
Tests for Legacy AI Adapter
============================

Test suite to verify that the legacy adapter correctly wraps the existing AI system
and produces identical behavior while conforming to the new interface.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

from app.ai_agents.legacy_adapter import LegacyAIAdapter
from app.ai_agents.interface import (
    AnalysisRequest, 
    AnalysisResult,
    Industry,
    ExperienceLevel,
    AIServiceError,
    AIServiceUnavailable,
    InvalidResumeContent
)
from app.ai.models.analysis_request import (
    CompleteAnalysisResult,
    StructureAnalysisResult, 
    AppealAnalysisResult
)


class TestLegacyAIAdapter:
    """Test cases for the legacy AI adapter."""
    
    @pytest.fixture
    def sample_request(self) -> AnalysisRequest:
        """Sample analysis request for testing."""
        return AnalysisRequest(
            text="""
            John Doe
            Senior Software Engineer
            
            Professional Summary:
            Experienced software engineer with 5+ years in web development.
            
            Skills:
            • Python, JavaScript, React
            • AWS, Docker, Kubernetes
            • Team leadership and mentoring
            
            Experience:
            Software Engineer at Tech Corp (2019-2024)
            • Led development of microservices architecture
            • Improved system performance by 40%
            • Mentored junior developers
            """.strip(),
            industry=Industry.STRATEGY_TECH,
            role="Senior Software Engineer",
            experience_level=ExperienceLevel.SENIOR
        )
    
    @pytest.fixture
    def mock_legacy_result(self) -> CompleteAnalysisResult:
        """Mock result from legacy orchestrator."""
        structure_result = StructureAnalysisResult(
            format_score=85.0,
            section_organization_score=90.0,
            professional_tone_score=88.0,
            completeness_score=82.0,
            formatting_issues=["Minor spacing inconsistency"],
            missing_sections=[],
            tone_problems=[],
            completeness_gaps=["Could add more quantified achievements"],
            strengths=["Clear professional summary", "Well-organized sections"],
            recommendations=["Add more specific metrics", "Improve formatting consistency"],
            total_sections_found=4,
            word_count=150,
            estimated_reading_time_minutes=1,
            confidence_score=0.85,
            processing_time_ms=2500,
            model_used="gpt-4",
            prompt_version="v1.0"
        )
        
        appeal_result = AppealAnalysisResult(
            achievement_relevance_score=88.0,
            skills_alignment_score=85.0,
            experience_fit_score=90.0,
            competitive_positioning_score=82.0,
            relevant_achievements=["Led microservices architecture", "40% performance improvement"],
            missing_skills=["Machine Learning", "Data Science"],
            transferable_experience=["Team leadership", "Performance optimization"],
            industry_keywords=["microservices", "AWS", "performance"],
            market_tier="senior",
            competitive_advantages=["Strong technical leadership", "Proven results"],
            improvement_areas=["Add ML skills", "More quantified metrics"],
            structure_context_used=True,
            target_industry="tech_consulting",
            confidence_score=0.87,
            processing_time_ms=3000,
            model_used="gpt-4",
            prompt_version="v1.0"
        )
        
        return CompleteAnalysisResult(
            overall_score=86.2,
            structure_analysis=structure_result,
            appeal_analysis=appeal_result,
            analysis_summary="Strong technical professional with proven leadership experience. Resume demonstrates clear progression and quantified achievements.",
            key_strengths=["Technical expertise", "Leadership experience", "Quantified results"],
            priority_improvements=["Add ML skills", "More specific metrics", "Industry certifications"],
            industry="tech_consulting",
            analysis_id="test-123",
            completed_at="2025-01-07T10:00:00Z",
            processing_time_seconds=5.5,
            confidence_metrics={"structure": 0.85, "appeal": 0.87}
        )
    
    @pytest.fixture
    def adapter_with_mock(self, mock_legacy_result):
        """Adapter with mocked orchestrator."""
        with patch('app.ai_agents.legacy_adapter.ResumeAnalysisOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.analyze_resume.return_value = mock_legacy_result
            mock_orchestrator_class.return_value = mock_orchestrator
            
            with patch('app.ai_agents.legacy_adapter.OpenAIClient'):
                adapter = LegacyAIAdapter()
                adapter.mock_orchestrator = mock_orchestrator  # For test access
                return adapter
    
    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        """Test that adapter initializes correctly."""
        with patch('app.ai_agents.legacy_adapter.ResumeAnalysisOrchestrator'):
            with patch('app.ai_agents.legacy_adapter.OpenAIClient'):
                adapter = LegacyAIAdapter()
                assert adapter is not None
                assert adapter.orchestrator is not None
    
    @pytest.mark.asyncio
    async def test_analyze_resume_success(self, adapter_with_mock, sample_request, mock_legacy_result):
        """Test successful resume analysis through adapter."""
        result = await adapter_with_mock.analyze_resume(sample_request)
        
        # Verify result structure
        assert isinstance(result, AnalysisResult)
        assert 0 <= result.overall_score <= 100
        assert len(result.summary) > 0
        assert result.structure_score is not None
        assert result.content_score is not None
        assert result.appeal_score is not None
        
        # Verify score calculations
        assert result.overall_score == 86  # int(86.2)
        assert result.ai_model_used.startswith("gpt-4")
        assert result.processing_time_ms > 0
        
        # Verify orchestrator was called correctly
        adapter_with_mock.mock_orchestrator.analyze_resume.assert_called_once()
        call_args = adapter_with_mock.mock_orchestrator.analyze_resume.call_args
        assert call_args[1]['resume_text'] == sample_request.text
        assert call_args[1]['industry'] == 'tech_consulting'  # Mapped industry
    
    @pytest.mark.asyncio
    async def test_industry_mapping(self, adapter_with_mock, mock_legacy_result):
        """Test industry mapping from new enum to legacy strings."""
        test_cases = [
            (Industry.STRATEGY_TECH, "tech_consulting"),
            (Industry.MA_FINANCIAL, "finance_banking"),
            (Industry.CONSULTING, "general_business"),
            (Industry.SYSTEM_INTEGRATOR, "system_integrator"),
            (Industry.GENERAL, "general_business")
        ]
        
        for new_industry, expected_legacy in test_cases:
            request = AnalysisRequest(
                text="Sample resume text here for testing",
                industry=new_industry
            )
            
            await adapter_with_mock.analyze_resume(request)
            
            # Check that the correct legacy industry was used
            call_args = adapter_with_mock.mock_orchestrator.analyze_resume.call_args
            assert call_args[1]['industry'] == expected_legacy
    
    @pytest.mark.asyncio
    async def test_data_transformation_accuracy(self, adapter_with_mock, sample_request, mock_legacy_result):
        """Test that data transformation preserves key information accurately."""
        result = await adapter_with_mock.analyze_resume(sample_request)
        
        # Verify structure score calculation
        expected_structure_score = int((85.0 + 90.0 + 88.0 + 82.0) / 4)  # 86
        assert result.structure_score.score == expected_structure_score
        
        # Verify appeal score calculation
        expected_appeal_score = int((88.0 + 85.0 + 90.0 + 82.0) / 4)  # 86
        assert result.appeal_score.score == expected_appeal_score
        
        # Verify strengths and recommendations are preserved
        assert len(result.strengths) > 0
        assert len(result.recommendations) > 0
        assert "Add ML skills" in result.recommendations  # From priority_improvements
    
    @pytest.mark.asyncio
    async def test_get_structure_analysis(self, adapter_with_mock, sample_request):
        """Test structure-only analysis method."""
        structure_score = await adapter_with_mock.get_structure_analysis(sample_request)
        
        assert structure_score.score == 86  # Expected from mock calculation
        assert len(structure_score.feedback) > 0
        assert "Structure Analysis" in structure_score.feedback
        assert len(structure_score.suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_get_appeal_analysis(self, adapter_with_mock, sample_request):
        """Test appeal-only analysis method."""
        appeal_score = await adapter_with_mock.get_appeal_analysis(sample_request)
        
        assert appeal_score.score == 86  # Expected from mock calculation
        assert len(appeal_score.feedback) > 0
        assert "Appeal Analysis" in appeal_score.feedback
        assert len(appeal_score.suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_input_validation(self, adapter_with_mock):
        """Test input validation catches invalid requests."""
        # Test empty text
        with pytest.raises(InvalidResumeContent):
            await adapter_with_mock.analyze_resume(AnalysisRequest(
                text="",
                industry=Industry.GENERAL
            ))
        
        # Test very short text
        with pytest.raises(InvalidResumeContent):
            await adapter_with_mock.analyze_resume(AnalysisRequest(
                text="Hi",
                industry=Industry.GENERAL
            ))
        
        # Test very long text
        long_text = "A" * 60000  # Over 50k limit
        with pytest.raises(InvalidResumeContent):
            await adapter_with_mock.analyze_resume(AnalysisRequest(
                text=long_text,
                industry=Industry.GENERAL
            ))
    
    @pytest.mark.asyncio
    async def test_error_handling(self, adapter_with_mock, sample_request):
        """Test error handling and exception mapping."""
        # Test timeout error
        adapter_with_mock.mock_orchestrator.analyze_resume.side_effect = Exception("timeout occurred")
        
        with pytest.raises(AIServiceError) as exc_info:
            await adapter_with_mock.analyze_resume(sample_request)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, adapter_with_mock):
        """Test health check with successful response."""
        # Health check should pass with mock returning valid data
        health_ok = await adapter_with_mock.health_check()
        assert health_ok is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, adapter_with_mock):
        """Test health check with failure."""
        adapter_with_mock.mock_orchestrator.analyze_resume.side_effect = Exception("Service unavailable")
        
        health_ok = await adapter_with_mock.health_check()
        assert health_ok is False
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self, adapter_with_mock, sample_request):
        """Test that performance metrics are tracked correctly."""
        start_time = time.time()
        result = await adapter_with_mock.analyze_resume(sample_request)
        end_time = time.time()
        
        # Verify processing time is reasonable and tracked
        assert result.processing_time_ms > 0
        actual_time_ms = (end_time - start_time) * 1000
        
        # Should be approximately equal (allowing for some overhead)
        assert abs(result.processing_time_ms - actual_time_ms) < 100  # Within 100ms
    
    @pytest.mark.asyncio
    async def test_confidence_score_calculation(self, adapter_with_mock, sample_request, mock_legacy_result):
        """Test confidence score calculation from legacy results."""
        result = await adapter_with_mock.analyze_resume(sample_request)
        
        # Should be average of structure and appeal confidence
        expected_confidence = (0.85 + 0.87) / 2  # 0.86
        assert abs(result.confidence_score - expected_confidence) < 0.01
    
    def test_industry_mapping_helper(self):
        """Test the industry mapping helper method."""
        with patch('app.ai_agents.legacy_adapter.ResumeAnalysisOrchestrator'):
            with patch('app.ai_agents.legacy_adapter.OpenAIClient'):
                adapter = LegacyAIAdapter()
                
                # Test all mappings
                assert adapter._map_industry_to_legacy(Industry.STRATEGY_TECH) == "tech_consulting"
                assert adapter._map_industry_to_legacy(Industry.MA_FINANCIAL) == "finance_banking"
                assert adapter._map_industry_to_legacy(Industry.CONSULTING) == "general_business"
                assert adapter._map_industry_to_legacy(Industry.SYSTEM_INTEGRATOR) == "system_integrator"
                assert adapter._map_industry_to_legacy(Industry.GENERAL) == "general_business"
    
    def test_experience_level_mapping(self):
        """Test experience level mapping helper."""
        with patch('app.ai_agents.legacy_adapter.ResumeAnalysisOrchestrator'):
            with patch('app.ai_agents.legacy_adapter.OpenAIClient'):
                adapter = LegacyAIAdapter()
                
                # Test all mappings
                assert adapter._map_experience_level(ExperienceLevel.ENTRY) == "entry"
                assert adapter._map_experience_level(ExperienceLevel.MID) == "mid"
                assert adapter._map_experience_level(ExperienceLevel.SENIOR) == "senior"
                assert adapter._map_experience_level(ExperienceLevel.EXECUTIVE) == "executive"
                assert adapter._map_experience_level(None) == "mid"  # Default


@pytest.mark.integration
class TestLegacyAdapterIntegration:
    """Integration tests for legacy adapter with real components."""
    
    @pytest.mark.asyncio
    async def test_real_integration(self):
        """Test adapter with real AI components (requires environment setup)."""
        # This test requires actual AI service setup
        # Skip if not in integration test environment
        pytest.skip("Integration test requires AI service setup")
        
        # When enabled, this would test:
        # adapter = LegacyAIAdapter()
        # request = AnalysisRequest(text="...", industry=Industry.GENERAL)
        # result = await adapter.analyze_resume(request)
        # assert result.overall_score > 0