"""
AI Agents Module
================

This module contains all AI agents used in the resume analysis workflow.
Each agent is designed as a LangGraph node that processes state and returns updates.

Available Agents:
- BaseAgent: Abstract base class for all agents
- StructureAgent: Analyzes resume structure, formatting, and completeness  
- AppealAgent: Industry-specific appeal and competitiveness analysis

All agents follow the LangGraph node pattern:
- Receive AnalysisState as input
- Return Dict[str, Any] with state updates
- Handle errors gracefully with structured error responses
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_agent import BaseAgent
    from .structure_agent import StructureAgent
    from .appeal_agent import AppealAgent