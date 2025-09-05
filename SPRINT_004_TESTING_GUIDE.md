# 🧪 Sprint 004 Testing Guide - LangGraph AI Orchestration

**Sprint:** 004 - LangGraph AI Orchestration Implementation  
**Guide Version:** 1.0  
**Last Updated:** September 5, 2025  
**Target Audience:** QA Engineers, Developers, Test Automation Engineers

---

## 📋 Overview

This guide provides comprehensive instructions for testing the newly implemented LangGraph AI orchestration system. Sprint 004 introduced a sophisticated multi-agent resume analysis workflow that requires specialized testing approaches.

### 🎯 **What's New in Sprint 004:**
- **LangGraph Orchestrator**: Multi-agent workflow coordination
- **Structure Agent**: Resume formatting and organization analysis
- **Appeal Agent**: Industry-specific competitiveness analysis
- **OpenAI Integration**: Real AI-powered analysis capabilities
- **Error Handling**: Comprehensive retry and fallback mechanisms

---

## 🗂️ Test File Organization

### Directory Structure
```
backend/tests/unit/ai/
├── __init__.py
├── test_orchestrator.py          # LangGraph workflow tests (19 tests)
├── test_structure_agent.py       # Structure analysis tests (16 tests) 
├── test_appeal_agent.py          # Appeal analysis tests (17 tests)
└── test_openai_client.py         # OpenAI integration tests (19 tests)

Total: 71 AI-specific test cases
```

### Test Categories by File

#### 1. **test_orchestrator.py** - Workflow Coordination
```python
# Core workflow tests
- Orchestrator initialization and configuration
- Resume preprocessing and validation
- Agent coordination and state management
- Error handling and retry logic
- Results aggregation
- End-to-end analysis workflow

# Key test methods:
- test_orchestrator_initialization()
- test_preprocess_resume_success()
- test_run_structure_agent()
- test_validate_structure_results()
- test_aggregate_final_results()
- test_analyze_resume_end_to_end()
```

#### 2. **test_structure_agent.py** - Resume Structure Analysis
```python
# Structure analysis functionality
- Agent initialization and configuration
- Resume section identification
- Score extraction from LLM output
- Feedback list parsing
- Confidence calculation
- Result validation

# Key test methods:
- test_extract_scores_from_output()
- test_extract_feedback_lists()
- test_analyze_success()
- test_parse_structure_output()
- test_validate_structure_result()
```

#### 3. **test_appeal_agent.py** - Industry-Specific Analysis
```python
# Appeal analysis functionality
- Industry-specific prompts
- Achievement relevance scoring
- Skills alignment assessment
- Market tier determination
- Competitive positioning analysis

# Key test methods:
- test_extract_scores_from_output()
- test_extract_achievement_lists()
- test_extract_market_tier()
- test_analyze_success()
- test_get_supported_industries()
```

#### 4. **test_openai_client.py** - AI Integration
```python
# OpenAI API integration
- Client initialization and configuration
- API call success and failure scenarios
- Rate limiting and error handling
- Token counting and usage tracking
- Retry logic and timeouts

# Key test methods:
- test_ainvoke_success()
- test_rate_limit_handling()
- test_authentication_error()
- test_retry_logic()
- test_usage_tracking()
```

---

## 🔧 Test Environment Setup

### Prerequisites

1. **Docker Environment Running**
   ```bash
   cd /path/to/project
   ./scripts/docker-dev.sh status  # Check if services are running
   ./scripts/docker-dev.sh up      # Start if needed
   ```

2. **Required Services**
   - ✅ Backend API (port 8000)
   - ✅ PostgreSQL (port 5432)  
   - ✅ Redis (port 6379)

3. **Environment Variables**
   ```bash
   # Required for OpenAI integration tests
   export OPENAI_API_KEY="your-api-key-here"
   
   # Optional: Control test behavior
   export AI_MOCK_MODE="true"          # Use mock LLM (no API costs)
   export AI_MOCK_MODE="false"         # Use real OpenAI API (costs money)
   ```

