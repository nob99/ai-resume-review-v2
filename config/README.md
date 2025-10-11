# GCP Environment Configuration

This directory contains centralized configuration for all GCP environments.

## Files

- **`environments.yml`** - Single source of truth for all environment settings (staging, production)

## Quick Reference

### Finding Configuration Values

```bash
# Install yq if not already installed
brew install yq

# Get staging backend service name
yq '.staging.backend.name' config/environments.yml

# Get production database instance name
yq '.production.database.instance_name' config/environments.yml

# Get all staging configuration
yq '.staging' config/environments.yml

# Get global project ID
yq '.global.project_id' config/environments.yml
```

### Usage in Bash Scripts

```bash
# Load environment configuration
source scripts/lib/load-config.sh staging

# Access variables (automatically exported)
echo $BACKEND_SERVICE_NAME
echo $SQL_INSTANCE_NAME
echo $VPC_NAME
```

### Usage in Terraform

```hcl
# Load YAML configuration
locals {
  config = yamldecode(file("${path.module}/../../../config/environments.yml"))
  env    = local.config.staging
  global = local.config.global
}

# Use values
resource "google_sql_database_instance" "postgres" {
  name = local.env.database.instance_name
  # ...
}
```

### Usage in GitHub Actions

```yaml
# Read YAML in workflow
- name: Load Configuration
  run: |
    BACKEND_NAME=$(yq '.staging.backend.name' config/environments.yml)
    echo "BACKEND_NAME=$BACKEND_NAME" >> $GITHUB_ENV
```

## Configuration Structure

```yaml
environments.yml
├── global/           # Shared across all environments
│   ├── project_id
│   ├── region
│   └── artifact_registry
│
├── staging/          # Staging-specific settings
│   ├── backend/
│   ├── frontend/
│   ├── database/
│   ├── network/
│   ├── secrets/
│   └── monitoring/
│
└── production/       # Production-specific settings
    ├── backend/
    ├── frontend/
    ├── database/
    ├── network/
    ├── secrets/
    └── monitoring/
```

## Adding a New Environment

1. Copy the `staging:` section in `environments.yml`
2. Rename to your new environment (e.g., `development:`)
3. Update all values to match the new environment
4. Update service names, database names, secrets, etc.
5. Test configuration:
   ```bash
   yq '.development' config/environments.yml
   ```

## Important Notes

- **Secrets:** This file contains secret **names** only, not values
- **Version Control:** This file is committed to git
- **Sensitive Values:** Never commit actual passwords, API keys, or tokens
- **Changes:** Test changes in staging before applying to production
- **Validation:** Use `yq` to validate YAML syntax before committing

## See Also

- [Terraform README](../terraform/README.md) - Infrastructure as Code setup
- [Deployment Scripts](../scripts/gcp/README.md) - Bash deployment scripts
- [GitHub Actions Workflows](../.github/workflows/) - CI/CD pipelines
