"""Infrastructure configuration for AI agents module."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM model and API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AI_AGENT_LLM_",
        case_sensitive=False
    )

    # API settings
    openai_api_key: str = ""  # Empty default, should be set via env var

    # Model settings
    model: str = "gpt-5-2025-08-07"
    fallback_model: Optional[str] = "gpt-4o"

    # Default parameters (can be overridden per agent in agents.yaml)
    default_temperature: float = 0.3
    default_max_tokens: int = 2000
    timeout_seconds: int = 120


class ResilienceConfig(BaseSettings):
    """Retry and error handling configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AI_AGENT_RETRY_",
        case_sensitive=False
    )

    max_retries: int = 3
    backoff_multiplier: float = 2.0  # Exponential backoff: 2^0, 2^1, 2^2
    max_backoff_seconds: int = 16


class PathConfig(BaseSettings):
    """File paths configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AI_AGENT_PATH_",
        case_sensitive=False
    )

    # Base paths (relative to ai_agents module root)
    config_dir: str = "config"
    prompts_dir: str = "prompts"


class AIAgentSettings(BaseSettings):
    """Main infrastructure settings for AI agents module."""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        case_sensitive=False
    )

    llm: LLMConfig = LLMConfig()
    resilience: ResilienceConfig = ResilienceConfig()
    paths: PathConfig = PathConfig()

    # Prompt language setting (single source of truth)
    # Change this value to switch between languages: "en" or "ja"
    prompt_language: str = "en"  # Default: English


# Singleton pattern
_settings: Optional[AIAgentSettings] = None


def get_settings() -> AIAgentSettings:
    """Get cached infrastructure settings instance."""
    global _settings
    if _settings is None:
        _settings = AIAgentSettings()
    return _settings
