"""
AI Models Module
================

This module contains all Pydantic models used in the AI analysis workflow.

Key Models:
- AnalysisState: TypedDict for LangGraph workflow state
- StructureAnalysisResult: Output model for structure agent
- AppealAnalysisResult: Output model for appeal agent  
- CompleteAnalysisResult: Final aggregated analysis result

All models use Pydantic v2 for validation and serialization.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .analysis_request import (
        AnalysisState,
        StructureAnalysisResult,
        AppealAnalysisResult,
        CompleteAnalysisResult
    )