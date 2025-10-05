# Detailed Migration Plan: Schema v1.0 → v1.1

**Date**: September 9, 2025  
**Migration Type**: Major Schema Restructure  
**Database**: `ai_resume_review_dev`  
**PostgreSQL Version**: 15

## Pre-Migration Checklist

### 🛡️ **CRITICAL: Complete Backup**
```bash
# 1. Stop all application services
./scripts/docker-dev.sh down

# 2. Create complete database backup
PGPASSWORD=dev_password_123 pg_dump -h localhost -U postgres -d ai_resume_review_dev \
  --verbose --clean --create --if-exists \
  --file=backup_v1.0_$(date +%Y%m%d_%H%M%S).sql

# 3. Backup data directory (if using Docker volumes)
docker volume ls | grep postgres
docker run --rm -v ai-resume-review-v2_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_data_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

### 📊 **Current State Validation**
```sql
-- Connect to database
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev

-- Record current data counts
SELECT 
    'users' as table_name, COUNT(*) as record_count FROM users
UNION ALL SELECT 'file_uploads', COUNT(*) FROM file_uploads
UNION ALL SELECT 'analysis_requests', COUNT(*) FROM analysis_requests  
UNION ALL SELECT 'analysis_results', COUNT(*) FROM analysis_results
UNION ALL SELECT 'prompts', COUNT(*) FROM prompts
UNION ALL SELECT 'prompt_history', COUNT(*) FROM prompt_history;

-- Save current schema
\d+ > current_schema_backup.txt
```

---

## **PHASE 1: Foundation Setup** (Day 1, 2-3 hours)

### Step 1.1: Create Migration Tracking
```sql
-- Track migration progress
CREATE TABLE migration_progress (
    phase VARCHAR(50) PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    rollback_completed BOOLEAN DEFAULT false
);

INSERT INTO migration_progress (phase) VALUES 
    ('phase_1_foundation'),
    ('phase_2_data_migration'),
    ('phase_3_review_system'),
    ('phase_4_section_tracking'),
    ('phase_5_prompt_system'),
    ('phase_6_cleanup'),
    ('phase_7_validation');

UPDATE migration_progress SET status = 'in_progress', started_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_1_foundation';
```

### Step 1.2: Create Core Candidates Table
```sql
-- CRITICAL: New business entity
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    current_company VARCHAR(255),
    current_role VARCHAR(255),
    years_experience INTEGER,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'placed', 'archived')),
    created_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Essential indexes for performance
CREATE INDEX idx_candidates_email ON candidates(email);
CREATE INDEX idx_candidates_created_by ON candidates(created_by_user_id);
CREATE INDEX idx_candidates_status ON candidates(status);
CREATE INDEX idx_candidates_created_at ON candidates(created_at);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_candidates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_candidates_timestamp
    BEFORE UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION update_candidates_updated_at();
```

### Step 1.3: Create User-Candidate Assignment Junction Table
```sql
-- CRITICAL: Many-to-many relationship with history tracking
CREATE TABLE user_candidate_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    assignment_type VARCHAR(20) DEFAULT 'primary' CHECK (assignment_type IN ('primary', 'secondary', 'viewer')),
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    unassigned_at TIMESTAMPTZ,
    assigned_by_user_id UUID REFERENCES users(id),
    unassigned_reason TEXT,
    is_active BOOLEAN DEFAULT true,
    
    -- Ensure no duplicate active assignments
    CONSTRAINT unique_active_assignment UNIQUE (user_id, candidate_id, is_active) 
    DEFERRABLE INITIALLY DEFERRED
);

-- Performance-critical indexes
CREATE INDEX idx_assignments_user_active ON user_candidate_assignments(user_id) WHERE is_active = true;
CREATE INDEX idx_assignments_candidate_active ON user_candidate_assignments(candidate_id) WHERE is_active = true;
CREATE INDEX idx_assignments_user_candidate ON user_candidate_assignments(user_id, candidate_id);
CREATE INDEX idx_assignments_assigned_at ON user_candidate_assignments(assigned_at);
```

### Step 1.4: Update Users Table for New Role Structure
```sql
-- Add migration tracking column
ALTER TABLE users ADD COLUMN migration_v1_1_completed BOOLEAN DEFAULT false;

-- Update role constraints for recruitment platform
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check 
    CHECK (role IN ('junior_recruiter', 'senior_recruiter', 'admin'));

-- Update existing user roles (CAREFUL - verify current users first!)
-- Check current users
SELECT id, email, role FROM users;

-- Step-by-step role migration to preserve admin users:
-- 1. Remove old constraint
ALTER TABLE users DROP CONSTRAINT users_role_check;

-- 2. Update consultant → junior_recruiter
UPDATE users SET role = 'junior_recruiter' WHERE role = 'consultant';

-- 3. Update admin → senior_recruiter (temporary)  
UPDATE users SET role = 'senior_recruiter' WHERE role = 'admin';

-- 4. Convert some senior_recruiters back to admin for system administration
WITH admin_candidates AS (
    SELECT id 
    FROM users 
    WHERE role = 'senior_recruiter' 
    ORDER BY created_at 
    LIMIT 10
)
UPDATE users SET role = 'admin' WHERE id IN (SELECT id FROM admin_candidates);

-- 5. Add new constraint supporting all three roles
ALTER TABLE users ADD CONSTRAINT users_role_check 
    CHECK (role IN ('junior_recruiter', 'senior_recruiter', 'admin'));

-- 6. Mark migration completed
UPDATE users SET migration_v1_1_completed = true;
```

### Step 1.5: Phase 1 Validation
```sql
-- Verify new tables created
\dt candidates
\dt user_candidate_assignments

-- Check constraints
\d+ candidates
\d+ user_candidate_assignments

-- Verify users role update
SELECT role, COUNT(*) FROM users GROUP BY role;

