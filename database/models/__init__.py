"""
Unified database models for AI Resume Review Platform.

This module provides a single source of truth for all SQLAlchemy models,
ensuring consistent database schema and eliminating conflicts between
multiple declarative bases.
"""

from sqlalchemy.orm import declarative_base

# Single source of truth for all database models
Base = declarative_base()

# Import all models to ensure they're registered with the Base
# This must be done after Base is created to avoid circular imports
from .auth import User, RefreshToken
from .files import FileUpload
from .analysis import ResumeAnalysis

# Export all models for easy importing
__all__ = [
    "Base",
    "User", 
    "RefreshToken",
    "FileUpload",
    "ResumeAnalysis",
]