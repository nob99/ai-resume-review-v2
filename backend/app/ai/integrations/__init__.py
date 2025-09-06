"""
LLM Integrations Module
=======================

This module provides integrations with various Large Language Model providers.
All integrations implement the BaseLLM interface for consistency.

Available Integrations:
- OpenAI GPT-4 (primary)
- Anthropic Claude (future)

The base interface ensures easy switching between providers and consistent
error handling across all LLM interactions.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_llm import BaseLLM
    from .openai_client import OpenAIClient