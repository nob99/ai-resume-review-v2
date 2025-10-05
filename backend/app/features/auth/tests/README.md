# Auth Feature Tests

This directory contains comprehensive tests for the new auth feature implementation, organized according to the feature-based architecture migration.

## Test Structure

```
app/features/auth/tests/
├── conftest.py              # Shared pytest configuration and fixtures
├── fixtures/                # Test data and mock objects
│   ├── __init__.py
│   └── mock_data.py        # Comprehensive mock data and test scenarios
├── unit/                    # Pure unit tests (no external dependencies)
│   ├── __init__.py
│   ├── test_api.py         # FastAPI route handlers
│   ├── test_service.py     # Business logic layer
│   ├── test_repository.py  # Data access layer
│   └── test_models.py      # SQLAlchemy models
├── integration/             # Integration tests (with real DB/Redis)
│   ├── __init__.py
│   └── test_auth_flow.py   # Complete authentication flows
└── README.md               # This file
```

## Test Categories

### Unit Tests (Pure isolation, mocked dependencies)
- **test_service.py**: Tests `AuthService` business logic with mocked repositories
- **test_repository.py**: Tests `UserRepository` and `RefreshTokenRepository` with mocked database
- **test_api.py**: Tests FastAPI route handlers with mocked service layer  
- **test_models.py**: Tests `User` and `RefreshToken` model behavior and validation

### Integration Tests (Real database and services)
- **test_auth_flow.py**: Tests complete authentication workflows end-to-end

### Test Fixtures
- **mock_data.py**: Comprehensive mock data, factory classes, and test scenarios
- **conftest.py**: Shared pytest fixtures and configuration

## Coverage Areas

### Authentication Flows
- ✅ User registration with validation
- ✅ Login with password verification  
- ✅ JWT token generation and validation
- ✅ Token refresh mechanism
- ✅ Logout with token blacklisting
- ✅ Password change functionality

### Security Features
- ✅ Password strength validation
- ✅ Account locking after failed attempts
- ✅ Rate limiting integration
- ✅ Token expiration handling
- ✅ Session management

### Error Handling
- ✅ Invalid credentials
- ✅ Non-existent users
- ✅ Expired tokens
- ✅ Database errors
- ✅ Validation errors

### API Layer
- ✅ Request/response validation
- ✅ HTTP status codes
- ✅ Authentication middleware
- ✅ CORS handling
- ✅ Error responses

## Running Tests

### Run all auth tests
```bash
# All auth feature tests
pytest app/features/auth/tests/ -v

# With coverage
pytest app/features/auth/tests/ --cov=app/features/auth --cov-report=html
```

### Run specific test categories
```bash
# Unit tests only (fast)
pytest app/features/auth/tests/unit/ -v

# Integration tests only
pytest app/features/auth/tests/integration/ -v

# Skip slow tests
pytest app/features/auth/tests/ -v -m "not slow"

# Skip integration tests (if DB not available)
pytest app/features/auth/tests/ -v -m "not integration"
```

### Run specific test files
```bash
# Test specific component
pytest app/features/auth/tests/unit/test_service.py -v

# Test specific scenarios  
pytest app/features/auth/tests/unit/test_service.py::TestAuthServiceLogin::test_successful_login -v
```

### Run with different configurations
```bash
# Test with new auth implementation (default)
USE_NEW_AUTH=true pytest app/features/auth/tests/

# Compare old vs new auth behavior
USE_NEW_AUTH=false pytest tests/auth/
USE_NEW_AUTH=true pytest app/features/auth/tests/
```

## Test Data Management

### Mock Data
- **MockAuthData**: Static test data (users, requests, responses)
- **MockAuthComponents**: Factory methods for creating mock objects
- **AuthTestScenarios**: Pre-defined test scenarios for common patterns

### Test Users
Tests create unique users with UUID-based emails to avoid conflicts:
- `integration.test.{uuid}@example.com`
- `api.test.{uuid}@example.com`
- `repo.test.{uuid}@example.com`

### Fixtures
- Shared fixtures in `conftest.py` for common test objects
- Component-specific fixtures in individual test files
- Database fixtures for integration tests

## Migration Validation

These tests validate that the new auth implementation:

1. **Maintains API Compatibility**: Same endpoints, same request/response formats
2. **Preserves Security**: Password hashing, rate limiting, token validation
3. **Improves Architecture**: Better separation of concerns, cleaner code structure
4. **Handles Edge Cases**: Error scenarios, validation, timeout handling

## Test Philosophy

### Unit Tests
- **Fast**: Run in milliseconds, no external dependencies
- **Isolated**: Each test focuses on one specific behavior
- **Reliable**: Consistent results, not affected by external state
- **Comprehensive**: Cover all code paths and edge cases

### Integration Tests  
- **Realistic**: Use real database and service connections
- **End-to-end**: Test complete workflows from API to database
- **Environment-aware**: Can be skipped if dependencies unavailable
- **Cleanup**: Properly clean up test data

## Migration Strategy

These tests support the migration from old auth to new auth by:

1. **Parallel Testing**: Can test both old and new implementations
2. **Behavioral Validation**: Ensure identical external behavior
3. **Regression Prevention**: Catch any breaking changes
4. **Confidence Building**: Comprehensive coverage provides migration confidence

## Future Enhancements

Potential test improvements:
- Performance benchmarking tests
- Security penetration testing scenarios
- Load testing for concurrent sessions
- Advanced mock scenarios for edge cases
- API contract testing with OpenAPI schemas

## Troubleshooting

### Common Issues

**Integration tests fail with database errors**
- Ensure PostgreSQL is running: `./scripts/docker-dev.sh status`
- Check database connection in `.env`
- Run with `SKIP_INTEGRATION_TESTS=true` to skip DB tests

**Import errors in tests**
- Ensure you're running from the backend directory
- Check Python path includes the current directory
- Verify all `__init__.py` files are present

**Mocking issues**
- Check that mock objects have the expected interface
- Verify async mocks use `AsyncMock` not `Mock`
- Ensure fixture scoping is appropriate

### Debugging Tests
```bash
# Run with detailed output
pytest app/features/auth/tests/ -v -s

# Run single test with debugging
pytest app/features/auth/tests/unit/test_service.py::TestAuthServiceLogin::test_successful_login -v -s --pdb

# Run with coverage to find untested code
pytest app/features/auth/tests/ --cov=app/features/auth --cov-report=term-missing
```