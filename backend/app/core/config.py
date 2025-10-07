"""
Centralized configuration management for the AI Resume Review application.
Handles environment variables and provides secure defaults.
"""

import os
from typing import Optional
from pathlib import Path

try:
    from google.cloud import secretmanager
except ImportError:
    secretmanager = None  # Will be None in local dev if not installed yet

# Load environment variables from .env file if it exists
def load_env_file():
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent.parent.parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value

# Load .env file on import
load_env_file()


def get_secret_from_gcp(secret_name: str) -> Optional[str]:
    """
    Get secret from Google Secret Manager (production only).

    Args:
        secret_name: Name of the secret in Secret Manager

    Returns:
        Secret value or None if not in production/error
    """
    # Only use Secret Manager in production
    if os.getenv("ENVIRONMENT") != "production":
        return None

    # Check if Secret Manager client is available
    if secretmanager is None:
        print(f"Warning: google-cloud-secret-manager not installed, cannot fetch {secret_name}")
        return None

    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("PROJECT_ID", "ytgrs-464303")
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        # Log but don't crash - will fall back to env vars
        print(f"Warning: Could not fetch secret {secret_name} from Secret Manager: {e}")
        return None


class DatabaseConfig:
    """Database configuration settings."""
    
    HOST: str = os.getenv("DB_HOST", "localhost")
    PORT: int = int(os.getenv("DB_PORT", "5432"))
    NAME: str = os.getenv("DB_NAME", "ai_resume_review_dev")
    USER: str = os.getenv("DB_USER", "postgres")
    PASSWORD: str = (
        get_secret_from_gcp("db-password-prod")
        or os.getenv("DB_PASSWORD", "dev_password_123")
    )
    
    @classmethod
    def get_url(cls, database_name: Optional[str] = None) -> str:
        """
        Get database URL for SQLAlchemy.

        Args:
            database_name: Optional database name override

        Returns:
            PostgreSQL connection URL
        """
        db_name = database_name or cls.NAME

        # Check if using Cloud SQL Unix socket (starts with /cloudsql/)
        if cls.HOST.startswith("/cloudsql/"):
            # Unix socket format for Cloud SQL
            # Format: postgresql://user:password@/dbname?host=/cloudsql/instance
            return f"postgresql://{cls.USER}:{cls.PASSWORD}@/{db_name}?host={cls.HOST}"
        else:
            # Standard TCP connection (local development)
            return f"postgresql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{db_name}"
    
    @classmethod
    def get_async_url(cls, database_name: Optional[str] = None) -> str:
        """
        Get async database URL for SQLAlchemy async operations.

        Args:
            database_name: Optional database name override

        Returns:
            PostgreSQL async connection URL using asyncpg driver
        """
        db_name = database_name or cls.NAME

        # Check if using Cloud SQL Unix socket (starts with /cloudsql/)
        if cls.HOST.startswith("/cloudsql/"):
            # Unix socket format for Cloud SQL with asyncpg
            return f"postgresql+asyncpg://{cls.USER}:{cls.PASSWORD}@/{db_name}?host={cls.HOST}"
        else:
            # Standard TCP connection (local development)
            return f"postgresql+asyncpg://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{db_name}"


class RedisConfig:
    """Redis configuration settings."""
    
    HOST: str = os.getenv("REDIS_HOST", "localhost")
    PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD") or None
    
    @classmethod
    def get_url(cls) -> str:
        """
        Get Redis URL.
        
        Returns:
            Redis connection URL
        """
        if cls.PASSWORD:
            return f"redis://:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/0"
        return f"redis://{cls.HOST}:{cls.PORT}/0"


class SecurityConfig:
    """Security configuration settings."""

    SECRET_KEY: str = (
        get_secret_from_gcp("jwt-secret-key-prod")
        or os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    )
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class AppConfig:
    """Application configuration settings."""
    
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes", "on")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Resume Review Platform"
    
    # CORS Configuration
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1", "0.0.0.0"]
    
    # Testing Configuration
    TEST_DB_NAME: str = os.getenv("TEST_DB_NAME", "ai_resume_review_test")


