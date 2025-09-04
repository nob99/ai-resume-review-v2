"""
Unit Tests for Structure Agent
==============================

Tests for the Structure Agent including analysis functionality,
output parsing, validation, and error handling.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from app.ai.agents.structure_agent import StructureAgent
from app.ai.models.analysis_request import AnalysisState, StructureAnalysisResult
from app.ai.integrations.base_llm import MockLLM, LLMResponse


@pytest.fixture
def mock_llm():
    """Create a mock LLM with structure-specific responses."""
    mock_responses = {
        "structure": """
        Format Score: 85
        Section Organization Score: 78
        Professional Tone Score: 82
        Completeness Score: 76
        
        Formatting Issues:
        - Inconsistent bullet point formatting
        - Uneven spacing between sections
        
        Missing Sections:
        - Professional summary missing
        - No contact information section
        
        Tone Problems:
        - Some informal language in experience section
        
        Completeness Gaps:
        - Missing quantifiable achievements
        - No specific dates for some positions
        
        Strengths:
        - Clear section headers and organization
        - Professional language throughout most sections
        - Comprehensive work experience listing
        
        Recommendations:
        - Add quantifiable achievements with specific metrics
        - Include a professional summary at the top
        - Standardize formatting across all sections
        - Add complete contact information
        """
    }
    return MockLLM(mock_responses=mock_responses)


@pytest.fixture
def structure_agent(mock_llm):
    """Create structure agent with mock LLM."""
    return StructureAgent(mock_llm)


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
        
        EDUCATION
        B.S. Computer Science | University of Technology | 2018
        
        SKILLS
        Languages: Python, JavaScript, TypeScript, SQL
        Frameworks: React, Node.js, Django, FastAPI
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


class TestStructureAgent:
    """Test the Structure Agent functionality."""
    
    def test_agent_initialization(self, mock_llm):
        """Test agent initializes correctly."""
        agent = StructureAgent(mock_llm)
        
        assert agent.llm == mock_llm
        assert agent.agent_name == "StructureAgent"
        assert len(agent.score_patterns) == 4
        assert len(agent.expected_sections) > 0
        assert len(agent.feedback_keywords) == 6
    
    def test_identify_resume_sections(self, structure_agent):
        """Test resume section identification."""
        resume_text = """
        SUMMARY
        Professional software engineer
        
        EXPERIENCE
        Senior Developer at TechCorp
        
        EDUCATION
        BS Computer Science
        
        SKILLS
        Python, JavaScript
        
        PROJECTS
        Built web application
        """
        
        sections = structure_agent._identify_resume_sections(resume_text)
        
        assert "Summary" in sections
        assert "Experience" in sections
        assert "Education" in sections
        assert "Skills" in sections
        assert "Projects" in sections
    
    def test_extract_scores_from_output(self, structure_agent):
        """Test score extraction from LLM output."""
        output = """
        The resume analysis shows:
        Format Score: 85
        Section Organization Score: 78
        Professional Tone Score: 82
        Completeness Score: 76
        """
        
        scores = structure_agent._extract_scores_from_output(output, structure_agent.score_patterns)
        
        assert scores["format_score"] == 85.0
        assert scores["section_organization_score"] == 78.0
        assert scores["professional_tone_score"] == 82.0
        assert scores["completeness_score"] == 76.0
    
    def test_extract_scores_missing_values(self, structure_agent):
        """Test score extraction with missing values uses defaults."""
        output = """
        Only some scores present:
        Format Score: 85
        Professional Tone Score: 82
        """
        
        scores = structure_agent._extract_scores_from_output(output, structure_agent.score_patterns)
        
        assert scores["format_score"] == 85.0
        assert scores["section_organization_score"] == 75.0  # Default
        assert scores["professional_tone_score"] == 82.0
        assert scores["completeness_score"] == 75.0  # Default
    
    def test_extract_feedback_lists(self, structure_agent):
        """Test extraction of feedback lists from output."""
        output = """
        Formatting Issues:
        - Inconsistent bullet points
        - Uneven spacing
        
        Strengths:
        - Clear headers
        - Professional language
        
        Recommendations:
        - Add quantifiable metrics
        - Include summary section
        """
        
        feedback = structure_agent._extract_feedback_lists(output)
        
        assert len(feedback["formatting_issues"]) == 2
        assert "Inconsistent bullet points" in feedback["formatting_issues"]
        assert len(feedback["strengths"]) == 2
        assert "Clear headers" in feedback["strengths"]
        assert len(feedback["recommendations"]) == 2
        assert "Add quantifiable metrics" in feedback["recommendations"]
    
    @pytest.mark.asyncio
    async def test_analyze_success(self, structure_agent, sample_state):
        """Test successful structure analysis."""
        result = await structure_agent.analyze(sample_state)
        
        assert "structure_analysis" in result
        assert "structure_confidence" in result
        assert result["current_stage"] == "structure_analysis"
        assert len(result["structure_errors"]) == 0
        
        analysis = result["structure_analysis"]
        assert isinstance(analysis, StructureAnalysisResult)
        assert 0 <= analysis.format_score <= 100
        assert 0 <= analysis.section_organization_score <= 100
        assert 0 <= analysis.professional_tone_score <= 100
        assert 0 <= analysis.completeness_score <= 100
        assert 0 <= analysis.confidence_score <= 1
        assert analysis.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_analyze_with_empty_state(self, structure_agent):
        """Test analysis with invalid state."""
        invalid_state = AnalysisState(
            resume_text="",  # Empty text
            industry="tech_consulting",
            analysis_id="test-invalid",
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
        
        result = await structure_agent.analyze(invalid_state)
        
        assert result["has_errors"] is True
        assert len(result["error_messages"]) > 0
    
    def test_parse_structure_output(self, structure_agent):
        """Test parsing of structure analysis output."""
        raw_output = """
        Format Score: 85
        Section Organization Score: 78
        Professional Tone Score: 82
        Completeness Score: 76
        
        Formatting Issues:
        - Inconsistent formatting
        
        Strengths:
        - Clear organization
        - Professional tone
        """
        
        resume_text = "Sample resume text for testing"
        result = structure_agent._parse_structure_output(raw_output, resume_text)
        
        assert isinstance(result, StructureAnalysisResult)
        assert result.format_score == 85.0
        assert result.section_organization_score == 78.0
        assert result.professional_tone_score == 82.0
        assert result.completeness_score == 76.0
        assert len(result.strengths) == 2
        assert "Clear organization" in result.strengths
        assert len(result.formatting_issues) == 1
        assert result.word_count > 0
    
    def test_calculate_structure_confidence(self, structure_agent):
        """Test structure-specific confidence calculation."""
        # Create a good result
        good_result = StructureAnalysisResult(
            format_score=85.0,
            section_organization_score=80.0,
            professional_tone_score=90.0,
            completeness_score=75.0,
            formatting_issues=["Minor issue"],
            missing_sections=[],
            tone_problems=[],
            completeness_gaps=["Missing dates"],
            strengths=["Clear headers", "Professional tone", "Good organization"],
            recommendations=["Add metrics", "Include summary"],
            total_sections_found=4,
            word_count=500,
            estimated_reading_time_minutes=3,
            confidence_score=0.0,
            processing_time_ms=1000,
            model_used="test",
            prompt_version="test"
        )
        
        raw_output = """
        Format score: 85, organization score: 80, tone: professional
        Strengths include clear headers, good organization
        Recommendations: add metrics, include summary
        """
        
        confidence = structure_agent._calculate_structure_confidence(good_result, raw_output)
        
        assert 0.3 <= confidence <= 1.0  # Should be reasonable confidence
        assert confidence > 0.5  # Should be relatively high for good result
    
    def test_create_default_structure_result(self, structure_agent):
        """Test creation of default result when parsing fails."""
        resume_text = "Sample resume text"
        result = structure_agent._create_default_structure_result(resume_text)
        
        assert isinstance(result, StructureAnalysisResult)
        assert result.format_score == 70.0  # Default values
        assert result.confidence_score == 0.3
        assert len(result.strengths) > 0
        assert len(result.recommendations) > 0
        assert result.word_count == len(resume_text.split())
    
    def test_validate_structure_result(self, structure_agent):
        """Test validation of structure analysis results."""
        # Valid result
        valid_result = StructureAnalysisResult(
            format_score=85.0,
            section_organization_score=80.0,
            professional_tone_score=90.0,
            completeness_score=75.0,
            formatting_issues=[],
            missing_sections=[],
            tone_problems=[],
            completeness_gaps=[],
            strengths=["Good formatting"],
            recommendations=["Add metrics"],
            total_sections_found=4,
            word_count=500,
            estimated_reading_time_minutes=3,
            confidence_score=0.8,
            processing_time_ms=1000,
            model_used="test",
            prompt_version="test"
        )
        
        assert structure_agent.validate_structure_result(valid_result) is True
        
        # Invalid result - score out of range
        invalid_result = StructureAnalysisResult(
            format_score=150.0,  # Invalid score
            section_organization_score=80.0,
            professional_tone_score=90.0,
            completeness_score=75.0,
            formatting_issues=[],
            missing_sections=[],
            tone_problems=[],
            completeness_gaps=[],
            strengths=["Good formatting"],
            recommendations=["Add metrics"],
            total_sections_found=4,
            word_count=500,
            estimated_reading_time_minutes=3,
            confidence_score=0.8,
            processing_time_ms=1000,
            model_used="test",
            prompt_version="test"
        )
        
        assert structure_agent.validate_structure_result(invalid_result) is False
    
    def test_get_capabilities(self, structure_agent):
        """Test agent capabilities reporting."""
        capabilities = structure_agent._get_capabilities()
        
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert "resume_formatting_analysis" in capabilities
        assert "section_organization_assessment" in capabilities
    
    def test_get_expected_sections(self, structure_agent):
        """Test getting expected resume sections."""
        sections = structure_agent.get_expected_sections()
        
        assert isinstance(sections, list)
        assert len(sections) > 0
        assert "experience" in [s.lower() for s in sections]
        assert "education" in [s.lower() for s in sections]
    
    def test_build_analysis_prompt(self, structure_agent, sample_state):
        """Test analysis prompt building."""
        context = structure_agent._prepare_analysis_context(sample_state)
        prompt = structure_agent._build_analysis_prompt(context)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be substantial
        assert "FORMATTING ASSESSMENT" in prompt
        assert "SECTION ORGANIZATION" in prompt
        assert "PROFESSIONAL TONE" in prompt
        assert "COMPLETENESS" in prompt
        assert context["resume_text"] in prompt
    
    def test_get_system_message(self, structure_agent):
        """Test system message generation."""
        system_msg = structure_agent._get_system_message()
        
        assert isinstance(system_msg, str)
        assert len(system_msg) > 50
        assert "structure" in system_msg.lower()
        assert "formatting" in system_msg.lower()
        assert "professional" in system_msg.lower()
    
    def test_prepare_analysis_context(self, structure_agent, sample_state):
        """Test analysis context preparation."""
        context = structure_agent._prepare_analysis_context(sample_state)
        
        assert "resume_text" in context
        assert "analysis_id" in context
        assert "word_count" in context
        assert "character_count" in context
        assert "sections_found" in context
        assert "estimated_reading_time" in context
        
        assert context["word_count"] > 0
        assert context["character_count"] > 0
        assert len(context["sections_found"]) > 0
        assert context["estimated_reading_time"] >= 1