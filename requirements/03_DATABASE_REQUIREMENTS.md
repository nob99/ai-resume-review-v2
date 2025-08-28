# Database Requirements

## 1. Overview
PostgreSQL database hosted on Cloud SQL to store user accounts, resume analysis results, and system configuration. Designed for simplicity with basic security and no complex performance optimizations for MVP.

### Key Decisions
- **Engine**: PostgreSQL (for JSON support)
- **Access**: Private IP only (no public access)
- **Data Retention**: Keep all data indefinitely
- **Expected Scale**: <50 users, <500 analyses/day

## 2. Data Models and Schema

### 2.1 Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'consultant', -- 'admin' or 'consultant'
    is_active BOOLEAN DEFAULT TRUE, -- for soft delete
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Resume Analyses Table
```sql
CREATE TABLE resume_analyses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    candidate_name VARCHAR(255) NOT NULL,
    target_industry VARCHAR(100) NOT NULL, -- matches industries.name
    status VARCHAR(50) NOT NULL DEFAULT 'processing', -- 'processing', 'completed', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 Analysis Results Table
```sql
CREATE TABLE analysis_results (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES resume_analyses(id),
    result_xml TEXT NOT NULL, -- Raw XML output from AI agents
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.4 Industries Table
```sql
CREATE TABLE industries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial industries
INSERT INTO industries (name, display_name) VALUES
('strategy_consulting', 'Strategy Consulting'),
('technology_consulting', 'Technology Consulting'),
('ma_consulting', 'M&A Consulting'),
('financial_advisory', 'Financial Advisory Consulting'),
('full_service_consulting', 'Full Service Consulting'),
('system_integrator', 'System Integrator');
```

## 3. Data Integrity Constraints

### 3.1 Foreign Key Constraints
- `resume_analyses.user_id` → `users.id` (NO CASCADE DELETE)
- `analysis_results.analysis_id` → `resume_analyses.id` (CASCADE DELETE)

### 3.2 Check Constraints
- `users.role` IN ('admin', 'consultant')
- `resume_analyses.status` IN ('processing', 'completed', 'failed')
- `email` must be valid email format

### 3.3 Unique Constraints
- `users.email` must be unique
- `industries.name` must be unique

## 4. Performance Indexes
No additional indexes required for MVP beyond primary keys and unique constraints.

## 5. Data Retention Policies

### 5.1 Active Data
- **User Data**: Retained indefinitely
- **Analysis Data**: Retained indefinitely
- **Results**: Retained indefinitely

### 5.2 Deleted Users
- **Soft Delete**: Set `is_active = FALSE`
- **Data Preservation**: All user's analyses remain in database
- **Admin Access**: Can query deleted user's data directly

### 5.3 Privacy Considerations
- **No Resume Storage**: Original resume files not stored
- **No PII in Logs**: Avoid logging sensitive data
- **Result Sanitization**: AI outputs only, no raw resume text

## 6. Security Configuration

### 6.1 Access Control (MVP)
- **Network**: Private IP only (no public endpoint)
- **Authentication**: Strong password for database users
- **SSL**: Not required for private IP connection

### 6.2 Database Users
```sql
-- Application user (limited permissions)
CREATE USER app_user WITH PASSWORD 'strong_random_password_here';
GRANT CONNECT ON DATABASE resume_review TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Admin user (full permissions)
CREATE USER admin_user WITH PASSWORD 'different_strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE resume_review TO admin_user;
```

### 6.3 Connection Security
- **Connection String**: Use private IP address
- **Password Storage**: Store in environment variables
- **Connection Pooling**: Limit to 20 connections

## 7. Backup Strategy (Future Enhancement)
- **MVP**: Rely on Cloud SQL default settings
- **Future**: Daily automated backups with 7-day retention