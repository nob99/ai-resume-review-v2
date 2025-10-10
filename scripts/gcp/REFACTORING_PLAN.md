# GCP Scripts Refactoring Plan

**Goal:** Streamline redundant code while keeping current architecture intact

**Strategy:** Low-risk refactoring first, architecture changes later

**Testing:** Dry-run mode for all changes

---

## Phase 1: Code Audit Results

### Common Functions Usage Analysis

**File:** `scripts/gcp/utils/common-functions.sh` (312 lines)

#### Heavily Used Functions (Keep & Optimize)
- `log_*` functions: ~500 usages across all scripts ✅ KEEP
- `check_secret_exists`, `check_sql_instance_exists`, `check_vpc_connector_exists`: Used in verification ✅ KEEP
- `get_service_url`, `get_secret`: ~19 usages ✅ KEEP
- `configure_docker_auth`, `tag_docker_image`, `push_docker_image`: 6 usages ✅ KEEP
- `confirm`, `die`, `check_status`: Error handling ✅ KEEP
- `init_checks`: Entry point for scripts ✅ KEEP

#### Lightly Used Functions (Review)
- `check_gcloud`: 1 usage (but critical for validation)
- `check_docker`: 3 usages (deployment scripts)
- `build_docker_image`: Custom wrapper, might be over-engineered

#### Functions Status
✅ **All functions are actively used** - No dead code found
⚠️ **Potential simplification:** `build_docker_image` wrapper might be unnecessary

---

## Phase 2: Script Consolidation Plan

### 2.1 Monitoring Scripts (Priority 1: Lowest Risk)

**Current State:**
```
monitoring/
├── 1-setup-notification-channels.sh
├── 2-setup-uptime-checks.sh
├── 3-setup-critical-alerts.sh
├── 4-setup-log-metrics.sh
├── 5-setup-budget-alert.sh
├── run-all-setup.sh (orchestrates 1-5)
└── verify-setup.sh
```

**Refactored State:**
```
monitoring/
├── setup.sh (consolidates 1-5 + run-all-setup.sh logic)
└── verify.sh (renamed from verify-setup.sh)
```

**Implementation:**
- Create new `setup.sh` with all 5 steps as functions
- Add `--step=N` flag for granular control
- Add `--dry-run` flag for testing
- Keep color output and progress indicators
- Remove 6 files, create 1 unified file

**Risk:** ⚠️ LOW (one-time setup scripts)

---

### 2.2 Deployment Scripts (Priority 2: Medium Risk)

**Current State:**
```
deploy/
├── 1-verify-prerequisites.sh
├── 2-run-migrations.sh
├── 3-deploy-backend.sh
├── 4-deploy-frontend.sh
└── deploy-all.sh
```

**Refactored State:**
```
deploy/
└── deploy.sh (consolidates all 5 scripts)
```

**Implementation:**
```bash
# Usage examples:
./deploy.sh                    # Run all steps (same as deploy-all.sh)
./deploy.sh --step=verify      # Step 1: Verify prerequisites only
./deploy.sh --step=migrate     # Step 2: Run migrations only
./deploy.sh --step=backend     # Step 3: Deploy backend only
./deploy.sh --step=frontend    # Step 4: Deploy frontend only
./deploy.sh --dry-run          # Show what would be executed
./deploy.sh --step=backend --dry-run  # Dry-run backend deployment
```

**Features:**
- Each step as a separate function
- Shared state validation
- Continue-on-error options
- Dry-run mode for all steps
- Progress tracking

**Risk:** ⚠️ MEDIUM (affects active deployments)
**Mitigation:** Test thoroughly with --dry-run before using

---

### 2.3 Setup Scripts (Priority 3: Medium-High Risk)

**Current State:**
```
setup/
├── setup-gcp-project.sh
├── setup-cloud-sql.sh
├── setup-secrets.sh
└── cleanup-old-resources.sh
```

**Refactored State:**
```
setup/
├── setup.sh (consolidates first 3 scripts)
└── cleanup.sh (renamed, kept separate - dangerous operation)
```

**Implementation:**
```bash
# Usage examples:
./setup.sh                     # Run all setup steps
./setup.sh --step=project      # GCP project setup only
./setup.sh --step=database     # Cloud SQL setup only
./setup.sh --step=secrets      # Secrets setup only
./setup.sh --dry-run           # Show what would be created
```

**Risk:** ⚠️ MEDIUM-HIGH (creates infrastructure)
**Mitigation:**
- Dry-run mode mandatory first
- Idempotent operations (safe to re-run)
- Only run once per environment

---

### 2.4 Verify Scripts (Priority 4: Keep As-Is)

**Current State:**
```
verify/
├── health-check.sh
└── integration-test.sh
```

**Decision:** ✅ **KEEP AS-IS**
- Only 2 scripts
- Different purposes (quick vs comprehensive)
- Not worth consolidating

---

## Phase 3: Code Deduplication

### 3.1 Duplicate Patterns Found

#### Pattern 1: Script Header
**Duplicated in:** All 21 scripts

**Current:**
```bash
#!/bin/bash
# Script description...

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../utils/common-functions.sh"
```

**Action:** Create template, ensure consistency

