# AI Orchestration Architecture - Sprint 004
## LangGraph Multi-Agent Resume Analysis System

**Document Version**: 1.0  
**Created**: September 4, 2025  
**Sprint**: 004  
**Architecture Pattern**: Sequential Supervisor with State Persistence

---

## 🎯 Overview

This document provides detailed technical specifications for implementing LangGraph-based AI orchestration in Sprint 004. The architecture enables sophisticated multi-agent resume analysis workflows while maintaining clean separation from business logic and simple deployment characteristics.

## 🏗️ Core Architecture Principles

### **1. Clean Separation of Concerns**
- **Business Logic Layer** (`/services/`) handles user requests, file processing, data persistence
- **AI Module** (`/ai/`) handles all AI processing, agent orchestration, LLM integration
- **Clear Interface Contract** between layers prevents tight coupling

### **2. LangGraph Workflow Orchestration**  
- **State-Driven Processing** with persistent workflow state
- **Sequential Agent Execution** with context passing
- **Conditional Routing** based on analysis results and error conditions
- **Error Recovery** with retry mechanisms and graceful degradation

### **3. Modular Agent Design**
- **Specialized Agents** for different analysis aspects
- **Reusable Components** with standardized interfaces
- **Industry-Specific Logic** through configurable prompts
- **Testable Isolation** for each agent and workflow component

---

## 🔄 LangGraph Workflow Design

### **Workflow State Schema**

```python
from typing import TypedDict, Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field

class AnalysisState(TypedDict):
    # Input Data
    resume_text: str
    industry: str  # tech_consulting, system_integrator, etc.
    analysis_id: str
    user_id: str
    
    # Workflow Control
    current_stage: Literal[
        "preprocessing", 
        "structure_analysis", 
        "structure_validation",
        "appeal_analysis", 
        "appeal_validation",
        "aggregation", 
        "complete", 
        "error"
    ]
    
    # Agent Results
    structure_analysis: Optional[StructureAnalysisResult]
    structure_confidence: Optional[float]
    structure_errors: List[str]
    
    appeal_analysis: Optional[AppealAnalysisResult]  
    appeal_confidence: Optional[float]
    appeal_errors: List[str]
    
    # Final Output
    final_result: Optional[CompleteAnalysisResult]
    overall_score: Optional[float]
    
    # Error Handling & Recovery
    has_errors: bool
    error_messages: List[str]
    retry_count: int
    max_retries: int
    
    # Metadata
    started_at: Optional[str]
    completed_at: Optional[str]
    processing_time_seconds: Optional[float]
```

### **LangGraph Workflow Definition**

```python
# /app/ai/orchestrator.py
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Dict, Any, Literal

class ResumeAnalysisOrchestrator:
    def __init__(self, llm_client: BaseLLM):
        self.llm_client = llm_client
        self.structure_agent = StructureAgent(llm_client)
        self.appeal_agent = AppealAgent(llm_client)
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    def _build_workflow(self) -> StateGraph:
        """Build the complete LangGraph workflow for resume analysis"""
        workflow = StateGraph(AnalysisState)
        
        # Add all workflow nodes
        workflow.add_node("preprocess", self.preprocess_resume)
        workflow.add_node("structure_analysis", self.run_structure_agent)
        workflow.add_node("structure_validation", self.validate_structure_results)
        workflow.add_node("appeal_analysis", self.run_appeal_agent)
        workflow.add_node("appeal_validation", self.validate_appeal_results)
        workflow.add_node("aggregate_results", self.aggregate_final_results)
        workflow.add_node("handle_error", self.handle_analysis_error)
        
        # Define workflow edges and routing
        workflow.add_edge(START, "preprocess")
        
        # Preprocessing → Structure Analysis
        workflow.add_conditional_edges(
            "preprocess",
            self.route_after_preprocess,
            {
                "continue": "structure_analysis",
                "error": "handle_error"
            }
        )
        
        # Structure Analysis → Validation
        workflow.add_conditional_edges(
            "structure_analysis", 
            self.route_after_structure,
            {
                "validate": "structure_validation",
                "retry": "structure_analysis",
                "error": "handle_error"
            }
        )
        
        # Structure Validation → Appeal Analysis
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
        
        # Final nodes to END
        workflow.add_edge("aggregate_results", END)
        workflow.add_edge("handle_error", END)
        
        return workflow
```