-- Mark phase 1 complete
UPDATE migration_progress SET 
    status = 'completed', 
    completed_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_1_foundation';
```

---

## **PHASE 2: Data Migration & Backfill** (Day 2, 4-5 hours)

### Step 2.1: Start Phase 2
```sql
UPDATE migration_progress SET 
    status = 'in_progress', 
    started_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_2_data_migration';
```

### Step 2.2: Create Candidates from Existing File Uploads
```sql
-- Strategy: Each file_upload represents a candidate
-- Since we don't have candidate names, we'll create placeholder records

-- First, let's see what file_uploads data we have
SELECT id, user_id, original_filename, created_at, extracted_text 
FROM file_uploads 
ORDER BY created_at;

-- Create candidates from file uploads
INSERT INTO candidates (
    first_name,
    last_name,
    email,
    created_by_user_id,
    created_at,
    updated_at
)
SELECT 
    'Candidate' as first_name,
    CONCAT('Resume-', SUBSTRING(fu.original_filename FROM 1 FOR 10)) as last_name,
    CONCAT('candidate-', LOWER(REPLACE(fu.id::text, '-', '')), '@temp.local') as email,
    fu.user_id as created_by_user_id,
    fu.created_at,
    fu.updated_at
FROM file_uploads fu;

-- Verify candidate creation
SELECT COUNT(*) as candidates_created FROM candidates;
SELECT * FROM candidates ORDER BY created_at;
```

### Step 2.3: Auto-assign Candidates to Their Creating Users
```sql
-- Create primary assignments for all candidates to their creators
INSERT INTO user_candidate_assignments (
    user_id,
    candidate_id,
    assignment_type,
    assigned_at,
    assigned_by_user_id,
    is_active
)
SELECT 
    c.created_by_user_id as user_id,
    c.id as candidate_id,
    'primary' as assignment_type,
    c.created_at as assigned_at,
    c.created_by_user_id as assigned_by_user_id,  -- Self-assigned
    true as is_active
FROM candidates c
WHERE c.created_by_user_id IS NOT NULL;

-- Verify assignments
SELECT 
    u.email as user_email,
    u.role,
    COUNT(uca.id) as assigned_candidates
FROM users u
LEFT JOIN user_candidate_assignments uca ON u.id = uca.user_id AND uca.is_active = true
GROUP BY u.id, u.email, u.role;
```

### Step 2.4: Create Resumes Table and Migrate File Upload Data
```sql
-- Create the new resumes table (replaces file_uploads)
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    uploaded_by_user_id UUID NOT NULL REFERENCES users(id),
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    file_size INTEGER NOT NULL CHECK (file_size > 0),
    mime_type VARCHAR(100) NOT NULL,
    version_number INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'error')),
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    extracted_text TEXT,
    word_count INTEGER,
    uploaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMPTZ
);

-- Performance indexes
CREATE INDEX idx_resumes_candidate ON resumes(candidate_id);
CREATE INDEX idx_resumes_uploaded_by ON resumes(uploaded_by_user_id);
CREATE INDEX idx_resumes_status ON resumes(status);
CREATE INDEX idx_resumes_file_hash ON resumes(file_hash);
CREATE INDEX idx_resumes_uploaded_at ON resumes(uploaded_at);
```

### Step 2.5: Migrate File Upload Data to Resumes
```sql
-- Complex migration linking file_uploads to candidates
-- We need to match file_uploads to the candidates we just created

WITH file_upload_candidate_mapping AS (
    -- Match file_uploads to candidates by user and creation time
    SELECT 
        fu.id as file_upload_id,
        fu.user_id,
        fu.original_filename,
        fu.filename,
        fu.file_hash,
        fu.file_size,
        fu.mime_type,
        fu.status,
        fu.progress,
        fu.extracted_text,
        fu.word_count,
        fu.created_at,
        fu.completed_at,
        c.id as candidate_id
    FROM file_uploads fu
    JOIN candidates c ON c.created_by_user_id = fu.user_id
    WHERE c.email LIKE CONCAT('candidate-', LOWER(REPLACE(fu.id::text, '-', '')), '@temp.local')
)
INSERT INTO resumes (
    candidate_id,
    uploaded_by_user_id,
    original_filename,
    stored_filename,
    file_hash,
    file_size,
    mime_type,
    version_number,
    status,
    progress,
    extracted_text,
    word_count,
    uploaded_at,
    processed_at
)
SELECT 
    mapping.candidate_id,
    mapping.user_id,
    mapping.original_filename,
    mapping.filename,
    mapping.file_hash,
    mapping.file_size,
    mapping.mime_type,
    1 as version_number,
    CASE 
        WHEN mapping.status = 'completed' THEN 'completed'
        WHEN mapping.status = 'error' THEN 'error'
        ELSE 'pending'
    END as status,
    COALESCE(mapping.progress, 0),
    mapping.extracted_text,
    mapping.word_count,
    mapping.created_at,
    mapping.completed_at
FROM file_upload_candidate_mapping mapping;

-- Verify resume migration
SELECT 
    'file_uploads' as source_table, COUNT(*) as record_count FROM file_uploads
UNION ALL
SELECT 'resumes' as target_table, COUNT(*) as record_count FROM resumes;

-- Detailed verification
SELECT 
    c.first_name, c.last_name,
    r.original_filename,
    r.status,
    r.uploaded_at
FROM candidates c
JOIN resumes r ON c.id = r.candidate_id
ORDER BY r.uploaded_at;
```

### Step 2.6: Phase 2 Validation
```sql
-- Critical validation checks
SELECT 'Validation: Candidates created' as check_name, 
       COUNT(*) as count 
FROM candidates;

SELECT 'Validation: Assignments created' as check_name, 
       COUNT(*) as count 
FROM user_candidate_assignments WHERE is_active = true;

SELECT 'Validation: Resumes migrated' as check_name, 
       COUNT(*) as count 
