# Daily GCP Cost Reporter - Implementation Plan

**Status**: ⏸️ Suspended - Waiting for Billing Account Access
**Created**: October 13, 2025
**Estimated Time**: 45 minutes
**Estimated Cost**: < $1/month

---

## Overview

Implement an automated daily cost reporting system that sends GCP spending reports to Slack every morning at 9:00 AM JST.

### What You'll Get

```
💰 Daily GCP Cost Report
January 13, 2025

📊 Yesterday's Cost: $12.34
📉 -8% vs previous day

Breakdown by Service:
• Cloud Run: $5.67 (46%)
• Cloud SQL: $4.32 (35%)
• Networking: $1.89 (15%)
• Cloud Storage: $0.46 (4%)

📈 Month-to-Date: $156.78
💵 Projected Monthly: $362.15

ℹ️ Note: Billing data is ~1 day delayed

[View Detailed Billing →]
```

---

## Architecture Design

### Components

1. **Cloud Function** (Python 3.11)
   - Queries Cloud Billing API for cost data
   - Reads Slack webhook from GCP Monitoring notification channel
   - Formats and sends Slack message
   - Runtime: ~5 seconds per execution

2. **Cloud Scheduler**
   - Triggers function daily at 9:00 AM JST
   - Uses OIDC authentication (secure)
   - No public endpoints

3. **Service Account** (`cost-reporter@ytgrs-464303.iam.gserviceaccount.com`)
   - Least privilege permissions
   - Only reads billing data and monitoring channels

### Security Features

✅ **No secrets in code** - Webhook read from GCP Monitoring channel dynamically
✅ **Least privilege** - Service account has only required permissions
✅ **Authentication required** - Function not publicly accessible
✅ **OIDC tokens** - Scheduler uses secure authentication
✅ **Audit logging** - All function invocations logged
✅ **Single source of truth** - Webhook URL from existing notification channel

---

## Prerequisites

### ⚠️ BLOCKER: Billing Account Access Required

**Current Status**:
- Project: `ytgrs-464303`
- Billing Account: `011275-97802D-6B812D`
- Your Account: `rp005058@gmail.com`
- **Issue**: No permission to access billing account

**Required Action**:
Contact the billing account administrator and request one of these roles:
- `Billing Account Viewer` (roles/billing.viewer) - **Recommended** (read-only)
- `Billing Account Administrator` (roles/billing.admin) - Full access

**How to Request**:
1. Find billing account owner at: https://console.cloud.google.com/billing/011275-97802D-6B812D
2. Request `Billing Account Viewer` role
3. Explain: "Need read-only access to implement automated daily cost reporting to Slack"

**How to Verify Access**:
```bash
gcloud billing accounts describe 011275-97802D-6B812D
```
If this command succeeds, you have access. Then resume implementation.

### Technical Prerequisites (Already Available)
- ✅ GCP Project: `ytgrs-464303`
- ✅ Slack webhook configured in GCP Monitoring
- ✅ Notification Channel: `projects/ytgrs-464303/notificationChannels/10908127531765369450`
- ✅ GitHub repository access

---

## Implementation Steps

### Phase 1: Setup & Prerequisites (5 minutes)

#### Step 1.1: Enable Required APIs
```bash
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbilling.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

#### Step 1.2: Create Dedicated Service Account
```bash
gcloud iam service-accounts create cost-reporter \
  --display-name="Daily Cost Reporter" \
  --description="Reads billing data and sends daily cost reports to Slack"
```

#### Step 1.3: Grant Minimal Permissions

**Permission 1: Read billing data**
```bash
# Try project-level first
gcloud projects add-iam-policy-binding ytgrs-464303 \
  --member="serviceAccount:cost-reporter@ytgrs-464303.iam.gserviceaccount.com" \
  --role="roles/billing.viewer"

# If that doesn't work, request org-level access from billing admin
```

**Permission 2: Read monitoring notification channels**
```bash
gcloud projects add-iam-policy-binding ytgrs-464303 \
  --member="serviceAccount:cost-reporter@ytgrs-464303.iam.gserviceaccount.com" \
  --role="roles/monitoring.viewer"
```

**Verification**:
```bash
gcloud projects get-iam-policy ytgrs-464303 \
  --flatten="bindings[].members" \
  --filter="bindings.members:cost-reporter@ytgrs-464303.iam.gserviceaccount.com"
