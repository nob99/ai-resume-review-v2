# GCP Monitoring Setup - Tier 1 (Essential)

**Version:** 1.0
**Last Updated:** October 8, 2025
**Status:** Production Ready

---

## 📋 Overview

This directory contains scripts to set up **essential production monitoring** for the AI Resume Review Platform deployed on Google Cloud Platform.

**Philosophy:** Best practices, zero over-engineering, zero ongoing maintenance.

---

## 🎯 What Gets Monitored

### **1. Uptime Checks** (2 checks)
- Backend `/health` endpoint - every 5 minutes
- Frontend homepage - every 5 minutes
- Checked from 3 regions: USA, Europe, Asia-Pacific

### **2. Critical Alerts** (3 alerts)
- **Service Downtime:** Triggers when no requests for 5+ minutes
- **High Error Rate:** Triggers when error rate > 10%
- **Database Issues:** Triggers when connections > 80

### **3. Security Monitoring** (1 metric)
- **Failed Logins:** Triggers when > 10 failed login attempts per hour

### **4. Budget Alert** (1 alert)
- Email notification at 80% ($80) and 100% ($100) of monthly budget

---

## 🚀 Quick Start

### **Option 1: Run All Scripts at Once** (Recommended)

```bash
cd scripts/gcp/monitoring
./run-all-setup.sh
```

**Time:** ~5 minutes
**Cost:** $0 (all within GCP free tier)

### **Option 2: Run Scripts Individually**

```bash
# Step 1: Setup notification channels
./1-setup-notification-channels.sh

# Step 2: Create uptime checks
./2-setup-uptime-checks.sh

# Step 3: Create critical alerts
./3-setup-critical-alerts.sh

# Step 4: Create log-based security metrics
./4-setup-log-metrics.sh

# Step 5: Create budget alert
./5-setup-budget-alert.sh
```

---

## 📁 Files in This Directory

| File | Purpose | Run Order |
|------|---------|-----------|
| `run-all-setup.sh` | Master script - runs all setup scripts | - |
| `1-setup-notification-channels.sh` | Creates Slack + Email channels | 1st |
| `2-setup-uptime-checks.sh` | Creates uptime checks | 2nd |
| `3-setup-critical-alerts.sh` | Creates alert policies | 3rd |
| `4-setup-log-metrics.sh` | Creates security metrics | 4th |
| `5-setup-budget-alert.sh` | Creates budget alert | 5th |
| `README.md` | This file | - |

---

## 🔔 Notification Channels

### **Slack**
- **Webhook URL:** `https://hooks.slack.com/services/T06KL5JSNCQ/B09K9MK5KC5/...`
- **Channel:** (configured in Slack)
- **Receives:** All critical alerts + security alerts

### **Email**
- **Address:** `nobu.fukumoto.99@gmail.com`
- **Receives:** All critical alerts + security alerts + budget alerts

---

## ✅ Verification Steps

### **1. Check Notification Channels**
```bash
gcloud alpha monitoring channels list --project=ytgrs-464303
```

**Expected:** 2 channels (Slack + Email)

### **2. Check Uptime Checks**
```bash
gcloud monitoring uptime-checks list --project=ytgrs-464303
```

**Expected:** 2 checks (Backend + Frontend)

### **3. Check Alert Policies**
```bash
gcloud alpha monitoring policies list --project=ytgrs-464303
```

**Expected:** 4-5 policies (3 critical + 1 security + existing)

### **4. Check Log Metrics**
```bash
gcloud logging metrics list --project=ytgrs-464303
```

**Expected:** 1 metric (`failed_login_attempts`)

### **5. Check Budget**
```bash
# Get billing account
BILLING_ACCOUNT=$(gcloud beta billing projects describe ytgrs-464303 \
  --format="value(billingAccountName)" | sed 's|billingAccounts/||')

# List budgets
gcloud billing budgets list --billing-account="$BILLING_ACCOUNT"
```

**Expected:** 1 budget ($100/month)

### **6. Test Slack Notification (Optional)**
```bash
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"✅ GCP Monitoring Setup Complete - Test Message"}'
```

**Expected:** Message appears in Slack channel

---

## 🔧 Troubleshooting

### **Problem: "Notification channels not set up" error**

**Solution:**
```bash
./1-setup-notification-channels.sh
```
Run the notification channels script first before other scripts.

---

### **Problem: "Permission denied" error**

**Solution:**
```bash
# Check GCP authentication
gcloud auth list

# Re-authenticate if needed
gcloud auth login

# Verify project
gcloud config get-value project
# Should show: ytgrs-464303
```

---

### **Problem: Script says "already exists" but I don't see it**

**Solution:**
The script detects existing resources. This is normal and safe. To verify:
```bash
# Check what exists
gcloud alpha monitoring channels list
gcloud monitoring uptime-checks list
gcloud alpha monitoring policies list
```

---

### **Problem: Uptime check creation fails**

**Solution:**
```bash
# Check if Monitoring API is enabled
gcloud services list --enabled | grep monitoring

# Enable if needed
gcloud services enable monitoring.googleapis.com
```

---

### **Problem: Budget alert creation fails**

**Solution:**
```bash
# Check if billing is enabled
gcloud beta billing projects describe ytgrs-464303

# Check if Billing API is enabled
gcloud services enable cloudbilling.googleapis.com
```

---

### **Problem: Not receiving Slack notifications**

