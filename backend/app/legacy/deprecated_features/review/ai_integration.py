"""
AI Integration Service for review feature.
Interfaces with the AI orchestrator and handles raw response processing.
"""

import time
from typing import Dict, Any, Optional
from uuid import UUID

from app.core.config import app_config
from app.core.datetime_utils import utc_now
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from ai_agents.orchestrator import ResumeAnalysisOrchestrator


class AIIntegrationService:
    """Service for integrating with AI resume analysis orchestrator."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI integration service.
        
        Args:
            api_key: Optional OpenAI API key (defaults to config)
        """
        self.orchestrator = ResumeAnalysisOrchestrator(api_key=api_key)
        self.model_name = app_config.AI_MODEL_NAME if hasattr(app_config, 'AI_MODEL_NAME') else "gpt-4"
    
    async def analyze_resume(
        self,
        resume_text: str,
        industry: str,
        review_request_id: UUID,
        target_role: Optional[str] = None,
        experience_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze resume using AI orchestrator and return raw response.
        
        Args:
            resume_text: The resume text to analyze
            industry: Target industry for analysis
            review_request_id: ID of the review request for tracking
            target_role: Optional target role information
            experience_level: Optional experience level
            
        Returns:
            Raw AI response with analysis results
        """
        start_time = time.time()
        
        try:
            # Use review_request_id as analysis_id for tracking
            analysis_id = str(review_request_id)
            
            # Call the AI orchestrator
            raw_response = await self.orchestrator.analyze(
                resume_text=resume_text,
                industry=industry,
                analysis_id=analysis_id
            )
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Enhance the response with metadata
            enhanced_response = self._enhance_response(
                raw_response,
                processing_time_ms,
                target_role,
                experience_level
            )
            
            return enhanced_response
            
        except Exception as e:
            # Return error response in consistent format
            processing_time_ms = int((time.time() - start_time) * 1000)
            return self._create_error_response(
                str(e),
                str(review_request_id),
                processing_time_ms
            )
    
    def _enhance_response(
        self,
        raw_response: Dict[str, Any],
        processing_time_ms: int,
        target_role: Optional[str] = None,
        experience_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enhance AI response with additional metadata.
        
        Args:
            raw_response: Original AI response
            processing_time_ms: Processing time in milliseconds
            target_role: Target role for enhancement
            experience_level: Experience level for enhancement
            
        Returns:
            Enhanced response with metadata
        """
        enhanced = raw_response.copy()
        
        # Add processing metadata
        enhanced["processing_metadata"] = {
            "processing_time_ms": processing_time_ms,
            "ai_model_used": self.model_name,
            "processed_at": utc_now().isoformat(),
            "target_role": target_role,
            "experience_level": experience_level
        }
        
        # Ensure consistent structure for success responses
        if enhanced.get("success", False):
            self._normalize_success_response(enhanced)
        
        return enhanced
    
    def _normalize_success_response(self, response: Dict[str, Any]) -> None:
        """
        Normalize successful AI response to ensure consistent structure.
        
        Args:
            response: AI response to normalize (modified in place)
        """
        # Ensure all required fields exist
        if "overall_score" not in response:
            response["overall_score"] = 0
        
        if "summary" not in response:
            response["summary"] = "Analysis completed"
        
        if "market_tier" not in response:
            response["market_tier"] = "unknown"
        
        # Ensure structure section exists
        if "structure" not in response:
            response["structure"] = {"scores": {}, "feedback": {}, "metadata": {}}
        else:
            structure = response["structure"]
            if "scores" not in structure:
                structure["scores"] = {}
            if "feedback" not in structure:
                structure["feedback"] = {}
            if "metadata" not in structure:
                structure["metadata"] = {}
        
        # Ensure appeal section exists
        if "appeal" not in response:
            response["appeal"] = {"scores": {}, "feedback": {}}
        else:
            appeal = response["appeal"]
            if "scores" not in appeal:
                appeal["scores"] = {}
            if "feedback" not in appeal:
                appeal["feedback"] = {}
    
    def _create_error_response(
        self,
        error_message: str,
        analysis_id: str,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """
        Create consistent error response format.
        
        Args:
            error_message: Error description
            analysis_id: Analysis tracking ID
            processing_time_ms: Processing time before error
            
        Returns:
            Formatted error response
        """
        return {
            "success": False,
            "analysis_id": analysis_id,
            "error": error_message,
            "overall_score": 0,
            "summary": f"Analysis failed: {error_message}",
            "processing_metadata": {
                "processing_time_ms": processing_time_ms,
                "ai_model_used": self.model_name,
                "processed_at": utc_now().isoformat(),
                "error_occurred": True
            },
            "structure": {"scores": {}, "feedback": {}, "metadata": {}},
            "appeal": {"scores": {}, "feedback": {}}
        }
    
    def extract_essential_fields(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract essential fields from raw AI response for database storage.
        
        Args:
            ai_response: Raw AI response dictionary
            
        Returns:
            Dict with essential fields extracted
        """
        metadata = ai_response.get("processing_metadata", {})
        
        return {
            "overall_score": ai_response.get("overall_score", 0),
            "executive_summary": ai_response.get("summary", ""),
            "ai_model_used": metadata.get("ai_model_used", self.model_name),
            "processing_time_ms": metadata.get("processing_time_ms", 0)
        }
    
    def validate_ai_response(self, ai_response: Dict[str, Any]) -> bool:
        """
        Validate that AI response has required structure.
        
        Args:
            ai_response: AI response to validate
            
        Returns:
            True if response is valid, False otherwise
        """
        if not isinstance(ai_response, dict):
            return False
        
        # Check required top-level fields
        required_fields = ["success", "analysis_id"]
        if not all(field in ai_response for field in required_fields):
            return False
        
        # For successful responses, check structure
        if ai_response.get("success", False):
            success_fields = ["overall_score", "summary", "structure", "appeal"]
            if not all(field in ai_response for field in success_fields):
                return False
            
            # Check nested structure
            structure = ai_response.get("structure", {})
            if not isinstance(structure, dict) or "scores" not in structure:
                return False
            
            appeal = ai_response.get("appeal", {})
            if not isinstance(appeal, dict) or "scores" not in appeal:
                return False
        
        return True
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to AI orchestrator with a simple request.
        
        Returns:
            Test result with success status and timing
        """
        start_time = time.time()
        
        try:
            # Simple test with minimal resume text
            test_response = await self.orchestrator.analyze(
                resume_text="Test resume: John Doe, Software Engineer with 5 years experience.",
                industry="Technology",
                analysis_id="test-connection"
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return {
                "success": True,
                "processing_time_ms": processing_time,
                "ai_model": self.model_name,
                "response_valid": self.validate_ai_response(test_response),
                "test_response": test_response
            }
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": processing_time,
                "ai_model": self.model_name
            }