# AI Agents Module

LangGraph-based AI orchestration system for resume analysis using two specialized agents.

## Overview

This module implements a simple two-agent workflow for analyzing resumes:
1. **Structure Agent**: Analyzes formatting, organization, and professional presentation
2. **Appeal Agent**: Evaluates industry-specific competitiveness and appeal

## Architecture

```
Resume Text → Structure Agent → Appeal Agent → Final Results
```

## Key Components

### Core
- `core/state.py`: LangGraph state schema
- `core/workflow.py`: Two-node workflow definition

### Agents
- `agents/structure.py`: Resume structure analysis
- `agents/appeal.py`: Industry-specific appeal analysis

### Orchestration
- `orchestrator.py`: Main workflow executor
- `models.py`: Pydantic models for type safety
- `utils.py`: Error handling and utilities

## Usage

```python
from app.ai_agents import ResumeAnalysisOrchestrator

# Initialize orchestrator
orchestrator = ResumeAnalysisOrchestrator()

# Run analysis
result = await orchestrator.analyze(
    resume_text="...",
    industry="tech_consulting"
)

# Access results
print(f"Overall Score: {result['overall_score']}")
print(f"Market Tier: {result['market_tier']}")
```

## Supported Industries

- `tech_consulting`: Technology Consulting
- `finance_banking`: Finance & Banking
- `strategy_consulting`: Strategy Consulting
- `system_integrator`: Systems Integration
- `full_service_consulting`: Full Service Consulting
- `general_business`: General Business

## Configuration

Set the following environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL_NAME`: Model to use (default: gpt-4)
- `OPENAI_MAX_TOKENS`: Max tokens per request (default: 4000)

## Testing

Run unit tests:
```bash
pytest app/ai_agents/tests/unit/ -v
```

Run example usage:
```bash
python app/ai_agents/example_usage.py
```

## Response Format

```json
{
  "success": true,
  "analysis_id": "uuid",
  "overall_score": 85.5,
  "market_tier": "senior",
  "summary": "Executive summary...",
  "structure": {
    "scores": {...},
    "feedback": {...}
  },
  "appeal": {
    "scores": {...},
    "feedback": {...}
  }
}
```

## Error Handling

- Automatic retry with exponential backoff
- Graceful degradation on partial failures
- Clear error messages in responses

## Performance

- Target: < 60 seconds for typical resume
- Supports concurrent analyses
- Minimal dependencies for fast startup