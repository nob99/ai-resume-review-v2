"""AI Agents Prompts Module.

This module contains prompt templates and parsing patterns for AI agents.

Prompt Templates (YAML):
- structure_prompt_v1_{lang}.yaml - Resume structure analysis prompts
- appeal_prompt_v1_{lang}.yaml - Industry-specific appeal analysis prompts

Parsing Patterns (Python):
- parsing_patterns.py - Shared regex patterns for consistent LLM response parsing

The regex patterns in YAML files follow a standardized format defined in parsing_patterns.py
to eliminate duplication and ensure consistency across languages (EN/JA).
"""

from .parsing_patterns import (
    build_score_pattern,
    build_market_tier_pattern,
    build_metadata_pattern,
)

__all__ = [
    "build_score_pattern",
    "build_market_tier_pattern",
    "build_metadata_pattern",
]