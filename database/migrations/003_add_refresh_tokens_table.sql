-- Migration: Add refresh tokens table for JWT session management
-- Description: Creates refresh_tokens table to support secure session management
-- Date: 2025-08-30
-- Related to: AUTH-003 Session Management

-- Create refresh_tokens table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    session_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    device_info TEXT,
    ip_address VARCHAR(45), -- Supports both IPv4 and IPv6
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_session_id ON refresh_tokens(session_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_status ON refresh_tokens(status);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- Create composite index for user session queries
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_session ON refresh_tokens(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_status ON refresh_tokens(user_id, status);

-- Add constraint to ensure valid status values
ALTER TABLE refresh_tokens ADD CONSTRAINT chk_refresh_tokens_status 
    CHECK (status IN ('active', 'expired', 'revoked'));

-- Create function to automatically expire old tokens
CREATE OR REPLACE FUNCTION expire_refresh_tokens()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE refresh_tokens 
    SET status = 'expired' 
    WHERE expires_at < CURRENT_TIMESTAMP 
    AND status = 'active';
END;
$$;

-- Create function to limit concurrent sessions per user (max 3)
CREATE OR REPLACE FUNCTION limit_user_sessions()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    -- Count active sessions for the user
    IF (SELECT COUNT(*) FROM refresh_tokens 
        WHERE user_id = NEW.user_id 
        AND status = 'active' 
        AND expires_at > CURRENT_TIMESTAMP) >= 3 THEN
        
        -- Revoke oldest session to make room for new one
        UPDATE refresh_tokens 
        SET status = 'revoked' 
        WHERE id = (
            SELECT id FROM refresh_tokens 
            WHERE user_id = NEW.user_id 
            AND status = 'active' 
            AND expires_at > CURRENT_TIMESTAMP
            ORDER BY created_at ASC 
            LIMIT 1
        );
    END IF;
    
    RETURN NEW;
END;
$$;

-- Create trigger to limit concurrent sessions
CREATE TRIGGER trigger_limit_user_sessions
    BEFORE INSERT ON refresh_tokens
    FOR EACH ROW EXECUTE FUNCTION limit_user_sessions();

-- Comment on table and columns
COMMENT ON TABLE refresh_tokens IS 'Stores JWT refresh tokens for secure session management';
COMMENT ON COLUMN refresh_tokens.id IS 'Primary key for refresh token record';
COMMENT ON COLUMN refresh_tokens.user_id IS 'Foreign key reference to users table';
COMMENT ON COLUMN refresh_tokens.token_hash IS 'SHA-256 hash of the JWT refresh token for security';
COMMENT ON COLUMN refresh_tokens.session_id IS 'Unique session identifier for tracking multiple sessions';
COMMENT ON COLUMN refresh_tokens.status IS 'Token status: active, expired, or revoked';
COMMENT ON COLUMN refresh_tokens.device_info IS 'Optional device/browser information for session identification';
COMMENT ON COLUMN refresh_tokens.ip_address IS 'IP address from which the session was created';
COMMENT ON COLUMN refresh_tokens.expires_at IS 'Token expiration timestamp (7 days from creation)';
COMMENT ON COLUMN refresh_tokens.created_at IS 'Timestamp when token was created';
COMMENT ON COLUMN refresh_tokens.last_used_at IS 'Timestamp when token was last used for refresh';

-- Create cleanup procedure for expired tokens (to be run periodically)
CREATE OR REPLACE FUNCTION cleanup_expired_refresh_tokens()
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count integer;
BEGIN
    -- Delete tokens that have been expired for more than 30 days
    DELETE FROM refresh_tokens 
    WHERE status = 'expired' 
    AND expires_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Also delete revoked tokens older than 7 days
    WITH revoked_delete AS (
        DELETE FROM refresh_tokens 
        WHERE status = 'revoked' 
        AND created_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
        RETURNING 1
    )
    SELECT deleted_count + (SELECT COUNT(*) FROM revoked_delete) INTO deleted_count;
    
    RETURN deleted_count;
END;
$$;

-- Grant permissions (assuming application user exists)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON refresh_tokens TO ai_resume_review_app;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO ai_resume_review_app;

-- Insert initial data or run any setup commands if needed
-- (None needed for this table)

COMMIT;