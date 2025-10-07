-- Migration: 007_schema_v1.1_candidate_centric_tables
-- Description: Add candidate-centric tables for schema v1.1
-- Date: 2025-10-07
-- Related: Schema migration from v1.0 to v1.1
-- Purpose: Implement multi-tenant recruitment platform with candidate-centric design

-- ============================================================================
-- SECTION 1: Create Core Tables (in dependency order)
-- ============================================================================

-- 1.1: candidates table
-- Core business entity - all operations center around candidates
CREATE TABLE IF NOT EXISTS candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    current_company VARCHAR(255),
    current_position VARCHAR(255),
    years_experience INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 1.2: user_candidate_assignments table
-- Junction table for role-based access control with assignment history
CREATE TABLE IF NOT EXISTS user_candidate_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    assignment_type VARCHAR(20) NOT NULL DEFAULT 'primary',
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    unassigned_at TIMESTAMP WITH TIME ZONE,
    assigned_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    unassigned_reason TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 1.3: resumes table
-- Resume documents with versioning support (replaces file_uploads)
CREATE TABLE IF NOT EXISTS resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    uploaded_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    extracted_text TEXT,
    word_count INTEGER,
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- 1.4: resume_sections table
-- Section-level tracking for precise AI feedback
CREATE TABLE IF NOT EXISTS resume_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    section_type VARCHAR(20) NOT NULL,
    section_title TEXT,
    content TEXT NOT NULL,
    start_page INTEGER,
    end_page INTEGER,
    start_position INTEGER,
    end_position INTEGER,
    sequence_order INTEGER NOT NULL DEFAULT 0,
    section_metadata JSONB
);

-- 1.5: review_requests table
-- AI review job tracking (replaces analysis_requests)
CREATE TABLE IF NOT EXISTS review_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    requested_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    target_role VARCHAR(255),
    target_industry VARCHAR(100),
    experience_level VARCHAR(20),
    review_type VARCHAR(20) NOT NULL DEFAULT 'comprehensive',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 1.6: review_results table
-- AI analysis output with detailed scoring (replaces analysis_results)
CREATE TABLE IF NOT EXISTS review_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_request_id UUID NOT NULL REFERENCES review_requests(id) ON DELETE CASCADE,
    overall_score INTEGER,
    ats_score INTEGER,
    content_score INTEGER,
    formatting_score INTEGER,
    executive_summary TEXT,
    detailed_scores JSONB,
    raw_ai_response JSONB,
    ai_model_used VARCHAR(100),
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 1.7: review_feedback_items table
-- Section-level feedback with precise highlighting support
CREATE TABLE IF NOT EXISTS review_feedback_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_result_id UUID NOT NULL REFERENCES review_results(id) ON DELETE CASCADE,
    resume_section_id UUID REFERENCES resume_sections(id) ON DELETE SET NULL,
    feedback_type VARCHAR(20) NOT NULL,
    category VARCHAR(20) NOT NULL,
    feedback_text TEXT NOT NULL,
    severity_level INTEGER NOT NULL DEFAULT 3,
    original_text TEXT,
    suggested_text TEXT,
    confidence_score INTEGER
);

-- 1.8: prompt_usage_history table
-- AI prompt usage audit trail (replaces prompt_history)
CREATE TABLE IF NOT EXISTS prompt_usage_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id UUID NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    agent_name VARCHAR(100),
    actual_prompt TEXT,
    variables_used JSONB,
    agent_response JSONB,
    tokens_used INTEGER,
    used_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 1.9: activity_logs table
-- Complete audit trail for compliance and tracking
CREATE TABLE IF NOT EXISTS activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    action VARCHAR(50) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SECTION 2: Add Constraints
-- ============================================================================

-- 2.1: candidates constraints
ALTER TABLE candidates ADD CONSTRAINT IF NOT EXISTS chk_candidates_status
    CHECK (status IN ('active', 'placed', 'archived'));

ALTER TABLE candidates ADD CONSTRAINT IF NOT EXISTS candidates_email_unique
    UNIQUE (email);

-- 2.2: user_candidate_assignments constraints
ALTER TABLE user_candidate_assignments ADD CONSTRAINT IF NOT EXISTS chk_assignments_type
    CHECK (assignment_type IN ('primary', 'secondary', 'viewer'));

-- 2.3: resumes constraints
ALTER TABLE resumes ADD CONSTRAINT IF NOT EXISTS chk_resumes_status
    CHECK (status IN ('pending', 'processing', 'completed', 'error'));

ALTER TABLE resumes ADD CONSTRAINT IF NOT EXISTS chk_resumes_progress
    CHECK (progress >= 0 AND progress <= 100);

ALTER TABLE resumes ADD CONSTRAINT IF NOT EXISTS chk_resumes_version
    CHECK (version_number >= 1);

ALTER TABLE resumes ADD CONSTRAINT IF NOT EXISTS chk_resumes_file_size
    CHECK (file_size > 0);

-- 2.4: resume_sections constraints
ALTER TABLE resume_sections ADD CONSTRAINT IF NOT EXISTS chk_sections_type
    CHECK (section_type IN ('contact', 'summary', 'experience', 'education', 'skills', 'certifications', 'other'));

