"""Base Agent class with common functionality for all analysis agents."""

import re
import yaml
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()


class BaseAgent:
    """Base class for all analysis agents.

    Provides common functionality:
    - OpenAI client initialization
    - Prompt template loading
    - Retry logic for API calls
    - Text parsing utilities
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the base agent.

        Args:
            api_key: OpenAI API key (defaults to environment variable)
        """
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.max_retries = 3

    def _load_prompt_template(self, template_name: str) -> Dict[str, Any]:
        """Load a prompt template from YAML file.

        Args:
            template_name: Name of the template file (e.g., "structure_v1.yaml")

        Returns:
            Loaded template dictionary
        """
        template_path = (
            Path(__file__).parent.parent
            / "prompts"
            / "templates"
            / "resume"
            / template_name
        )

        with open(template_path, "r") as f:
            template = yaml.safe_load(f)

        return template

    async def _call_openai_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> str:
        """Call OpenAI API with exponential backoff retry logic.

        Args:
            system_prompt: System message for GPT
            user_prompt: User message with content to analyze
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            GPT response text

        Raises:
            Exception: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                return response.choices[0].message.content

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

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