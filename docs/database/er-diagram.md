# Database ER Diagram - AI Resume Review Platform

## Entity Relationship Diagram

```mermaid
erDiagram
    users {
        UUID id PK
        VARCHAR email UK
        VARCHAR password_hash
        VARCHAR first_name
        VARCHAR last_name
        VARCHAR role
        BOOLEAN is_active
        BOOLEAN email_verified
        TIMESTAMP created_at
        TIMESTAMP updated_at
        TIMESTAMP last_login_at
        TIMESTAMP password_changed_at
        INTEGER failed_login_attempts
        TIMESTAMP locked_until
    }
    
    analysis_requests {
        UUID id PK
        UUID user_id FK
        VARCHAR original_filename
        VARCHAR file_path
        INTEGER file_size_bytes
        VARCHAR mime_type
        VARCHAR status
        VARCHAR target_role
        VARCHAR target_industry
        VARCHAR experience_level
        TIMESTAMP created_at
        TIMESTAMP updated_at
        TIMESTAMP completed_at
    }
    
    analysis_results {
        UUID id PK
        UUID request_id FK
        INTEGER overall_score
        TEXT[] strengths
        TEXT[] weaknesses
        TEXT[] recommendations
        INTEGER formatting_score
        INTEGER content_score
        INTEGER keyword_optimization_score
        JSONB detailed_feedback
        VARCHAR ai_model_used
        INTEGER processing_time_ms
        TIMESTAMP created_at
    }
    
    prompts {
        UUID id PK
        VARCHAR name UK
        TEXT description
        TEXT template
        INTEGER version
        BOOLEAN is_active
        VARCHAR prompt_type
        UUID created_by FK
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    prompt_history {
        UUID id PK
        UUID prompt_id FK
        UUID request_id FK
        INTEGER prompt_version
        TEXT prompt_content
        TIMESTAMP created_at
    }

    users ||--o{ analysis_requests : "creates"
    analysis_requests ||--|| analysis_results : "generates"
    users ||--o{ prompts : "creates"
    prompts ||--o{ prompt_history : "tracks"
    analysis_requests ||--o{ prompt_history : "uses"
```

## Table Descriptions

### users
- **Purpose**: Store user authentication and profile information
- **Key Features**: 
  - UUID primary key for security
  - Role-based access (consultant, admin)
  - Email verification tracking
  - Soft delete via is_active flag
  - Password security tracking (failed attempts, lockout, change history)

### analysis_requests
- **Purpose**: Track resume analysis requests and metadata
- **Key Features**:
  - File metadata storage
  - Status tracking (pending → processing → completed/failed)
  - Target job context (role, industry, experience level)
  - Audit trail with timestamps

### analysis_results
- **Purpose**: Store AI-generated analysis and feedback
- **Key Features**:
  - Structured scoring system (0-100)
  - Flexible feedback storage with arrays and JSONB
  - Performance tracking (processing time, model used)
  - One-to-one relationship with requests

### prompts
- **Purpose**: Manage AI prompt templates and versions
- **Key Features**:
  - Versioned prompt templates
  - Type categorization (system, analysis, formatting, content)
  - Active/inactive status for A/B testing
  - User attribution for custom prompts

### prompt_history
- **Purpose**: Audit trail for prompt usage in analyses
- **Key Features**:
  - Links specific prompt versions to analysis requests
  - Enables reproducibility and debugging
  - Supports A/B testing analytics

## Relationships

1. **users → analysis_requests**: One-to-many (users can submit multiple requests)
2. **analysis_requests → analysis_results**: One-to-one (each request generates one result)
3. **users → prompts**: One-to-many (users can create custom prompts)
4. **prompts → prompt_history**: One-to-many (prompts track usage history)
5. **analysis_requests → prompt_history**: One-to-many (requests use multiple prompts)

## Security Considerations

- All tables use UUID primary keys to prevent enumeration attacks
- Password hashing is handled at the application layer
- Foreign key constraints ensure referential integrity
- Cascading deletes maintain data consistency
- Indexes optimize query performance

## Performance Optimizations

- Strategic indexing on frequently queried columns
- JSONB for flexible schema evolution
- Array types for efficient list storage
- Timestamp indexing for chronological queries