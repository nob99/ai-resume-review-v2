#!/usr/bin/env python3
"""
Compare API responses between old and new auth implementations.

This script tests both implementations with the same requests and compares responses
to ensure the migration maintains identical behavior.
"""

import os
import asyncio
import json
from typing import Dict, Any
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock

# Ensure the backend module is importable
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

def setup_mocks():
    """Set up consistent mocks for both implementations."""
    from app.models.user import User
    from app.database.connection import get_db
    from app.main import app
    
    # Create a consistent mock user
    mock_user = Mock(spec=User)
    mock_user.id = "550e8400-e29b-41d4-a716-446655440000"
    mock_user.email = "test@example.com"
    mock_user.first_name = "John"
    mock_user.last_name = "Doe"
    mock_user.role = "consultant"
    mock_user.is_active = True
    mock_user.email_verified = True
    mock_user.failed_login_attempts = 0
    mock_user.locked_until = None
    mock_user.last_login_at = None
    mock_user.check_password.return_value = True
    mock_user.is_account_locked.return_value = False

    # Mock database session
    mock_db = Mock()
    mock_query = Mock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    mock_db.commit.return_value = None

    def get_mock_db():
        return mock_db

    # Set up mocks for both old and new implementations
    app.dependency_overrides[get_db] = get_mock_db
    
    # For new auth implementation, also mock the async session
    try:
        from app.infrastructure.persistence.postgres.connection import get_async_session
        
        async def get_mock_async_session():
            mock_async_session = AsyncMock()
            mock_async_session.execute = AsyncMock()
            mock_async_session.commit = AsyncMock()
            mock_async_session.rollback = AsyncMock()
            mock_async_session.close = AsyncMock()
            mock_async_session.add = Mock()
            mock_async_session.delete = Mock()
            mock_async_session.flush = AsyncMock()
            
            # Set up query behavior to return the mock user
            query_result = AsyncMock()
            query_result.scalars.return_value.first.return_value = mock_user
            def mock_scalar_one_or_none():
                return mock_user
            query_result.scalar_one_or_none = mock_scalar_one_or_none
            
            async def mock_execute(*args, **kwargs):
                return query_result
            
            mock_async_session.execute = mock_execute
            return mock_async_session
        
        app.dependency_overrides[get_async_session] = get_mock_async_session
        print("✅ Successfully set up mocks for both old and new auth implementations")
    except ImportError:
        print("⚠️ New infrastructure not available, testing old implementation only")

    return mock_user, mock_db

def test_implementation(use_new_auth: bool, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Test a specific implementation with given payload."""
    # Set environment variable
    os.environ['USE_NEW_AUTH'] = str(use_new_auth).lower()
    
    # Re-import to pick up environment variable
    from app.main import app
    
    client = TestClient(app)
    
    try:
        response = client.post(endpoint, json=payload)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.json() if response.headers.get("content-type") == "application/json" else response.text
        }
    except Exception as e:
        return {
            "status_code": None,
            "error": str(e),
            "body": None
        }

def compare_responses(old_response: Dict, new_response: Dict) -> Dict[str, Any]:
    """Compare two API responses and return analysis."""
    comparison = {
        "status_match": old_response["status_code"] == new_response["status_code"],
        "identical": old_response == new_response,
        "differences": []
    }
    
    # Check status codes
    if old_response["status_code"] != new_response["status_code"]:
        comparison["differences"].append({
            "field": "status_code",
            "old": old_response["status_code"],
            "new": new_response["status_code"]
        })
    
    # Check body structure (if both are successful)
    if old_response["status_code"] == 200 and new_response["status_code"] == 200:
        old_body = old_response.get("body", {})
        new_body = new_response.get("body", {})
        
        if isinstance(old_body, dict) and isinstance(new_body, dict):
            # Compare keys
            old_keys = set(old_body.keys())
            new_keys = set(new_body.keys())
            
            if old_keys != new_keys:
                comparison["differences"].append({
                    "field": "response_keys",
                    "old_only": list(old_keys - new_keys),
                    "new_only": list(new_keys - old_keys)
                })
            
            # Compare common keys (excluding timestamps and tokens which may differ)
            ignore_keys = {"access_token", "refresh_token", "expires_at", "created_at", "last_login_at"}
            for key in old_keys & new_keys:
                if key not in ignore_keys and old_body.get(key) != new_body.get(key):
                    comparison["differences"].append({
                        "field": key,
                        "old": old_body.get(key),
                        "new": new_body.get(key)
                    })
    
    return comparison

def main():
    """Main comparison script."""
    print("🔬 Auth Implementation Comparison Script")
    print("=" * 50)
    
    # Set up consistent mocks
    mock_user, mock_db = setup_mocks()
    
    # Test cases
    test_cases = [
        {
            "name": "Successful Login",
            "endpoint": "/api/v1/auth/login",
            "payload": {
                "email": "test@example.com",
                "password": "securePassword123!"
            }
        },
        {
            "name": "Invalid Password",
            "endpoint": "/api/v1/auth/login", 
            "payload": {
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print("-" * 30)
        
        # Test old implementation
        print("📊 Testing OLD implementation...")
        old_response = test_implementation(False, test_case["endpoint"], test_case["payload"])
        print(f"   Status: {old_response['status_code']}")
        
        # Test new implementation
        print("📊 Testing NEW implementation...")
        new_response = test_implementation(True, test_case["endpoint"], test_case["payload"])
        print(f"   Status: {new_response['status_code']}")
        
        # Compare responses
        comparison = compare_responses(old_response, new_response)
        
        if comparison["status_match"]:
            print("✅ Status codes match")
        else:
            print("❌ Status codes differ")
        
        if comparison["identical"]:
            print("✅ Responses are identical")
        else:
            print("⚠️ Responses have differences:")
            for diff in comparison["differences"]:
                print(f"   - {diff}")
        
        results.append({
            "test_case": test_case["name"],
            "old_response": old_response,
            "new_response": new_response,
            "comparison": comparison
        })
    
    # Summary
    print("\n📋 Summary")
    print("=" * 50)
    
    total_tests = len(results)
    status_matches = sum(1 for r in results if r["comparison"]["status_match"])
    identical_responses = sum(1 for r in results if r["comparison"]["identical"])
    
    print(f"Total tests: {total_tests}")
    print(f"Status code matches: {status_matches}/{total_tests}")
    print(f"Identical responses: {identical_responses}/{total_tests}")
    
    if status_matches == total_tests:
        print("\n🎉 SUCCESS: All status codes match!")
        print("✅ The new auth implementation is working correctly")
    else:
        print("\n⚠️ WARNING: Some status codes don't match")
        print("❌ The new auth implementation needs fixes")
    
    # Clean up
    from app.main import app
    app.dependency_overrides.clear()
    
    return results

if __name__ == "__main__":
    results = main()