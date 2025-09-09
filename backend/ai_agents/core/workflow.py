"""LangGraph workflow for resume analysis."""

from langgraph.graph import StateGraph, END
from typing import TYPE_CHECKING, Any

from .state import ResumeAnalysisState

if TYPE_CHECKING:
    from ..agents.structure import StructureAgent
    from ..agents.appeal import AppealAgent


def create_workflow(
    structure_agent: "StructureAgent",
    appeal_agent: "AppealAgent"
) -> Any:
    """Create the two-agent resume analysis workflow.
    
    Args:
        structure_agent: Agent for analyzing resume structure
        appeal_agent: Agent for analyzing industry-specific appeal
        
    Returns:
        Compiled LangGraph workflow
    """
    
    # Create workflow with our state schema
    workflow = StateGraph(ResumeAnalysisState)
    
    # Add nodes (just 2 agents!)
    workflow.add_node("structure", structure_agent.analyze)
    workflow.add_node("appeal", appeal_agent.analyze)
    
    # Define the flow: structure → appeal → end
    workflow.set_entry_point("structure")
    workflow.add_edge("structure", "appeal")
    workflow.add_edge("appeal", END)
    
    # Compile and return the workflow
    return workflow.compile()