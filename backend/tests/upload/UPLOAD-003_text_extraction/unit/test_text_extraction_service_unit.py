"""
Unit tests for TextExtractionService (UPLOAD-003)

Tests the core text extraction functionality including:
- PDF text extraction with multiple libraries
- DOCX document processing
- Error handling and edge cases
- Performance and timeout handling
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, mock_open
from io import BytesIO

from app.services.text_extraction_service import (
    TextExtractionService,
    PDFTextExtractor,
    DocxTextExtractor,
    DocTextExtractor,
    ExtractionStatus,
    ExtractionResult,
    text_extraction_service
)
from app.core.file_validation import FileInfo


class TestPDFTextExtractor:
    """Test PDF text extraction functionality."""
    
    def test_supports_pdf_file_type(self):
        """Test PDF file type support detection."""
        extractor = PDFTextExtractor()
        
        # Test PDF support
        pdf_file_info = FileInfo(
            file_type="application/pdf",
            file_size=1000,
            is_valid=True
        )
        assert extractor.supports_file_type(pdf_file_info)
        
        # Test non-PDF files are not supported
        docx_file_info = FileInfo(
            file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=1000,
            is_valid=True
        )
        assert not extractor.supports_file_type(docx_file_info)
    
    @patch('app.services.text_extraction_service.pdfplumber.open')
    def test_pdf_extraction_with_pdfplumber_success(self, mock_pdfplumber_open):
        """Test successful PDF extraction using pdfplumber."""
        # Mock pdfplumber response
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample resume text from page 1"
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        
        mock_pdfplumber_open.return_value = mock_pdf
        
        extractor = PDFTextExtractor()
        test_file = Path("/tmp/test.pdf")
        
        result = extractor.extract_text(test_file)
        
        assert result.status == ExtractionStatus.COMPLETED
        assert "Sample resume text from page 1" in result.extracted_text
        assert result.metadata["extraction_method"] == "pdfplumber"
        assert result.metadata["file_type"] == "pdf"
        assert result.processing_time_seconds is not None
    
    @patch('app.services.text_extraction_service.pdfplumber.open')
    @patch('app.services.text_extraction_service.PyPDF2.PdfReader')
    def test_pdf_extraction_fallback_to_pypdf2(self, mock_pypdf2_reader, mock_pdfplumber_open):
        """Test PDF extraction fallback to PyPDF2 when pdfplumber fails."""
        # Mock pdfplumber to return empty text
        mock_page = Mock()
        mock_page.extract_text.return_value = ""
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        
        mock_pdfplumber_open.return_value = mock_pdf
        
        # Mock PyPDF2 to return text
        mock_pypdf2_page = Mock()
        mock_pypdf2_page.extract_text.return_value = "Fallback text from PyPDF2"
        
        mock_reader = Mock()
        mock_reader.pages = [mock_pypdf2_page]
        mock_pypdf2_reader.return_value = mock_reader
        
        extractor = PDFTextExtractor()
        test_file = Path("/tmp/test.pdf")
        
        with patch('builtins.open', mock_open(read_data=b"mock pdf content")):
            result = extractor.extract_text(test_file)
        
        assert result.status == ExtractionStatus.COMPLETED
        assert "Fallback text from PyPDF2" in result.extracted_text
        assert result.metadata["extraction_method"] == "pypdf2"
    
    @patch('app.services.text_extraction_service.pdfplumber.open')
    @patch('app.services.text_extraction_service.PyPDF2.PdfReader')
    def test_pdf_extraction_no_text_found(self, mock_pypdf2_reader, mock_pdfplumber_open):
        """Test PDF extraction when no text is found."""
        # Mock both libraries to return empty text
        mock_pdfplumber_page = Mock()
        mock_pdfplumber_page.extract_text.return_value = ""
        
        mock_pdfplumber_pdf = Mock()
        mock_pdfplumber_pdf.pages = [mock_pdfplumber_page]
        mock_pdfplumber_pdf.__enter__ = Mock(return_value=mock_pdfplumber_pdf)
        mock_pdfplumber_pdf.__exit__ = Mock(return_value=None)
        
        mock_pdfplumber_open.return_value = mock_pdfplumber_pdf
        
        mock_pypdf2_page = Mock()
        mock_pypdf2_page.extract_text.return_value = ""
        
        mock_reader = Mock()
        mock_reader.pages = [mock_pypdf2_page]
        mock_pypdf2_reader.return_value = mock_reader
        
        extractor = PDFTextExtractor()
        test_file = Path("/tmp/test.pdf")
        
        with patch('builtins.open', mock_open(read_data=b"mock pdf content")):
            result = extractor.extract_text(test_file)
        
        assert result.status == ExtractionStatus.FAILED
        assert "No extractable text found" in result.error_message
    
    @patch('app.services.text_extraction_service.pdfplumber.open')
    def test_pdf_extraction_exception_handling(self, mock_pdfplumber_open):
        """Test PDF extraction exception handling."""
        mock_pdfplumber_open.side_effect = Exception("PDF parsing error")
        
        extractor = PDFTextExtractor()
        test_file = Path("/tmp/test.pdf")
        
        result = extractor.extract_text(test_file)
        
        assert result.status == ExtractionStatus.FAILED
        assert "PDF extraction error" in result.error_message
        assert result.processing_time_seconds is not None


class TestDocxTextExtractor:
    """Test DOCX text extraction functionality."""
    
    def test_supports_docx_file_type(self):
        """Test DOCX file type support detection."""
        extractor = DocxTextExtractor()
        
        # Test DOCX support
        docx_file_info = FileInfo(
            file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=1000,
            is_valid=True
        )
        assert extractor.supports_file_type(docx_file_info)
        
        # Test non-DOCX files are not supported
        pdf_file_info = FileInfo(
            file_type="application/pdf",
            file_size=1000,
            is_valid=True
        )
        assert not extractor.supports_file_type(pdf_file_info)
    
    @patch('app.services.text_extraction_service.DocxDocument')
    def test_docx_extraction_success(self, mock_docx_document):
        """Test successful DOCX extraction."""
        # Mock paragraphs
        mock_paragraph1 = Mock()
        mock_paragraph1.text = "John Doe"
        mock_paragraph2 = Mock()
        mock_paragraph2.text = "Software Engineer with 5 years experience"
        
        # Mock table
        mock_cell = Mock()
        mock_cell.text = "Python"
        mock_row = Mock()
        mock_row.cells = [mock_cell]
        mock_table = Mock()
        mock_table.rows = [mock_row]
        
        # Mock document
        mock_document = Mock()
        mock_document.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_document.tables = [mock_table]
        
        mock_docx_document.return_value = mock_document
        
        extractor = DocxTextExtractor()
        test_file = Path("/tmp/test.docx")
        
        result = extractor.extract_text(test_file)
        
        assert result.status == ExtractionStatus.COMPLETED
        assert "John Doe" in result.extracted_text
        assert "Software Engineer" in result.extracted_text
        assert "Python" in result.extracted_text
        assert result.metadata["extraction_method"] == "python-docx"
        assert result.metadata["paragraph_count"] == 2
        assert result.metadata["table_count"] == 1
    
    @patch('app.services.text_extraction_service.DocxDocument')
    def test_docx_extraction_empty_document(self, mock_docx_document):
        """Test DOCX extraction with empty document."""
        mock_document = Mock()
        mock_document.paragraphs = []
        mock_document.tables = []
        
        mock_docx_document.return_value = mock_document
        
        extractor = DocxTextExtractor()
        test_file = Path("/tmp/empty.docx")
        
        result = extractor.extract_text(test_file)
        
        assert result.status == ExtractionStatus.FAILED
        assert "No text content found" in result.error_message
    
    @patch('app.services.text_extraction_service.DocxDocument')
    def test_docx_extraction_exception_handling(self, mock_docx_document):
        """Test DOCX extraction exception handling."""
        mock_docx_document.side_effect = Exception("Corrupted DOCX file")
        
        extractor = DocxTextExtractor()
        test_file = Path("/tmp/corrupted.docx")
        
        result = extractor.extract_text(test_file)
        
        assert result.status == ExtractionStatus.FAILED
        assert "DOCX extraction error" in result.error_message


class TestDocTextExtractor:
    """Test DOC text extraction functionality."""
    
    def test_supports_doc_file_type(self):
        """Test DOC file type support detection."""
        extractor = DocTextExtractor()
        
        # Test DOC support
        doc_file_info = FileInfo(
            file_type="application/msword",
            file_size=1000,
            is_valid=True
        )
        assert extractor.supports_file_type(doc_file_info)
    
    def test_doc_extraction_not_supported(self):
        """Test DOC extraction returns not supported message."""
        extractor = DocTextExtractor()
        test_file = Path("/tmp/test.doc")
        
        result = extractor.extract_text(test_file)
        
        assert result.status == ExtractionStatus.FAILED
        assert "DOC file format not fully supported" in result.error_message


class TestTextExtractionService:
    """Test the main TextExtractionService."""
    
    @pytest.fixture
    def service(self):
        """Create TextExtractionService instance for testing."""
        return TextExtractionService()
    
    def test_get_extractor_for_pdf(self, service):
        """Test getting correct extractor for PDF files."""
        pdf_file_info = FileInfo(
            file_type="application/pdf",
            file_size=1000,
            is_valid=True
        )
        
        extractor = service._get_extractor_for_file(pdf_file_info)
        
        assert isinstance(extractor, PDFTextExtractor)
    
    def test_get_extractor_for_docx(self, service):
        """Test getting correct extractor for DOCX files."""
        docx_file_info = FileInfo(
            file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=1000,
            is_valid=True
        )
        
        extractor = service._get_extractor_for_file(docx_file_info)
        
        assert isinstance(extractor, DocxTextExtractor)
    
    def test_get_extractor_for_unsupported_type(self, service):
        """Test getting extractor for unsupported file type."""
        unsupported_file_info = FileInfo(
            file_type="image/jpeg",
            file_size=1000,
            is_valid=True
        )
        
        extractor = service._get_extractor_for_file(unsupported_file_info)
        
        assert extractor is None
    
    def test_get_supported_file_types(self, service):
        """Test getting list of supported file types."""
        supported_types = service.get_supported_file_types()
        
        expected_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ]
        
        assert all(file_type in supported_types for file_type in expected_types)
    
    @pytest.mark.asyncio
    async def test_extract_text_file_not_found(self, service):
        """Test extraction when file doesn't exist."""
        non_existent_file = Path("/tmp/nonexistent.pdf")
        file_info = FileInfo(
            file_type="application/pdf",
            file_size=1000,
            is_valid=True
        )
        
        result = await service.extract_text_from_file(non_existent_file, file_info)
        
        assert result.status == ExtractionStatus.FAILED
        assert "File not found" in result.error_message
    
    @pytest.mark.asyncio
    async def test_extract_text_unsupported_type(self, service):
        """Test extraction with unsupported file type."""
        test_file = Path("/tmp/test.jpg")
        unsupported_file_info = FileInfo(
            file_type="image/jpeg",
            file_size=1000,
            is_valid=True
        )
        
        # Mock file existence
        with patch.object(Path, 'exists', return_value=True):
            result = await service.extract_text_from_file(test_file, unsupported_file_info)
        
        assert result.status == ExtractionStatus.FAILED
        assert "No extractor available" in result.error_message
    
    @pytest.mark.asyncio
    async def test_extract_text_timeout(self, service):
        """Test extraction timeout handling."""
        test_file = Path("/tmp/test.pdf")
        file_info = FileInfo(
            file_type="application/pdf",
            file_size=1000,
            is_valid=True
        )
        
        # Mock a slow extraction that will timeout
        def slow_extraction(file_path):
            import time
            time.sleep(2)  # Simulate slow processing
            return ExtractionResult(
                status=ExtractionStatus.COMPLETED,
                extracted_text="Should not reach here"
            )
        
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(PDFTextExtractor, 'extract_text', side_effect=slow_extraction):
                result = await service.extract_text_from_file(
                    test_file, 
                    file_info, 
                    timeout_seconds=1
                )
        
        assert result.status == ExtractionStatus.TIMEOUT
        assert "timed out" in result.error_message
    
    @pytest.mark.asyncio
    async def test_extract_text_success_with_logging(self, service, caplog):
        """Test successful extraction with logging verification."""
        test_file = Path("/tmp/test.pdf")
        file_info = FileInfo(
            file_type="application/pdf",
            file_size=1000,
            is_valid=True
        )
        
        # Mock successful extraction
        mock_result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="Test resume content with multiple words",
            processing_time_seconds=0.5
        )
        
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(PDFTextExtractor, 'extract_text', return_value=mock_result):
                result = await service.extract_text_from_file(test_file, file_info)
        
        assert result.status == ExtractionStatus.COMPLETED
        assert result.extracted_text == "Test resume content with multiple words"
        
        # Check logging
        assert "Successfully extracted" in caplog.text
        assert "characters" in caplog.text


