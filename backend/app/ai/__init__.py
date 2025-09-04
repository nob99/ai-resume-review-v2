"""
AI Module for Resume Analysis
=============================

This module provides LangGraph-based AI orchestration for multi-agent resume analysis.
It implements a clean separation between business logic and AI processing, enabling
sophisticated multi-agent workflows while maintaining deployment simplicity.

Key Components:
- orchestrator.py: Main LangGraph workflow orchestration  
- agents/: AI agents for structure and appeal analysis
- models/: Pydantic models for state and results
- integrations/: LLM client integrations (OpenAI, Claude)
- prompts/: Prompt management and templates

Architecture Pattern: Sequential Supervisor with State Persistence
- Structure Agent → Appeal Agent → Results Aggregation
- Error handling and retry mechanisms at each step
- Industry-specific analysis with configurable prompts
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import ResumeAnalysisOrchestrator
    from .models.analysis_request import AnalysisState, AnalysisResult

__version__ = "1.0.0"
__author__ = "AI Resume Review Platform Team"