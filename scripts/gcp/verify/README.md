# Verify Scripts - Post-Deployment Testing

**Status**: ✅ **READY TO USE**

This folder contains scripts for testing deployed services.

---

## 🚀 Quick Start

After deploying your application, run these tests:

```bash
./health-check.sh           # Quick smoke test (~1 minute)
./integration-test.sh       # Full user flow test (~2-3 minutes)
```

---

## 📜 Script Reference

### health-check.sh

**Purpose**: Quick smoke test of deployed services

**What it tests**:
- ✅ Backend health endpoint (/health)
- ✅ Backend database connectivity
- ✅ Frontend accessibility
- ✅ API documentation (/docs)

**Run time**: ~30 seconds

**Safe to run**: Yes (read-only, no data changes)

**Example**:
```bash
./health-check.sh
```

**Expected output**:
```
========================================
Backend Health Check
========================================
ℹ Checking if backend service exists...
✓ Backend service URL: https://...
ℹ Testing /health endpoint...
✓ Health endpoint responding (HTTP 200)
{
  "status": "healthy",
  "database": "ok",
  "timestamp": "2025-10-07T..."
}
✓ Database connectivity: OK

========================================
Frontend Health Check
========================================
ℹ Checking if frontend service exists...
✓ Frontend service URL: https://...
ℹ Testing frontend accessibility...
✓ Frontend is accessible (HTTP 200)

========================================
Health Check Summary
========================================

✓ Backend: Healthy
✓ Frontend: Healthy

🎉 All services are healthy!
```

**When to run**:
- After every deployment
- Before making changes
- During troubleshooting
- In monitoring/alerting scripts

---

### integration-test.sh

**Purpose**: Test complete user flow end-to-end

**What it tests**:
1. **User Registration** - Create new user account
2. **User Login** - Authenticate and get token
3. **Authenticated Request** - Access protected endpoint
4. **API Documentation** - Check /docs accessibility
5. **Frontend Loading** - Verify frontend serves HTML

**Run time**: ~2-3 minutes

**Safe to run**: Yes (creates test user, cleans up after)

**Side effects**:
- Creates test user in database (email: test-{timestamp}@example.com)
- Test user persists in database (can be manually deleted later if needed)

**Example**:
```bash
./integration-test.sh
```

**Expected output**:
```
========================================
Test 1: User Registration
========================================
ℹ Registering test user: test-1696723456@example.com
✓ Registration successful (HTTP 201)
{
  "id": "uuid-here",
  "email": "test-1696723456@example.com",
  "first_name": "Test",
  "last_name": "User"
}

========================================
Test 2: User Login
========================================
ℹ Logging in as: test-1696723456@example.com
✓ Login successful (HTTP 200)
✓ Access token received

[... more tests ...]

========================================
Integration Test Summary
========================================

✓ User Registration: PASS
✓ User Login: PASS
✓ Authenticated Request: PASS
✓ API Documentation: PASS
✓ Frontend Loading: PASS

ℹ Tests passed: 5/5

🎉 Integration tests mostly successful!
ℹ Your application is working correctly
```

**When to run**:
- After first deployment
- After major code changes
- Before promoting to production (if you add staging)
- Weekly/monthly regression testing

---

## 🔍 Common Scenarios

### Quick Health Check After Deployment

```bash
./health-check.sh
```

If this passes, your deployment is healthy.

### Full Validation After First Deployment

```bash
./health-check.sh && ./integration-test.sh
```

Both should pass for successful deployment.

### Continuous Monitoring

Add health check to cron:

```bash
# Check every 5 minutes
*/5 * * * * /path/to/scripts/gcp/verify/health-check.sh || echo "Health check failed!" | mail -s "Alert" admin@example.com
```

### Before Making Changes

Always check current health:

```bash
./health-check.sh
# If healthy, proceed with changes
# If unhealthy, fix issues first
```

---

## 🐛 Troubleshooting

### Health Check Fails - Backend

**Symptoms**:
```
✗ Backend: Unhealthy
  HTTP 503 or timeout
```

**Solutions**:
1. Check if service is deployed:
   ```bash
   gcloud run services list --region=us-central1
   ```

2. Check Cloud Run logs:
   ```bash
   gcloud logging read "resource.labels.service_name=ai-resume-review-v2-backend-prod" --limit=50
   ```

3. Check if database is accessible:
   ```bash
   gcloud sql instances list
   ```

4. Verify secrets exist:
   ```bash
   gcloud secrets list
   ```

5. Check VPC connector:
   ```bash
   gcloud compute networks vpc-access connectors describe arr-v2-connector --region=us-central1
   ```

### Health Check Fails - Frontend

**Symptoms**:
```
✗ Frontend: Unhealthy
  HTTP 404 or timeout
```

**Solutions**:
1. Check if service is deployed:
   ```bash
   gcloud run services list --region=us-central1
   ```

2. Check frontend logs:
   ```bash
   gcloud logging read "resource.labels.service_name=ai-resume-review-v2-frontend-prod" --limit=50
   ```

3. Verify backend is healthy (frontend needs backend URL)

### Integration Test Fails - Registration

**Symptoms**:
```
✗ User Registration: FAIL
  HTTP 400 or 500
```

**Solutions**:
1. Check backend logs for validation errors
2. Verify database migrations ran: `cd backend && alembic current`
3. Check if database tables exist
4. Verify OpenAI API key is valid (if registration triggers AI)

### Integration Test Fails - Login

**Symptoms**:
```
✗ User Login: FAIL
  HTTP 401 or 500
```

**Solutions**:
1. Check if registration succeeded first
2. Verify JWT secret is set in Secret Manager
3. Check backend authentication configuration
4. Review backend logs for auth errors

---

## 📊 Test Coverage

### health-check.sh

**Coverage**:
- ✅ Service availability (Cloud Run)
- ✅ Basic endpoint functionality (/health)
- ✅ Database connectivity
- ✅ API documentation access

**Does NOT test**:
- ❌ Authentication
- ❌ Business logic
- ❌ AI agent functionality
- ❌ File uploads

### integration-test.sh

**Coverage**:
- ✅ User authentication flow
- ✅ API authentication (JWT tokens)
- ✅ Basic CRUD operations
- ✅ Frontend rendering

**Does NOT test**:
- ❌ Resume upload
- ❌ AI analysis
- ❌ Complex user flows
- ❌ Performance/load testing

---

## 🔧 Customization

### Adding More Tests

Edit `integration-test.sh` to add custom tests:

```bash
# Add after existing tests

test_resume_upload() {
    log_section "Test: Resume Upload"
    # Your test code here
}

# Call in main():
test_resume_upload || upload_status=$?
```

### Changing Test Data

Edit variables at top of `integration-test.sh`:

```bash
TEST_EMAIL="test-$(date +%s)@example.com"
TEST_PASSWORD="TestPassword123!"
```

---

## ✅ Success Criteria

**Tests pass when**:
- `health-check.sh` shows all services as healthy
- `integration-test.sh` passes at least 4/5 tests

**If less than 4/5 tests pass**, investigate failures before considering deployment successful.

---

## 🔗 Related Documentation

- [../deploy/README.md](../deploy/README.md) - Deployment guide
- [../README.md](../README.md) - Main scripts guide
- [../../../PHASE3_DEPLOYMENT_GUIDE.md](../../../PHASE3_DEPLOYMENT_GUIDE.md) - Deployment guide

---

**Last Updated**: 2025-10-07
