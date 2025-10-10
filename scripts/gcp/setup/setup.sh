#!/bin/bash
# setup.sh - GCP Infrastructure Complete Setup
#
# Usage: ./setup.sh [options]
# Options:
#   --step=<step>    Run specific step only (project, database, secrets, all)
#   --dry-run        Show what would be executed
#   --help           Show this help message
#
# Examples:
#   ./setup.sh                       # Run all steps
#   ./setup.sh --step=project        # GCP project setup only
#   ./setup.sh --step=database       # Cloud SQL setup only
#   ./setup.sh --step=secrets        # Secrets setup only
#   ./setup.sh --dry-run             # Preview all steps
#
# What it does:
#   1. GCP Project Setup (Service Accounts, IAM, VPC, Artifact Registry)
#   2. Cloud SQL Setup (PostgreSQL instance, database, VPC peering)
#   3. Secrets Setup (OpenAI API key, JWT secret, DB password)
#
# Total time: ~15-20 minutes (Cloud SQL creation takes 5-10 minutes)
# Cost: ~$45-65/month after setup

set -e

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
source "$SCRIPT_DIR/../utils/common-functions.sh"

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN=false
STEP=""

# Resource naming (v2 convention)
BACKEND_SA="arr-v2-backend-prod"
FRONTEND_SA="arr-v2-frontend-prod"
GITHUB_SA="arr-v2-github-actions"
ARTIFACT_REPO="ai-resume-review-v2"
VPC_NETWORK="ai-resume-review-v2-vpc"
VPC_SUBNET="ai-resume-review-v2-subnet"
VPC_SUBNET_CIDR="10.0.0.0/24"

# Cloud SQL configuration
INSTANCE_NAME="ai-resume-review-v2-db-prod"
DATABASE_VERSION="POSTGRES_15"
TIER="db-f1-micro"
STORAGE_SIZE="10"  # GB
DATABASE_NAME="ai_resume_review_prod"
BACKUP_START_TIME="02:00"
BACKUP_RETENTION_DAYS="7"

# Secret names
SECRETS=(
    "openai-api-key-prod"
    "jwt-secret-key-prod"
    "db-password-prod"
)

# ============================================================================
# Helper Functions
# ============================================================================

show_help() {
    grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //' | sed 's/^#//'
}

dry_run() {
    local command="$1"
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would execute: $command"
        return 0
    else
        eval "$command"
        return $?
    fi
}

generate_password() {
    openssl rand -base64 24 | tr -d "=+/" | cut -c1-24
}

generate_jwt_secret() {
    openssl rand -hex 32
}

# ============================================================================
# Step 1: GCP Project Setup
# ============================================================================

