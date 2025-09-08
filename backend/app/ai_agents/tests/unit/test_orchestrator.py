"""Unit tests for Resume Analysis Orchestrator."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import uuid


@pytest.mark.asyncio
async def test_orchestrator_analyze_success(
    mock_structure_agent,
    mock_appeal_agent,
    sample_resume_text
):
    """Test successful orchestration of analysis workflow."""
    from app.ai_agents.orchestrator import ResumeAnalysisOrchestrator
    from app.ai_agents.core.workflow import create_workflow
    
    # Create orchestrator with mocked agents
    orchestrator = ResumeAnalysisOrchestrator()
    orchestrator.structure_agent = mock_structure_agent
    orchestrator.appeal_agent = mock_appeal_agent
    orchestrator.workflow = create_workflow(mock_structure_agent, mock_appeal_agent)
    
    # Run analysis
    result = await orchestrator.analyze(
        resume_text=sample_resume_text,
        industry="tech_consulting"
    )
    
    # Check response structure
    assert result["success"] is True
    assert "analysis_id" in result
    assert result["overall_score"] > 0
    assert result["market_tier"] in ["entry", "mid", "senior", "executive"]
    assert "summary" in result
    
    # Check structure results
    assert "structure" in result
    assert "scores" in result["structure"]
    assert "feedback" in result["structure"]
    
    # Check appeal results
    assert "appeal" in result
    assert "scores" in result["appeal"]
    assert "feedback" in result["appeal"]


@pytest.mark.asyncio
async def test_orchestrator_with_custom_analysis_id(
    mock_structure_agent,
    mock_appeal_agent,
    sample_resume_text
):
    """Test orchestrator with custom analysis ID."""
    from app.ai_agents.orchestrator import ResumeAnalysisOrchestrator
    from app.ai_agents.core.workflow import create_workflow
    
    orchestrator = ResumeAnalysisOrchestrator()
    orchestrator.structure_agent = mock_structure_agent
    orchestrator.appeal_agent = mock_appeal_agent
    orchestrator.workflow = create_workflow(mock_structure_agent, mock_appeal_agent)
    
    custom_id = "test-analysis-123"
    
    result = await orchestrator.analyze(
        resume_text=sample_resume_text,
        industry="finance_banking",
        analysis_id=custom_id
    )
    
    assert result["analysis_id"] == custom_id


@pytest.mark.asyncio
async def test_orchestrator_error_handling():
    """Test orchestrator error handling."""
    from app.ai_agents.orchestrator import ResumeAnalysisOrchestrator
    
    orchestrator = ResumeAnalysisOrchestrator()
    
    # Mock workflow to raise an error
    orchestrator.workflow = AsyncMock()
    orchestrator.workflow.ainvoke = AsyncMock(
        side_effect=Exception("Workflow error")
    )
    
    result = await orchestrator.analyze(
        resume_text="Test resume",
        industry="tech_consulting"
    )
    
    assert result["success"] is False
    assert "error" in result
    assert "Workflow error" in result["error"]
    assert result["overall_score"] == 0
    assert result["market_tier"] == "unknown"


@pytest.mark.asyncio
async def test_orchestrator_format_success_response():
    """Test formatting of successful response."""
    from app.ai_agents.orchestrator import ResumeAnalysisOrchestrator
    
    orchestrator = ResumeAnalysisOrchestrator()
    
    state = {
        "overall_score": 85.5,
        "market_tier": "senior",
        "summary": "Test summary",
        "structure_scores": {"format": 80},
        "structure_feedback": {"issues": ["Test issue"]},
        "structure_metadata": {"word_count": 250},
        "appeal_scores": {"skills_alignment": 90},
        "appeal_feedback": {"missing_skills": ["Python"]}
    }
    
    response = orchestrator._format_success_response(state, "test-id")
    
    assert response["success"] is True
    assert response["analysis_id"] == "test-id"
    assert response["overall_score"] == 85.5
    assert response["market_tier"] == "senior"
    assert response["summary"] == "Test summary"
    assert response["structure"]["scores"]["format"] == 80
    assert response["appeal"]["scores"]["skills_alignment"] == 90


@pytest.mark.asyncio
async def test_orchestrator_format_error_response():
    """Test formatting of error response."""
    from app.ai_agents.orchestrator import ResumeAnalysisOrchestrator
    
    orchestrator = ResumeAnalysisOrchestrator()
    
    response = orchestrator._format_error_response(
        "Test error message",
        "error-id"
    )
    
    assert response["success"] is False
    assert response["analysis_id"] == "error-id"
    assert response["error"] == "Test error message"
    assert response["overall_score"] == 0
    assert response["market_tier"] == "unknown"
    assert "error" in response["summary"].lower()