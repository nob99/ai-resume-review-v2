#!/bin/bash
# ============================================================================
# Secret Manager Setup Script
# ============================================================================
#
# PURPOSE:
#   Create and populate secrets in Google Secret Manager for both staging
#   and production environments.
#
# USAGE:
#   ./scripts/gcp/setup-secrets.sh [staging|production|both]
#
# WHAT THIS SCRIPT DOES:
#   1. Create secrets in Secret Manager:
#      Staging:
#        - openai-api-key-staging
#        - db-password-staging
#        - jwt-secret-key-staging
#
#      Production:
#        - openai-api-key-prod
#        - db-password-prod
#        - jwt-secret-key-prod
#
#   2. Prompt user to enter secret values securely
#   3. Store secret values in Secret Manager
#   4. Set up IAM permissions:
#      - Backend service account: secretAccessor role
#   5. Enable secret versioning
#   6. Display access instructions
#
# PREREQUISITES:
#   - GCP project set up
#   - Secret Manager API enabled
#   - Service accounts created
#
# SECRETS TO BE CREATED:
#   1. openai-api-key:
#      - Purpose: OpenAI GPT-4 API access
#      - Format: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#      - Access: Backend Cloud Run only
#
#   2. db-password:
#      - Purpose: PostgreSQL database password
#      - Format: Strong password (min 16 chars)
#      - Access: Backend Cloud Run only
#
#   3. jwt-secret-key:
#      - Purpose: JWT token signing
#      - Format: 256-bit random string
#      - Access: Backend Cloud Run only
#
# SECURITY FEATURES:
#   - Secrets never logged or displayed
#   - Input hidden during entry (using read -s)
#   - IAM-based access control
#   - Automatic encryption at rest
#   - Audit logging enabled
#   - Secret versioning (can rollback)
#
# DESIGN PRINCIPLES:
#   - Secure by default: No secrets in code or environment variables
#   - Least privilege: Only backend service account has access
#   - Audit trail: All secret access is logged
#   - Rotation ready: Support for secret rotation
#
# SECRET ACCESS PATTERN (in backend code):
#   ```python
#   from google.cloud import secretmanager
#
#   def get_secret(secret_name):
#       client = secretmanager.SecretManagerServiceClient()
#       name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
#       response = client.access_secret_version(request={"name": name})
#       return response.payload.data.decode("UTF-8")
#   ```
#
# OUTPUTS:
#   - Secret resource names
#   - IAM permissions set
#   - Access instructions for backend
#
# NEXT STEPS:
#   1. Update backend config.py to read from Secret Manager
#   2. Test secret access from Cloud Run
#   3. Document secret rotation procedure
#
# ============================================================================

# TODO: Implement script logic here
