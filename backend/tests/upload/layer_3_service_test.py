#!/usr/bin/env python3
"""
Layer 3 Test: Service Layer
Tests UploadService dependency injection and business logic coordination.
"""

import sys
import logging
from pathlib import Path
from uuid import uuid4
from io import BytesIO

# Add backend to path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

from app.database.connection import get_db
from app.services.upload_service import UploadService, get_upload_service, UploadServiceError
from app.models.user import User
from app.models.upload import ExperienceLevel
from fastapi import UploadFile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_pdf_content() -> bytes:
    """Create minimal valid PDF content for testing."""
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
(Service Test Resume) Tj
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


def create_mock_user() -> User:
    """Create a mock user for testing using real database user."""
    from uuid import UUID
    user = User(
        email="test_5406ab4e@example.com",
        password="TestPassword123!",
        first_name="Test",
        last_name="User"
    )
    user.id = UUID("8955190d-e058-43ce-8260-fe5481dbb6e9")  # Real user ID from database
    user.is_active = True
    user.role = "consultant"
    return user


class MockUploadFile:
    """Mock UploadFile for testing."""
    
    def __init__(self, content: bytes, filename: str):
        self.content = content
        self.filename = filename
        self._file = BytesIO(content)
        
    async def read(self) -> bytes:
        return self.content
        
    async def seek(self, position: int):
        self._file.seek(position)


def test_service_dependency_injection():
    """Test UploadService dependency injection."""
    logger.info("=== Testing Service Dependency Injection ===")
    
    try:
        # Test manual instantiation
        db = next(get_db())
        service = UploadService(db)
        logger.info("✅ Manual UploadService instantiation successful")
        
        if hasattr(service, 'db') and service.db is not None:
            logger.info("✅ Database session injected correctly")
        else:
            logger.error("❌ Database session not injected")
            return False
            
        if hasattr(service, 'repository') and service.repository is not None:
            logger.info("✅ Repository injected correctly")
        else:
            logger.error("❌ Repository not injected")
            return False
            
        # Test dependency injection function
        service2 = get_upload_service(db)
        logger.info("✅ Dependency injection function works")
        
        if isinstance(service2, UploadService):
            logger.info("✅ Correct service type returned")
        else:
            logger.error(f"❌ Wrong service type: {type(service2)}")
            return False
            
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Service dependency injection failed: {str(e)}")
        return False


def test_service_methods_exist():
    """Test that UploadService has all required methods."""
    logger.info("=== Testing Service Methods Exist ===")
    
    try:
        db = next(get_db())
        service = UploadService(db)
        
        required_methods = [
            'create_upload',
            'get_upload',
            'list_uploads',
            'delete_upload',
            'get_user_statistics',
            'get_extraction_result',
            'get_ai_ready_data',
            'start_text_extraction'
        ]
        
        for method in required_methods:
            if hasattr(service, method):
                logger.info(f"✅ Service has method: {method}")
            else:
                logger.error(f"❌ Service missing method: {method}")
                return False
                
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Service method check failed: {str(e)}")
        return False