ALTER TABLE resume_sections ADD CONSTRAINT IF NOT EXISTS chk_sections_start_position
    CHECK (start_position >= 0 OR start_position IS NULL);

ALTER TABLE resume_sections ADD CONSTRAINT IF NOT EXISTS chk_sections_end_position
    CHECK (end_position >= 0 OR end_position IS NULL);

ALTER TABLE resume_sections ADD CONSTRAINT IF NOT EXISTS chk_sections_sequence_order
    CHECK (sequence_order >= 0);

-- 2.5: review_requests constraints
ALTER TABLE review_requests ADD CONSTRAINT IF NOT EXISTS chk_review_requests_status
    CHECK (status IN ('pending', 'processing', 'completed', 'failed'));

ALTER TABLE review_requests ADD CONSTRAINT IF NOT EXISTS chk_review_requests_type
    CHECK (review_type IN ('comprehensive', 'quick_scan', 'ats_check'));

ALTER TABLE review_requests ADD CONSTRAINT IF NOT EXISTS chk_review_requests_experience
    CHECK (experience_level IN ('entry', 'mid', 'senior', 'executive') OR experience_level IS NULL);

-- 2.6: review_results constraints
ALTER TABLE review_results ADD CONSTRAINT IF NOT EXISTS chk_review_results_overall_score
    CHECK (overall_score >= 0 AND overall_score <= 100 OR overall_score IS NULL);

ALTER TABLE review_results ADD CONSTRAINT IF NOT EXISTS chk_review_results_ats_score
    CHECK (ats_score >= 0 AND ats_score <= 100 OR ats_score IS NULL);

ALTER TABLE review_results ADD CONSTRAINT IF NOT EXISTS chk_review_results_content_score
    CHECK (content_score >= 0 AND content_score <= 100 OR content_score IS NULL);

ALTER TABLE review_results ADD CONSTRAINT IF NOT EXISTS chk_review_results_formatting_score
    CHECK (formatting_score >= 0 AND formatting_score <= 100 OR formatting_score IS NULL);

-- 2.7: review_feedback_items constraints
ALTER TABLE review_feedback_items ADD CONSTRAINT IF NOT EXISTS chk_feedback_type
    CHECK (feedback_type IN ('strength', 'weakness', 'suggestion', 'error'));

ALTER TABLE review_feedback_items ADD CONSTRAINT IF NOT EXISTS chk_feedback_category
    CHECK (category IN ('content', 'formatting', 'keywords', 'grammar'));

ALTER TABLE review_feedback_items ADD CONSTRAINT IF NOT EXISTS chk_feedback_severity
    CHECK (severity_level >= 1 AND severity_level <= 5);

ALTER TABLE review_feedback_items ADD CONSTRAINT IF NOT EXISTS chk_feedback_confidence
    CHECK (confidence_score >= 0 AND confidence_score <= 100 OR confidence_score IS NULL);

-- 2.8: activity_logs constraints
ALTER TABLE activity_logs ADD CONSTRAINT IF NOT EXISTS chk_activity_logs_entity_type
    CHECK (entity_type IN ('candidate', 'resume', 'review', 'user'));

ALTER TABLE activity_logs ADD CONSTRAINT IF NOT EXISTS chk_activity_logs_action
    CHECK (action IN ('create', 'update', 'delete', 'view', 'download'));

-- ============================================================================
-- SECTION 3: Create Indexes
-- ============================================================================