---

## 🧠 Agent Implementation Architecture

### **Base Agent Interface**

```python
# /app/ai/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel

class BaseAnalysisResult(BaseModel):
    """Base class for all agent analysis results"""
    confidence_score: float = Field(ge=0.0, le=1.0)
    processing_time_ms: int
    model_used: str
    prompt_version: str
    
class BaseAgent(ABC):
    def __init__(self, llm_client: BaseLLM):
        self.llm = llm_client
        self.prompt_manager = PromptManager()
        
    @abstractmethod
    async def analyze(self, state: AnalysisState) -> Dict[str, Any]:
        """Main analysis method that returns state updates"""
        pass
        
    def _calculate_confidence(self, raw_output: str) -> float:
        """Calculate confidence score based on output quality indicators"""
        # Implementation for confidence scoring
        pass
        
    def _handle_agent_error(self, error: Exception, state: AnalysisState) -> Dict[str, Any]:
        """Standardized error handling for agents"""
        return {
            "has_errors": True,
            "error_messages": [f"{self.__class__.__name__}: {str(error)}"],
            "retry_count": state.get("retry_count", 0) + 1
        }
```

### **Structure Agent Implementation**

```python
# /app/ai/agents/structure_agent.py
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class StructureAnalysisResult(BaseAnalysisResult):
    # Core Scoring (0-100 scale)
    format_score: float = Field(description="Resume formatting quality")
    section_organization_score: float = Field(description="Section organization quality")
    professional_tone_score: float = Field(description="Professional tone assessment")
    completeness_score: float = Field(description="Information completeness")
    
    # Detailed Analysis
    formatting_issues: List[str] = Field(description="Specific formatting problems")
    missing_sections: List[str] = Field(description="Expected sections not found")
    tone_problems: List[str] = Field(description="Unprofessional language instances")
    completeness_gaps: List[str] = Field(description="Missing critical information")
    
    # Strengths & Recommendations
    strengths: List[str] = Field(description="Well-executed structural elements")
    recommendations: List[str] = Field(description="Specific improvement suggestions")
    
    # Metadata
    total_sections_found: int
    word_count: int
    estimated_reading_time_minutes: int

class StructureAgent(BaseAgent):
    async def analyze(self, state: AnalysisState) -> Dict[str, Any]:
        """Analyze resume structure, formatting, and completeness"""
        start_time = time.time()
        
        try:
            # Load structure analysis prompt
            prompt = self.prompt_manager.get_prompt(
                agent_type="structure",
                industry="general"  # Structure analysis is industry-agnostic
            )
            
            # Prepare analysis context
            analysis_context = {
                "resume_text": state["resume_text"],
                "analysis_id": state["analysis_id"],
                "word_count": len(state["resume_text"].split())
            }
            
            # Execute LLM analysis
            formatted_prompt = prompt.format(**analysis_context)
            raw_result = await self.llm.ainvoke(formatted_prompt)
            
            # Parse structured output
            structured_result = self._parse_structure_output(raw_result.content)
            
            # Calculate confidence based on output quality
            confidence = self._calculate_structure_confidence(structured_result)
            
            # Return state updates
            return {
                "structure_analysis": structured_result,
                "structure_confidence": confidence,
                "current_stage": "structure_analysis",
                "structure_errors": []
            }
            
        except Exception as e:
            return self._handle_agent_error(e, state)
    
    def _parse_structure_output(self, raw_output: str) -> StructureAnalysisResult:
        """Parse LLM output into structured result"""
        # Implementation using structured output parsing
        # Could use Pydantic with LLM structured output or custom parsing
        pass
        
    def _calculate_structure_confidence(self, result: StructureAnalysisResult) -> float:
        """Calculate confidence based on analysis completeness and consistency"""
        # Implementation for structure-specific confidence calculation
        pass
```

### **Appeal Agent Implementation**

