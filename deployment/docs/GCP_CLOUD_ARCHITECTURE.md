# GCP Cloud Architecture - AI Resume Review Platform

**Version**: MVP 1.0
**Date**: 2025-10-06
**Status**: Architecture Design Approved
**Region**: us-central1 (Iowa)

---

## 📋 Executive Summary

This document defines the Google Cloud Platform (GCP) architecture for deploying the AI Resume Review Platform MVP. The architecture follows "simple is best" and "best practice" principles, optimized for cost-effectiveness while maintaining production-ready standards.

**Key Principles:**
- ✅ Simple, no over-engineering
- ✅ Follow GCP best practices
- ✅ Cost-optimized for MVP (~$123-190/month)
- ✅ Production-ready with security first
- ✅ Easy to scale as user base grows

---

## 🏗️ High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Cloud DNS + Cloud CDN (Not in MVP)                 │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│                      Cloud Load Balancer (HTTPS)                      │
│                     SSL Certificate (Managed)                          │
└────────────┬──────────────────────────────────────┬───────────────────┘
             │                                      │
   ┌─────────▼─────────┐                 ┌─────────▼─────────┐
   │   Cloud Run       │                 │   Cloud Run       │
   │   (Frontend)      │                 │   (Backend)       │
   │                   │                 │                   │
   │ Next.js 15.5.2    │──────API────────│ FastAPI 0.104.1   │
   │ React 19.1.0      │                 │ Python 3.12       │
   │ Memory: 512MB     │                 │ Memory: 2GB       │
   │ CPU: 1 vCPU       │                 │ CPU: 2 vCPU       │
   │ Min: 0 instances  │                 │ Min: 1 instances  │
   │ Max: 10 instances │                 │ Max: 20 instances │
   │ Port: 3000        │                 │ Port: 8000        │
   └───────────────────┘                 └─────────┬─────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────┐
                    │                              │              │
         ┌──────────▼──────────┐    ┌─────────────▼──────┐  ┌───▼────────┐
         │   Cloud SQL         │    │  Secret Manager    │  │ In-Memory  │
         │   (PostgreSQL 15)   │    │                    │  │ Cache      │
         │                     │    │ - OPENAI_API_KEY   │  │ (Redis)    │
         │ Instance:           │    │ - DB_PASSWORD      │  │            │
         │   db-f1-micro       │    │ - SECRET_KEY       │  │ No         │
         │ Storage: 10GB SSD   │    │ - ALGORITHM        │  │ Memorystore│
         │ Backup: Daily       │    │                    │  │ for MVP    │
         │ Retention: 7 days   │    │                    │  │            │
         │ HA: No (MVP)        │    │                    │  │            │
         └─────────────────────┘    └────────────────────┘  └────────────┘
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    │                                                   │
         ┌──────────▼──────────┐                           ┌───────────▼──────────┐
         │  Cloud Logging      │                           │  Cloud Monitoring    │
         │  (Structured Logs)  │                           │  (Metrics & Alerts)  │
         │                     │                           │                      │
         │ - Application Logs  │                           │ - Uptime Checks      │
         │ - Request Logs      │                           │ - CPU/Memory Alerts  │
         │ - Error Tracking    │                           │ - Error Rate Alerts  │
         └─────────────────────┘                           │ - Latency Tracking   │
                    │                                      └──────────────────────┘
         ┌──────────▼──────────┐
         │  Cloud Trace        │
         │  (Performance)      │
         │                     │
         │ - Request Tracing   │
         │ - AI Workflow Time  │
         └─────────────────────┘
```

---

## 🎯 Component Details

### 1. Frontend - Cloud Run (Next.js)

**Technology Stack:**
- Next.js 15.5.2
- React 19.1.0
- TypeScript
- Tailwind CSS

**Cloud Run Configuration:**
```yaml
Service Name: ai-resume-review-frontend-{env}
Container Image: us-central1-docker.pkg.dev/{PROJECT_ID}/ai-resume-review/frontend:latest
Region: us-central1
CPU: 1 vCPU
Memory: 512MB
Min Instances: 0 (scale to zero for cost savings)
Max Instances: 10
Concurrency: 80 requests per container
Timeout: 300 seconds (5 minutes)
Port: 3000
Ingress: All traffic
Authentication: Allow unauthenticated
```

**Environment Variables:**
```bash
NEXT_PUBLIC_API_URL=https://ai-resume-review-backend-{env}-{hash}.run.app
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

