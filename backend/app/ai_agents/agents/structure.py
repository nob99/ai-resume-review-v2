"""Structure Agent for analyzing resume formatting and organization."""

import re
import yaml
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()


class StructureAgent:
    """Agent that analyzes resume structure, formatting, and professional presentation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Structure Agent.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
        """
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.prompt_template = self._load_prompt_template()
        self.max_retries = 3
        
    def _load_prompt_template(self) -> Dict[str, Any]:
        """Load the structure analysis prompt template from YAML."""
        template_path = Path(__file__).parent.parent / "prompts" / "templates" / "resume" / "structure_v1.yaml"
        
        with open(template_path, "r") as f:
            template = yaml.safe_load(f)
        
        return template
    
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
    
    async def _call_openai_with_retry(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI API with exponential backoff retry logic.
        
        Args:
            system_prompt: System message for GPT
            user_prompt: User message with resume text
            
        Returns:
            GPT response text
        """
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
    
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
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                results["scores"][key] = float(match.group(1))
            else:
                results["scores"][key] = 0.0
        
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