FROM resumes;

-- Relationship integrity check
SELECT 
    'Orphaned resumes' as issue,
    COUNT(*) as count
FROM resumes r
LEFT JOIN candidates c ON r.candidate_id = c.id
WHERE c.id IS NULL;

-- Should return 0 orphaned records
-- If > 0, investigate and fix before proceeding

-- Mark phase 2 complete
UPDATE migration_progress SET 
    status = 'completed', 
    completed_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_2_data_migration';
```

---

## **PHASE 3: Review System Migration** (Day 3, 3-4 hours)

### Step 3.1: Start Phase 3
```sql
UPDATE migration_progress SET 
    status = 'in_progress', 
    started_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_3_review_system';
```

### Step 3.2: Create Review Request Table
```sql
CREATE TABLE review_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    requested_by_user_id UUID NOT NULL REFERENCES users(id),
    target_role VARCHAR(255),
    target_industry VARCHAR(255),
    experience_level VARCHAR(50) CHECK (experience_level IN ('entry', 'mid', 'senior', 'executive')),
    review_type VARCHAR(20) DEFAULT 'comprehensive' CHECK (review_type IN ('comprehensive', 'quick_scan', 'ats_check')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    requested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    processing_notes TEXT
);

-- Performance indexes
CREATE INDEX idx_review_requests_resume ON review_requests(resume_id);
CREATE INDEX idx_review_requests_user ON review_requests(requested_by_user_id);
CREATE INDEX idx_review_requests_status ON review_requests(status);
CREATE INDEX idx_review_requests_requested_at ON review_requests(requested_at);
```

### Step 3.3: Create Review Results Table
```sql
CREATE TABLE review_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_request_id UUID NOT NULL REFERENCES review_requests(id) ON DELETE CASCADE,
    overall_score INTEGER CHECK (overall_score >= 0 AND overall_score <= 100),
    ats_score INTEGER CHECK (ats_score >= 0 AND ats_score <= 100),
    content_score INTEGER CHECK (content_score >= 0 AND content_score <= 100),
    formatting_score INTEGER CHECK (formatting_score >= 0 AND formatting_score <= 100),
    executive_summary TEXT,
    detailed_scores JSONB,
    ai_model_used VARCHAR(100) NOT NULL,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_review_results_request ON review_results(review_request_id);
CREATE INDEX idx_review_results_overall_score ON review_results(overall_score);
CREATE INDEX idx_review_results_created_at ON review_results(created_at);
```

### Step 3.4: Migrate Analysis Data to Review System
```sql
-- First, let's examine existing analysis data
SELECT 
    'analysis_requests' as table_name, COUNT(*) as count FROM analysis_requests
UNION ALL
SELECT 'analysis_results', COUNT(*) FROM analysis_results;

-- Show sample analysis data
SELECT * FROM analysis_requests LIMIT 3;
SELECT * FROM analysis_results LIMIT 3;

-- Migrate analysis_requests to review_requests
-- Complex migration: need to link analysis_requests to resumes
WITH analysis_resume_mapping AS (
    SELECT 
        ar.id as analysis_request_id,
        ar.user_id,
        ar.original_filename,
        ar.target_role,
        ar.target_industry,
        ar.experience_level,
        ar.status,
        ar.created_at,
        ar.completed_at,
        r.id as resume_id
    FROM analysis_requests ar
    JOIN resumes r ON r.original_filename = ar.original_filename 
        AND r.uploaded_by_user_id = ar.user_id
)
INSERT INTO review_requests (
    resume_id,
    requested_by_user_id,
    target_role,
    target_industry,
    experience_level,
    review_type,
    status,
    requested_at,
    completed_at
)
SELECT 
    mapping.resume_id,
    mapping.user_id,
    mapping.target_role,
    mapping.target_industry,
    CASE 
        WHEN mapping.experience_level = 'junior' THEN 'entry'
        WHEN mapping.experience_level = 'mid' THEN 'mid' 
        WHEN mapping.experience_level = 'senior' THEN 'senior'
        ELSE 'mid'
    END as experience_level,
    'comprehensive' as review_type,
    CASE 
        WHEN mapping.status = 'completed' THEN 'completed'
        WHEN mapping.status = 'failed' THEN 'failed'
        WHEN mapping.status = 'processing' THEN 'processing'
        ELSE 'pending'
    END as status,
    mapping.created_at,
    mapping.completed_at
FROM analysis_resume_mapping mapping;

-- Verify review_requests migration
SELECT COUNT(*) as review_requests_created FROM review_requests;
```

### Step 3.5: Migrate Analysis Results to Review Results
```sql
-- Migrate analysis_results to review_results
-- Need to link through the analysis_requests we just migrated
INSERT INTO review_results (
    review_request_id,
    overall_score,
    content_score,
    formatting_score,
    ats_score,
    executive_summary,
    detailed_scores,
    ai_model_used,
    processing_time_ms,
    created_at
)
SELECT 
    rr.id as review_request_id,
    COALESCE(ares.overall_score, 0)::INTEGER as overall_score,
    COALESCE(ares.content_score, 0)::INTEGER as content_score,
    COALESCE(ares.formatting_score, 0)::INTEGER as formatting_score,
    COALESCE(ares.keyword_optimization_score, 0)::INTEGER as ats_score,
    CASE 
        WHEN array_length(ares.strengths, 1) > 0 OR array_length(ares.weaknesses, 1) > 0 THEN
            'Strengths: ' || COALESCE(array_to_string(ares.strengths, '; '), 'None noted') || 
            E'\n\nWeaknesses: ' || COALESCE(array_to_string(ares.weaknesses, '; '), 'None noted') ||
            E'\n\nRecommendations: ' || COALESCE(array_to_string(ares.recommendations, '; '), 'None provided')
        ELSE NULL
    END as executive_summary,
    jsonb_build_object(
        'detailed_feedback', ares.detailed_feedback,
        'strengths', ares.strengths,
        'weaknesses', ares.weaknesses,
        'recommendations', ares.recommendations
    ) as detailed_scores,
    COALESCE(ares.ai_model_used, 'unknown') as ai_model_used,
    ares.processing_time_ms,
    ares.created_at
