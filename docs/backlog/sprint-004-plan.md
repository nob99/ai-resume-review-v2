# Sprint 004 Plan: AI Framework & Results Dashboard
## Modular Monolith with Clear Internal Separation

**Sprint Duration**: 2 weeks  
**Sprint Start**: September 16, 2025  
**Sprint End**: September 29, 2025  
**Sprint Branch**: `sprint-004`  
**Architecture**: Modular Monolith with Dedicated AI Module

---

## 🎯 Sprint Goal

**Build a complete AI-powered resume analysis pipeline with clear internal separation between business logic and AI processing, enabling end-to-end resume review from upload to results display.**

We will implement the AI analysis capabilities within our FastAPI backend using a dedicated AI module that maintains clean boundaries while avoiding deployment complexity.

---

## 🏗️ Architecture Decision: Modular Monolith

### **Why This Approach?**
- ✅ **Simple Deployment**: Single FastAPI service, no microservices complexity
- ✅ **Clear Separation**: AI logic completely isolated in dedicated module
- ✅ **Future Flexibility**: Can extract AI module to separate service later if needed
- ✅ **Development Efficiency**: No service coordination overhead
- ✅ **Maintainable Code**: Well-organized, testable architecture

### **Core Principle: Clear Internal Boundaries**
Each module has **single responsibility** and **well-defined interfaces**:
- **Business Logic** → Handles user requests, file processing, data management
- **AI Module** → Handles all AI processing, agent orchestration, LLM integration
- **Clean Interface** → Business logic calls AI module through clear contracts

---

## 📁 New Project Structure (Backend Focus)

```
backend/
├── app/
│   ├── main.py                    # FastAPI app entry point
│   │
│   ├── api/v1/                   # 🔵 API LAYER
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication endpoints
│   │   ├── upload.py             # File upload & validation endpoints  
│   │   └── analysis.py           # Analysis request & results endpoints
│   │
│   ├── core/                     # 🔵 CORE INFRASTRUCTURE
│   │   ├── __init__.py
│   │   ├── config.py             # Configuration management
│   │   ├── database.py           # Database connection & models
│   │   ├── security.py           # JWT, password hashing
│   │   └── datetime_utils.py     # UTC datetime utilities
│   │
│   ├── services/                 # 🔵 BUSINESS LOGIC LAYER
│   │   ├── __init__.py
│   │   ├── auth_service.py       # Authentication business logic
│   │   ├── file_service.py       # File upload, validation, extraction
│   │   └── analysis_service.py   # Analysis coordination & results management
│   │
│   ├── ai/                       # 🟢 AI MODULE (NEW!)
│   │   ├── __init__.py
│   │   │
│   │   ├── orchestrator.py       # 🤖 Main AI orchestration logic
│   │   │
│   │   ├── agents/               # 🤖 AI Agents
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py     # Abstract base agent class
│   │   │   ├── structure_agent.py # Resume structure analysis
│   │   │   └── appeal_agent.py   # Industry-specific appeal analysis
│   │   │
│   │   ├── prompts/              # 🤖 Prompt Management  
│   │   │   ├── __init__.py
│   │   │   ├── prompt_manager.py # Dynamic prompt loading
│   │   │   └── templates/        # Prompt template files
│   │   │       ├── structure/
│   │   │       │   ├── base.txt
│   │   │       │   └── format_analysis.txt
│   │   │       └── appeal/
│   │   │           ├── tech_consulting.txt
│   │   │           ├── system_integrator.txt
│   │   │           ├── finance_banking.txt
│   │   │           ├── healthcare_pharma.txt
│   │   │           ├── manufacturing.txt
│   │   │           └── general_business.txt
│   │   │
│   │   ├── integrations/         # 🤖 External AI Services
│   │   │   ├── __init__.py
│   │   │   ├── openai_client.py  # OpenAI GPT integration
│   │   │   ├── claude_client.py  # Anthropic Claude integration
│   │   │   └── base_llm.py       # Abstract LLM interface
│   │   │
│   │   └── models/               # 🤖 AI Data Models
│   │       ├── __init__.py
│   │       ├── analysis_request.py
│   │       ├── analysis_result.py
│   │       └── agent_output.py
│   │
│   ├── models/                   # 🔵 DATABASE MODELS
│   │   ├── __init__.py
│   │   ├── user.py               # User model
│   │   ├── analysis.py           # Analysis request/result models
│   │   └── prompt.py             # Prompt storage models
│   │
│   └── schemas/                  # 🔵 API SCHEMAS
│       ├── __init__.py
│       ├── auth.py               # Auth request/response schemas
│       ├── upload.py             # File upload schemas
│       └── analysis.py           # Analysis schemas
│
├── tests/                        # 🧪 TESTING
│   ├── unit/
│   │   ├── services/             # Business logic tests
│   │   └── ai/                   # AI module unit tests
│   │       ├── test_orchestrator.py
│   │       ├── agents/
│   │       └── integrations/
│   ├── integration/
│   │   ├── test_upload_pipeline.py
│   │   ├── test_ai_analysis.py
│   │   └── test_end_to_end.py
│   └── fixtures/
│       ├── sample_resumes/
│       └── mock_responses/
│
├── requirements.txt              # Python dependencies
├── requirements-dev.txt          # Development dependencies
└── Dockerfile                    # Single container deployment
```

