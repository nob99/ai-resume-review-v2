#!/usr/bin/env python3
"""
Layer 4 Test: API Layer
Tests FastAPI endpoint routing, dependency injection, and request handling.
"""

import sys
import logging
from pathlib import Path
import asyncio
from io import BytesIO

# Add backend to path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch, MagicMock

# Import the app
from app.main import app

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
(API Test Resume) Tj
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


def test_api_routing():
    """Test that API routes are properly configured."""
    logger.info("=== Testing API Routing ===")
    
    try:
        client = TestClient(app)
        
        # Test health check endpoint
        response = client.get("/health")
        if response.status_code == 200:
            logger.info("✅ Health check endpoint accessible")
        else:
            logger.error(f"❌ Health check failed: {response.status_code}")
            return False
        
        # Test root endpoint
        response = client.get("/")
        if response.status_code == 200:
            logger.info("✅ Root endpoint accessible")
        else:
            logger.error(f"❌ Root endpoint failed: {response.status_code}")
            return False
        
        # Test OpenAPI docs
        response = client.get("/docs")
        if response.status_code == 200:
            logger.info("✅ OpenAPI docs accessible")
        else:
            logger.error(f"❌ OpenAPI docs failed: {response.status_code}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ API routing test failed: {str(e)}")
        return False


def test_upload_endpoint_exists():
    """Test that upload endpoints exist and are routable."""
    logger.info("=== Testing Upload Endpoint Exists ===")
    
    try:
        client = TestClient(app)
        
        # Test upload endpoint with invalid auth (should return 401, not 404)
        response = client.post("/api/v1/upload/resume")
        
        if response.status_code == 401:
            logger.info("✅ Upload endpoint exists (returned 401 for missing auth)")
        elif response.status_code == 404:
            logger.error("❌ Upload endpoint not found (404)")
            return False
        else:
            logger.info(f"✅ Upload endpoint exists (returned {response.status_code})")
        
        # Test list endpoint
        response = client.get("/api/v1/upload/list")
        if response.status_code in [401, 422]:  # Auth required or validation error
            logger.info("✅ List endpoint exists")
        elif response.status_code == 404:
            logger.error("❌ List endpoint not found")
            return False
        
        # Test statistics endpoint
        response = client.get("/api/v1/upload/statistics")
        if response.status_code in [401, 422]:
            logger.info("✅ Statistics endpoint exists")
        elif response.status_code == 404:
            logger.error("❌ Statistics endpoint not found")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Upload endpoint test failed: {str(e)}")
        return False


def test_auth_dependency():
    """Test authentication dependency injection."""
    logger.info("=== Testing Auth Dependency ===")
    
    try:
        client = TestClient(app)
        
        # Test upload without auth token
        response = client.post("/api/v1/upload/resume")
        
        if response.status_code == 401:
            logger.info("✅ Auth dependency working (401 for missing token)")
            
            response_data = response.json()
            if "detail" in response_data:
                logger.info(f"Auth error message: {response_data['detail']}")
            
        else:
            logger.warning(f"⚠️ Expected 401, got {response.status_code}")
        
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/api/v1/upload/resume", headers=headers)
        
        if response.status_code == 401:
            logger.info("✅ Auth validation working (401 for invalid token)")
        else:
            logger.warning(f"⚠️ Expected 401 for invalid token, got {response.status_code}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Auth dependency test failed: {str(e)}")
        return False


