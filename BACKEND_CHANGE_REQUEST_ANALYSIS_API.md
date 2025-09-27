# Backend Change Request: Fix Analysis API Rate Limiter

## Issue Summary
The resume analysis API endpoint is failing with a 500 Internal Server Error due to incorrect rate limiter implementation.

## Error Details

### Current Error
```
ERROR - Unexpected error: RedisRateLimiter.check_rate_limit() got an unexpected keyword argument 'key'
```

### Location
- **File**: `backend/app/features/resume_analysis/api.py`
- **Lines**: 67-71
- **Endpoint**: `POST /api/v1/analysis/resumes/{resume_id}/analyze`

## Root Cause

The analysis API is using an outdated/incorrect rate limiter interface:

### Current Implementation (INCORRECT)
```python
# Lines 67-71 in backend/app/features/resume_analysis/api.py
await rate_limiter.check_rate_limit(
    key=f"analysis:{current_user.id}",
    max_requests=5,
    window_seconds=300  # 5 analyses per 5 minutes
)
```

### Expected Implementation (CORRECT)
Based on the rate limiter interface defined in `backend/app/core/rate_limiter.py`, the correct usage should be:

```python
from app.core.rate_limiter import rate_limiter, RateLimitExceeded, RateLimitType

# Apply rate limiting
is_allowed, rate_info = await rate_limiter.check_rate_limit(
    limit_type=RateLimitType.GENERAL,  # or create RateLimitType.ANALYSIS
    identifier=str(current_user.id)
)

if not is_allowed:
    raise RateLimitExceeded("Analysis rate limit exceeded")
```

## Required Changes

### Option 1: Quick Fix
Update lines 67-71 to use the correct rate limiter interface:

```python
# Replace lines 67-71 with:
is_allowed, rate_info = await rate_limiter.check_rate_limit(
    limit_type=RateLimitType.GENERAL,
    identifier=str(current_user.id)
)

if not is_allowed:
    raise RateLimitExceeded("Too many analysis requests. Please wait before analyzing more resumes.")
```

### Option 2: Proper Implementation
1. Add a new rate limit type in `backend/app/core/rate_limiter.py`:
```python
class RateLimitType(Enum):
    LOGIN = "login"
    REGISTRATION = "registration"
    PASSWORD_RESET = "password_reset"
    FILE_UPLOAD = "file_upload"
    GENERAL = "general"
    ANALYSIS = "analysis"  # Add this
```

2. Configure the rate limit for analysis:
```python
rate_limits = {
    RateLimitType.ANALYSIS: {"max_requests": 5, "window_seconds": 300},  # 5 per 5 minutes
    # ... other limits
}
```

3. Update the analysis API to use the new type:
```python
is_allowed, rate_info = await rate_limiter.check_rate_limit(
    limit_type=RateLimitType.ANALYSIS,
    identifier=str(current_user.id)
)
```

## Impact

### Current Impact
- **Severity**: HIGH - Complete feature failure
- **Affected Feature**: Resume Analysis
- **User Experience**: Users cannot analyze uploaded resumes
- **Error Type**: 500 Internal Server Error

### Systems Affected
- Resume analysis workflow
- Upload page analysis functionality
- Analysis results display

## Testing Required

After fixing, test the following scenarios:
1. Basic analysis request with valid resume ID
2. Rate limiting behavior (6th request within 5 minutes should fail)
3. Error handling for invalid resume IDs
4. Concurrent analysis requests

## Reference Implementation

The correct pattern is already implemented in `backend/app/features/resume_upload/api.py` lines 64-69:

```python
# Correct implementation example from upload API
is_allowed, rate_info = await rate_limiter.check_rate_limit(
    limit_type=RateLimitType.FILE_UPLOAD,
    identifier=str(current_user.id)
)
if not is_allowed:
    raise RateLimitExceeded("Upload rate limit exceeded")
```

## Priority
**CRITICAL** - This is blocking the entire analysis feature which is a core functionality of the application.

## Verification Steps

1. Check that the import includes `RateLimitType`:
   ```python
   from app.core.rate_limiter import rate_limiter, RateLimitExceeded, RateLimitType
   ```

2. Verify the rate limiter call returns a tuple:
   ```python
   is_allowed, rate_info = await rate_limiter.check_rate_limit(...)
   ```

3. Ensure proper error handling for rate limit exceeded

## Additional Notes

The same incorrect pattern might exist in other parts of the analysis API. Please review:
- Line 67-71: Primary issue location
- Any other rate limiter usage in the analysis module

This fix is required for the frontend analysis feature to work correctly.