### Python Environment
```bash
# Ensure you're in the backend directory
cd backend

# Set Python path for imports
export PYTHONPATH=$PWD

# Verify dependencies
pip install -r requirements.txt
```

---

## 🚀 Running Tests

### Quick Commands

#### Run All AI Tests
```bash
# From backend directory
python3 -m pytest tests/unit/ai/ -v
```

#### Run Specific Test Files
```bash
# Structure agent tests only
python3 -m pytest tests/unit/ai/test_structure_agent.py -v

# Orchestrator tests only
python3 -m pytest tests/unit/ai/test_orchestrator.py -v

# Appeal agent tests only
python3 -m pytest tests/unit/ai/test_appeal_agent.py -v

# OpenAI client tests only
python3 -m pytest tests/unit/ai/test_openai_client.py -v
```

#### Run Individual Tests
```bash
# Specific test method
python3 -m pytest tests/unit/ai/test_structure_agent.py::TestStructureAgent::test_analyze_success -v

# Test class
python3 -m pytest tests/unit/ai/test_orchestrator.py::TestResumeAnalysisOrchestrator -v
```

### Test Coverage Analysis
```bash
# Generate coverage report
python3 -m pytest tests/unit/ai/ --cov=app/ai --cov-report=term-missing

# HTML coverage report
python3 -m pytest tests/unit/ai/ --cov=app/ai --cov-report=html
# Open htmlcov/index.html in browser
```

### Performance Testing
```bash
# Run tests with timing
python3 -m pytest tests/unit/ai/ -v --durations=10

# Parallel execution (if pytest-xdist installed)
python3 -m pytest tests/unit/ai/ -n 4
```

---

## 🧪 Testing Approaches by Component

### 1. Structure Agent Testing

**Focus Areas:**
- Text parsing accuracy
- Score extraction reliability
- Feedback categorization
- Error handling

**Sample Test Execution:**
```bash
# Test structure agent comprehensively
python3 -m pytest tests/unit/ai/test_structure_agent.py -v

# Expected: 16 tests, all should pass
# Coverage: ~92% for structure_agent.py
```

**Common Issues to Check:**
- Regex pattern matching for score extraction
- List parsing accuracy for feedback items
- Pydantic validation for score ranges (0-100)
- Confidence calculation logic

### 2. Appeal Agent Testing

**Focus Areas:**
- Industry-specific analysis logic
- Achievement relevance scoring  
- Market tier assessment
- Skills alignment evaluation

**Sample Test Execution:**
```bash
# Test appeal agent functionality
python3 -m pytest tests/unit/ai/test_appeal_agent.py -v

# Note: Some tests may fail if methods aren't fully implemented
# Coverage: ~20% for appeal_agent.py (work in progress)
```

**Test Strategy:**
- Mock LLM responses for consistent testing
- Validate industry-specific prompt generation
- Check achievement categorization accuracy
- Verify market tier classification logic

### 3. Orchestrator Testing

**Focus Areas:**
- Workflow state management
- Agent coordination
- Error propagation
- Results aggregation

**Sample Test Execution:**
```bash
# Test workflow orchestration
python3 -m pytest tests/unit/ai/test_orchestrator.py -v

# Expected: 17/19 tests passing (2 edge case failures acceptable)
# Coverage: ~70% for orchestrator.py
```

**Critical Test Scenarios:**
- End-to-end workflow execution
- Error recovery and retry logic
- State persistence across workflow steps
- Conditional routing between agents

### 4. OpenAI Client Testing

**Focus Areas:**
- API integration reliability
- Error handling robustness
- Rate limiting behavior
- Token usage tracking

**Sample Test Execution:**
```bash
# Test OpenAI integration (requires API key)
export OPENAI_API_KEY="your-key"
python3 -m pytest tests/unit/ai/test_openai_client.py -v

# Note: Tests use mocks to avoid API costs
# Some integration tests may require real API calls
```

**Testing Considerations:**
- Most tests use mocked API responses
- Real API testing should be done sparingly (costs money)
- Focus on error scenarios and edge cases
- Validate retry logic with exponential backoff

