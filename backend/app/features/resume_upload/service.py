"""Resume upload service with candidate-centric upload and storage."""

import io
import uuid
import logging
import hashlib
from typing import Optional, List, Dict, Any
from pathlib import Path

import PyPDF2
import docx
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.datetime_utils import utc_now
from .repository import ResumeUploadRepository
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.models.resume import Resume, ResumeStatus
from .schemas import (
    FileUploadResponse,
    UploadedFileV2,
    FileInfo,
    ProgressInfo,
    FileValidationError,
    FileType
)

logger = logging.getLogger(__name__)


class ResumeUploadService:
    """Service for handling resume uploads with candidate association and version management."""
    
    # Configuration
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MIN_FILE_SIZE = 100  # 100 bytes
    ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt'}
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    }
    
    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.session = session
        self.repository = ResumeUploadRepository(session)
        self.settings = get_settings()
    
    async def upload_resume(
        self,
        candidate_id: uuid.UUID,
        file: UploadFile,
        user_id: uuid.UUID,
        progress_callback: Optional[callable] = None
    ) -> UploadedFileV2:
        """Upload a resume for a specific candidate with version management."""
        
        file_id = str(uuid.uuid4())
        
        try:
            # Step 1: Validate file
            await self._validate_file(file)
            
            # Step 2: Read file content
            content = await file.read()
            file_size = len(content)
            
            # Step 3: Generate unique filename and hash
            file_extension = Path(file.filename).suffix.lower()
            unique_filename = f"{file_id}{file_extension}"

            # Generate file hash for deduplication
            import hashlib
            file_hash = hashlib.sha256(content).hexdigest()

            # Step 4: Extract text early (needed for database record)
            extracted_text = await self._extract_text(content, file_extension)

            # Step 5: Create database record with proper Resume model fields
            db_upload = await self.repository.create_resume(
                candidate_id=candidate_id,
                uploaded_by_user_id=user_id,
                original_filename=file.filename,
                stored_filename=unique_filename,
                file_hash=file_hash,
                file_size=file_size,
                mime_type=file.content_type or 'application/octet-stream',
                extracted_text=extracted_text
            )
            
            # Step 6: Update status to completed (text already extracted)
            await self.repository.update_status(db_upload.id, ResumeStatus.COMPLETED)
            
            # Return frontend-compatible response
            return self._to_uploaded_file_v2(db_upload, extracted_text)
            
        except Exception as e:
            logger.error(f"File upload failed for {file.filename}: {str(e)}")
            
            # Mark as error if we have a DB record
            if 'db_upload' in locals():
                await self.repository.update_status(
                    db_upload.id,
                    ResumeStatus.ERROR,
                    str(e)
                )
            
            raise HTTPException(status_code=400, detail=str(e))
    
    async def _validate_file(self, file: UploadFile) -> None:
        """Validate file before processing."""
        
        # Check filename
        if not file.filename:
            raise ValueError("File must have a filename")
        
        # Check extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type not supported. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
        
        # Check MIME type
        if file.content_type and file.content_type not in self.ALLOWED_MIME_TYPES:
            raise ValueError(f"MIME type {file.content_type} not supported")
        
        # Check file size (will check actual size after reading)
        if file.size and file.size > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size is {self.MAX_FILE_SIZE / (1024*1024)}MB")
    
    async def _validate_content(self, content: bytes) -> None:
        """Validate file content (placeholder for virus scanning)."""
        
        # Check actual size
        if len(content) > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size is {self.MAX_FILE_SIZE / (1024*1024)}MB")
        
        if len(content) < self.MIN_FILE_SIZE:
            raise ValueError(f"File too small. Minimum size is {self.MIN_FILE_SIZE} bytes")
        
        # TODO: Implement virus scanning here
        # For now, just check for suspicious patterns
        suspicious_patterns = [b'<script', b'javascript:', b'onclick=']
        content_lower = content.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                logger.warning(f"Suspicious pattern detected: {pattern}")
                # In production, might want to reject the file
    
    async def _extract_text(self, content: bytes, file_extension: str) -> str:
        """Extract text from file content."""
        
        try:
            if file_extension == '.pdf':
                return self._extract_pdf_text(content)
            elif file_extension in ['.doc', '.docx']:
                return self._extract_docx_text(content)
            elif file_extension == '.txt':
                return content.decode('utf-8', errors='ignore')
            else:
                raise ValueError(f"Text extraction not supported for {file_extension}")
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            raise ValueError(f"Failed to extract text from file: {str(e)}")
    
    def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF content."""
        text_parts = []
        
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_parts.append(page.extract_text())
            
            return '\n'.join(text_parts)
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    def _extract_docx_text(self, content: bytes) -> str:
        """Extract text from DOCX content."""
        text_parts = []
        
        try:
            doc_file = io.BytesIO(content)
            doc = docx.Document(doc_file)
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_parts.append(cell.text)
            
            return '\n'.join(text_parts)
        except Exception as e:
            logger.error(f"DOCX extraction error: {str(e)}")
            raise ValueError(f"Failed to extract text from document: {str(e)}")
    
    def _calculate_metadata(self, text: str, content: bytes) -> Dict[str, Any]:
        """Calculate metadata for the uploaded file."""
        
        # Basic text statistics
        lines = text.split('\n')
        words = text.split()
        
        return {
            "file_hash": hashlib.sha256(content).hexdigest(),
            "line_count": len(lines),
            "word_count": len(words),
            "character_count": len(text),
            "has_email": '@' in text,
            "has_phone": any(c.isdigit() for c in text) and len([c for c in text if c.isdigit()]) >= 10,
            "extraction_timestamp": utc_now().isoformat()
        }
    
    def _get_file_type(self, extension: str) -> str:
        """Get file type from extension."""
        mapping = {
            '.pdf': FileType.PDF,
            '.doc': FileType.DOC,
            '.docx': FileType.DOCX,
            '.txt': FileType.TXT
        }
        return mapping.get(extension.lower(), FileType.TXT)
    
    def _to_uploaded_file_v2(self, db_upload: Resume, extracted_text: str) -> UploadedFileV2:
        """Convert database model to frontend-compatible schema."""

        # Map MIME type to simple file type
        file_type = 'txt'
        if db_upload.mime_type:
            if 'pdf' in db_upload.mime_type:
                file_type = 'pdf'
            elif 'msword' in db_upload.mime_type or 'document' in db_upload.mime_type:
                file_type = 'docx'

        return UploadedFileV2(
            id=str(db_upload.id),
            candidate_id=str(db_upload.candidate_id),
            filename=db_upload.original_filename,
            file=FileInfo(
                name=db_upload.original_filename,
                size=db_upload.file_size,
                type=file_type,
                lastModified=int(db_upload.uploaded_at.timestamp() * 1000)
            ),
            status=db_upload.status,
            progress=db_upload.progress or (100 if db_upload.status == ResumeStatus.COMPLETED.value else 0),
            progressInfo=ProgressInfo(
                fileId=str(db_upload.id),
                fileName=db_upload.original_filename,
                stage=db_upload.status,
                percentage=db_upload.progress or (100 if db_upload.status == ResumeStatus.COMPLETED.value else 0),
                bytesUploaded=db_upload.file_size if db_upload.status == ResumeStatus.COMPLETED.value else 0,
                totalBytes=db_upload.file_size,
                timeElapsed=0,
                estimatedTimeRemaining=0,
                speed=0,
                retryCount=0,
                maxRetries=3
            ),
            extracted_text=extracted_text or db_upload.extracted_text,
            error=None,
            startTime=int(db_upload.uploaded_at.timestamp() * 1000),
            endTime=int(db_upload.processed_at.timestamp() * 1000) if db_upload.processed_at else None
        )
    
    async def get_upload(self, file_id: uuid.UUID, user_id: uuid.UUID) -> Optional[FileUploadResponse]:
        """Get a specific upload by ID."""
        
        upload = await self.repository.get_by_id(file_id)
        if not upload or upload.uploaded_by_user_id != user_id:
            return None
        
        return FileUploadResponse.from_orm(upload)
    
    async def get_user_uploads(
        self,
        user_id: uuid.UUID,
        status: Optional[ResumeStatus] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[FileUploadResponse]:
        """Get uploads for a user."""

        uploads = await self.repository.get_by_user(user_id, status, limit, offset)
        return [FileUploadResponse.from_orm(u) for u in uploads]

    async def get_candidate_resumes(
        self,
        candidate_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[UploadedFileV2]:
        """Get all resume versions for a specific candidate."""

        # TODO: Add candidate access validation
        # TODO: Query resumes by candidate_id when database model is updated
        # For now, return empty list as we can't modify database models
        logger.info(f"Getting resumes for candidate {candidate_id} by user {user_id}")
        return []
    
    async def cancel_upload(self, file_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Cancel an ongoing upload."""
        
        upload = await self.repository.get_by_id(file_id)
        if not upload or upload.uploaded_by_user_id != user_id:
            return False
        
        if upload.status in [ResumeStatus.COMPLETED, ResumeStatus.ERROR, ResumeStatus.CANCELLED]:
            return False
        
        await self.repository.mark_cancelled(file_id)
        return True
    
    async def get_upload_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get upload statistics for a user."""
        return await self.repository.get_upload_stats(user_id)