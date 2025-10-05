"""Configuration loaders for domain and infrastructure settings."""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from functools import lru_cache


class AgentBehaviorConfig:
    """Domain configuration for agent behavior and scoring."""

    def __init__(self, config_path: Optional[Path] = None):
        """Load agent behavior configuration from YAML.

        Args:
            config_path: Path to agents.yaml (defaults to config/agents.yaml)
        """
        if config_path is None:
            config_path = Path(__file__).parent / "agents.yaml"

        with open(config_path, "r") as f:
            self._config = yaml.safe_load(f)

    def get_agent_params(self, agent_name: str) -> Dict[str, Any]:
        """Get LLM parameters for a specific agent.

        Args:
            agent_name: Name of the agent (e.g., 'structure', 'appeal')

        Returns:
            Dictionary of agent-specific parameters (may be empty)
        """
        return self._config.get("agents", {}).get(agent_name, {})

    @property
    def scoring_weights(self) -> Dict[str, float]:
        """Get score calculation weights."""
        return self._config.get("scoring", {}).get("weights", {
            "structure": 0.4,
            "appeal": 0.6
        })

    @property
    def market_tier_thresholds(self) -> Dict[str, int]:
        """Get market tier score thresholds."""
        return self._config.get("scoring", {}).get("market_tiers", {
            "excellent": 80,
            "strong": 70,
            "good": 60,
            "fair": 50
        })

    @property
    def score_categories(self) -> Dict[str, str]:
        """Get score category descriptions."""
        return self._config.get("scoring", {}).get("categories", {
            "excellent": "excellent candidate",
            "strong": "strong candidate",
            "good": "good candidate",
            "fair": "fair candidate",
            "needs_improvement": "needs improvement"
        })


class IndustryConfig:
    """Domain configuration for industries."""

    def __init__(self, config_path: Optional[Path] = None):
        """Load industry configuration from YAML.

        Args:
            config_path: Path to industries.yaml (defaults to config/industries.yaml)
        """
        if config_path is None:
            config_path = Path(__file__).parent / "industries.yaml"

        with open(config_path, "r") as f:
            self._config = yaml.safe_load(f)

    def get_industry(self, industry_code: str) -> Dict[str, Any]:
        """Get configuration for a specific industry.

        Args:
            industry_code: Industry code (e.g., 'tech_consulting')

        Returns:
            Industry configuration dictionary
        """
        industries = self._config.get("industries", {})
        return industries.get(industry_code, industries.get("general_business", {}))

    def get_all_industries(self) -> Dict[str, Dict[str, Any]]:
        """Get all industry configurations."""
        return self._config.get("industries", {})

    def get_supported_codes(self) -> List[str]:
        """Get list of supported industry codes."""
        return list(self._config.get("industries", {}).keys())


# Singleton instances with caching
@lru_cache(maxsize=1)
def get_agent_config() -> AgentBehaviorConfig:
    """Get cached agent behavior configuration."""
    return AgentBehaviorConfig()


@lru_cache(maxsize=1)
def get_industry_config() -> IndustryConfig:
    """Get cached industry configuration."""
    return IndustryConfig()


__all__ = ["AgentBehaviorConfig", "IndustryConfig", "get_agent_config", "get_industry_config"]
