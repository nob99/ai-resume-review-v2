"""AI Agents Prompts Module.

This module contains prompt templates for AI agents, organized by agent type.

Directory Structure:
- appeal/ - Industry-specific appeal analysis prompts
- structure/ - Resume structure analysis prompts
- summary/ - Summary generation templates

Naming Convention:
{agent_type}_prompt_{version}_{lang}.yaml

Examples:
- appeal/appeal_prompt_v1.0_ja.yaml
- structure/structure_prompt_v1.1_en.yaml
- summary/summary_templates_v1.0_ja.yaml

The prompt templates include:
- System and user prompt text
- Parsing configuration (regex patterns for extracting scores and feedback)
- Metadata about the agent type and version

Language support: English (en) and Japanese (ja)
Version control: v1.0 (stable), v1.1 (enhanced feedback), etc.
"""

__all__ = []
