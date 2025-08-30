"""
Integration tests for logout endpoint.

Tests the complete logout flow including:
- API endpoint accessibility
- Authentication requirements
- Token invalidation
- Redis integration
- Security headers
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import json


class TestLogoutIntegrationFlow:
    """Integration tests for complete logout flow."""
    
    def test_logout_endpoint_exists(self, client):
        """Test that logout endpoint is accessible at correct URL."""
        # Should return authentication error (403) not 404, confirming endpoint exists
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 403  # Authentication required, not 404
        
        data = response.json()
        assert "detail" in data
    
    def test_logout_endpoint_methods(self, client):
        """Test allowed HTTP methods for logout endpoint."""
        # POST should be allowed (with auth error)
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 403  # Authentication required
        
        # GET should not be allowed
        response = client.get("/api/v1/auth/logout")
        assert response.status_code == 405  # Method not allowed
        
        # PUT should not be allowed
        response = client.put("/api/v1/auth/logout")
        assert response.status_code == 405
        
        # DELETE should not be allowed
        response = client.delete("/api/v1/auth/logout")
        assert response.status_code == 405
    
    def test_logout_requires_authentication(self, client):
        """Test that logout endpoint requires authentication."""
        # No authorization header
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 403
        
        # Invalid authorization header
        headers = {"Authorization": "Invalid"}
        response = client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 401
        
        # Malformed bearer token
        headers = {"Authorization": "Bearer"}
        response = client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 401
        
        # Invalid token format
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 401
    
    def test_logout_with_expired_token(self, client):
        """Test logout with an expired token."""
        # Create an expired token
        from app.core.security import create_access_token
        from datetime import timedelta
        
        expired_token = create_access_token(
            data={"sub": "test_user", "email": "test@example.com"},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 401  # Should reject expired token
    
    def test_successful_logout_with_real_token(self, client, create_test_user):
        """Test successful logout with a real user and token."""
        # Create a real user
        test_user = create_test_user(
            email="logout.test@example.com",
            password="TestPassword123!",
            first_name="Logout",
            last_name="Test"
        )
        
        # Login to get a valid token
        login_response = client.post("/api/v1/auth/login", json={
            "email": "logout.test@example.com",
            "password": "TestPassword123!"
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        access_token = login_data["access_token"]
        
        # Now logout with the valid token
        headers = {"Authorization": f"Bearer {access_token}"}
        logout_response = client.post("/api/v1/auth/logout", headers=headers)
        
        # Verify successful logout
        assert logout_response.status_code == 200
        logout_data = logout_response.json()
        assert logout_data["message"] == "Successfully logged out"
    
    def test_token_invalidation_after_logout(self, client, create_test_user):
        """Test that token is invalidated after logout."""
        # Create a real user
        test_user = create_test_user(
            email="invalidation.test@example.com",
            password="TestPassword123!",
            first_name="Invalidation",
            last_name="Test"
        )
        
        # Login to get a valid token
        login_response = client.post("/api/v1/auth/login", json={
            "email": "invalidation.test@example.com",
            "password": "TestPassword123!"
        })
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Verify token works before logout
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        # Logout
        logout_response = client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response.status_code == 200
        
        # Verify token is invalidated after logout
        me_response_after = client.get("/api/v1/auth/me", headers=headers)
        assert me_response_after.status_code == 401  # Should be unauthorized now
    
    def test_multiple_logout_attempts(self, client, create_test_user):
        """Test multiple logout attempts with the same token."""
        # Create a real user
        test_user = create_test_user(
            email="multiple.logout@example.com",
            password="TestPassword123!",
            first_name="Multiple",
            last_name="Logout"
        )
        
        # Login to get a valid token
        login_response = client.post("/api/v1/auth/login", json={
            "email": "multiple.logout@example.com",
            "password": "TestPassword123!"
        })
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # First logout should succeed
        logout_response1 = client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response1.status_code == 200
        
        # Second logout attempt should fail (token is blacklisted)
        logout_response2 = client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response2.status_code == 401  # Unauthorized due to blacklisted token
    
    def test_content_type_handling(self, client, create_test_user):
        """Test content type handling for logout endpoint."""
        # Create user and get token
        test_user = create_test_user(
            email="content.type@example.com",
            password="TestPassword123!",
            first_name="Content",
            last_name="Type"
        )
        
        login_response = client.post("/api/v1/auth/login", json={
            "email": "content.type@example.com",
            "password": "TestPassword123!"
        })
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Logout endpoint should not require JSON body (POST with no body)
        response = client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 200
    
    def test_cors_and_security_headers(self, client):
        """Test CORS and security headers in logout response."""
        # Even unauthorized requests should have proper CORS headers
        response = client.post("/api/v1/auth/logout")
        
        # Check that response has appropriate headers (may vary based on CORS setup)
        # At minimum, should have content-type
        assert "content-type" in response.headers
        assert response.headers["content-type"] == "application/json"
    
    def test_logout_endpoint_error_responses(self, client):
        """Test various error response formats."""
        # Test unauthorized response format
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 403
        
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        
        # Test with invalid bearer token format
        headers = {"Authorization": "Bearer invalid.token.format"}
        response = client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 401
        
        data = response.json()
        assert "detail" in data
    
    def test_concurrent_logout_attempts(self, client, create_test_user):
        """Test concurrent logout attempts with the same user."""
        # Create user
        test_user = create_test_user(
            email="concurrent.logout@example.com",
            password="TestPassword123!",
            first_name="Concurrent",
            last_name="Logout"
        )
        
        # Get two valid tokens for the same user (simulate multiple sessions)
        login_response1 = client.post("/api/v1/auth/login", json={
            "email": "concurrent.logout@example.com",
            "password": "TestPassword123!"
        })
        login_response2 = client.post("/api/v1/auth/login", json={
            "email": "concurrent.logout@example.com", 
            "password": "TestPassword123!"
        })
        
        assert login_response1.status_code == 200
        assert login_response2.status_code == 200
        
        token1 = login_response1.json()["access_token"]
        token2 = login_response2.json()["access_token"]
        
        # Both tokens should work initially
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        me_response1 = client.get("/api/v1/auth/me", headers=headers1)
        me_response2 = client.get("/api/v1/auth/me", headers=headers2)
        assert me_response1.status_code == 200
        assert me_response2.status_code == 200
        
        # Logout with first token
        logout_response1 = client.post("/api/v1/auth/logout", headers=headers1)
        assert logout_response1.status_code == 200
        
        # First token should be invalid, second should still work
        me_after1 = client.get("/api/v1/auth/me", headers=headers1)
        me_after2 = client.get("/api/v1/auth/me", headers=headers2)
        assert me_after1.status_code == 401  # First token invalidated
        assert me_after2.status_code == 200   # Second token still valid