#### Pattern 2: Docker Build Sequence
**Duplicated in:** `3-deploy-backend.sh`, `4-deploy-frontend.sh`

**Current:**
```bash
# Configure Docker authentication
configure_docker_auth

# Tag image
tag_docker_image "$LOCAL_IMAGE" "$REMOTE_IMAGE"

# Push image
push_docker_image "$REMOTE_IMAGE"
```

**Action:** Create `deploy_docker_image()` function in common-functions.sh

#### Pattern 3: Service Health Check
**Duplicated in:** Multiple deployment scripts

**Current:**
```bash
local max_retries=5
local retry=0

while [ $retry -lt $max_retries ]; do
    if curl -f -s "$url/health" > /dev/null 2>&1; then
        log_success "Health check passed!"
        return 0
    fi
    retry=$((retry + 1))
    sleep 10
done
```

**Action:** Create `wait_for_service_health()` function in common-functions.sh

---

## Phase 4: Script Structure Standardization

### 4.1 Standard Template

Every script should follow this structure:

```bash
#!/bin/bash
# script-name.sh - Brief description
#
# Usage: ./script-name.sh [options]
# Options:
#   --step=<step>    Run specific step only
#   --dry-run        Show what would be executed
#   --help           Show this help message
#
# Examples:
#   ./script-name.sh
#   ./script-name.sh --step=1 --dry-run

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

# ============================================================================
# Helper Functions
# ============================================================================

show_help() {
    # Extract usage from header comments
    grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //' | sed 's/^#//'
}

# ============================================================================
# Step Functions
# ============================================================================

step_1_do_something() {
    log_section "Step 1: Do Something"
    # ... logic here
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

    # Run initialization checks
    init_checks || die "Environment checks failed"

    # Execute requested step or all steps
    if [ -n "$STEP" ]; then
        "step_${STEP}_do_something"
    else
        step_1_do_something
        # ... other steps
    fi
}

# Run main function
main "$@"
```

---

## Phase 5: Enhanced Common Functions

### 5.1 New Functions to Add

```bash
# Deploy Docker image (consolidates repeated pattern)
deploy_docker_image() {
    local local_image=$1
    local remote_image=$2

    log_section "Deploying Docker Image"
    configure_docker_auth
    tag_docker_image "$local_image" "$remote_image"
    push_docker_image "$remote_image"
}

# Wait for service to be healthy
wait_for_service_health() {
    local service_url=$1
    local max_retries=${2:-5}
    local retry=0

    log_info "Waiting for service to be healthy..."

    while [ $retry -lt $max_retries ]; do
        log_info "Attempt $((retry + 1))/$max_retries..."

        if curl -f -s "$service_url/health" > /dev/null 2>&1; then
            log_success "Health check passed!"
            return 0
        fi

        retry=$((retry + 1))
        if [ $retry -lt $max_retries ]; then
            log_info "Retrying in 10 seconds..."
            sleep 10
        fi
    done

    log_error "Health check failed after $max_retries attempts"
    return 1
}

# Dry-run wrapper
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
```

### 5.2 Functions to Simplify

**build_docker_image:**
- Currently has complex eval logic
- Simplify to just call docker build directly
- Move complexity to calling code if needed

---

## Implementation Order

### Week 1: Low-Risk Changes
- [x] Day 1: Audit complete ✓
- [ ] Day 2: Consolidate monitoring scripts (7 → 2)
- [ ] Day 3: Add new common functions (deploy_docker_image, wait_for_service_health, dry_run)
- [ ] Day 4: Test monitoring refactor with --dry-run

### Week 2: Medium-Risk Changes
- [ ] Day 5: Consolidate deployment scripts (5 → 1)
- [ ] Day 6: Test deployment refactor with --dry-run
- [ ] Day 7: Consolidate setup scripts (4 → 2)
- [ ] Day 8: Test setup refactor with --dry-run

### Week 3: Cleanup & Documentation
- [ ] Day 9: Standardize all script structures
- [ ] Day 10: Update all README files
- [ ] Day 11: Update scripts/README.md
- [ ] Day 12: Final testing and validation

---

## Success Metrics

After refactoring:
- ✅ Script count: 21 → 8 (62% reduction)
- ✅ Lines of code: ~2000 → ~1200 (40% reduction)
- ✅ Duplicate code: 0 occurrences
- ✅ All scripts have --dry-run mode
- ✅ All scripts have --help
- ✅ All scripts follow standard template
- ✅ Zero functionality loss
- ✅ All tests pass

---

## Risk Mitigation

1. **Git Safety:**
   - Commit after each script refactor
   - Descriptive commit messages
   - Easy to rollback

2. **Dry-Run Testing:**
   - Every script must support --dry-run
   - Test dry-run before actual execution
   - Document dry-run output

3. **Incremental Approach:**
   - One script type at a time
   - Test before moving to next
   - Don't rush

4. **Documentation:**
   - Update docs alongside code
   - Include migration guide
   - Document breaking changes (if any)

---

## Next Steps

Ready to proceed with:
1. ✅ Task 1: Complete (Audit)
2. → Task 2: Consolidate monitoring scripts

Proceed? (yes/no)
