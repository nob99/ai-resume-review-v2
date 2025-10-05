-- Migration 005: Remove unique constraint on file_hash
-- Purpose: Allow users to upload the same file multiple times for resume iterations
--
-- Business Case:
-- - Users need to upload updated versions of their resume after AI review
-- - Same filename/content should be allowed multiple times per candidate
-- - Version numbering will handle iteration tracking
--
-- Date: 2025-09-27
-- Sprint: Schema v1.1 Migration

-- Remove the unique constraint on file_hash
ALTER TABLE resumes DROP CONSTRAINT IF EXISTS resumes_file_hash_key;

-- Add comment to document the change
COMMENT ON COLUMN resumes.file_hash IS 'SHA-256 hash of file content. Multiple files with same hash allowed for resume iterations.';

-- Verification query (should return 0 if constraint removed successfully)
-- SELECT COUNT(*) FROM pg_constraint WHERE conname = 'resumes_file_hash_key';