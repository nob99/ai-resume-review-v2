"""Resume analysis feature module for AI Resume Review Platform."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service import AnalysisService
    from .repository import AnalysisRepository

__all__ = ["AnalysisService", "AnalysisRepository"]