---

## 🔄 Data Flow & LangGraph Orchestration

### **LangGraph Workflow Architecture**

```
┌─────────────────┐
│   Frontend      │ HTTP Requests
│   (Next.js)     │────────────────┐
└─────────────────┘                │
                                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │   API Layer     │    │ Business Logic  │               │
│  │ /api/v1/        │───▶│   /services/    │               │
│  │ analysis.py     │    │ analysis_service│               │
│  └─────────────────┘    └─────────┬───────┘               │
│                                   │ Clean Interface       │
│                                   ▼                       │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              AI Module (/ai/)                       │  │
│  │                                                     │  │
│  │    ┌─────────────────────────────────────────────┐  │  │
│  │    │         LangGraph Workflow                  │  │  │
│  │    │                                             │  │  │
│  │    │  START → preprocess → structure_agent      │  │  │
│  │    │            │              │                 │  │  │
│  │    │            ▼              ▼                 │  │  │
│  │    │       validation    → appeal_agent         │  │  │
│  │    │            │              │                 │  │  │
│  │    │            ▼              ▼                 │  │  │
│  │    │       error_handling → aggregate → END     │  │  │
│  │    │                                             │  │  │
│  │    └─────────────────────────────────────────────┘  │  │
│  │                                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │  │
│  │  │ Structure   │  │ Appeal      │  │ LLM         │ │  │
│  │  │ Agent       │  │ Agent       │  │ Integration │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                         ┌─────────────────┐
                         │ External APIs   │
                         │ OpenAI, Claude  │
                         └─────────────────┘
```

### **LangGraph State Management Flow**

```python
# State flows through LangGraph nodes
AnalysisState = {
    "resume_text": str,           # Input
    "industry": str,              # Input  
    "current_stage": str,         # Workflow tracking
    "structure_analysis": dict,   # Structure Agent output
    "appeal_analysis": dict,      # Appeal Agent output  
    "final_result": dict,         # Aggregated results
    "has_errors": bool,           # Error state
    "retry_count": int            # Retry tracking
}

# Clean interface between Business Logic and AI Module  
class AnalysisService:
    async def analyze_resume(self, resume_text: str, industry: str) -> AnalysisResult:
        # Business logic: validation, logging, error handling
        initial_state = AnalysisState(resume_text=resume_text, industry=industry)
        result = await self.ai_orchestrator.app.ainvoke(initial_state)
        return result["final_result"]

# LangGraph orchestrator handles all AI coordination
class ResumeAnalysisOrchestrator:
    def __init__(self):
        self.workflow = self._build_langgraph_workflow()
        self.app = self.workflow.compile()
```

---

## 📋 Sprint 004 Backlog

### **Priority 1: Complete Upload Pipeline (8 points)**

