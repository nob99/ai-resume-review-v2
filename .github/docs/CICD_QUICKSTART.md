# CI/CD Quick Start Guide

## 🚀 Deploy to Staging (Automatic)

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Code and commit
git add .
git commit -m "feat: my feature"

# 3. Push and create PR
git push origin feature/my-feature
# Create PR on GitHub → main

# 4. Merge PR
# ✨ Auto-deploys to staging!
# Wait ~8-10 minutes
```

**Staging URLs:**
- Backend: https://ai-resume-review-v2-backend-staging-wnjxxf534a-uc.a.run.app
- Frontend: https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app

---

## 🎯 Deploy to Production (Manual)

```bash
# 1. Test on staging first!

# 2. Go to GitHub Actions
https://github.com/nob99/ai-resume-review-v2/actions

# 3. Click "Deploy to Production"
# 4. Click "Run workflow"
# 5. Configure:
#    - Backend image: staging-latest
#    - Build frontend: ✓ checked
# 6. Click "Run workflow"
# 7. Wait ~6-8 minutes
```

**Production URLs:**
- Backend: https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app
- Frontend: https://ai-resume-review-v2-frontend-prod-wnjxxf534a-uc.a.run.app

---

## 🔄 Rollback Production

```bash
# List revisions
gcloud run revisions list --service=ai-resume-review-v2-backend-prod --region=us-central1

# Rollback backend
gcloud run services update-traffic ai-resume-review-v2-backend-prod \
  --to-revisions=PREVIOUS_REVISION_NAME=100 --region=us-central1

# Rollback frontend
gcloud run services update-traffic ai-resume-review-v2-frontend-prod \
  --to-revisions=PREVIOUS_REVISION_NAME=100 --region=us-central1
```

---

## 📊 Check Deployment Status

```bash
# View workflow runs
https://github.com/nob99/ai-resume-review-v2/actions

# Check service health
curl https://ai-resume-review-v2-backend-staging-wnjxxf534a-uc.a.run.app/health
curl https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app/health

# View logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=ai-resume-review-v2-backend-staging" --limit=20
```

---

## 🗄️ Database Migrations (Manual)

```bash
# ⚠️ NOT automated - run manually before deploying!

# 1. Add public IP temporarily
gcloud sql instances patch ai-resume-review-v2-db-staging --assign-ip

# 2. Get IP address
gcloud sql instances describe ai-resume-review-v2-db-staging --format="value(ipAddresses[0].ipAddress)"

# 3. Run migration
DB_PASS=$(gcloud secrets versions access latest --secret=db-password-staging)
PGPASSWORD=$DB_PASS psql -h IP_ADDRESS -U postgres -d ai_resume_review_staging -f migration.sql

# 4. Remove public IP
gcloud sql instances patch ai-resume-review-v2-db-staging --no-assign-ip

# 5. Repeat for production
```

---

## 🐛 Troubleshooting

### Tests fail in CI
```bash
# Check GitHub Actions logs
# Fix locally and push again
```

### Deployment fails
```bash
# Check Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# Check image exists
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/ytgrs-464303/ai-resume-review-v2/backend
```

### Health check fails
```bash
# Check service status
gcloud run services describe ai-resume-review-v2-backend-staging --region=us-central1

# Check logs for errors
gcloud logging read "resource.labels.service_name=ai-resume-review-v2-backend-staging" \
  --limit=100 --format="table(timestamp,severity,textPayload)"
```

---

## 📚 Full Documentation

See [CICD_SETUP.md](./CICD_SETUP.md) for complete documentation.

---

**Deployment Times:**
- Staging: ~8-10 minutes (automatic on merge)
- Production: ~6-8 minutes (manual trigger)

**Cost:**
- GitHub Actions: $0/month (within free tier)
- Artifact Registry: ~$1-2/month
