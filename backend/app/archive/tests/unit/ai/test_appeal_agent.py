"""
Unit Tests for Appeal Agent
============================

Tests for the Appeal Agent including industry-specific analysis functionality,
output parsing, validation, and error handling.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from pydantic import ValidationError
from app.ai.agents.appeal_agent import AppealAgent
from app.ai.models.analysis_request import AnalysisState, AppealAnalysisResult, StructureAnalysisResult
from app.ai.integrations.base_llm import MockLLM, LLMResponse


@pytest.fixture
def mock_llm():
    """Create a mock LLM with appeal-specific responses."""
    mock_responses = {
        "appeal": """
        Achievement Relevance Score: 82
        Skills Alignment Score: 78
        Experience Fit Score: 85
        Competitive Positioning Score: 80
        
        Relevant Achievements:
        - Led development team of 8 engineers
        - Improved system performance by 40%
        - Architected microservices for 1M+ users
        
        Missing Skills:
        - AWS cloud services experience
        - Machine learning frameworks
        - DevOps automation tools
        
        Transferable Experience:
        - Technical leadership experience
        - Full-stack development skills
        - Agile project management
        
        Industry Keywords:
        - Software engineering
        - System architecture
        - Technical leadership
        
        Market Tier Assessment: Senior
        
        Competitive Advantages:
        - Strong technical leadership background
        - Proven scalability expertise
        - Full-stack versatility
        
        Improvement Areas:
        - Add cloud computing certifications
        - Include machine learning projects
        - Highlight DevOps experience
        """
    }
    return MockLLM(mock_responses=mock_responses)


@pytest.fixture
def appeal_agent(mock_llm):
    """Create AppealAgent with mock LLM."""
    return AppealAgent(mock_llm)


@pytest.fixture
def sample_state():
    """Create sample analysis state for testing."""
    # Mock structure analysis result
    structure_analysis = StructureAnalysisResult(
        format_score=85.0,
        section_organization_score=80.0,
        professional_tone_score=90.0,
        completeness_score=75.0,
        formatting_issues=["Minor spacing issues"],
        missing_sections=[],
        tone_problems=[],
        completeness_gaps=["Missing quantifiable metrics"],
        strengths=["Clear section headers", "Professional language"],
        recommendations=["Add quantifiable achievements", "Include technical skills"],
        total_sections_found=6,
        word_count=450,
        estimated_reading_time_minutes=2,
        confidence_score=0.82,
        processing_time_ms=1200,
        model_used="gpt-4",
        prompt_version="structure_v1.0"
    )
    
    return AnalysisState(
        resume_text="""
        John Smith
        Senior Software Engineer
        john.smith@email.com | (555) 123-4567
        
        EXPERIENCE
        Senior Software Engineer | TechCorp Inc. | 2020-Present
        - Led team of 8 developers on React/Node.js applications
        - Improved system performance by 40% through optimization
        - Architected microservices handling 1M+ daily requests
        
        Software Engineer | StartupXYZ | 2018-2020
        - Developed REST APIs using Python/Django
        - Collaborated with cross-functional teams
        
        SKILLS
        Languages: Python, JavaScript, TypeScript, SQL
        Frameworks: React, Node.js, Django, FastAPI
        """,
        industry="tech_consulting",
        analysis_id="test-appeal-123",
        user_id="test-user",
        current_stage="appeal_analysis",
        has_errors=False,
        error_messages=[],
        retry_count=0,
        structure_errors=[],
        appeal_errors=[],
        structure_analysis=structure_analysis,
        structure_confidence=0.82,
        appeal_analysis=None,
        appeal_confidence=None,
        final_result=None,
        overall_score=None,
        max_retries=2,
        started_at=None,
        completed_at=None,
        processing_time_seconds=None
    )


class TestAppealAgent:
    """Test the Appeal Agent functionality."""
    
    def test_agent_initialization(self, mock_llm):
        """Test appeal agent initializes correctly."""
        agent = AppealAgent(mock_llm)
        
        assert agent.agent_name == "AppealAgent"
        assert agent.llm == mock_llm
        assert agent.score_patterns is not None
        assert "achievement_relevance_score" in agent.score_patterns
        assert "skills_alignment_score" in agent.score_patterns
        assert "experience_fit_score" in agent.score_patterns
        assert "competitive_positioning_score" in agent.score_patterns
    
    def test_extract_scores_from_output(self, appeal_agent):
        """Test score extraction from LLM output."""
        output = """
        Achievement Relevance Score: 85.5
        Skills Alignment Score: 78.2
        Experience Fit Score: 90.0
        Competitive Positioning Score: 82.8
        """
        
        scores = appeal_agent._extract_scores_from_output(output)
        
        assert scores["achievement_relevance_score"] == 85.5
        assert scores["skills_alignment_score"] == 78.2
        assert scores["experience_fit_score"] == 90.0
        assert scores["competitive_positioning_score"] == 82.8
    
    def test_extract_scores_missing_values(self, appeal_agent):
        """Test score extraction with missing values."""
        output = """
        Achievement Relevance Score: 85
        Skills Alignment Score: Not available
        Experience Fit Score: 90
        """
        
        scores = appeal_agent._extract_scores_from_output(output)
        
        assert scores["achievement_relevance_score"] == 85.0
        assert scores["skills_alignment_score"] == 70.0  # Default value
        assert scores["experience_fit_score"] == 90.0
        assert scores["competitive_positioning_score"] == 70.0  # Default value
    
    def test_extract_achievement_lists(self, appeal_agent):
        """Test extraction of achievement lists from output."""
        output = """
        Relevant Achievements:
        - Led development team of 8 engineers
        - Improved system performance by 40%
        - Architected microservices for 1M+ users
        
        Missing Skills:
        - AWS cloud services experience
        - Machine learning frameworks
        
        Transferable Experience:
        - Technical leadership experience
        - Full-stack development skills
        
        Industry Keywords:
        - Software engineering
        - System architecture
        - Technical leadership
        
        Competitive Advantages:
        - Strong technical leadership background
        - Proven scalability expertise
        
        Improvement Areas:
        - Add cloud computing certifications
        - Include machine learning projects
        """
        
        lists = appeal_agent._extract_achievement_lists(output)
        
        assert len(lists["relevant_achievements"]) == 3
        assert "Led development team of 8 engineers" in lists["relevant_achievements"]
        assert len(lists["missing_skills"]) == 2
        assert "AWS cloud services experience" in lists["missing_skills"]
        assert len(lists["transferable_experience"]) == 2
        assert len(lists["industry_keywords"]) == 3
        assert len(lists["competitive_advantages"]) == 2
        assert len(lists["improvement_areas"]) == 2
    
    def test_extract_market_tier(self, appeal_agent):
        """Test market tier extraction."""
        output_senior = "Market Tier Assessment: Senior"
        output_mid = "Market Tier Assessment: Mid-level"
        output_entry = "Market Tier Assessment: Entry"
        output_executive = "Market Tier Assessment: Executive"
        
        assert appeal_agent._extract_market_tier(output_senior) == "senior"
        assert appeal_agent._extract_market_tier(output_mid) == "mid"
        assert appeal_agent._extract_market_tier(output_entry) == "entry"
        assert appeal_agent._extract_market_tier(output_executive) == "executive"
    
    def test_extract_market_tier_default(self, appeal_agent):
        """Test market tier extraction with default value."""
        output = "No market tier information available"
        
        tier = appeal_agent._extract_market_tier(output)
        assert tier == "mid"  # Default value
    
    @pytest.mark.asyncio
    async def test_analyze_success(self, appeal_agent, sample_state):
        """Test successful appeal analysis."""
        result = await appeal_agent.analyze(sample_state)
        
        assert "appeal_analysis" in result
        assert "appeal_confidence" in result
        assert result["current_stage"] == "appeal_analysis"
        assert len(result["appeal_errors"]) == 0
        
        analysis = result["appeal_analysis"]
        assert isinstance(analysis, AppealAnalysisResult)
        assert 0 <= analysis.achievement_relevance_score <= 100
        assert 0 <= analysis.skills_alignment_score <= 100
        assert 0 <= analysis.experience_fit_score <= 100
        assert 0 <= analysis.competitive_positioning_score <= 100
        assert analysis.target_industry == "tech_consulting"
        assert analysis.structure_context_used is True
    
    @pytest.mark.asyncio
    async def test_analyze_with_empty_state(self, appeal_agent):
        """Test appeal analysis with minimal state."""
        empty_state = AnalysisState(
            resume_text="",
            industry="tech_consulting",
            analysis_id="test-empty",
            user_id="test-user",
            current_stage="appeal_analysis",
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
        
        result = await appeal_agent.analyze(empty_state)
        
        assert result["has_errors"] is True
        assert "appeal_errors" in result
        assert len(result["appeal_errors"]) > 0
    
    def test_parse_appeal_output(self, appeal_agent):
        """Test parsing of complete appeal output."""
        output = """
        Achievement Relevance Score: 82
        Skills Alignment Score: 78
        Experience Fit Score: 85
        Competitive Positioning Score: 80
        
        Relevant Achievements:
        - Led team of 8 developers
        - Improved performance by 40%
        
        Missing Skills:
        - AWS experience
        - DevOps tools
        
        Transferable Experience:
        - Leadership experience
        - Full-stack skills
        
        Industry Keywords:
        - Software engineering
        - System architecture
        
        Market Tier Assessment: Senior
        
        Competitive Advantages:
        - Strong leadership background
        - Technical expertise
        
        Improvement Areas:
        - Add certifications
        - Include projects
        """
        
        result = appeal_agent._parse_appeal_output(
            raw_output=output,
            industry="tech_consulting",
            structure_context_used=True,
            processing_time_ms=1500
        )
        
        assert isinstance(result, AppealAnalysisResult)
        assert result.achievement_relevance_score == 82.0
        assert result.skills_alignment_score == 78.0
        assert result.experience_fit_score == 85.0
        assert result.competitive_positioning_score == 80.0
        assert len(result.relevant_achievements) == 2
        assert len(result.missing_skills) == 2
        assert len(result.transferable_experience) == 2
        assert len(result.industry_keywords) == 2
        assert result.market_tier == "senior"
        assert len(result.competitive_advantages) == 2
        assert len(result.improvement_areas) == 2
        assert result.target_industry == "tech_consulting"
        assert result.structure_context_used is True
    
    def test_calculate_appeal_confidence(self, appeal_agent):
        """Test appeal confidence calculation."""
        result = AppealAnalysisResult(
            achievement_relevance_score=85.0,
            skills_alignment_score=80.0,
            experience_fit_score=90.0,
            competitive_positioning_score=88.0,
            relevant_achievements=["Led team", "Improved performance", "Architected system"],
            missing_skills=["AWS", "ML"],
            transferable_experience=["Leadership", "Development"],
            industry_keywords=["Engineering", "Architecture"],
            market_tier="senior",
            competitive_advantages=["Leadership", "Technical expertise"],
            improvement_areas=["Certifications", "Projects"],
            structure_context_used=True,
            target_industry="tech_consulting",
            confidence_score=0.0,  # Will be calculated
            processing_time_ms=1000,
            model_used="gpt-4",
            prompt_version="appeal_v1.0"
        )
        
        raw_output = "Detailed analysis with comprehensive scores and feedback"
        
        confidence = appeal_agent._calculate_appeal_confidence(result, raw_output)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be decent confidence with good data
    
    def test_create_default_appeal_result(self, appeal_agent):
        """Test creation of default appeal result."""
        result = appeal_agent._create_default_appeal_result(
            industry="tech_consulting",
            structure_context_used=False,
            processing_time_ms=500
        )
        
        assert isinstance(result, AppealAnalysisResult)
        assert result.target_industry == "tech_consulting"
        assert result.structure_context_used is False
        assert result.processing_time_ms == 500
        assert result.achievement_relevance_score == 70.0  # Default score
        assert result.skills_alignment_score == 70.0
        assert result.experience_fit_score == 70.0
        assert result.competitive_positioning_score == 70.0
        assert result.market_tier == "mid"  # Default tier
    
    def test_validate_appeal_result(self, appeal_agent):
        """Test appeal result validation."""
        # Valid result
        valid_result = AppealAnalysisResult(
            achievement_relevance_score=85.0,
            skills_alignment_score=80.0,
            experience_fit_score=90.0,
            competitive_positioning_score=88.0,
            relevant_achievements=["Achievement 1"],
            missing_skills=["Skill 1"],
            transferable_experience=["Experience 1"],
            industry_keywords=["Keyword 1"],
            market_tier="senior",
            competitive_advantages=["Advantage 1"],
            improvement_areas=["Improvement 1"],
            structure_context_used=True,
            target_industry="tech_consulting",
            confidence_score=0.85,
            processing_time_ms=1000,
            model_used="gpt-4",
            prompt_version="appeal_v1.0"
        )
        
        assert appeal_agent.validate_appeal_result(valid_result) is True
        
        # Test that invalid scores raise validation errors
        with pytest.raises(ValidationError):
            invalid_result = AppealAnalysisResult(
                achievement_relevance_score=150.0,  # Invalid score - over 100
                skills_alignment_score=80.0,
                experience_fit_score=90.0,
                competitive_positioning_score=88.0,
                relevant_achievements=["Achievement 1"],
                missing_skills=["Skill 1"],
                transferable_experience=["Experience 1"],
                industry_keywords=["Keyword 1"],
                market_tier="senior",
                competitive_advantages=["Advantage 1"],
                improvement_areas=["Improvement 1"],
                structure_context_used=True,
                target_industry="tech_consulting",
                confidence_score=0.85,
                processing_time_ms=1000,
                model_used="gpt-4",
                prompt_version="appeal_v1.0"
            )
    
    def test_get_supported_industries(self, appeal_agent):
        """Test getting supported industries."""
        industries = appeal_agent._get_supported_industries()
        
        assert isinstance(industries, list)
        assert len(industries) > 0
        assert "tech_consulting" in industries
        assert "system_integrator" in industries
        assert "finance_banking" in industries
        assert "healthcare_pharma" in industries
        assert "manufacturing" in industries
        assert "general_business" in industries
    
    def test_build_analysis_prompt(self, appeal_agent, sample_state):
        """Test building analysis prompt."""
        prompt = appeal_agent._build_analysis_prompt(sample_state)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "tech_consulting" in prompt.lower()
        assert "resume" in prompt.lower()
        assert "analysis" in prompt.lower()
        # Should include structure context if available
        assert "structure" in prompt.lower()
    
    def test_build_analysis_prompt_without_structure(self, appeal_agent):
        """Test building analysis prompt without structure context."""
        state_no_structure = AnalysisState(
            resume_text="Sample resume text",
            industry="tech_consulting",
            analysis_id="test",
            user_id="user",
            current_stage="appeal_analysis",
            has_errors=False,
            error_messages=[],
            retry_count=0,
            structure_errors=[],
            appeal_errors=[],
            structure_analysis=None,  # No structure analysis
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
        
        prompt = appeal_agent._build_analysis_prompt(state_no_structure)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 50
        assert "tech_consulting" in prompt.lower()
    
    def test_get_industry_specific_prompt(self, appeal_agent):
        """Test getting industry-specific prompts."""
        tech_prompt = appeal_agent._get_industry_specific_prompt("tech_consulting")
        finance_prompt = appeal_agent._get_industry_specific_prompt("finance_banking")
        general_prompt = appeal_agent._get_industry_specific_prompt("unknown_industry")
        
        assert isinstance(tech_prompt, str)
        assert len(tech_prompt) > 50
        assert "technical" in tech_prompt.lower()
        
        assert isinstance(finance_prompt, str)
        assert len(finance_prompt) > 50
        assert "financial" in finance_prompt.lower()
        
        assert isinstance(general_prompt, str)
        assert len(general_prompt) > 50
        assert "business" in general_prompt.lower()
    
    def test_get_agent_info(self, appeal_agent):
        """Test getting agent information."""
        info = appeal_agent.get_agent_info()
        
        assert isinstance(info, dict)
        assert "agent_name" in info
        assert "capabilities" in info
        assert "supported_industries" in info
        assert info["agent_name"] == "AppealAgent"
        assert len(info["supported_industries"]) == 6