class AIConfig:
    """AI and LLM configuration settings."""

    # OpenAI Configuration
    OPENAI_API_KEY: str = (
        get_secret_from_gcp("openai-api-key-prod")
        or os.getenv("OPENAI_API_KEY", "")
    )
    OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4")
    OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    OPENAI_REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "30"))
    
    # LangGraph Configuration
    LANGGRAPH_WORKFLOW_TIMEOUT_SECONDS: int = int(os.getenv("LANGGRAPH_WORKFLOW_TIMEOUT_SECONDS", "300"))
    LANGGRAPH_MAX_RETRIES: int = int(os.getenv("LANGGRAPH_MAX_RETRIES", "2"))
    
    # Agent Configuration
    STRUCTURE_AGENT_CONFIDENCE_THRESHOLD: float = float(os.getenv("STRUCTURE_AGENT_CONFIDENCE_THRESHOLD", "0.6"))
    APPEAL_AGENT_CONFIDENCE_THRESHOLD: float = float(os.getenv("APPEAL_AGENT_CONFIDENCE_THRESHOLD", "0.65"))
    
    # Monitoring
    ENABLE_AI_WORKFLOW_LOGGING: bool = os.getenv("ENABLE_AI_WORKFLOW_LOGGING", "True").lower() in ("true", "1", "yes", "on")
    AI_METRICS_COLLECTION_ENABLED: bool = os.getenv("AI_METRICS_COLLECTION_ENABLED", "True").lower() in ("true", "1", "yes", "on")


# Global configuration instances
db_config = DatabaseConfig()
redis_config = RedisConfig()
security_config = SecurityConfig()
app_config = AppConfig()
ai_config = AIConfig()


def get_test_database_url() -> str:
    """Get database URL for testing."""
    return DatabaseConfig.get_url(app_config.TEST_DB_NAME)


def get_database_url() -> str:
    """Get main database URL."""
    return DatabaseConfig.get_url()


def get_async_database_url() -> str:
    """Get async database URL for new infrastructure."""
    return DatabaseConfig.get_async_url()


def get_redis_url() -> str:
    """Get Redis URL."""
    return RedisConfig.get_url()


def get_settings():
    """Get combined settings object for easy access."""
    class Settings:
        # Database
        DATABASE_URL = get_database_url()
        ASYNC_DATABASE_URL = get_async_database_url()
        TEST_DATABASE_URL = get_test_database_url()
        REDIS_URL = get_redis_url()
        
        # Security
        SECRET_KEY = security_config.SECRET_KEY
        ALGORITHM = security_config.ALGORITHM
        ACCESS_TOKEN_EXPIRE_MINUTES = security_config.ACCESS_TOKEN_EXPIRE_MINUTES
        REFRESH_TOKEN_EXPIRE_DAYS = security_config.REFRESH_TOKEN_EXPIRE_DAYS
        
        # App
        DEBUG = app_config.DEBUG
        LOG_LEVEL = app_config.LOG_LEVEL
        ENVIRONMENT = app_config.ENVIRONMENT
        API_V1_STR = app_config.API_V1_STR
        PROJECT_NAME = app_config.PROJECT_NAME
        ALLOWED_HOSTS = app_config.ALLOWED_HOSTS
        
        # AI
        OPENAI_API_KEY = ai_config.OPENAI_API_KEY
        OPENAI_MODEL_NAME = ai_config.OPENAI_MODEL_NAME
        OPENAI_MAX_TOKENS = ai_config.OPENAI_MAX_TOKENS
        OPENAI_TEMPERATURE = ai_config.OPENAI_TEMPERATURE
        OPENAI_REQUEST_TIMEOUT_SECONDS = ai_config.OPENAI_REQUEST_TIMEOUT_SECONDS
        LANGGRAPH_WORKFLOW_TIMEOUT_SECONDS = ai_config.LANGGRAPH_WORKFLOW_TIMEOUT_SECONDS
        LANGGRAPH_MAX_RETRIES = ai_config.LANGGRAPH_MAX_RETRIES
        STRUCTURE_AGENT_CONFIDENCE_THRESHOLD = ai_config.STRUCTURE_AGENT_CONFIDENCE_THRESHOLD
        APPEAL_AGENT_CONFIDENCE_THRESHOLD = ai_config.APPEAL_AGENT_CONFIDENCE_THRESHOLD
        ENABLE_AI_WORKFLOW_LOGGING = ai_config.ENABLE_AI_WORKFLOW_LOGGING
        AI_METRICS_COLLECTION_ENABLED = ai_config.AI_METRICS_COLLECTION_ENABLED

        # Infrastructure settings
        DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "10"))
        DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
        REDIS_POOL_SIZE = int(os.getenv("REDIS_POOL_SIZE", "10"))
        LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "/tmp/ai_resume_storage")
        TESTING = os.getenv("TESTING", "false").lower() == "true"
        API_URL = os.getenv("API_URL", "http://localhost:8000")
    
    return Settings()


# Validate critical configuration on import
def validate_config():
    """Validate that critical configuration is set."""
    if security_config.SECRET_KEY == "your-secret-key-change-in-production":
        if app_config.ENVIRONMENT == "production":
            raise ValueError("SECRET_KEY must be changed in production environment")
        print("WARNING: Using default SECRET_KEY. Change this in production!")
    
    if not db_config.PASSWORD:
        raise ValueError("DB_PASSWORD must be set")

# Run validation
validate_config()