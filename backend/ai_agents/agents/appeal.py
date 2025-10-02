"""Appeal Agent for industry-specific resume analysis."""

import logging
import re
from typing import Dict, Any, List, Optional

from .base import BaseAgent
from ai_agents.config import get_industry_config

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
    
    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resume appeal for specific industry.

        Args:
            state: Current workflow state with resume_text and structure results

        Returns:
            Updated state with appeal analysis results and final score
        """
        industry = state.get("industry", "general_business")
        logger.info(f"Appeal analysis started industry={industry}")

        try:
            # Get industry configuration from YAML
            industry_data = self.industry_config_loader.get_industry(industry)
            
            # Build structure context from previous analysis
            structure_context = self._build_structure_context(state)

            # Prepare prompt variables
            prompt_vars = {
                "resume_text": state["resume_text"],
                "industry": industry,
                "industry_title": industry_data["display_name"],
                "industry_display": industry_data["display_name"],
                "industry_upper": industry_data["display_name"].upper(),
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

            # Calculate overall score using config weights
            state["overall_score"] = self._calculate_overall_score(state)
            state["summary"] = self._generate_summary(state, industry_data["display_name"])

            # Log completion
            scores = parsed_results["scores"]
            avg_score = sum(scores.values()) / len(scores) if scores else 0
            logger.info(f"Appeal analysis completed score={avg_score:.1f} tier={state['market_tier']}")

        except Exception as e:
            logger.error(f"Appeal analysis failed: {str(e)}", exc_info=True)
            state["error"] = f"Appeal analysis failed: {str(e)}"
            # Set default values on error
            state["appeal_scores"] = {"achievement_relevance": 0, "skills_alignment": 0, "experience_fit": 0, "competitive_positioning": 0}
            state["appeal_feedback"] = {"missing_skills": ["Analysis failed"], "competitive_advantages": []}
            state["market_tier"] = "unknown"
            state["overall_score"] = 0
            state["summary"] = "Analysis could not be completed due to an error."
        
        return state
    
    def _build_structure_context(self, state: Dict[str, Any]) -> str:
        """Build context from structure analysis results.
        
        Args:
            state: Current state with structure analysis results
            
        Returns:
            Formatted context string
        """
        if not state.get("structure_scores"):
            return ""
        
        scores = state["structure_scores"]
        feedback = state.get("structure_feedback", {})
        
        context_parts = [
            "STRUCTURE ANALYSIS CONTEXT:",
            f"- Format Score: {scores.get('format', 0)}/100",
            f"- Organization Score: {scores.get('organization', 0)}/100",
            f"- Professional Tone Score: {scores.get('tone', 0)}/100",
            f"- Completeness Score: {scores.get('completeness', 0)}/100"
        ]
        
        if feedback.get("issues"):
            issues = feedback["issues"][:3]  # Top 3 issues
            context_parts.append(f"- Key Issues: {', '.join(issues)}")
        
        if feedback.get("strengths"):
            strengths = feedback["strengths"][:2]  # Top 2 strengths
            context_parts.append(f"- Strengths: {', '.join(strengths)}")
        
        return "\n".join(context_parts)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the GPT response using parsing config from template.

        Args:
            response: Raw text response from GPT

        Returns:
            Parsed results with scores, feedback, and market tier
        """
        results = {
            "scores": {},
            "feedback": {},
            "market_tier": "mid"
        }

        # Extract scores using parsing config
        score_configs = self.parsing_config.get("scores", {})
        for score_name, score_config in score_configs.items():
            pattern = score_config.get("pattern", "")
            default = score_config.get("default", 0)
            results["scores"][score_name] = self._extract_score(response, pattern, default)

        # Extract market tier using parsing config
        tier_config = self.parsing_config.get("market_tier", {})
        tier_pattern = tier_config.get("pattern", r"Market\s*Tier[:\s]*(entry|mid|senior|executive)")
        tier_match = re.search(tier_pattern, response, re.IGNORECASE)
        if tier_match:
            results["market_tier"] = tier_match.group(1).lower()
        else:
            results["market_tier"] = tier_config.get("default", "mid")

        # Extract feedback using parsing config
        feedback_configs = self.parsing_config.get("feedback", {})
        for feedback_key, section_name in feedback_configs.items():
            results["feedback"][feedback_key] = self._extract_list(response, section_name)

        return results

    def _calculate_overall_score(self, state: Dict[str, Any]) -> float:
        """Calculate weighted overall score using config weights.

        Args:
            state: State with both structure and appeal scores

        Returns:
            Overall score (0-100)
        """
        # Get weights from domain config
        weights = self.agent_config.scoring_weights
        structure_weight = weights.get("structure", 0.4)
        appeal_weight = weights.get("appeal", 0.6)

        # Calculate structure average
        structure_scores = state.get("structure_scores", {})
        if structure_scores:
            structure_avg = sum(structure_scores.values()) / len(structure_scores)
        else:
            structure_avg = 0

        # Calculate appeal average
        appeal_scores = state.get("appeal_scores", {})
        if appeal_scores:
            appeal_avg = sum(appeal_scores.values()) / len(appeal_scores)
        else:
            appeal_avg = 0

        # Calculate weighted overall score
        overall = (structure_avg * structure_weight) + (appeal_avg * appeal_weight)

        return round(overall, 1)
    
    def _generate_summary(self, state: Dict[str, Any], industry_name: str) -> str:
        """Generate executive summary using thresholds from config.

        Args:
            state: Complete state with all analysis results
            industry_name: Display name of the industry

        Returns:
            Executive summary text
        """
        overall_score = state.get("overall_score", 0)
        market_tier = state.get("market_tier", "mid")

        # Get thresholds and categories from domain config
        thresholds = self.agent_config.market_tier_thresholds
        categories = self.agent_config.score_categories

        # Determine category using thresholds from config
        if overall_score >= thresholds.get("excellent", 80):
            category = categories.get("excellent", "excellent candidate")
        elif overall_score >= thresholds.get("strong", 70):
            category = categories.get("strong", "strong candidate")
        elif overall_score >= thresholds.get("good", 60):
            category = categories.get("good", "good candidate")
        elif overall_score >= thresholds.get("fair", 50):
            category = categories.get("fair", "fair candidate")
        else:
            category = categories.get("needs_improvement", "needs improvement")
        
        # Get top strengths and improvements
        structure_feedback = state.get("structure_feedback", {})
        appeal_feedback = state.get("appeal_feedback", {})
        
        strengths = structure_feedback.get("strengths", [])[:1] + appeal_feedback.get("competitive_advantages", [])[:1]
        improvements = appeal_feedback.get("improvement_areas", [])[:2]
        
        # Build summary
        summary_parts = [
            f"This resume scores {overall_score}/100, indicating a {category} candidate for {industry_name} roles.",
            f"The candidate appears to be at the {market_tier} level."
        ]
        
        if strengths:
            summary_parts.append(f"Key strengths include: {', '.join(strengths)}.")
        
        if improvements:
            summary_parts.append(f"Priority improvements: {', '.join(improvements)}.")
        
        return " ".join(summary_parts)