#### **UPLOAD-002: File Validation (Backend Implementation)** 
**Story Points**: 3  
**Module**: `/services/file_service.py`  
**Assignee**: Backend Developer  

**Implementation Focus**:
```python
# app/services/file_service.py
class FileService:
    async def validate_file(self, file_data) -> ValidationResult:
        # File type, size, virus scanning
        # NO AI logic here - pure file validation
```

**Acceptance Criteria**:
- Implement file type validation (PDF, DOC, DOCX only)
- File size validation (max 10MB)
- Virus/malware scanning integration
- Rate limiting (max 5 uploads per minute per user)
- Return structured validation results

---

#### **UPLOAD-003: Text Extraction (Backend Implementation)**
**Story Points**: 5  
**Module**: `/services/file_service.py`  
**Assignee**: Backend Developer  

**Implementation Focus**:
```python
# app/services/file_service.py  
class FileService:
    async def extract_text(self, file_data) -> TextExtractionResult:
        # PDF/Word text extraction using PyPDF2, python-docx
        # Clean and normalize text
        # NO AI processing - pure text extraction
```

**Acceptance Criteria**:
- PDF text extraction with layout preservation
- Word document extraction (.doc/.docx)
- Text cleaning and normalization
- Memory-efficient processing (no temp files)
- Handle corrupted/password-protected files gracefully

---

### **Priority 2: LangGraph AI Orchestration (10 points)**

#### **AI-002: LangGraph Workflow & State Management**
**Story Points**: 5  
**Module**: `/ai/orchestrator.py`, `/ai/models/`  
**Assignee**: AI/ML Engineer  

**Implementation Focus**:
```python
# app/ai/orchestrator.py - LangGraph Workflow
from langgraph.graph import StateGraph, START, END

class ResumeAnalysisOrchestrator:
    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(AnalysisState)
        
        # Add workflow nodes
        workflow.add_node("preprocess", self.preprocess_resume)
        workflow.add_node("structure_analysis", self.run_structure_agent)
        workflow.add_node("structure_validation", self.validate_structure_results)
        workflow.add_node("appeal_analysis", self.run_appeal_agent)
        workflow.add_node("aggregate_results", self.aggregate_final_results)
        
        # Define conditional routing
        workflow.add_conditional_edges("structure_analysis", self.route_after_structure)
        workflow.add_conditional_edges("appeal_analysis", self.route_after_appeal)
        
        return workflow
```

**Key Deliverables**:
- LangGraph StateGraph workflow definition
- AnalysisState schema with TypedDict
- Sequential execution with conditional routing
- State persistence and error recovery
- Clean business logic interface

---

#### **AI-003: LLM Integration & Agent Implementation**
**Story Points**: 3  
**Module**: `/ai/integrations/`, `/ai/agents/`  
**Assignee**: AI/ML Engineer  

**Implementation Focus**:
```python
# app/ai/agents/structure_agent.py - LangGraph Node
class StructureAgent:
    async def analyze(self, state: AnalysisState) -> Dict[str, Any]:
        # LangGraph node function
        prompt = self.prompt_manager.get_prompt("structure_analysis")
        result = await self.llm.ainvoke(prompt.format(resume_text=state["resume_text"]))
        
        return {
            "structure_analysis": parsed_result,
            "current_stage": "structure"
        }
```

**Key Deliverables**:
- Structure Agent as LangGraph node
- OpenAI GPT-4 integration with async calls
- Structured output parsing with Pydantic
- Error handling and retry mechanisms
- Industry-agnostic resume structure analysis

---

#### **APPEAL-001: Industry Selection (Frontend Enhancement)**
**Story Points**: 2  
**Module**: Frontend components  
**Assignee**: Frontend Developer  

**Implementation Focus**:
- Add industry dropdown to upload workflow
- Support 6 industries: Tech Consulting, System Integrator, Finance/Banking, Healthcare/Pharma, Manufacturing, General Business
- Remember selection in local storage
- Pass industry to analysis API

---

### **Priority 3: Results Dashboard Foundation (7 points)**

#### **RESULTS-001: Results Dashboard Core**
**Story Points**: 5  
**Module**: Frontend `/results` page  
**Assignee**: Frontend Developer  