```

---

### Phase 2: Create Cloud Function (20 minutes)

#### Directory Structure
```
scripts/gcp/cost-reporter/
├── main.py                 # Cloud Function entry point (~150 lines)
├── requirements.txt        # Python dependencies
├── deploy.sh              # Deployment script
├── test.sh                # Manual test script
└── README.md              # Documentation
```

#### Step 2.1: main.py - Core Logic

**Function Entry Point**:
```python
import functions_framework
from google.cloud import monitoring_v3, billing_v1
import requests
from datetime import datetime, timedelta
import os

@functions_framework.http
def send_daily_cost_report(request):
    """
    Cloud Function entry point.
    Triggered daily by Cloud Scheduler.
    """
    try:
        # 1. Get Slack webhook from monitoring channel
        slack_webhook = get_slack_webhook()

        # 2. Query billing data
        cost_data = get_billing_data()

        # 3. Format Slack message
        message = format_slack_message(cost_data)

        # 4. Send to Slack
        response = requests.post(slack_webhook, json=message)
        response.raise_for_status()

        return {"status": "success", "message": "Cost report sent to Slack"}

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {"status": "error", "message": str(e)}, 500
```

**Get Slack Webhook from Monitoring Channel**:
```python
def get_slack_webhook():
    """Read Slack webhook URL from GCP Monitoring notification channel."""
    client = monitoring_v3.NotificationChannelServiceClient()
    channel_id = os.environ.get('NOTIFICATION_CHANNEL_ID')

    channel = client.get_notification_channel(name=channel_id)
    webhook_url = channel.labels.get('url')

    if not webhook_url:
        raise ValueError("Webhook URL not found in notification channel")

    return webhook_url
```

**Query Billing Data**:
```python
def get_billing_data():
    """Query Cloud Billing API for yesterday's costs."""
    from google.cloud import billing_budgets_v1

    # Query billing export or use Cloud Billing API
    # Get costs for yesterday
    # Group by service (Cloud Run, Cloud SQL, etc.)
    # Calculate month-to-date total
    # Calculate projected monthly cost

    # Return structured data
    return {
        'yesterday_cost': 12.34,
        'yesterday_change_pct': -8.0,
        'breakdown': [
            {'service': 'Cloud Run', 'cost': 5.67, 'percentage': 46},
            {'service': 'Cloud SQL', 'cost': 4.32, 'percentage': 35},
            {'service': 'Networking', 'cost': 1.89, 'percentage': 15},
            {'service': 'Other', 'cost': 0.46, 'percentage': 4},
        ],
        'month_to_date': 156.78,
        'projected_monthly': 362.15,
        'date': '2025-01-13'
    }
```

**Format Slack Message**:
```python
def format_slack_message(cost_data):
    """Format cost data as Slack Block Kit message."""

    # Emoji indicators
    trend_emoji = "📉" if cost_data['yesterday_change_pct'] < 0 else "📈"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "💰 Daily GCP Cost Report"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{cost_data['date']}*"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*📊 Yesterday's Cost:*\n${cost_data['yesterday_cost']:.2f}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*{trend_emoji} Change:*\n{cost_data['yesterday_change_pct']:+.1f}% vs previous day"
                }
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Breakdown by Service:*\n" + "\n".join([
                    f"• {item['service']}: ${item['cost']:.2f} ({item['percentage']}%)"
                    for item in cost_data['breakdown']
                ])
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*📈 Month-to-Date:*\n${cost_data['month_to_date']:.2f}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*💵 Projected Monthly:*\n${cost_data['projected_monthly']:.2f}"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "ℹ️ _Note: Billing data is typically 1-2 days delayed_"
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Detailed Billing"
                    },
                    "url": f"https://console.cloud.google.com/billing/011275-97802D-6B812D/reports?project=ytgrs-464303"
                }
            ]
        }
    ]

    return {
        "text": "💰 Daily GCP Cost Report",
        "blocks": blocks
    }
```

#### Step 2.2: requirements.txt
```txt
functions-framework==3.5.0
google-cloud-monitoring==2.16.0
google-cloud-billing==1.12.0
requests==2.31.0
```

#### Step 2.3: deploy.sh
```bash
#!/bin/bash
# deploy.sh - Deploy cost reporter Cloud Function

set -e

PROJECT_ID="ytgrs-464303"
FUNCTION_NAME="daily-cost-reporter"
REGION="us-central1"
SERVICE_ACCOUNT="cost-reporter@${PROJECT_ID}.iam.gserviceaccount.com"
NOTIFICATION_CHANNEL_ID="projects/ytgrs-464303/notificationChannels/10908127531765369450"
BILLING_ACCOUNT_ID="011275-97802D-6B812D"

