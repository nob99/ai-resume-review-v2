"""Base Agent class with common functionality for all analysis agents."""

import re
import yaml
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from ai_agents.settings import get_settings
from ai_agents.config import get_agent_config


class BaseAgent:
    """Base class for all analysis agents.

    Provides common functionality:
    - OpenAI client initialization
    - Prompt template loading
    - Retry logic for API calls
    - Text parsing utilities
    """

    def __init__(self, api_key: Optional[str] = None, agent_config=None):
        """Initialize the base agent.

        Args:
            api_key: OpenAI API key (defaults to environment variable)
            agent_config: Optional AgentBehaviorConfig instance
        """
        self.settings = get_settings()
        self.agent_config = agent_config or get_agent_config()

        self.client = AsyncOpenAI(api_key=api_key or self.settings.llm.openai_api_key)
        self.max_retries = self.settings.resilience.max_retries
        self.backoff_multiplier = self.settings.resilience.backoff_multiplier

    def _load_prompt_template(self, template_name: str) -> Dict[str, Any]:
        """Load a prompt template from YAML file.

        Args:
            template_name: Name of the template file (e.g., "structure_v1.yaml")

        Returns:
            Loaded template dictionary
        """
        template_path = (
            Path(__file__).parent.parent
            / self.settings.paths.prompts_dir
            / template_name
        )

        with open(template_path, "r") as f:
            template = yaml.safe_load(f)

        return template

    async def _call_openai_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        agent_name: str,
        **kwargs
    ) -> str:
        """Call OpenAI API with exponential backoff retry logic.

        Args:
            system_prompt: System message for GPT
            user_prompt: User message with content to analyze
            agent_name: Name of the agent (for config lookup)
            **kwargs: Optional overrides for temperature, max_tokens

        Returns:
            GPT response text

        Raises:
            Exception: If all retries fail
        """
        # Get agent-specific overrides from config
        agent_params = self.agent_config.get_agent_params(agent_name)

        # Merge: kwargs > agent_config > defaults
        temperature = (
            kwargs.get("temperature")
            or agent_params.get("temperature")
            or self.settings.llm.default_temperature
        )
        max_tokens = (
            kwargs.get("max_tokens")
            or agent_params.get("max_tokens")
            or self.settings.llm.default_max_tokens
        )

        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.settings.llm.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.settings.llm.timeout_seconds
                )

                return response.choices[0].message.content

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                # Exponential backoff
                await asyncio.sleep(self.backoff_multiplier ** attempt)

    def _extract_list(self, text: str, section_name: str) -> List[str]:
        """Extract a bulleted list from the response text.

        Args:
            text: Full response text
            section_name: Name of the section to extract

        Returns:
            List of items from that section
        """
        # Try to find the section and extract items
        pattern = rf"{section_name}:?\s*\n((?:\s*[-•]\s*.+\n?)+)"
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)

        if match:
            items_text = match.group(1)
            # Extract individual items (handle various indentation)
            items = re.findall(r"^\s*[-•]\s*(.+)$", items_text, re.MULTILINE)
            return [item.strip() for item in items if item.strip()]

        return []

    def _extract_score(self, text: str, pattern: str, default: float = 0.0) -> float:
        """Extract a numeric score from text using regex pattern.

        Args:
            text: Text to search
            pattern: Regex pattern to match score
            default: Default value if not found

        Returns:
            Extracted score as float
        """
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return default