"""File upload feature module for AI Resume Review Platform."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service import FileUploadService
    from .repository import FileUploadRepository

__all__ = ["FileUploadService", "FileUploadRepository"]