step_project_setup() {
    log_section "Step 1/3: GCP Project Setup"

    # 1.1: Service Accounts
    log_info "Creating service accounts..."

    local service_accounts=(
        "$BACKEND_SA:Backend service account for Cloud Run"
        "$FRONTEND_SA:Frontend service account for Cloud Run"
        "$GITHUB_SA:GitHub Actions deployment service account"
    )

    for sa_config in "${service_accounts[@]}"; do
        local sa_name=$(echo "$sa_config" | cut -d: -f1)
        local sa_description=$(echo "$sa_config" | cut -d: -f2)
        local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"

        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create service account: $sa_email"
        else
            if gcloud iam service-accounts describe "$sa_email" --project="$PROJECT_ID" &>/dev/null; then
                log_warning "Service account already exists: $sa_name"
            else
                gcloud iam service-accounts create "$sa_name" \
                    --display-name="$sa_description" \
                    --project="$PROJECT_ID" \
                    --quiet
                log_success "Created service account: $sa_name"
            fi
        fi
    done

    # 1.2: IAM Role Assignments
    log_info "Assigning IAM roles..."

    # Backend roles
    local backend_roles=(
        "roles/cloudsql.client"
        "roles/secretmanager.secretAccessor"
        "roles/logging.logWriter"
    )

    for role in "${backend_roles[@]}"; do
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would assign $role to $BACKEND_SA"
        else
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
                --role="$role" \
                --quiet &>/dev/null
            log_success "Assigned $role to $BACKEND_SA"
        fi
    done

    # Frontend roles
    local frontend_roles=("roles/logging.logWriter")

    for role in "${frontend_roles[@]}"; do
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would assign $role to $FRONTEND_SA"
        else
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:${FRONTEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
                --role="$role" \
                --quiet &>/dev/null
            log_success "Assigned $role to $FRONTEND_SA"
        fi
    done

    # GitHub Actions roles
    local github_roles=(
        "roles/run.admin"
        "roles/iam.serviceAccountUser"
        "roles/artifactregistry.writer"
        "roles/cloudbuild.builds.editor"
    )

    for role in "${github_roles[@]}"; do
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would assign $role to $GITHUB_SA"
        else
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:${GITHUB_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
                --role="$role" \
                --quiet &>/dev/null
            log_success "Assigned $role to $GITHUB_SA"
        fi
    done

    # 1.3: Artifact Registry
    log_info "Creating Artifact Registry..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would create Artifact Registry: $ARTIFACT_REPO in $REGION"
    else
        if gcloud artifacts repositories describe "$ARTIFACT_REPO" \
            --location="$REGION" \
            --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Artifact Registry already exists: $ARTIFACT_REPO"
        else
            gcloud artifacts repositories create "$ARTIFACT_REPO" \
                --repository-format=docker \
                --location="$REGION" \
                --description="Docker images for AI Resume Review v2 platform" \
                --project="$PROJECT_ID" \
                --quiet
            log_success "Created Artifact Registry: $ARTIFACT_REPO"
        fi
    fi

    # 1.4: VPC Network
    log_info "Creating VPC network..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would create VPC: $VPC_NETWORK"
        log_info "[DRY-RUN] Would create subnet: $VPC_SUBNET ($VPC_SUBNET_CIDR)"
    else
        # Create VPC
        if gcloud compute networks describe "$VPC_NETWORK" --project="$PROJECT_ID" &>/dev/null; then
            log_warning "VPC network already exists: $VPC_NETWORK"
        else
            gcloud compute networks create "$VPC_NETWORK" \
                --subnet-mode=custom \
                --project="$PROJECT_ID" \
                --quiet
            log_success "Created VPC network: $VPC_NETWORK"
        fi

        # Create subnet
        if gcloud compute networks subnets describe "$VPC_SUBNET" \
            --region="$REGION" \
            --project="$PROJECT_ID" &>/dev/null; then
            log_warning "VPC subnet already exists: $VPC_SUBNET"
        else
            gcloud compute networks subnets create "$VPC_SUBNET" \
                --network="$VPC_NETWORK" \
                --region="$REGION" \
                --range="$VPC_SUBNET_CIDR" \
                --project="$PROJECT_ID" \
                --quiet
            log_success "Created VPC subnet: $VPC_SUBNET"
        fi
    fi

    log_success "GCP project setup complete"
}

# ============================================================================
# Step 2: Cloud SQL Setup
# ============================================================================

step_database_setup() {
    log_section "Step 2/3: Cloud SQL Database Setup"

    # 2.1: Check VPC exists
    if [ "$DRY_RUN" = false ]; then
        if ! gcloud compute networks describe "$VPC_NETWORK" --project="$PROJECT_ID" &>/dev/null; then
            die "VPC network not found: $VPC_NETWORK. Run --step=project first."
        fi
    fi

    # 2.2: Enable Service Networking API
    if [ "$DRY_RUN" = false ]; then
        if ! gcloud services list --enabled --filter="name:servicenetworking.googleapis.com" \
            --format="value(name)" | grep -q "servicenetworking"; then
            log_info "Enabling Service Networking API..."
            gcloud services enable servicenetworking.googleapis.com --project="$PROJECT_ID"
            log_success "Service Networking API enabled"
        fi
    fi

    # 2.3: VPC Peering Setup
    log_info "Setting up VPC peering for Cloud SQL..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would allocate IP range for private services"
        log_info "[DRY-RUN] Would create VPC peering connection"
    else
        # Check if IP range already allocated
        local existing_range=$(gcloud compute addresses list \
            --global \
            --filter="purpose:VPC_PEERING AND network:$VPC_NETWORK" \
            --format="value(name)" \
            --project="$PROJECT_ID" 2>/dev/null | head -1)

        if [ -n "$existing_range" ]; then
            log_warning "IP range already allocated: $existing_range"
        else
            gcloud compute addresses create google-managed-services-$VPC_NETWORK \
                --global \
                --purpose=VPC_PEERING \
                --prefix-length=16 \
                --network=$VPC_NETWORK \
                --project="$PROJECT_ID" \
                --quiet
            log_success "Allocated IP range for private services"
        fi

        # Create VPC peering
        if gcloud services vpc-peerings list \
            --network=$VPC_NETWORK \
            --project="$PROJECT_ID" 2>/dev/null | grep -q "servicenetworking"; then
            log_warning "VPC peering already exists"
        else
            gcloud services vpc-peerings connect \
                --service=servicenetworking.googleapis.com \
                --ranges=google-managed-services-$VPC_NETWORK \
                --network=$VPC_NETWORK \
                --project="$PROJECT_ID" \
                --quiet
            log_success "VPC peering connection created"
        fi
    fi

    # 2.4: Create Cloud SQL Instance
    log_info "Creating Cloud SQL instance (this takes 5-10 minutes)..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would create Cloud SQL instance:"
        log_info "  Name: $INSTANCE_NAME"
        log_info "  Version: $DATABASE_VERSION"
        log_info "  Tier: $TIER"
        log_info "  Storage: ${STORAGE_SIZE}GB SSD"
        log_info "  Private IP only (no public IP)"
    else
        if gcloud sql instances describe "$INSTANCE_NAME" --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Cloud SQL instance already exists: $INSTANCE_NAME"
        else
            gcloud sql instances create "$INSTANCE_NAME" \
                --database-version="$DATABASE_VERSION" \
                --tier="$TIER" \
                --region="$REGION" \
                --network="projects/$PROJECT_ID/global/networks/$VPC_NETWORK" \
                --no-assign-ip \
                --storage-type=SSD \
                --storage-size="${STORAGE_SIZE}GB" \
                --storage-auto-increase \
                --backup \
                --backup-start-time="$BACKUP_START_TIME" \
                --retained-backups-count="$BACKUP_RETENTION_DAYS" \
                --maintenance-window-day=SUN \
                --maintenance-window-hour=2 \
                --maintenance-release-channel=production \
                --deletion-protection \
                --project="$PROJECT_ID" \
                --quiet

            log_success "Cloud SQL instance created: $INSTANCE_NAME"
        fi
    fi

    # 2.5: Create Database
    log_info "Creating database..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would create database: $DATABASE_NAME"
    else
        if gcloud sql databases describe "$DATABASE_NAME" \
            --instance="$INSTANCE_NAME" \
            --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Database already exists: $DATABASE_NAME"
        else
            gcloud sql databases create "$DATABASE_NAME" \
                --instance="$INSTANCE_NAME" \
                --project="$PROJECT_ID" \
                --quiet
            log_success "Database created: $DATABASE_NAME"
        fi
    fi

    # 2.6: Set Database Password
    log_info "Setting database password..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would generate and set postgres password"
        log_info "[DRY-RUN] Password would be saved to: /tmp/db-password-prod.txt"
    else
        DB_PASSWORD=$(generate_password)

        gcloud sql users set-password postgres \
            --instance="$INSTANCE_NAME" \
            --password="$DB_PASSWORD" \
            --project="$PROJECT_ID" \
            --quiet

        # Save password for secrets setup
        echo "$DB_PASSWORD" > /tmp/db-password-prod.txt
        chmod 600 /tmp/db-password-prod.txt

        log_success "Password set and saved to: /tmp/db-password-prod.txt"
    fi

    log_success "Cloud SQL setup complete"
}

# ============================================================================
# Step 3: Secrets Setup
# ============================================================================

step_secrets_setup() {
    log_section "Step 3/3: Secrets Setup"

    # 3.1: Check prerequisites
    if [ "$DRY_RUN" = false ]; then
        local backend_sa_email="${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
        if ! gcloud iam service-accounts describe "$backend_sa_email" --project="$PROJECT_ID" &>/dev/null; then
            die "Backend service account not found. Run --step=project first."
        fi
    fi

    # 3.2: Create Secrets
    log_info "Creating secrets in Secret Manager..."

    for secret_name in "${SECRETS[@]}"; do
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create secret: $secret_name"
            continue
        fi

        # Check if secret exists
        if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Secret already exists: $secret_name"

            if ! confirm "Update existing secret $secret_name?" "n"; then
                log_info "Skipped: $secret_name"
                continue
            fi
        else
            gcloud secrets create "$secret_name" \
                --replication-policy="automatic" \
                --project="$PROJECT_ID" \
                --quiet
            log_success "Created secret: $secret_name"
        fi

        # Get secret value
        local secret_value=""

        case "$secret_name" in
            "db-password-prod")
                if [ -f "/tmp/db-password-prod.txt" ]; then
                    secret_value=$(cat /tmp/db-password-prod.txt)
                    log_info "Using database password from /tmp/db-password-prod.txt"
                else
                    echo ""
                    log_warning "Enter database password (hidden):"
                    read -s secret_value
                    echo ""
                fi
                ;;

            "jwt-secret-key-prod")
                secret_value=$(generate_jwt_secret)
                log_info "Generated JWT secret (256-bit)"
                ;;

            "openai-api-key-prod")
                echo ""
                log_warning "Enter OpenAI API key (starts with sk-):"
                read -s secret_value
                echo ""

                if [[ ! "$secret_value" =~ ^sk- ]]; then
                    log_error "Invalid OpenAI API key format (should start with 'sk-')"
                    continue
                fi
                ;;
        esac

        # Add secret version
        if [ -n "$secret_value" ]; then
            echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
                --data-file=- \
                --project="$PROJECT_ID" \
                --quiet
            log_success "Added value to secret: $secret_name"
        fi
    done

    # 3.3: Grant IAM Permissions
    log_info "Granting IAM permissions to backend service account..."

    local backend_sa_email="${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

    for secret_name in "${SECRETS[@]}"; do
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would grant access to: $secret_name"
            continue
        fi

        if ! gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Secret not found, skipping: $secret_name"
            continue
        fi

        gcloud secrets add-iam-policy-binding "$secret_name" \
            --member="serviceAccount:$backend_sa_email" \
            --role="roles/secretmanager.secretAccessor" \
            --project="$PROJECT_ID" \
            --quiet &>/dev/null

        log_success "Granted access to: $secret_name"
    done

    # 3.4: Cleanup temp files
    if [ "$DRY_RUN" = false ] && [ -f "/tmp/db-password-prod.txt" ]; then
        log_info "Cleaning up temporary password file..."
        rm -f /tmp/db-password-prod.txt
        log_success "Deleted: /tmp/db-password-prod.txt"
    fi

    log_success "Secrets setup complete"
}

