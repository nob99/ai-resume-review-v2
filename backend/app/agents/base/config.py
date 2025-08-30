"""
Agent configuration management.
"""

import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from .agent import AgentConfig, AgentType


class LLMProviderConfig(BaseModel):
    """Configuration for LLM providers."""
    provider: str
    api_key_env: str
    base_url: Optional[str] = None
    default_model: str
    available_models: List[str]


class AIAgentSettings(BaseSettings):
    """AI Agent system settings."""
    
    # API Keys (will be loaded from environment)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API Key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API Key")
    
    # Default configurations
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    default_max_tokens: int = Field(default=1000, ge=1)
    default_timeout: int = Field(default=30, ge=1)
    
    # Provider configurations
    providers: Dict[str, LLMProviderConfig] = Field(default_factory=lambda: {
        "openai": LLMProviderConfig(
            provider="openai",
            api_key_env="OPENAI_API_KEY",
            default_model="gpt-3.5-turbo",
            available_models=[
                "gpt-3.5-turbo",
                "gpt-4",
                "gpt-4-turbo-preview"
            ]
        ),
        "anthropic": LLMProviderConfig(
            provider="anthropic",
            api_key_env="ANTHROPIC_API_KEY",
            default_model="claude-3-haiku-20240307",
            available_models=[
                "claude-3-haiku-20240307",
                "claude-3-sonnet-20240229",
                "claude-3-opus-20240229"
            ]
        )
    })
    
    class Config:
        env_prefix = "AI_AGENT_"
        case_sensitive = False


class AgentConfigManager:
    """Manager for agent configurations."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.settings = AIAgentSettings()
        self._default_configs = self._create_default_configs()
    
    def _create_default_configs(self) -> Dict[AgentType, AgentConfig]:
        """Create default configurations for each agent type."""
        return {
            AgentType.TEST: AgentConfig(
                agent_type=AgentType.TEST,
                name="test_agent",
                description="Simple test agent for LangChain integration",
                model_provider="openai",
                model_name="gpt-3.5-turbo",
                temperature=0.7,
                system_prompt="You are a helpful test assistant."
            ),
            AgentType.RESUME_ANALYZER: AgentConfig(
                agent_type=AgentType.RESUME_ANALYZER,
                name="resume_analyzer",
                description="Analyzes resumes for overall structure and content",
                model_provider="openai",
                model_name="gpt-4",
                temperature=0.3,
                system_prompt="You are an expert resume analyzer and career counselor."
            ),
            AgentType.SKILLS_EXTRACTOR: AgentConfig(
                agent_type=AgentType.SKILLS_EXTRACTOR,
                name="skills_extractor",
                description="Extracts and categorizes skills from resumes",
                model_provider="anthropic",
                model_name="claude-3-haiku-20240307",
                temperature=0.2,
                system_prompt="You are a specialist in identifying and categorizing professional skills."
            )
        }
    
    def get_config(self, agent_type: AgentType) -> AgentConfig:
        """Get configuration for an agent type.
        
        Args:
            agent_type: Type of agent
            
        Returns:
            Agent configuration
        """
        return self._default_configs.get(agent_type)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available LLM providers.
        
        Returns:
            List of provider names
        """
        return list(self.settings.providers.keys())
    
    def get_provider_config(self, provider: str) -> Optional[LLMProviderConfig]:
        """Get configuration for a specific provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Provider configuration or None if not found
        """
        return self.settings.providers.get(provider)
    
    def is_provider_available(self, provider: str) -> bool:
        """Check if a provider is available (has API key).
        
        Args:
            provider: Provider name
            
        Returns:
            True if provider is available
        """
        provider_config = self.get_provider_config(provider)
        if not provider_config:
            return False
        
        api_key = os.getenv(provider_config.api_key_env)
        return api_key is not None and api_key.strip() != ""
    
    def get_available_providers_with_keys(self) -> List[str]:
        """Get list of providers that have API keys configured.
        
        Returns:
            List of available provider names
        """
        return [
            provider for provider in self.get_available_providers()
            if self.is_provider_available(provider)
        ]
    
    def validate_config(self, config: AgentConfig) -> tuple[bool, Optional[str]]:
        """Validate an agent configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if provider exists
        if config.model_provider not in self.get_available_providers():
            return False, f"Unknown provider: {config.model_provider}"
        
        # Check if provider is available
        if not self.is_provider_available(config.model_provider):
            return False, f"Provider {config.model_provider} not available (missing API key)"
        
        # Check if model is supported
        provider_config = self.get_provider_config(config.model_provider)
        if config.model_name not in provider_config.available_models:
            return False, f"Model {config.model_name} not supported by {config.model_provider}"
        
        return True, None


# Global configuration manager instance
config_manager = AgentConfigManager()