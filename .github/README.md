# GitHub Workflows

This directory contains GitHub Actions workflows for CI/CD automation.

## Active Workflows

### [staging.yml](workflows/staging.yml)
**Trigger:** Automatic on push to `main` branch and PRs to `main`

Continuous integration and deployment pipeline for staging environment:
- Runs tests and linting (non-blocking for MVP)
- Builds Docker images for backend and frontend
- Deploys to Cloud Run staging environment
- Runs health checks

**Staging URL:** https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app

---

### [production.yml](workflows/production.yml)
**Trigger:** Manual only (`workflow_dispatch`)

Production deployment workflow:
- Deploys backend using image tag from staging
- Builds fresh frontend with production API URL
- Deploys to Cloud Run production environment
- Runs health checks

**Production URL:** https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app

**How to trigger:**
1. Go to [Actions](../../actions)
2. Select "Deploy to Production"
3. Click "Run workflow"
4. Enter backend image tag (default: `staging-latest`)
5. Choose whether to build new frontend (default: `true`)

---

## Documentation

See [docs/](docs/) for detailed CI/CD documentation:
- [CICD_SETUP.md](docs/CICD_SETUP.md) - Complete CI/CD setup guide
- [CICD_QUICKSTART.md](docs/CICD_QUICKSTART.md) - Quick reference

---

## Workflow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Developer Workflow                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    Push to 'main' branch
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      staging.yml (Auto)                      │
│  1. Run tests/linting                                        │
│  2. Build Docker images                                      │
│  3. Deploy to staging                                        │
│  4. Health checks                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    Verify in staging environment
                              │
                              ▼
                    Manual trigger (when ready)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   production.yml (Manual)                    │
│  1. Pull backend image from staging                         │
│  2. Build frontend with prod API URL                        │
│  3. Deploy to production                                     │
│  4. Health checks                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Environment Variables

Both workflows use these common environment variables:

```yaml
GCP_PROJECT_ID: ytgrs-464303
GCP_REGION: us-central1
ARTIFACT_REGISTRY: us-central1-docker.pkg.dev/ytgrs-464303/ai-resume-review-v2
```

---

## Secrets Configuration

Required GitHub secrets:
- Workload Identity Provider: `projects/864523342928/locations/global/workloadIdentityPools/github-actions/providers/github`
- Service Account: `github-actions-deployer@ytgrs-464303.iam.gserviceaccount.com`

---

## Troubleshooting

**Staging deployment failed:**
1. Check [Actions tab](../../actions) for error logs
2. Verify Docker images build successfully
3. Check Cloud Run service logs in GCP Console

**Production deployment failed:**
1. Verify backend image exists in Artifact Registry
2. Check frontend build logs
3. Verify health check endpoints respond

**Health checks failing:**
- Backend health: `/health` endpoint
- Frontend health: Root `/` endpoint
- Wait 30 seconds for services to warm up

---

**Last Updated:** October 9, 2025
