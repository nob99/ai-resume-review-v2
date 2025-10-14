"""Main orchestrator for the AI resume analysis workflow."""

import logging
import time
import uuid
from typing import Dict, Any, Optional

from .agents import StructureAgent, AppealAgent
from .workflows import create_workflow, ResumeAnalysisState
from .settings import get_settings
from .config import get_agent_config
from .utils import log_analysis_start, log_analysis_complete, log_analysis_error
from app.core.config import ai_config

logger = logging.getLogger(__name__)


class ResumeAnalysisOrchestrator:
    """Orchestrates the two-agent resume analysis workflow."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the orchestrator with agents and workflow.

        Args:
            api_key: Optional OpenAI API key (defaults to centralized config)
        """
        # Get settings and config
        settings = get_settings()
        agent_config = get_agent_config()

        # Initialize agents with config - use centralized OpenAI API key
        self.structure_agent = StructureAgent(
            api_key=api_key or ai_config.OPENAI_API_KEY,
            agent_config=agent_config
        )
        self.appeal_agent = AppealAgent(
            api_key=api_key or ai_config.OPENAI_API_KEY,
            agent_config=agent_config
        )

        # Create the workflow
        self.workflow = create_workflow(
            structure_agent=self.structure_agent,
            appeal_agent=self.appeal_agent
        )
    
    async def analyze(
        self,
        resume_text: str,
        industry: str,
        analysis_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the complete resume analysis workflow.
        
        Args:
            resume_text: The resume text to analyze
            industry: Target industry for appeal analysis
            analysis_id: Optional analysis ID for tracking
            
        Returns:
            Complete analysis results with scores and feedback
        """
        # Generate analysis ID if not provided
        if not analysis_id:
            analysis_id = str(uuid.uuid4())

        start_time = time.time()
        log_analysis_start(logger, analysis_id, industry)

        # Initialize state
        initial_state: ResumeAnalysisState = {
            "resume_text": resume_text,
            "industry": industry,
            "structure_scores": None,
            "structure_feedback": None,
            "structure_metadata": None,
            "appeal_scores": None,
            "appeal_feedback": None,
            "market_tier": None,
            "overall_score": None,
            "summary": None,
            "error": None,
            "retry_count": 0
        }

        try:
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)

            # Check for errors in the final state
            if final_state.get("error"):
                elapsed = time.time() - start_time
                log_analysis_error(logger, analysis_id, final_state['error'], elapsed, exc_info=False)
                return self._format_error_response(final_state["error"], analysis_id)

            # Format and return successful results
            elapsed = time.time() - start_time
            overall_score = final_state.get("overall_score", 0)
            log_analysis_complete(logger, analysis_id, overall_score, elapsed)
            return self._format_success_response(final_state, analysis_id)

        except Exception as e:
            # Handle unexpected errors
            elapsed = time.time() - start_time
            log_analysis_error(logger, analysis_id, str(e), elapsed)
            return self._format_error_response(str(e), analysis_id)
    
    def _format_success_response(self, state: Dict[str, Any], analysis_id: str) -> Dict[str, Any]:
        """Format successful analysis results for API response.

        Args:
            state: Final workflow state with all results
            analysis_id: Analysis tracking ID

        Returns:
            Formatted response dictionary
        """
        response = {
            "success": True,
            "analysis_id": analysis_id,
            "overall_score": state.get("overall_score", 0),
            "market_tier": state.get("market_tier", "unknown"),
            "summary": state.get("summary", ""),
            "structure": {
                "scores": state.get("structure_scores", {}),
                "feedback": state.get("structure_feedback", {}),
                "metadata": state.get("structure_metadata", {})
            },
            "appeal": {
                "scores": state.get("appeal_scores", {}),
                "feedback": state.get("appeal_feedback", {})
            }
        }

        # === DATA SIZE CHECKPOINT 5: ORCHESTRATOR FORMATTED RESPONSE ===
        logger.debug(f"=== CHECKPOINT 5: ORCHESTRATOR FORMATTED RESPONSE ===")
        logger.debug(f"Analysis ID: {analysis_id}")
        logger.debug(f"Overall score: {response['overall_score']}")
        logger.debug(f"Market tier: {response['market_tier']}")

        # Count structure feedback items
        structure_feedback = response['structure']['feedback']
        structure_total = sum(len(v) if isinstance(v, list) else 0 for v in structure_feedback.values())
        logger.debug(f"Structure feedback total items: {structure_total}")
        for key, value in structure_feedback.items():
            if isinstance(value, list):
                logger.debug(f"  - structure.{key}: {len(value)} items")

        # Count appeal feedback items
        appeal_feedback = response['appeal']['feedback']
        appeal_total = sum(len(v) if isinstance(v, list) else 0 for v in appeal_feedback.values())
        logger.debug(f"Appeal feedback total items: {appeal_total}")
        for key, value in appeal_feedback.items():
            if isinstance(value, list):
                logger.debug(f"  - appeal.{key}: {len(value)} items")

        logger.debug(f"Total feedback items in response: {structure_total + appeal_total}")
        logger.debug(f"=== END CHECKPOINT 5 ===")

        return response
    
    def _format_error_response(self, error_message: str, analysis_id: str) -> Dict[str, Any]:
        """Format error response for API.
        
        Args:
            error_message: Error description
            analysis_id: Analysis tracking ID
            
        Returns:
            Formatted error response dictionary
        """
        return {
            "success": False,
            "analysis_id": analysis_id,
            "error": error_message,
            "overall_score": 0,
            "market_tier": "unknown",
            "summary": "Analysis could not be completed due to an error.",
            "structure": {
                "scores": {},
                "feedback": {},
                "metadata": {}
            },
            "appeal": {
                "scores": {},
                "feedback": {}
            }
        }