```python
# /app/ai/agents/appeal_agent.py
from typing import Dict, List, Literal

class AppealAnalysisResult(BaseAnalysisResult):
    # Core Industry Scoring (0-100 scale)
    achievement_relevance_score: float = Field(description="Industry-relevant achievements")
    skills_alignment_score: float = Field(description="Skills match for industry")
    experience_fit_score: float = Field(description="Experience relevance")
    competitive_positioning_score: float = Field(description="Market competitiveness")
    
    # Detailed Industry Analysis
    relevant_achievements: List[str] = Field(description="Standout achievements for industry")
    missing_skills: List[str] = Field(description="Critical skills gaps")
    transferable_experience: List[str] = Field(description="Cross-industry experience value")
    industry_keywords: List[str] = Field(description="Industry-specific terms found")
    
    # Competitive Assessment
    market_tier: Literal["entry", "mid", "senior", "executive"] = Field(description="Market level assessment")
    competitive_advantage: List[str] = Field(description="Unique selling points")
    areas_for_improvement: List[str] = Field(description="Enhancement opportunities")
    
    # Context from Structure Agent
    structure_context_used: bool = Field(description="Whether structure analysis informed appeal analysis")
    
class AppealAgent(BaseAgent):
    async def analyze(self, state: AnalysisState) -> Dict[str, Any]:
        """Perform industry-specific appeal analysis with structure context"""
        start_time = time.time()
        
        try:
            # Get industry-specific prompt
            prompt = self.prompt_manager.get_prompt(
                agent_type="appeal",
                industry=state["industry"]
            )
            
            # Include context from structure analysis
            structure_context = state.get("structure_analysis")
            structure_strengths = structure_context.strengths if structure_context else []
            
            analysis_context = {
                "resume_text": state["resume_text"],
                "industry": state["industry"],
                "analysis_id": state["analysis_id"],
                "structure_strengths": structure_strengths,
                "structure_recommendations": structure_context.recommendations if structure_context else []
            }
            
            # Execute industry-specific LLM analysis
            formatted_prompt = prompt.format(**analysis_context)
            raw_result = await self.llm.ainvoke(formatted_prompt)
            
            # Parse structured output
            structured_result = self._parse_appeal_output(raw_result.content, state["industry"])
            
            # Calculate confidence
            confidence = self._calculate_appeal_confidence(structured_result)
            
            return {
                "appeal_analysis": structured_result,
                "appeal_confidence": confidence,
                "current_stage": "appeal_analysis", 
                "appeal_errors": []
            }
            
        except Exception as e:
            return self._handle_agent_error(e, state)
    
    def _parse_appeal_output(self, raw_output: str, industry: str) -> AppealAnalysisResult:
        """Parse LLM output with industry-specific validation"""
        # Implementation with industry-specific parsing logic
        pass
```

---

## 🛤️ Workflow Node Implementations

### **Preprocessing Node**

```python
def preprocess_resume(self, state: AnalysisState) -> Dict[str, Any]:
    """Preprocess and validate resume text before analysis"""
    resume_text = state["resume_text"].strip()
    
    # Validation checks
    if len(resume_text) < 100:
        return {
            "has_errors": True,
            "error_messages": ["Resume text too short for meaningful analysis"],
            "current_stage": "preprocessing"
        }
    
    if len(resume_text) > 50000:  # Very large resume
        return {
            "has_errors": True,
            "error_messages": ["Resume text exceeds maximum length for analysis"],
            "current_stage": "preprocessing"
        }
    
    # Text cleaning and normalization
    processed_text = self._clean_resume_text(resume_text)
    
    return {
        "resume_text": processed_text,
        "current_stage": "preprocessing",
        "started_at": datetime.utcnow().isoformat(),
        "has_errors": False,
        "max_retries": 2
    }

def _clean_resume_text(self, text: str) -> str:
    """Clean and normalize resume text"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters that might interfere with LLM processing
    text = re.sub(r'[^\w\s\-\.\,\;\:\!\?\(\)\/\@]', '', text)
    return text.strip()
```

### **Validation Nodes**

