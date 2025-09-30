"""Appeal Agent for industry-specific resume analysis."""

import re
from typing import Dict, Any, List, Optional

from .base import BaseAgent
from app.core.industries import get_industry_config


class AppealAgent(BaseAgent):
    """Agent that analyzes resume appeal and competitiveness for specific industries."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Appeal Agent.

        Args:
            api_key: OpenAI API key (defaults to environment variable)
        """
        super().__init__(api_key)
        self.prompt_template = self._load_prompt_template("appeal_v1.yaml")
    
    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resume appeal for specific industry.
        
        Args:
            state: Current workflow state with resume_text and structure results
            
        Returns:
            Updated state with appeal analysis results and final score
        """
        try:
            # Get industry configuration
            industry = state.get("industry", "general_business")
            industry_config = get_industry_config(industry)
            
            # Build structure context from previous analysis
            structure_context = self._build_structure_context(state)
            
            # Prepare prompt variables
            prompt_vars = {
                "resume_text": state["resume_text"],
                "industry": industry,
                "industry_title": industry_config["display_name"],
                "industry_display": industry_config["display_name"],
                "industry_upper": industry_config["display_name"].upper(),
                "key_skills_list": ", ".join(industry_config["key_skills"]),
                "structure_context_section": structure_context
            }
            
            # Get the prompts from template
            system_prompt = self.prompt_template["prompts"]["system"].format(**prompt_vars)
            user_prompt = self.prompt_template["prompts"]["user"].format(**prompt_vars)
            
            # Call OpenAI with retry logic (with custom temperature and tokens for appeal)
            response = await self._call_openai_with_retry(
                system_prompt,
                user_prompt,
                temperature=0.4,
                max_tokens=2500
            )
            
            # Parse the response
            parsed_results = self._parse_response(response)
            
            # Update state with results
            state["appeal_scores"] = parsed_results["scores"]
            state["appeal_feedback"] = parsed_results["feedback"]
            state["market_tier"] = parsed_results.get("market_tier", "mid")
            
            # Calculate overall score
            state["overall_score"] = self._calculate_overall_score(state)
            state["summary"] = self._generate_summary(state, industry_config["display_name"])
            
        except Exception as e:
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
        """Parse the GPT response to extract scores and feedback.
        
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
        
        # Extract scores using regex patterns
        score_patterns = {
            "achievement_relevance": r"Achievement\s*Relevance\s*Score[:\s]*(\d+)",
            "skills_alignment": r"Skills?\s*Alignment\s*Score[:\s]*(\d+)",
            "experience_fit": r"Experience\s*Fit\s*Score[:\s]*(\d+)",
            "competitive_positioning": r"Competitive\s*Positioning\s*Score[:\s]*(\d+)"
        }

        for key, pattern in score_patterns.items():
            results["scores"][key] = self._extract_score(response, pattern)
        
        # Extract market tier
        tier_match = re.search(r"Market\s*Tier[:\s]*(entry|mid|senior|executive)", response, re.IGNORECASE)
        if tier_match:
            results["market_tier"] = tier_match.group(1).lower()
        
        # Extract feedback lists
        results["feedback"]["relevant_achievements"] = self._extract_list(response, "Relevant Achievements")
        results["feedback"]["missing_skills"] = self._extract_list(response, "Missing Skills")
        results["feedback"]["transferable_experience"] = self._extract_list(response, "Transferable Experience")
        results["feedback"]["competitive_advantages"] = self._extract_list(response, "Competitive Advantages")
        results["feedback"]["improvement_areas"] = self._extract_list(response, "Improvement Areas")

        return results

    def _calculate_overall_score(self, state: Dict[str, Any]) -> float:
        """Calculate weighted overall score from structure and appeal scores.
        
        Args:
            state: State with both structure and appeal scores
            
        Returns:
            Overall score (0-100)
        """
        # Weight configuration: 40% structure, 60% appeal
        structure_weight = 0.4
        appeal_weight = 0.6
        
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
        """Generate executive summary of the analysis.
        
        Args:
            state: Complete state with all analysis results
            industry_name: Display name of the industry
            
        Returns:
            Executive summary text
        """
        overall_score = state.get("overall_score", 0)
        market_tier = state.get("market_tier", "mid")
        
        # Determine score category
        if overall_score >= 80:
            category = "excellent"
        elif overall_score >= 70:
            category = "strong"
        elif overall_score >= 60:
            category = "good"
        elif overall_score >= 50:
            category = "fair"
        else:
            category = "needs improvement"
        
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