---

## 📊 Expected Test Results

### Current Status (Post-Fixes)

| Test File | Total Tests | Passing | Failing | Coverage |
|-----------|-------------|---------|---------|----------|
| **test_structure_agent.py** | 16 | ✅ 16 | 0 | 92% |
| **test_orchestrator.py** | 19 | ✅ 17 | ⚠️ 2 | 70% |
| **test_appeal_agent.py** | 17 | ⚠️ 2 | 15 | 20% |
| **test_openai_client.py** | 19 | ⚠️ 3 | 16 | 0% |
| **Total** | **71** | **38** | **33** | **58%** |

### Test Success Criteria

**✅ Acceptable Results:**
- Structure Agent: All tests passing (16/16)
- Orchestrator: Core functionality passing (17/19)
- Overall AI module coverage: >50%

**⚠️ Known Issues:**
- Appeal Agent: Test infrastructure created but needs method implementations
- OpenAI Client: Mock setup needs refinement for integration tests
- 2 orchestrator edge case tests failing (non-blocking)

---

## 🐛 Common Issues & Troubleshooting

### Issue 1: Import Errors
```bash
Error: ModuleNotFoundError: No module named 'app.ai.orchestrator'

Solution:
export PYTHONPATH=/path/to/backend
cd /path/to/backend
python3 -m pytest tests/unit/ai/ -v
```

### Issue 2: Missing Environment Variables
```bash
Error: OPENAI_API_KEY not configured

Solutions:
# For mock testing (recommended)
export AI_MOCK_MODE="true"

# For real API testing
export OPENAI_API_KEY="your-api-key-here"
```

### Issue 3: Docker Services Not Running
```bash
Error: Connection refused to PostgreSQL

Solution:
./scripts/docker-dev.sh status
./scripts/docker-dev.sh up
```

### Issue 4: Pydantic Validation Errors
```bash
Error: Input should be less than or equal to 100

Solution:
# This is expected for negative test cases
# Tests should use pytest.raises() for validation errors
```

### Issue 5: LangGraph Import Issues
```bash
Error: No module named 'langgraph'

Solution:
pip install -r requirements.txt
# Check that langgraph is in requirements.txt
```

---

## 🔍 Test Data & Fixtures

### Sample Test Data

#### Resume Text Fixture
```python
SAMPLE_RESUME_TEXT = """
John Smith
Senior Software Engineer
john.smith@email.com | (555) 123-4567

EXPERIENCE
Senior Software Engineer | TechCorp Inc. | 2020-Present
- Led team of 8 developers on React/Node.js applications
- Improved system performance by 40% through optimization
- Architected microservices handling 1M+ daily requests

EDUCATION
B.S. Computer Science | University of Technology | 2018

SKILLS
Languages: Python, JavaScript, TypeScript, SQL
Frameworks: React, Node.js, Django, FastAPI
"""
```

#### Expected Analysis Results
```python
# Structure analysis scores
expected_structure_scores = {
    "format_score": 85.0,
    "section_organization_score": 80.0,
    "professional_tone_score": 90.0,
    "completeness_score": 75.0
}

# Appeal analysis for tech_consulting
expected_appeal_scores = {
    "achievement_relevance_score": 82.0,
    "skills_alignment_score": 88.0,
    "experience_fit_score": 85.0,
    "competitive_positioning_score": 80.0
}
```

### Mock LLM Responses

#### Structure Agent Mock Response
```python
MOCK_STRUCTURE_RESPONSE = """
Format Score: 85
Section Organization Score: 78
Professional Tone Score: 82
Completeness Score: 76

Strengths:
- Clear section headers and organization
- Professional language throughout
- Comprehensive work experience

Recommendations:
- Add quantifiable achievements
- Include technical skills section
- Improve formatting consistency
"""
```

