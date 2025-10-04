"""Standardized logging utilities for AI agents.

This module provides consistent logging helpers to eliminate duplicate
logging patterns across agent files.
"""

import logging
from typing import Dict, Any, Optional


def log_agent_start(logger: logging.Logger, agent_name: str, **context) -> None:
    """Log agent analysis start with consistent format.

    Args:
        logger: Logger instance
        agent_name: Name of the agent (e.g., "structure", "appeal")
        **context: Additional context to log (e.g., industry=value)
    """
    context_str = " ".join(f"{k}={v}" for k, v in context.items())
    msg = f"{agent_name.capitalize()} analysis started"
    if context_str:
        msg = f"{msg} {context_str}"
    logger.info(msg)


def log_agent_complete(
    logger: logging.Logger,
    agent_name: str,
    score: Optional[float] = None,
    **context
) -> None:
    """Log agent analysis completion with consistent format.

    Args:
        logger: Logger instance
        agent_name: Name of the agent
        score: Optional score to log
        **context: Additional context (e.g., tier=value)
    """
    parts = [f"{agent_name.capitalize()} analysis completed"]

    if score is not None:
        parts.append(f"score={score:.1f}")

    for k, v in context.items():
        parts.append(f"{k}={v}")

    logger.info(" ".join(parts))


def log_api_call(
    logger: logging.Logger,
    agent_name: str,
    model: str,
    max_tokens: int
) -> None:
    """Log OpenAI API call with consistent format.

    Args:
        logger: Logger instance
        agent_name: Name of the calling agent
        model: Model being requested
        max_tokens: Max tokens parameter
    """
    logger.info(
        f"Calling OpenAI API - agent: {agent_name}, "
        f"model: {model}, max_tokens: {max_tokens}"
    )


def log_api_response(
    logger: logging.Logger,
    agent_name: str,
    actual_model: str,
    usage: Dict[str, int]
) -> None:
    """Log OpenAI API response with consistent format.

    Args:
        logger: Logger instance
        agent_name: Name of the calling agent
        actual_model: Actual model used by OpenAI
        usage: Token usage dict with prompt_tokens, completion_tokens, total_tokens
    """
    logger.info(
        f"OpenAI API response - agent: {agent_name}, "
        f"actual model used: {actual_model}, "
        f"tokens: prompt={usage.get('prompt_tokens', 0)}, "
        f"completion={usage.get('completion_tokens', 0)}, "
        f"total={usage.get('total_tokens', 0)}"
    )


def log_prompts(logger: logging.Logger, agent_name: str, system: str, user: str) -> None:
    """Log the actual prompts being sent to OpenAI.

    Args:
        logger: Logger instance
        agent_name: Name of the calling agent
        system: System prompt content
        user: User prompt content
    """
    logger.info(f"=== SYSTEM PROMPT for {agent_name} ===")
    logger.info(system)
    logger.info(f"=== USER PROMPT for {agent_name} ===")
    logger.info(user)
    logger.info(f"=== END PROMPTS for {agent_name} ===")


def log_analysis_start(
    logger: logging.Logger,
    request_id: str,
    industry: str
) -> None:
    """Log orchestrator analysis start.

    Args:
        logger: Logger instance
        request_id: Analysis request ID
        industry: Target industry
    """
    logger.info(f"Starting analysis request_id={request_id} industry={industry}")


def log_analysis_complete(
    logger: logging.Logger,
    request_id: str,
    overall_score: float,
    elapsed: float
) -> None:
    """Log orchestrator analysis completion.

    Args:
        logger: Logger instance
        request_id: Analysis request ID
        overall_score: Final overall score
        elapsed: Elapsed time in seconds
    """
    logger.info(
        f"Analysis completed request_id={request_id} "
        f"overall_score={overall_score} time={elapsed:.1f}s"
    )


def log_analysis_error(
    logger: logging.Logger,
    request_id: str,
    error: str,
    elapsed: float,
    exc_info: bool = True
) -> None:
    """Log orchestrator analysis error.

    Args:
        logger: Logger instance
        request_id: Analysis request ID
        error: Error message
        elapsed: Elapsed time in seconds
        exc_info: Whether to include exception traceback
    """
    logger.error(
        f"Analysis failed request_id={request_id} "
        f"error={error} time={elapsed:.1f}s",
        exc_info=exc_info
    )
