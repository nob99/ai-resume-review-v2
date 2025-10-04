"""Utility functions and helpers for AI agents."""

from .exceptions import (
    AIAgentError,
    RetryableError,
    FatalError,
    APIRateLimitError,
    InvalidInputError
)
from .validation import validate_industry, validate_resume_text
from .context_builder import build_structure_context
from .logging import (
    log_agent_start,
    log_agent_complete,
    log_api_call,
    log_api_response,
    log_prompts,
    log_analysis_start,
    log_analysis_complete,
    log_analysis_error
)

__all__ = [
    # Exceptions
    "AIAgentError",
    "RetryableError",
    "FatalError",
    "APIRateLimitError",
    "InvalidInputError",
    # Validation
    "validate_industry",
    "validate_resume_text",
    # Context building
    "build_structure_context",
    # Logging
    "log_agent_start",
    "log_agent_complete",
    "log_api_call",
    "log_api_response",
    "log_prompts",
    "log_analysis_start",
    "log_analysis_complete",
    "log_analysis_error",
]
