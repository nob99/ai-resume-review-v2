"""
Background Processing System for UPLOAD-003

Implements asynchronous task queue for text extraction processing.
Handles concurrent processing, progress tracking, and job management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from uuid import UUID, uuid4
import traceback
import json
from pathlib import Path

from app.core.datetime_utils import utc_now
from app.services.text_extraction_service import text_extraction_service, ExtractionStatus, ExtractionResult
from app.core.text_processor import text_processor
from app.core.file_validation import get_file_info


class JobStatus(str, Enum):
    """Status of background processing job."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class JobPriority(str, Enum):
    """Priority levels for background jobs."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ProcessingJob:
    """Background processing job for text extraction."""
    job_id: UUID = field(default_factory=uuid4)
    user_id: UUID = None
    upload_id: UUID = None
    file_path: str = ""
    original_filename: str = ""
    mime_type: str = ""
    
    # Job configuration
    priority: JobPriority = JobPriority.NORMAL
    timeout_seconds: int = 30
    max_retries: int = 2
    retry_delay_seconds: int = 5
    
    # Job status
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Processing results
    extraction_result: Optional[ExtractionResult] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Retry tracking
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize job after creation."""
        if not self.job_id:
            self.job_id = uuid4()
        if not self.created_at:
            self.created_at = utc_now()
    
    def start_processing(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.PROCESSING
        self.started_at = utc_now()
    
    def complete_successfully(self, extraction_result: ExtractionResult) -> None:
        """Mark job as completed successfully."""
        self.status = JobStatus.COMPLETED
        self.completed_at = utc_now()
        self.extraction_result = extraction_result
        self.error_message = None
        self.error_details = None
    
    def fail_with_error(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.completed_at = utc_now()
        self.error_message = error_message
        self.error_details = error_details
    
    def should_retry(self) -> bool:
        """Check if job should be retried."""
        return (self.status == JobStatus.FAILED and 
                self.retry_count < self.max_retries and
                self.error_message and 
                "timeout" not in self.error_message.lower())
    
    def schedule_retry(self) -> None:
        """Schedule job for retry."""
        if self.should_retry():
            self.retry_count += 1
            self.last_retry_at = utc_now()
            self.status = JobStatus.QUEUED
            self.started_at = None
            self.completed_at = None
    
    def get_processing_duration(self) -> Optional[float]:
        """Get processing duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def get_priority_score(self) -> int:
        """Get numeric priority score for sorting."""
        priority_scores = {
            JobPriority.URGENT: 4,
            JobPriority.HIGH: 3,
            JobPriority.NORMAL: 2,
            JobPriority.LOW: 1
        }
        return priority_scores.get(self.priority, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "job_id": str(self.job_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "upload_id": str(self.upload_id) if self.upload_id else None,
            "file_path": self.file_path,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "processing_duration_seconds": self.get_processing_duration()
        }


class BackgroundProcessor:
    """
    Background processing system for text extraction jobs.
    
    Manages a queue of text extraction jobs with priority handling,
    concurrent processing, and automatic retry logic.
    """
    
    def __init__(self, max_concurrent_jobs: int = 3, cleanup_interval_minutes: int = 60):
        """
        Initialize background processor.
        
        Args:
            max_concurrent_jobs: Maximum number of concurrent processing jobs
            cleanup_interval_minutes: Interval for cleaning up old jobs
        """
        self.logger = logging.getLogger(__name__)
        self.max_concurrent_jobs = max_concurrent_jobs
        self.cleanup_interval_minutes = cleanup_interval_minutes
        
        # Job storage
        self._job_queue: List[ProcessingJob] = []
        self._active_jobs: Dict[UUID, ProcessingJob] = {}
        self._completed_jobs: Dict[UUID, ProcessingJob] = {}
        
        # Processing state
        self._is_running = False
        self._processor_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._stats = {
            "jobs_processed": 0,
            "jobs_succeeded": 0,
            "jobs_failed": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "started_at": utc_now().isoformat()
        }
        
        # Job callbacks
        self._job_callbacks: Dict[str, List[Callable[[ProcessingJob], Awaitable[None]]]] = {
            "on_job_started": [],
            "on_job_completed": [],
            "on_job_failed": []
        }
    
    def add_callback(self, event: str, callback: Callable[[ProcessingJob], Awaitable[None]]) -> None:
        """Add callback for job events."""
        if event in self._job_callbacks:
            self._job_callbacks[event].append(callback)
    
    async def _trigger_callbacks(self, event: str, job: ProcessingJob) -> None:
        """Trigger callbacks for job event."""
        for callback in self._job_callbacks.get(event, []):
            try:
                await callback(job)
            except Exception as e:
                self.logger.error(f"Callback error for {event}: {str(e)}")
    
    async def start(self) -> None:
        """Start the background processor."""
        if self._is_running:
            self.logger.warning("Background processor is already running")
            return
        
        self._is_running = True
        self.logger.info(f"Starting background processor with {self.max_concurrent_jobs} concurrent jobs")
        
        # Start processor and cleanup tasks
        self._processor_task = asyncio.create_task(self._process_jobs())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_jobs())
    
    async def stop(self) -> None:
        """Stop the background processor."""
        if not self._is_running:
            return
        
        self.logger.info("Stopping background processor...")
        self._is_running = False
        
        # Cancel tasks
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Wait for active jobs to complete (with timeout)
        if self._active_jobs:
            self.logger.info(f"Waiting for {len(self._active_jobs)} active jobs to complete...")
            await asyncio.sleep(2)  # Give jobs time to finish
        
        self.logger.info("Background processor stopped")
    
    def submit_job(
        self,
        user_id: UUID,
        upload_id: UUID,
        file_path: str,
        original_filename: str,
        mime_type: str,
        priority: JobPriority = JobPriority.NORMAL,
        timeout_seconds: int = 30
    ) -> UUID:
        """
        Submit a new text extraction job to the queue.
        
        Args:
            user_id: User ID who owns the upload
            upload_id: Upload ID to process
            file_path: Path to the file to process
            original_filename: Original filename
            mime_type: File MIME type
            priority: Job priority level
            timeout_seconds: Processing timeout
            
        Returns:
            Job ID for tracking
        """
        job = ProcessingJob(
            user_id=user_id,
            upload_id=upload_id,
            file_path=file_path,
            original_filename=original_filename,
            mime_type=mime_type,
            priority=priority,
            timeout_seconds=timeout_seconds
        )
        
        # Add to queue in priority order
        self._insert_job_by_priority(job)
        
        self.logger.info(f"Submitted job {job.job_id} for upload {upload_id} "
                        f"(priority: {priority.value}, queue size: {len(self._job_queue)})")
        
        return job.job_id
    
    def _insert_job_by_priority(self, job: ProcessingJob) -> None:
        """Insert job into queue by priority."""
        inserted = False
        for i, existing_job in enumerate(self._job_queue):
            if job.get_priority_score() > existing_job.get_priority_score():
                self._job_queue.insert(i, job)
                inserted = True
                break
        
        if not inserted:
            self._job_queue.append(job)
    
    def get_job_status(self, job_id: UUID) -> Optional[ProcessingJob]:
        """Get status of a specific job."""
        # Check active jobs
        if job_id in self._active_jobs:
            return self._active_jobs[job_id]
        
        # Check completed jobs
        if job_id in self._completed_jobs:
            return self._completed_jobs[job_id]
        
        # Check queued jobs
        for job in self._job_queue:
            if job.job_id == job_id:
                return job
        
        return None
    
    def cancel_job(self, job_id: UUID) -> bool:
        """Cancel a queued job."""
        # Remove from queue if not started
        for i, job in enumerate(self._job_queue):
            if job.job_id == job_id:
                job.status = JobStatus.CANCELLED
                job.completed_at = utc_now()
                self._job_queue.pop(i)
                self._completed_jobs[job_id] = job
                self.logger.info(f"Cancelled job {job_id}")
                return True
        
        return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue and processing statistics."""
        queue_by_priority = {}
        for job in self._job_queue:
            priority = job.priority.value
            queue_by_priority[priority] = queue_by_priority.get(priority, 0) + 1
        
        active_jobs_info = []
        for job in self._active_jobs.values():
            duration = None
            if job.started_at:
                duration = (utc_now() - job.started_at).total_seconds()
            
            active_jobs_info.append({
                "job_id": str(job.job_id),
                "upload_id": str(job.upload_id),
                "filename": job.original_filename,
                "priority": job.priority.value,
                "duration_seconds": duration
            })
        
        return {
            "queue_size": len(self._job_queue),
            "active_jobs": len(self._active_jobs),
            "completed_jobs": len(self._completed_jobs),
            "queue_by_priority": queue_by_priority,
            "active_jobs_info": active_jobs_info,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "is_running": self._is_running,
            "stats": self._stats
        }
    
    async def _process_jobs(self) -> None:
        """Main job processing loop."""
        self.logger.info("Job processor started")
        
        while self._is_running:
            try:
                # Start new jobs if slots available
                while (len(self._active_jobs) < self.max_concurrent_jobs and 
                       self._job_queue and self._is_running):
                    
                    job = self._job_queue.pop(0)
                    self._active_jobs[job.job_id] = job
                    
                    # Start job processing
                    asyncio.create_task(self._process_single_job(job))
                
                # Wait before next iteration
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error in job processing loop: {str(e)}")
                await asyncio.sleep(1)
    
    async def _process_single_job(self, job: ProcessingJob) -> None:
        """Process a single text extraction job."""
        try:
            job.start_processing()
            await self._trigger_callbacks("on_job_started", job)
            
            self.logger.info(f"Processing job {job.job_id} for upload {job.upload_id}")
            
            # Get file info
            file_path_obj = Path(job.file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {job.file_path}")
            
            file_info = get_file_info(file_path_obj, job.original_filename)
            
            # Extract text with timeout
            extraction_result = await text_extraction_service.extract_text_from_file(
                file_path_obj,
                file_info,
                timeout_seconds=job.timeout_seconds
            )
            
            if extraction_result.is_success:
                # Process extracted text
                processed_text = text_processor.process_text(extraction_result.extracted_text)
                
                # Generate AI-ready data
                ai_ready_data = text_processor.get_ai_ready_format(processed_text)
                
                # Update extraction result with processed data
                extraction_result.metadata.update({
                    "processed_text": processed_text.cleaned_text,
                    "ai_ready_data": ai_ready_data,
                    "sections_detected": len(processed_text.sections),
                    "word_count": processed_text.word_count,
                    "line_count": processed_text.line_count
                })
                
                job.complete_successfully(extraction_result)
                await self._trigger_callbacks("on_job_completed", job)
                
                # Update stats
                self._stats["jobs_succeeded"] += 1
                
                self.logger.info(f"Job {job.job_id} completed successfully: "
                                f"{processed_text.word_count} words, "
                                f"{len(processed_text.sections)} sections")
            else:
                # Extraction failed
                error_details = {
                    "extraction_status": extraction_result.status.value,
                    "processing_time": extraction_result.processing_time_seconds,
                    "file_path": job.file_path,
                    "mime_type": job.mime_type
                }
                
                job.fail_with_error(extraction_result.error_message, error_details)
                await self._trigger_callbacks("on_job_failed", job)
                
                self._stats["jobs_failed"] += 1
                
                # Check if should retry
                if job.should_retry():
                    self.logger.warning(f"Job {job.job_id} failed, scheduling retry "
                                       f"({job.retry_count}/{job.max_retries})")
                    job.schedule_retry()
                    # Add back to queue
                    await asyncio.sleep(job.retry_delay_seconds)
                    if self._is_running:
                        self._insert_job_by_priority(job)
                else:
                    self.logger.error(f"Job {job.job_id} failed permanently: {job.error_message}")
            
        except asyncio.TimeoutError:
            job.fail_with_error("Processing timeout exceeded")
            await self._trigger_callbacks("on_job_failed", job)
            self._stats["jobs_failed"] += 1
            self.logger.error(f"Job {job.job_id} timed out")
            
        except Exception as e:
            error_details = {
                "exception_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "file_path": job.file_path
            }
            
            job.fail_with_error(f"Processing error: {str(e)}", error_details)
            await self._trigger_callbacks("on_job_failed", job)
            self._stats["jobs_failed"] += 1
            
            self.logger.error(f"Job {job.job_id} failed with error: {str(e)}")
            
        finally:
            # Move job from active to completed
            if job.job_id in self._active_jobs:
                del self._active_jobs[job.job_id]
            self._completed_jobs[job.job_id] = job
            
            # Update processing stats
            self._stats["jobs_processed"] += 1
            
            if job.get_processing_duration():
                self._stats["total_processing_time"] += job.get_processing_duration()
                self._stats["average_processing_time"] = (
                    self._stats["total_processing_time"] / self._stats["jobs_processed"]
                )
    
    async def _cleanup_old_jobs(self) -> None:
        """Clean up old completed jobs to prevent memory leaks."""
        while self._is_running:
            try:
                # Wait for cleanup interval
                await asyncio.sleep(self.cleanup_interval_minutes * 60)
                
                if not self._is_running:
                    break
                
                # Remove completed jobs older than 24 hours
                cutoff_time = utc_now() - timedelta(hours=24)
                jobs_to_remove = []
                
                for job_id, job in self._completed_jobs.items():
                    if job.completed_at and job.completed_at < cutoff_time:
                        jobs_to_remove.append(job_id)
                
                for job_id in jobs_to_remove:
                    del self._completed_jobs[job_id]
                
                if jobs_to_remove:
                    self.logger.info(f"Cleaned up {len(jobs_to_remove)} old completed jobs")
                
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying


# Global background processor instance
background_processor = BackgroundProcessor(
    max_concurrent_jobs=3,  # Process up to 3 files concurrently
    cleanup_interval_minutes=60  # Clean up old jobs every hour
)