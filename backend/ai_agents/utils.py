"""Utility functions for AI agents."""

import asyncio
import logging
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


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


async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retry_on: tuple = (RetryableError, Exception)
) -> T:
    """Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        max_delay: Maximum delay between retries in seconds
        retry_on: Tuple of exception types to retry on
        
    Returns:
        Result of the function call
        
    Raises:
        The last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retry_on as e:
            last_exception = e
            
            if attempt == max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded: {str(e)}")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(backoff_factor ** attempt, max_delay)
            
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}. "
                f"Retrying in {delay:.1f} seconds..."
            )
            
            await asyncio.sleep(delay)
    
    raise last_exception


def validate_industry(industry: str) -> str:
    """Validate and normalize industry code.
    
    Args:
        industry: Industry code to validate
        
    Returns:
        Normalized industry code
        
    Raises:
        InvalidInputError: If industry is not supported
    """
    valid_industries = {
        "tech_consulting",
        "finance_banking",
        "general_business",
        "system_integrator",
        "strategy_consulting",
        "full_service_consulting"
    }
    
    normalized = industry.lower().strip()
    
    if normalized not in valid_industries:
        raise InvalidInputError(
            f"Invalid industry '{industry}'. "
            f"Supported industries: {', '.join(sorted(valid_industries))}"
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


def calculate_weighted_score(
    scores: dict,
    weights: Optional[dict] = None
) -> float:
    """Calculate weighted average of scores.
    
    Args:
        scores: Dictionary of score names to values
        weights: Optional dictionary of score names to weights
                If not provided, equal weights are used
        
    Returns:
        Weighted average score (0-100)
    """
    if not scores:
        return 0.0
    
    # Use equal weights if not provided
    if weights is None:
        weights = {key: 1.0 for key in scores.keys()}
    
    # Normalize weights to sum to 1
    total_weight = sum(weights.get(key, 0) for key in scores.keys())
    if total_weight == 0:
        return 0.0
    
    # Calculate weighted average
    weighted_sum = sum(
        scores[key] * weights.get(key, 0) / total_weight
        for key in scores.keys()
    )
    
    return round(weighted_sum, 1)


def truncate_text(text: str, max_length: int = 1000) -> str:
    """Truncate text to maximum length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def extract_email(text: str) -> Optional[str]:
    """Extract email address from resume text.
    
    Args:
        text: Resume text
        
    Returns:
        Email address if found, None otherwise
    """
    import re
    
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text)
    
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    """Extract phone number from resume text.
    
    Args:
        text: Resume text
        
    Returns:
        Phone number if found, None otherwise
    """
    import re
    
    # Common phone patterns
    phone_patterns = [
        r'\+?1?\s*\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})',  # US format
        r'\+\d{1,3}\s*\d{4,14}',  # International format
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return None


def sanitize_for_llm(text: str) -> str:
    """Sanitize text before sending to LLM.
    
    Removes or masks sensitive information.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text
    """
    import re
    
    # Mask email addresses
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL]',
        text
    )
    
    # Mask phone numbers
    text = re.sub(
        r'\+?1?\s*\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})',
        '[PHONE]',
        text
    )
    
    # Mask SSN patterns
    text = re.sub(
        r'\b\d{3}-\d{2}-\d{4}\b',
        '[SSN]',
        text
    )
    
    return text