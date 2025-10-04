"""Custom exceptions for AI agents."""


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
