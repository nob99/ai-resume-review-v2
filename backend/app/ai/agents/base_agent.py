"""
Base Agent Class
================

Abstract base class for all resume analysis agents used in the LangGraph workflow.
Each agent is designed as a LangGraph node that processes state and returns updates.

This base class provides:
- Common interface for all agents
- Standardized error handling
- Confidence score calculation
- Performance monitoring
- Prompt management integration
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.ai.integrations.base_llm import BaseLLM, LLMError
from app.ai.models.analysis_request import AnalysisState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all resume analysis agents.
    
    Each agent implements the analyze() method which acts as a LangGraph node.
    The method receives the current workflow state and returns state updates.
    """
    
    def __init__(self, llm_client: BaseLLM, agent_name: Optional[str] = None):
        """
        Initialize base agent with LLM client.
        
        Args:
            llm_client: LLM client for making AI calls
            agent_name: Optional name for this agent (defaults to class name)
        """
        self.llm = llm_client
        self.agent_name = agent_name or self.__class__.__name__
        self.prompt_manager = None  # Will be set when prompt manager is implemented
        
        logger.info(f"Initialized {self.agent_name} with LLM: {llm_client.__class__.__name__}")
    
    @abstractmethod
    async def analyze(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Main analysis method that must be implemented by each agent.
        
        This method acts as a LangGraph node function:
        - Receives the current workflow state
        - Performs agent-specific analysis
        - Returns dictionary of state updates
        
        Args:
            state: Current workflow state containing resume text and context
            
        Returns:
            Dict containing state updates for the workflow
            
        Raises:
            LLMError: When LLM processing fails
            ValueError: When input validation fails
        """
        pass
    
    def _calculate_confidence(
        self, 
        raw_output: str, 
        expected_elements: List[str],
        min_content_length: int = 100
    ) -> float:
        """
        Calculate confidence score based on output quality indicators.
        
        Args:
            raw_output: Raw LLM output to analyze
            expected_elements: List of expected elements in the output
            min_content_length: Minimum expected content length
            
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        if not raw_output or len(raw_output) < min_content_length:
            return 0.2
        
        # Check for expected elements/content
        found_elements = 0
        for element in expected_elements:
            if element.lower() in raw_output.lower():
                found_elements += 1
        
        element_confidence = found_elements / len(expected_elements) if expected_elements else 0.5
        
        # Check for reasonable content length
        length_score = min(len(raw_output) / 1000, 1.0)  # Normalize to 1000 chars
        
        # Check for structured content (presence of scores, lists, etc.)
        structure_indicators = [
            "score", "rating", "points", "analysis", 
            "recommendation", "strength", "weakness",
            "•", "-", "1.", "2.", "3."  # List indicators
        ]
        
        structure_found = sum(1 for indicator in structure_indicators 
                            if indicator in raw_output.lower())
        structure_confidence = min(structure_found / 5, 1.0)
        
        # Weighted combination
        overall_confidence = (
            element_confidence * 0.4 +
            length_score * 0.3 + 
            structure_confidence * 0.3
        )
        
        # Ensure reasonable bounds
        return max(0.1, min(overall_confidence, 1.0))
    
    def _handle_agent_error(self, error: Exception, state: AnalysisState) -> Dict[str, Any]:
        """
        Standardized error handling for all agents.
        
        Args:
            error: Exception that occurred during analysis
            state: Current workflow state
            
        Returns:
            Dict containing error state updates
        """
        error_msg = f"{self.agent_name} error: {str(error)}"
        logger.error(
            f"Agent {self.agent_name} failed for analysis {state.get('analysis_id', 'unknown')}: {error_msg}",
            exc_info=True
        )
        
        return {
            "has_errors": True,
            "error_messages": [error_msg],
            "retry_count": state.get("retry_count", 0) + 1,
            "current_stage": f"{self.agent_name.lower()}_error"
        }
    
    def _get_processing_time_ms(self, start_time: float) -> int:
        """
        Calculate processing time in milliseconds.
        
        Args:
            start_time: Start timestamp from time.time()
            
        Returns:
            int: Processing time in milliseconds
        """
        return int((time.time() - start_time) * 1000)
    
    def _validate_input_state(self, state: AnalysisState) -> None:
        """
        Validate that required state elements are present.
        
        Args:
            state: Workflow state to validate
            
        Raises:
            ValueError: When required state elements are missing
        """
        required_fields = ["resume_text", "analysis_id", "industry"]
        missing_fields = [field for field in required_fields if not state.get(field)]
        
        if missing_fields:
            raise ValueError(f"Missing required state fields: {', '.join(missing_fields)}")
        
        # Validate resume text length
        resume_text = state.get("resume_text", "")
        if len(resume_text.strip()) < 50:
            raise ValueError("Resume text is too short for meaningful analysis")
    
    def _log_agent_start(self, state: AnalysisState) -> None:
        """Log agent analysis start."""
        logger.info(
            f"Starting {self.agent_name} analysis for {state.get('analysis_id', 'unknown')} "
            f"(industry: {state.get('industry', 'unknown')})"
        )
    
    def _log_agent_completion(
        self, 
        state: AnalysisState, 
        confidence: float, 
        processing_time_ms: int
    ) -> None:
        """Log agent analysis completion."""
        logger.info(
            f"{self.agent_name} analysis completed for {state.get('analysis_id', 'unknown')} "
            f"(confidence: {confidence:.2f}, time: {processing_time_ms}ms)"
        )
    
    def _extract_scores_from_output(self, raw_output: str, score_patterns: Dict[str, str]) -> Dict[str, float]:
        """
        Extract numerical scores from LLM output using regex patterns.
        
        Args:
            raw_output: Raw LLM output text
            score_patterns: Dict mapping score names to regex patterns
            
        Returns:
            Dict mapping score names to extracted values (defaults to 75.0 if not found)
        """
        import re
        scores = {}
        
        for score_name, pattern in score_patterns.items():
            match = re.search(pattern, raw_output, re.IGNORECASE)
            if match:
                try:
                    score_value = float(match.group(1))
                    # Ensure score is within valid range
                    scores[score_name] = max(0.0, min(100.0, score_value))
                except ValueError:
                    scores[score_name] = 75.0  # Default fallback
            else:
                scores[score_name] = 75.0  # Default when pattern not found
        
        return scores
    
    def _extract_list_items(self, raw_output: str, section_keywords: List[str]) -> Dict[str, List[str]]:
        """
        Extract list items from different sections of LLM output.
        
        Args:
            raw_output: Raw LLM output text
            section_keywords: Keywords that indicate different sections
            
        Returns:
            Dict mapping section names to extracted list items
        """
        sections = {keyword: [] for keyword in section_keywords}
        
        lines = raw_output.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line indicates a new section
            line_lower = line.lower()
            for keyword in section_keywords:
                if keyword.lower() in line_lower:
                    current_section = keyword
                    break
            
            # Extract list items (lines starting with bullet points, numbers, etc.)
            if current_section and any(line.startswith(marker) for marker in ['-', '•', '*', '1.', '2.', '3.']):
                # Clean the list item
                item = line.lstrip('-•*123456789. ').strip()
                if item and len(item) > 10:  # Only meaningful items
                    sections[current_section].append(item)
        
        return sections
    
    def _create_default_result(self, state: AnalysisState, error_msg: str) -> Dict[str, Any]:
        """
        Create a default result when analysis fails.
        
        Args:
            state: Current workflow state
            error_msg: Error message to include
            
        Returns:
            Dict containing default analysis result
        """
        return {
            "has_errors": True,
            "error_messages": [f"{self.agent_name} failed: {error_msg}"],
            "current_stage": f"{self.agent_name.lower()}_failed",
            "confidence_score": 0.1,
            "processing_time_ms": 0
        }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get information about this agent for monitoring and debugging.
        
        Returns:
            Dict containing agent metadata
        """
        return {
            "agent_name": self.agent_name,
            "agent_class": self.__class__.__name__,
            "llm_provider": self.llm.__class__.__name__,
            "llm_model": self.llm.model,
            "capabilities": self._get_capabilities(),
            "version": "1.0.0"
        }
    
    @abstractmethod
    def _get_capabilities(self) -> List[str]:
        """
        Return list of capabilities this agent provides.
        
        Returns:
            List of capability strings
        """
        pass
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.agent_name}(llm={self.llm.__class__.__name__}, model={self.llm.model})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        return (
            f"{self.__class__.__name__}("
            f"agent_name='{self.agent_name}', "
            f"llm={self.llm.__class__.__name__}, "
            f"model='{self.llm.model}'"
            f")"
        )