FROM analysis_results ares
JOIN analysis_requests ar ON ares.request_id = ar.id
JOIN review_requests rr ON (
    rr.requested_at = ar.created_at 
    AND rr.requested_by_user_id = ar.user_id
);

-- Verify review_results migration
SELECT 
    'analysis_results source' as table_name, COUNT(*) as count FROM analysis_results
UNION ALL
SELECT 'review_results migrated', COUNT(*) FROM review_results;
```

### Step 3.6: Phase 3 Validation
```sql
-- Comprehensive validation of review system migration
SELECT 
    rr.id as review_request_id,
    c.first_name || ' ' || c.last_name as candidate_name,
    r.original_filename,
    rr.target_role,
    rr.status as request_status,
    res.overall_score,
    res.ai_model_used
FROM review_requests rr
JOIN resumes r ON rr.resume_id = r.id
JOIN candidates c ON r.candidate_id = c.id
LEFT JOIN review_results res ON rr.id = res.review_request_id
ORDER BY rr.requested_at;

-- Check for orphaned records
SELECT 'Orphaned review_results' as issue, COUNT(*) as count
FROM review_results res
LEFT JOIN review_requests rr ON res.review_request_id = rr.id
WHERE rr.id IS NULL;

-- Mark phase 3 complete
UPDATE migration_progress SET 
    status = 'completed', 
    completed_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_3_review_system';
```

---

## **PHASE 4: Section Tracking System** (Day 4, 3-4 hours)

### Step 4.1: Start Phase 4
```sql
UPDATE migration_progress SET 
    status = 'in_progress', 
    started_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_4_section_tracking';
```

### Step 4.2: Create Resume Sections Table
```sql
CREATE TABLE resume_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    section_type VARCHAR(50) NOT NULL CHECK (section_type IN (
        'contact', 'summary', 'experience', 'education', 'skills', 
        'certifications', 'projects', 'achievements', 'other', 'full_content'
    )),
    section_title VARCHAR(255),
    content TEXT NOT NULL,
    start_page INTEGER DEFAULT 1,
    end_page INTEGER DEFAULT 1,
    start_position INTEGER DEFAULT 0,
    end_position INTEGER,
    sequence_order INTEGER NOT NULL,
    confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
    metadata JSONB,
    extracted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_sections_resume_order ON resume_sections(resume_id, sequence_order);
CREATE INDEX idx_sections_type ON resume_sections(section_type);
CREATE INDEX idx_sections_resume ON resume_sections(resume_id);
```

### Step 4.3: Create Review Feedback Items Table
```sql
CREATE TABLE review_feedback_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_result_id UUID NOT NULL REFERENCES review_results(id) ON DELETE CASCADE,
    resume_section_id UUID REFERENCES resume_sections(id) ON DELETE SET NULL,
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('strength', 'weakness', 'suggestion', 'error', 'improvement')),
    category VARCHAR(20) CHECK (category IN ('content', 'formatting', 'keywords', 'grammar', 'structure', 'ats')),
    feedback_text TEXT NOT NULL,
    severity_level INTEGER CHECK (severity_level >= 1 AND severity_level <= 5),
    original_text TEXT,
    suggested_text TEXT,
    confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
    position_start INTEGER,
    position_end INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_feedback_result ON review_feedback_items(review_result_id);
CREATE INDEX idx_feedback_section ON review_feedback_items(resume_section_id);
CREATE INDEX idx_feedback_type ON review_feedback_items(feedback_type);
CREATE INDEX idx_feedback_severity ON review_feedback_items(severity_level);
```

### Step 4.4: Extract Sections from Existing Resumes
```sql
-- Basic section extraction from existing resume text
-- This creates a "full_content" section for each resume with extracted text
INSERT INTO resume_sections (
    resume_id,
    section_type,
    section_title,
    content,
    sequence_order,
    confidence_score,
    end_position,
    metadata
)
SELECT 
    r.id as resume_id,
    'full_content' as section_type,
    'Complete Resume Content' as section_title,
    COALESCE(r.extracted_text, 'No content extracted') as content,
    1 as sequence_order,
    CASE 
        WHEN r.extracted_text IS NOT NULL AND LENGTH(r.extracted_text) > 100 THEN 90
        WHEN r.extracted_text IS NOT NULL THEN 70
        ELSE 30
    END as confidence_score,
    LENGTH(COALESCE(r.extracted_text, '')) as end_position,
    jsonb_build_object(
        'word_count', r.word_count,
        'extraction_method', 'migration_basic',
        'original_filename', r.original_filename
    ) as metadata
FROM resumes r
WHERE r.id IS NOT NULL;

-- Verify section extraction
SELECT 
    rs.section_type,
    COUNT(*) as section_count,
    AVG(LENGTH(rs.content)) as avg_content_length
FROM resume_sections rs
GROUP BY rs.section_type;
```

### Step 4.5: Create Basic Feedback Items from Existing Analysis Results
```sql
-- Extract feedback from existing review_results detailed_scores
-- This is a basic migration - real feedback will come from new AI analysis
INSERT INTO review_feedback_items (
    review_result_id,
    resume_section_id,
    feedback_type,
    category,
    feedback_text,
    severity_level,
    confidence_score
)
SELECT 
    rr.id as review_result_id,
    rs.id as resume_section_id,
    CASE 
        WHEN rr.overall_score >= 80 THEN 'strength'
        WHEN rr.overall_score <= 40 THEN 'weakness'
        ELSE 'suggestion'
    END as feedback_type,
    'content' as category,
    CASE 
        WHEN rr.overall_score >= 80 THEN 'Overall resume quality is strong based on analysis metrics.'
        WHEN rr.overall_score <= 40 THEN 'Resume needs significant improvement based on analysis metrics.'
        ELSE 'Resume has moderate quality with room for improvement.'
    END as feedback_text,
    CASE 
        WHEN rr.overall_score >= 80 THEN 1  -- Low severity for strengths
        WHEN rr.overall_score <= 40 THEN 4  -- High severity for weaknesses
        ELSE 3  -- Medium severity for suggestions
    END as severity_level,
    LEAST(rr.overall_score, 85) as confidence_score
