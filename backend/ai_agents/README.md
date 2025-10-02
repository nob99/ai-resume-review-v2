# AI Agents Module

**Version 2.0.0** - LangGraph-based resume analysis with two specialized agents

## Quick Start

```python
from ai_agents import ResumeAnalysisOrchestrator

orchestrator = ResumeAnalysisOrchestrator()
result = await orchestrator.analyze(
    resume_text="...",
    industry="tech_consulting"
)
```

## Architecture

```
Resume Text → Structure Agent → Appeal Agent → Final Results
```

**Structure Agent**: Formatting, organization, ATS compatibility
**Appeal Agent**: Industry-specific competitiveness

## Project Structure

```
ai_agents/
├── agents/           # Agent implementations (base, structure, appeal)
├── workflows/        # LangGraph workflow & state definitions
├── config/           # YAML configs (agents.yaml, industries.yaml)
├── prompts/          # Prompt templates (YAML)
├── tests/            # Unit tests
├── settings.py       # Infrastructure config (Python)
└── orchestrator.py   # Main workflow executor
```

## Configuration

### Infrastructure (`settings.py`)
Set via environment variables:
```bash
AI_AGENT_LLM__OPENAI_API_KEY=sk-your-key
AI_AGENT_LLM__MODEL=gpt-4o
```

### Business Rules (`config/agents.yaml`)
Edit scoring weights, thresholds, agent parameters

### Prompts (`prompts/*.yaml`)
Edit prompt templates and parsing rules

### Language Settings (`settings.py`)

**Single source of truth** for prompt language:

```python
# backend/ai_agents/settings.py
prompt_language: str = "ja"  # "en" or "ja"
```

**To switch languages:**
1. Edit `settings.py` and change `prompt_language` value
2. Rebuild Docker: `./scripts/docker-dev.sh build`
3. Restart: `./scripts/docker-dev.sh up`

**Available prompt files:**
- English: `prompts/*_prompt_v1_en.yaml`
- Japanese: `prompts/*_prompt_v1_ja.yaml`

## Development Guidelines

**Design Principles:**
1. Simple is best - clear code over clever code
2. YAML for business logic - non-engineers can edit
3. No dependencies on parent `app.core.*`

**Adding a New Agent:**
1. Create `agents/new_agent.py` extending `BaseAgent`
2. Add prompt template in `prompts/` (e.g., `new_agent_v1.yaml`)
3. Update `workflows/workflow.py`
4. Add tests in `tests/unit/`

**Testing:**
```bash
pytest backend/ai_agents/tests/ -v
```

**Verify Imports:**
```bash
python3 -c "from ai_agents import ResumeAnalysisOrchestrator; print('✅ OK')"
```

## Supported Industries

`tech_consulting`, `strategy_consulting`, `finance_banking`, `system_integrator`, `full_service_consulting`, `general_business`

## Migration from v1.0

- `core/` → `workflows/`
- `config.py` → `settings.py`
- Industry config moved to `config/industries.yaml`

---

**Simple is Best** ✨
