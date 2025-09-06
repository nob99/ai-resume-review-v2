"""
LangGraph Resume Analysis Orchestrator
======================================

Main orchestrator for multi-agent resume analysis using LangGraph.
This class implements the complete workflow from preprocessing through
structure and appeal analysis to final results aggregation.

Workflow Architecture:
- Sequential supervisor pattern with state persistence
- Structure Agent → Appeal Agent → Results Aggregation
- Error handling and retry mechanisms at each step
- Conditional routing based on analysis results and confidence scores

Key Features:
- Complete LangGraph StateGraph implementation
- Robust error handling and recovery
- Performance monitoring and logging
- Clean interface for business logic integration
"""

import time
import asyncio
import logging
from typing import Dict, Any, Literal, Optional, List
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from app.ai.models.analysis_request import AnalysisState, CompleteAnalysisResult
from app.ai.agents.structure_agent import StructureAgent
from app.ai.agents.appeal_agent import AppealAgent
from app.ai.integrations.base_llm import BaseLLM
from app.core.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class ResumeAnalysisOrchestrator:
    """
    Main LangGraph orchestrator for multi-agent resume analysis.
    
    This class implements the complete workflow:
    START → preprocess → structure_analysis → structure_validation
    → appeal_analysis → appeal_validation → aggregate_results → END
    
    With comprehensive error handling and retry logic at each step.
    """
    
    def __init__(self, llm_client: BaseLLM):
        """
        Initialize the orchestrator with LLM client and agents.
        
        Args:
            llm_client: LLM client for AI processing
        """
        self.llm_client = llm_client
        
        # Initialize specialized agents
        self.structure_agent = StructureAgent(llm_client)
        self.appeal_agent = AppealAgent(llm_client)
        
        # Build and compile the LangGraph workflow
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
        
        # Configuration
        self.config = {
            "structure_confidence_threshold": 0.6,
            "appeal_confidence_threshold": 0.65,
            "max_retries": 2,
            "supported_industries": [
                "tech_consulting", "system_integrator", "finance_banking",
                "healthcare_pharma", "manufacturing", "general_business"
            ]
        }
        
        logger.info(f"ResumeAnalysisOrchestrator initialized with LLM: {llm_client.__class__.__name__}")
    
    def _build_workflow(self) -> StateGraph:
        """
        Build the complete LangGraph workflow for resume analysis.
        
        This is the core of our AI orchestration system. Each node is a function
        that receives state and returns state updates.
        
        Returns:
            StateGraph: Compiled workflow ready for execution
        """
        workflow = StateGraph(AnalysisState)
        
        # Add all workflow nodes
        workflow.add_node("preprocess", self.preprocess_resume)
        workflow.add_node("structure_analysis", self.run_structure_agent)
        workflow.add_node("structure_validation", self.validate_structure_results)
        workflow.add_node("appeal_analysis", self.run_appeal_agent)
        workflow.add_node("appeal_validation", self.validate_appeal_results)
        workflow.add_node("aggregate_results", self.aggregate_final_results)
        workflow.add_node("handle_error", self.handle_analysis_error)
        
        # Define workflow flow with conditional routing
        workflow.add_edge(START, "preprocess")
        
        # Preprocessing → Structure Analysis (with error handling)
        workflow.add_conditional_edges(
            "preprocess",
            self.route_after_preprocess,
            {
                "continue": "structure_analysis",
                "error": "handle_error"
            }
        )
        
        # Structure Analysis → Validation (with retry logic)
        workflow.add_conditional_edges(
            "structure_analysis",
            self.route_after_structure,
            {
                "validate": "structure_validation",
                "retry": "structure_analysis",
                "error": "handle_error"
            }
        )
        
        # Structure Validation → Appeal Analysis (with retry)
        workflow.add_conditional_edges(
            "structure_validation",
            self.route_after_structure_validation,
            {
                "continue": "appeal_analysis",
                "retry": "structure_analysis",
                "error": "handle_error"
            }
        )
        
        # Appeal Analysis → Validation
        workflow.add_conditional_edges(
            "appeal_analysis",
            self.route_after_appeal,
            {
                "validate": "appeal_validation",
                "retry": "appeal_analysis",
                "error": "handle_error"
            }
        )
        
        # Appeal Validation → Results Aggregation
        workflow.add_conditional_edges(
            "appeal_validation",
            self.route_after_appeal_validation,
            {
                "continue": "aggregate_results",
                "retry": "appeal_analysis",
                "error": "handle_error"
            }
        )
        
        # Terminal nodes
        workflow.add_edge("aggregate_results", END)
        workflow.add_edge("handle_error", END)
        
        return workflow
    
    # ========================================================================
    # LANGRAPH NODE IMPLEMENTATIONS
    # ========================================================================
    
    def preprocess_resume(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Preprocess and validate resume text before analysis.
        
        LangGraph Node Function:
        - Validates input data
        - Cleans and normalizes resume text
        - Sets up workflow metadata
        - Returns state updates for next node
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict: State updates for workflow
        """
        logger.info(f"Starting preprocessing for analysis {state['analysis_id']}")
        
        resume_text = state["resume_text"].strip()
        industry = state["industry"]
        
        # Input validation
        if not resume_text:
            return {
                "has_errors": True,
                "error_messages": ["No resume text provided for analysis"],
                "current_stage": "preprocessing"
            }
        
        if len(resume_text) < 100:
            return {
                "has_errors": True,
                "error_messages": ["Resume text too short for meaningful analysis (minimum 100 characters)"],
                "current_stage": "preprocessing"
            }
        
        if len(resume_text) > 50000:
            return {
                "has_errors": True,
                "error_messages": ["Resume text exceeds maximum length (50,000 characters)"],
                "current_stage": "preprocessing"
            }
        
        # Industry validation
        if industry not in self.config["supported_industries"]:
            return {
                "has_errors": True,
                "error_messages": [
                    f"Unsupported industry: {industry}. "
                    f"Supported: {', '.join(self.config['supported_industries'])}"
                ],
                "current_stage": "preprocessing"
            }
        
        # Text cleaning and normalization
        processed_text = self._clean_resume_text(resume_text)
        
        # Set up workflow metadata
        logger.info(f"Preprocessing completed for {state['analysis_id']}")
        return {
            "resume_text": processed_text,
            "current_stage": "preprocessing",
            "started_at": utc_now().isoformat(),
            "has_errors": False,
            "error_messages": [],
            "retry_count": 0,
            "max_retries": self.config["max_retries"],
            "structure_errors": [],
            "appeal_errors": []
        }
    
    async def run_structure_agent(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Execute structure analysis agent.
        
        LangGraph Node Function:
        - Calls StructureAgent.analyze()
        - Handles agent-specific errors
        - Returns structured analysis results
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict: State updates from structure agent
        """
        logger.info(f"Running structure analysis for {state['analysis_id']}")
        
        try:
            result = await self.structure_agent.analyze(state)
            logger.info(f"Structure analysis completed for {state['analysis_id']}")
            return result
            
        except Exception as e:
            logger.error(f"Structure agent failed for {state['analysis_id']}: {str(e)}")
            return {
                "structure_errors": [f"Structure analysis failed: {str(e)}"],
                "has_errors": True,
                "current_stage": "structure_analysis"
            }
    
    def validate_structure_results(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Validate structure analysis results for quality and completeness.
        
        LangGraph Node Function:
        - Checks analysis quality and confidence
        - Determines if retry is needed
        - Returns validation decision
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict: Validation results and routing decisions
        """
        structure_analysis = state.get("structure_analysis")
        confidence = state.get("structure_confidence", 0.0)
        
        logger.info(f"Validating structure results for {state['analysis_id']} (confidence: {confidence:.2f})")
        
        # Check if analysis was successful
        if not structure_analysis:
            return {
                "has_errors": True,
                "error_messages": ["Structure analysis produced no results"],
                "structure_errors": ["Analysis failed to complete"],
                "current_stage": "structure_validation"
            }
        
        # Confidence threshold check
        confidence_threshold = self.config["structure_confidence_threshold"]
        if confidence < confidence_threshold:
            retry_count = state.get("retry_count", 0)
            max_retries = state.get("max_retries", 2)
            
            if retry_count < max_retries:
                logger.warning(
                    f"Structure analysis confidence too low ({confidence:.2f} < {confidence_threshold}), "
                    f"retrying... (attempt {retry_count + 1}/{max_retries})"
                )
                return {
                    "structure_errors": [f"Low confidence score: {confidence:.2f}, retrying analysis"],
                    "retry_count": retry_count + 1,
                    "current_stage": "structure_validation"
                }
            else:
                logger.error(f"Structure analysis confidence still too low after {retry_count} retries")
                return {
                    "has_errors": True,
                    "error_messages": [f"Structure analysis confidence too low after {retry_count} retries"],
                    "current_stage": "structure_validation"
                }
        
        # Validate required fields exist
        if not self.structure_agent.validate_structure_result(structure_analysis):
            return {
                "structure_errors": ["Structure analysis result validation failed"],
                "has_errors": True,
                "current_stage": "structure_validation"
            }
        
        # Reset retry count for next phase
        logger.info(f"Structure validation passed for {state['analysis_id']}")
        return {
            "current_stage": "structure_validated",
            "structure_errors": [],
            "retry_count": 0  # Reset for next phase
        }
    
    async def run_appeal_agent(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Execute appeal analysis agent with structure context.
        
        LangGraph Node Function:
        - Calls AppealAgent.analyze() with structure results as context
        - Handles agent-specific errors
        - Returns industry-specific analysis results
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict: State updates from appeal agent
        """
        logger.info(f"Running appeal analysis for {state['analysis_id']} (industry: {state['industry']})")
        
        try:
            result = await self.appeal_agent.analyze(state)
            logger.info(f"Appeal analysis completed for {state['analysis_id']}")
            return result
            
        except Exception as e:
            logger.error(f"Appeal agent failed for {state['analysis_id']}: {str(e)}")
            return {
                "appeal_errors": [f"Appeal analysis failed: {str(e)}"],
                "has_errors": True,
                "current_stage": "appeal_analysis"
            }
    
    def validate_appeal_results(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Validate appeal analysis results with industry-specific checks.
        
        LangGraph Node Function:
        - Validates appeal analysis quality
        - Checks industry-specific requirements
        - Determines if retry is needed
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict: Validation results and routing decisions
        """
        appeal_analysis = state.get("appeal_analysis")
        confidence = state.get("appeal_confidence", 0.0)
        
        logger.info(f"Validating appeal results for {state['analysis_id']} (confidence: {confidence:.2f})")
        
        if not appeal_analysis:
            return {
                "has_errors": True,
                "error_messages": ["Appeal analysis produced no results"],
                "appeal_errors": ["Analysis failed to complete"],
                "current_stage": "appeal_validation"
            }
        
        # Validate result structure
        if not self.appeal_agent.validate_appeal_result(appeal_analysis):
            return {
                "appeal_errors": ["Appeal analysis result validation failed"],
                "has_errors": True,
                "current_stage": "appeal_validation"
            }
        
        # Confidence threshold check
        confidence_threshold = self.config["appeal_confidence_threshold"]
        if confidence < confidence_threshold:
            retry_count = state.get("retry_count", 0)
            max_retries = state.get("max_retries", 2)
            
            if retry_count < max_retries:
                logger.warning(
                    f"Appeal analysis confidence too low ({confidence:.2f} < {confidence_threshold}), "
                    f"retrying... (attempt {retry_count + 1}/{max_retries})"
                )
                return {
                    "appeal_errors": [f"Low confidence score: {confidence:.2f}, retrying"],
                    "retry_count": retry_count + 1,
                    "current_stage": "appeal_validation"
                }
            else:
                logger.error(f"Appeal analysis confidence still too low after {retry_count} retries")
                return {
                    "has_errors": True,
                    "error_messages": [f"Appeal analysis confidence too low after {retry_count} retries"],
                    "current_stage": "appeal_validation"
                }
        
        logger.info(f"Appeal validation passed for {state['analysis_id']}")
        return {
            "current_stage": "appeal_validated",
            "appeal_errors": []
        }
    
    def aggregate_final_results(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Combine structure and appeal analysis into comprehensive final result.
        
        LangGraph Node Function:
        - Aggregates results from both agents
        - Calculates weighted overall score
        - Generates executive summary
        - Returns complete analysis result
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict: Final aggregated results
        """
        logger.info(f"Aggregating final results for {state['analysis_id']}")
        
        structure = state["structure_analysis"]
        appeal = state["appeal_analysis"]
        
        # Calculate weighted overall score
        structure_weight = 0.35  # 35% weight for structure
        appeal_weight = 0.65     # 65% weight for industry appeal
        
        # Structure component (average of 4 core scores)
        structure_avg = (
            structure.format_score +
            structure.section_organization_score +
            structure.professional_tone_score +
            structure.completeness_score
        ) / 4
        
        # Appeal component (average of 4 core scores)
        appeal_avg = (
            appeal.achievement_relevance_score +
            appeal.skills_alignment_score +
            appeal.experience_fit_score +
            appeal.competitive_positioning_score
        ) / 4
        
        # Weighted overall score
        overall_score = (structure_weight * structure_avg) + (appeal_weight * appeal_avg)
        
        # Generate comprehensive summary and insights
        analysis_summary = self._generate_executive_summary(structure, appeal, overall_score)
        key_strengths = self._extract_key_strengths(structure, appeal)
        priority_improvements = self._extract_priority_improvements(structure, appeal)
        
        # Create confidence metrics
        confidence_metrics = {
            "structure_confidence": structure.confidence_score,
            "appeal_confidence": appeal.confidence_score,
            "overall_confidence": (structure.confidence_score + appeal.confidence_score) / 2
        }
        
        # Create comprehensive final result
        final_result = CompleteAnalysisResult(
            overall_score=round(overall_score, 2),
            structure_analysis=structure,
            appeal_analysis=appeal,
            
            analysis_summary=analysis_summary,
            key_strengths=key_strengths,
            priority_improvements=priority_improvements,
            
            industry=state["industry"],
            analysis_id=state["analysis_id"],
            completed_at=utc_now().isoformat(),
            processing_time_seconds=self._calculate_total_processing_time(state),
            confidence_metrics=confidence_metrics
        )
        
        logger.info(f"Analysis completed for {state['analysis_id']} with overall score: {overall_score:.2f}")
        
        return {
            "final_result": final_result,
            "overall_score": overall_score,
            "current_stage": "complete",
            "completed_at": utc_now().isoformat()
        }
    
    def handle_analysis_error(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Handle analysis errors with graceful degradation.
        
        LangGraph Node Function:
        - Processes workflow errors
        - Attempts to provide partial results
        - Returns error state for workflow termination
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict: Error handling results
        """
        error_messages = state.get("error_messages", [])
        current_stage = state.get("current_stage", "unknown")
        
        logger.error(f"Analysis error in stage {current_stage} for {state['analysis_id']}: {error_messages}")
        
        # Try to provide partial results if possible
        partial_result = self._create_partial_result(state)
        
        return {
            "has_errors": True,
            "error_messages": error_messages,
            "current_stage": "error",
            "final_result": partial_result,
            "completed_at": utc_now().isoformat()
        }
    
    # ========================================================================
    # CONDITIONAL ROUTING FUNCTIONS
    # ========================================================================
    
    def route_after_preprocess(self, state: AnalysisState) -> str:
        """Route after preprocessing based on validation results."""
        if state.get("has_errors"):
            return "error"
        return "continue"
    
    def route_after_structure(self, state: AnalysisState) -> str:
        """Route after structure analysis based on success/failure."""
        if state.get("structure_errors"):
            retry_count = state.get("retry_count", 0)
            max_retries = state.get("max_retries", 2)
            
            if retry_count < max_retries:
                return "retry"
            else:
                return "error"
        
        return "validate"
    
    def route_after_structure_validation(self, state: AnalysisState) -> str:
        """Route after structure validation."""
        if state.get("has_errors"):
            return "error"
        
        if state.get("structure_errors"):
            retry_count = state.get("retry_count", 0)
            max_retries = state.get("max_retries", 2)
            
            if retry_count < max_retries:
                return "retry"
            else:
                return "error"
        
        return "continue"
    
    def route_after_appeal(self, state: AnalysisState) -> str:
        """Route after appeal analysis."""
        if state.get("appeal_errors"):
            retry_count = state.get("retry_count", 0)
            max_retries = state.get("max_retries", 2)
            
            if retry_count < max_retries:
                return "retry"
            else:
                return "error"
        
        return "validate"
    
    def route_after_appeal_validation(self, state: AnalysisState) -> str:
        """Route after appeal validation."""
        if state.get("has_errors"):
            return "error"
        
        if state.get("appeal_errors"):
            retry_count = state.get("retry_count", 0)
            max_retries = state.get("max_retries", 2)
            
            if retry_count < max_retries:
                return "retry"
            else:
                return "error"
        
        return "continue"
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _clean_resume_text(self, text: str) -> str:
        """Clean and normalize resume text for analysis."""
        import re
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere with LLM processing
        text = re.sub(r'[^\w\s\-\.\,\;\:\!\?\(\)\/\@\#\&\*\+\=\[\]\_\{\}\|\~\`\'\"]', '', text)
        
        return text.strip()
    
    def _generate_executive_summary(
        self,
        structure: "StructureAnalysisResult",
        appeal: "AppealAnalysisResult",
        overall_score: float
    ) -> str:
        """Generate executive summary of the analysis."""
        score_tier = (
            "excellent" if overall_score >= 85
            else "strong" if overall_score >= 70
            else "moderate" if overall_score >= 55
            else "needs improvement"
        )
        
        industry_display = appeal.target_industry.replace('_', ' ').title()
        
        return (
            f"This resume demonstrates {score_tier} quality with an overall score of {overall_score:.1f}/100. "
            f"Structurally, the resume shows strengths in {', '.join(structure.strengths[:2]) if structure.strengths else 'basic formatting'}. "
            f"For the {industry_display} industry, the candidate shows {appeal.market_tier}-level positioning "
            f"with notable achievements in {', '.join(appeal.relevant_achievements[:2]) if appeal.relevant_achievements else 'their experience'}."
        )
    
    def _extract_key_strengths(
        self,
        structure: "StructureAnalysisResult",
        appeal: "AppealAnalysisResult"
    ) -> List[str]:
        """Extract top strengths from both analyses."""
        strengths = []
        
        # Add top structure strengths
        strengths.extend(structure.strengths[:2])
        
        # Add top appeal strengths
        strengths.extend(appeal.competitive_advantages[:2])
        
        # Add one more from either if we don't have enough
        if len(strengths) < 3:
            if len(structure.strengths) > 2:
                strengths.append(structure.strengths[2])
            elif len(appeal.competitive_advantages) > 2:
                strengths.append(appeal.competitive_advantages[2])
        
        return strengths[:5]  # Return top 5
    
    def _extract_priority_improvements(
        self,
        structure: "StructureAnalysisResult",
        appeal: "AppealAnalysisResult"
    ) -> List[str]:
        """Extract priority improvement areas."""
        improvements = []
        
        # Add top structure recommendations
        improvements.extend(structure.recommendations[:2])
        
        # Add top appeal improvements
        improvements.extend(appeal.improvement_areas[:2])
        
        # Add one more if we don't have enough
        if len(improvements) < 3:
            if len(structure.recommendations) > 2:
                improvements.append(structure.recommendations[2])
            elif len(appeal.improvement_areas) > 2:
                improvements.append(appeal.improvement_areas[2])
        
        return improvements[:5]  # Return top 5
    
    def _calculate_total_processing_time(self, state: AnalysisState) -> float:
        """Calculate total processing time for the analysis."""
        if state.get("started_at"):
            from datetime import datetime
            started = datetime.fromisoformat(state["started_at"])
            now = utc_now()
            return (now - started).total_seconds()
        return 0.0
    
    def _create_partial_result(self, state: AnalysisState) -> Optional[CompleteAnalysisResult]:
        """Create partial result when analysis fails."""
        # If we have structure analysis but not appeal, create partial result
        structure_analysis = state.get("structure_analysis")
        if structure_analysis:
            # Create minimal appeal result for partial completion
            from app.ai.models.analysis_request import AppealAnalysisResult
            
            minimal_appeal = AppealAnalysisResult(
                achievement_relevance_score=70.0,
                skills_alignment_score=70.0,
                experience_fit_score=70.0,
                competitive_positioning_score=70.0,
                
                relevant_achievements=["Analysis incomplete"],
                missing_skills=["Analysis incomplete"],
                transferable_experience=["Analysis incomplete"],
                industry_keywords=[],
                
                market_tier="mid",
                competitive_advantages=["Analysis incomplete"],
                improvement_areas=["Complete analysis was not possible"],
                
                structure_context_used=True,
                target_industry=state["industry"],
                
                confidence_score=0.3,
                processing_time_ms=0,
                model_used="partial",
                prompt_version="error_fallback"
            )
            
            # Calculate partial overall score (structure only)
            structure_avg = (
                structure_analysis.format_score +
                structure_analysis.section_organization_score +
                structure_analysis.professional_tone_score +
                structure_analysis.completeness_score
            ) / 4
            
            return CompleteAnalysisResult(
                overall_score=round(structure_avg * 0.7, 2),  # Reduce score due to incomplete analysis
                structure_analysis=structure_analysis,
                appeal_analysis=minimal_appeal,
                
                analysis_summary="Analysis was partially completed due to processing errors.",
                key_strengths=structure_analysis.strengths[:3],
                priority_improvements=[
                    "Complete analysis was not possible - please retry",
                    *structure_analysis.recommendations[:2]
                ],
                
                industry=state["industry"],
                analysis_id=state["analysis_id"],
                completed_at=utc_now().isoformat(),
                processing_time_seconds=self._calculate_total_processing_time(state),
                confidence_metrics={
                    "structure_confidence": structure_analysis.confidence_score,
                    "appeal_confidence": 0.0,
                    "overall_confidence": structure_analysis.confidence_score * 0.5
                }
            )
        
        return None
    
    # ========================================================================
    # PUBLIC INTERFACE
    # ========================================================================
    
    async def analyze_resume(
        self,
        resume_text: str,
        industry: str,
        analysis_id: str,
        user_id: str
    ) -> CompleteAnalysisResult:
        """
        High-level interface for complete resume analysis.
        
        Args:
            resume_text: Resume text to analyze
            industry: Target industry for analysis
            analysis_id: Unique identifier for this analysis
            user_id: User requesting the analysis
            
        Returns:
            CompleteAnalysisResult: Complete analysis results
            
        Raises:
            ValueError: When input validation fails
            Exception: When analysis fails completely
        """
        # Initialize workflow state
        initial_state = AnalysisState(
            resume_text=resume_text,
            industry=industry,
            analysis_id=analysis_id,
            user_id=user_id,
            current_stage="preprocessing",
            has_errors=False,
            error_messages=[],
            retry_count=0,
            structure_errors=[],
            appeal_errors=[],
            structure_analysis=None,
            structure_confidence=None,
            appeal_analysis=None,
            appeal_confidence=None,
            final_result=None,
            overall_score=None,
            max_retries=self.config["max_retries"],
            started_at=None,
            completed_at=None,
            processing_time_seconds=None
        )
        
        try:
            # Execute complete LangGraph workflow
            logger.info(f"Starting complete analysis workflow for {analysis_id}")
            result = await self.app.ainvoke(initial_state)
            
            # Handle results or errors
            if result.get("has_errors"):
                error_msg = f"Analysis failed: {result.get('error_messages', [])}"
                logger.error(f"Analysis {analysis_id} failed: {error_msg}")
                
                # Return partial result if available
                if result.get("final_result"):
                    return result["final_result"]
                else:
                    raise Exception(error_msg)
            
            final_result = result["final_result"]
            if not final_result:
                raise Exception("Analysis completed but produced no results")
            
            logger.info(f"Analysis {analysis_id} completed successfully with score {final_result.overall_score}")
            return final_result
            
        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed with exception: {str(e)}")
            raise Exception(f"Resume analysis failed: {str(e)}")
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the workflow configuration."""
        return {
            "workflow_nodes": [
                "preprocess", "structure_analysis", "structure_validation",
                "appeal_analysis", "appeal_validation", "aggregate_results", "handle_error"
            ],
            "supported_industries": self.config["supported_industries"],
            "confidence_thresholds": {
                "structure": self.config["structure_confidence_threshold"],
                "appeal": self.config["appeal_confidence_threshold"]
            },
            "max_retries": self.config["max_retries"],
            "agents": {
                "structure": self.structure_agent.get_agent_info(),
                "appeal": self.appeal_agent.get_agent_info()
            },
            "llm_info": self.llm_client.get_usage_stats()
        }
    
    async def validate_setup(self) -> bool:
        """
        Validate that the orchestrator is properly set up.
        
        Returns:
            bool: True if setup is valid, False otherwise
        """
        try:
            # Test LLM connection
            if not await self.llm_client.validate_connection():
                logger.error("LLM connection validation failed")
                return False
            
            # Test workflow compilation
            if not self.app:
                logger.error("Workflow compilation failed")
                return False
            
            # Test agents
            if not self.structure_agent or not self.appeal_agent:
                logger.error("Agents not properly initialized")
                return False
            
            logger.info("Orchestrator setup validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Setup validation failed: {str(e)}")
            return False