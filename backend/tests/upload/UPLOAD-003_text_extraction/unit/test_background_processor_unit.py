"""
Unit tests for BackgroundProcessor (UPLOAD-003)

Tests background processing system functionality including:
- Job queue management and priority handling
- Concurrent processing and job lifecycle
- Error handling and retry logic
- Statistics and monitoring
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timedelta

from app.core.background_processor import (
    BackgroundProcessor,
    ProcessingJob,
    JobStatus,
    JobPriority,
    background_processor
)
from app.services.text_extraction_service import ExtractionResult, ExtractionStatus
from app.core.datetime_utils import utc_now


class TestProcessingJob:
    """Test ProcessingJob data class and methods."""
    
    def test_job_creation_with_defaults(self):
        """Test creating job with default values."""
        job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="resume.pdf",
            mime_type="application/pdf"
        )
        
        assert job.job_id is not None
        assert job.priority == JobPriority.NORMAL
        assert job.status == JobStatus.QUEUED
        assert job.timeout_seconds == 30
        assert job.max_retries == 2
        assert job.retry_count == 0
        assert job.created_at is not None
    
    def test_job_creation_with_custom_values(self):
        """Test creating job with custom values."""
        user_id = uuid4()
        upload_id = uuid4()
        
        job = ProcessingJob(
            user_id=user_id,
            upload_id=upload_id,
            file_path="/tmp/urgent.pdf",
            original_filename="important.pdf",
            mime_type="application/pdf",
            priority=JobPriority.URGENT,
            timeout_seconds=60,
            max_retries=5
        )
        
        assert job.user_id == user_id
        assert job.upload_id == upload_id
        assert job.priority == JobPriority.URGENT
        assert job.timeout_seconds == 60
        assert job.max_retries == 5
    
    def test_start_processing(self):
        """Test marking job as started."""
        job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf"
        )
        
        assert job.status == JobStatus.QUEUED
        assert job.started_at is None
        
        job.start_processing()
        
        assert job.status == JobStatus.PROCESSING
        assert job.started_at is not None
    
    def test_complete_successfully(self):
        """Test completing job successfully."""
        job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf"
        )
        
        job.start_processing()
        
        extraction_result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="Test content",
            processing_time_seconds=1.5
        )
        
        job.complete_successfully(extraction_result)
        
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.extraction_result == extraction_result
        assert job.error_message is None
    
    def test_fail_with_error(self):
        """Test marking job as failed."""
        job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf"
        )
        
        job.start_processing()
        
        error_details = {"error_type": "FileNotFoundError"}
        job.fail_with_error("File not found", error_details)
        
        assert job.status == JobStatus.FAILED
        assert job.completed_at is not None
        assert job.error_message == "File not found"
        assert job.error_details == error_details
    
    def test_should_retry_true(self):
        """Test should_retry returns True when conditions are met."""
        job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
            max_retries=3
        )
        
        job.fail_with_error("Network error")
        
        assert job.retry_count == 0
        assert job.should_retry() is True
    
    def test_should_retry_false_max_retries(self):
        """Test should_retry returns False when max retries exceeded."""
        job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
            max_retries=2
        )
        
        job.retry_count = 2
        job.fail_with_error("Network error")
        
        assert job.should_retry() is False
    
    def test_should_retry_false_timeout_error(self):
        """Test should_retry returns False for timeout errors."""
        job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf"
        )
        
        job.fail_with_error("Processing timeout exceeded")
        
        assert job.should_retry() is False
    
    def test_schedule_retry(self):
        """Test scheduling job for retry."""
        job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf"
        )
        
        job.start_processing()
        job.fail_with_error("Temporary error")
        
        original_retry_count = job.retry_count
        job.schedule_retry()
        
        assert job.status == JobStatus.QUEUED
        assert job.retry_count == original_retry_count + 1
        assert job.last_retry_at is not None
        assert job.started_at is None
        assert job.completed_at is None
    
    def test_get_processing_duration(self):
        """Test calculating processing duration."""
        job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf"
        )
        
        # No duration before processing
        assert job.get_processing_duration() is None
        
        job.start_processing()
        # Simulate processing time
        job.completed_at = job.started_at + timedelta(seconds=2.5)
        
        duration = job.get_processing_duration()
        assert duration == 2.5
    
    def test_get_priority_score(self):
        """Test priority score calculation."""
        job_low = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
            priority=JobPriority.LOW
        )
        
        job_urgent = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
            priority=JobPriority.URGENT
        )
        
        assert job_urgent.get_priority_score() > job_low.get_priority_score()
    
    def test_to_dict(self):
        """Test converting job to dictionary."""
        user_id = uuid4()
        upload_id = uuid4()
        
        job = ProcessingJob(
            user_id=user_id,
            upload_id=upload_id,
            file_path="/tmp/test.pdf",
            original_filename="resume.pdf",
            mime_type="application/pdf"
        )
        
        job_dict = job.to_dict()
        
        assert job_dict["job_id"] == str(job.job_id)
        assert job_dict["user_id"] == str(user_id)
        assert job_dict["upload_id"] == str(upload_id)
        assert job_dict["original_filename"] == "resume.pdf"
        assert job_dict["priority"] == "normal"
        assert job_dict["status"] == "queued"


class TestBackgroundProcessor:
    """Test BackgroundProcessor functionality."""
    
    @pytest.fixture
    def processor(self):
        """Create BackgroundProcessor instance for testing."""
        return BackgroundProcessor(max_concurrent_jobs=2, cleanup_interval_minutes=1)
    
    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.max_concurrent_jobs == 2
        assert processor.cleanup_interval_minutes == 1
        assert not processor._is_running
        assert len(processor._job_queue) == 0
        assert len(processor._active_jobs) == 0
        assert len(processor._completed_jobs) == 0
    
    def test_submit_job(self, processor):
        """Test submitting job to queue."""
        user_id = uuid4()
        upload_id = uuid4()
        
        job_id = processor.submit_job(
            user_id=user_id,
            upload_id=upload_id,
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
            priority=JobPriority.HIGH
        )
        
        assert isinstance(job_id, UUID)
        assert len(processor._job_queue) == 1
        
        job = processor._job_queue[0]
        assert job.job_id == job_id
        assert job.user_id == user_id
        assert job.upload_id == upload_id
        assert job.priority == JobPriority.HIGH
    
    def test_submit_multiple_jobs_priority_order(self, processor):
        """Test submitting multiple jobs maintains priority order."""
        user_id = uuid4()
        
        # Submit jobs in mixed priority order
        job_normal = processor.submit_job(
            user_id=user_id,
            upload_id=uuid4(),
            file_path="/tmp/normal.pdf",
            original_filename="normal.pdf",
            mime_type="application/pdf",
            priority=JobPriority.NORMAL
        )
        
        job_urgent = processor.submit_job(
            user_id=user_id,
            upload_id=uuid4(),
            file_path="/tmp/urgent.pdf",
            original_filename="urgent.pdf",
            mime_type="application/pdf",
            priority=JobPriority.URGENT
        )
        
        job_low = processor.submit_job(
            user_id=user_id,
            upload_id=uuid4(),
            file_path="/tmp/low.pdf",
            original_filename="low.pdf",
            mime_type="application/pdf",
            priority=JobPriority.LOW
        )
        
        # Queue should be ordered by priority: URGENT, NORMAL, LOW
        assert len(processor._job_queue) == 3
        assert processor._job_queue[0].job_id == job_urgent
        assert processor._job_queue[1].job_id == job_normal
        assert processor._job_queue[2].job_id == job_low
    
    def test_get_job_status_queued(self, processor):
        """Test getting status of queued job."""
        user_id = uuid4()
        upload_id = uuid4()
        
        job_id = processor.submit_job(
            user_id=user_id,
            upload_id=upload_id,
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf"
        )
        
        job = processor.get_job_status(job_id)
        
        assert job is not None
        assert job.job_id == job_id
        assert job.status == JobStatus.QUEUED
    
    def test_get_job_status_not_found(self, processor):
        """Test getting status of non-existent job."""
        non_existent_id = uuid4()
        
        job = processor.get_job_status(non_existent_id)
        
        assert job is None
    
    def test_cancel_queued_job(self, processor):
        """Test cancelling a queued job."""
        user_id = uuid4()
        upload_id = uuid4()
        
        job_id = processor.submit_job(
            user_id=user_id,
            upload_id=upload_id,
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf"
        )
        
        success = processor.cancel_job(job_id)
        
        assert success is True
        assert len(processor._job_queue) == 0
        assert job_id in processor._completed_jobs
        assert processor._completed_jobs[job_id].status == JobStatus.CANCELLED
    
    def test_cancel_non_existent_job(self, processor):
        """Test cancelling non-existent job."""
        non_existent_id = uuid4()
        
        success = processor.cancel_job(non_existent_id)
        
        assert success is False
    
    def test_get_queue_stats(self, processor):
        """Test getting queue statistics."""
        user_id = uuid4()
        
        # Add jobs with different priorities
        processor.submit_job(
            user_id=user_id,
            upload_id=uuid4(),
            file_path="/tmp/urgent.pdf",
            original_filename="urgent.pdf",
            mime_type="application/pdf",
            priority=JobPriority.URGENT
        )
        
        processor.submit_job(
            user_id=user_id,
            upload_id=uuid4(),
            file_path="/tmp/normal.pdf",
            original_filename="normal.pdf",
            mime_type="application/pdf",
            priority=JobPriority.NORMAL
        )
        
        stats = processor.get_queue_stats()
        
        assert stats["queue_size"] == 2
        assert stats["active_jobs"] == 0
        assert stats["completed_jobs"] == 0
        assert stats["queue_by_priority"]["urgent"] == 1
        assert stats["queue_by_priority"]["normal"] == 1
        assert stats["max_concurrent_jobs"] == 2
        assert stats["is_running"] is False
    
    def test_add_callback(self, processor):
        """Test adding event callbacks."""
        callback_calls = []
        
        async def test_callback(job):
            callback_calls.append(f"job_started:{job.job_id}")
        
        processor.add_callback("on_job_started", test_callback)
        
        assert len(processor._job_callbacks["on_job_started"]) == 1
    
    @pytest.mark.asyncio
    async def test_trigger_callbacks(self, processor):
        """Test triggering event callbacks."""
        callback_calls = []
        
        async def test_callback(job):
            callback_calls.append(job.job_id)
        
        processor.add_callback("on_job_started", test_callback)
        
        test_job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf"
        )
        
        await processor._trigger_callbacks("on_job_started", test_job)
        
        assert len(callback_calls) == 1
        assert callback_calls[0] == test_job.job_id
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, processor):
        """Test starting and stopping processor."""
        assert not processor._is_running
        
        # Start processor
        await processor.start()
        
        assert processor._is_running
        assert processor._processor_task is not None
        assert processor._cleanup_task is not None
        
        # Stop processor
        await processor.stop()
        
        assert not processor._is_running
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, processor, caplog):
        """Test starting processor when already running."""
        await processor.start()
        
        # Try to start again
        await processor.start()
        
        assert "already running" in caplog.text
        
        await processor.stop()
    
    @pytest.mark.asyncio
    @patch('app.core.background_processor.text_extraction_service')
    @patch('app.core.background_processor.text_processor')
    @patch('app.core.background_processor.get_file_info')
    @patch('pathlib.Path.exists')
    async def test_process_single_job_success(self, mock_exists, mock_get_file_info, 
                                            mock_text_processor, mock_extraction_service, processor):
        """Test successful processing of single job."""
        # Setup mocks
        mock_exists.return_value = True
        mock_get_file_info.return_value = Mock()
        
        mock_extraction_result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="Test resume content",
            processing_time_seconds=1.0,
            metadata={}
        )
        mock_extraction_service.extract_text_from_file.return_value = mock_extraction_result
        
        mock_processed_text = Mock()
        mock_processed_text.cleaned_text = "Cleaned resume content"
        mock_processed_text.sections = []
        mock_processed_text.word_count = 3
        mock_processed_text.line_count = 1
        mock_processed_text.metadata = {}
        mock_text_processor.process_text.return_value = mock_processed_text
        mock_text_processor.get_ai_ready_format.return_value = {"ai": "data"}
        
        # Create test job
        test_job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf"
        )
        
        # Process job
        await processor._process_single_job(test_job)
        
        # Verify job completed successfully
        assert test_job.status == JobStatus.COMPLETED
        assert test_job.extraction_result is not None
        assert test_job.extraction_result.status == ExtractionStatus.COMPLETED
        assert test_job.error_message is None
    
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    async def test_process_single_job_file_not_found(self, mock_exists, processor):
        """Test processing job when file doesn't exist."""
        mock_exists.return_value = False
        
        test_job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/nonexistent.pdf",
            original_filename="nonexistent.pdf",
            mime_type="application/pdf"
        )
        
        await processor._process_single_job(test_job)
        
        assert test_job.status == JobStatus.FAILED
        assert "File not found" in test_job.error_message
    
    @pytest.mark.asyncio
    @patch('app.core.background_processor.text_extraction_service')
    @patch('app.core.background_processor.get_file_info')
    @patch('pathlib.Path.exists')
    async def test_process_single_job_extraction_failed(self, mock_exists, mock_get_file_info,
                                                       mock_extraction_service, processor):
        """Test processing job when extraction fails."""
        # Setup mocks
        mock_exists.return_value = True
        mock_get_file_info.return_value = Mock()
        
        mock_extraction_result = ExtractionResult(
            status=ExtractionStatus.FAILED,
            error_message="PDF extraction failed"
        )
        mock_extraction_service.extract_text_from_file.return_value = mock_extraction_result
        
        test_job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/corrupted.pdf",
            original_filename="corrupted.pdf",
            mime_type="application/pdf"
        )
        
        await processor._process_single_job(test_job)
        
        assert test_job.status == JobStatus.FAILED
        assert test_job.error_message == "PDF extraction failed"
    
    @pytest.mark.asyncio
    @patch('app.core.background_processor.text_extraction_service')
    @patch('app.core.background_processor.get_file_info')
    @patch('pathlib.Path.exists')
    async def test_process_single_job_with_retry(self, mock_exists, mock_get_file_info,
                                               mock_extraction_service, processor):
        """Test job retry logic."""
        # Setup mocks
        mock_exists.return_value = True
        mock_get_file_info.return_value = Mock()
        
        mock_extraction_result = ExtractionResult(
            status=ExtractionStatus.FAILED,
            error_message="Network error"
        )
        mock_extraction_service.extract_text_from_file.return_value = mock_extraction_result
        
        test_job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
            max_retries=2
        )
        
        # Add job to processor for retry queue
        processor._active_jobs[test_job.job_id] = test_job
        
        await processor._process_single_job(test_job)
        
        # Job should be marked for retry initially
        assert test_job.status == JobStatus.QUEUED  # Scheduled for retry
        assert test_job.retry_count == 1
    
    @pytest.mark.asyncio
    async def test_process_single_job_timeout(self, processor):
        """Test job timeout handling."""
        test_job = ProcessingJob(
            user_id=uuid4(),
            upload_id=uuid4(),
            file_path="/tmp/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
            timeout_seconds=1
        )
        
        # Mock a slow operation that will timeout
        with patch('pathlib.Path.exists', return_value=True):
            with patch('app.core.background_processor.get_file_info'):
                with patch('app.core.background_processor.text_extraction_service.extract_text_from_file') as mock_extract:
                    async def slow_extraction(*args, **kwargs):
                        await asyncio.sleep(2)  # Longer than timeout
                        return ExtractionResult(status=ExtractionStatus.COMPLETED)
                    
                    mock_extract.side_effect = slow_extraction
                    
                    await processor._process_single_job(test_job)
        
        assert test_job.status == JobStatus.FAILED
        assert "timeout" in test_job.error_message.lower()


