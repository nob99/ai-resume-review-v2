"""
Integration tests for AUTH-003 Session Management functionality.
Tests the complete session management flow with real database and API calls.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.models.user import User
from app.models.session import RefreshToken, SessionStatus
from app.database.connection import get_db
from app.core.security import create_refresh_token


# Test database setup
TEST_DATABASE_URL = "postgresql://postgres:dev_password_123@localhost:5432/ai_resume_review_dev"
test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def get_test_db():
    """Override database dependency for testing."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override dependency
app.dependency_overrides[get_db] = get_test_db

client = TestClient(app)


class TestSessionManagementIntegration:
    """Integration tests for session management API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup test data and cleanup after each test."""
        # Create test database session
        self.db = TestSessionLocal()
        
        # Create unique test user for each test
        self.test_email = f"test-session-{uuid4().hex[:8]}@example.com"
        self.test_password = "TestPassword123!"
        
        self.test_user = User(
            email=self.test_email,
            password=self.test_password,
            first_name="Test",
            last_name="User"
        )
        
        self.db.add(self.test_user)
        self.db.commit()
        self.db.refresh(self.test_user)
        
        yield
        
        # Cleanup: Delete test user and related data
        self.db.query(RefreshToken).filter(RefreshToken.user_id == self.test_user.id).delete()
        self.db.query(User).filter(User.id == self.test_user.id).delete()
        self.db.commit()
        self.db.close()
    
    def test_login_creates_session(self):
        """Test that login creates a session with refresh token."""
        # Login
        login_response = client.post("/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        
        # Should receive both access and refresh tokens
        assert "access_token" in login_data
        assert "refresh_token" in login_data
        assert login_data["token_type"] == "bearer"
        assert login_data["expires_in"] == 1800  # 30 minutes in seconds
        
        # Check that refresh token was stored in database
        refresh_token_record = self.db.query(RefreshToken).filter(
            RefreshToken.user_id == self.test_user.id
        ).first()
        
        assert refresh_token_record is not None
        assert refresh_token_record.status == SessionStatus.ACTIVE.value
        assert refresh_token_record.device_info is not None
        assert refresh_token_record.is_active() is True
    
    def test_refresh_token_endpoint(self):
        """Test the token refresh endpoint."""
        # Login to get initial tokens
        login_response = client.post("/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]
        
        # Wait a moment to ensure token timestamps differ
        import time
        time.sleep(0.1)
        
        # Refresh tokens
        refresh_response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        
        # Should receive new tokens
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        assert refresh_data["token_type"] == "bearer"
        assert refresh_data["expires_in"] == 1800
        
        # New tokens should be different from original
        assert refresh_data["access_token"] != login_data["access_token"]
        assert refresh_data["refresh_token"] != refresh_token
        
        # Original refresh token should no longer work
        old_refresh_response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert old_refresh_response.status_code == 401
    
    def test_refresh_token_with_invalid_token(self):
        """Test refresh endpoint with invalid tokens."""
        # Test with completely invalid token
        invalid_response = client.post("/auth/refresh", json={
            "refresh_token": "invalid.jwt.token"
        })
        
        assert invalid_response.status_code == 401
        assert "Invalid refresh token" in invalid_response.json()["detail"]
        
        # Test with access token instead of refresh token
        login_response = client.post("/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        access_token = login_response.json()["access_token"]
        
        wrong_type_response = client.post("/auth/refresh", json={
            "refresh_token": access_token
        })
        
        assert wrong_type_response.status_code == 401
    
    def test_session_listing(self):
        """Test listing user sessions."""
        # Login to create a session
        login_response = client.post("/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        access_token = login_response.json()["access_token"]
        
        # List sessions
        sessions_response = client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert sessions_response.status_code == 200
        sessions_data = sessions_response.json()
        
        # Should have one active session
        assert sessions_data["total_sessions"] == 1
        assert sessions_data["max_sessions"] == 3
        assert len(sessions_data["sessions"]) == 1
        
        session = sessions_data["sessions"][0]
        assert session["is_current"] is True
        assert "session_id" in session
        assert "device_info" in session
        assert "created_at" in session
        assert "last_used_at" in session
    
    def test_multiple_sessions(self):
        """Test managing multiple concurrent sessions."""
        sessions = []
        
        # Create 3 sessions (at the limit)
        for i in range(3):
            # Use different user agent for each session
            login_response = client.post(
                "/auth/login", 
                json={
                    "email": self.test_email,
                    "password": self.test_password
                },
                headers={"User-Agent": f"TestBrowser-{i}"}
            )
            
            assert login_response.status_code == 200
            sessions.append(login_response.json())
        
        # List sessions using the last created session
        last_access_token = sessions[-1]["access_token"]
        sessions_response = client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {last_access_token}"}
        )
        
        assert sessions_response.status_code == 200
        sessions_data = sessions_response.json()
        
        # Should have exactly 3 sessions
        assert sessions_data["total_sessions"] == 3
        
        # Create 4th session - should revoke oldest
        fourth_login = client.post("/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        assert fourth_login.status_code == 200
        
        # Check that we still have only 3 sessions total
        new_access_token = fourth_login.json()["access_token"]
        final_sessions_response = client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        
        final_sessions_data = final_sessions_response.json()
        assert final_sessions_data["total_sessions"] <= 3
    
    def test_session_revocation(self):
        """Test revoking specific sessions."""
        # Create 2 sessions
        login1 = client.post("/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        login2 = client.post("/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        access_token1 = login1.json()["access_token"]
        access_token2 = login2.json()["access_token"]
        
        # List sessions from second session
        sessions_response = client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {access_token2}"}
        )
        
        sessions_data = sessions_response.json()
        assert sessions_data["total_sessions"] == 2
        
        # Find the other session (not current)
        other_session = None
        for session in sessions_data["sessions"]:
            if not session["is_current"]:
                other_session = session
                break
        
        assert other_session is not None
        
        # Revoke the other session
        revoke_response = client.delete(
            f"/auth/sessions/{other_session['session_id']}",
            headers={"Authorization": f"Bearer {access_token2}"}
        )
        
        assert revoke_response.status_code == 200
        revoke_data = revoke_response.json()
        assert revoke_data["success"] is True
        
        # Verify first session's token no longer works
        test_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token1}"}
        )
        
        # The access token might still work briefly, but refresh should fail
        refresh_response = client.post("/auth/refresh", json={
            "refresh_token": login1.json()["refresh_token"]
        })
        
        assert refresh_response.status_code == 401
    
    def test_revoke_all_other_sessions(self):
        """Test revoking all other sessions."""
        # Create 3 sessions
        sessions = []
        for i in range(3):
            login = client.post("/auth/login", json={
                "email": self.test_email,
                "password": self.test_password
            })
            sessions.append(login.json())
        
        # Use the last session to revoke all others
        current_access_token = sessions[-1]["access_token"]
        
        revoke_all_response = client.post(
            "/auth/sessions/revoke-all",
            headers={"Authorization": f"Bearer {current_access_token}"}
        )
        
        assert revoke_all_response.status_code == 200
        revoke_data = revoke_all_response.json()
        
        assert revoke_data["revoked_sessions"] == 2
        assert revoke_data["current_session_preserved"] is True
        
        # Verify only current session remains
        sessions_response = client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {current_access_token}"}
        )
        
        sessions_data = sessions_response.json()
        assert sessions_data["total_sessions"] == 1
        assert sessions_data["sessions"][0]["is_current"] is True
        
        # Verify other sessions' refresh tokens don't work
        for i in range(2):  # First 2 sessions should be revoked
            refresh_response = client.post("/auth/refresh", json={
                "refresh_token": sessions[i]["refresh_token"]
            })
            assert refresh_response.status_code == 401
    
    def test_prevent_current_session_revocation(self):
        """Test that users cannot revoke their current session."""
        # Login
        login_response = client.post("/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        access_token = login_response.json()["access_token"]
        
        # Get current session ID
        sessions_response = client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        current_session_id = sessions_response.json()["sessions"][0]["session_id"]
        
        # Try to revoke current session
        revoke_response = client.delete(
            f"/auth/sessions/{current_session_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert revoke_response.status_code == 200
        revoke_data = revoke_response.json()
        assert revoke_data["success"] is False
        assert "current session" in revoke_data["message"].lower()
    
    def test_expired_session_cleanup(self):
        """Test that expired sessions are properly handled."""
        # Create a session
        login_response = client.post("/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        access_token = login_response.json()["access_token"]
        
        # Manually expire the refresh token in database
        refresh_token_record = self.db.query(RefreshToken).filter(
            RefreshToken.user_id == self.test_user.id
        ).first()
        
        refresh_token_record.expires_at = datetime.utcnow() - timedelta(hours=1)
        self.db.commit()
        
        # List sessions - should automatically mark as expired
        sessions_response = client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert sessions_response.status_code == 200
        sessions_data = sessions_response.json()
        
        # Should show 0 active sessions after cleanup
        assert sessions_data["total_sessions"] == 0
        
        # Verify token is marked as expired in database
        self.db.refresh(refresh_token_record)
        assert refresh_token_record.status == SessionStatus.EXPIRED.value
    
    def test_session_security_isolation(self):
        """Test that users can only access their own sessions."""
        # Create second test user
        other_user_email = f"other-user-{uuid4().hex[:8]}@example.com"
        other_user = User(
            email=other_user_email,
            password="OtherPassword123!",
            first_name="Other",
            last_name="User"
        )
        
        self.db.add(other_user)
        self.db.commit()
        
        # Login both users
        login1 = client.post("/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        login2 = client.post("/auth/login", json={
            "email": other_user_email,
            "password": "OtherPassword123!"
        })
        
        token1 = login1.json()["access_token"]
        token2 = login2.json()["access_token"]
        
        # Get sessions for both users
        sessions1 = client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {token1}"}
        ).json()
        
        sessions2 = client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {token2}"}
        ).json()
        
        # Each user should only see their own session
        assert sessions1["total_sessions"] == 1
        assert sessions2["total_sessions"] == 1
        
        # Users should not be able to revoke each other's sessions
        user1_session_id = sessions1["sessions"][0]["session_id"]
        user2_session_id = sessions2["sessions"][0]["session_id"]
        
        # User 1 tries to revoke User 2's session
        cross_revoke_response = client.delete(
            f"/auth/sessions/{user2_session_id}",
            headers={"Authorization": f"Bearer {token1}"}
        )
        
        assert cross_revoke_response.status_code == 404  # Not found (their session)
        
        # Cleanup other user
        self.db.query(RefreshToken).filter(RefreshToken.user_id == other_user.id).delete()
        self.db.query(User).filter(User.id == other_user.id).delete()
        self.db.commit()


class TestSessionManagementEdgeCases:
    """Test edge cases and error conditions for session management."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.db = TestSessionLocal()
        yield
        self.db.close()
    
    def test_refresh_with_malformed_token(self):
        """Test refresh endpoint with malformed tokens."""
        test_cases = [
            "",  # Empty string
            "not.a.jwt",  # Invalid format
            "header.payload",  # Missing signature
            "header.payload.signature.extra",  # Too many parts
        ]
        
        for malformed_token in test_cases:
            response = client.post("/auth/refresh", json={
                "refresh_token": malformed_token
            })
            assert response.status_code == 401
    
    def test_sessions_without_authentication(self):
        """Test session endpoints without authentication."""
        # Test sessions listing
        response = client.get("/auth/sessions")
        assert response.status_code == 401
        
        # Test session revocation
        response = client.delete("/auth/sessions/fake-session-id")
        assert response.status_code == 401
        
        # Test revoke all sessions
        response = client.post("/auth/sessions/revoke-all")
        assert response.status_code == 401
    
    def test_revoke_nonexistent_session(self):
        """Test revoking a session that doesn't exist."""
        # Create user and login
        test_email = f"test-nonexistent-{uuid4().hex[:8]}@example.com"
        test_user = User(
            email=test_email,
            password="TestPassword123!",
            first_name="Test",
            last_name="User"
        )
        
        self.db.add(test_user)
        self.db.commit()
        
        login_response = client.post("/auth/login", json={
            "email": test_email,
            "password": "TestPassword123!"
        })
        
        access_token = login_response.json()["access_token"]
        
        # Try to revoke non-existent session
        response = client.delete(
            "/auth/sessions/non-existent-session-id",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 404
        
        # Cleanup
        self.db.query(RefreshToken).filter(RefreshToken.user_id == test_user.id).delete()
        self.db.query(User).filter(User.id == test_user.id).delete()
        self.db.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])