**Rationale:**
- **Scale to zero**: Minimize costs during low traffic periods
- **512MB memory**: Sufficient for Next.js SSR
- **Concurrency 80**: Standard for stateless web apps
- **Max 10 instances**: Handles ~800 concurrent users

---

### 2. Backend - Cloud Run (FastAPI)

**Technology Stack:**
- FastAPI 0.104.1
- Python 3.12
- LangChain/LangGraph
- OpenAI/Anthropic APIs
- SQLAlchemy 2.0
- Pydantic 2.0

**Cloud Run Configuration:**
```yaml
Service Name: ai-resume-review-backend-{env}
Container Image: us-central1-docker.pkg.dev/{PROJECT_ID}/ai-resume-review/backend:latest
Region: us-central1
CPU: 2 vCPU
Memory: 2GB
Min Instances: 1 (avoid cold starts for better UX)
Max Instances: 20
Concurrency: 20 requests per container (lower due to AI processing)
Timeout: 600 seconds (10 minutes for long AI operations)
Port: 8000
Ingress: All traffic
Authentication: Allow unauthenticated (app handles auth)
```

**Environment Variables:**
```bash
# Database
DB_HOST=/cloudsql/{PROJECT_ID}:us-central1:{INSTANCE_NAME}
DB_PORT=5432
DB_NAME=ai_resume_review_{env}
DB_USER=postgres
DB_PASSWORD={from Secret Manager}

# Redis (In-Memory for MVP)
REDIS_HOST=localhost
REDIS_PORT=6379

# Security
SECRET_KEY={from Secret Manager}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI Configuration
OPENAI_API_KEY={from Secret Manager}
OPENAI_MODEL_NAME=gpt-4
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.3

# Application
ENVIRONMENT={staging|production}
DEBUG=False
LOG_LEVEL=INFO
API_V1_STR=/api/v1
```