FROM review_results rr
JOIN review_requests req ON rr.review_request_id = req.id
JOIN resume_sections rs ON req.resume_id = rs.resume_id
WHERE rs.section_type = 'full_content';

-- Add specific feedback for formatting and content scores
INSERT INTO review_feedback_items (
    review_result_id,
    resume_section_id,
    feedback_type,
    category,
    feedback_text,
    severity_level,
    confidence_score
)
SELECT 
    rr.id,
    rs.id,
    CASE WHEN rr.formatting_score <= 50 THEN 'weakness' ELSE 'strength' END,
    'formatting',
    CASE 
        WHEN rr.formatting_score <= 50 THEN 'Resume formatting needs improvement for better readability.'
        ELSE 'Resume has good formatting structure.'
    END,
    CASE WHEN rr.formatting_score <= 50 THEN 3 ELSE 2 END,
    LEAST(COALESCE(rr.formatting_score, 50), 80)
FROM review_results rr
JOIN review_requests req ON rr.review_request_id = req.id  
JOIN resume_sections rs ON req.resume_id = rs.resume_id
WHERE rs.section_type = 'full_content' AND rr.formatting_score IS NOT NULL;
```

### Step 4.6: Phase 4 Validation
```sql
-- Validate section tracking system
SELECT 
    'Resume sections created' as metric,
    COUNT(*) as count
FROM resume_sections;

SELECT 
    'Feedback items created' as metric, 
    COUNT(*) as count
FROM review_feedback_items;

-- Detailed validation
SELECT 
    c.first_name || ' ' || c.last_name as candidate,
    r.original_filename,
    COUNT(rs.id) as sections_count,
    COUNT(rfi.id) as feedback_items_count
FROM candidates c
JOIN resumes r ON c.id = r.candidate_id
JOIN resume_sections rs ON r.id = rs.resume_id
LEFT JOIN review_results rres ON rres.review_request_id IN (
    SELECT rreq.id FROM review_requests rreq WHERE rreq.resume_id = r.id
)
LEFT JOIN review_feedback_items rfi ON rres.id = rfi.review_result_id
GROUP BY c.id, c.first_name, c.last_name, r.original_filename, r.id
ORDER BY c.first_name;

-- Mark phase 4 complete
UPDATE migration_progress SET 
    status = 'completed', 
    completed_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_4_section_tracking';
```

---

## **PHASE 5: Prompt System Update** (Day 5, 2-3 hours)

### Step 5.1: Start Phase 5
```sql
UPDATE migration_progress SET 
    status = 'in_progress', 
    started_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_5_prompt_system';
```

### Step 5.2: Update Prompts Table Structure
```sql
-- Add new columns for AI agent system
ALTER TABLE prompts ADD COLUMN agent_type VARCHAR(50);
ALTER TABLE prompts ADD COLUMN variables JSONB DEFAULT '{}';

-- Add constraint for agent types
ALTER TABLE prompts ADD CONSTRAINT prompts_agent_type_check 
    CHECK (agent_type IN ('base_agent', 'structure_agent', 'appeal_agent'));

-- Remove user relationship (prompts are now system-wide)
ALTER TABLE prompts DROP CONSTRAINT IF EXISTS prompts_created_by_fkey;
ALTER TABLE prompts DROP COLUMN IF EXISTS created_by;

-- Update existing prompts with agent types
UPDATE prompts SET 
    agent_type = 'base_agent',
    variables = jsonb_build_object(
        'target_role', '{{target_role}}',
        'target_industry', '{{target_industry}}',
        'experience_level', '{{experience_level}}'
    )
WHERE agent_type IS NULL;
```

### Step 5.3: Create New Prompt Usage History Table
```sql
CREATE TABLE prompt_usage_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id UUID NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    agent_name VARCHAR(50) NOT NULL CHECK (agent_name IN ('base_agent', 'structure_agent', 'appeal_agent')),
    review_request_id UUID REFERENCES review_requests(id) ON DELETE SET NULL,
    actual_prompt TEXT NOT NULL,
    variables_used JSONB DEFAULT '{}',
    agent_response JSONB,
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    used_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_prompt_usage_prompt ON prompt_usage_history(prompt_id);
CREATE INDEX idx_prompt_usage_agent ON prompt_usage_history(agent_name);
CREATE INDEX idx_prompt_usage_request ON prompt_usage_history(review_request_id);
CREATE INDEX idx_prompt_usage_date ON prompt_usage_history(used_at);
```

### Step 5.4: Migrate Existing Prompt History
```sql
-- Migrate data from old prompt_history table
INSERT INTO prompt_usage_history (
    prompt_id,
    agent_name,
    review_request_id,
    actual_prompt,
    variables_used,
    used_at
)
SELECT 
    ph.prompt_id,
    'base_agent' as agent_name,  -- Default to base_agent
    rr.id as review_request_id,  -- Link to new review_requests
    ph.prompt_content,
    '{}' as variables_used,  -- Empty variables (legacy data)
    ph.created_at
FROM prompt_history ph
LEFT JOIN analysis_requests ar ON ph.request_id = ar.id
LEFT JOIN review_requests rr ON (
    rr.requested_by_user_id = ar.user_id 
    AND rr.requested_at = ar.created_at
)
WHERE ph.prompt_id IS NOT NULL AND ph.prompt_content IS NOT NULL;

