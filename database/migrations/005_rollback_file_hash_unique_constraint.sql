-- Rollback Migration 005: Restore unique constraint on file_hash
-- WARNING: This rollback will fail if duplicate file_hash values exist
--
-- Steps to rollback safely:
-- 1. Check for duplicates: SELECT file_hash, COUNT(*) FROM resumes GROUP BY file_hash HAVING COUNT(*) > 1;
-- 2. Remove duplicates manually if needed
-- 3. Run this script
--
-- Date: 2025-09-27

-- Restore the unique constraint (will fail if duplicates exist)
ALTER TABLE resumes ADD CONSTRAINT resumes_file_hash_key UNIQUE (file_hash);

-- Restore original comment
COMMENT ON COLUMN resumes.file_hash IS 'SHA-256 hash of file content for deduplication. Must be unique.';

-- Verification query (should return 1 if constraint restored successfully)
-- SELECT COUNT(*) FROM pg_constraint WHERE conname = 'resumes_file_hash_key';