#### Appeal Agent Mock Response
```python
MOCK_APPEAL_RESPONSE = """
Achievement Relevance Score: 79
Skills Alignment Score: 84
Experience Fit Score: 87
Competitive Positioning Score: 81

Relevant Achievements:
- Led team of 8 developers on React project
- Improved system performance by 40%
- Architected microservices handling 1M+ requests

Market Tier Assessment: Senior
"""
```

---

## 📈 Performance Benchmarks

### Expected Test Execution Times

| Test Suite | Expected Duration | Benchmark |
|------------|-------------------|-----------|
| Structure Agent | 0.1 - 0.2s | Fast unit tests |
| Orchestrator | 0.2 - 0.5s | Medium complexity |
| Appeal Agent | 0.1 - 0.3s | Fast unit tests |
| OpenAI Client | 0.1 - 0.2s | Mock responses |
| **Full AI Suite** | **1-2 seconds** | **Target** |

### Coverage Targets

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| Structure Agent | 92% | 95% | Medium |
| Base Agent | 72% | 80% | Medium |
| Orchestrator | 70% | 80% | High |
| Appeal Agent | 20% | 70% | High |
| OpenAI Client | 0% | 60% | Medium |
| **Overall AI** | **58%** | **80%** | **High** |

---

## 🔒 Security Testing Considerations

### API Key Management
```bash
# Never commit API keys
echo "OPENAI_API_KEY=sk-..." >> .env
echo ".env" >> .gitignore

# Use test API keys with limits
export OPENAI_API_KEY="sk-test-limited-key"
```

### Input Validation Testing
```python
# Test malicious input handling
def test_malicious_input_handling():
    malicious_inputs = [
        "<script>alert('xss')</script>",
        "'; DROP TABLE users; --",
        "../../../etc/passwd",
        "A" * 100000  # Very long input
    ]
    
    for malicious_input in malicious_inputs:
        # Should handle gracefully without crashing
        result = agent.analyze(malicious_input)
        assert result["has_errors"] == True
```

### Rate Limiting Tests
```python
# Test API rate limiting behavior
def test_rate_limiting():
    # Simulate rapid API calls
    # Should implement exponential backoff
    # Should not crash on rate limit errors
```

---

## 📚 Additional Resources

### Documentation Links
- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **OpenAI API Reference**: https://platform.openai.com/docs/api-reference
- **Pytest Documentation**: https://docs.pytest.org/
- **Coverage.py**: https://coverage.readthedocs.io/

### Internal Resources
- **Architecture Design**: `/docs/ai-architecture.md`
- **API Documentation**: http://localhost:8000/docs
- **Database Schema**: `/database/README.md`
- **Deployment Guide**: `/infrastructure/README.md`

### Support Contacts
- **AI Team Lead**: ai-team@airesumereview.com
- **QA Team Lead**: qa-team@airesumereview.com  
- **DevOps Support**: devops@airesumereview.com

---

## 🚀 Quick Start Checklist

For new testers joining Sprint 004:

### Setup (First Time)
- [ ] Clone repository
- [ ] Start Docker services: `./scripts/docker-dev.sh up`
- [ ] Set PYTHONPATH: `export PYTHONPATH=/path/to/backend`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Configure API key: `export OPENAI_API_KEY="your-key"`

### Daily Testing Routine
- [ ] Check service status: `./scripts/docker-dev.sh status`
- [ ] Run AI test suite: `python3 -m pytest tests/unit/ai/ -v`
- [ ] Check coverage: `python3 -m pytest tests/unit/ai/ --cov=app/ai --cov-report=term-missing`
- [ ] Review failing tests and investigate issues
- [ ] Update test documentation if needed

### Before Committing Changes
- [ ] All structure agent tests passing (16/16)
- [ ] Core orchestrator tests passing (17/19 minimum)
- [ ] No new critical failures introduced
- [ ] Coverage maintained or improved
- [ ] Documentation updated if needed

---

**Guide Version:** 1.0  
**Next Update:** When Sprint 005 begins  
**Feedback:** Please report issues or suggestions to qa-team@airesumereview.com

---

*This guide is living documentation - please keep it updated as the testing infrastructure evolves.*