-- Verify migration
SELECT 
    'prompt_history (old)' as table_name, COUNT(*) as count FROM prompt_history
UNION ALL
SELECT 'prompt_usage_history (new)', COUNT(*) FROM prompt_usage_history;
```

### Step 5.5: Phase 5 Validation
```sql
-- Validate prompt system updates
\d+ prompts
\d+ prompt_usage_history

-- Check prompt data
SELECT 
    name,
    agent_type,
    is_active,
    version
FROM prompts
ORDER BY name;

-- Check usage history
SELECT 
    agent_name,
    COUNT(*) as usage_count
FROM prompt_usage_history
GROUP BY agent_name;

-- Mark phase 5 complete
UPDATE migration_progress SET 
    status = 'completed', 
    completed_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_5_prompt_system';
```

---

## **PHASE 6: Cleanup & Optimization** (Day 6, 2-3 hours)

### Step 6.1: Start Phase 6
```sql
UPDATE migration_progress SET 
    status = 'in_progress', 
    started_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_6_cleanup';
```

### Step 6.2: Create Activity Logs Table (Optional)
```sql
-- Optional: Add comprehensive audit logging
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN ('candidate', 'resume', 'review', 'assignment')),
    entity_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('create', 'update', 'delete', 'view', 'download', 'assign', 'unassign')),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for audit queries
CREATE INDEX idx_activity_logs_user ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_entity ON activity_logs(entity_type, entity_id);
CREATE INDEX idx_activity_logs_action ON activity_logs(action);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at);
```

### Step 6.3: Create Performance Indexes
```sql
-- Additional performance indexes based on expected query patterns

-- User role-based queries
CREATE INDEX idx_users_role_active ON users(role) WHERE is_active = true;

-- Candidate search and filtering
CREATE INDEX idx_candidates_name_search ON candidates USING gin(to_tsvector('english', first_name || ' ' || last_name));
CREATE INDEX idx_candidates_company_role ON candidates(current_company, current_role);

-- Resume version tracking
CREATE INDEX idx_resumes_candidate_version ON resumes(candidate_id, version_number DESC);

-- Review performance queries
CREATE INDEX idx_review_requests_status_date ON review_requests(status, requested_at);
CREATE INDEX idx_review_results_scores ON review_results(overall_score, ats_score, content_score);

-- Section-based feedback queries
CREATE INDEX idx_feedback_type_severity ON review_feedback_items(feedback_type, severity_level);

-- Composite indexes for common queries
CREATE INDEX idx_assignments_user_candidate_active ON user_candidate_assignments(user_id, candidate_id) WHERE is_active = true;
```

### Step 6.4: Backup Old Tables (Don't Drop Yet!)
```sql
-- Rename old tables for backup instead of dropping
-- This allows for rollback if issues are found later

ALTER TABLE file_uploads RENAME TO file_uploads_backup_v1_0;
ALTER TABLE analysis_requests RENAME TO analysis_requests_backup_v1_0;
ALTER TABLE analysis_results RENAME TO analysis_results_backup_v1_0;
ALTER TABLE prompt_history RENAME TO prompt_history_backup_v1_0;

-- Optional: Move refresh_tokens to backup if using Redis for sessions
-- ALTER TABLE refresh_tokens RENAME TO refresh_tokens_backup_v1_0;
```

### Step 6.5: Update Database Statistics
```sql
-- Update table statistics for query optimizer
ANALYZE candidates;
ANALYZE user_candidate_assignments;
ANALYZE resumes;
ANALYZE resume_sections;
ANALYZE review_requests;
ANALYZE review_results;
ANALYZE review_feedback_items;
ANALYZE prompts;
ANALYZE prompt_usage_history;
```

### Step 6.6: Phase 6 Validation
```sql
-- Check all new tables exist
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name NOT LIKE '%_backup_v1_0'
ORDER BY table_name;

-- Check backup tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name LIKE '%_backup_v1_0'
ORDER BY table_name;

-- Mark phase 6 complete
UPDATE migration_progress SET 
    status = 'completed', 
    completed_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_6_cleanup';
```

---

## **PHASE 7: Final Validation & Testing** (Day 7, 4-5 hours)

### Step 7.1: Start Phase 7
```sql
UPDATE migration_progress SET 
    status = 'in_progress', 
    started_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_7_validation';
```

### Step 7.2: Data Integrity Validation
```sql
-- Comprehensive data integrity checks

-- 1. Record count validation
WITH migration_counts AS (
    SELECT 
        'candidates' as table_name, COUNT(*) as new_count, NULL as old_count
    FROM candidates
    UNION ALL
    SELECT 'resumes', COUNT(*), (SELECT COUNT(*) FROM file_uploads_backup_v1_0)
    FROM resumes
    UNION ALL
    SELECT 'review_requests', COUNT(*), (SELECT COUNT(*) FROM analysis_requests_backup_v1_0)
    FROM review_requests
    UNION ALL
    SELECT 'review_results', COUNT(*), (SELECT COUNT(*) FROM analysis_results_backup_v1_0)
    FROM review_results
    UNION ALL
    SELECT 'prompt_usage_history', COUNT(*), (SELECT COUNT(*) FROM prompt_history_backup_v1_0)
    FROM prompt_usage_history
)
SELECT * FROM migration_counts;

