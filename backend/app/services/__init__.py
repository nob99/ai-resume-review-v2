"""
Services Module
===============

Business logic services for the AI Resume Review Platform.
This module contains all business logic separated from API endpoints and AI processing.

Available Services:
- AnalysisService: Orchestrates complete resume analysis workflow
- FileService: Handles file processing and validation
- UserService: Manages user-related operations
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .analysis_service import AnalysisService