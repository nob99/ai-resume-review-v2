# Infrastructure Requirements

## 1. Overview
Google Cloud Platform infrastructure using Cloud Run for containerized services, Cloud SQL for database, and minimal additional services for MVP. Deployment via gcloud CLI with production-only environment.

### Key Decisions
- **Platform**: Google Cloud Platform (GCP)
- **Compute**: Cloud Run (serverless containers)
- **Database**: Cloud SQL PostgreSQL
- **Deployment**: gcloud CLI (manual)
- **Environment**: Production only (MVP)

## 2. Cloud Run Specifications

### 2.1 Frontend Service (Next.js)
```yaml
Service Name: resume-review-frontend
Memory: 1GB
CPU: 1 vCPU
Min Instances: 0 (cold start acceptable)
Max Instances: 5
Timeout: 60 seconds
Port: 3000
Concurrency: 100
```

### 2.2 Backend Service (FastAPI)
```yaml
Service Name: resume-review-backend
Memory: 2GB (for AI processing)
CPU: 2 vCPU
Min Instances: 0 (cold start acceptable)
Max Instances: 5
Timeout: 900 seconds (15 minutes for AI processing)
Port: 8000
Concurrency: 10 (due to AI processing load)
```

### 2.3 Cold Start Considerations
- **Expected delay**: 5-10 seconds on first request after idle
- **Acceptable for MVP**: Cost savings outweigh occasional delays
- **User impact**: Show loading message during processing

## 3. Database Infrastructure

### 3.1 Cloud SQL Instance
```yaml
Engine: PostgreSQL 15
Machine Type: db-f1-micro
Storage: 10GB SSD
Availability: Single zone (MVP)
Backups: Default GCP automated backups
Network: Private IP only
Connection Limit: 25
```

## 4. Security Configuration

### 4.1 Network Security
- **HTTPS**: Automatic via Cloud Run
- **Private IPs**: Database not publicly accessible
- **Service Communication**: Via private network

### 4.2 Secrets Management
```bash
# Store sensitive data in Secret Manager
- JWT_SECRET_KEY
- DATABASE_PASSWORD
- OPENAI_API_KEY

# Access in Cloud Run via environment variables
env:
  - name: JWT_SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: jwt-secret
        key: latest
```

### 4.3 Service Accounts
- **Frontend SA**: `resume-frontend@project.iam.gserviceaccount.com`
- **Backend SA**: `resume-backend@project.iam.gserviceaccount.com`
- **Permissions**: Minimal required for each service

## 5. Deployment Process

### 5.1 Build and Deploy Commands

#### Frontend Deployment
```bash
# Build container
docker build -t gcr.io/[PROJECT_ID]/resume-frontend:latest ./frontend

# Push to Container Registry
docker push gcr.io/[PROJECT_ID]/resume-frontend:latest

# Deploy to Cloud Run
gcloud run deploy resume-review-frontend \
  --image gcr.io/[PROJECT_ID]/resume-frontend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60 \
  --min-instances 0 \
  --max-instances 5
```

#### Backend Deployment
```bash
# Build container
docker build -t gcr.io/[PROJECT_ID]/resume-backend:latest ./backend

# Push to Container Registry
docker push gcr.io/[PROJECT_ID]/resume-backend:latest

# Deploy to Cloud Run
gcloud run deploy resume-review-backend \
  --image gcr.io/[PROJECT_ID]/resume-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 900 \
  --min-instances 0 \
  --max-instances 5 \
  --set-env-vars "DATABASE_HOST=private-ip" \
  --set-secrets "JWT_SECRET_KEY=jwt-secret:latest"
```

### 5.2 Database Setup
```bash
# Create Cloud SQL instance
gcloud sql instances create resume-review-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --network=default \
  --no-assign-ip

# Create database
gcloud sql databases create resume_review \
  --instance=resume-review-db

# Set root password
gcloud sql users set-password postgres \
  --instance=resume-review-db \
  --password=[SECURE_PASSWORD]
```

## 6. Monitoring and Logging

### 6.1 Cloud Logging
- **Automatic**: All container logs collected
- **Retention**: 30 days (default free tier)
- **Access**: Via GCP Console Logs Explorer
- **Log levels**: ERROR, WARNING, INFO

### 6.2 Basic Monitoring
- **Cloud Monitoring**: Default metrics (CPU, memory, requests)
- **Uptime Checks**: Simple HTTPS health check
- **Alerts**: Email notification for service downtime
- **Dashboard**: Basic Cloud Run metrics view

### 6.3 Error Alerting
```yaml
Alert Policy:
  - Condition: Error logs > 10 in 5 minutes
  - Notification: Email to admin
  - Auto-resolve: When condition clears
```

## 7. Availability and Performance

### 7.1 Service Level Objectives (SLOs)
- **Uptime Target**: 99% (allows ~7 hours downtime/month)
- **Response Time**: <2 seconds for UI, <5 minutes for AI analysis
- **Region**: Single region (us-central1)
- **Disaster Recovery**: Manual redeploy from git

### 7.2 Performance Considerations
- **Cold Start Mitigation**: None for MVP
- **Caching**: None for MVP
- **CDN**: None for MVP
- **Load Balancing**: Automatic via Cloud Run

## 8. Cost Management

### 8.1 Resource Limits
- **Cloud Run**: Max 5 instances per service
- **Database**: Fixed size (no auto-growth)
- **Estimated Cost**: ~$50-100/month for low usage

### 8.2 Cost Monitoring
- **Manual**: Check GCP Console billing
- **Budget Alerts**: Optional setup in billing
- **No automation**: Manual intervention if needed