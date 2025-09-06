"""
Unit Tests for Resume Analysis Orchestrator
===========================================

Tests for the LangGraph orchestrator including workflow execution,
error handling, state management, and result aggregation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.ai.orchestrator import ResumeAnalysisOrchestrator
from app.ai.models.analysis_request import AnalysisState, StructureAnalysisResult, AppealAnalysisResult
from app.ai.integrations.base_llm import MockLLM


@pytest.fixture
def mock_llm():
    """Create a mock LLM with predefined responses."""
    mock_responses = {
        "structure": """
        Format Score: 85
        Section Organization Score: 78
        Professional Tone Score: 82
        Completeness Score: 76
        
        Strengths:
        - Clear section headers and organization
        - Professional language throughout
        - Comprehensive work experience
        
        Recommendations:
        - Add quantifiable achievements
        - Include technical skills section
        - Improve formatting consistency
        """,
        "appeal": """
        Achievement Relevance Score: 79
        Skills Alignment Score: 84
        Experience Fit Score: 87
        Competitive Positioning Score: 81
        
        Relevant Achievements:
        - Led team of 8 developers on React project
        - Improved system performance by 40%
        - Architected microservices handling 1M+ requests
        
        Missing Skills:
        - AWS cloud services
        - Docker containerization
        - Kubernetes orchestration
        
        Market Tier Assessment: Senior
        """
    }
    return MockLLM(mock_responses=mock_responses)


@pytest.fixture
def orchestrator(mock_llm):
    """Create orchestrator with mock LLM."""
    return ResumeAnalysisOrchestrator(mock_llm)


@pytest.fixture
def sample_state():
    """Create sample analysis state for testing."""
    return AnalysisState(
        resume_text="""
        John Smith
        Senior Software Engineer
        john.smith@email.com | (555) 123-4567
        
        SUMMARY
        Experienced software engineer with 5+ years in full-stack development.
        
        EXPERIENCE
        Senior Software Engineer | TechCorp Inc. | 2020-Present
        - Led team of 8 developers on React/Node.js applications
        - Improved system performance by 40% through optimization
        - Architected microservices handling 1M+ daily requests
        
        Software Engineer | StartupXYZ | 2018-2020
        - Developed REST APIs using Python/Django
        - Collaborated with cross-functional teams
        
        EDUCATION
        B.S. Computer Science | University of Technology | 2018
        
        SKILLS
        Languages: Python, JavaScript, TypeScript, SQL
        Frameworks: React, Node.js, Django, FastAPI
        Tools: Docker, AWS, Git, PostgreSQL
        """,
        industry="tech_consulting",
        analysis_id="test-123",
        user_id="user-456",
        current_stage="preprocessing",
        has_errors=False,
        error_messages=[],
        retry_count=0,
        structure_errors=[],
        appeal_errors=[],
        structure_analysis=None,
        structure_confidence=None,
        appeal_analysis=None,
        appeal_confidence=None,
        final_result=None,
        overall_score=None,
        max_retries=2,
        started_at=None,
        completed_at=None,
        processing_time_seconds=None
    )


class TestResumeAnalysisOrchestrator:
    """Test the main orchestrator functionality."""
    
    def test_orchestrator_initialization(self, mock_llm):
        """Test orchestrator initializes correctly."""
        orchestrator = ResumeAnalysisOrchestrator(mock_llm)
        
        assert orchestrator.llm_client == mock_llm
        assert orchestrator.structure_agent is not None
        assert orchestrator.appeal_agent is not None
        assert orchestrator.workflow is not None
        assert orchestrator.app is not None
        
        # Check configuration
        assert "supported_industries" in orchestrator.config
        assert len(orchestrator.config["supported_industries"]) == 6
        assert orchestrator.config["max_retries"] == 2
    
    def test_preprocess_resume_success(self, orchestrator, sample_state):
        """Test successful resume preprocessing."""
        result = orchestrator.preprocess_resume(sample_state)
        
        assert result["has_errors"] is False
        assert result["current_stage"] == "preprocessing"
        assert "started_at" in result
        assert result["max_retries"] == 2
        assert result["retry_count"] == 0
        assert isinstance(result["structure_errors"], list)
        assert isinstance(result["appeal_errors"], list)
    
    def test_preprocess_resume_empty_text(self, orchestrator):
        """Test preprocessing with empty resume text."""
        empty_state = AnalysisState(
            resume_text="",
            industry="tech_consulting",
            analysis_id="test-empty",
            user_id="user-456",
            current_stage="preprocessing",
            has_errors=False,
            error_messages=[],
            retry_count=0,
            structure_errors=[],
            appeal_errors=[],
            structure_analysis=None,
            structure_confidence=None,
            appeal_analysis=None,
            appeal_confidence=None,
            final_result=None,
            overall_score=None,
            max_retries=2,
            started_at=None,
            completed_at=None,
            processing_time_seconds=None
        )
        
        result = orchestrator.preprocess_resume(empty_state)
        
        assert result["has_errors"] is True
        assert "empty" in result["error_messages"][0].lower()
        assert result["current_stage"] == "preprocessing"
    
    def test_preprocess_resume_short_text(self, orchestrator):
        """Test preprocessing with too short resume text."""
        short_state = AnalysisState(
            resume_text="Too short",
            industry="tech_consulting",
            analysis_id="test-short",
            user_id="user-456",
            current_stage="preprocessing",
            has_errors=False,
            error_messages=[],
            retry_count=0,
            structure_errors=[],
            appeal_errors=[],
            structure_analysis=None,
            structure_confidence=None,
            appeal_analysis=None,
            appeal_confidence=None,
            final_result=None,
            overall_score=None,
            max_retries=2,
            started_at=None,
            completed_at=None,
            processing_time_seconds=None
        )
        
        result = orchestrator.preprocess_resume(short_state)
        
        assert result["has_errors"] is True
        assert "too short" in result["error_messages"][0].lower()
    
    def test_preprocess_invalid_industry(self, orchestrator, sample_state):
        """Test preprocessing with invalid industry."""
        sample_state["industry"] = "invalid_industry"
        
        result = orchestrator.preprocess_resume(sample_state)
        
        assert result["has_errors"] is True
        assert "unsupported industry" in result["error_messages"][0].lower()
    
    @pytest.mark.asyncio
    async def test_run_structure_agent_success(self, orchestrator, sample_state):
        """Test successful structure agent execution."""
        # Mock the structure agent
        mock_result = {
            "structure_analysis": "mock_result",
            "structure_confidence": 0.85,
            "current_stage": "structure_analysis",
            "structure_errors": []
        }
        
        orchestrator.structure_agent.analyze = AsyncMock(return_value=mock_result)
        
        result = await orchestrator.run_structure_agent(sample_state)
        
        assert result["structure_confidence"] == 0.85
        assert result["current_stage"] == "structure_analysis"
        assert len(result["structure_errors"]) == 0
        orchestrator.structure_agent.analyze.assert_called_once_with(sample_state)
    
    @pytest.mark.asyncio
    async def test_run_structure_agent_failure(self, orchestrator, sample_state):
        """Test structure agent failure handling."""
        # Mock agent to raise exception
        orchestrator.structure_agent.analyze = AsyncMock(side_effect=Exception("Agent failed"))
        
        result = await orchestrator.run_structure_agent(sample_state)
        
        assert result["has_errors"] is True
        assert "structure analysis failed" in result["structure_errors"][0].lower()
        assert result["current_stage"] == "structure_analysis"
    
    def test_validate_structure_results_success(self, orchestrator, sample_state):
        """Test successful structure validation."""
        # Create mock structure analysis result
        mock_structure = MagicMock()
        mock_structure.format_score = 85
        mock_structure.section_organization_score = 80
        mock_structure.professional_tone_score = 90
        mock_structure.completeness_score = 75
        
        sample_state["structure_analysis"] = mock_structure
        sample_state["structure_confidence"] = 0.85
        
        # Mock the validation method
        orchestrator.structure_agent.validate_structure_result = MagicMock(return_value=True)
        
        result = orchestrator.validate_structure_results(sample_state)
        
        assert result["current_stage"] == "structure_validated"
        assert len(result["structure_errors"]) == 0
        assert result["retry_count"] == 0
    
    def test_validate_structure_low_confidence_retry(self, orchestrator, sample_state):
        """Test structure validation with low confidence triggering retry."""
        mock_structure = MagicMock()
        sample_state["structure_analysis"] = mock_structure
        sample_state["structure_confidence"] = 0.3  # Below threshold
        sample_state["retry_count"] = 0
        sample_state["max_retries"] = 2
        
        orchestrator.structure_agent.validate_structure_result = MagicMock(return_value=True)
        
        result = orchestrator.validate_structure_results(sample_state)
        
        assert "low confidence" in result["structure_errors"][0].lower()
        assert result["retry_count"] == 1
        assert result["current_stage"] == "structure_validation"
    
    def test_validate_structure_max_retries_exceeded(self, orchestrator, sample_state):
        """Test structure validation failing after max retries."""
        mock_structure = MagicMock()
        sample_state["structure_analysis"] = mock_structure
        sample_state["structure_confidence"] = 0.3
        sample_state["retry_count"] = 2  # At max retries
        sample_state["max_retries"] = 2
        
        orchestrator.structure_agent.validate_structure_result = MagicMock(return_value=True)
        
        result = orchestrator.validate_structure_results(sample_state)
        
        assert result["has_errors"] is True
        assert "too low after" in result["error_messages"][0].lower()
        assert result["current_stage"] == "structure_validation"
    
    def test_routing_logic(self, orchestrator, sample_state):
        """Test conditional routing logic."""
        # Test successful routing
        route = orchestrator.route_after_preprocess(sample_state)
        assert route == "continue"
        
        # Test error routing
        error_state = sample_state.copy()
        error_state["has_errors"] = True
        route = orchestrator.route_after_preprocess(error_state)
        assert route == "error"
        
        # Test retry routing
        retry_state = sample_state.copy()
        retry_state["structure_errors"] = ["Some error"]
        retry_state["retry_count"] = 0
        retry_state["max_retries"] = 2
        route = orchestrator.route_after_structure(retry_state)
        assert route == "retry"
        
        # Test max retries routing
        max_retry_state = sample_state.copy()
        max_retry_state["structure_errors"] = ["Some error"]
        max_retry_state["retry_count"] = 2
        max_retry_state["max_retries"] = 2
        route = orchestrator.route_after_structure(max_retry_state)
        assert route == "error"
    
    def test_aggregate_final_results(self, orchestrator, sample_state):
        """Test final results aggregation."""
        # Create mock analysis results
        mock_structure = MagicMock()
        mock_structure.format_score = 85
        mock_structure.section_organization_score = 80
        mock_structure.professional_tone_score = 90
        mock_structure.completeness_score = 75
        mock_structure.strengths = ["Good formatting", "Clear sections"]
        mock_structure.recommendations = ["Add metrics", "Include skills"]
        mock_structure.confidence_score = 0.85
        
        mock_appeal = MagicMock()
        mock_appeal.achievement_relevance_score = 82
        mock_appeal.skills_alignment_score = 88
        mock_appeal.experience_fit_score = 85
        mock_appeal.competitive_positioning_score = 80
        mock_appeal.competitive_advantages = ["Strong leadership", "Technical expertise"]
        mock_appeal.improvement_areas = ["Add certifications", "Include portfolio"]
        mock_appeal.target_industry = "tech_consulting"
        mock_appeal.confidence_score = 0.78
        
        sample_state["structure_analysis"] = mock_structure
        sample_state["appeal_analysis"] = mock_appeal
        sample_state["started_at"] = "2023-01-01T00:00:00"
        
        with patch('app.ai.orchestrator.utc_now') as mock_utc_now:
            mock_utc_now.return_value = MagicMock()
            mock_utc_now.return_value.isoformat.return_value = "2023-01-01T00:05:00"
            
            result = orchestrator.aggregate_final_results(sample_state)
        
        assert result["current_stage"] == "complete"
        assert "final_result" in result
        assert "overall_score" in result
        assert result["overall_score"] > 0
        assert "completed_at" in result
        
        final_result = result["final_result"]
        assert final_result.industry == "tech_consulting"
        assert final_result.analysis_id == "test-123"
        assert len(final_result.key_strengths) > 0
        assert len(final_result.priority_improvements) > 0
        assert final_result.confidence_metrics is not None
    
    def test_handle_analysis_error(self, orchestrator, sample_state):
        """Test error handling."""
        sample_state["has_errors"] = True
        sample_state["error_messages"] = ["Something went wrong"]
        sample_state["current_stage"] = "structure_analysis"
        
        result = orchestrator.handle_analysis_error(sample_state)
        
        assert result["has_errors"] is True
        assert result["current_stage"] == "error"
        assert result["error_messages"] == ["Something went wrong"]
        assert "completed_at" in result
    
    @pytest.mark.asyncio
    async def test_analyze_resume_end_to_end(self, orchestrator):
        """Test complete end-to-end analysis."""
        resume_text = """
        John Smith
        Software Engineer
        
        EXPERIENCE
        Software Engineer at TechCorp (2020-2023)
        - Developed web applications using React and Node.js
        - Led team of 5 developers
        
        EDUCATION
        BS Computer Science, Tech University (2020)
        
        SKILLS
        JavaScript, Python, React, Node.js
        """
        
        # Mock the app.ainvoke method to simulate successful workflow
        mock_final_result = MagicMock()
        mock_final_result.overall_score = 82.5
        mock_final_result.analysis_id = "test-end-to-end"
        
        mock_workflow_result = {
            "has_errors": False,
            "final_result": mock_final_result,
            "current_stage": "complete"
        }
        
        orchestrator.app.ainvoke = AsyncMock(return_value=mock_workflow_result)
        
        result = await orchestrator.analyze_resume(
            resume_text=resume_text,
            industry="tech_consulting",
            analysis_id="test-end-to-end",
            user_id="test-user"
        )
        
        assert result == mock_final_result
        assert result.overall_score == 82.5
        orchestrator.app.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_resume_failure(self, orchestrator):
        """Test end-to-end analysis failure handling."""
        resume_text = "Valid resume text for testing failure scenarios"
        
        # Mock workflow to return error
        mock_workflow_result = {
            "has_errors": True,
            "error_messages": ["Workflow failed"],
            "current_stage": "error",
            "final_result": None
        }
        
        orchestrator.app.ainvoke = AsyncMock(return_value=mock_workflow_result)
        
        with pytest.raises(Exception) as exc_info:
            await orchestrator.analyze_resume(
                resume_text=resume_text,
                industry="tech_consulting",
                analysis_id="test-failure",
                user_id="test-user"
            )
        
        assert "Analysis failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_setup(self, orchestrator):
        """Test setup validation."""
        # Mock successful validation
        orchestrator.llm_client.validate_connection = AsyncMock(return_value=True)
        
        result = await orchestrator.validate_setup()
        assert result is True
        
        # Mock failed LLM validation
        orchestrator.llm_client.validate_connection = AsyncMock(return_value=False)
        
        result = await orchestrator.validate_setup()
        assert result is False
    
    def test_get_workflow_info(self, orchestrator):
        """Test workflow info retrieval."""
        info = orchestrator.get_workflow_info()
        
        assert "workflow_nodes" in info
        assert "supported_industries" in info
        assert "confidence_thresholds" in info
        assert "max_retries" in info
        assert "agents" in info
        assert "llm_info" in info
        
        assert len(info["workflow_nodes"]) == 7  # All workflow nodes
        assert len(info["supported_industries"]) == 6
        assert info["max_retries"] == 2
    
    def test_clean_resume_text(self, orchestrator):
        """Test resume text cleaning."""
        dirty_text = "Resume\r\n\r\nwith\x00bad\r\ncharacters   and   spaces"
        cleaned = orchestrator._clean_resume_text(dirty_text)
        
        assert "\x00" not in cleaned
        assert "\r" not in cleaned
        assert "   " not in cleaned  # Excessive spaces removed
        assert cleaned.startswith("Resume")
        assert cleaned.endswith("characters and spaces")
    
    def test_text_processing_methods(self, orchestrator):
        """Test helper text processing methods."""
        # Test generate executive summary
        mock_structure = MagicMock()
        mock_structure.strengths = ["Good formatting", "Clear organization"]
        
        mock_appeal = MagicMock()
        mock_appeal.target_industry = "tech_consulting"
        mock_appeal.market_tier = "senior"
        mock_appeal.relevant_achievements = ["Led team", "Improved performance"]
        
        summary = orchestrator._generate_executive_summary(mock_structure, mock_appeal, 85.0)
        assert "excellent quality" in summary.lower()
        assert "85.0/100" in summary
        assert "tech consulting" in summary.lower()
        
        # Test extract key strengths
        strengths = orchestrator._extract_key_strengths(mock_structure, mock_appeal)
        assert len(strengths) >= 2
        assert "Good formatting" in strengths
        
        # Test extract priority improvements
        mock_structure.recommendations = ["Add metrics", "Include portfolio"]
        mock_appeal.improvement_areas = ["Get certification", "Build projects"]
        
        improvements = orchestrator._extract_priority_improvements(mock_structure, mock_appeal)
        assert len(improvements) >= 2
        assert "Add metrics" in improvements