# Database Documentation - AI Resume Review Platform

## Overview

This document provides comprehensive information about the database setup, access procedures, and migration framework for the AI Resume Review Platform.

## Database Architecture

- **Database Engine**: PostgreSQL 15
- **Cloud Provider**: Google Cloud SQL (production/staging)
- **Local Development**: Docker containers
- **Schema Management**: SQL migrations with version tracking

## Environment Setup

### Local Development

#### Prerequisites
- Docker Desktop
- Docker Compose
- PostgreSQL client (psql) - optional but recommended

#### Quick Start

1. **Automated Setup** (Recommended):
   ```bash
   ./database/scripts/setup-dev-db.sh
   ```

2. **Manual Setup**:
   ```bash
   # Start database containers
   docker-compose -f docker-compose.dev.yml up -d postgres redis
   
   # Run migrations
   export DB_PASSWORD=dev_password_123
   ./database/scripts/migrate.sh dev up
   
   # Optional: Start pgAdmin
   docker-compose -f docker-compose.dev.yml up -d pgadmin
   ```

#### Connection Details
- **Host**: localhost
- **Port**: 5432
- **Database**: ai_resume_review_dev
- **Username**: postgres
- **Password**: dev_password_123

#### Management Tools
- **pgAdmin**: http://localhost:8080
  - Email: dev@airesumereview.com
  - Password: dev_pgadmin_123
- **Redis**: localhost:6379 (no password)

### Staging Environment

#### Connection
```bash
# Install Cloud SQL Proxy (one time)
gcloud components install cloud_sql_proxy

# Connect to staging database
gcloud sql connect ai-resume-review-staging --user=app_user

# Or use proxy for applications
cloud_sql_proxy -instances=ytgrs-464303:us-central1:ai-resume-review-staging=tcp:5432
```

#### Migration
```bash
export DB_PASSWORD="[staging_password]"
./database/scripts/migrate.sh staging up
```

### Production Environment

#### Connection
```bash
# Connect to production database (requires elevated permissions)
gcloud sql connect ai-resume-review-prod --user=app_user

# Or use proxy
cloud_sql_proxy -instances=ytgrs-464303:us-central1:ai-resume-review-prod=tcp:5432
```

#### Migration
```bash
export DB_PASSWORD="[production_password]"
./database/scripts/migrate.sh prod up
```

## Database Schema

### Core Tables

#### users
Stores user authentication and profile information.
- **Primary Key**: UUID
- **Unique Constraints**: email
- **Features**: Role-based access, email verification, soft delete

#### analysis_requests
Tracks resume analysis requests and metadata.
- **Primary Key**: UUID
- **Foreign Keys**: user_id → users(id)
- **Status Flow**: pending → processing → completed/failed

#### analysis_results
Stores AI-generated analysis and feedback.
- **Primary Key**: UUID
- **Foreign Keys**: request_id → analysis_requests(id)
- **Features**: Structured scoring, flexible feedback storage (JSONB)

#### prompts
Manages AI prompt templates with versioning.
- **Primary Key**: UUID
- **Features**: Version control, type categorization, active/inactive status

#### prompt_history
Audit trail for prompt usage in analyses.
- **Primary Key**: UUID
- **Foreign Keys**: prompt_id → prompts(id), request_id → analysis_requests(id)
- **Purpose**: Reproducibility and A/B testing

### Detailed Schema
See [ER Diagram](./er-diagram.md) for complete relationship mapping.

## Migration Framework

### Overview
The migration system uses numbered SQL files to track and apply database changes systematically.

### Migration Files
- **Location**: `database/migrations/`
- **Naming**: `XXX_description.sql` (e.g., `001_initial_schema.sql`)
- **Structure**: Each file contains both the migration and rollback SQL

### Migration Commands

#### Apply Migrations
```bash
# Development
export DB_PASSWORD=dev_password_123
./database/scripts/migrate.sh dev up

# Staging
export DB_PASSWORD=[staging_password]
./database/scripts/migrate.sh staging up

# Production
export DB_PASSWORD=[production_password]  
./database/scripts/migrate.sh prod up
```

#### Check Migration Status
```bash
# Connect to database and check applied migrations
psql -h localhost -p 5432 -U postgres -d ai_resume_review_dev
SELECT * FROM schema_migrations ORDER BY version;
```

