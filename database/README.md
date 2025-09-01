# Database Documentation
AI Resume Review Platform - Database Layer

## 📋 Overview

This directory contains all database-related files including schema migrations, setup scripts, and testing utilities for the AI Resume Review Platform. The system uses PostgreSQL as the primary database with Redis for caching.

## 🗂️ Directory Structure

```
database/
├── migrations/               # Database schema migrations
│   ├── 001_initial_schema.sql
│   ├── 002_add_password_security_columns.sql
│   └── 003_add_refresh_tokens_table.sql
├── scripts/                  # Database management scripts
│   ├── migrate.sh           # Migration runner script
│   └── setup-dev-db.sh      # Development database setup
├── tests/                    # Database testing utilities
│   ├── run_tests.sh         # Test runner script
│   └── schema_tests.sql     # Schema integrity tests
└── README.md                # This documentation
```

## 🛠️ Quick Start

### 1. Development Environment Setup

Start the development database with all services:

```bash
# Start PostgreSQL + Redis + pgAdmin
./database/scripts/setup-dev-db.sh

# Or skip pgAdmin
./database/scripts/setup-dev-db.sh --no-pgadmin
```

### 2. Manual Database Connection

Connect directly to the development database:

```bash
psql -h localhost -p 5432 -U postgres -d ai_resume_review_dev
```

**Default Credentials:**
- Host: `localhost`
- Port: `5432`
- Database: `ai_resume_review_dev`
- Username: `postgres`
- Password: `dev_password_123`

## 📊 Database Schema

### Core Tables

#### `users`
User authentication and profile management
- Primary key: `id` (UUID)
- Unique constraint: `email`
- Includes password security tracking (failed attempts, lockouts)
- Timezone-aware timestamps

#### `analysis_requests`
Resume analysis request tracking
- Links to `users` table
- Stores file metadata and processing status
- Supports different experience levels and target roles

#### `analysis_results`
AI-generated resume analysis results
- Links to `analysis_requests`
- Stores scores (0-100 range with constraints)
- Includes strengths, weaknesses, and recommendations arrays
- JSONB field for detailed feedback

#### `prompts`
AI prompt template management
- Versioned prompt templates
- Different prompt types: system, analysis, formatting, content
- Active/inactive flag for A/B testing

#### `prompt_history`
Audit trail for prompt usage
- Tracks which prompts were used for each analysis
- Enables prompt performance analysis

#### `refresh_tokens`
JWT refresh token management (added in migration 003)
- Secure session management
- Device tracking and IP logging
- Automatic session limiting (max 3 concurrent sessions)
- Token expiration and cleanup functions

### Indexes
Optimized for common query patterns:
- User lookups by email
- Analysis requests by user and status
- Results by request ID
- Prompt lookups by type and active status

## 🔄 Migration Management

### Running Migrations

```bash
# Development environment
export DB_PASSWORD="dev_password_123"
./database/scripts/migrate.sh dev up

# Staging/Production (requires Cloud SQL Proxy)
export DB_PASSWORD="your_production_password"
./database/scripts/migrate.sh staging up
```

### Migration Files

1. **001_initial_schema.sql** - Core database structure
   - Creates all primary tables
   - Sets up UUID extension
   - Adds performance indexes
   - Includes update triggers
   - Inserts default system prompts

2. **002_add_password_security_columns.sql** - Security enhancements
   - Password change tracking
   - Failed login attempt counting
   - Account lockout functionality

3. **003_add_refresh_tokens_table.sql** - Session management
   - JWT refresh token storage
   - Session limiting (max 3 concurrent)
   - Device and IP tracking
   - Automatic cleanup procedures

### Creating New Migrations

1. Create new file: `database/migrations/00X_description.sql`
2. Follow the existing format with header comments
3. Add migration record: `INSERT INTO schema_migrations (version) VALUES ('00X_description');`
4. Test thoroughly before applying to production

## 🧪 Testing

### Running Database Tests

```bash
# All tests (requires running database)
./database/tests/run_tests.sh dev all

# Specific test types
./database/tests/run_tests.sh dev schema
./database/tests/run_tests.sh dev performance
./database/tests/run_tests.sh dev connection
```

### Test Categories

- **Schema Tests**: Table structure, constraints, indexes
- **Migration Tests**: Migration script validation
- **Performance Tests**: Query execution timing
- **Connection Tests**: Database connectivity and limits

## ⚙️ Configuration

### Environment Variables

Required in `.env` file:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_resume_review_dev
DB_USER=postgres
DB_PASSWORD=your_password
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Database Features

- **UUID Primary Keys**: All tables use UUID for better distributed system support
- **Timezone-Aware Timestamps**: All datetime columns use `TIMESTAMP WITH TIME ZONE`
- **Automatic Updates**: `updated_at` columns automatically updated via triggers
- **Constraint Validation**: Enum constraints for status fields, score ranges
- **Cascade Deletes**: Proper foreign key relationships with cascade rules

## 🔐 Security Features

### Password Security
- BCrypt hashing (12 rounds minimum)
- Failed login attempt tracking
- Account lockout after repeated failures
- Password change timestamp tracking

### Session Management
- JWT refresh tokens with SHA-256 hashing
- Session device and IP tracking
- Automatic session limiting (3 concurrent max)
- Token expiration and cleanup procedures

### Data Protection
- No sensitive data stored in plain text
- Proper foreign key constraints
- Input validation via CHECK constraints
- Audit trail for critical operations

## 🚀 Deployment

### Development
Uses Docker Compose with:
- PostgreSQL 13+
- Redis 6+
- pgAdmin 4 (optional)

### Production
Uses Google Cloud SQL with:
- Automated backups
- Point-in-time recovery
- Connection pooling
- SSL enforcement

## 🛠️ Maintenance Tasks

### Regular Cleanup
The database includes automated cleanup procedures:

```sql
-- Clean up expired refresh tokens (run periodically)
SELECT cleanup_expired_refresh_tokens();

-- Expire active tokens past expiration
SELECT expire_refresh_tokens();
```

### Monitoring
Monitor these key metrics:
- Connection pool usage
- Query performance (especially user lookups)
- Table sizes (analysis_results can grow large)
- Index effectiveness

## 📞 Support

For database-related issues:
1. Check connection using provided credentials
2. Review recent migrations for schema changes  
3. Run schema tests to validate integrity
4. Check Docker containers if using development setup

## 🔗 Related Documentation

- **Backend API**: `backend/README.md`
- **Architecture**: `docs/design/architecture.md` 
- **Working Agreements**: `docs/working-agreements.md`
- **API Specification**: `docs/api/openapi.yaml`