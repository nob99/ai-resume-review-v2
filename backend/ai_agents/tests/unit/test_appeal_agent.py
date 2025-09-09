"""Unit tests for Appeal Agent."""

import pytest
from unittest.mock import AsyncMock, Mock


@pytest.mark.asyncio
async def test_appeal_agent_analyze_success(mock_appeal_agent, initial_state):
    """Test successful appeal analysis."""
    # Add structure results to state (from previous agent)
    initial_state["structure_scores"] = {
        "format": 85,
        "organization": 90,
        "tone": 88,
        "completeness": 82
    }
    initial_state["structure_feedback"] = {
        "issues": ["Inconsistent spacing"],
        "strengths": ["Clear headers", "Good bullet points"]
    }
    
    # Run analysis
    result = await mock_appeal_agent.analyze(initial_state)
    
    # Check that scores were extracted correctly
    assert result["appeal_scores"] is not None
    assert result["appeal_scores"]["achievement_relevance"] == 88
    assert result["appeal_scores"]["skills_alignment"] == 92
    assert result["appeal_scores"]["experience_fit"] == 85
    assert result["appeal_scores"]["competitive_positioning"] == 87
    
    # Check market tier
    assert result["market_tier"] == "senior"
    
    # Check overall score calculation
    assert result["overall_score"] is not None
    assert 80 <= result["overall_score"] <= 90  # Should be weighted average
    
    # Check summary generation
    assert result["summary"] is not None
    assert "Technology Consulting" in result["summary"]
    assert "senior" in result["summary"]


@pytest.mark.asyncio
async def test_appeal_agent_different_industries():
    """Test appeal agent with different industries."""
    from app.ai_agents.agents.appeal import AppealAgent
    
    agent = AppealAgent()
    
    # Test industry configurations
    industries = ["tech_consulting", "finance_banking", "strategy_consulting"]
    
    for industry in industries:
        config = agent.INDUSTRY_CONFIGS[industry]
        assert "display_name" in config
        assert "key_skills" in config
        assert len(config["key_skills"]) > 0


@pytest.mark.asyncio
async def test_appeal_agent_build_structure_context():
    """Test structure context building."""
    from app.ai_agents.agents.appeal import AppealAgent
    
    agent = AppealAgent()
    
    state = {
        "structure_scores": {
            "format": 85,
            "organization": 90,
            "tone": 88,
            "completeness": 82
        },
        "structure_feedback": {
            "issues": ["Issue 1", "Issue 2", "Issue 3", "Issue 4"],
            "strengths": ["Strength 1", "Strength 2", "Strength 3"]
        }
    }
    
    context = agent._build_structure_context(state)
    
    assert "Format Score: 85/100" in context
    assert "Organization Score: 90/100" in context
    assert "Key Issues:" in context
    assert "Issue 1" in context
    assert "Strengths:" in context
    assert "Strength 1" in context


@pytest.mark.asyncio
async def test_appeal_agent_calculate_overall_score():
    """Test overall score calculation."""
    from app.ai_agents.agents.appeal import AppealAgent
    
    agent = AppealAgent()
    
    state = {
        "structure_scores": {
            "format": 80,
            "organization": 80,
            "tone": 80,
            "completeness": 80
        },
        "appeal_scores": {
            "achievement_relevance": 90,
            "skills_alignment": 90,
            "experience_fit": 90,
            "competitive_positioning": 90
        }
    }
    
    score = agent._calculate_overall_score(state)
    
    # Should be 40% structure (80) + 60% appeal (90) = 86
    assert score == 86.0


@pytest.mark.asyncio
async def test_appeal_agent_generate_summary():
    """Test summary generation."""
    from app.ai_agents.agents.appeal import AppealAgent
    
    agent = AppealAgent()
    
    state = {
        "overall_score": 85,
        "market_tier": "senior",
        "structure_feedback": {
            "strengths": ["Clear formatting"]
        },
        "appeal_feedback": {
            "competitive_advantages": ["Strong leadership"],
            "improvement_areas": ["Add certifications", "More metrics"]
        }
    }
    
    summary = agent._generate_summary(state, "Technology Consulting")
    
    assert "85/100" in summary
    assert "excellent" in summary.lower()
    assert "senior" in summary
    assert "Technology Consulting" in summary
    assert "Clear formatting" in summary or "Strong leadership" in summary
    assert "Add certifications" in summary or "More metrics" in summary


@pytest.mark.asyncio
async def test_appeal_agent_error_handling(initial_state):
    """Test appeal analysis with API error."""
    from app.ai_agents.agents.appeal import AppealAgent
    
    agent = AppealAgent()
    agent.client = AsyncMock()
    
    # Mock API error
    agent.client.chat.completions.create = AsyncMock(
        side_effect=Exception("API Error")
    )
    
    # Add structure results
    initial_state["structure_scores"] = {"format": 80}
    
    # Run analysis
    result = await agent.analyze(initial_state)
    
    # Check error handling
    assert result["error"] is not None
    assert "Appeal analysis failed" in result["error"]
    assert result["appeal_scores"]["achievement_relevance"] == 0
    assert result["market_tier"] == "unknown"
    assert result["overall_score"] == 0