```python
def validate_structure_results(self, state: AnalysisState) -> Dict[str, Any]:
    """Validate structure analysis results for quality and completeness"""
    structure_analysis = state.get("structure_analysis")
    confidence = state.get("structure_confidence", 0.0)
    
    # Check if analysis was successful
    if not structure_analysis:
        return {
            "has_errors": True,
            "error_messages": ["Structure analysis produced no results"],
            "structure_errors": ["Analysis failed to complete"]
        }
    
    # Confidence threshold check
    if confidence < 0.6:
        retry_count = state.get("retry_count", 0)
        if retry_count < state.get("max_retries", 2):
            return {
                "structure_errors": [f"Low confidence score: {confidence:.2f}"],
                "retry_count": retry_count + 1,
                "current_stage": "structure_validation"
            }
        else:
            return {
                "has_errors": True,
                "error_messages": [f"Structure analysis confidence too low after {retry_count} retries"],
                "current_stage": "structure_validation"
            }
    
    # Validate required fields
    required_scores = ['format_score', 'section_organization_score', 'professional_tone_score', 'completeness_score']
    missing_scores = [score for score in required_scores if not hasattr(structure_analysis, score)]
    
    if missing_scores:
        return {
            "structure_errors": [f"Missing required scores: {', '.join(missing_scores)}"],
            "has_errors": True,
            "current_stage": "structure_validation"
        }
    
    # Validation passed
    return {
        "current_stage": "structure_validated",
        "structure_errors": []
    }

def validate_appeal_results(self, state: AnalysisState) -> Dict[str, Any]:
    """Validate appeal analysis results with industry-specific checks"""
    appeal_analysis = state.get("appeal_analysis")
    confidence = state.get("appeal_confidence", 0.0)
    
    if not appeal_analysis:
        return {
            "has_errors": True,
            "error_messages": ["Appeal analysis produced no results"],
            "appeal_errors": ["Analysis failed to complete"]
        }
    
    # Industry-specific validation
    industry = state["industry"]
    if not self._validate_industry_analysis(appeal_analysis, industry):
        retry_count = state.get("retry_count", 0)
        if retry_count < state.get("max_retries", 2):
            return {
                "appeal_errors": [f"Industry analysis incomplete for {industry}"],
                "retry_count": retry_count + 1,
                "current_stage": "appeal_validation"
            }
    
    return {
        "current_stage": "appeal_validated",
        "appeal_errors": []
    }
```

### **Results Aggregation Node**

```python
def aggregate_final_results(self, state: AnalysisState) -> Dict[str, Any]:
    """Combine structure and appeal analysis into comprehensive final result"""
    structure = state["structure_analysis"]
    appeal = state["appeal_analysis"]
    
    # Calculate weighted overall score
    structure_weight = 0.35  # 35% for structure
    appeal_weight = 0.65     # 65% for industry appeal
    
    # Structure component (average of 4 scores)
    structure_avg = (
        structure.format_score +
        structure.section_organization_score +
        structure.professional_tone_score +
        structure.completeness_score
    ) / 4
    
    # Appeal component (average of 4 scores)
    appeal_avg = (
        appeal.achievement_relevance_score +
        appeal.skills_alignment_score +
        appeal.experience_fit_score +
        appeal.competitive_positioning_score
    ) / 4
    
    # Weighted overall score
    overall_score = (structure_weight * structure_avg) + (appeal_weight * appeal_avg)
    
    # Create comprehensive final result
    final_result = CompleteAnalysisResult(
        overall_score=round(overall_score, 2),
        structure_analysis=structure,
        appeal_analysis=appeal,
        analysis_summary=self._generate_summary(structure, appeal, overall_score),
        industry=state["industry"],
        analysis_id=state["analysis_id"],
        completed_at=datetime.utcnow().isoformat(),
        processing_time_seconds=self._calculate_processing_time(state)
    )
    
    return {
        "final_result": final_result,
        "overall_score": overall_score,
        "current_stage": "complete",
        "completed_at": datetime.utcnow().isoformat()
    }

def _generate_summary(self, structure: StructureAnalysisResult, appeal: AppealAnalysisResult, score: float) -> str:
    """Generate executive summary of analysis"""
    # Implementation for generating comprehensive summary
    pass
```

---

## 🔀 Routing Logic Implementation

### **Conditional Edge Functions**

