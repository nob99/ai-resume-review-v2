# AI Agents Implementation Plan

## Executive Summary
This document outlines the implementation plan for the LangGraph-based AI orchestration system in Sprint 004. The system uses two specialized agents (Structure and Appeal) to analyze resumes with industry-specific insights.

**Core Principle**: Keep it simple - Two agents, one flow, clean results.

---

## 🎯 System Overview

### **Simple Flow Architecture**
```
Resume Text → Structure Agent → Appeal Agent → Final Results
```

### **Key Design Decisions**
- **Two Agents Only**: Structure analysis followed by Appeal analysis
- **LangGraph Orchestration**: Simple state management and workflow control
- **Direct OpenAI Integration**: No unnecessary abstraction layers
- **Industry-Specific Analysis**: Appeal agent adapts based on industry parameter
- **Clean State Management**: Minimal state schema with essential fields only

---

## 📁 Directory Structure

```
backend/app/ai_agents/
├── agents/
│   ├── __init__.py
│   ├── structure.py      # Structure analysis agent
│   └── appeal.py         # Appeal analysis agent
├── core/
│   ├── __init__.py
│   ├── state.py          # Simple state for LangGraph
│   └── workflow.py       # LangGraph workflow (2 nodes only)
├── orchestrator.py       # Main entry point
├── models.py             # Pydantic models for results
└── utils.py              # Helper functions and error handling
```

---

## 🔧 Technical Implementation

### **1. State Schema (core/state.py)**

```python
from typing import TypedDict, Optional, Dict, List

class ResumeAnalysisState(TypedDict):
    # Input
    resume_text: str
    industry: str
    
    # Structure Agent output
    structure_scores: Optional[Dict[str, float]]
    structure_feedback: Optional[Dict[str, List[str]]]
    
    # Appeal Agent output  
    appeal_scores: Optional[Dict[str, float]]
    appeal_feedback: Optional[Dict[str, List[str]]]
    market_tier: Optional[str]
    
    # Final aggregated result
    overall_score: Optional[float]
    summary: Optional[str]
    
    # Simple error tracking
    error: Optional[str]
```

### **2. Structure Agent (agents/structure.py)**

**Purpose**: Analyze resume structure, formatting, and professional presentation

**Key Features**:
- Format and layout assessment (0-100 score)
- Section organization evaluation
- Professional tone analysis
- Completeness checking
- Uses existing structure_v1.yaml prompt template

**Implementation Approach**:
```python
class StructureAgent:
    - Load prompt from YAML template
    - Call OpenAI GPT-4 with structured prompt
    - Parse response using regex patterns from template
    - Return scores and feedback in state
```

### **3. Appeal Agent (agents/appeal.py)**

**Purpose**: Industry-specific competitiveness and appeal analysis

**Key Features**:
- Achievement relevance scoring (0-100)
- Skills alignment assessment
- Experience fit evaluation
- Competitive positioning analysis
- Market tier determination (entry/mid/senior/executive)
- Uses structure results as context

**Implementation Approach**:
```python
class AppealAgent:
    - Load industry-specific prompt from YAML
    - Include structure analysis context
    - Call OpenAI GPT-4 with appeal prompt
    - Parse response and calculate overall score
    - Generate executive summary
```

### **4. LangGraph Workflow (core/workflow.py)**

**Simple Two-Node Workflow**:
```python
def create_workflow():
    workflow = StateGraph(ResumeAnalysisState)
    
    # Add nodes (just 2!)
    workflow.add_node("structure", structure_agent.analyze)
    workflow.add_node("appeal", appeal_agent.analyze)
    
    # Define flow: structure → appeal → end
    workflow.set_entry_point("structure")
    workflow.add_edge("structure", "appeal")
    workflow.add_edge("appeal", END)
    
    return workflow.compile()
```

### **5. Orchestrator (orchestrator.py)**

**Main Entry Point**:
```python
class ResumeAnalysisOrchestrator:
    async def analyze(self, resume_text: str, industry: str) -> Dict[str, Any]:
        # Initialize state
        # Run workflow
        # Return clean results with overall score and feedback
```

---

## 🔄 Error Handling Strategy

### **Retry Logic**
- 3 retry attempts with exponential backoff
- Graceful degradation on partial failures
- Clear error messages in response

### **Error Types**
- **Retryable**: API timeouts, rate limits
- **Non-Retryable**: Invalid API keys, malformed input
- **Partial Failure**: One agent fails, return available results

---

## 📊 Response Format

