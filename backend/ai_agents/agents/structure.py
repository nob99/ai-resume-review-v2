"""Structure Agent for analyzing resume formatting and organization."""

import re
from typing import Dict, Any, List, Optional

from .base import BaseAgent


class StructureAgent(BaseAgent):
    """Agent that analyzes resume structure, formatting, and professional presentation."""

    def __init__(self, api_key: Optional[str] = None, agent_config=None):
        """Initialize the Structure Agent.

        Args:
            api_key: OpenAI API key (defaults to environment variable)
            agent_config: Optional AgentBehaviorConfig instance
        """
        super().__init__(api_key, agent_config)
        self.prompt_template = self._load_prompt_template("structure_v1.yaml")
        self.parsing_config = self.prompt_template.get("parsing", {})
    
    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resume structure and formatting.

        Args:
            state: Current workflow state containing resume_text

        Returns:
            Updated state with structure analysis results
        """
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

        except Exception as e:
            state["error"] = f"Structure analysis failed: {str(e)}"
            # Set default values on error
            state["structure_scores"] = {"format": 0, "organization": 0, "tone": 0, "completeness": 0}
            state["structure_feedback"] = {"issues": ["Analysis failed"], "strengths": []}
            state["structure_metadata"] = {}

        return state

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the GPT response using parsing config from template.

        Args:
            response: Raw text response from GPT

        Returns:
            Parsed results with scores, feedback, and metadata
        """
        results = {
            "scores": {},
            "feedback": {},
            "metadata": {}
        }

        # Extract scores using parsing config
        score_configs = self.parsing_config.get("scores", {})
        for score_name, score_config in score_configs.items():
            pattern = score_config.get("pattern", "")
            default = score_config.get("default", 0)
            results["scores"][score_name] = self._extract_score(response, pattern, default)

        # Extract feedback using parsing config
        feedback_configs = self.parsing_config.get("feedback", {})
        for feedback_key, section_name in feedback_configs.items():
            results["feedback"][feedback_key] = self._extract_list(response, section_name)

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

        return results