### Creating New Migrations

1. **Create Migration File**:
   ```bash
   # Create new migration file with incremental number
   touch database/migrations/002_add_user_preferences.sql
   ```

2. **Migration Template**:
   ```sql
   -- Migration: 002_add_user_preferences
   -- Description: Add user preferences table for storing UI settings
   -- Author: [Your Name]
   -- Created: [Date]
   
   -- Forward migration
   CREATE TABLE user_preferences (
       id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
       user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
       theme VARCHAR(20) DEFAULT 'light',
       language VARCHAR(10) DEFAULT 'en',
       created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
       updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
   );
   
   CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
   
   -- Record migration
   INSERT INTO schema_migrations (version) VALUES ('002_add_user_preferences');
   ```

3. **Test Migration**:
   ```bash
   # Test on development first
   ./database/scripts/migrate.sh dev up
   
   # Verify schema changes
   psql -h localhost -p 5432 -U postgres -d ai_resume_review_dev -c "\dt"
   ```

## Security Considerations

### Access Control
- **Production**: Restricted access with service accounts
- **Staging**: Development team access via IAM roles  
- **Development**: Local-only access

### Password Management
- **Production/Staging**: Stored in Google Secret Manager
- **Development**: Hardcoded for convenience (never commit real passwords)
- **Environment Variables**: Use `TF_VAR_db_password` for Terraform

### Connection Security
- **Production/Staging**: Private VPC, encrypted connections
- **Development**: Local network only

### Data Protection
- **Backups**: Automated daily backups with 7-day retention
- **Encryption**: Data encrypted at rest and in transit
- **Audit Logging**: All database operations logged

## Performance Optimization

### Indexing Strategy
- **Primary Keys**: UUID with B-tree indexes
- **Foreign Keys**: Automatic indexing for relationships
- **Query Optimization**: Indexes on commonly filtered columns
- **Composite Indexes**: For complex query patterns

### Connection Management
- **Production**: Connection pooling via Google Cloud SQL
- **Application**: Use connection pooling libraries
- **Monitoring**: Track connection usage and query performance

### Monitoring
- **Slow Queries**: Log queries > 1000ms
- **Connection Metrics**: Monitor active connections
- **Storage Usage**: Track database growth

## Troubleshooting

### Common Issues

#### Connection Problems
```bash
# Check if database is running (dev)
docker-compose -f docker-compose.dev.yml ps

# Check database logs
docker-compose -f docker-compose.dev.yml logs postgres

# Test connection
psql -h localhost -p 5432 -U postgres -d ai_resume_review_dev -c "SELECT version();"
```

#### Migration Issues
```bash
# Check migration status
psql -h localhost -p 5432 -U postgres -d ai_resume_review_dev -c "SELECT * FROM schema_migrations;"

# Reset development database (destructive)
docker-compose -f docker-compose.dev.yml down -v
./database/scripts/setup-dev-db.sh
```

#### Performance Issues
```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Getting Help
- **Database Issues**: Check logs first, then consult this documentation
- **Schema Questions**: Review ER diagram and schema.sql
- **Migration Problems**: Ensure proper environment variables and permissions
- **Performance**: Use built-in PostgreSQL monitoring tools

## Best Practices

### Development
1. **Always run migrations on development first**
2. **Test schema changes thoroughly**
3. **Use transactions for complex migrations**
4. **Document migration purpose and impact**

### Production
1. **Schedule migrations during maintenance windows**
2. **Backup database before major changes**
3. **Monitor performance after migrations**
4. **Have rollback plan ready**

### Security
1. **Never commit passwords or secrets**
2. **Use environment variables for credentials**
3. **Rotate passwords regularly**
4. **Monitor access logs**

---

## Quick Reference Commands

```bash
# Start dev environment
./database/scripts/setup-dev-db.sh

# Run migrations
export DB_PASSWORD=dev_password_123
./database/scripts/migrate.sh dev up

# Connect to dev database
psql -h localhost -p 5432 -U postgres -d ai_resume_review_dev

# Stop dev environment
docker-compose -f docker-compose.dev.yml down

# View logs
docker-compose -f docker-compose.dev.yml logs -f postgres
```

---

*Last Updated: November 2024*  
*Next Review: End of Sprint 3*