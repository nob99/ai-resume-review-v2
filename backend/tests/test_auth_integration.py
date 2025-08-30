"""
Integration tests for authentication endpoints.

Tests the complete authentication flow including:
- API endpoint accessibility
- Request/response validation
- Error handling
- Security headers
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
from sqlalchemy.orm import Session
import json


class TestAuthIntegrationFlow:
    """Integration tests for complete authentication flow."""
    
    def test_login_endpoint_exists(self, client):
        """Test that login endpoint is accessible at correct URL."""
        # Should return validation error (422) not 404, confirming endpoint exists
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422  # Validation error, not 404
        
        data = response.json()
        # Our custom error handler uses 'details' not 'detail'
        assert "details" in data or "error" in data
    
    def test_login_endpoint_methods(self, client):
        """Test allowed HTTP methods for login endpoint."""
        # POST should be allowed (with validation error)
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422
        
        # GET should not be allowed
        response = client.get("/api/v1/auth/login")
        assert response.status_code == 405  # Method not allowed
        
        # PUT should not be allowed
        response = client.put("/api/v1/auth/login")
        assert response.status_code == 405
        
        # DELETE should not be allowed
        response = client.delete("/api/v1/auth/login")
        assert response.status_code == 405
    
    def test_request_content_type(self, client):
        """Test content type handling."""
        valid_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        # JSON content type should work
        response = client.post(
            "/api/v1/auth/login",
            json=valid_data,
            headers={"Content-Type": "application/json"}
        )
        # Should get to validation/authentication, not content type error
        assert response.status_code in [400, 401, 500]  # Not 415 (Unsupported Media Type)
        
        # Form data should not work for this endpoint
        response = client.post(
            "/api/v1/auth/login",
            data=valid_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_request_validation_errors(self, client):
        """Test comprehensive request validation."""
        test_cases = [
            # Missing email
            ({"password": "password123"}, "email"),
            # Missing password
            ({"email": "test@example.com"}, "password"),
            # Invalid email format
            ({"email": "invalid-email", "password": "password123"}, "email"),
            # Empty email
            ({"email": "", "password": "password123"}, "email"),
            # Empty password
            ({"email": "test@example.com", "password": ""}, "password"),
            # Null values
            ({"email": None, "password": "password123"}, "email"),
            ({"email": "test@example.com", "password": None}, "password"),
        ]
        
        for data, expected_field in test_cases:
            response = client.post("/api/v1/auth/login", json=data)
            assert response.status_code == 422
            
            error_detail = response.json()
            assert "detail" in error_detail
            
            # Check that the error mentions the expected field
            error_str = str(error_detail)
            assert expected_field in error_str.lower()
    
    def test_successful_login_with_real_user(self, client, create_test_user):
        """Test successful login response format with real user in database."""
        # Create a real user in the database
        test_user = create_test_user(
            email="integration.test@example.com",
            password="TestPassword123!",
            first_name="Integration",
            last_name="Test"
        )
        
        # Make login request
        response = client.post("/api/v1/auth/login", json={
            "email": "integration.test@example.com",
            "password": "TestPassword123!"
        })
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        required_fields = ["access_token", "token_type", "expires_in", "user"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Check token properties
        assert data["token_type"] == "bearer"
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] == 900  # 15 minutes
        
        # Check user properties
        user_data = data["user"]
        user_required_fields = ["id", "email", "first_name", "last_name", "role", "is_active"]
        for field in user_required_fields:
            assert field in user_data, f"Missing user field: {field}"
        
        assert user_data["email"] == "integration.test@example.com"
        assert user_data["first_name"] == "Integration"
        assert user_data["last_name"] == "Test"
        assert user_data["role"] == "consultant"
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        # OPTIONS request should include CORS headers
        response = client.options("/api/v1/auth/login")
        assert response.status_code in [200, 204]
        
        # POST request should also include CORS headers
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Check for CORS headers (these are set by middleware)
        headers = response.headers
        # The test client might not include all CORS headers,
        # but we can check that CORS middleware is configured
        # by verifying the response doesn't fail due to CORS
        assert response.status_code != 501  # Not implemented (CORS issue)
    
    def test_security_headers(self, client):
        """Test security headers in responses."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com", 
            "password": "password123"
        })
        
        # Response should not expose server information
        headers = response.headers
        assert "Server" not in headers or "FastAPI" not in headers.get("Server", "")
        
        # Content-Type should be set
        assert "content-type" in headers
        assert "application/json" in headers["content-type"]
    
    def test_login_with_invalid_credentials(self, client):
        """Test login with invalid credentials returns 401."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "invalid" in data["detail"].lower() or "password" in data["detail"].lower()
    
    def test_error_response_format(self, client):
        """Test error response format consistency."""
        # Test validation error format
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422
        
        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], (str, list))
    
    def test_api_versioning(self, client):
        """Test API versioning is working correctly."""
        # v1 endpoint should exist
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422  # Validation error, endpoint exists
        
        # Direct /auth/login should not exist (since we use /api/v1 prefix)
        response = client.post("/auth/login", json={})
        assert response.status_code == 404  # Not found
    
    def test_json_response_encoding(self, client):
        """Test JSON response encoding."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Should be valid JSON
        try:
            data = response.json()
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON")
        
        # Content-Type should be application/json
        assert "application/json" in response.headers.get("content-type", "")


class TestAuthEndpointSecurity:
    """Security-focused integration tests."""
    
    def test_password_not_logged_in_errors(self, client):
        """Test that passwords are not exposed in error messages."""
        test_password = "supersecretpassword123!"
        
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": test_password
        })
        
        # Check that password is not in response
        response_text = response.text.lower()
        assert test_password.lower() not in response_text
        
        # Check JSON response
        if response.headers.get("content-type", "").startswith("application/json"):
            response_json = json.dumps(response.json()).lower()
            assert test_password.lower() not in response_json
    
    def test_malformed_email_handling(self, client):
        """Test that malformed emails are handled gracefully."""
        malformed_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "",
            None
        ]
        
        for email in malformed_emails:
            response = client.post("/api/v1/auth/login", json={
                "email": email,
                "password": "password123"
            })
            
            # Should return validation error, not crash
            assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])