# Makefile for AI Resume Review Platform Infrastructure

.PHONY: help init-dev init-staging plan-dev plan-staging apply-dev apply-staging destroy-dev destroy-staging fmt validate

# Default environment
ENV ?= dev

help:
	@echo "Available commands:"
	@echo "  make setup          - Run GCP project setup script"
	@echo "  make init-dev       - Initialize Terraform for development"
	@echo "  make init-staging   - Initialize Terraform for staging"
	@echo "  make plan-dev       - Plan infrastructure changes for development"
	@echo "  make plan-staging   - Plan infrastructure changes for staging"
	@echo "  make apply-dev      - Apply infrastructure changes for development"
	@echo "  make apply-staging  - Apply infrastructure changes for staging"
	@echo "  make destroy-dev    - Destroy development infrastructure (CAREFUL!)"
	@echo "  make destroy-staging - Destroy staging infrastructure (CAREFUL!)"
	@echo "  make fmt            - Format Terraform files"
	@echo "  make validate       - Validate Terraform configuration"

setup:
	@./scripts/setup-gcp-project.sh

init-dev:
	@cd terraform && terraform init -backend-config=backend-configs/dev.hcl

init-staging:
	@cd terraform && terraform init -backend-config=backend-configs/staging.hcl

plan-dev:
	@cd terraform && terraform plan -var-file=environments/dev.tfvars -out=dev.tfplan

plan-staging:
	@cd terraform && terraform plan -var-file=environments/staging.tfvars -out=staging.tfplan

apply-dev:
	@cd terraform && terraform apply -var-file=environments/dev.tfvars -auto-approve

apply-staging:
	@cd terraform && terraform apply -var-file=environments/staging.tfvars -auto-approve

destroy-dev:
	@echo "WARNING: This will destroy all development infrastructure!"
	@echo "Press Ctrl+C to cancel, or Enter to continue."
	@read confirm
	@cd terraform && terraform destroy -var-file=environments/dev.tfvars

destroy-staging:
	@echo "WARNING: This will destroy all staging infrastructure!"
	@echo "Press Ctrl+C to cancel, or Enter to continue."
	@read confirm
	@cd terraform && terraform destroy -var-file=environments/staging.tfvars

fmt:
	@cd terraform && terraform fmt -recursive

validate:
	@cd terraform && terraform validate

# Additional utility commands
check-cost:
	@echo "Checking estimated monthly costs..."
	@cd terraform && terraform plan -var-file=environments/$(ENV).tfvars | grep -A 10 "monthly cost"

list-resources:
	@cd terraform && terraform state list

show-outputs:
	@cd terraform && terraform output