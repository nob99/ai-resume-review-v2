"""Utility functions for AI agents."""

from app.core.industries import INDUSTRY_CONFIGS


class AIAgentError(Exception):
    """Base exception for AI agent errors."""
    pass


class RetryableError(AIAgentError):
    """Error that can be retried."""
    pass


class FatalError(AIAgentError):
    """Error that should not be retried."""
    pass


class APIRateLimitError(RetryableError):
    """API rate limit exceeded."""
    pass


class InvalidInputError(FatalError):
    """Invalid input provided to agent."""
    pass


def validate_industry(industry: str) -> str:
    """Validate and normalize industry code.

    Args:
        industry: Industry code to validate

    Returns:
        Normalized industry code

    Raises:
        InvalidInputError: If industry is not supported
    """
    normalized = industry.lower().strip()

    if normalized not in INDUSTRY_CONFIGS:
        raise InvalidInputError(
            f"Invalid industry '{industry}'. "
            f"Supported industries: {', '.join(sorted(INDUSTRY_CONFIGS.keys()))}"
        )

    return normalized


def validate_resume_text(resume_text: str) -> str:
    """Validate resume text input.
    
    Args:
        resume_text: Resume text to validate
        
    Returns:
        Cleaned resume text
        
    Raises:
        InvalidInputError: If resume text is invalid
    """
    if not resume_text:
        raise InvalidInputError("Resume text cannot be empty")
    
    # Clean the text
    cleaned = resume_text.strip()
    
    # Check minimum length (at least 100 characters for a valid resume)
    if len(cleaned) < 100:
        raise InvalidInputError(
            "Resume text is too short. Please provide a complete resume."
        )
    
    # Check maximum length (roughly 10 pages of text)
    if len(cleaned) > 50000:
        raise InvalidInputError(
            "Resume text is too long. Maximum 50,000 characters allowed."
        )
    
    return cleaned