"""Structure Agent for analyzing resume formatting and organization."""

import re
from typing import Dict, Any, List, Optional

from .base import BaseAgent


class StructureAgent(BaseAgent):
    """Agent that analyzes resume structure, formatting, and professional presentation."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Structure Agent.

        Args:
            api_key: OpenAI API key (defaults to environment variable)
        """
        super().__init__(api_key)
        self.prompt_template = self._load_prompt_template("structure_v1.yaml")
    
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
            
            # Call OpenAI with retry logic
            response = await self._call_openai_with_retry(system_prompt, user_prompt)
            
            # Parse the response
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
        """Parse the GPT response to extract scores and feedback.
        
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
        
        # Extract scores using regex patterns from template
        score_patterns = {
            "format": r"Format\s*Score[:\s]*(\d+)",
            "organization": r"Section\s*Organization\s*Score[:\s]*(\d+)",
            "tone": r"Professional\s*Tone\s*Score[:\s]*(\d+)",
            "completeness": r"Completeness\s*Score[:\s]*(\d+)"
        }

        for key, pattern in score_patterns.items():
            results["scores"][key] = self._extract_score(response, pattern)
        
        # Extract feedback lists
        results["feedback"]["issues"] = self._extract_list(response, "Formatting Issues")
        results["feedback"]["missing_sections"] = self._extract_list(response, "Missing Sections")
        results["feedback"]["tone_problems"] = self._extract_list(response, "Tone Problems")
        results["feedback"]["strengths"] = self._extract_list(response, "Strengths")
        results["feedback"]["recommendations"] = self._extract_list(response, "Recommendations")
        
        # Extract metadata
        metadata_patterns = {
            "total_sections": r"Total\s*Sections\s*Found[:\s]*(\d+)",
            "word_count": r"Word\s*Count[:\s]*(\d+)",
            "reading_time": r"Estimated\s*Reading\s*Time[:\s]*(\d+)"
        }
        
        for key, pattern in metadata_patterns.items():
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                results["metadata"][key] = int(match.group(1))

        return results