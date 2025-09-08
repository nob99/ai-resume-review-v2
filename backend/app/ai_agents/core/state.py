"""State schema for LangGraph resume analysis workflow."""

from typing import TypedDict, Optional, Dict, List, Any


class ResumeAnalysisState(TypedDict):
    """State schema for the resume analysis workflow.
    
    This state is passed between the Structure and Appeal agents,
    accumulating results as the analysis progresses.
    """
    
    # Input fields
    resume_text: str
    industry: str
    
    # Structure Agent output
    structure_scores: Optional[Dict[str, float]]
    structure_feedback: Optional[Dict[str, List[str]]]
    structure_metadata: Optional[Dict[str, Any]]
    
    # Appeal Agent output  
    appeal_scores: Optional[Dict[str, float]]
    appeal_feedback: Optional[Dict[str, List[str]]]
    market_tier: Optional[str]
    
    # Final aggregated results
    overall_score: Optional[float]
    summary: Optional[str]
    
    # Error tracking
    error: Optional[str]
    retry_count: Optional[int]