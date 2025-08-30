"""
AUTH-003 Session Management Test Suite

This test suite covers the comprehensive session management functionality including:
- Refresh token generation and validation
- Session tracking and concurrent session limits
- Token rotation security
- Session listing and revocation APIs
- Security isolation between users
- Edge cases and error handling

Test Structure:
- unit/: Unit tests for models and security functions
- integration/: Full API and database integration tests

Key Test Areas:
1. Refresh Token Security
2. Session Management APIs
3. Concurrent Session Limits
4. Token Rotation
5. User Session Isolation
6. Error Handling and Edge Cases
"""

__version__ = "1.0.0"
__test_suite__ = "AUTH-003_session_management"