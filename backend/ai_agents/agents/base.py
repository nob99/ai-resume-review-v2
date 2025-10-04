"""Base Agent class with common functionality for all analysis agents."""

import logging
import re
import yaml
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from ai_agents.settings import get_settings
from ai_agents.config import get_agent_config
from ai_agents.utils import log_api_call, log_api_response, log_prompts

logger = logging.getLogger(__name__)


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

        # Initialize parsing_config placeholder (child agents will set this)
        self.parsing_config = {}

    def _load_prompt_template(self, template_base: str) -> Dict[str, Any]:
        """Load a prompt template from YAML file.

        Args:
            template_base: Base name of the template (e.g., "structure_prompt_v1")
                          Language suffix will be added automatically based on settings

        Returns:
            Loaded template dictionary
        """
        # Get language from settings (single source of truth)
        lang = self.settings.prompt_language

        # Construct full template filename with language suffix
        template_name = f"{template_base}_{lang}.yaml"

        template_path = (
            Path(__file__).parent.parent
            / self.settings.paths.prompts_dir
            / template_name
        )

        with open(template_path, "r", encoding="utf-8") as f:
            template = yaml.safe_load(f)

        logger.info(f"Loaded prompt template: {template_name}")
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
                # Log API call
                log_api_call(logger, agent_name, self.settings.llm.model, max_tokens)

                # Log the actual prompts being sent to OpenAI
                log_prompts(logger, agent_name, system_prompt, user_prompt)

                response = await self.client.chat.completions.create(
                    model=self.settings.llm.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_completion_tokens=max_tokens,
                    timeout=self.settings.llm.timeout_seconds,
                    response_format={"type": "json_object"}
                )

                # Log API response
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                log_api_response(logger, agent_name, response.model, usage)

                # Validate response
                if not response:
                    raise ValueError("No response from OpenAI API")

                if not response.choices or len(response.choices) == 0:
                    raise ValueError("Empty choices in OpenAI response")

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty content from OpenAI API")

                # Log the raw response for debugging
                logger.info(f"=== RAW OPENAI RESPONSE for {agent_name} ===")
                logger.info(content)
                logger.info(f"=== END RAW RESPONSE (length: {len(content)} chars, ~{len(content.split())} words) ===")

                # === DATA SIZE CHECKPOINT 1: RAW OPENAI RESPONSE ===
                logger.info(f"=== CHECKPOINT 1: RAW OPENAI RESPONSE ({agent_name}) ===")
                logger.info(f"Total characters: {len(content)}")
                logger.info(f"Total words: {len(content.split())}")
                logger.info(f"Total lines: {len(content.splitlines())}")
                logger.info(f"First 200 chars: {content[:200]}")
                logger.info(f"Last 200 chars: {content[-200:]}")
                logger.info(f"=== END CHECKPOINT 1 ===")

                return content

            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"OpenAI API call failed after {self.max_retries} retries: {str(e)}")
                    raise e
                # Retry with exponential backoff
                logger.warning(f"OpenAI API call failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
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

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from GPT.

        Args:
            response: Raw JSON string response from GPT

        Returns:
            Parsed results as dictionary

        Raises:
            ValueError: If JSON parsing fails
        """
        # Parse JSON
        try:
            results = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {response[:500]}")
            raise ValueError(f"Invalid JSON from OpenAI: {e}")

        # === DATA SIZE CHECKPOINT 2: PARSED JSON RESPONSE ===
        logger.info(f"=== CHECKPOINT 2: PARSED JSON RESPONSE ===")
        logger.info(f"Top-level keys: {list(results.keys())}")

        if "scores" in results:
            logger.info(f"Score fields: {list(results['scores'].keys())}")

        if "feedback" in results:
            feedback = results.get('feedback', {})
            total_feedback_items = sum(len(v) if isinstance(v, list) else 0 for v in feedback.values())
            logger.info(f"Total feedback items: {total_feedback_items}")
            for key, value in feedback.items():
                if isinstance(value, list):
                    logger.info(f"  - {key}: {len(value)} items")

        logger.info(f"=== END CHECKPOINT 2 ===")

        return results

    def _get_error_defaults(self) -> Dict[str, Any]:
        """Get default values to set in state when analysis fails.

        Subclasses must override this to return their specific error defaults.
        This ensures consistent error handling across all agents.

        Returns:
            Dictionary of state keys and their default error values

        Example:
            return {
                "structure_scores": {"format": 0, "organization": 0},
                "structure_feedback": {"issues": ["Analysis failed"]},
                "structure_metadata": {}
            }
        """
        raise NotImplementedError("Subclasses must implement _get_error_defaults()")

    def _handle_analysis_error(self, state: Dict[str, Any], error: Exception, agent_name: str) -> Dict[str, Any]:
        """Handle analysis error by logging and setting default state values.

        This method provides consistent error handling across all agents.

        Args:
            state: Current workflow state
            error: The exception that occurred
            agent_name: Name of the agent for logging

        Returns:
            Updated state with error information and default values
        """
        error_msg = f"{agent_name.capitalize()} analysis failed: {str(error)}"
        logger.error(error_msg, exc_info=True)

        # Set error message
        state["error"] = error_msg

        # Set agent-specific default values
        defaults = self._get_error_defaults()
        state.update(defaults)

        return state