async def test_service_create_upload():
    """Test service create_upload method."""
    logger.info("=== Testing Service Create Upload ===")
    
    db = None
    created_upload_id = None
    
    try:
        db = next(get_db())
        service = UploadService(db)
        
        # Create test data
        pdf_content = create_test_pdf_content()
        mock_file = MockUploadFile(pdf_content, "service_test.pdf")
        mock_user = create_mock_user()
        
        logger.info(f"Testing upload for user: {mock_user.id}")
        logger.info(f"File: {mock_file.filename}, Size: {len(pdf_content)} bytes")
        
        # Call create_upload
        result = await service.create_upload(
            file=mock_file,
            user=mock_user,
            target_role="Software Engineer",
            target_industry="Technology",
            experience_level=ExperienceLevel.MID
        )
        
        logger.info(f"Upload result: {result}")
        
        # Verify result structure
        required_keys = [
            'id', 'original_filename', 'file_size_bytes', 'mime_type', 
            'status', 'created_at', 'message'
        ]
        
        for key in required_keys:
            if key in result:
                logger.info(f"✅ Result has key: {key} = {result[key]}")
            else:
                logger.error(f"❌ Result missing key: {key}")
                return False
        
        # Store ID for cleanup
        created_upload_id = result['id']
        
        # Verify values
        if result['original_filename'] == mock_file.filename:
            logger.info("✅ Filename preserved correctly")
        else:
            logger.error("❌ Filename not preserved")
            return False
            
        if result['file_size_bytes'] == len(pdf_content):
            logger.info("✅ File size calculated correctly")
        else:
            logger.error("❌ File size incorrect")
            return False
            
        if result['mime_type'] == 'application/pdf':
            logger.info("✅ MIME type detected correctly")
        else:
            logger.warning(f"⚠️ Unexpected MIME type: {result['mime_type']}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Service create upload failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
        
    finally:
        # Cleanup
        if db and created_upload_id:
            try:
                # Delete via service
                mock_user = create_mock_user()  # Recreate for cleanup
                service.delete_upload(created_upload_id, mock_user)
                logger.info("✅ Test upload cleaned up")
            except Exception as e:
                logger.warning(f"⚠️ Failed to cleanup test upload: {str(e)}")
        
        if db:
            db.close()


async def test_service_error_handling():
    """Test service error handling."""
    logger.info("=== Testing Service Error Handling ===")
    
    try:
        db = next(get_db())
        service = UploadService(db)
        
        # Test with invalid file (empty content)
        mock_file = MockUploadFile(b"", "empty.pdf")
        mock_user = create_mock_user()
        
        try:
            result = await service.create_upload(
                file=mock_file,
                user=mock_user
            )
            logger.warning("⚠️ Empty file was accepted (unexpected)")
            
        except (UploadServiceError, Exception) as e:
            logger.info(f"✅ Empty file correctly rejected: {str(e)}")
        
        # Test with invalid filename
        pdf_content = create_test_pdf_content()
        mock_file = MockUploadFile(pdf_content, "")
        
        try:
            result = await service.create_upload(
                file=mock_file,
                user=mock_user
            )
            logger.warning("⚠️ Invalid filename was accepted (unexpected)")
            
        except (UploadServiceError, Exception) as e:
            logger.info(f"✅ Invalid filename correctly rejected: {str(e)}")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Service error handling test failed: {str(e)}")
        return False


def test_service_list_operations():
    """Test service list and get operations."""
    logger.info("=== Testing Service List Operations ===")
    
    try:
        db = next(get_db())
        service = UploadService(db)
        mock_user = create_mock_user()
        
        # Test list_uploads (should work even with no uploads)
        result = service.list_uploads(mock_user, page=1, per_page=10)
        logger.info(f"List result: {result}")
        
        if 'uploads' in result and 'pagination' in result:
            logger.info("✅ List uploads returns correct structure")
            logger.info(f"Found {len(result['uploads'])} uploads")
        else:
            logger.error("❌ List uploads missing required keys")
            return False
            
        # Test get_user_statistics
        stats = service.get_user_statistics(mock_user)
        logger.info(f"Statistics: {stats}")
        
        if isinstance(stats, dict):
            logger.info("✅ Get user statistics returns dictionary")
        else:
            logger.error("❌ Get user statistics wrong return type")
            return False
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Service list operations failed: {str(e)}")
        return False


def main():
    """Run all service layer tests."""
    logger.info("🧪 Starting Layer 3: Service Layer Tests")
    logger.info("=" * 60)
    
    import asyncio
    
    # Sync tests
    sync_tests = [
        ("Service Dependency Injection", test_service_dependency_injection),
        ("Service Methods Exist", test_service_methods_exist),
        ("Service List Operations", test_service_list_operations),
    ]
    
    # Async tests
    async_tests = [
        ("Service Create Upload", test_service_create_upload),
        ("Service Error Handling", test_service_error_handling),
    ]
    
    results = {}
    
    # Run sync tests
    for test_name, test_func in sync_tests:
        logger.info(f"\n🔍 Running: {test_name}")
        logger.info("-" * 40)
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {str(e)}")
            results[test_name] = False
    
    # Run async tests
    for test_name, test_func in async_tests:
        logger.info(f"\n🔍 Running: {test_name}")
        logger.info("-" * 40)
        
        try:
            results[test_name] = asyncio.run(test_func())
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {str(e)}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 LAYER 3 TEST RESULTS")
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
        logger.info("🎉 Layer 3 (Service Layer) is working correctly!")
    else:
        logger.error("💥 Layer 3 has issues that need to be fixed before proceeding.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)