```python
def route_after_preprocess(self, state: AnalysisState) -> str:
    """Route after preprocessing based on validation results"""
    if state.get("has_errors"):
        return "error"
    return "continue"

def route_after_structure(self, state: AnalysisState) -> str:
    """Route after structure analysis based on success/failure"""
    if state.get("structure_errors"):
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        
        if retry_count < max_retries:
            return "retry"
        else:
            return "error"
    
    return "validate"

def route_after_structure_validation(self, state: AnalysisState) -> str:
    """Route after structure validation"""
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
    """Route after appeal analysis"""
    if state.get("appeal_errors"):
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        
        if retry_count < max_retries:
            return "retry"
        else:
            return "error"
    
    return "validate"

def route_after_appeal_validation(self, state: AnalysisState) -> str:
    """Route after appeal validation"""
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
```

---

## 🔌 Business Logic Integration

### **Clean Interface Implementation**

```python
# /app/services/analysis_service.py
from app.ai.orchestrator import ResumeAnalysisOrchestrator
from app.ai.models.analysis_result import CompleteAnalysisResult
from app.core.config import get_settings

class AnalysisService:
    def __init__(self):
        settings = get_settings()
        llm_client = self._create_llm_client(settings)
        self.ai_orchestrator = ResumeAnalysisOrchestrator(llm_client)
        
    async def analyze_resume(
        self, 
        resume_text: str, 
        industry: str,
        analysis_id: str,
        user_id: str
    ) -> CompleteAnalysisResult:
        """Main business logic interface for resume analysis"""
        
        # Business logic: logging, validation, monitoring
        logger.info(f"Starting analysis {analysis_id} for user {user_id}, industry: {industry}")
        
        # Initialize LangGraph workflow state
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
            appeal_errors=[]
        )
        
        try:
            # Execute LangGraph workflow
            result = await self.ai_orchestrator.app.ainvoke(initial_state)
            
            # Business logic: handle results or errors
            if result.get("has_errors"):
                error_msg = f"Analysis failed: {result.get('error_messages', [])}"
                logger.error(f"Analysis {analysis_id} failed: {error_msg}")
                raise AnalysisException(error_msg)
            
            final_result = result["final_result"]
            logger.info(f"Analysis {analysis_id} completed successfully with score {final_result.overall_score}")
            
            # Business logic: store results, update database, send notifications
            await self._store_analysis_result(final_result)
            
            return final_result
            
        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed with exception: {str(e)}")
            raise AnalysisException(f"Resume analysis failed: {str(e)}")
    
    def _create_llm_client(self, settings) -> BaseLLM:
        """Create appropriate LLM client based on configuration"""
        # Implementation for LLM client creation
        pass
        
    async def _store_analysis_result(self, result: CompleteAnalysisResult):
        """Store analysis results in database (business logic)"""
        # Implementation for result persistence
        pass
```

---

## 🧪 Testing Strategy

### **Unit Testing for LangGraph Components**

```python
# /tests/unit/ai/test_orchestrator.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.ai.orchestrator import ResumeAnalysisOrchestrator
from app.ai.models.analysis_request import AnalysisState

class TestResumeAnalysisOrchestrator:
    @pytest.fixture
    def orchestrator(self):
        mock_llm = AsyncMock()
        return ResumeAnalysisOrchestrator(mock_llm)
    
    @pytest.fixture
    def sample_state(self):
        return AnalysisState(
            resume_text="Sample resume text for testing...",
            industry="tech_consulting",
            analysis_id="test-123",
            user_id="user-456",
            current_stage="preprocessing",
            has_errors=False,
            error_messages=[],
            retry_count=0
        )
    
    async def test_preprocess_resume_success(self, orchestrator, sample_state):
        """Test successful resume preprocessing"""
        result = orchestrator.preprocess_resume(sample_state)
        
        assert result["has_errors"] is False
        assert result["current_stage"] == "preprocessing"
        assert "started_at" in result
        
    async def test_preprocess_resume_too_short(self, orchestrator):
        """Test preprocessing with too short resume"""
        short_state = AnalysisState(resume_text="Too short", ...)
        result = orchestrator.preprocess_resume(short_state)
        
        assert result["has_errors"] is True
        assert "too short" in result["error_messages"][0].lower()
    
    async def test_workflow_routing(self, orchestrator, sample_state):
        """Test conditional routing logic"""
        # Test successful routing
        route = orchestrator.route_after_preprocess(sample_state)
        assert route == "continue"
        
        # Test error routing
        error_state = {**sample_state, "has_errors": True}
        route = orchestrator.route_after_preprocess(error_state)
        assert route == "error"
```

