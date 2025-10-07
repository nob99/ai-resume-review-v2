-- Migration: 008_update_schema_v1.0_to_v1.1_constraints
-- Description: Update existing tables from schema v1.0 to match v1.1 requirements
-- Date: 2025-10-07
-- Related: Schema migration from v1.0 to v1.1 - Update existing table constraints
-- Purpose: Fix role constraints and prompts table structure to match v1.1 specification

-- ============================================================================
-- SECTION 1: Update users table role constraint
-- ============================================================================

-- 1.1: Drop old role constraint
-- Old constraint only allowed: 'consultant', 'admin'
-- New constraint must allow: 'junior_recruiter', 'senior_recruiter', 'admin'
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;

-- 1.2: Add new role constraint with v1.1 role values
ALTER TABLE users ADD CONSTRAINT users_role_check
    CHECK (role IN ('junior_recruiter', 'senior_recruiter', 'admin'));

-- 1.3: Update default role value from 'consultant' to 'junior_recruiter'
ALTER TABLE users ALTER COLUMN role SET DEFAULT 'junior_recruiter';

-- 1.4: Migrate existing 'consultant' roles to 'junior_recruiter'
-- This ensures existing users can continue to work with the new role system
UPDATE users SET role = 'junior_recruiter' WHERE role = 'consultant';

-- 1.5: Add comment explaining the role system
COMMENT ON COLUMN users.role IS 'User role: junior_recruiter (sees assigned candidates), senior_recruiter (sees all candidates), admin (full system access)';

-- ============================================================================
-- SECTION 2: Update prompts table structure
-- ============================================================================

-- 2.1: Add agent_type column for AI agent classification
-- This column identifies which AI agent uses the prompt
ALTER TABLE prompts ADD COLUMN IF NOT EXISTS agent_type VARCHAR(50);

-- 2.2: Add variables column for prompt template variables
-- Stores dynamic variables used in prompt templates as JSON
ALTER TABLE prompts ADD COLUMN IF NOT EXISTS variables JSONB;

-- 2.3: Drop old prompt_type constraint
-- Old values: 'system', 'analysis', 'formatting', 'content'
-- New values: 'system', 'analysis', 'extraction'
ALTER TABLE prompts DROP CONSTRAINT IF EXISTS prompts_prompt_type_check;

-- 2.4: Add new prompt_type constraint with v1.1 values
ALTER TABLE prompts ADD CONSTRAINT prompts_prompt_type_check
    CHECK (prompt_type IN ('system', 'analysis', 'extraction'));

-- 2.5: Add agent_type constraint
-- Values match the specialized AI agents in the system
ALTER TABLE prompts ADD CONSTRAINT IF NOT EXISTS prompts_agent_type_check
    CHECK (agent_type IN ('base_agent', 'structure_agent', 'appeal_agent') OR agent_type IS NULL);

-- 2.6: Make created_by column nullable for system prompts
-- Some prompts are system-generated and don't have a creating user
ALTER TABLE prompts ALTER COLUMN created_by DROP NOT NULL;

-- 2.7: Add comments for new columns
COMMENT ON COLUMN prompts.agent_type IS 'AI agent type: base_agent (common checks), structure_agent (resume structure), appeal_agent (industry-specific appeal)';
COMMENT ON COLUMN prompts.variables IS 'Dynamic variables used in prompt template (JSON format)';

-- ============================================================================
-- SECTION 3: Create indexes for new columns
-- ============================================================================

-- 3.1: Index on agent_type for filtering prompts by agent
CREATE INDEX IF NOT EXISTS idx_prompts_agent_type ON prompts(agent_type) WHERE agent_type IS NOT NULL;

-- 3.2: Composite index for agent_type and is_active (common query pattern)
CREATE INDEX IF NOT EXISTS idx_prompts_agent_active ON prompts(agent_type, is_active) WHERE agent_type IS NOT NULL;

-- ============================================================================
-- SECTION 4: Update existing prompt data (if any)
-- ============================================================================

-- 4.1: Update existing prompts to use new prompt_type values
-- Map old 'formatting' type to 'analysis' (closest match)
UPDATE prompts SET prompt_type = 'analysis' WHERE prompt_type = 'formatting';

-- Map old 'content' type to 'analysis' (closest match)
UPDATE prompts SET prompt_type = 'analysis' WHERE prompt_type = 'content';

-- 4.2: Set default agent_type for existing system prompts
-- Based on the prompt name patterns from 001_initial_schema.sql
UPDATE prompts SET agent_type = 'base_agent'
WHERE name = 'resume_analysis_system' AND agent_type IS NULL;

UPDATE prompts SET agent_type = 'structure_agent'
WHERE name = 'formatting_analysis' AND agent_type IS NULL;

UPDATE prompts SET agent_type = 'structure_agent'
WHERE name = 'content_analysis' AND agent_type IS NULL;

-- ============================================================================
-- SECTION 5: Verify data integrity
-- ============================================================================

-- 5.1: Ensure no users have invalid roles
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO invalid_count
    FROM users
    WHERE role NOT IN ('junior_recruiter', 'senior_recruiter', 'admin');

    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Found % users with invalid roles. Please review data before migration.', invalid_count;
    END IF;
END $$;

-- 5.2: Ensure no prompts have invalid prompt_type values
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO invalid_count
    FROM prompts
    WHERE prompt_type NOT IN ('system', 'analysis', 'extraction');

    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Found % prompts with invalid prompt_type. Please review data before migration.', invalid_count;
    END IF;
END $$;

-- ============================================================================
-- SECTION 6: Add helpful views (optional)
-- ============================================================================

-- 6.1: Create view for active prompts by agent
CREATE OR REPLACE VIEW active_prompts_by_agent AS
SELECT
    agent_type,
    prompt_type,
    COUNT(*) as prompt_count,
    array_agg(name ORDER BY name) as prompt_names
FROM prompts
WHERE is_active = true
GROUP BY agent_type, prompt_type
ORDER BY agent_type, prompt_type;

COMMENT ON VIEW active_prompts_by_agent IS 'Summary of active prompts organized by agent type and prompt type';

-- 6.2: Create view for user role distribution
CREATE OR REPLACE VIEW user_role_distribution AS
SELECT
    role,
    COUNT(*) as user_count,
    COUNT(*) FILTER (WHERE is_active = true) as active_users,
    COUNT(*) FILTER (WHERE is_active = false) as inactive_users
FROM users
GROUP BY role
ORDER BY role;

COMMENT ON VIEW user_role_distribution IS 'Distribution of users by role with active/inactive counts';

-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Record this migration
INSERT INTO schema_migrations (version) VALUES ('008_update_schema_v1.0_to_v1.1_constraints')
ON CONFLICT (version) DO NOTHING;

COMMIT;
