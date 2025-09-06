"""
Structure Agent Implementation
==============================

The Structure Agent analyzes resume structure, formatting, and professional presentation.
It operates as a LangGraph node in the workflow, focusing on industry-agnostic aspects
of resume quality such as organization, completeness, and professional tone.

Key Responsibilities:
- Format and layout analysis
- Section organization assessment  
- Professional tone evaluation
- Completeness checking
- Structural recommendations

This agent produces structured output that can be consumed by the Appeal Agent
for context-aware industry-specific analysis.
"""

import time
import re
import logging
from typing import Dict, Any, List

from .base_agent import BaseAgent
from app.ai.models.analysis_request import AnalysisState, StructureAnalysisResult
from app.ai.integrations.base_llm import BaseLLM

logger = logging.getLogger(__name__)


class StructureAgent(BaseAgent):
    """
    Analyzes resume structure, formatting, and professional presentation.
    
    This agent is industry-agnostic and focuses on universal resume quality factors
    that apply regardless of the target industry or role.
    """
    
    def __init__(self, llm_client: BaseLLM):
        """Initialize Structure Agent with LLM client."""
        super().__init__(llm_client, "StructureAgent")
        
        # Score extraction patterns for parsing LLM output
        self.score_patterns = {
            "format_score": r"format[_\s]*score[:\s]*(\d+\.?\d*)",
            "section_organization_score": r"(?:section[_\s]*)?organization[_\s]*score[:\s]*(\d+\.?\d*)",
            "professional_tone_score": r"(?:professional[_\s]*)?tone[_\s]*score[:\s]*(\d+\.?\d*)",
            "completeness_score": r"completeness[_\s]*score[:\s]*(\d+\.?\d*)"
        }
        
        # Expected sections in a well-structured resume
        self.expected_sections = [
            "experience", "education", "skills", "summary", "objective",
            "projects", "certifications", "awards", "achievements"
        ]
        
        # Keywords for extracting feedback sections
        self.feedback_keywords = [
            "formatting_issues", "missing_sections", "tone_problems", 
            "completeness_gaps", "strengths", "recommendations"
        ]
    
    async def analyze(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Perform comprehensive structure analysis of resume.
        
        This is the main LangGraph node function that:
        1. Validates input state
        2. Calls LLM for structure analysis  
        3. Parses structured output
        4. Returns state updates for workflow
        
        Args:
            state: Current workflow state containing resume text and context
            
        Returns:
            Dict containing structure analysis results and state updates
        """
        start_time = time.time()
        
        try:
            # Validate input state
            self._validate_input_state(state)
            self._log_agent_start(state)
            
            # Prepare analysis context
            analysis_context = self._prepare_analysis_context(state)
            
            # Get analysis prompt
            analysis_prompt = self._build_analysis_prompt(analysis_context)
            
            # Execute LLM analysis
            logger.debug(f"Calling LLM for structure analysis: {state['analysis_id']}")
            llm_response = await self.llm.ainvoke(
                analysis_prompt,
                system_message=self._get_system_message(),
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=3000
            )
            
            # Parse structured output
            structured_result = self._parse_structure_output(
                llm_response.content, 
                state["resume_text"]
            )
            
            # Calculate confidence score
            confidence = self._calculate_structure_confidence(
                structured_result, 
                llm_response.content
            )
            
            # Update result metadata
            processing_time_ms = self._get_processing_time_ms(start_time)
            structured_result.processing_time_ms = processing_time_ms
            structured_result.confidence_score = confidence
            structured_result.model_used = self.llm.model
            
            self._log_agent_completion(state, confidence, processing_time_ms)
            
            # Return state updates for LangGraph workflow
            return {
                "structure_analysis": structured_result,
                "structure_confidence": confidence,
                "current_stage": "structure_analysis",
                "structure_errors": []
            }
            
        except Exception as e:
            logger.error(f"Structure analysis failed for {state.get('analysis_id', 'unknown')}: {str(e)}")
            return self._handle_agent_error(e, state)
    
    def _prepare_analysis_context(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Prepare context for structure analysis.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict containing analysis context
        """
        resume_text = state["resume_text"]
        
        return {
            "resume_text": resume_text,
            "analysis_id": state["analysis_id"],
            "word_count": len(resume_text.split()),
            "character_count": len(resume_text),
            "sections_found": self._identify_resume_sections(resume_text),
            "estimated_reading_time": max(1, len(resume_text.split()) // 200)
        }
    
    def _build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build the analysis prompt for the LLM.
        
        Args:
            context: Analysis context prepared by _prepare_analysis_context
            
        Returns:
            str: Complete analysis prompt
        """
        return f"""
Analyze the following resume for structural quality, formatting, and professional presentation.

RESUME TO ANALYZE:
{context['resume_text']}

ANALYSIS REQUIREMENTS:

1. FORMATTING ASSESSMENT (0-100 scale):
   - Visual layout and organization
   - Consistent formatting and spacing
   - Professional appearance
   - Readability and structure

2. SECTION ORGANIZATION ASSESSMENT (0-100 scale):
   - Logical flow of information
   - Appropriate section ordering
   - Clear section headers
   - Content organization within sections

3. PROFESSIONAL TONE ASSESSMENT (0-100 scale):
   - Professional language usage
   - Appropriate terminology
   - Consistent voice and style
   - Absence of informal language

4. COMPLETENESS ASSESSMENT (0-100 scale):
   - Presence of essential sections
   - Sufficient detail in each section
   - Contact information completeness
   - Overall information adequacy

EXPECTED OUTPUT FORMAT:

SCORES:
- Format Score: [0-100]
- Section Organization Score: [0-100]
- Professional Tone Score: [0-100]  
- Completeness Score: [0-100]

DETAILED ANALYSIS:

Formatting Issues:
- [List specific formatting problems, if any]
- [Each issue should be actionable and specific]

Missing Sections:
- [List any expected sections that are missing]
- [Focus on sections relevant to professional resumes]

Tone Problems:
- [List instances of unprofessional language]
- [Include overly casual or inappropriate phrasing]

Completeness Gaps:
- [List missing critical information]
- [Focus on essential details for resume effectiveness]

Strengths:
- [List well-executed structural elements]
- [Highlight what the resume does well structurally]

Recommendations:
- [Provide 3-5 specific improvement suggestions]
- [Focus on actionable structural improvements]

CONTEXT:
- Word Count: {context['word_count']}
- Sections Identified: {len(context['sections_found'])}
- Estimated Reading Time: {context['estimated_reading_time']} minutes

Please provide thorough, specific analysis focusing on structural and formatting aspects only.
Do not consider industry-specific content relevance - focus purely on structure and presentation.
"""
    
    def _get_system_message(self) -> str:
        """Get system message for the LLM."""
        return """You are an expert resume structure and formatting analyst. Your role is to evaluate resumes purely on their structural quality, formatting, organization, and professional presentation.

You focus exclusively on:
- Visual layout and formatting consistency
- Section organization and logical flow
- Professional language and tone
- Completeness of essential information

You do NOT evaluate:
- Industry-specific content relevance
- Skills alignment with particular roles
- Achievement significance in specific fields

Provide detailed, actionable feedback with specific scores and recommendations for structural improvements."""
    
    def _identify_resume_sections(self, resume_text: str) -> List[str]:
        """
        Identify major resume sections present in the text.
        
        Args:
            resume_text: Resume text to analyze
            
        Returns:
            List of identified section names
        """
        found_sections = []
        text_lower = resume_text.lower()
        
        # Define section keywords and their variations
        section_patterns = {
            "Summary": [r"summary", r"profile", r"overview"],
            "Objective": [r"objective", r"goal"],
            "Experience": [r"experience", r"employment", r"work history", r"career"],
            "Education": [r"education", r"academic", r"degree"],
            "Skills": [r"skills", r"competencies", r"technical skills"],
            "Projects": [r"projects", r"portfolio"],
            "Certifications": [r"certifications", r"certificates", r"credentials"],
            "Awards": [r"awards", r"honors", r"achievements", r"recognition"],
            "Publications": [r"publications", r"papers", r"research"],
            "Languages": [r"languages", r"linguistic"],
            "Volunteer": [r"volunteer", r"community", r"service"],
            "References": [r"references", r"contacts"]
        }
        
        for section_name, patterns in section_patterns.items():
            for pattern in patterns:
                if re.search(rf"\b{pattern}\b", text_lower):
                    found_sections.append(section_name)
                    break  # Found this section, move to next
        
        return found_sections
    
    def _parse_structure_output(
        self, 
        raw_output: str, 
        resume_text: str
    ) -> StructureAnalysisResult:
        """
        Parse LLM output into structured StructureAnalysisResult.
        
        Args:
            raw_output: Raw LLM response text
            resume_text: Original resume text for context
            
        Returns:
            StructureAnalysisResult: Parsed and validated result
        """
        try:
            # Extract scores using regex patterns
            scores = self._extract_scores_from_output(raw_output, self.score_patterns)
            
            # Extract feedback lists
            feedback = self._extract_feedback_lists(raw_output)
            
            # Analyze resume metadata
            sections_found = self._identify_resume_sections(resume_text)
            word_count = len(resume_text.split())
            
            return StructureAnalysisResult(
                # Core scores
                format_score=scores.get("format_score", 75.0),
                section_organization_score=scores.get("section_organization_score", 75.0),
                professional_tone_score=scores.get("professional_tone_score", 75.0),
                completeness_score=scores.get("completeness_score", 75.0),
                
                # Detailed feedback
                formatting_issues=feedback.get("formatting_issues", []),
                missing_sections=feedback.get("missing_sections", []),
                tone_problems=feedback.get("tone_problems", []),
                completeness_gaps=feedback.get("completeness_gaps", []),
                
                # Positive feedback
                strengths=feedback.get("strengths", []),
                recommendations=feedback.get("recommendations", []),
                
                # Metadata
                total_sections_found=len(sections_found),
                word_count=word_count,
                estimated_reading_time_minutes=max(1, word_count // 200),
                
                # Will be set by calling function
                confidence_score=0.0,
                processing_time_ms=0,
                model_used="",
                prompt_version="structure_v1.0"
            )
            
        except Exception as e:
            logger.error(f"Error parsing structure output: {str(e)}")
            return self._create_default_structure_result(resume_text)
    
    def _extract_feedback_lists(self, raw_output: str) -> Dict[str, List[str]]:
        """
        Extract feedback lists from LLM output.
        
        Args:
            raw_output: Raw LLM response
            
        Returns:
            Dict mapping feedback categories to extracted items
        """
        feedback = {
            "formatting_issues": [],
            "missing_sections": [],
            "tone_problems": [],
            "completeness_gaps": [],
            "strengths": [],
            "recommendations": []
        }
        
        # Split output into lines for processing
        lines = raw_output.split('\n')
        current_category = None
        
        # Category detection patterns
        category_patterns = {
            "formatting_issues": [r"formatting\s+issues?", r"format\s+problems?"],
            "missing_sections": [r"missing\s+sections?"],
            "tone_problems": [r"tone\s+problems?", r"language\s+issues?"],
            "completeness_gaps": [r"completeness\s+gaps?", r"missing\s+information"],
            "strengths": [r"strengths?", r"positive\s+aspects?"],
            "recommendations": [r"recommendations?", r"suggestions?", r"improvements?"]
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line indicates a new category
            line_lower = line.lower()
            category_found = False
            for category, patterns in category_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line_lower):
                        current_category = category
                        category_found = True
                        break
                if category_found:
                    break
            
            # If this line is a category header, don't process it as an item
            if category_found:
                continue
            
            # Extract list items (lines starting with bullets, dashes, numbers)
            if current_category and re.match(r'^[-•*\d+\.]\s+', line):
                # Clean the list item
                item = re.sub(r'^[-•*\d+\.]\s*', '', line).strip()
                if item and len(item) > 5:  # Only meaningful items
                    feedback[current_category].append(item)
        
        return feedback
    
    def _calculate_structure_confidence(
        self, 
        result: StructureAnalysisResult, 
        raw_output: str
    ) -> float:
        """
        Calculate confidence specific to structure analysis.
        
        Args:
            result: Parsed structure analysis result
            raw_output: Raw LLM output
            
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        confidence_factors = []
        
        # Factor 1: Score reasonableness (all scores should be 0-100)
        scores = [
            result.format_score, 
            result.section_organization_score,
            result.professional_tone_score, 
            result.completeness_score
        ]
        valid_scores = sum(1 for score in scores if 0 <= score <= 100)
        score_confidence = valid_scores / len(scores)
        confidence_factors.append(("score_validity", score_confidence, 0.25))
        
        # Factor 2: Feedback completeness
        feedback_items = (
            len(result.strengths) + 
            len(result.recommendations) + 
            len(result.formatting_issues) + 
            len(result.completeness_gaps)
        )
        feedback_confidence = min(feedback_items / 8, 1.0)  # Normalize to 8 items
        confidence_factors.append(("feedback_completeness", feedback_confidence, 0.25))
        
        # Factor 3: Output structure and length
        structure_confidence = self._calculate_confidence(
            raw_output, 
            ["score", "formatting", "sections", "recommendations"],
            min_content_length=200
        )
        confidence_factors.append(("output_structure", structure_confidence, 0.3))
        
        # Factor 4: Consistency between scores and feedback
        has_issues = len(result.formatting_issues) + len(result.completeness_gaps) > 0
        avg_score = sum(scores) / len(scores)
        
        # If average score is low but no issues identified, or vice versa
        if (avg_score < 60 and not has_issues) or (avg_score > 85 and has_issues):
            consistency_confidence = 0.5
        else:
            consistency_confidence = 0.9
        confidence_factors.append(("score_feedback_consistency", consistency_confidence, 0.2))
        
        # Calculate weighted confidence
        total_confidence = sum(factor[1] * factor[2] for factor in confidence_factors)
        
        # Ensure reasonable bounds
        return max(0.3, min(total_confidence, 1.0))
    
    def _create_default_structure_result(self, resume_text: str) -> StructureAnalysisResult:
        """
        Create default result when parsing fails.
        
        Args:
            resume_text: Original resume text
            
        Returns:
            StructureAnalysisResult: Default result with basic analysis
        """
        word_count = len(resume_text.split())
        sections_found = self._identify_resume_sections(resume_text)
        
        return StructureAnalysisResult(
            format_score=70.0,
            section_organization_score=70.0,
            professional_tone_score=70.0,
            completeness_score=70.0,
            
            formatting_issues=["Unable to analyze formatting due to parsing error"],
            missing_sections=[],
            tone_problems=[],
            completeness_gaps=["Analysis incomplete due to processing error"],
            
            strengths=["Resume structure analysis was incomplete"],
            recommendations=[
                "Please retry the analysis",
                "Ensure resume is properly formatted",
                "Contact support if issue persists"
            ],
            
            total_sections_found=len(sections_found),
            word_count=word_count,
            estimated_reading_time_minutes=max(1, word_count // 200),
            
            confidence_score=0.3,
            processing_time_ms=0,
            model_used="",
            prompt_version="structure_v1.0"
        )
    
    def _get_capabilities(self) -> List[str]:
        """Return list of capabilities this agent provides."""
        return [
            "resume_formatting_analysis",
            "section_organization_assessment",
            "professional_tone_evaluation",
            "completeness_checking",
            "structural_recommendations",
            "layout_quality_scoring"
        ]
    
    def get_expected_sections(self) -> List[str]:
        """Get list of expected resume sections."""
        return self.expected_sections.copy()
    
    def validate_structure_result(self, result: StructureAnalysisResult) -> bool:
        """
        Validate a structure analysis result for completeness and correctness.
        
        Args:
            result: Structure analysis result to validate
            
        Returns:
            bool: True if result is valid, False otherwise
        """
        try:
            # Check that all scores are within valid range
            scores = [
                result.format_score,
                result.section_organization_score,
                result.professional_tone_score,
                result.completeness_score
            ]
            
            if not all(0 <= score <= 100 for score in scores):
                return False
            
            # Check that confidence is within valid range
            if not (0 <= result.confidence_score <= 1):
                return False
            
            # Check that required fields are present
            required_lists = [
                result.strengths,
                result.recommendations
            ]
            
            if not all(isinstance(lst, list) for lst in required_lists):
                return False
            
            # Check basic metadata
            if result.word_count < 0 or result.total_sections_found < 0:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating structure result: {str(e)}")
            return False