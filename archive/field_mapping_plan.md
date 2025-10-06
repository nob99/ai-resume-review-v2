# Field Mapping Plan - Model Adaptation Strategy

**Date**: September 9, 2025  
**Purpose**: Map new SQLAlchemy models to existing database schema  
**Strategy**: Adapt code to match production schema (zero database changes)

## Executive Summary

Our new models have **significant mismatches** with the existing schema:
- **User/RefreshToken models**: ~90% compatible ✅
- **FileUpload model**: ~40% compatible ⚠️ 
- **ResumeAnalysis model**: 0% compatible ❌ (wrong pattern entirely)

The existing schema is **more comprehensive** than our new models, with additional fields for performance tracking, security features, and workflow management.

## 1. Authentication Models (auth.py)

### User Model Mapping

| New Model Field | Existing Table Column | Status | Action Required |
|-----------------|----------------------|---------|-----------------|
| `id` (UUID) | `id` (uuid) | ✅ Match | None |
| `email` | `email` | ✅ Match | None |
| `password_hash` | `password_hash` | ✅ Match | None |
| `first_name` | `first_name` | ✅ Match | None |
| `last_name` | `last_name` | ✅ Match | None |
| `role` | `role` | ✅ Match | None |
| `is_active` | `is_active` | ✅ Match | None |
| `email_verified` | `email_verified` | ✅ Match | None |
| `created_at` | `created_at` | ✅ Match | None |
| `updated_at` | `updated_at` | ✅ Match | None |
| `last_login_at` | `last_login_at` | ✅ Match | None |
| `password_changed_at` | `password_changed_at` | ✅ Match | None |
| `failed_login_attempts` | `failed_login_attempts` | ✅ Match | None |
| `locked_until` | `locked_until` | ✅ Match | None |

**Relationships to Fix**:
```python
# Current (incorrect):
file_uploads = relationship("FileUpload", back_populates="user")
analyses = relationship("ResumeAnalysis", back_populates="user")

# Should be:
file_uploads = relationship("FileUpload", back_populates="user")
analysis_requests = relationship("AnalysisRequest", back_populates="user")
prompts = relationship("Prompt", back_populates="created_by_user")
```

### RefreshToken Model Mapping

| New Model Field | Existing Table Column | Status | Action Required |
|-----------------|----------------------|---------|-----------------|
| `id` (UUID) | `id` (uuid) | ✅ Match | None |
| `user_id` | `user_id` | ✅ Match | None |
| `token_hash` | `token_hash` | ✅ Match | None |
| `session_id` | `session_id` | ✅ Match | None |
| `expires_at` | `expires_at` | ✅ Match | None |
| `created_at` | `created_at` | ✅ Match | None |
| `last_used_at` | `last_used_at` | ✅ Match | None |
| `status` | `status` | ✅ Match | None |
| `device_info` | `device_info` | ✅ Match | None |
| `ip_address` | `ip_address` | ✅ Match | None |

**Verdict**: ✅ **Auth models are 90% compatible** - Minor relationship fixes needed

## 2. File Upload Model (files.py)

### FileUpload Model Mapping

| New Model Field | Existing Table Column | Status | Action Required |
|-----------------|----------------------|---------|-----------------|
| `id` | `id` | ✅ Match | None |
| `filename` | `filename` | ✅ Match | None |
| `original_filename` | `original_filename` | ✅ Match | None |
| `file_type` | ❌ NO MATCH | ❌ Missing | Use `mime_type` instead |
| `file_size` | `file_size` | ✅ Match | None |
| `mime_type` | `mime_type` | ✅ Match | None |
| `status` | `status` | ⚠️ Partial | Different enum values |
| `extracted_text` | `extracted_text` | ✅ Match | None |
| `extraction_metadata` (JSON) | ❌ NO MATCH | ❌ Missing | Use multiple fields |
| `error_message` | `error_message` | ✅ Match | None |
| `user_id` | `user_id` | ✅ Match | None |
| `upload_started_at` | ❌ NO MATCH | ❌ Missing | Use `created_at` |
| `upload_completed_at` | ❌ NO MATCH | ❌ Missing | Use `completed_at` |
| `processing_time_ms` | `processing_time` | ⚠️ Partial | Different unit (ms vs unspecified) |
| `created_at` | `created_at` | ✅ Match | None |
| `updated_at` | `updated_at` | ✅ Match | None |

### Missing from New Model (Must Add)

| Existing Column | Type | Purpose | Priority |
|-----------------|------|---------|----------|
| `file_hash` | varchar(64) | **Security: SHA256 for integrity** | 🔴 HIGH |
| `progress` | integer | **UX: Processing progress 0-100%** | 🔴 HIGH |
| `target_role` | varchar(255) | **Analysis context** | 🟡 MEDIUM |
| `target_industry` | varchar(255) | **Analysis context** | 🟡 MEDIUM |
| `experience_level` | varchar(20) | **Analysis context** | 🟡 MEDIUM |
| `word_count` | integer | **Content metrics** | 🟢 LOW |
| `character_count` | integer | **Content metrics** | 🟢 LOW |
| `extraction_method` | varchar(50) | **Audit: pdfplumber/pypdf2** | 🟢 LOW |
| `detected_sections` | jsonb | **AI: Resume sections** | 🟡 MEDIUM |
| `validation_time` | integer | **Performance tracking** | 🟢 LOW |
| `extraction_time` | integer | **Performance tracking** | 🟢 LOW |
| `completed_at` | timestamptz | **Workflow tracking** | 🔴 HIGH |

### Status Enum Mismatch