class TestGlobalServiceInstance:
    """Test the global text_extraction_service instance."""
    
    def test_global_service_exists(self):
        """Test that global service instance exists and is properly configured."""
        assert text_extraction_service is not None
        assert isinstance(text_extraction_service, TextExtractionService)
        assert len(text_extraction_service._extractors) == 3
    
    def test_global_service_has_all_extractors(self):
        """Test that global service has all expected extractors."""
        extractor_types = [type(extractor) for extractor in text_extraction_service._extractors]
        
        assert PDFTextExtractor in extractor_types
        assert DocxTextExtractor in extractor_types
        assert DocTextExtractor in extractor_types


class TestExtractionResult:
    """Test ExtractionResult data class functionality."""
    
    def test_extraction_result_is_success_true(self):
        """Test is_success property for successful extraction."""
        result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="Some text"
        )
        
        assert result.is_success is True
    
    def test_extraction_result_is_success_false_no_text(self):
        """Test is_success property when no text extracted."""
        result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text=None
        )
        
        assert result.is_success is False
    
    def test_extraction_result_is_success_false_failed_status(self):
        """Test is_success property with failed status."""
        result = ExtractionResult(
            status=ExtractionStatus.FAILED,
            extracted_text="Some text"
        )
        
        assert result.is_success is False
    
    def test_extraction_result_defaults(self):
        """Test ExtractionResult default values."""
        result = ExtractionResult(status=ExtractionStatus.PENDING)
        
        assert result.extracted_text is None
        assert result.metadata is None
        assert result.error_message is None
        assert result.processing_time_seconds is None


@pytest.mark.performance
class TestPerformanceCharacteristics:
    """Test performance characteristics of text extraction."""
    
    @pytest.mark.asyncio
    async def test_concurrent_extractions(self):
        """Test concurrent text extractions don't interfere."""
        service = TextExtractionService()
        
        # Mock multiple successful extractions
        mock_result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="Concurrent test content",
            processing_time_seconds=0.1
        )
        
        test_files = [Path(f"/tmp/test{i}.pdf") for i in range(5)]
        file_info = FileInfo(
            file_type="application/pdf",
            file_size=1000,
            is_valid=True
        )
        
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(PDFTextExtractor, 'extract_text', return_value=mock_result):
                tasks = [
                    service.extract_text_from_file(file, file_info)
                    for file in test_files
                ]
                
                results = await asyncio.gather(*tasks)
        
        # All extractions should succeed
        assert len(results) == 5
        assert all(result.status == ExtractionStatus.COMPLETED for result in results)
        assert all(result.extracted_text == "Concurrent test content" for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])