**Rationale:**
- **2GB memory**: LangChain/LangGraph + AI agents need more memory
- **Min 1 instance**: Avoid cold starts (users don't wait 10-15s)
- **Concurrency 20**: AI processing is CPU/memory intensive
- **Timeout 600s**: Resume analysis can take 30-60s per request

---

### 3. Database - Cloud SQL (PostgreSQL 15)

**Configuration:**
```yaml
Instance Name: ai-resume-review-db-{env}
Database Version: PostgreSQL 15
Region: us-central1
Zone: Automatic
Instance Type: db-f1-micro (1 vCPU, 3.75GB RAM)
Storage Type: SSD
Storage Size: 10GB
Storage Auto-increase: Enabled (up to 100GB)
High Availability: No (MVP) / Yes (Production later)
Backups:
  - Automated: Daily
  - Retention: 7 days
  - Point-in-time recovery: No (MVP)
Maintenance Window: Sunday 2:00 AM - 3:00 AM (us-central1 time)
Connectivity:
  - Private IP: Yes (VPC peering)
  - Public IP: No (security best practice)
Flags:
  - max_connections: 100
  - shared_buffers: 256MB
  - effective_cache_size: 1GB
```

**Databases:**
- `ai_resume_review_staging` (staging environment)
- `ai_resume_review_prod` (production environment)

**Connection Method:**
Cloud Run connects via Unix socket:
```
/cloudsql/{PROJECT_ID}:us-central1:{INSTANCE_NAME}
```

**Rationale:**
- **db-f1-micro**: Cheapest option, sufficient for MVP (<1000 users)
- **Private IP only**: Security best practice, no public access
- **Daily backups**: Protect against data loss
- **7-day retention**: Balance cost vs recovery window

**When to upgrade:**
- Upgrade to `db-n1-standard-1` when:
  - Active users > 1000
  - Database size > 5GB
  - CPU usage consistently > 80%

---

### 4. Cache - In-Memory (MVP) / Memorystore (Future)

**MVP Approach:**
```python
# Use in-memory cache in Cloud Run instances
# Sufficient for MVP use cases:
# - Rate limiting (file upload, login attempts)
# - Short-lived session data
# - API response caching (5-10 min TTL)

# FastAPI with in-memory cache
from functools import lru_cache
import time

class InMemoryCache:
    def __init__(self):
        self.cache = {}

    def set(self, key: str, value: any, ttl: int = 300):
        expire_at = time.time() + ttl
        self.cache[key] = {"value": value, "expire_at": expire_at}

    def get(self, key: str):
        if key in self.cache:
            if time.time() < self.cache[key]["expire_at"]:
                return self.cache[key]["value"]
            else:
                del self.cache[key]
        return None
```

**Future - Memorystore for Redis:**
```yaml
# When to upgrade: >5000 active users or need shared cache across instances
Tier: Basic (MVP) / Standard (HA)
Memory: 1GB
Version: 7.x
Region: us-central1
Network: Same VPC as Cloud SQL
Auth: Enabled
Cost: ~$50/month
```

**Rationale:**
- **In-memory for MVP**: Save $50/month
- **Simple implementation**: No external dependencies
- **Easy migration**: Switch to Memorystore when needed

---

### 5. Secrets - Secret Manager

**Stored Secrets:**

| Secret Name | Description | Access |
|------------|-------------|--------|
| `openai-api-key` | OpenAI API key for GPT-4 | Backend Cloud Run |
| `anthropic-api-key` | Anthropic API key (optional) | Backend Cloud Run |
| `db-password-staging` | Cloud SQL password (staging) | Backend Cloud Run (staging) |
| `db-password-prod` | Cloud SQL password (production) | Backend Cloud Run (prod) |
| `jwt-secret-key` | JWT signing secret | Backend Cloud Run |

**Access Pattern:**
```python
# Backend accesses secrets via Secret Manager API
from google.cloud import secretmanager

def get_secret(secret_name: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Example usage
OPENAI_API_KEY = get_secret("openai-api-key")
```

**IAM Permissions:**
- Backend Cloud Run service account: `roles/secretmanager.secretAccessor`

**Rationale:**
- **No hardcoded secrets**: Security best practice
- **Centralized management**: Easy rotation
- **Audit logging**: Track secret access
- **Version control**: Keep secret history

---

### 6. Load Balancer - Cloud Load Balancer

**Configuration:**
```yaml
Type: Global External Application Load Balancer
SSL Certificate: Google-managed certificate (auto-renewal)
Backend Services:
  - Frontend: Cloud Run service (ai-resume-review-frontend-prod)
  - Backend: Cloud Run service (ai-resume-review-backend-prod)
Routing Rules:
  - Host: app.yourcompany.com → Frontend
  - Host: api.yourcompany.com → Backend
  - Path: /api/* → Backend
  - Path: /* → Frontend
Health Checks:
  - Frontend: GET /api/health
  - Backend: GET /health
Timeout: 30 seconds
```

**MVP Domain Structure:**
```
Frontend: https://ai-resume-review-frontend-prod-{hash}.run.app
Backend:  https://ai-resume-review-backend-prod-{hash}.run.app
```

**Future Custom Domain:**
```
Frontend: https://app.yourcompany.com
Backend:  https://api.yourcompany.com
```

**Rationale:**
- **Single HTTPS entry point**: Professional, secure
- **Managed SSL**: Auto-renewal, no manual cert management
- **Path-based routing**: Flexible routing rules
- **No CDN for MVP**: Save $20/month, add later if needed

---

### 7. Monitoring & Observability

#### Cloud Logging
```yaml
Log Types:
  - Application Logs (structured JSON)
  - Request/Response Logs
  - Error Logs
  - AI Workflow Logs

Log Retention: 30 days
Log Exports: None (MVP) / BigQuery (future analytics)

Example Log Entry:
{
  "timestamp": "2025-10-06T10:30:00Z",
  "severity": "INFO",
  "service": "backend",
  "message": "Resume analysis completed",
  "request_id": "abc123",
  "user_id": "user-uuid",
  "industry": "Strategy Consulting",
  "duration_ms": 45000,
  "ai_model": "gpt-4"
}
```

#### Cloud Monitoring
```yaml
Uptime Checks:
  - Frontend: Every 1 minute
  - Backend: Every 1 minute

Alert Policies:
  1. High CPU Usage:
     - Condition: CPU > 80% for 5 minutes
     - Notification: Email

  2. High Memory Usage:
     - Condition: Memory > 90% for 5 minutes
     - Notification: Email

  3. Error Rate:
     - Condition: Error rate > 5% for 5 minutes
     - Notification: Email + Slack

  4. High Latency:
     - Condition: P95 latency > 5 seconds
     - Notification: Email

  5. Database Connection Errors:
     - Condition: Connection errors > 10 in 5 minutes
     - Notification: Email + Slack

Dashboards:
  - Request Rate (requests/second)
  - Error Rate (errors/total requests)
  - Latency (P50, P95, P99)
  - CPU & Memory Usage
  - Database Connections
  - AI Analysis Duration
```

#### Cloud Trace
```yaml
Tracing:
  - HTTP request tracing
  - Database query tracing
  - AI workflow tracing

Sample Rate: 10% (MVP) / 100% (debugging)
```

---

## 🌍 Environment Architecture

### Staging Environment
```yaml
Purpose: Pre-production testing
URL:
  - Frontend: https://ai-resume-review-frontend-staging-{hash}.run.app
  - Backend: https://ai-resume-review-backend-staging-{hash}.run.app

Cloud Run:
  - Frontend: Min 0, Max 5 instances
  - Backend: Min 0, Max 10 instances

Cloud SQL:
  - Instance: db-f1-micro
  - Database: ai_resume_review_staging
  - Backups: Weekly

Secrets:
  - Separate secrets from production
  - Can use test OpenAI API key (cheaper)

Deployment Trigger:
  - Automatic on push to 'staging' branch
```

### Production Environment
```yaml
Purpose: Live production
URL:
  - Frontend: https://ai-resume-review-frontend-prod-{hash}.run.app (MVP)
            → https://app.yourcompany.com (future)
  - Backend: https://ai-resume-review-backend-prod-{hash}.run.app (MVP)
           → https://api.yourcompany.com (future)

Cloud Run:
  - Frontend: Min 0, Max 10 instances
  - Backend: Min 1, Max 20 instances

Cloud SQL:
  - Instance: db-f1-micro
  - Database: ai_resume_review_prod
  - Backups: Daily, 7-day retention

Secrets:
  - Production OpenAI API key
  - Strong JWT secret (256-bit)

Deployment Trigger:
  - Manual approval after staging tests pass
  - Only from 'main' branch
```

---

## 🚀 CI/CD Architecture (GitHub Actions)

### Workflow Overview
```
Git Push (feature branch) → Run Tests → Code Review → Merge to Staging

Git Push (staging branch) → GitHub Actions:
  1. Run Unit Tests (Jest, Pytest)
  2. Run Linting (ESLint, Black, Flake8)
  3. Build Docker Images (frontend, backend)
  4. Push to Artifact Registry
  5. Deploy to Staging
  6. Run Integration Tests on Staging
  7. Notify team (Slack)

Manual Approval → Deploy to Production:
  1. Pull images from Artifact Registry
  2. Deploy to Production Cloud Run
  3. Run smoke tests
  4. Notify team (Slack)
  5. Monitor for 30 minutes
```

### GitHub Actions Files
```
.github/workflows/
├── test.yml                    # Run tests on PR
├── deploy-staging.yml          # Auto-deploy to staging
├── deploy-production.yml       # Manual deploy to prod
└── rollback.yml                # Rollback to previous version
```

### Workload Identity Setup
```yaml
# Secure authentication: GitHub Actions → GCP
# No service account keys needed!

GCP Side:
  - Workload Identity Pool
  - Workload Identity Provider (GitHub)
  - Service Account with Cloud Run permissions

GitHub Side:
  - Repository secrets (PROJECT_ID, etc.)
  - OIDC token for authentication
```

---

## 🔐 Security Architecture

### Network Security
```yaml
Cloud SQL:
  - Private IP only (no public access)
  - VPC peering with Cloud Run
  - Authorized networks: None

Cloud Run:
  - HTTPS only (HTTP redirects to HTTPS)
  - VPC egress for database connections
  - No direct internet access to database

Secrets:
  - Stored in Secret Manager
  - IAM-based access control
  - Audit logging enabled
```

### Application Security
```yaml
Authentication:
  - JWT tokens (access: 30min, refresh: 7 days)
  - Bcrypt password hashing (12 rounds)
  - Refresh token rotation

Authorization:
  - Role-based access control (consultant, admin)
  - Feature flags for admin features

Rate Limiting:
  - Login: 5 attempts per 15 minutes
  - File upload: 10 uploads per hour per user
  - API requests: 100 requests per minute per user

File Upload Security:
  - Max size: 30MB
  - Allowed types: PDF, DOCX
  - Virus scanning: Future enhancement
  - No persistent storage (process in-memory only)

Input Validation:
  - Pydantic models for all inputs
  - SQL injection prevention (SQLAlchemy ORM)
  - XSS prevention (React escaping)
```

### Data Security
```yaml
Encryption at Rest:
  - Cloud SQL: AES-256 encryption (default)
  - Secrets: Encrypted by Secret Manager

Encryption in Transit:
  - HTTPS everywhere (TLS 1.2+)
  - Database connections over Unix socket (encrypted)

Data Retention:
  - Resume text: Deleted after analysis (no storage)
  - Analysis results: Stored indefinitely
  - Logs: 30 days retention
  - Backups: 7 days retention

Compliance:
  - GDPR: User data deletion on request
  - Data residency: us-central1 (USA)
```

---

## 💰 Cost Breakdown

### Staging Environment
| Service | Configuration | Est. Cost/Month |
|---------|--------------|----------------|
| Cloud Run (Frontend) | 512MB, avg 0.5 instance | $3-5 |
| Cloud Run (Backend) | 2GB, avg 0.5 instance | $10-15 |
| Cloud SQL | db-f1-micro, 10GB | $25 |
| Secret Manager | 5 secrets | $0.06 |
| Cloud Logging | 5GB logs | $2.50 |
| **Staging Total** | | **$40-47/month** |

### Production Environment
| Service | Configuration | Est. Cost/Month |
|---------|--------------|----------------|
| Cloud Run (Frontend) | 512MB, avg 1 instance | $5-15 |
| Cloud Run (Backend) | 2GB, min 1 instance | $30-50 |
| Cloud SQL | db-f1-micro, 10GB | $25-35 |
| Secret Manager | 5 secrets | $0.06 |
| Load Balancer | 100GB traffic | $18-25 |
| Cloud Logging | 10GB logs | $5 |
| Cloud Monitoring | Basic metrics | Free |
| **Production Total** | | **$83-130/month** |

### CI/CD & Shared Services
| Service | Configuration | Est. Cost/Month |
|---------|--------------|----------------|
| GitHub Actions | Within free tier | $0 |
| Artifact Registry | Docker images storage | $1-2 |
| **CI/CD Total** | | **$1-2/month** |

### Grand Total
```
Staging:     $40-47/month
Production:  $83-130/month
CI/CD:       $1-2/month
─────────────────────────
TOTAL:       $124-179/month
```

### Additional Variable Costs
```
OpenAI API (GPT-4):
  - $0.01-0.03 per resume analysis
  - Estimated: $50-200/month (depends on usage)

Egress Bandwidth:
  - First 1GB free
  - $0.12/GB thereafter
  - Estimated: $5-10/month

Total with AI costs: $179-389/month
```

---

## 📊 Performance Targets

### Latency Targets
```yaml
Frontend (Cold Start): < 2 seconds
Frontend (Warm): < 500ms
Backend (Cold Start): < 10 seconds
Backend (Warm): < 200ms
Resume Analysis (AI): 30-60 seconds
Database Queries: < 100ms (p95)
```

### Throughput Targets
```yaml
Concurrent Users: 100-500 (MVP)
Requests/Second: 50-100
Resume Analyses/Hour: 60-120
```

### Availability Targets
```yaml
Uptime SLA: 99.5% (MVP) / 99.9% (future)
Monthly Downtime: < 3.6 hours (MVP)
Recovery Time Objective (RTO): < 1 hour
Recovery Point Objective (RPO): < 24 hours
```

---

## 🔄 Scaling Strategy

### Current Capacity (MVP)
```
Cloud Run Frontend: Max 10 instances × 80 concurrency = 800 users
Cloud Run Backend: Max 20 instances × 20 concurrency = 400 concurrent analyses
Cloud SQL: db-f1-micro = ~100 concurrent connections
```

### When to Scale
```yaml
Frontend Scale Trigger:
  - CPU > 80% for 10 minutes → Increase max instances to 20
  - Request latency > 2s (p95) → Increase memory to 1GB

Backend Scale Trigger:
  - CPU > 80% for 10 minutes → Increase max instances to 50
  - Memory > 85% → Increase memory to 4GB
  - Queue depth > 50 → Consider async processing

Database Scale Trigger:
  - CPU > 80% for 10 minutes → Upgrade to db-n1-standard-1
  - Storage > 8GB → Increase to 20GB
  - Connections > 80 → Increase max_connections
```

### Future Scaling Options
```
1. Async Processing:
   - Add Cloud Tasks for background jobs
   - Queue-based resume analysis
   - Cost: +$10-20/month

2. Redis Cache:
   - Memorystore Basic 1GB
   - Reduce database load
   - Cost: +$50/month

3. Multi-Region:
   - Deploy to us-central1 + asia-northeast1
   - Global load balancing
   - Cost: +100% (double infrastructure)

4. CDN:
   - Cloud CDN for static assets
   - Faster global load times
   - Cost: +$20-30/month
```

---

## 🛠️ Operational Procedures

### Deployment Process
```bash
# Staging Deployment (Automatic)
1. Push to 'staging' branch
2. GitHub Actions runs tests
3. Build Docker images
4. Deploy to Cloud Run (staging)
5. Run integration tests
6. Notify team

# Production Deployment (Manual Approval)
1. Staging tests pass
2. Product owner approves
3. Trigger production workflow
4. Deploy to Cloud Run (prod)
5. Run smoke tests
6. Monitor for 30 minutes
```

### Rollback Process
```bash
# If production deployment fails:
1. Trigger rollback workflow
2. Deploy previous working version
3. Verify health checks pass
4. Investigate issue in staging
```

### Database Migration Process
```bash
# Alembic migrations on Cloud Run
1. Create migration: alembic revision --autogenerate -m "description"
2. Test on local database
3. Deploy to staging
4. Run migration: alembic upgrade head
5. Verify schema changes
6. Deploy to production
7. Run migration: alembic upgrade head
8. Monitor for errors
```

### Incident Response
```
1. Alert triggered (email/Slack)
2. Check Cloud Monitoring dashboard
3. Review Cloud Logging for errors
4. Identify root cause
5. Apply fix or rollback
6. Document incident
7. Post-mortem meeting
```

---

## 📝 Next Steps

### Phase 1: GCP Setup (Week 1)
- [ ] Create GCP project
- [ ] Enable required APIs
- [ ] Set up billing alerts
- [ ] Create service accounts
- [ ] Configure Workload Identity
- [ ] Set up Artifact Registry

### Phase 2: Infrastructure Deployment (Week 1-2)
- [ ] Deploy Cloud SQL (staging + prod)
- [ ] Configure Secret Manager
- [ ] Deploy backend to Cloud Run (staging)
- [ ] Deploy frontend to Cloud Run (staging)
- [ ] Test staging environment

### Phase 3: CI/CD Setup (Week 2)
- [ ] Create GitHub Actions workflows
- [ ] Test automated staging deployment
- [ ] Test manual production deployment
- [ ] Set up rollback workflow

### Phase 4: Monitoring & Security (Week 2-3)
- [ ] Configure Cloud Monitoring alerts
- [ ] Set up uptime checks
- [ ] Enable Cloud Trace
- [ ] Security audit
- [ ] Load testing

### Phase 5: Production Launch (Week 3)
- [ ] Deploy to production
- [ ] Smoke tests
- [ ] User acceptance testing
- [ ] Documentation
- [ ] Team training

---

## 🔗 Related Documents

- [Local Development Guide](./CLAUDE.md)
- [Product Vision](./knowledge/design/product_vision.md)
- [Current Architecture](./knowledge/design/architecture.md)
- [Database Schema](./database/docs/schema.md)
- [API Documentation](./backend/README.md)

---

## 📞 Support & Contacts

**GCP Resources:**
- GCP Console: https://console.cloud.google.com
- Cloud Run Docs: https://cloud.google.com/run/docs
- Cloud SQL Docs: https://cloud.google.com/sql/docs
- Secret Manager Docs: https://cloud.google.com/secret-manager/docs

**Monitoring:**
- Cloud Monitoring: https://console.cloud.google.com/monitoring
- Cloud Logging: https://console.cloud.google.com/logs
- Cloud Trace: https://console.cloud.google.com/traces

---

**Document Version**: 1.0
**Last Updated**: 2025-10-06
**Approved By**: Product Team
**Next Review**: After MVP launch
