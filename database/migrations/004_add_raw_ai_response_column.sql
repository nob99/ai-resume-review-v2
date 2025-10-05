-- Migration: Add raw_ai_response column to review_results table
-- Description: Adds JSONB column to store complete AI response for flexible frontend processing
-- Date: 2025-09-10
-- Related to: Sprint 004 - AI Integration MVP
-- Requested by: Backend Engineering Team
-- Priority: High

-- ============================================================================
-- FORWARD MIGRATION
-- ============================================================================

-- Add raw_ai_response column to review_results table
ALTER TABLE review_results 
ADD COLUMN IF NOT EXISTS raw_ai_response JSONB NULL;

-- Add descriptive comment for documentation
COMMENT ON COLUMN review_results.raw_ai_response IS 
'Complete raw AI response JSON for flexible frontend processing. Stores the unmodified response from AI agents to enable frontend adaptation to format changes without backend modifications.';

-- ============================================================================
-- OPTIONAL: GIN Index for JSON Queries (Deferred to Post-MVP)
-- ============================================================================
-- Uncomment after MVP validation if JSON query performance becomes critical:
--
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_review_results_raw_ai_response_gin 
-- ON review_results USING GIN (raw_ai_response);
--
-- COMMENT ON INDEX idx_review_results_raw_ai_response_gin IS
-- 'GIN index for efficient JSONB queries on raw AI response data';

-- ============================================================================
-- VALIDATION QUERIES
-- ============================================================================

-- Verify column was added successfully
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'review_results' 
        AND column_name = 'raw_ai_response'
    ) THEN
        RAISE EXCEPTION 'Migration failed: raw_ai_response column was not added';
    END IF;
    
    RAISE NOTICE 'Migration successful: raw_ai_response column added to review_results table';
END $$;

-- ============================================================================
-- SAMPLE DATA STRUCTURE (For Reference)
-- ============================================================================
/*
Sample raw_ai_response JSON structure:
{
  "success": true,
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-09-10T10:30:00Z",
  "model_version": "gpt-4-turbo-2024",
  "overall_score": 85.5,
  "market_tier": "senior",
  "executive_summary": "Strong technical background with demonstrated leadership...",
  "structure_analysis": {
    "agent": "structure_agent",
    "scores": {
      "format": 90,
      "organization": 85,
      "tone": 88,
      "completeness": 92,
      "ats_compatibility": 87
    },
    "feedback": {
      "issues": [
        {
          "type": "formatting",
          "severity": "medium",
          "description": "Inconsistent bullet point formatting",
          "section": "experience",
          "suggestion": "Standardize bullet points with action verbs"
        }
      ],
      "recommendations": [
        "Add quantifiable achievements to experience section",
        "Include relevant certifications"
      ]
    }
  },
  "appeal_analysis": {
    "agent": "appeal_agent",
    "target_industry": "strategy_consulting",
    "scores": {
      "achievement_relevance": 87,
      "skills_alignment": 82,
      "industry_fit": 79,
      "leadership_indicators": 91
    },
    "feedback": {
      "relevant_achievements": [
        "Led cross-functional team of 15+ members",
        "Delivered $2M cost savings through process optimization"
      ],
      "improvement_areas": [
        "Emphasize strategic thinking examples",
        "Add more consulting-specific terminology"
      ],
      "competitive_advantages": [
        "Strong quantitative background",
        "International experience"
      ]
    }
  },
  "metadata": {
    "processing_time_ms": 3450,
    "token_usage": {
      "prompt_tokens": 2500,
      "completion_tokens": 1200,
      "total_tokens": 3700
    },
    "agents_used": ["base_agent", "structure_agent", "appeal_agent"],
    "confidence_score": 0.92
  }
}
*/

-- ============================================================================
-- MIGRATION METADATA
-- ============================================================================
/*
Migration Details:
- Table: review_results
- New Column: raw_ai_response (JSONB, nullable)
- Backward Compatible: Yes (nullable column, no data migration required)
- Storage Impact: ~5-15KB per record
- Performance Impact: Minimal (JSONB is efficient)
- Rollback Safe: Yes (see rollback script: 004_rollback_raw_ai_response_column.sql)
*/