"""Unit tests for utility functions."""

import pytest
import asyncio
from app.ai_agents.utils import (
    validate_industry,
    validate_resume_text,
    calculate_weighted_score,
    truncate_text,
    extract_email,
    extract_phone,
    sanitize_for_llm,
    retry_with_backoff,
    InvalidInputError,
    RetryableError
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


def test_calculate_weighted_score_equal_weights():
    """Test weighted score calculation with equal weights."""
    scores = {"a": 80, "b": 90, "c": 70}
    result = calculate_weighted_score(scores)
    assert result == 80.0  # Average of 80, 90, 70


def test_calculate_weighted_score_custom_weights():
    """Test weighted score calculation with custom weights."""
    scores = {"a": 80, "b": 90}
    weights = {"a": 0.3, "b": 0.7}
    result = calculate_weighted_score(scores, weights)
    assert result == 87.0  # 80*0.3 + 90*0.7


def test_calculate_weighted_score_empty():
    """Test weighted score with empty scores."""
    assert calculate_weighted_score({}) == 0.0


def test_truncate_text():
    """Test text truncation."""
    text = "A" * 1500
    
    # Test truncation
    result = truncate_text(text, max_length=1000)
    assert len(result) == 1000
    assert result.endswith("...")
    
    # Test no truncation needed
    short_text = "Short text"
    result = truncate_text(short_text, max_length=100)
    assert result == short_text


def test_extract_email():
    """Test email extraction from text."""
    text = "Contact me at john.doe@example.com for more info"
    email = extract_email(text)
    assert email == "john.doe@example.com"
    
    # Test no email
    text_no_email = "No email here"
    assert extract_email(text_no_email) is None


def test_extract_phone():
    """Test phone extraction from text."""
    # US format
    text = "Call me at (555) 123-4567"
    phone = extract_phone(text)
    assert phone is not None
    assert "555" in phone
    assert "123" in phone
    assert "4567" in phone
    
    # No phone
    text_no_phone = "No phone here"
    assert extract_phone(text_no_phone) is None


def test_sanitize_for_llm():
    """Test text sanitization for LLM."""
    text = """
    John Doe
    Email: john.doe@example.com
    Phone: (555) 123-4567
    SSN: 123-45-6789
    """
    
    sanitized = sanitize_for_llm(text)
    
    assert "[EMAIL]" in sanitized
    assert "john.doe@example.com" not in sanitized
    assert "[PHONE]" in sanitized
    assert "(555) 123-4567" not in sanitized
    assert "[SSN]" in sanitized
    assert "123-45-6789" not in sanitized


@pytest.mark.asyncio
async def test_retry_with_backoff_success():
    """Test retry with backoff on success."""
    call_count = 0
    
    async def func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RetryableError("Temporary error")
        return "success"
    
    result = await retry_with_backoff(func, max_retries=3, backoff_factor=0.1)
    
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_with_backoff_max_retries():
    """Test retry with backoff reaching max retries."""
    call_count = 0
    
    async def func():
        nonlocal call_count
        call_count += 1
        raise RetryableError("Always fails")
    
    with pytest.raises(RetryableError):
        await retry_with_backoff(func, max_retries=2, backoff_factor=0.1)
    
    assert call_count == 3  # Initial + 2 retries