**Implementation Focus**:
- Create results dashboard page with dynamic routing
- Display analysis results from AI module
- Visual score indicators and expandable sections
- Integration with analysis status API

---

#### **UX-003: Enhanced Loading States**
**Story Points**: 2  
**Module**: Frontend progress components  
**Assignee**: Frontend Developer  

**Implementation Focus**:
- Extend Sprint 003 progress system with AI analysis phases
- Show current AI agent being executed
- Time estimates for each processing phase

---

## 🔧 Technical Implementation Strategy

### **Phase 1: LangGraph Foundation (Days 1-3)**
1. **Install LangGraph dependencies** and configure environment
2. **Create AI module structure** with LangGraph integration
3. **Define AnalysisState schema** with TypedDict and Pydantic models
4. **Build basic StateGraph workflow** with START/END nodes
5. **Complete file validation and text extraction** (business logic)

### **Phase 2: Agent Implementation (Days 4-6)**
1. **Implement Structure Agent** as LangGraph node
2. **Add conditional routing** and state validation
3. **Create Appeal Agent** with industry-specific prompts
4. **Set up OpenAI integration** with async calls
5. **Test sequential agent execution** with context passing

### **Phase 3: Workflow Integration (Days 7-8)**
1. **Complete LangGraph workflow** with error handling
2. **Implement retry logic** and state recovery
3. **Add results aggregation** node
4. **Integrate with business logic** layer through clean interface
5. **Frontend industry selection** and basic results display

### **Phase 4: Testing & Optimization (Days 9-10)**
1. **End-to-end workflow testing** with sample resumes
2. **Performance optimization** and monitoring setup
3. **Enhanced loading states** with LangGraph progress tracking
4. **Comprehensive error handling** and documentation
5. **Create technical architecture** documentation

---

## 🧪 Testing Strategy for Modular Architecture

### **Unit Testing by Module**
```python
# tests/unit/services/test_file_service.py
def test_file_validation_logic():
    # Test business logic without AI

# tests/unit/ai/test_orchestrator.py  
def test_agent_orchestration():
    # Test AI logic with mocked LLM responses

# tests/unit/ai/agents/test_structure_agent.py
def test_structure_analysis():
    # Test individual agent logic
```

### **Integration Testing**
```python
# tests/integration/test_analysis_pipeline.py
def test_end_to_end_analysis():
    # Test complete pipeline: upload → extract → AI → results
    
def test_ai_module_integration():
    # Test business logic → AI module interface
```

### **Module Boundary Testing**
- Verify clean interfaces between modules
- Test error propagation across boundaries  
- Validate data contracts between layers

---

## 🎯 Definition of Done for Each Module

### **Business Logic Modules** (`/services/`)
- ✅ Clear single responsibility
- ✅ No AI logic mixed in
- ✅ Clean interface to AI module
- ✅ Comprehensive error handling
- ✅ Unit tests with mocked dependencies

### **AI Module** (`/ai/`)
- ✅ Complete isolation from business logic
- ✅ Self-contained with all AI dependencies
- ✅ Clean external interface
- ✅ Comprehensive agent testing
- ✅ LLM integration with fallbacks

### **API Layer** (`/api/v1/`)
- ✅ Thin layer, delegates to services
- ✅ Proper request/response schemas
- ✅ Error handling and status codes
- ✅ API documentation

---

## 📊 Sprint Success Metrics

### **Functional Metrics**
- ✅ Complete upload → AI analysis → results pipeline working
- ✅ Sub-60 second analysis time for typical resumes
- ✅ Industry-specific analysis producing different outputs
- ✅ Error handling across all module boundaries

### **Architecture Quality Metrics**
- ✅ **Clear Separation**: No AI logic in business services
- ✅ **Clean Interfaces**: Well-defined contracts between modules
- ✅ **Testability**: Each module testable in isolation
- ✅ **Maintainability**: Easy to understand and modify each module

### **Performance Metrics**
- ✅ File processing < 5 seconds
- ✅ AI analysis < 45 seconds  
- ✅ API response times < 2 seconds (excluding AI processing)
- ✅ Memory usage optimized (no file persistence)

