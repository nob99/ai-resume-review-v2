"""Unit tests for utility functions."""

import pytest
from ai_agents.utils import (
    validate_industry,
    validate_resume_text,
    InvalidInputError
)


def test_validate_industry_valid():
    """Test validation of valid industry codes."""
    valid_industries = [
        "tech_consulting",
        "finance_banking",
        "general_business",
        "system_integrator",
        "strategy_consulting",
        "full_service_consulting"
    ]
    
    for industry in valid_industries:
        result = validate_industry(industry)
        assert result == industry.lower()
    
    # Test with uppercase
    assert validate_industry("TECH_CONSULTING") == "tech_consulting"
    
    # Test with spaces
    assert validate_industry("  finance_banking  ") == "finance_banking"


def test_validate_industry_invalid():
    """Test validation of invalid industry codes."""
    with pytest.raises(InvalidInputError) as exc_info:
        validate_industry("invalid_industry")
    
    assert "Invalid industry" in str(exc_info.value)
    assert "Supported industries" in str(exc_info.value)


def test_validate_resume_text_valid():
    """Test validation of valid resume text."""
    valid_text = "A" * 200  # 200 characters
    result = validate_resume_text(valid_text)
    assert result == valid_text


def test_validate_resume_text_empty():
    """Test validation of empty resume text."""
    with pytest.raises(InvalidInputError) as exc_info:
        validate_resume_text("")
    
    assert "cannot be empty" in str(exc_info.value)


def test_validate_resume_text_too_short():
    """Test validation of too short resume text."""
    with pytest.raises(InvalidInputError) as exc_info:
        validate_resume_text("Too short")
    
    assert "too short" in str(exc_info.value)


def test_validate_resume_text_too_long():
    """Test validation of too long resume text."""
    with pytest.raises(InvalidInputError) as exc_info:
        validate_resume_text("A" * 50001)

    assert "too long" in str(exc_info.value)