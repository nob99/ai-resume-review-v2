"""Structure Agent for analyzing resume formatting and organization."""

import logging
import re
from typing import Dict, Any, List, Optional

from .base import BaseAgent
from ai_agents.utils import log_agent_start, log_agent_complete

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
        log_agent_start(logger, "structure")

        try:
            # Get the prompts from template
            system_prompt = self.prompt_template["prompts"]["system"]
            user_prompt = self.prompt_template["prompts"]["user"].replace(
                "{resume_text}", state["resume_text"]
            )

            # Call OpenAI with retry logic (uses agent config)
            response = await self._call_openai_with_retry(
                system_prompt,
                user_prompt,
                agent_name="structure"
            )

            # Parse the response (now JSON parsing)
            parsed_results = self._parse_response(response)

            # Update state with results
            state["structure_scores"] = parsed_results.get("scores", {})
            state["structure_feedback"] = parsed_results.get("feedback", {})
            state["structure_metadata"] = parsed_results.get("metadata", {})

            # === DATA SIZE CHECKPOINT 3: STRUCTURE AGENT STATE ===
            logger.info(f"=== CHECKPOINT 3: STRUCTURE AGENT STATE ===")
            logger.info(f"Scores: {parsed_results['scores']}")
            logger.info(f"Metadata: {parsed_results['metadata']}")
            total_feedback_items = sum(len(v) if isinstance(v, list) else 0 for v in parsed_results['feedback'].values())
            logger.info(f"Total feedback items: {total_feedback_items}")
            for key, value in parsed_results['feedback'].items():
                if isinstance(value, list):
                    logger.info(f"  - {key}: {len(value)} items")
                    for idx, item in enumerate(value[:3], 1):  # Show first 3 items
                        logger.info(f"    [{idx}] {item[:100]}..." if len(item) > 100 else f"    [{idx}] {item}")
            logger.info(f"=== END CHECKPOINT 3 ===")

            # Calculate average score and log completion
            scores = parsed_results["scores"]
            avg_score = sum(scores.values()) / len(scores) if scores else 0
            log_agent_complete(logger, "structure", score=avg_score)

        except Exception as e:
            return self._handle_analysis_error(state, e, "structure")

        return state

    def _get_error_defaults(self) -> Dict[str, Any]:
        """Get default values for structure analysis errors.

        Returns:
            Dictionary with structure-specific error defaults
        """
        return {
            "structure_scores": {
                "format": 0,
                "organization": 0,
                "tone": 0,
                "completeness": 0
            },
            "structure_feedback": {
                "issues": ["Analysis failed"],
                "strengths": []
            },
            "structure_metadata": {}
        }