"""Appeal Agent for industry-specific resume analysis."""

import logging
import re
from typing import Dict, Any, Optional

from .base import BaseAgent
from ai_agents.config import get_industry_config
from ai_agents.utils import log_agent_start, log_agent_complete, build_structure_context
from ai_agents.services import ScoreCalculator, SummaryGenerator

logger = logging.getLogger(__name__)


class AppealAgent(BaseAgent):
    """Agent that analyzes resume appeal and competitiveness for specific industries."""

    def __init__(self, api_key: Optional[str] = None, agent_config=None):
        """Initialize the Appeal Agent.

        Args:
            api_key: OpenAI API key (defaults to environment variable)
            agent_config: Optional AgentBehaviorConfig instance
        """
        super().__init__(api_key, agent_config)
        self.prompt_template = self._load_prompt_template("appeal_prompt_v1")
        self.parsing_config = self.prompt_template.get("parsing", {})
        self.industry_config_loader = get_industry_config()

        # Initialize services
        self.score_calculator = ScoreCalculator(self.agent_config.scoring_weights)
        self.summary_generator = SummaryGenerator(
            self.agent_config.market_tier_thresholds,
            self.agent_config.score_categories
        )
    
    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resume appeal for specific industry.

        Args:
            state: Current workflow state with resume_text and structure results

        Returns:
            Updated state with appeal analysis results and final score
        """
        industry = state.get("industry", "general_business")
        log_agent_start(logger, "appeal", industry=industry)

        try:
            # Get industry configuration from YAML
            industry_data = self.industry_config_loader.get_industry(industry)

            # Build structure context from previous analysis using utility
            structure_context = build_structure_context(state)

            # Prepare prompt variables
            industry_name = industry_data["display_name"]
            prompt_vars = {
                "resume_text": state["resume_text"],
                "industry": industry,
                "industry_title": industry_name,
                "industry_upper": industry_name.upper(),
                "key_skills_list": ", ".join(industry_data["key_skills"]),
                "structure_context_section": structure_context
            }

            # Get the prompts from template
            system_prompt = self.prompt_template["prompts"]["system"].format(**prompt_vars)
            user_prompt = self.prompt_template["prompts"]["user"].format(**prompt_vars)

            # Call OpenAI with retry logic (uses agent config for temp/tokens)
            response = await self._call_openai_with_retry(
                system_prompt,
                user_prompt,
                agent_name="appeal"
            )

            # Parse the response using parsing config
            parsed_results = self._parse_response(response)

            # Update state with results
            state["appeal_scores"] = parsed_results["scores"]
            state["appeal_feedback"] = parsed_results["feedback"]
            state["market_tier"] = parsed_results.get("market_tier", "mid")

            # === DATA SIZE CHECKPOINT 4: APPEAL AGENT STATE ===
            logger.info(f"=== CHECKPOINT 4: APPEAL AGENT STATE ===")
            logger.info(f"Scores: {parsed_results['scores']}")
            logger.info(f"Market tier: {state['market_tier']}")
            total_feedback_items = sum(len(v) if isinstance(v, list) else 0 for v in parsed_results['feedback'].values())
            logger.info(f"Total feedback items: {total_feedback_items}")
            for key, value in parsed_results['feedback'].items():
                if isinstance(value, list):
                    logger.info(f"  - {key}: {len(value)} items")
                    for idx, item in enumerate(value[:3], 1):  # Show first 3 items
                        logger.info(f"    [{idx}] {item[:100]}..." if len(item) > 100 else f"    [{idx}] {item}")
            logger.info(f"=== END CHECKPOINT 4 ===")

            # Calculate overall score using ScoreCalculator service
            state["overall_score"] = self.score_calculator.calculate_overall_score(state)

            # Generate summary using SummaryGenerator service
            state["summary"] = self.summary_generator.generate_summary(
                overall_score=state["overall_score"],
                market_tier=state["market_tier"],
                industry_name=industry_name,
                structure_feedback=state.get("structure_feedback", {}),
                appeal_feedback=state["appeal_feedback"]
            )

            # Log completion
            scores = parsed_results["scores"]
            avg_score = sum(scores.values()) / len(scores) if scores else 0
            log_agent_complete(logger, "appeal", score=avg_score, tier=state['market_tier'])

        except Exception as e:
            return self._handle_analysis_error(state, e, "appeal")

        return state
    
    def _get_error_defaults(self) -> Dict[str, Any]:
        """Get default values for appeal analysis errors.

        Returns:
            Dictionary with appeal-specific error defaults
        """
        return {
            "appeal_scores": {
                "achievement_relevance": 0,
                "skills_alignment": 0,
                "experience_fit": 0,
                "competitive_positioning": 0
            },
            "appeal_feedback": {
                "missing_skills": ["Analysis failed"],
                "competitive_advantages": []
            },
            "market_tier": "unknown",
            "overall_score": 0,
            "summary": "Analysis could not be completed due to an error."
        }

    def _parse_agent_specific_fields(self, response: str, results: Dict[str, Any]) -> None:
        """Add market tier extraction for appeal analysis.

        Args:
            response: Raw LLM response text
            results: Results dict to mutate (adds 'market_tier' field)
        """
        # Extract market tier using parsing config
        tier_config = self.parsing_config.get("market_tier", {})
        tier_pattern = tier_config.get("pattern", r"Market\s*Tier[:\s]*(entry|mid|senior|executive)")
        tier_match = re.search(tier_pattern, response, re.IGNORECASE)
        if tier_match:
            results["market_tier"] = tier_match.group(1).lower()
        else:
            results["market_tier"] = tier_config.get("default", "mid")