```python
# NEW MODEL Status values:
PENDING, UPLOADING, VALIDATING, EXTRACTING, COMPLETED, ERROR, CANCELLED

# EXISTING TABLE Status values (CHECK constraint):
pending, validating, extracting, completed, error

# MAPPING REQUIRED:
- Remove: UPLOADING, CANCELLED (not supported)
- Lowercase all values
```

## 3. Analysis Models (analysis.py) ❌ **COMPLETE REWRITE NEEDED**

### Critical Issue: Wrong Pattern

**New Model**: Single `resume_analyses` table  
**Existing Schema**: Two-table pattern (`analysis_requests` + `analysis_results`)

### Required New Models

#### AnalysisRequest Model (NEW)

```python
class AnalysisRequest(Base):
    __tablename__ = "analysis_requests"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    status = Column(String(50), default='pending')  # pending/processing/completed/failed
    target_role = Column(String(255))
    target_industry = Column(String(255))
    experience_level = Column(String(50))  # entry/mid/senior/executive
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User")
    analysis_result = relationship("AnalysisResult", back_populates="request", uselist=False)
    prompt_history = relationship("PromptHistory", back_populates="request")
```

#### AnalysisResult Model (NEW)

```python
class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID, ForeignKey("analysis_requests.id"), nullable=False)
    overall_score = Column(Integer)  # 0-100
    strengths = Column(ARRAY(Text))  # PostgreSQL array
    weaknesses = Column(ARRAY(Text))  # PostgreSQL array
    recommendations = Column(ARRAY(Text))  # PostgreSQL array
    formatting_score = Column(Integer)  # 0-100
    content_score = Column(Integer)  # 0-100
    keyword_optimization_score = Column(Integer)  # 0-100
    detailed_feedback = Column(JSON)  # JSONB
    ai_model_used = Column(String(100), nullable=False)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    # Relationships
    request = relationship("AnalysisRequest", back_populates="analysis_result")
```

### Field Mapping from ResumeAnalysis → New Models

| Old Field | New Model | New Field | Notes |
|-----------|-----------|-----------|-------|
| `file_upload_id` | ❌ Remove | - | Use `file_path` in requests |
| `user_id` | AnalysisRequest | `user_id` | Move to request |
| `industry` | AnalysisRequest | `target_industry` | Rename |
| `status` | AnalysisRequest | `status` | Move to request |
| `overall_score` | AnalysisResult | `overall_score` | Keep |
| `market_tier` | ❌ Remove | - | Not in existing schema |
| `structure_scores` | AnalysisResult | `detailed_feedback` | Merge into JSONB |
| `appeal_scores` | AnalysisResult | `detailed_feedback` | Merge into JSONB |
| `confidence_metrics` | AnalysisResult | `detailed_feedback` | Merge into JSONB |
| `structure_feedback` | AnalysisResult | `strengths/weaknesses` | Split into arrays |
| `appeal_feedback` | AnalysisResult | `recommendations` | Convert to array |
| `analysis_summary` | AnalysisResult | `detailed_feedback` | Store in JSONB |
| `improvement_suggestions` | AnalysisResult | `recommendations` | Add to array |
| `processing_time_seconds` | AnalysisResult | `processing_time_ms` | Convert to ms |
| `error_message` | AnalysisRequest | - | Store in request status |
| `retry_count` | ❌ Remove | - | Not in existing schema |
| `ai_model_version` | AnalysisResult | `ai_model_used` | Rename |
| `ai_tokens_used` | AnalysisResult | `detailed_feedback` | Store in JSONB |

## 4. Missing Models (Need to Create)

### Prompt Model
```python
class Prompt(Base):
    __tablename__ = "prompts"
    # Implementation needed for AI prompt templates
```

### PromptHistory Model
```python
class PromptHistory(Base):
    __tablename__ = "prompt_history"
    # Implementation needed for audit trail
```

## Implementation Priority

### Phase 1: Critical Fixes (Day 1)
1. ✅ Fix User model relationships
2. ✅ Fix RefreshToken model (minimal changes)
3. ❌ **Complete rewrite** of FileUpload model to match schema
4. ❌ **Complete rewrite** of analysis models (two-table pattern)

### Phase 2: Missing Features (Day 2)
1. Add Prompt model
2. Add PromptHistory model
3. Add missing fields to FileUpload
4. Implement proper enum mappings

### Phase 3: Service Layer Updates (Day 3)
1. Update file upload service to use new fields
2. Rewrite analysis service for two-table pattern
3. Update API responses to match new structure

## Key Decisions Required

### 1. FileUpload Status Values
**Question**: Should we keep `UPLOADING` and `CANCELLED` status?  
**Recommendation**: No - use only existing schema values

### 2. Analysis Workflow
**Question**: How to handle file_upload → analysis relationship?  
**Recommendation**: Use `file_path` in analysis_requests (as designed)

### 3. Processing Times
**Question**: Standardize on milliseconds or seconds?  
**Recommendation**: Use milliseconds (matches existing schema)

### 4. Missing Features
**Question**: Implement prompt management now or later?  
**Recommendation**: Later - focus on core upload/analysis first

## Migration Risks

### ⚠️ High Risk Areas
1. **Analysis model** - Complete architectural change
2. **File hash** - Must implement for security
3. **Progress tracking** - Required for UX

### ✅ Low Risk Areas
1. **Auth models** - Minimal changes
2. **Timestamps** - Already using UTC
3. **Relationships** - Clear FK patterns

## Conclusion

The existing schema is **significantly more mature** than our new models. We must:
1. **Abandon** the single-table ResumeAnalysis model
2. **Adopt** the two-table analysis pattern
3. **Add** ~15 missing fields to FileUpload
4. **Preserve** all existing security and tracking features

**Estimated effort**: 3-4 days for complete adaptation

---

*Generated: September 9, 2025*  
*Next Step: Begin model rewrites starting with FileUpload*