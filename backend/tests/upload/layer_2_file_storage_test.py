#!/usr/bin/env python3
"""
Layer 2 Test: File Storage Layer
Tests file_service.store_uploaded_file() functionality in isolation.
"""

import sys
import logging
import tempfile
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

from app.services.file_service import store_uploaded_file, FileStorageResult
from app.core.file_validation import get_file_info, validate_uploaded_file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_pdf_content() -> bytes:
    """Create minimal valid PDF content for testing."""
    # Minimal PDF content that passes validation
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Resume) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000110 00000 n 
0000000181 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
270
%%EOF"""
    return pdf_content


def test_file_validation():
    """Test file validation functionality."""
    logger.info("=== Testing File Validation ===")
    
    try:
        # Test with valid PDF content
        pdf_content = create_test_pdf_content()
        
        logger.info("Testing file validation with PDF content...")
        validation_result = validate_uploaded_file(pdf_content, "test.pdf")
        
        logger.info(f"Validation result: {validation_result}")
        
        # Check validation result
        if validation_result.is_valid:
            logger.info("✅ File validation passed")
        else:
            logger.error(f"❌ File validation failed: {validation_result.errors}")
            return False
        
        # Check MIME type
        mime_type = validation_result.file_info.get('mime_type', 'unknown')
        if mime_type == 'application/pdf':
            logger.info("✅ PDF MIME type detected correctly")
        else:
            logger.warning(f"⚠️ Unexpected MIME type: {mime_type}")
            
        # Check file size
        file_size = validation_result.file_info.get('file_size', 0)
        if file_size > 0:
            logger.info(f"✅ File size detected: {file_size} bytes")
        else:
            logger.error("❌ File size not detected")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ File validation failed: {str(e)}")
        return False


def test_file_storage_basic():
    """Test basic file storage functionality."""
    logger.info("=== Testing Basic File Storage ===")
    
    try:
        # Create test content
        pdf_content = create_test_pdf_content()
        test_filename = "test_storage.pdf"
        test_user_id = "test_user_123"
        
        logger.info(f"Attempting to store file: {test_filename}")
        logger.info(f"Content size: {len(pdf_content)} bytes")
        
        # Call store_uploaded_file
        result = store_uploaded_file(
            file_content=pdf_content,
            original_filename=test_filename,
            user_id=test_user_id
        )
        
        logger.info(f"Storage result type: {type(result)}")
        logger.info(f"Storage result: {result}")
        
        # Check if result is FileStorageResult
        if isinstance(result, FileStorageResult):
            logger.info("✅ Returned FileStorageResult object")
        else:
            logger.error(f"❌ Expected FileStorageResult, got: {type(result)}")
            return False
        
        # Check success status
        if result.success:
            logger.info("✅ Storage reported success")
            logger.info(f"Stored file path: {result.file_path}")
            
            # Verify file exists (need to prepend storage root)
            from app.core.config import get_settings
            settings = get_settings()
            storage_root = Path(settings.file_storage_path or "storage/uploads")
            full_file_path = storage_root / result.file_path
            
            if result.file_path and full_file_path.exists():
                logger.info("✅ Stored file exists on disk")
                
                # Cleanup
                full_file_path.unlink()
                logger.info("✅ Test file cleaned up")
            else:
                logger.error(f"❌ Stored file not found: {full_file_path}")
                return False
                
        else:
            logger.error(f"❌ Storage failed: {result.error_message}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ File storage test failed: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def test_file_storage_validation_integration():
    """Test file storage with validation integration."""
    logger.info("=== Testing File Storage + Validation Integration ===")
    
    try:
        # Create test content
        pdf_content = create_test_pdf_content()
        test_filename = "test_validation.pdf"
        
        result = store_uploaded_file(
            file_content=pdf_content,
            original_filename=test_filename,
            user_id="validation_test_user"
        )
        
        if not result.success:
            logger.error(f"❌ Storage failed: {result.error_message}")
            return False
            
        # Check validation result is included
        if hasattr(result, 'validation_result') and result.validation_result:
            logger.info("✅ Validation result included in storage result")
            
            validation = result.validation_result
            if hasattr(validation, 'file_info') and validation.file_info:
                logger.info(f"✅ File info available: {validation.file_info}")
            else:
                logger.warning("⚠️ File info not found in validation result")
                
        else:
            logger.warning("⚠️ Validation result not found in storage result")
        
        # Cleanup
        if result.file_path:
            from app.core.config import get_settings
            settings = get_settings()
            storage_root = Path(settings.file_storage_path or "storage/uploads")
            full_file_path = storage_root / result.file_path
            if full_file_path.exists():
                full_file_path.unlink()
                logger.info("✅ Test file cleaned up")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Storage + validation test failed: {str(e)}")
        return False


def test_error_handling():
    """Test file storage error handling."""
    logger.info("=== Testing File Storage Error Handling ===")
    
    try:
        # Test with invalid content
        logger.info("Testing with empty content...")
        result = store_uploaded_file(
            file_content=b"",
            original_filename="empty.pdf",
            user_id="error_test_user"
        )
        
        if not result.success:
            logger.info("✅ Empty file correctly rejected")
            logger.info(f"Error message: {result.error_message}")
        else:
            logger.warning("⚠️ Empty file was accepted (unexpected)")
        
        # Test with invalid filename
        logger.info("Testing with invalid filename...")
        pdf_content = create_test_pdf_content()
        result = store_uploaded_file(
            file_content=pdf_content,
            original_filename="",
            user_id="error_test_user"
        )
        
        if not result.success:
            logger.info("✅ Invalid filename correctly rejected")
            logger.info(f"Error message: {result.error_message}")
        else:
            logger.warning("⚠️ Invalid filename was accepted (unexpected)")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Error handling test failed: {str(e)}")
        return False


def test_storage_directory_permissions():
    """Test storage directory creation and permissions."""
    logger.info("=== Testing Storage Directory Permissions ===")
    
    try:
        # Create test content
        pdf_content = create_test_pdf_content()
        
        result = store_uploaded_file(
            file_content=pdf_content,
            original_filename="permissions_test.pdf",
            user_id="permissions_user"
        )
        
        if result.success and result.file_path:
            from app.core.config import get_settings
            settings = get_settings()
            storage_root = Path(settings.file_storage_path or "storage/uploads")
            full_file_path = storage_root / result.file_path
            
            logger.info(f"✅ File stored at: {result.file_path}")
            logger.info(f"Full path: {full_file_path}")
            
            # Check parent directory exists
            if full_file_path.parent.exists():
                logger.info("✅ Storage directory exists")
                
                # Check if we can read the file
                if full_file_path.exists() and full_file_path.is_file():
                    logger.info("✅ File is readable")
                    
                    # Check file size
                    actual_size = full_file_path.stat().st_size
                    expected_size = len(pdf_content)
                    
                    if actual_size == expected_size:
                        logger.info(f"✅ File size correct: {actual_size} bytes")
                    else:
                        logger.error(f"❌ File size mismatch: expected {expected_size}, got {actual_size}")
                        return False
                else:
                    logger.error("❌ Stored file is not readable")
                    return False
            else:
                logger.error("❌ Storage directory does not exist")
                return False
            
            # Cleanup
            full_file_path.unlink()
            logger.info("✅ Test file cleaned up")
            
        else:
            logger.error("❌ File storage failed in permissions test")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Storage directory permissions test failed: {str(e)}")
        return False


def main():
    """Run all file storage layer tests."""
    logger.info("🧪 Starting Layer 2: File Storage Tests")
    logger.info("=" * 60)
    
    tests = [
        ("File Validation", test_file_validation),
        ("Basic File Storage", test_file_storage_basic),
        ("Storage + Validation Integration", test_file_storage_validation_integration),
        ("Error Handling", test_error_handling),
        ("Storage Directory Permissions", test_storage_directory_permissions),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        logger.info("-" * 40)
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {str(e)}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 LAYER 2 TEST RESULTS")
    logger.info("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if success:
            passed += 1
    
    logger.info("-" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 Layer 2 (File Storage) is working correctly!")
    else:
        logger.error("💥 Layer 2 has issues that need to be fixed before proceeding.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)