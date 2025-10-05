# Migration 004: Raw AI Response Column - Deployment Guide

**Migration**: Add `raw_ai_response` JSONB column to `review_results` table  
**Date**: September 10, 2025  
**Priority**: High (Required for AI Integration MVP)  
**Risk Level**: Low (Backward-compatible, nullable column)

## 📋 Quick Reference

| Environment | Database | Migration File | Rollback File |
|------------|----------|---------------|---------------|
| Development | `ai_resume_review_dev` | `004_add_raw_ai_response_column.sql` | `004_rollback_raw_ai_response_column.sql` |
| Staging | `ai_resume_review_staging` | Same | Same |
| Production | `ai_resume_review_prod` | Same | Same |

## 🚀 Deployment Steps

### Phase 1: Development Environment

#### 1.1 Pre-Migration Checks
```bash
# Connect to development database
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev

# Check current table structure
\d review_results

# Count existing records (for reference)
SELECT COUNT(*) FROM review_results;

# Exit psql
\q
```

#### 1.2 Apply Migration
```bash
# Run migration script
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev \
  -f database/migrations/004_add_raw_ai_response_column.sql

# Expected output:
# NOTICE:  Migration successful: raw_ai_response column added to review_results table
```

#### 1.3 Verify Migration
```bash
# Verify column exists
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev -c "
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'review_results' 
AND column_name = 'raw_ai_response';"

# Expected output:
# column_name     | data_type | is_nullable
# ----------------+-----------+-------------
# raw_ai_response | jsonb     | YES
```

### Phase 2: Testing

#### 2.1 Test JSONB Storage
```sql
-- Connect to database and test
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev

-- Insert test data (if review_requests exist)
UPDATE review_results 
SET raw_ai_response = '{
  "success": true,
  "overall_score": 85,
  "test": "migration_validation"
}'::jsonb
WHERE id = (SELECT id FROM review_results LIMIT 1);

-- Query JSON data
SELECT 
  id,
  raw_ai_response->>'success' as success,
  raw_ai_response->>'overall_score' as score
FROM review_results 
WHERE raw_ai_response IS NOT NULL;

-- Clean up test data (optional)
UPDATE review_results 
SET raw_ai_response = NULL 
WHERE raw_ai_response->>'test' = 'migration_validation';
```

#### 2.2 Test Application Compatibility
```bash
# Restart backend to ensure no issues
./scripts/docker-dev.sh restart backend

# Check backend logs
./scripts/docker-dev.sh logs backend | tail -20

# Test API endpoints (should work without modification)
curl -X GET http://localhost:8000/health
```

### Phase 3: Rollback Testing (Optional but Recommended)

#### 3.1 Test Rollback Procedure
```bash
# Apply rollback
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev \
  -f database/migrations/004_rollback_raw_ai_response_column.sql

# Verify column removed
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev -c "
SELECT COUNT(*) 
FROM information_schema.columns 
WHERE table_name = 'review_results' 
AND column_name = 'raw_ai_response';"

# Re-apply migration after testing
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev \
  -f database/migrations/004_add_raw_ai_response_column.sql
```

### Phase 4: Staging Deployment

```bash
# 1. Create database backup
pg_dump -h staging-host -U postgres -d ai_resume_review_staging > backup_staging_$(date +%Y%m%d_%H%M%S).sql

# 2. Apply migration
psql -h staging-host -U postgres -d ai_resume_review_staging \
  -f database/migrations/004_add_raw_ai_response_column.sql

# 3. Run integration tests
pytest backend/tests/integration/

# 4. Monitor for 24 hours
```

### Phase 5: Production Deployment

#### 5.1 Pre-Deployment Checklist
- [ ] Staging testing completed successfully
- [ ] Database backup created
- [ ] Maintenance window scheduled
- [ ] Rollback procedure tested
- [ ] Team notified

#### 5.2 Production Migration
```bash
# 1. Create production backup
pg_dump -h prod-host -U postgres -d ai_resume_review_prod > backup_prod_$(date +%Y%m%d_%H%M%S).sql

# 2. Apply migration during maintenance window
psql -h prod-host -U postgres -d ai_resume_review_prod \
  -f database/migrations/004_add_raw_ai_response_column.sql

# 3. Verify migration
psql -h prod-host -U postgres -d ai_resume_review_prod -c "
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'review_results' 
AND column_name = 'raw_ai_response';"

# 4. Deploy updated backend code (if ready)
# kubectl apply -f k8s/backend-deployment.yaml
```

## 🔄 Rollback Procedure

If issues arise after migration:

```bash
# 1. Stop backend services (if necessary)
# kubectl scale deployment backend --replicas=0

# 2. Apply rollback
psql -h [host] -U postgres -d [database] \
  -f database/migrations/004_rollback_raw_ai_response_column.sql

# 3. Restore backend to previous version (if deployed)
# kubectl rollout undo deployment backend

# 4. Restart services
# kubectl scale deployment backend --replicas=3
```

## 📊 Monitoring

### Post-Migration Checks

```sql
-- Check for any errors in application logs
SELECT * FROM activity_logs 
WHERE created_at > NOW() - INTERVAL '1 hour'
AND action LIKE '%error%';

-- Monitor table size growth
SELECT 
  pg_size_pretty(pg_table_size('review_results')) as table_size,
  COUNT(*) as total_records,
  COUNT(raw_ai_response) as records_with_ai_response
FROM review_results;

-- Check JSON query performance (if using)
EXPLAIN ANALYZE
SELECT * FROM review_results 
WHERE raw_ai_response->>'success' = 'true';
```

## ⚠️ Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| "column already exists" error | Column was already added; safe to ignore or check with `\d review_results` |
| Permission denied | Ensure user has ALTER TABLE privileges |
| Disk space concerns | JSONB is compressed; monitor with query above |
| Slow JSON queries | Consider adding GIN index (see migration comments) |
| Application errors | Ensure backend code is updated to handle nullable column |

## 📝 Post-Migration Tasks

1. **Update Documentation**
   - [ ] Update API documentation if endpoints change
   - [ ] Update data dictionary with new column

2. **Backend Updates**
   - [ ] Update SQLAlchemy model (see `Update SQLAlchemy Model` section)
   - [ ] Deploy backend code that uses new column

3. **Monitoring**
   - [ ] Set up alerts for JSON column size growth
   - [ ] Monitor query performance for first week

## 🔗 Related Files

- Migration Script: `database/migrations/004_add_raw_ai_response_column.sql`
- Rollback Script: `database/migrations/004_rollback_raw_ai_response_column.sql`
- Change Request: `database/docs/DBA_SCHEMA_CHANGE_REQUEST.md`
- Backend Model: `backend/app/models/review.py` (to be updated)

## 📞 Support Contacts

- **DBA Team**: #database-support (Slack)
- **Backend Team**: #backend-engineering (Slack)
- **On-Call**: Check PagerDuty schedule

---

*Last Updated: September 10, 2025*