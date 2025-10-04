"""Structure Agent for analyzing resume formatting and organization."""

import logging
import re
from typing import Dict, Any, List, Optional

from .base import BaseAgent

logger = logging.getLogger(__name__)


class StructureAgent(BaseAgent):
    """Agent that analyzes resume structure, formatting, and professional presentation."""

    def __init__(self, api_key: Optional[str] = None, agent_config=None):
        """Initialize the Structure Agent.

        Args:
            api_key: OpenAI API key (defaults to environment variable)
            agent_config: Optional AgentBehaviorConfig instance
        """
        super().__init__(api_key, agent_config)
        self.prompt_template = self._load_prompt_template("structure_prompt_v1")
        self.parsing_config = self.prompt_template.get("parsing", {})
    
    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resume structure and formatting.

        Args:
            state: Current workflow state containing resume_text

        Returns:
            Updated state with structure analysis results
        """
        logger.info("Structure analysis started")

        try:
            # Get the prompts from template
            system_prompt = self.prompt_template["prompts"]["system"]
            user_prompt = self.prompt_template["prompts"]["user"].format(
                resume_text=state["resume_text"]
            )

            # Call OpenAI with retry logic (uses agent config)
            response = await self._call_openai_with_retry(
                system_prompt,
                user_prompt,
                agent_name="structure"
            )

            # Parse the response using parsing config
            parsed_results = self._parse_response(response)

            # Update state with results
            state["structure_scores"] = parsed_results["scores"]
            state["structure_feedback"] = parsed_results["feedback"]
            state["structure_metadata"] = parsed_results["metadata"]

            # Calculate average score
            scores = parsed_results["scores"]
            avg_score = sum(scores.values()) / len(scores) if scores else 0
            logger.info(f"Structure analysis completed score={avg_score:.1f}")

        except Exception as e:
            logger.error(f"Structure analysis failed: {str(e)}", exc_info=True)
            state["error"] = f"Structure analysis failed: {str(e)}"
            # Set default values on error
            state["structure_scores"] = {"format": 0, "organization": 0, "tone": 0, "completeness": 0}
            state["structure_feedback"] = {"issues": ["Analysis failed"], "strengths": []}
            state["structure_metadata"] = {}

        return state

    def _parse_agent_specific_fields(self, response: str, results: Dict[str, Any]) -> None:
        """Add metadata extraction for structure analysis.

        Args:
            response: Raw LLM response text
            results: Results dict to mutate (adds 'metadata' field)
        """
        results["metadata"] = {}

        # Extract metadata using parsing config
        metadata_configs = self.parsing_config.get("metadata", {})
        for metadata_key, metadata_config in metadata_configs.items():
            pattern = metadata_config.get("pattern", "")
            default = metadata_config.get("default")
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                results["metadata"][metadata_key] = int(match.group(1))
            elif default is not None:
                results["metadata"][metadata_key] = default