### **Successful Analysis Response**
```json
{
  "overall_score": 78.5,
  "structure": {
    "scores": {
      "format": 85,
      "organization": 80,
      "tone": 75,
      "completeness": 70
    },
    "feedback": {
      "issues": ["Inconsistent date formatting", "Missing summary section"],
      "strengths": ["Clear section headers", "Professional language"]
    }
  },
  "appeal": {
    "scores": {
      "achievement_relevance": 82,
      "skills_alignment": 75,
      "experience_fit": 78,
      "competitive_positioning": 80
    },
    "feedback": {
      "missing_skills": ["Python", "Cloud Architecture"],
      "competitive_advantages": ["Strong leadership experience"],
      "improvement_areas": ["Add quantifiable achievements"]
    },
    "market_tier": "senior"
  },
  "summary": "Strong senior-level candidate with solid structure..."
}
```

---

## 🚀 Implementation Timeline

### **Day 1: Foundation Setup**
- [ ] Create directory structure
- [ ] Implement ResumeAnalysisState schema
- [ ] Set up LangGraph workflow skeleton
- [ ] Create Pydantic models for results

### **Day 2: Structure Agent**
- [ ] Implement StructureAgent class
- [ ] Integrate with existing prompt templates
- [ ] Add response parsing logic
- [ ] Create unit tests with mock responses

### **Day 3: Appeal Agent**
- [ ] Implement AppealAgent class
- [ ] Add industry-specific prompt handling
- [ ] Integrate structure context usage
- [ ] Create unit tests for appeal analysis

### **Day 4: Integration**
- [ ] Complete orchestrator implementation
- [ ] Add error handling and retry logic
- [ ] Integrate with FastAPI endpoint
- [ ] End-to-end workflow testing

### **Day 5: Polish & Testing**
- [ ] Performance optimization
- [ ] Comprehensive error handling
- [ ] Integration tests
- [ ] Documentation updates

---

## 🧪 Testing Strategy

### **Unit Tests**
- Mock OpenAI responses for predictable testing
- Test each agent independently
- Validate response parsing logic
- Test error handling scenarios

### **Integration Tests**
- Test complete workflow with sample resumes
- Validate state transitions
- Test different industry configurations
- Ensure <60 second processing time

### **Test Structure**
```
backend/app/ai_agents/tests/
├── unit/
│   ├── test_structure_agent.py
│   ├── test_appeal_agent.py
│   └── test_workflow.py
├── integration/
│   └── test_orchestrator.py
├── fixtures/
│   ├── sample_resumes.json
│   └── mock_responses.json
└── conftest.py
```

---

## 🔌 API Integration

### **Endpoint**: `POST /api/analyze`

**Request**:
```json
{
  "file": "resume.pdf",
  "industry": "tech_consulting"
}
```

**Integration Code**:
```python
@router.post("/analyze")
async def analyze_resume(file: UploadFile, industry: str):
    # 1. Extract text from file (existing Sprint 003)
    text = await extract_text(file)
    
    # 2. Run AI analysis
    orchestrator = ResumeAnalysisOrchestrator()
    result = await orchestrator.analyze(text, industry)
    
    # 3. Store and return results
    return result
```

---

## 📈 Performance Targets

- **Analysis Time**: < 60 seconds for typical resume
- **Concurrent Requests**: Support 10 simultaneous analyses
- **Error Rate**: < 1% for valid inputs
- **Retry Success**: > 95% success rate with retries

---

## 🔐 Security Considerations

- API keys stored in environment variables
- No PII logging in production
- Rate limiting on analysis endpoint
- Input validation and sanitization
- Secure file handling (no persistent storage)

---

## 📚 Dependencies

### **Python Packages** (already in requirements.txt)
- `langgraph>=0.2.0` - Workflow orchestration
- `langchain>=0.3.0` - LLM utilities
- `openai>=1.6.0` - OpenAI API client
- `pydantic>=2.7.4` - Data validation

### **External Services**
- OpenAI API (GPT-4 access required)
- Redis for caching (optional)

---

## ✅ Success Criteria

1. **Functional Requirements**
   - [x] Two agents (Structure and Appeal) working in sequence
   - [x] LangGraph orchestration of workflow
   - [x] Industry-specific analysis capability
   - [x] Clean API integration

2. **Quality Requirements**
   - [x] < 60 second analysis time
   - [x] Comprehensive error handling
   - [x] 80% test coverage
   - [x] Clean, maintainable code

3. **Deliverables**
   - [x] Working AI orchestration system
   - [x] Unit and integration tests
   - [x] API endpoint integration
   - [x] Documentation

---

## 🎯 Key Benefits of This Approach

1. **Simplicity**: Just two agents with clear responsibilities
2. **Maintainability**: Clean separation of concerns
3. **Testability**: Easy to mock and test independently
4. **Scalability**: Can add more agents later if needed
5. **Performance**: Minimal overhead, direct API calls
6. **Flexibility**: Industry-specific analysis without complexity

---

## 📝 Notes

- This plan prioritizes simplicity over feature richness
- The system can be extended with additional agents in future sprints
- Prompt templates are managed separately in YAML files for easy updates
- The workflow is designed to be observable and debuggable

---

**Document Version**: 1.0.0  
**Sprint**: 004  
**Created**: September 2025  
**Status**: Ready for Implementation