echo "🚀 Deploying ${FUNCTION_NAME} to ${REGION}..."

gcloud functions deploy ${FUNCTION_NAME} \
  --gen2 \
  --runtime=python311 \
  --region=${REGION} \
  --source=. \
  --entry-point=send_daily_cost_report \
  --trigger-http \
  --no-allow-unauthenticated \
  --service-account=${SERVICE_ACCOUNT} \
  --memory=256MB \
  --timeout=60s \
  --set-env-vars=NOTIFICATION_CHANNEL_ID=${NOTIFICATION_CHANNEL_ID},BILLING_ACCOUNT_ID=${BILLING_ACCOUNT_ID} \
  --project=${PROJECT_ID}

echo "✅ Function deployed successfully!"
echo ""
echo "Function URL:"
gcloud functions describe ${FUNCTION_NAME} \
  --region=${REGION} \
  --format="value(serviceConfig.uri)"
```

#### Step 2.4: test.sh
```bash
#!/bin/bash
# test.sh - Manually trigger cost reporter function

set -e

PROJECT_ID="ytgrs-464303"
FUNCTION_NAME="daily-cost-reporter"
REGION="us-central1"

echo "🧪 Testing ${FUNCTION_NAME}..."

# Get function URL
FUNCTION_URL=$(gcloud functions describe ${FUNCTION_NAME} \
  --region=${REGION} \
  --format="value(serviceConfig.uri)")

echo "Function URL: ${FUNCTION_URL}"
echo ""

# Trigger function with authenticated request
gcloud functions call ${FUNCTION_NAME} \
  --region=${REGION} \
  --data='{}'

echo ""
echo "✅ Function triggered! Check Slack for the message."
echo "📋 View logs:"
echo "   gcloud functions logs read ${FUNCTION_NAME} --region=${REGION} --limit=50"
```

---

### Phase 3: Create Cloud Scheduler (5 minutes)

#### Step 3.1: Create Scheduler Job
```bash
#!/bin/bash
# Create daily cost report scheduler job

PROJECT_ID="ytgrs-464303"
FUNCTION_NAME="daily-cost-reporter"
REGION="us-central1"
SERVICE_ACCOUNT="cost-reporter@${PROJECT_ID}.iam.gserviceaccount.com"

# Get function URL
FUNCTION_URL=$(gcloud functions describe ${FUNCTION_NAME} \
  --region=${REGION} \
  --format="value(serviceConfig.uri)")

echo "Creating Cloud Scheduler job..."

gcloud scheduler jobs create http daily-cost-report \
  --location=${REGION} \
  --schedule="0 9 * * *" \
  --time-zone="Asia/Tokyo" \
  --uri="${FUNCTION_URL}" \
  --http-method=POST \
  --oidc-service-account-email=${SERVICE_ACCOUNT} \
  --oidc-token-audience="${FUNCTION_URL}" \
  --description="Daily GCP cost report sent to Slack at 9 AM JST"

echo "✅ Scheduler job created!"
```

#### Step 3.2: Verify Scheduler
```bash
# List scheduler jobs
gcloud scheduler jobs list --location=us-central1

# Describe the job
gcloud scheduler jobs describe daily-cost-report --location=us-central1

# Manually trigger for testing
gcloud scheduler jobs run daily-cost-report --location=us-central1
```

---

### Phase 4: Testing & Verification (10 minutes)

#### Step 4.1: Manual Function Test
```bash
cd scripts/gcp/cost-reporter
./test.sh
```

#### Step 4.2: Verify in Slack
- ✅ Message appears in correct Slack channel
- ✅ Cost data looks accurate
- ✅ Formatting is clean and readable
- ✅ Links work correctly

#### Step 4.3: Check Logs
```bash
# View function logs
gcloud functions logs read daily-cost-reporter --region=us-central1 --limit=50

# View scheduler logs
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=daily-cost-report" --limit=20
```

#### Step 4.4: Test Scheduler
```bash
# Manually trigger scheduler
gcloud scheduler jobs run daily-cost-report --location=us-central1