# ============================================================================
# Main Function
# ============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --step=*)
                STEP="${1#*=}"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    log_section "GCP Infrastructure Setup"

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY-RUN MODE - No changes will be made"
    fi

    # Run initialization checks
    init_checks || die "Environment checks failed"

    # Execute requested step or all steps
    if [ -n "$STEP" ]; then
        case "$STEP" in
            project)
                step_project_setup
                ;;
            database)
                step_database_setup
                ;;
            secrets)
                step_secrets_setup
                ;;
            all)
                step_project_setup || die "Project setup failed"
                echo ""
                step_database_setup || die "Database setup failed"
                echo ""
                step_secrets_setup || die "Secrets setup failed"
                ;;
            *)
                log_error "Unknown step: $STEP"
                log_info "Valid steps: project, database, secrets, all"
                exit 1
                ;;
        esac
    else
        # Run all steps
        if [ "$DRY_RUN" = false ]; then
            if ! confirm "This will set up complete GCP infrastructure. Continue?" "y"; then
                log_info "Setup cancelled"
                exit 0
            fi
        fi

        step_project_setup || die "Project setup failed"
        echo ""
        step_database_setup || die "Database setup failed"
        echo ""
        step_secrets_setup || die "Secrets setup failed"
        echo ""

        # Final summary
        log_section "Infrastructure Setup Complete!"

        log_success "✓ All infrastructure components created!"
        echo ""
        log_info "Created resources:"
        log_info "  Service Accounts:"
        log_info "    - ${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
        log_info "    - ${FRONTEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
        log_info "    - ${GITHUB_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
        echo ""
        log_info "  Infrastructure:"
        log_info "    - Artifact Registry: $ARTIFACT_REPO"
        log_info "    - VPC Network: $VPC_NETWORK"
        log_info "    - Cloud SQL: $INSTANCE_NAME (POSTGRES_15, $TIER)"
        log_info "    - Database: $DATABASE_NAME"
        echo ""
        log_info "  Secrets:"
        log_info "    - openai-api-key-prod"
        log_info "    - jwt-secret-key-prod"
        log_info "    - db-password-prod"
        echo ""
        log_info "Next steps:"
        log_info "  1. Run database migrations: scripts/gcp/deploy/deploy.sh --step=migrate"
        log_info "  2. Deploy application: scripts/gcp/deploy/deploy.sh"
        log_info "  3. Set up monitoring: scripts/gcp/monitoring/setup.sh"
        echo ""
    fi
}

# Run main function
main "$@"
