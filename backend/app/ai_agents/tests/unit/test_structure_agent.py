"""Unit tests for Structure Agent."""

import pytest
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.asyncio
async def test_structure_agent_analyze_success(mock_structure_agent, initial_state):
    """Test successful structure analysis."""
    # Run analysis
    result = await mock_structure_agent.analyze(initial_state)
    
    # Check that scores were extracted correctly
    assert result["structure_scores"] is not None
    assert result["structure_scores"]["format"] == 85
    assert result["structure_scores"]["organization"] == 90
    assert result["structure_scores"]["tone"] == 88
    assert result["structure_scores"]["completeness"] == 82
    
    # Check feedback was extracted
    assert result["structure_feedback"] is not None
    assert "issues" in result["structure_feedback"]
    assert "strengths" in result["structure_feedback"]
    assert len(result["structure_feedback"]["strengths"]) > 0
    
    # Check metadata
    assert result["structure_metadata"] is not None
    assert result["structure_metadata"]["total_sections"] == 5
    assert result["structure_metadata"]["word_count"] == 250


@pytest.mark.asyncio
async def test_structure_agent_analyze_with_error(initial_state):
    """Test structure analysis with API error."""
    from app.ai_agents.agents.structure import StructureAgent
    
    agent = StructureAgent()
    agent.client = AsyncMock()
    
    # Mock API error
    agent.client.chat.completions.create = AsyncMock(
        side_effect=Exception("API Error")
    )
    
    # Run analysis
    result = await agent.analyze(initial_state)
    
    # Check error handling
    assert result["error"] is not None
    assert "Structure analysis failed" in result["error"]
    assert result["structure_scores"]["format"] == 0
    assert result["structure_feedback"]["issues"] == ["Analysis failed"]


@pytest.mark.asyncio
async def test_structure_agent_retry_logic():
    """Test retry logic on API failures."""
    from app.ai_agents.agents.structure import StructureAgent
    
    agent = StructureAgent()
    agent.client = AsyncMock()
    
    # Mock successful response after 2 failures
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Format Score: 75"
    
    agent.client.chat.completions.create = AsyncMock(
        side_effect=[
            Exception("Temporary error"),
            Exception("Another temporary error"),
            mock_response
        ]
    )
    
    state = {"resume_text": "Test resume"}
    
    # Run analysis - should succeed after retries
    result = await agent.analyze(state)
    
    # Verify retry happened
    assert agent.client.chat.completions.create.call_count == 3
    assert result["structure_scores"]["format"] == 75


def test_structure_agent_parse_response():
    """Test response parsing logic."""
    from app.ai_agents.agents.structure import StructureAgent
    
    agent = StructureAgent()
    
    response = """
    Format Score: 90
    Section Organization Score: 85
    Professional Tone Score: 92
    Completeness Score: 88
    
    Strengths:
    - Excellent formatting
    - Clear structure
    
    Recommendations:
    - Add more details
    - Include certifications
    """
    
    parsed = agent._parse_response(response)
    
    assert parsed["scores"]["format"] == 90
    assert parsed["scores"]["organization"] == 85
    assert parsed["scores"]["tone"] == 92
    assert parsed["scores"]["completeness"] == 88
    assert len(parsed["feedback"]["strengths"]) == 2
    assert len(parsed["feedback"]["recommendations"]) == 2


def test_structure_agent_extract_list():
    """Test list extraction from text."""
    from app.ai_agents.agents.structure import StructureAgent
    
    agent = StructureAgent()
    
    text = """
    Some Section:
    - First item
    - Second item
    - Third item
    
    Another Section:
    - Different item
    """
    
    items = agent._extract_list(text, "Some Section")
    
    assert len(items) == 3
    assert items[0] == "First item"
    assert items[1] == "Second item"
    assert items[2] == "Third item"