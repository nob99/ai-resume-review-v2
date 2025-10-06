-- Migration 006 Rollback: Revert industry enum values to previous state
-- Date: 2025-10-06
-- Description: Rollback industry values to original format
--              - strategy_consulting -> strategy_tech
--              - ma_finance -> ma_financial
--              - full_service_consulting -> consulting
--              - tech_consulting -> strategy_tech (as closest match)
--              - system_integrator -> system_integrator (unchanged)

-- Start transaction
BEGIN;

-- Step 1: Revert existing data to old industry values
UPDATE review_requests
SET target_industry = 'strategy_tech'
WHERE target_industry = 'strategy_consulting';

UPDATE review_requests
SET target_industry = 'ma_financial'
WHERE target_industry = 'ma_finance';

UPDATE review_requests
SET target_industry = 'consulting'
WHERE target_industry = 'full_service_consulting';

-- Map tech_consulting back to strategy_tech (best available match)
UPDATE review_requests
SET target_industry = 'strategy_tech'
WHERE target_industry = 'tech_consulting';

-- Step 2: Revert resume_analyses table if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'resume_analyses') THEN
        UPDATE resume_analyses
        SET industry = 'strategy_tech'
        WHERE industry = 'strategy_consulting';

        UPDATE resume_analyses
        SET industry = 'ma_financial'
        WHERE industry = 'ma_finance';

        UPDATE resume_analyses
        SET industry = 'consulting'
        WHERE industry = 'full_service_consulting';

        UPDATE resume_analyses
        SET industry = 'strategy_tech'
        WHERE industry = 'tech_consulting';
    END IF;
END $$;

-- Step 3: Restore old constraint
ALTER TABLE review_requests DROP CONSTRAINT IF EXISTS review_requests_target_industry_check;
ALTER TABLE review_requests ADD CONSTRAINT review_requests_target_industry_check
    CHECK (target_industry IN (
        'strategy_tech',
        'ma_financial',
        'consulting',
        'system_integrator',
        'general'
    ));

-- Restore constraint for resume_analyses if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'resume_analyses') THEN
        ALTER TABLE resume_analyses DROP CONSTRAINT IF EXISTS resume_analyses_industry_check;
        ALTER TABLE resume_analyses ADD CONSTRAINT resume_analyses_industry_check
            CHECK (industry IN (
                'strategy_tech',
                'ma_financial',
                'consulting',
                'system_integrator',
                'general'
            ));
    END IF;
END $$;

-- Commit transaction
COMMIT;

-- Verification queries (run these manually to verify)
-- SELECT target_industry, COUNT(*) FROM review_requests GROUP BY target_industry;
-- SELECT industry, COUNT(*) FROM resume_analyses GROUP BY industry;