# Wait 10 seconds, then check Slack
```

---

### Phase 5: Documentation (5 minutes)

#### Create README.md
Document:
- What the cost reporter does
- How to deploy
- How to test manually
- How to troubleshoot
- How to modify schedule
- Security considerations

---

## Cost Analysis

### Monthly Costs (Estimated)

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Functions | 30 invocations/month × 5 seconds | ~$0.01 |
| Cloud Scheduler | 1 job (FREE tier) | $0.00 |
| Cloud Billing API | 30 queries/month | $0.00 |
| Cloud Monitoring API | 30 queries/month | $0.00 |
| **Total** | | **< $1/month** |

### Cost Optimization
- Function runs only once per day (not continuously)
- Uses minimal memory (256MB)
- Short execution time (~5 seconds)
- All within GCP free tier limits

---

## Troubleshooting Guide

### Issue 1: "Permission denied" when querying billing data
**Cause**: Service account lacks billing.viewer role
**Solution**:
```bash
gcloud projects add-iam-policy-binding ytgrs-464303 \
  --member="serviceAccount:cost-reporter@ytgrs-464303.iam.gserviceaccount.com" \
  --role="roles/billing.viewer"
```

### Issue 2: "Notification channel not found"
**Cause**: Wrong channel ID or missing monitoring.viewer permission
**Solution**:
```bash
# Verify channel exists
gcloud alpha monitoring channels describe projects/ytgrs-464303/notificationChannels/10908127531765369450

# Grant permission
gcloud projects add-iam-policy-binding ytgrs-464303 \
  --member="serviceAccount:cost-reporter@ytgrs-464303.iam.gserviceaccount.com" \
  --role="roles/monitoring.viewer"
```

### Issue 3: "No billing data available"
**Cause**: Billing data is delayed 1-2 days
**Solution**: This is normal. Adjust query to look 2 days back instead of yesterday.

### Issue 4: Function times out
**Cause**: Billing API query takes too long
**Solution**: Increase timeout:
```bash
gcloud functions deploy daily-cost-reporter \
  --timeout=120s \
  --region=us-central1
```

### Issue 5: Slack message not received
**Cause**: Wrong webhook URL or network issue
**Solution**: Check logs:
```bash
gcloud functions logs read daily-cost-reporter --region=us-central1 --limit=50
```

---

## Maintenance

### Update Schedule
```bash
# Change to 8 AM JST
gcloud scheduler jobs update http daily-cost-report \
  --location=us-central1 \
  --schedule="0 8 * * *"
```

### Pause/Resume
```bash
# Pause
gcloud scheduler jobs pause daily-cost-report --location=us-central1

# Resume
gcloud scheduler jobs resume daily-cost-report --location=us-central1
```

### Update Function
```bash
cd scripts/gcp/cost-reporter
./deploy.sh
```

### Delete Everything
```bash
# Delete scheduler
gcloud scheduler jobs delete daily-cost-report --location=us-central1

# Delete function
gcloud functions delete daily-cost-reporter --region=us-central1

# Delete service account
gcloud iam service-accounts delete cost-reporter@ytgrs-464303.iam.gserviceaccount.com
```

---

## Future Enhancements

### Optional Features to Add Later

1. **Cost Threshold Alerts**
   - Send warning if daily cost > average by 50%
   - Example: "⚠️ Yesterday's cost was 50% higher than your 7-day average!"

2. **Weekly Summary**
   - Every Monday, send weekly comparison
   - Show trending services

3. **Budget Warnings**
   - Alert when approaching monthly budget
   - Show percentage of budget used

4. **Historical Charts**
   - Generate cost trend charts
   - Upload to Slack as images

5. **Cost Optimization Tips**
   - Suggest idle resources to delete
   - Recommend cheaper alternatives

---

## Security Checklist

Before deploying, verify:

- [ ] Service account has minimal permissions (only billing.viewer + monitoring.viewer)
- [ ] Function requires authentication (--no-allow-unauthenticated)
- [ ] Scheduler uses OIDC authentication
- [ ] No secrets hardcoded in code
- [ ] Webhook URL read dynamically from monitoring channel
- [ ] Audit logging enabled
- [ ] Function timeout set appropriately
- [ ] Error handling implemented

---

## Next Steps

### When You Get Billing Access:

1. **Verify access**:
   ```bash
   gcloud billing accounts describe 011275-97802D-6B812D
   ```

2. **Resume implementation**:
   - Start from Phase 1, Step 1.1
   - Follow this document step by step
   - Test thoroughly before scheduling

3. **Contact me if you need help**:
   - Reference this document
   - Mention which step you're on
   - Include any error messages

---

## References

- [Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
- [Cloud Billing API](https://cloud.google.com/billing/docs/reference/rest)
- [Slack Block Kit](https://api.slack.com/block-kit)
- [GCP Monitoring Notification Channels](https://cloud.google.com/monitoring/support/notification-options)

---

**Document Version**: 1.0
**Last Updated**: October 13, 2025
**Status**: Ready to implement once billing access is granted
