# Upload Layer Tests

This directory contains systematic layer-by-layer tests to diagnose upload system issues.

## Overview

The upload system has been refactored from raw SQL to ORM + Repository pattern, but browser uploads are returning 500 errors. These tests isolate each architectural layer to pinpoint the exact failure point.

## Architecture Layers

```
Browser Upload Request
       ↓
[Layer 4] API Layer (FastAPI endpoints, auth, validation)
       ↓
[Layer 3] Service Layer (UploadService, business logic coordination)
       ↓
[Layer 2] File Storage Layer (file_service.store_uploaded_file())
       ↓
[Layer 1] Repository Layer (AnalysisRepository, ORM operations)
       ↓
    Database
```

## Test Scripts

### 1. `layer_1_repository_test.py`
**Repository/Database Layer**
- Tests ORM operations and database connectivity
- Verifies AnalysisRepository CRUD operations
- Checks SQLAlchemy 2.0 compatibility

### 2. `layer_2_file_storage_test.py`
**File Storage Layer**
- Tests file validation and storage
- Verifies `store_uploaded_file()` functionality
- Checks directory permissions and file system operations

### 3. `layer_3_service_test.py`
**Service Layer**
- Tests UploadService dependency injection
- Verifies business logic coordination
- Tests service methods and error handling

### 4. `layer_4_api_test.py`
**API Layer**
- Tests FastAPI endpoint routing
- Verifies authentication and validation
- Tests request/response handling

### 5. `run_layer_tests.py`
**Test Runner**
- Executes all layer tests in sequence
- Stops at first failure for focused debugging
- Provides diagnostic guidance

## Usage

### Quick Run (Recommended)
```bash
cd backend/tests/upload
python run_layer_tests.py
```

### Individual Layer Testing
```bash
# Test specific layer
python layer_1_repository_test.py
python layer_2_file_storage_test.py
python layer_3_service_test.py
python layer_4_api_test.py
```

### Docker Environment
```bash
# Run inside Docker container
docker exec -it backend python tests/upload/run_layer_tests.py
```

## Expected Output

### Success Case
```
🎉 ALL LAYERS PASSED!
The upload system architecture is working correctly.
Issue may be in integration or runtime environment.
```

### Failure Case
```
🛑 STOPPING: Layer 2 (File Storage) failed
Fix this layer before proceeding to higher layers.

💥 DIAGNOSIS: Upload system failed at Layer 2: File Storage
🔧 Focus on: File validation, storage directories, permissions
```

## Debugging Strategy

1. **Bottom-Up Approach**: Fix lower layers before testing higher layers
2. **Focused Debugging**: Tests stop at first failure to avoid confusion
3. **Layer Isolation**: Each test is independent and doesn't rely on other layers
4. **Progressive Validation**: Only proceed to next layer after current layer passes

## Common Issues

### Layer 1 (Repository) Failures
- Database connection issues
- SQLAlchemy 2.0 compatibility problems  
- ORM model/schema mismatches

### Layer 2 (File Storage) Failures
- File validation logic errors
- Storage directory permissions
- File system path issues

### Layer 3 (Service) Failures
- Dependency injection problems
- Business logic coordination errors
- Service method implementation bugs

### Layer 4 (API) Failures
- FastAPI routing configuration
- Authentication/authorization issues
- Request validation problems

## Integration Testing

After all layers pass individually, the issue may be in:
- Inter-layer communication
- Runtime environment configuration
- Network connectivity
- Production-specific settings

## File Structure

```
backend/tests/upload/
├── README.md                     # This file
├── run_layer_tests.py           # Test runner
├── layer_1_repository_test.py   # Repository layer tests
├── layer_2_file_storage_test.py # File storage layer tests
├── layer_3_service_test.py      # Service layer tests
└── layer_4_api_test.py          # API layer tests
```

## Recent Refactor Context

The upload system was recently refactored (commit 8a5ec20):
- ✅ Eliminated all raw SQL (16 → 0 queries)
- ✅ Implemented Repository pattern
- ✅ Added Service layer architecture  
- ✅ Fixed SQLAlchemy 2.0 compatibility
- ❌ Browser upload still returns 500 error

These tests help identify if the refactor introduced any issues at specific architectural layers.