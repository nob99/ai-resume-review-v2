-- Rollback Migration: Remove raw_ai_response column from review_results table
-- Description: Emergency rollback script to remove raw_ai_response column if issues arise
-- Date: 2025-09-10
-- Related to: Migration 004_add_raw_ai_response_column.sql
-- WARNING: This will permanently delete all data in the raw_ai_response column

-- ============================================================================
-- PRE-ROLLBACK CHECKS
-- ============================================================================

-- Check if column exists before attempting rollback
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'review_results' 
        AND column_name = 'raw_ai_response'
    ) THEN
        RAISE NOTICE 'Column raw_ai_response does not exist - rollback not needed';
    ELSE
        RAISE NOTICE 'Column raw_ai_response found - proceeding with rollback';
    END IF;
END $$;

-- ============================================================================
-- OPTIONAL: BACKUP DATA BEFORE ROLLBACK
-- ============================================================================
-- Uncomment to create a backup table with the raw_ai_response data before deletion:
--
-- CREATE TABLE IF NOT EXISTS review_results_raw_ai_backup AS
-- SELECT 
--     id,
--     review_request_id,
--     raw_ai_response,
--     created_at,
--     CURRENT_TIMESTAMP as backed_up_at
-- FROM review_results
-- WHERE raw_ai_response IS NOT NULL;
--
-- COMMENT ON TABLE review_results_raw_ai_backup IS 
-- 'Backup of raw_ai_response data before rollback - Created: ' || CURRENT_TIMESTAMP;

-- ============================================================================
-- ROLLBACK: DROP COLUMN
-- ============================================================================

-- Remove any indexes on the column first (if they exist)
DROP INDEX IF EXISTS idx_review_results_raw_ai_response_gin;

-- Drop the column
ALTER TABLE review_results 
DROP COLUMN IF EXISTS raw_ai_response;

-- ============================================================================
-- POST-ROLLBACK VALIDATION
-- ============================================================================

-- Verify column was removed successfully
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'review_results' 
        AND column_name = 'raw_ai_response'
    ) THEN
        RAISE EXCEPTION 'Rollback failed: raw_ai_response column still exists';
    ELSE
        RAISE NOTICE 'Rollback successful: raw_ai_response column removed from review_results table';
    END IF;
END $$;

-- ============================================================================
-- ROLLBACK METADATA
-- ============================================================================
/*
Rollback Details:
- Action: DROP COLUMN raw_ai_response from review_results table
- Data Loss: Yes - all data in raw_ai_response column will be lost
- Backup Option: Uncomment backup section to preserve data before rollback
- Safe to Run Multiple Times: Yes (uses IF EXISTS clauses)
- Dependencies: None (column is nullable and has no foreign key constraints)

To Execute Rollback:
1. Consider creating backup if data exists (uncomment backup section)
2. Run this script: psql -d ai_resume_review_dev -f 004_rollback_raw_ai_response_column.sql
3. Verify application still functions without the column
4. Remove or revert application code that references raw_ai_response

Recovery After Rollback:
- If backed up: Data available in review_results_raw_ai_backup table
- To re-apply: Run 004_add_raw_ai_response_column.sql again
- To restore data: UPDATE review_results SET raw_ai_response = backup.raw_ai_response 
                   FROM review_results_raw_ai_backup backup 
                   WHERE review_results.id = backup.id;
*/