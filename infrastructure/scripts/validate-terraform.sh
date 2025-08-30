#!/bin/bash
set -euo pipefail

# Script to validate Terraform configuration

echo "Terraform Configuration Validation"
echo "================================="

cd terraform

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "❌ Error: Terraform is not installed"
    echo "Please install Terraform: https://www.terraform.io/downloads"
    exit 1
fi

echo "Terraform version:"
terraform version
echo ""

# Format check
echo "1. Checking Terraform formatting..."
if terraform fmt -check -recursive .; then
    echo "✅ All files properly formatted"
else
    echo "❌ Some files need formatting"
    echo "Run 'terraform fmt -recursive .' to fix"
    exit 1
fi

# Validate configuration
echo ""
echo "2. Validating Terraform configuration..."
if terraform validate; then
    echo "✅ Configuration is valid"
else
    echo "❌ Configuration validation failed"
    exit 1
fi

# Check for required variables
echo ""
echo "3. Checking required variables in dev.tfvars..."
REQUIRED_VARS=(
    "project_id"
    "region"
    "environment"
    "budget_alert_email"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}" environments/dev.tfvars; then
        MISSING_VARS+=($var)
    fi
done

if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    echo "✅ All required variables present"
else
    echo "❌ Missing required variables:"
    printf '%s\n' "${MISSING_VARS[@]}"
fi

# Check for placeholder values
echo ""
echo "4. Checking for placeholder values..."
PLACEHOLDERS=(
    "XXXXX-XXXXX-XXXXX"
    "team@example.com"
    "Replace with"
)

FOUND_PLACEHOLDERS=false
for placeholder in "${PLACEHOLDERS[@]}"; do
    if grep -q "$placeholder" environments/dev.tfvars; then
        echo "⚠️  Found placeholder: $placeholder"
        FOUND_PLACEHOLDERS=true
    fi
done

if [ "$FOUND_PLACEHOLDERS" = false ]; then
    echo "✅ No placeholder values found"
fi

# Check module structure
echo ""
echo "5. Checking module structure..."
if [ -d "modules/iam" ]; then
    echo "✅ IAM module exists"
else
    echo "❌ IAM module missing"
fi

# Summary
echo ""
echo "================================="
echo "Validation Summary:"
echo "================================="

# Count issues
ISSUES=0
[ ${#MISSING_VARS[@]} -gt 0 ] && ISSUES=$((ISSUES + ${#MISSING_VARS[@]}))
[ "$FOUND_PLACEHOLDERS" = true ] && ISSUES=$((ISSUES + 1))

if [ $ISSUES -eq 0 ]; then
    echo "✅ All checks passed! Configuration is ready."
    echo ""
    echo "Next steps:"
    echo "1. Run the setup script: ./scripts/setup-existing-project.sh --dry-run"
    echo "2. Initialize Terraform: terraform init -backend-config=backend-configs/dev.hcl"
    echo "3. Plan changes: terraform plan -var-file=environments/dev.tfvars"
else
    echo "⚠️  Found $ISSUES issue(s) that need attention"
    echo ""
    echo "Please fix the issues above before proceeding."
fi