class TestGlobalProcessorInstance:
    """Test the global background_processor instance."""
    
    def test_global_processor_exists(self):
        """Test that global processor instance exists."""
        assert background_processor is not None
        assert isinstance(background_processor, BackgroundProcessor)
    
    def test_global_processor_configuration(self):
        """Test global processor configuration."""
        assert background_processor.max_concurrent_jobs == 3
        assert background_processor.cleanup_interval_minutes == 60


@pytest.mark.integration
class TestBackgroundProcessorIntegration:
    """Integration tests for BackgroundProcessor with realistic scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_job_lifecycle(self):
        """Test complete job lifecycle from submission to completion."""
        processor = BackgroundProcessor(max_concurrent_jobs=1, cleanup_interval_minutes=1)
        
        try:
            user_id = uuid4()
            upload_id = uuid4()
            
            # Mock successful processing
            with patch('pathlib.Path.exists', return_value=True):
                with patch('app.core.background_processor.get_file_info'):
                    with patch('app.core.background_processor.text_extraction_service.extract_text_from_file') as mock_extract:
                        with patch('app.core.background_processor.text_processor.process_text'):
                            with patch('app.core.background_processor.text_processor.get_ai_ready_format'):
                                
                                mock_extract.return_value = ExtractionResult(
                                    status=ExtractionStatus.COMPLETED,
                                    extracted_text="Test content",
                                    processing_time_seconds=0.1,
                                    metadata={}
                                )
                                
                                # Start processor
                                await processor.start()
                                
                                # Submit job
                                job_id = processor.submit_job(
                                    user_id=user_id,
                                    upload_id=upload_id,
                                    file_path="/tmp/test.pdf",
                                    original_filename="test.pdf",
                                    mime_type="application/pdf"
                                )
                                
                                # Wait for processing
                                await asyncio.sleep(0.5)
                                
                                # Check job completed
                                job = processor.get_job_status(job_id)
                                assert job is not None
                                assert job.status in [JobStatus.COMPLETED, JobStatus.PROCESSING]  # May still be processing
                                
                                # Wait a bit more for completion
                                await asyncio.sleep(0.5)
                                job = processor.get_job_status(job_id)
                                
                                if job.status == JobStatus.COMPLETED:
                                    assert job.extraction_result is not None
                                    assert job.extraction_result.extracted_text == "Test content"
        
        finally:
            await processor.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])