-- 3.1: candidates indexes
CREATE INDEX IF NOT EXISTS idx_candidates_created_by ON candidates(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_candidates_created_at ON candidates(created_at DESC);

-- 3.2: user_candidate_assignments indexes (critical for performance)
CREATE INDEX IF NOT EXISTS idx_assignments_user_active ON user_candidate_assignments(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_assignments_candidate_active ON user_candidate_assignments(candidate_id, is_active);
CREATE INDEX IF NOT EXISTS idx_assignments_assigned_by ON user_candidate_assignments(assigned_by_user_id);

-- 3.3: resumes indexes
CREATE INDEX IF NOT EXISTS idx_resumes_candidate ON resumes(candidate_id);
CREATE INDEX IF NOT EXISTS idx_resumes_status ON resumes(status);
CREATE INDEX IF NOT EXISTS idx_resumes_uploaded_by ON resumes(uploaded_by_user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_uploaded_at ON resumes(uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_resumes_file_hash ON resumes(file_hash);

-- 3.4: resume_sections indexes
CREATE INDEX IF NOT EXISTS idx_sections_resume ON resume_sections(resume_id, sequence_order);
CREATE INDEX IF NOT EXISTS idx_sections_type ON resume_sections(section_type);

-- 3.5: review_requests indexes
CREATE INDEX IF NOT EXISTS idx_review_requests_resume ON review_requests(resume_id);
CREATE INDEX IF NOT EXISTS idx_review_requests_user ON review_requests(requested_by_user_id);
CREATE INDEX IF NOT EXISTS idx_review_requests_status ON review_requests(status);
CREATE INDEX IF NOT EXISTS idx_review_requests_requested_at ON review_requests(requested_at DESC);

-- 3.6: review_results indexes
CREATE INDEX IF NOT EXISTS idx_review_results_request ON review_results(review_request_id);
CREATE INDEX IF NOT EXISTS idx_review_results_created_at ON review_results(created_at DESC);

-- 3.7: review_feedback_items indexes
CREATE INDEX IF NOT EXISTS idx_feedback_result ON review_feedback_items(review_result_id);
CREATE INDEX IF NOT EXISTS idx_feedback_section ON review_feedback_items(resume_section_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON review_feedback_items(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_category ON review_feedback_items(category);

-- 3.8: prompt_usage_history indexes
CREATE INDEX IF NOT EXISTS idx_prompt_usage_prompt ON prompt_usage_history(prompt_id);
CREATE INDEX IF NOT EXISTS idx_prompt_usage_agent ON prompt_usage_history(agent_name);
CREATE INDEX IF NOT EXISTS idx_prompt_usage_used_at ON prompt_usage_history(used_at DESC);

-- 3.9: activity_logs indexes
CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_entity ON activity_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_logs_action ON activity_logs(action);

-- ============================================================================
-- SECTION 4: Create Triggers
-- ============================================================================

-- 4.1: Auto-update candidates.updated_at on row changes
-- Reuse existing trigger function from 001_initial_schema.sql
CREATE TRIGGER update_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SECTION 5: Add Comments (Documentation)
-- ============================================================================

-- 5.1: Table comments
COMMENT ON TABLE candidates IS 'Core business entity - candidate information and status tracking';
COMMENT ON TABLE user_candidate_assignments IS 'Junction table for role-based access control with full assignment history';
COMMENT ON TABLE resumes IS 'Resume documents with versioning support (replaces file_uploads)';
COMMENT ON TABLE resume_sections IS 'Section-level tracking for precise AI feedback and highlighting';
COMMENT ON TABLE review_requests IS 'AI review job tracking (replaces analysis_requests)';
COMMENT ON TABLE review_results IS 'AI analysis output with detailed scoring (replaces analysis_results)';
COMMENT ON TABLE review_feedback_items IS 'Section-level feedback with precise highlighting support';
COMMENT ON TABLE prompt_usage_history IS 'AI prompt usage audit trail for tracking agent behavior';
COMMENT ON TABLE activity_logs IS 'Complete audit trail for compliance and activity tracking';

-- 5.2: Key column comments
COMMENT ON COLUMN candidates.status IS 'Candidate status: active, placed, or archived';
COMMENT ON COLUMN candidates.created_by_user_id IS 'User who created this candidate record';

COMMENT ON COLUMN user_candidate_assignments.assignment_type IS 'Assignment type: primary, secondary, or viewer';
COMMENT ON COLUMN user_candidate_assignments.is_active IS 'Quick filter for current assignments (not unassigned)';

COMMENT ON COLUMN resumes.version_number IS 'Version number for tracking resume iterations';
COMMENT ON COLUMN resumes.file_hash IS 'SHA-256 hash for duplicate detection (non-unique to allow iterations)';
COMMENT ON COLUMN resumes.progress IS 'Processing progress 0-100 for UI display';

COMMENT ON COLUMN resume_sections.sequence_order IS 'Order of section within resume for proper display';
COMMENT ON COLUMN resume_sections.start_position IS 'Character position for text highlighting in frontend';
COMMENT ON COLUMN resume_sections.section_metadata IS 'Additional section-specific data in JSON format';

COMMENT ON COLUMN review_requests.review_type IS 'Type of review: comprehensive, quick_scan, or ats_check';
COMMENT ON COLUMN review_requests.experience_level IS 'Target experience level: entry, mid, senior, or executive';

COMMENT ON COLUMN review_results.raw_ai_response IS 'Complete raw AI response JSON for flexible frontend processing';
COMMENT ON COLUMN review_results.detailed_scores IS 'Detailed score breakdowns in JSON format';

COMMENT ON COLUMN review_feedback_items.severity_level IS 'Severity level 1-5 (1=minor, 5=critical)';
COMMENT ON COLUMN review_feedback_items.confidence_score IS 'AI confidence score 0-100';
COMMENT ON COLUMN review_feedback_items.resume_section_id IS 'Optional link to specific section (NULL for general feedback)';

COMMENT ON COLUMN activity_logs.entity_type IS 'Type of entity: candidate, resume, review, or user';
COMMENT ON COLUMN activity_logs.action IS 'Action performed: create, update, delete, view, or download';
COMMENT ON COLUMN activity_logs.old_values IS 'Previous values before change (for update/delete actions)';
COMMENT ON COLUMN activity_logs.new_values IS 'New values after change (for create/update actions)';

-- ============================================================================
-- SECTION 6: Grant Permissions (if needed)
-- ============================================================================

-- Note: Permissions will be handled by Cloud Run service account
-- No additional GRANT statements needed for Cloud SQL managed access

-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Record this migration
INSERT INTO schema_migrations (version) VALUES ('007_schema_v1.1_candidate_centric_tables')
ON CONFLICT (version) DO NOTHING;

COMMIT;
