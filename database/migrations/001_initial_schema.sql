-- Migration: 001_initial_schema
-- Description: Create initial database schema for AI Resume Review Platform
-- Author: Infrastructure Team
-- Created: 2024-11-30

-- Enable UUID extension for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table for authentication and profile management
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'consultant' CHECK (role IN ('consultant', 'admin')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Analysis requests table for tracking resume review requests
CREATE TABLE analysis_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    target_role VARCHAR(255),
    target_industry VARCHAR(255),
    experience_level VARCHAR(50) CHECK (experience_level IN ('entry', 'mid', 'senior', 'executive')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Analysis results table for storing AI-generated feedback
CREATE TABLE analysis_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL REFERENCES analysis_requests(id) ON DELETE CASCADE,
    overall_score INTEGER CHECK (overall_score >= 0 AND overall_score <= 100),
    strengths TEXT[],
    weaknesses TEXT[],
    recommendations TEXT[],
    formatting_score INTEGER CHECK (formatting_score >= 0 AND formatting_score <= 100),
    content_score INTEGER CHECK (content_score >= 0 AND content_score <= 100),
    keyword_optimization_score INTEGER CHECK (keyword_optimization_score >= 0 AND keyword_optimization_score <= 100),
    detailed_feedback JSONB,
    ai_model_used VARCHAR(100) NOT NULL,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Prompts table for managing AI prompt templates
CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    template TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    prompt_type VARCHAR(50) NOT NULL CHECK (prompt_type IN ('system', 'analysis', 'formatting', 'content')),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Prompt history for tracking prompt evolution and A/B testing
CREATE TABLE prompt_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    request_id UUID NOT NULL REFERENCES analysis_requests(id) ON DELETE CASCADE,
    prompt_version INTEGER NOT NULL,
    prompt_content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Migration tracking table
CREATE TABLE schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for performance optimization
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_analysis_requests_user_id ON analysis_requests(user_id);
CREATE INDEX idx_analysis_requests_status ON analysis_requests(status);
CREATE INDEX idx_analysis_requests_created_at ON analysis_requests(created_at DESC);
CREATE INDEX idx_analysis_results_request_id ON analysis_results(request_id);
CREATE INDEX idx_prompts_name ON prompts(name);
CREATE INDEX idx_prompts_type_active ON prompts(prompt_type, is_active);
CREATE INDEX idx_prompt_history_prompt_id ON prompt_history(prompt_id);
CREATE INDEX idx_prompt_history_request_id ON prompt_history(request_id);

-- Update trigger function for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analysis_requests_updated_at BEFORE UPDATE ON analysis_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prompts_updated_at BEFORE UPDATE ON prompts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default system prompts
INSERT INTO prompts (name, description, template, prompt_type, created_by) VALUES
('resume_analysis_system', 'Main system prompt for resume analysis', 
'You are an expert resume reviewer and career consultant. Analyze resumes comprehensively and provide constructive feedback.', 
'system', NULL),

('content_analysis', 'Prompt for analyzing resume content quality', 
'Analyze the content of this resume for clarity, relevance, and impact. Focus on achievements, skills presentation, and overall narrative.', 
'content', NULL),

('formatting_analysis', 'Prompt for analyzing resume formatting and structure', 
'Evaluate the visual presentation, structure, and readability of this resume. Consider layout, typography, and professional appearance.', 
'formatting', NULL);

-- Record this migration
INSERT INTO schema_migrations (version) VALUES ('001_initial_schema');