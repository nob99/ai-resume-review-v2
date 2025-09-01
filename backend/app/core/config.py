"""
Centralized configuration management for the AI Resume Review application.
Handles environment variables and provides secure defaults.
"""

import os
from typing import Optional
from pathlib import Path

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


class DatabaseConfig:
    """Database configuration settings."""
    
    HOST: str = os.getenv("DB_HOST", "localhost")
    PORT: int = int(os.getenv("DB_PORT", "5432"))
    NAME: str = os.getenv("DB_NAME", "ai_resume_review_dev")
    USER: str = os.getenv("DB_USER", "postgres")
    PASSWORD: str = os.getenv("DB_PASSWORD", "dev_password_123")
    
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
        return f"postgresql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{db_name}"


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
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
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
    
    # File Storage Configuration
    FILE_STORAGE_PATH: str = os.getenv("FILE_STORAGE_PATH", "storage/uploads")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "30"))
    
    # Testing Configuration
    TEST_DB_NAME: str = os.getenv("TEST_DB_NAME", "ai_resume_review_test")


# Global configuration instances
db_config = DatabaseConfig()
redis_config = RedisConfig()
security_config = SecurityConfig()
app_config = AppConfig()


def get_test_database_url() -> str:
    """Get database URL for testing."""
    return DatabaseConfig.get_url(app_config.TEST_DB_NAME)


def get_database_url() -> str:
    """Get main database URL."""
    return DatabaseConfig.get_url()


def get_redis_url() -> str:
    """Get Redis URL."""
    return RedisConfig.get_url()


def get_settings():
    """Get application settings."""
    return type('Settings', (), {
        'file_storage_path': app_config.FILE_STORAGE_PATH,
        'max_file_size_mb': app_config.MAX_FILE_SIZE_MB,
        'database_url': get_database_url(),
        'redis_url': get_redis_url(),
        'debug': app_config.DEBUG,
        'environment': app_config.ENVIRONMENT
    })()


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