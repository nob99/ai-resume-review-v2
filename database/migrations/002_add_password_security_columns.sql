-- Migration: 002_add_password_security_columns
-- Description: Add password security tracking columns to users table
-- Author: Tech Lead
-- Created: 2024-12-30

-- Forward migration
ALTER TABLE users ADD COLUMN password_changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN locked_until TIMESTAMP WITH TIME ZONE;

-- Create index for security queries
CREATE INDEX idx_users_locked_until ON users(locked_until);
CREATE INDEX idx_users_failed_attempts ON users(failed_login_attempts);

-- Record migration
INSERT INTO schema_migrations (version) VALUES ('002_add_password_security_columns');