-- 2. Relationship integrity checks
SELECT 'Orphaned resumes' as check_type, COUNT(*) as violations
FROM resumes r LEFT JOIN candidates c ON r.candidate_id = c.id WHERE c.id IS NULL
UNION ALL
SELECT 'Orphaned assignments', COUNT(*)
FROM user_candidate_assignments uca 
LEFT JOIN candidates c ON uca.candidate_id = c.id 
LEFT JOIN users u ON uca.user_id = u.id
WHERE c.id IS NULL OR u.id IS NULL
UNION ALL
SELECT 'Orphaned review_requests', COUNT(*)
FROM review_requests rr 
LEFT JOIN resumes r ON rr.resume_id = r.id
LEFT JOIN users u ON rr.requested_by_user_id = u.id
WHERE r.id IS NULL OR u.id IS NULL
UNION ALL
SELECT 'Orphaned review_results', COUNT(*)
FROM review_results res LEFT JOIN review_requests req ON res.review_request_id = req.id
WHERE req.id IS NULL
UNION ALL
SELECT 'Orphaned feedback_items', COUNT(*)
FROM review_feedback_items fi 
LEFT JOIN review_results res ON fi.review_result_id = res.id
WHERE res.id IS NULL;

-- All violation counts should be 0
```

### Step 7.3: Business Logic Validation
```sql
-- Test role-based access patterns

-- Test 1: Junior recruiter should only see assigned candidates
CREATE TEMPORARY VIEW junior_recruiter_candidates AS
SELECT c.*
FROM candidates c
JOIN user_candidate_assignments uca ON c.id = uca.candidate_id
WHERE uca.user_id = (SELECT id FROM users WHERE role = 'junior_recruiter' LIMIT 1)
  AND uca.is_active = true;

-- Test 2: Senior recruiter should see all candidates
CREATE TEMPORARY VIEW senior_recruiter_candidates AS
SELECT * FROM candidates;

-- Test 3: Candidate-resume relationships
SELECT 
    c.first_name || ' ' || c.last_name as candidate_name,
    COUNT(r.id) as resume_count,
    STRING_AGG(r.original_filename, ', ') as resume_files
FROM candidates c
LEFT JOIN resumes r ON c.id = r.candidate_id
GROUP BY c.id, c.first_name, c.last_name
ORDER BY c.first_name;

-- Test 4: Review workflow integrity
SELECT 
    c.first_name || ' ' || c.last_name as candidate_name,
    r.original_filename,
    rr.status as review_status,
    res.overall_score,
    COUNT(fi.id) as feedback_count
FROM candidates c
JOIN resumes r ON c.id = r.candidate_id
JOIN review_requests rr ON r.id = rr.resume_id
LEFT JOIN review_results res ON rr.id = res.review_request_id
LEFT JOIN review_feedback_items fi ON res.id = fi.review_result_id
GROUP BY c.id, c.first_name, c.last_name, r.id, r.original_filename, rr.id, rr.status, res.overall_score
ORDER BY c.first_name;
```

### Step 7.4: Performance Testing
```sql
-- Test critical query performance

-- Query 1: User dashboard (most common query)
EXPLAIN ANALYZE
SELECT 
    c.id,
    c.first_name || ' ' || c.last_name as name,
    c.current_company,
    c.status,
    COUNT(r.id) as resume_count,
    MAX(r.uploaded_at) as latest_resume
FROM candidates c
LEFT JOIN resumes r ON c.id = r.candidate_id
JOIN user_candidate_assignments uca ON c.id = uca.candidate_id
WHERE uca.user_id = (SELECT id FROM users LIMIT 1)
  AND uca.is_active = true
GROUP BY c.id, c.first_name, c.last_name, c.current_company, c.status
ORDER BY MAX(r.uploaded_at) DESC NULLS LAST;

-- Query 2: Resume review history
EXPLAIN ANALYZE
SELECT 
    r.original_filename,
    rr.requested_at,
    res.overall_score,
    COUNT(fi.id) as feedback_items
FROM resumes r
JOIN review_requests rr ON r.id = rr.resume_id  
LEFT JOIN review_results res ON rr.id = res.review_request_id
LEFT JOIN review_feedback_items fi ON res.id = fi.review_result_id
WHERE r.candidate_id = (SELECT id FROM candidates LIMIT 1)
GROUP BY r.id, r.original_filename, rr.id, rr.requested_at, res.overall_score
ORDER BY rr.requested_at DESC;

-- Performance should be reasonable (< 50ms for typical dataset)
```

### Step 7.5: Application Integration Testing
```sql
-- Create test scenarios for application layer

-- Scenario 1: New user assignment workflow
DO $$
DECLARE
    test_user_id UUID;
    test_candidate_id UUID;
    test_assignment_id UUID;
BEGIN
    -- Get test IDs
    SELECT id INTO test_user_id FROM users WHERE role = 'junior_recruiter' LIMIT 1;
    SELECT id INTO test_candidate_id FROM candidates LIMIT 1;
    
    -- Test assignment
    INSERT INTO user_candidate_assignments (
        user_id, candidate_id, assignment_type, assigned_by_user_id, is_active
    ) VALUES (
        test_user_id, test_candidate_id, 'secondary', test_user_id, true
    ) RETURNING id INTO test_assignment_id;
    
    -- Verify assignment
    IF EXISTS (
        SELECT 1 FROM user_candidate_assignments 
        WHERE id = test_assignment_id AND is_active = true
    ) THEN
        RAISE NOTICE 'Assignment test PASSED';
    ELSE
        RAISE EXCEPTION 'Assignment test FAILED';
    END IF;
    
    -- Cleanup test data
    DELETE FROM user_candidate_assignments WHERE id = test_assignment_id;
END $$;