---

## 🔄 Future Architecture Evolution

### **Benefits of This Modular Approach**
1. **Easy Microservice Extraction**: AI module can become separate service later
2. **Technology Flexibility**: Can change AI stack without affecting business logic
3. **Independent Scaling**: AI processing logic already isolated
4. **Team Separation**: Different developers can work on different modules
5. **Testing Efficiency**: Fast unit tests for business logic, focused AI testing

### **Migration Path (Future)**
If we need to extract AI module to separate service:
```python
# Current: Direct function call
result = await ai_orchestrator.analyze(text, industry)

# Future: HTTP API call  
result = await ai_service_client.analyze(text, industry)
# Same interface, different implementation!
```

---

## 🎮 Sprint Demo Scenarios

### **Primary Demo: End-to-End Analysis**
1. ✅ Upload resume via drag-and-drop interface (Sprint 003)
2. 🆕 Backend validates and extracts text (file_service.py)
3. 🆕 User selects industry (frontend enhancement)
4. 🆕 AI module processes with progress feedback (ai/orchestrator.py)
5. 🆕 Results dashboard displays structured analysis
6. 🆕 Clear separation visible in logs/monitoring

### **Architecture Demo: Module Separation**
1. 🆕 Show clean interface calls between modules
2. 🆕 Demonstrate AI module working independently
3. 🆕 Test error handling across module boundaries
4. 🆕 Show testability of each module in isolation

---

## ⚠️ Risks & Mitigation

### **Architecture Risks**
| Risk | Mitigation |
|------|------------|
| **Module boundaries blur** | Clear interface contracts, code reviews |
| **AI logic leaks into services** | Strict separation rules, automated testing |
| **Performance overhead** | Profile module boundaries, optimize interfaces |

### **Technical Risks**
| Risk | Mitigation |
|------|------------|
| **LangChain complexity** | Start simple, iterate based on needs |
| **OpenAI API costs** | Usage monitoring, cost alerts, rate limiting |
| **AI processing timeouts** | Implement proper timeouts and partial results |

---

## 📝 Sprint Ceremonies & Communication

### **Daily Focus Areas**
- **Monday-Tuesday**: Module structure setup, interfaces
- **Wednesday-Thursday**: AI implementation, LLM integration  
- **Friday**: Results dashboard, end-to-end testing
- **Week 2**: Integration, polish, testing, documentation

### **Architecture Reviews**
- **Mid-sprint check**: Review module boundaries and interfaces
- **Code reviews**: Enforce separation principles
- **Demo preparation**: Showcase clean architecture benefits

---

## 🚀 Post-Sprint 004 Vision

Upon completion, we will have:
- ✅ **Complete LangGraph workflow** orchestrating resume analysis pipeline
- ✅ **Structure and Appeal agents** working as LangGraph nodes with state passing
- ✅ **Results dashboard** displaying sophisticated AI workflow outputs  
- ✅ **State persistence and error recovery** throughout the AI analysis process
- ✅ **Clean, maintainable AI architecture** with excellent separation of concerns
- ✅ **Production-ready foundation** for complex multi-agent AI workflows

**Sprint 005** will focus on enhancing agent capabilities, advanced prompt management, and performance optimization, building on our robust LangGraph foundation.

---

**Plan Created**: September 4, 2025  
**Architecture**: Modular Monolith with LangGraph AI Orchestration  
**Status**: Ready for Implementation  
**Key Principle**: *"Sophisticated AI workflows with simple deployment and clean boundaries"*

*This plan establishes a production-ready foundation for LangGraph-powered multi-agent resume analysis while maintaining deployment simplicity and architectural clarity.*

---

## 📖 Related Documentation

- **Technical Architecture**: See `docs/design/ai-orchestration-architecture-sprint004.md` for detailed LangGraph implementation
- **User Stories**: All user stories defined in `docs/backlog/user-stories.md`
- **Sprint 003 Completion**: Foundation work completed in `docs/backlog/sprint-003-completion.md`