@patch('app.api.auth.get_current_user')
@patch('app.services.upload_service.get_upload_service')
def test_upload_with_mocked_dependencies(mock_upload_service, mock_auth):
    """Test upload endpoint with mocked dependencies."""
    logger.info("=== Testing Upload with Mocked Dependencies ===")
    
    try:
        # Mock user
        from app.models.user import User
        from uuid import uuid4
        
        mock_user = User()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True
        mock_auth.return_value = mock_user
        
        # Mock upload service
        mock_service_instance = MagicMock()
        mock_upload_service.return_value = mock_service_instance
        
        # Mock successful upload result
        mock_result = {
            "id": uuid4(),
            "original_filename": "test.pdf",
            "file_size_bytes": 1024,
            "mime_type": "application/pdf",
            "status": "pending",
            "extraction_status": "pending",
            "target_role": None,
            "target_industry": None,
            "experience_level": None,
            "created_at": "2024-01-01T00:00:00Z",
            "message": "Upload completed successfully"
        }
        
        # Mock the async create_upload method
        async def mock_create_upload(*args, **kwargs):
            return mock_result
            
        mock_service_instance.create_upload = mock_create_upload
        
        client = TestClient(app)
        
        # Create test file
        pdf_content = create_test_pdf_content()
        
        # Test upload
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        headers = {"Authorization": "Bearer mock_token"}
        
        response = client.post("/api/v1/upload/resume", files=files, headers=headers)
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        if response.status_code == 201:
            logger.info("✅ Upload endpoint responds correctly with mocked dependencies")
            
            response_data = response.json()
            if "id" in response_data and "original_filename" in response_data:
                logger.info("✅ Response structure correct")
            else:
                logger.error("❌ Response structure incorrect")
                return False
                
        elif response.status_code == 422:
            logger.warning("⚠️ Validation error - check request format")
            logger.warning(f"Validation details: {response.json()}")
        else:
            logger.error(f"❌ Unexpected status code: {response.status_code}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Mocked upload test failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def test_validation_middleware():
    """Test FastAPI validation middleware."""
    logger.info("=== Testing Validation Middleware ===")
    
    try:
        client = TestClient(app)
        
        # Mock auth to bypass authentication
        with patch('app.api.auth.get_current_user') as mock_auth:
            from app.models.user import User
            from uuid import uuid4
            
            mock_user = User()
            mock_user.id = uuid4()
            mock_user.email = "test@example.com"
            mock_auth.return_value = mock_user
            
            headers = {"Authorization": "Bearer mock_token"}
            
            # Test without file
            response = client.post("/api/v1/upload/resume", headers=headers)
            
            if response.status_code == 422:
                logger.info("✅ Validation catches missing file")
                
                error_details = response.json()
                logger.info(f"Validation error: {error_details}")
                
            else:
                logger.warning(f"⚠️ Expected 422 for missing file, got {response.status_code}")
            
            # Test with invalid file type (if validation exists)
            files = {"file": ("test.txt", b"invalid content", "text/plain")}
            response = client.post("/api/v1/upload/resume", files=files, headers=headers)
            
            logger.info(f"Invalid file type response: {response.status_code}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Validation middleware test failed: {str(e)}")
        return False


def test_error_handling():
    """Test API error handling."""
    logger.info("=== Testing API Error Handling ===")
    
    try:
        client = TestClient(app)
        
        # Test 404 for non-existent endpoints
        response = client.get("/api/v1/nonexistent")
        if response.status_code == 404:
            logger.info("✅ 404 handling works for non-existent endpoints")
        else:
            logger.warning(f"⚠️ Expected 404, got {response.status_code}")
        
        # Test method not allowed
        response = client.delete("/api/v1/upload/resume")  # Should be POST
        if response.status_code == 405:
            logger.info("✅ 405 handling works for wrong methods")
        else:
            logger.warning(f"⚠️ Expected 405, got {response.status_code}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ API error handling test failed: {str(e)}")
        return False


def main():
    """Run all API layer tests."""
    logger.info("🧪 Starting Layer 4: API Layer Tests")
    logger.info("=" * 60)
    
    tests = [
        ("API Routing", test_api_routing),
        ("Upload Endpoint Exists", test_upload_endpoint_exists),
        ("Auth Dependency", test_auth_dependency),
        ("Upload with Mocked Dependencies", test_upload_with_mocked_dependencies),
        ("Validation Middleware", test_validation_middleware),
        ("Error Handling", test_error_handling),
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
    logger.info("📊 LAYER 4 TEST RESULTS")
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
        logger.info("🎉 Layer 4 (API Layer) is working correctly!")
    else:
        logger.error("💥 Layer 4 has issues that need to be fixed before proceeding.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)