-- Scenario 2: Resume upload simulation  
-- (This would be tested in application layer with actual file handling)
```

### Step 7.6: Generate Migration Report
```sql
-- Final migration summary report
CREATE TEMPORARY TABLE migration_report AS
WITH table_counts AS (
    SELECT 'candidates' as entity, COUNT(*) as count FROM candidates
    UNION ALL SELECT 'resumes', COUNT(*) FROM resumes  
    UNION ALL SELECT 'user_candidate_assignments', COUNT(*) FROM user_candidate_assignments
    UNION ALL SELECT 'resume_sections', COUNT(*) FROM resume_sections
    UNION ALL SELECT 'review_requests', COUNT(*) FROM review_requests
    UNION ALL SELECT 'review_results', COUNT(*) FROM review_results
    UNION ALL SELECT 'review_feedback_items', COUNT(*) FROM review_feedback_items
    UNION ALL SELECT 'prompt_usage_history', COUNT(*) FROM prompt_usage_history
    UNION ALL SELECT 'users (updated)', COUNT(*) FROM users WHERE migration_v1_1_completed = true
),
migration_status AS (
    SELECT phase, status, 
           started_at, 
           completed_at,
           completed_at - started_at as duration
    FROM migration_progress 
    ORDER BY started_at
)
SELECT 
    'MIGRATION SUMMARY' as section,
    '==================' as details
UNION ALL
SELECT 'Entity Counts:', ''
UNION ALL
SELECT entity, count::text FROM table_counts  
UNION ALL
SELECT '', ''
UNION ALL
SELECT 'Phase Status:', ''
UNION ALL  
SELECT phase, status || ' (' || COALESCE(duration::text, 'pending') || ')' FROM migration_status;

-- Display report
SELECT * FROM migration_report;

-- Save completion timestamp
UPDATE migration_progress SET 
    status = 'completed', 
    completed_at = CURRENT_TIMESTAMP 
WHERE phase = 'phase_7_validation';

-- Final success check
DO $$
DECLARE
    failed_phases INTEGER;
BEGIN
    SELECT COUNT(*) INTO failed_phases 
    FROM migration_progress 
    WHERE status != 'completed';
    
    IF failed_phases = 0 THEN
        RAISE NOTICE 'MIGRATION COMPLETED SUCCESSFULLY! All phases completed.';
        
        -- Update schema_migrations table
        INSERT INTO schema_migrations (version, applied_at) 
        VALUES ('1.1.0', CURRENT_TIMESTAMP);
    ELSE
        RAISE WARNING 'MIGRATION INCOMPLETE: % phases not completed', failed_phases;
    END IF;
END $$;
```

---

## **POST-MIGRATION TASKS**

### Application Code Updates Required

#### 1. Update SQLAlchemy Models
```python
# New models to create:
# - app/models/candidate.py
# - app/models/user_candidate_assignment.py  
# - app/models/resume.py (replaces file_upload.py)
# - app/models/resume_section.py
# - app/models/review_request.py (replaces analysis_request.py)
# - app/models/review_result.py (replaces analysis_result.py)
# - app/models/review_feedback_item.py

# Models to update:
# - app/models/user.py (role enum)
# - app/models/prompt.py (add agent_type)
```

#### 2. Update Service Layer  
```python
# Services to create:
# - app/services/candidate_service.py
# - app/services/assignment_service.py
# - app/services/resume_service.py (replace file_upload_service.py)
# - app/services/review_service.py (replace analysis_service.py)

# Services to update:
# - app/services/auth_service.py (role-based access)
# - app/services/prompt_service.py (agent integration)
```

#### 3. Update API Endpoints
```python
# New endpoints to create:
# - /api/candidates/* (CRUD operations)
# - /api/assignments/* (assignment management)
# - /api/resumes/* (replace /api/files/*)
# - /api/reviews/* (replace /api/analysis/*)

# Endpoints to update:
# - /api/auth/* (handle new roles)
# - All endpoints (add role-based access control)
```

### Rollback Procedure (If Needed)

```sql
-- EMERGENCY ROLLBACK - Only if critical issues found
-- Step 1: Stop application
-- Step 2: Run rollback commands

ALTER TABLE file_uploads_backup_v1_0 RENAME TO file_uploads;
ALTER TABLE analysis_requests_backup_v1_0 RENAME TO analysis_requests;
ALTER TABLE analysis_results_backup_v1_0 RENAME TO analysis_results;
ALTER TABLE prompt_history_backup_v1_0 RENAME TO prompt_history;

-- Drop new tables (order matters due to foreign keys)
DROP TABLE IF EXISTS activity_logs;
DROP TABLE IF EXISTS review_feedback_items;
DROP TABLE IF EXISTS resume_sections;
DROP TABLE IF EXISTS review_results;
DROP TABLE IF EXISTS review_requests;
DROP TABLE IF EXISTS prompt_usage_history;
DROP TABLE IF EXISTS resumes;
DROP TABLE IF EXISTS user_candidate_assignments;
DROP TABLE IF EXISTS candidates;

-- Restore users table
ALTER TABLE users DROP CONSTRAINT users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check 
    CHECK (role IN ('consultant', 'admin'));
ALTER TABLE users DROP COLUMN migration_v1_1_completed;

-- Remove migration tracking
DROP TABLE migration_progress;

-- Restore prompt table
ALTER TABLE prompts DROP COLUMN IF EXISTS agent_type;
ALTER TABLE prompts DROP COLUMN IF EXISTS variables;

DELETE FROM schema_migrations WHERE version = '1.1.0';

-- Step 3: Restart application with old code
```

---

## **SUCCESS CRITERIA CHECKLIST**

- [ ] **All 7 migration phases completed successfully**  
- [ ] **Zero data loss** - all original records preserved or migrated
- [ ] **Relationship integrity** - no orphaned records  
- [ ] **Performance acceptable** - key queries under 50ms
- [ ] **Role-based access working** - juniors see assigned, seniors see all, admins have full system access
- [ ] **Backup tables created** - rollback possible if needed
- [ ] **New schema_migrations entry** - version 1.1.0 recorded
- [ ] **Application code updated** - models, services, API endpoints
- [ ] **Frontend updated** - new API calls, candidate management UI
- [ ] **Testing completed** - all user workflows function

**Estimated Total Duration**: 7 days  
**Risk Level**: HIGH - requires careful execution and validation  
**Team Required**: 1-2 backend developers + DBA oversight

---

*Detailed Migration Plan v1.1 - Created September 9, 2025*