#!/bin/bash
set -euo pipefail

# Script to help set up a new GCP project for AI Resume Review Platform

echo "AI Resume Review Platform - GCP Project Setup"
echo "============================================"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed. Please install it first."
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get current authentication info
echo "Current gcloud configuration:"
gcloud config list

# Function to create project
create_project() {
    local PROJECT_ID=$1
    local PROJECT_NAME=$2
    local BILLING_ACCOUNT=$3
    
    echo "Creating project: $PROJECT_ID"
    
    # Create the project
    gcloud projects create $PROJECT_ID --name="$PROJECT_NAME" || {
        echo "Project might already exist, continuing..."
    }
    
    # Link billing account
    echo "Linking billing account..."
    gcloud beta billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT
    
    # Set as current project
    gcloud config set project $PROJECT_ID
}

# Main setup flow
echo ""
echo "Choose environment to set up:"
echo "1) Development"
echo "2) Staging"
echo "3) Production"
read -p "Enter choice (1-3): " ENV_CHOICE

case $ENV_CHOICE in
    1)
        ENV="dev"
        DEFAULT_PROJECT_ID="ai-resume-review-dev"
        ;;
    2)
        ENV="staging"
        DEFAULT_PROJECT_ID="ai-resume-review-staging"
        ;;
    3)
        ENV="prod"
        DEFAULT_PROJECT_ID="ai-resume-review-prod"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

# Get project details
read -p "Enter project ID (default: $DEFAULT_PROJECT_ID): " PROJECT_ID
PROJECT_ID=${PROJECT_ID:-$DEFAULT_PROJECT_ID}

read -p "Enter project name (default: AI Resume Review - $ENV): " PROJECT_NAME
PROJECT_NAME=${PROJECT_NAME:-"AI Resume Review - $ENV"}

# List available billing accounts
echo ""
echo "Available billing accounts:"
gcloud beta billing accounts list

read -p "Enter billing account ID: " BILLING_ACCOUNT

# Confirm
echo ""
echo "Summary:"
echo "- Environment: $ENV"
echo "- Project ID: $PROJECT_ID"
echo "- Project Name: $PROJECT_NAME"
echo "- Billing Account: $BILLING_ACCOUNT"
echo ""
read -p "Proceed with setup? (y/n): " CONFIRM

if [[ $CONFIRM != "y" ]]; then
    echo "Setup cancelled"
    exit 0
fi

# Create the project
create_project "$PROJECT_ID" "$PROJECT_NAME" "$BILLING_ACCOUNT"

# Create terraform state bucket
echo ""
echo "Creating Terraform state bucket..."
BUCKET_NAME="${PROJECT_ID}-terraform-state"
gsutil mb -p $PROJECT_ID -c STANDARD -l US-CENTRAL1 gs://$BUCKET_NAME/ || {
    echo "Bucket might already exist, continuing..."
}

# Enable versioning on the bucket
gsutil versioning set on gs://$BUCKET_NAME/

# Create backend config file
BACKEND_CONFIG="infrastructure/terraform/backend-configs/${ENV}.hcl"
mkdir -p infrastructure/terraform/backend-configs
cat > $BACKEND_CONFIG <<EOF
bucket = "$BUCKET_NAME"
prefix = "terraform/state/${ENV}"
EOF

echo "Backend configuration written to: $BACKEND_CONFIG"

# Update terraform variables file
TFVARS_FILE="infrastructure/terraform/environments/${ENV}.tfvars"
echo ""
echo "Updating $TFVARS_FILE with project ID..."
sed -i.bak "s/project_id.*=.*/project_id = \"$PROJECT_ID\"/" $TFVARS_FILE
sed -i.bak "s/billing_account_id.*=.*/billing_account_id = \"$BILLING_ACCOUNT\"/" $TFVARS_FILE

echo ""
echo "Setup complete! Next steps:"
echo "1. Update team member emails in $TFVARS_FILE"
echo "2. Run terraform init with: terraform init -backend-config=backend-configs/${ENV}.hcl"
echo "3. Run terraform plan with: terraform plan -var-file=environments/${ENV}.tfvars"
echo "4. Run terraform apply with: terraform apply -var-file=environments/${ENV}.tfvars"