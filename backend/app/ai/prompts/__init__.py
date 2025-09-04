"""
Prompts Module
==============

This module manages AI prompts for resume analysis agents.
Prompts are stored as templates and loaded dynamically based on agent type and industry.

Features:
- Template-based prompt management
- Industry-specific prompt variations
- Dynamic prompt loading and caching
- Version tracking for prompt templates

Directory Structure:
- templates/structure/: Structure analysis prompts
- templates/appeal/: Industry-specific appeal analysis prompts
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .prompt_manager import PromptManager