**Solution:**
1. Verify webhook URL is correct in script
2. Test webhook manually (see verification steps above)
3. Check Slack app permissions
4. Verify channel exists in Slack

---

### **Problem: Not receiving email notifications**

**Solution:**
1. Check spam folder
2. Verify email address is correct
3. Email notifications may take 5-10 minutes to arrive
4. Check email in GCP Console → Monitoring → Alerting → Notification Channels

---

## 📊 Monitoring Dashboard

**View in GCP Console:**
```
https://console.cloud.google.com/monitoring/dashboards?project=ytgrs-464303
```

**Default Dashboard:** "AI Resume Review - Production Dashboard" (already exists)

**Create Custom Views:**
1. Go to Cloud Console → Monitoring → Dashboards
2. Click on existing dashboard
3. Add widgets for specific metrics you want to track

---

## 💰 Cost Breakdown

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| Uptime Checks | $0 | Free tier: 1M checks/month |
| Alert Policies | $0 | Free tier: 150 MB/month |
| Log Metrics | $0 | Included in Cloud Logging |
| Budget Alerts | $0 | No cost |
| Notification Channels | $0 | No cost |
| **Total** | **$0/month** | All within free tier |

**Future Costs:** Only if you exceed free tier limits (unlikely for MVP)

---

## 🗑️ How to Remove Monitoring

If you need to remove all monitoring (not recommended):

```bash
# Delete uptime checks
gcloud monitoring uptime-checks list --format="value(name)" | \
  xargs -I {} gcloud monitoring uptime-checks delete {} --quiet

# Delete alert policies
gcloud alpha monitoring policies list --format="value(name)" | \
  grep "AI Resume Review" | \
  xargs -I {} gcloud alpha monitoring policies delete {} --quiet

# Delete log metrics
gcloud logging metrics delete failed_login_attempts --quiet

# Delete notification channels
gcloud alpha monitoring channels list --format="value(name)" | \
  grep "AI Resume Review" | \
  xargs -I {} gcloud alpha monitoring channels delete {} --quiet

# Delete budget (manual - go to Billing Console)
```

---

## 📈 What to Monitor (Usage Tips)

### **Daily:**
- Check Slack for any alerts (should be none if all is healthy)

### **Weekly:**
- Review GCP Monitoring Dashboard
- Check for any unusual patterns in error rates
- Verify uptime checks are passing

### **Monthly:**
- Review billing to ensure costs are within budget
- Review alert policies - tune thresholds if needed
- Clean up old logs (optional)

---

## 🔄 Updating Configuration

### **To Change Slack Webhook:**
1. Edit `1-setup-notification-channels.sh`
2. Update `SLACK_WEBHOOK_URL` variable
3. Run the script again (it will update existing channel)

### **To Change Email:**
1. Edit `1-setup-notification-channels.sh` and `5-setup-budget-alert.sh`
2. Update `EMAIL_ADDRESS` variable in both files
3. Run both scripts again

### **To Change Alert Thresholds:**
1. Edit `3-setup-critical-alerts.sh` or `4-setup-log-metrics.sh`
2. Update threshold values
3. Run the script again

---

## 🎓 Understanding the Alerts

### **Service Downtime Alert**
- **Trigger:** No requests for 5+ minutes
- **What it means:** Service is down or unreachable
- **Action:** Check Cloud Run service status, view logs

### **High Error Rate Alert**
- **Trigger:** Error rate > 10%
- **What it means:** Many requests are failing (5xx errors)
- **Action:** Check application logs for errors

### **Database Connection Alert**
- **Trigger:** More than 80 connections
- **What it means:** Database may be overloaded or connection leak
- **Action:** Check for connection leaks, review database queries

### **Failed Login Alert**
- **Trigger:** More than 10 failed logins per hour
- **What it means:** Possible brute force attack
- **Action:** Review authentication logs, consider IP blocking

### **Budget Alert**
- **Trigger:** 80% or 100% of budget spent
- **What it means:** Costs are higher than expected
- **Action:** Review billing dashboard, check for unexpected usage

---

## 📚 Additional Resources

**GCP Documentation:**
- [Cloud Monitoring](https://cloud.google.com/monitoring/docs)
- [Uptime Checks](https://cloud.google.com/monitoring/uptime-checks)
- [Alert Policies](https://cloud.google.com/monitoring/alerts)
- [Log-Based Metrics](https://cloud.google.com/logging/docs/logs-based-metrics)

**Project Documentation:**
- Main README: `/README.md`
- CLAUDE.md: `/CLAUDE.md`
- Deployment Guide: `/HANDOVER.md`

---

## 🆘 Support

**If alerts are firing:**
1. Check the alert documentation (above)
2. View logs in GCP Console
3. Check service status
4. Review recent deployments

**If setup fails:**
1. Check troubleshooting section (above)
2. Verify GCP permissions
3. Check API enablement
4. Review script output for specific errors

---

## ✅ Success Criteria

After running setup, you should have:
- [x] 2 notification channels (Slack + Email)
- [x] 2 uptime checks (Backend + Frontend)
- [x] 4 alert policies (3 critical + 1 security)
- [x] 1 log-based metric (failed logins)
- [x] 1 budget alert ($100/month)
- [x] $0/month monitoring cost

---

**Setup Complete! Your production monitoring is now active.** 🎉

For questions or issues, refer to the troubleshooting section or review GCP Console logs.
