# Configuration Management

This document explains the centralized configuration system for the AI Resume Review backend.

## Quick Start

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your local values:**
   ```bash
   # Required: Set your database password
   DB_PASSWORD=your_local_db_password
   
   # Required: Set your OpenAI API key  
   OPENAI_API_KEY=your-openai-api-key
   
   # Optional: Change other settings as needed
   ```

3. **Start development:**
   ```bash
   # Start all services (database, Redis, backend)
   ./scripts/docker/dev.sh up

   # Run tests inside backend container
   ./scripts/docker/dev.sh shell backend
   pytest
   ```

## Configuration Structure

### Files
- `.env.example` - Template with all available settings and defaults
- `.env` - Your local configuration (not in version control)
- `app/core/config.py` - Centralized configuration module

### Configuration Classes
- `DatabaseConfig` - PostgreSQL connection settings
- `RedisConfig` - Redis connection settings  
- `SecurityConfig` - JWT and authentication settings
- `AppConfig` - General application settings

## Environment Variables

### Database
```bash
DB_HOST=localhost          # Database hostname
DB_PORT=5432              # Database port
DB_NAME=ai_resume_review_dev # Database name
DB_USER=postgres          # Database username
DB_PASSWORD=              # Database password (REQUIRED)
```

### Redis
```bash
REDIS_HOST=localhost      # Redis hostname
REDIS_PORT=6379          # Redis port
REDIS_PASSWORD=          # Redis password (optional)
```

### Security
```bash
SECRET_KEY=              # JWT signing key (change in production!)
ALGORITHM=HS256          # JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES=30   # Access token lifetime
REFRESH_TOKEN_EXPIRE_DAYS=7      # Refresh token lifetime
```

### Application
```bash
DEBUG=True               # Enable debug mode
LOG_LEVEL=INFO          # Logging level
ENVIRONMENT=development  # Environment name
```

## Usage in Code

### Import Configuration
```python
from app.core.config import get_database_url, security_config, app_config

# Get database URL
db_url = get_database_url()

# Access security settings
secret = security_config.SECRET_KEY
token_expiry = security_config.ACCESS_TOKEN_EXPIRE_MINUTES

# Check environment
if app_config.DEBUG:
    print("Debug mode enabled")
```

### Database Connection
```python
from app.core.config import get_database_url
from sqlalchemy import create_engine

# ✅ Correct - Uses centralized config
engine = create_engine(get_database_url())

# ❌ Wrong - Hardcoded credentials
engine = create_engine("postgresql://postgres:password@localhost/db")
```

## Testing

The configuration system automatically loads from `.env` files and provides consistent settings across:
- Unit tests
- Integration tests  
- Development server
- Production deployment

## Security Notes

1. **Never commit `.env` files** - they contain sensitive credentials
2. **Always use `.env.example`** as the template for new environments
3. **Change SECRET_KEY in production** - the default is only for development
4. **Use strong database passwords** - especially in shared development environments

## Team Coordination

- **Changing default settings**: Update `.env.example` and notify team in #dev-general
- **Local password changes**: Each developer can use their own database password
- **Adding new settings**: Add to `config.py` classes and document in this README

## Troubleshooting

### Common Issues

**"DB_PASSWORD must be set" error:**
- Copy `.env.example` to `.env` 
- Set your database password in `.env`

**Tests failing with database connection errors:**
- Ensure all services are running: `./scripts/docker/dev.sh status`
- Start services if needed: `./scripts/docker/dev.sh up`
- Check your `.env` file has correct database credentials
- Verify database is accessible: `./scripts/docker/dev.sh shell postgres`

**"Using default SECRET_KEY" warning:**
- Normal in development 
- Must be changed in production environments

### Validation

The configuration system validates critical settings on startup:
- Database password must be set
- Secret key must be changed in production
- Required environment variables are present

For support, ask in #dev-help or check the working agreements document.