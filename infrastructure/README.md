# AI Resume Review Platform - Infrastructure

This directory contains all infrastructure-as-code (IaC) configurations for the AI Resume Review Platform using Terraform and Google Cloud Platform (GCP).

## Prerequisites

1. **GCloud CLI**: Install the Google Cloud SDK
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Linux/Windows
   # Visit: https://cloud.google.com/sdk/docs/install
   ```

2. **Terraform**: Install Terraform 1.5+
   ```bash
   # macOS
   brew install terraform
   
   # Linux/Windows
   # Visit: https://www.terraform.io/downloads
   ```

3. **Authentication**: Authenticate with GCP
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

## Quick Start

### 1. Set Up GCP Project

#### Option A: Use Existing Project (Recommended for ytgrs-464303)

For the existing project `ytgrs-464303`, run:

```bash
cd infrastructure
./scripts/setup-existing-project.sh
```

This script will:
- Verify project access
- Enable required APIs
- Create Terraform state bucket
- Generate backend configuration
- Set up default team configuration

#### Option B: Create a New GCP Project

Run the setup script to create a new GCP project:

```bash
cd infrastructure
./scripts/setup-gcp-project.sh
```

This script will:
- Create a new GCP project
- Link billing account
- Create Terraform state bucket
- Generate backend configuration

### 2. Update Team Configuration

Edit the environment-specific variables file:

```bash
# For development environment
vi terraform/environments/dev.tfvars
```

Update the team member emails:
```hcl
frontend_developer_email = "frontend@example.com"
backend_developer_email  = "backend@example.com"
ai_ml_engineer_email    = "ai@example.com"
devops_engineer_email   = "devops@example.com"
qa_engineer_email       = "qa@example.com"
budget_alert_email      = "team@example.com"
```

### 3. Initialize Terraform

```bash
cd terraform
terraform init -backend-config=backend-configs/dev.hcl
```

### 4. Plan Infrastructure Changes

```bash
terraform plan -var-file=environments/dev.tfvars
```

### 5. Apply Infrastructure

```bash
terraform apply -var-file=environments/dev.tfvars
```

## Infrastructure Components

### Core Infrastructure (INFRA-001)
- **GCP Project**: Isolated project with proper naming
- **IAM Roles**: Role-based access for team members
- **Service Accounts**: Separate accounts for app and Cloud SQL
- **APIs Enabled**:
  - Cloud Run
  - Cloud SQL
  - Secret Manager
  - Artifact Registry
  - Cloud Build
  - Monitoring & Logging

### Security & Compliance
- **Budget Alerts**: Notifications at 50%, 80%, and 100% of budget
- **Logging**: Centralized logging with 30-day retention
- **Encryption**: Optional KMS encryption for storage
- **IAM**: Principle of least privilege access

### Environments
- **Development**: Lower resources, relaxed limits
- **Staging**: Production-like configuration
- **Production**: Full security and monitoring (future)

## Team Access Management

### Developer Access
- View project resources
- Access Cloud SQL databases
- Deploy to Cloud Run
- Read secrets
- View logs and metrics

### DevOps Access
- Full infrastructure management
- IAM administration
- Service account management
- Monitoring configuration

### QA Access
- View resources
- Invoke Cloud Run services
- View logs and metrics

## Terraform State Management

State is stored in GCS buckets with:
- Versioning enabled
- Backend encryption
- Access logging

State bucket naming: `{project-id}-terraform-state`

## Common Commands

### View current infrastructure
```bash
terraform show
```

### Destroy infrastructure (careful!)
```bash
terraform destroy -var-file=environments/dev.tfvars
```

### Import existing resources
```bash
terraform import google_project_service.compute {project-id}/compute.googleapis.com
```

## Troubleshooting

### Permission Denied Errors
Ensure your Google account has the following roles:
- `roles/resourcemanager.projectCreator`
- `roles/billing.user`
- `roles/serviceusage.serviceUsageAdmin`

### API Not Enabled Errors
The Terraform configuration automatically enables required APIs. If you encounter issues:
```bash
gcloud services enable {service-name}.googleapis.com
```

### State Lock Issues
If Terraform state is locked:
```bash
terraform force-unlock {lock-id}
```

## Cost Management

### Budget Alerts
- Development: $500/month
- Staging: $750/month
- Production: TBD

### Cost Optimization
- Use preemptible instances where possible
- Set up resource quotas
- Regular cost reviews

## Security Best Practices

1. **Never commit sensitive data**
   - Use Secret Manager for API keys
   - Use tfvars files for configuration
   - Add *.tfvars to .gitignore

2. **Regular Reviews**
   - Audit IAM permissions quarterly
   - Review service account keys
   - Check for unused resources

3. **Monitoring**
   - Enable audit logs
   - Set up alerts for suspicious activity
   - Regular security scans

## Next Steps

After infrastructure setup:
1. **INFRA-002**: Set up Cloud SQL database
2. **AUTH-004**: Implement password security
3. **AI-001**: Configure LangChain setup

## Support

For infrastructure issues:
1. Check Terraform plan output
2. Review GCP Console logs
3. Contact DevOps team lead

## References

- [GCP Terraform Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [IAM Best Practices](https://cloud.google.com/iam/docs/best-practices)