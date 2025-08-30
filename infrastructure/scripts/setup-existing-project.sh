#!/bin/bash
set -euo pipefail

# Script to configure an existing GCP project for AI Resume Review Platform

# Parse command line arguments
DRY_RUN=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --dry-run    Show what would be done without making changes"
            echo "  --verbose    Show detailed output"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "AI Resume Review Platform - Existing Project Setup"
echo "================================================"

if [ "$DRY_RUN" = true ]; then
    echo "🔍 DRY RUN MODE - No changes will be made"
    echo ""
fi

PROJECT_ID="ytgrs-464303"
ENV="dev"

# Helper function for dry run
execute_command() {
    local cmd="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = true ]; then
        echo "📋 Would execute: $description"
        if [ "$VERBOSE" = true ]; then
            echo "   Command: $cmd"
        fi
    else
        echo "✓ Executing: $description"
        if [ "$VERBOSE" = true ]; then
            echo "   Command: $cmd"
        fi
        eval "$cmd"
    fi
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed. Please install it first."
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set current project
echo "Setting current project to: $PROJECT_ID"
execute_command "gcloud config set project $PROJECT_ID" "Set active project"

# Check project exists and we have access
echo "Verifying project access..."
if [ "$DRY_RUN" = true ]; then
    echo "📋 Would verify: Project access for $PROJECT_ID"
else
    gcloud projects describe $PROJECT_ID > /dev/null 2>&1 || {
        echo "Error: Cannot access project $PROJECT_ID. Please check:"
        echo "1. The project ID is correct"
        echo "2. You have the necessary permissions"
        echo "3. You are authenticated with: gcloud auth login"
        exit 1
    }
    echo "✓ Project verified: $PROJECT_ID"
fi

# Enable required APIs
echo ""
echo "Enabling required APIs..."
APIS=(
    "compute.googleapis.com"
    "run.googleapis.com"
    "sqladmin.googleapis.com"
    "secretmanager.googleapis.com"
    "cloudresourcemanager.googleapis.com"
    "iam.googleapis.com"
    "logging.googleapis.com"
    "monitoring.googleapis.com"
    "artifactregistry.googleapis.com"
    "cloudbuild.googleapis.com"
)

for api in "${APIS[@]}"; do
    execute_command "gcloud services enable $api --project=$PROJECT_ID" "Enable $api"
done

if [ "$DRY_RUN" = false ]; then
    echo "✓ All APIs enabled"
fi

# Create terraform state bucket
echo ""
echo "Creating Terraform state bucket..."
BUCKET_NAME="${PROJECT_ID}-terraform-state"

# Check if bucket exists
if [ "$DRY_RUN" = true ]; then
    echo "📋 Would check: If bucket gs://$BUCKET_NAME exists"
    echo "📋 Would create: Storage bucket with versioning if it doesn't exist"
else
    if gsutil ls -b gs://$BUCKET_NAME &> /dev/null; then
        echo "✓ Terraform state bucket already exists: $BUCKET_NAME"
    else
        echo "Creating bucket: $BUCKET_NAME"
        gsutil mb -p $PROJECT_ID -c STANDARD -l US-CENTRAL1 gs://$BUCKET_NAME/
        
        # Enable versioning on the bucket
        gsutil versioning set on gs://$BUCKET_NAME/
        echo "✓ Bucket created with versioning enabled"
    fi
fi

# Create backend config file
BACKEND_CONFIG="infrastructure/terraform/backend-configs/${ENV}.hcl"
if [ "$DRY_RUN" = true ]; then
    echo "📋 Would create: Directory infrastructure/terraform/backend-configs"
    echo "📋 Would create: Backend config file $BACKEND_CONFIG with:"
    echo "   bucket = \"$BUCKET_NAME\""
    echo "   prefix = \"terraform/state/${ENV}\""
else
    mkdir -p infrastructure/terraform/backend-configs
    cat > $BACKEND_CONFIG <<EOF
bucket = "$BUCKET_NAME"
prefix = "terraform/state/${ENV}"
EOF
    echo "✓ Backend configuration written to: $BACKEND_CONFIG"
fi

# Get current user for default DevOps role
CURRENT_USER=$(gcloud config get-value account)
echo ""
echo "Current user: $CURRENT_USER"

# Update terraform variables with current user as DevOps engineer
echo ""
echo "Setting up default team configuration..."
if [ "$DRY_RUN" = true ]; then
    echo "📋 Would create: infrastructure/terraform/environments/${ENV}.auto.tfvars"
    echo "   with DevOps engineer set to: $CURRENT_USER"
else
    cat > terraform/environments/${ENV}.auto.tfvars <<EOF
# Auto-generated team configuration
# Update these with actual team member emails
frontend_developer_email = ""
backend_developer_email  = ""
ai_ml_engineer_email    = ""
devops_engineer_email   = "$CURRENT_USER"
qa_engineer_email       = ""
EOF
    echo "✓ Default team configuration created"
fi

# Check billing account
echo ""
echo "Checking billing configuration..."
if [ "$DRY_RUN" = true ]; then
    echo "📋 Would check: Billing account for project $PROJECT_ID"
    echo "📋 Would update: billing_account_id in dev.tfvars if found"
else
    BILLING_INFO=$(gcloud beta billing projects describe $PROJECT_ID --format="value(billingAccountName)" 2>/dev/null || true)
    if [[ -z "$BILLING_INFO" ]]; then
        echo "⚠️  WARNING: No billing account linked to project"
        echo "Available billing accounts:"
        gcloud beta billing accounts list
        echo ""
        echo "Please update billing_account_id in infrastructure/terraform/environments/dev.tfvars"
    else
        BILLING_ACCOUNT=$(echo $BILLING_INFO | sed 's/billingAccounts\///')
        echo "✓ Billing account found: $BILLING_ACCOUNT"
        # Update tfvars with billing account
        sed -i.bak "s/billing_account_id.*=.*/billing_account_id = \"$BILLING_ACCOUNT\"/" terraform/environments/dev.tfvars
    fi
fi

echo ""
echo "Setup complete! Next steps:"
echo "1. Review and update team member emails in:"
echo "   infrastructure/terraform/environments/${ENV}.auto.tfvars"
echo "2. Update budget alert email in:"
echo "   infrastructure/terraform/environments/${ENV}.tfvars"
echo "3. Initialize Terraform:"
echo "   cd infrastructure/terraform"
echo "   terraform init -backend-config=backend-configs/${ENV}.hcl"
echo "4. Review the plan:"
echo "   terraform plan -var-file=environments/${ENV}.tfvars"
echo "5. Apply infrastructure:"
echo "   terraform apply -var-file=environments/${ENV}.tfvars"