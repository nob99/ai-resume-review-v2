-- Migration 006: Update industry enum values
-- Date: 2025-10-06
-- Description: Align industry values across frontend, backend, and AI agents
--              - strategy_tech -> strategy_consulting
--              - ma_financial -> ma_finance
--              - consulting -> full_service_consulting
--              - Remove general (no replacement)
--              - Add tech_consulting (new)
--              - Keep system_integrator (unchanged)

-- Start transaction
BEGIN;

-- Step 1: Update existing data to new industry values
UPDATE review_requests
SET target_industry = 'strategy_consulting'
WHERE target_industry = 'strategy_tech';

UPDATE review_requests
SET target_industry = 'ma_finance'
WHERE target_industry = 'ma_financial';

UPDATE review_requests
SET target_industry = 'full_service_consulting'
WHERE target_industry = 'consulting';

-- Step 2: Handle 'general' industry (if any exist, map to full_service_consulting as fallback)
UPDATE review_requests
SET target_industry = 'full_service_consulting'
WHERE target_industry = 'general';

-- Step 3: Update resume_analyses table (legacy table if still in use)
-- Note: This table may not exist in two-table workflow
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'resume_analyses') THEN
        UPDATE resume_analyses
        SET industry = 'strategy_consulting'
        WHERE industry = 'strategy_tech';

        UPDATE resume_analyses
        SET industry = 'ma_finance'
        WHERE industry = 'ma_financial';

        UPDATE resume_analyses
        SET industry = 'full_service_consulting'
        WHERE industry = 'consulting';

        UPDATE resume_analyses
        SET industry = 'full_service_consulting'
        WHERE industry = 'general';
    END IF;
END $$;

-- Step 4: Add constraint to ensure only valid industry values
-- (PostgreSQL doesn't have native enum types in our schema, using varchar constraints)
ALTER TABLE review_requests DROP CONSTRAINT IF EXISTS review_requests_target_industry_check;
ALTER TABLE review_requests ADD CONSTRAINT review_requests_target_industry_check
    CHECK (target_industry IN (
        'strategy_consulting',
        'ma_finance',
        'tech_consulting',
        'full_service_consulting',
        'system_integrator'
    ));

-- Add constraint for resume_analyses if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'resume_analyses') THEN
        ALTER TABLE resume_analyses DROP CONSTRAINT IF EXISTS resume_analyses_industry_check;
        ALTER TABLE resume_analyses ADD CONSTRAINT resume_analyses_industry_check
            CHECK (industry IN (
                'strategy_consulting',
                'ma_finance',
                'tech_consulting',
                'full_service_consulting',
                'system_integrator'
            ));
    END IF;
END $$;

-- Commit transaction
COMMIT;

-- Verification queries (run these manually to verify)
-- SELECT target_industry, COUNT(*) FROM review_requests GROUP BY target_industry;
-- SELECT industry, COUNT(*) FROM resume_analyses GROUP BY industry;