### **Integration Testing for Complete Workflow**

```python
# /tests/integration/test_ai_workflow.py
import pytest
from app.ai.orchestrator import ResumeAnalysisOrchestrator
from app.ai.integrations.openai_client import OpenAIClient

class TestCompleteAIWorkflow:
    @pytest.fixture
    def real_orchestrator(self):
        """Create orchestrator with real LLM client for integration testing"""
        llm_client = OpenAIClient(api_key="test-key")  # Use test API key
        return ResumeAnalysisOrchestrator(llm_client)
    
    @pytest.fixture  
    def sample_resume_text(self):
        return """
        John Smith
        Software Engineer
        
        Experience:
        - 3 years at Tech Company developing web applications
        - Led team of 5 developers on React project
        
        Education:
        - BS Computer Science, University of Technology
        
        Skills: React, Python, AWS, SQL
        """
    
    async def test_end_to_end_analysis(self, real_orchestrator, sample_resume_text):
        """Test complete workflow from start to finish"""
        initial_state = AnalysisState(
            resume_text=sample_resume_text,
            industry="tech_consulting", 
            analysis_id="integration-test-1",
            user_id="test-user",
            current_stage="preprocessing",
            has_errors=False,
            error_messages=[],
            retry_count=0
        )
        
        # Execute complete workflow
        result = await real_orchestrator.app.ainvoke(initial_state)
        
        # Verify successful completion
        assert result["current_stage"] == "complete"
        assert result["has_errors"] is False
        assert result["final_result"] is not None
        assert result["overall_score"] > 0
        
        final_result = result["final_result"]
        assert final_result.structure_analysis is not None
        assert final_result.appeal_analysis is not None
        assert final_result.industry == "tech_consulting"
```

---

## 📊 Monitoring & Observability

### **LangGraph State Monitoring**

```python
# /app/ai/monitoring.py
import logging
from typing import Dict, Any
from datetime import datetime

class WorkflowMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def log_state_transition(self, from_stage: str, to_stage: str, state: AnalysisState):
        """Log workflow state transitions for monitoring"""
        self.logger.info(
            f"Workflow {state['analysis_id']} transition: {from_stage} -> {to_stage}",
            extra={
                "analysis_id": state["analysis_id"],
                "user_id": state["user_id"], 
                "from_stage": from_stage,
                "to_stage": to_stage,
                "retry_count": state.get("retry_count", 0),
                "has_errors": state.get("has_errors", False)
            }
        )
    
    def log_agent_performance(self, agent_name: str, confidence: float, processing_time: float):
        """Log individual agent performance metrics"""
        self.logger.info(
            f"Agent {agent_name} completed",
            extra={
                "agent_name": agent_name,
                "confidence_score": confidence,
                "processing_time_ms": processing_time * 1000,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_workflow_error(self, error: Exception, state: AnalysisState):
        """Log workflow errors with context"""
        self.logger.error(
            f"Workflow error in {state['analysis_id']}",
            extra={
                "analysis_id": state["analysis_id"],
                "current_stage": state["current_stage"],
                "error_type": type(error).__name__,
                "error_message": str(error),
                "retry_count": state.get("retry_count", 0)
            },
            exc_info=True
        )
```

### **Performance Metrics Collection**

```python
# /app/ai/metrics.py
from dataclasses import dataclass
from typing import Dict, List
import time

@dataclass
class WorkflowMetrics:
    analysis_id: str
    total_duration_seconds: float
    structure_agent_duration_seconds: float  
    appeal_agent_duration_seconds: float
    preprocessing_duration_seconds: float
    aggregation_duration_seconds: float
    retry_count: int
    final_confidence_score: float

class MetricsCollector:
    def __init__(self):
        self.metrics: Dict[str, WorkflowMetrics] = {}
        self.stage_timers: Dict[str, float] = {}
    
    def start_stage_timer(self, analysis_id: str, stage: str):
        """Start timing a workflow stage"""
        key = f"{analysis_id}_{stage}"
        self.stage_timers[key] = time.time()
    
    def end_stage_timer(self, analysis_id: str, stage: str) -> float:
        """End timing a workflow stage and return duration"""
        key = f"{analysis_id}_{stage}"
        start_time = self.stage_timers.get(key)
        if start_time:
            duration = time.time() - start_time
            del self.stage_timers[key]
            return duration
        return 0.0
    
    def record_workflow_completion(self, analysis_id: str, final_state: AnalysisState):
        """Record complete workflow metrics"""
        # Implementation for metrics collection and storage
        pass
```

