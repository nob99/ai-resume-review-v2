# Database Schema Change Request

**Date**: September 9, 2025  
**Requested by**: Backend Engineering Team  
**Priority**: High (Required for AI Integration MVP)  
**Target Sprint**: Sprint 004

---

## 📋 Change Summary

**Add new field to `review_results` table to store complete raw AI response JSON for flexible frontend processing.**

---

## 🎯 Business Justification

### Problem Statement
The current `detailed_scores` JSON field in `review_results` table only stores AI score breakdowns. However, for MVP flexibility, we need to store the complete raw AI response to:

1. **Enable Frontend Flexibility**: Allow frontend to adapt to AI response format changes without backend code changes
2. **Accelerate Development**: Reduce complex backend mapping logic during MVP phase
3. **Future-Proof Design**: Support evolving AI response formats based on user feedback
4. **Improve Debugging**: Store complete AI responses for troubleshooting and analysis

### Impact if Not Implemented
- Backend team needs to implement complex AI-to-database mapping logic
- Every AI format change requires backend code updates and deployments
- Slower MVP iteration cycles
- Potential data loss if AI response format changes unexpectedly

---

## 📊 Schema Change Details

### Table: `review_results`

**Add New Column:**
```sql
ALTER TABLE review_results 
ADD COLUMN raw_ai_response JSONB NULL;
```

**Column Specifications:**
- **Name**: `raw_ai_response`
- **Type**: `JSONB` (PostgreSQL native JSON with indexing support)
- **Nullable**: `TRUE` (for backward compatibility with existing records)
- **Default**: `NULL`
- **Index**: Consider adding GIN index for JSON queries (optional for MVP)

**Sample JSON Structure:**
```json
{
  "success": true,
  "analysis_id": "uuid",
  "overall_score": 85.5,
  "market_tier": "senior",
  "summary": "Executive summary...",
  "structure": {
    "scores": {
      "format": 90,
      "organization": 85,
      "tone": 88,
      "completeness": 92
    },
    "feedback": {
      "issues": [...],
      "recommendations": [...]
    }
  },
  "appeal": {
    "scores": {
      "achievement_relevance": 87,
      "skills_alignment": 82
    },
    "feedback": {
      "relevant_achievements": [...],
      "improvement_areas": [...]
    }
  }
}
```

---

## 🔄 Migration Strategy

### Migration Script Template
```sql
-- Add column
ALTER TABLE review_results 
ADD COLUMN raw_ai_response JSONB NULL;

-- Add comment
COMMENT ON COLUMN review_results.raw_ai_response IS 'Complete raw AI response JSON for flexible frontend processing';

-- Optional: Add GIN index for JSON queries
-- CREATE INDEX CONCURRENTLY idx_review_results_raw_ai_response 
-- ON review_results USING GIN (raw_ai_response);
```

### Data Migration
- **No data migration required** - new field will be `NULL` for existing records
- New records will populate this field going forward
- Existing structured fields (`overall_score`, `detailed_scores`) remain unchanged for backward compatibility

### Rollback Plan
```sql
-- Rollback: Drop the column if needed
ALTER TABLE review_results 
DROP COLUMN IF EXISTS raw_ai_response;
```

---

## ⚡ Performance Considerations

### Storage Impact
- **Estimated JSON Size**: 5-15KB per record (based on AI response format)
- **Monthly Growth**: ~50MB (assuming 1000 reviews/month)
- **Annual Impact**: ~600MB additional storage
- **Assessment**: Minimal impact on database performance

### Query Performance
- JSONB provides efficient storage and querying
- No impact on existing queries (new column is optional)
- Future JSON queries will benefit from potential GIN indexing

### Indexing Recommendation
```sql
-- Consider adding after MVP validation:
CREATE INDEX CONCURRENTLY idx_review_results_raw_ai_response_gin 
ON review_results USING GIN (raw_ai_response);
```

---

## 🧪 Testing Requirements

### Pre-Migration Testing
- [ ] Test migration script on development database
- [ ] Verify no impact on existing queries
- [ ] Validate JSON storage and retrieval

### Post-Migration Validation
- [ ] Confirm new column exists and accepts JSONB data
- [ ] Test application can write/read raw AI responses
- [ ] Verify backward compatibility with existing records

---

## 📅 Timeline & Deployment

### Requested Timeline
- **Migration Script Review**: September 10, 2025
- **Development DB Migration**: September 11, 2025  
- **Production Migration**: September 12, 2025 (during maintenance window)

### Deployment Coordination
- **Backend Code**: Ready to deploy after DB migration
- **Frontend Updates**: No immediate changes required
- **API Changes**: Backward compatible - existing endpoints unchanged

---

## 🔒 Security & Compliance

### Data Classification
- **Type**: Application data (AI analysis results)
- **Sensitivity**: Medium (business analysis, no PII)
- **Retention**: Follow existing `review_results` retention policy

### Access Control
- Inherits existing `review_results` table permissions
- No additional security requirements

---

## 📋 Approval Checklist

- [ ] **DBA Review**: Schema change approved
- [ ] **Migration Script**: Reviewed and tested
- [ ] **Performance Impact**: Assessed and approved
- [ ] **Backup Plan**: Verified before production migration
- [ ] **Rollback Procedure**: Documented and tested
- [ ] **Development Migration**: Completed successfully
- [ ] **Production Migration**: Scheduled and executed

---

## 📞 Contact Information

**Primary Contact**: Backend Engineering Team  
**Technical Lead**: [Backend Engineer Name]  
**Slack Channel**: #backend-engineering  
**Priority**: High - Required for Sprint 004 AI Integration delivery

---

## 📎 Related Documentation

- `backend/app/AI_INTEGRATION_ARCHITECTURE.md` - Architecture overview
- `database/models/review.py` - Current model definition
- `ai_agents/orchestrator.py` - AI response format source

---

*This change request supports the AI Integration MVP implementation and enables flexible, future-proof resume analysis capabilities.*