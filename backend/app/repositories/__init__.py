"""
Repository layer for data access abstraction.
Provides clean, testable data access patterns using SQLAlchemy ORM.
"""

from .analysis_repository import AnalysisRepository
from .base_repository import BaseRepository

__all__ = ["AnalysisRepository", "BaseRepository"]