---

## 🚀 Deployment & Configuration

### **Environment Configuration**

```python
# /app/core/config.py additions for AI module
class Settings(BaseSettings):
    # ... existing settings ...
    
    # LangGraph Configuration
    LANGGRAPH_WORKFLOW_TIMEOUT_SECONDS: int = 300
    LANGGRAPH_MAX_RETRIES: int = 2
    LANGGRAPH_ENABLE_CHECKPOINTS: bool = True
    
    # AI Agent Configuration  
    STRUCTURE_AGENT_CONFIDENCE_THRESHOLD: float = 0.6
    APPEAL_AGENT_CONFIDENCE_THRESHOLD: float = 0.65
    
    # LLM Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL_NAME: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 4000
    OPENAI_TEMPERATURE: float = 0.3
    
    # Monitoring
    ENABLE_AI_MONITORING: bool = True
    AI_METRICS_COLLECTION_ENABLED: bool = True
```

### **Dependencies & Installation**

```python
# requirements.txt additions
langgraph>=0.2.0
langchain>=0.2.0
langchain-openai>=0.1.0
pydantic>=2.0.0
tiktoken>=0.7.0

# For development/testing
pytest-asyncio>=0.23.0
```

---

## 📋 Implementation Checklist

### **Week 1: Foundation (Days 1-3)**
- [ ] Install and configure LangGraph dependencies
- [ ] Create `AnalysisState` TypedDict schema
- [ ] Implement basic `ResumeAnalysisOrchestrator` class
- [ ] Create `BaseAgent` abstract class
- [ ] Build basic StateGraph with START/END nodes
- [ ] Implement preprocessing node with validation

### **Week 2: Agent Implementation (Days 4-6)**  
- [ ] Implement `StructureAgent` with LangGraph node wrapper
- [ ] Create structured output parsing with Pydantic models
- [ ] Add conditional routing logic for structure analysis
- [ ] Implement `AppealAgent` with industry-specific logic
- [ ] Add context passing from structure to appeal agent
- [ ] Test sequential agent execution

### **Week 3: Integration (Days 7-8)**
- [ ] Complete error handling and retry mechanisms
- [ ] Implement results aggregation node
- [ ] Add comprehensive workflow routing logic
- [ ] Integrate with business logic layer (`AnalysisService`)
- [ ] Create monitoring and metrics collection
- [ ] Frontend integration for displaying workflow results

### **Week 4: Testing & Polish (Days 9-10)**
- [ ] Unit tests for all workflow nodes and routing
- [ ] Integration tests for complete workflow
- [ ] Performance optimization and timeout handling
- [ ] Error recovery testing with various failure scenarios
- [ ] Documentation and code review
- [ ] Deploy and validate in staging environment

---

## 🎯 Success Criteria

### **Functional Requirements**
- ✅ Complete LangGraph workflow executing successfully
- ✅ Structure and Appeal agents producing valid results
- ✅ State persistence throughout workflow execution
- ✅ Error handling and retry mechanisms working
- ✅ Results aggregation and scoring calculation
- ✅ Clean integration with business logic layer

### **Performance Requirements**
- ✅ Total analysis time < 60 seconds for typical resumes
- ✅ Individual agent execution < 25 seconds
- ✅ Workflow state transitions < 1 second
- ✅ Error recovery without data loss
- ✅ Memory usage optimized for concurrent workflows

### **Quality Requirements** 
- ✅ Code coverage > 80% for AI module
- ✅ All workflow paths tested with integration tests
- ✅ Error scenarios handled gracefully
- ✅ Monitoring and logging implemented
- ✅ Documentation complete and accurate

---

**Document Status**: Ready for Implementation  
**Next Review**: Mid-Sprint 004 (September 23, 2025)  
**Architecture Decision**: Approved for Sprint 004 development

*This architecture provides a robust foundation for sophisticated AI-powered resume analysis while maintaining clean separation of concerns and deployment simplicity.*