# AI Agents Documentation

This directory contains the AI agent system for the resume review platform.

## Architecture

The agent system is built using LangChain and follows a modular, extensible design:

```
app/agents/
├── __init__.py
├── base/
│   ├── __init__.py
│   ├── agent.py          # Base agent abstract class
│   ├── config.py         # Configuration management
│   ├── factory.py        # Agent factory for creating instances
│   └── test_agent.py     # Simple test agent implementation
└── resume/
    ├── __init__.py
    └── [future resume-specific agents]
```

## Core Components

### BaseAgent Class

All agents inherit from `BaseAgent` which provides:
- Configuration management via `AgentConfig`
- LLM initialization and caching
- Chain building and execution
- Input validation
- Metrics collection
- Error handling

### Agent Configuration

Agents are configured using `AgentConfig` which includes:
- Agent type and metadata
- LLM provider (OpenAI, Anthropic)
- Model selection and parameters
- System prompts
- Timeout and resource limits

### Agent Factory

The `AgentFactory` provides:
- Agent instance creation
- Configuration validation
- Provider availability checking
- Type registration system

## Available Agent Types

| Agent Type | Description | Status |
|------------|-------------|---------|
| `TEST` | Simple test agent for integration testing | ✅ Implemented |
| `RESUME_ANALYZER` | Analyzes overall resume structure and content | 🚧 Planned |
| `SKILLS_EXTRACTOR` | Extracts and categorizes skills | 🚧 Planned |
| `EXPERIENCE_ANALYZER` | Analyzes work experience | 🚧 Planned |
| `FEEDBACK_GENERATOR` | Generates improvement feedback | 🚧 Planned |

## LLM Provider Support

### OpenAI
- **Models**: gpt-3.5-turbo, gpt-4, gpt-4-turbo-preview
- **Requirements**: `OPENAI_API_KEY` environment variable
- **Usage**: High-quality general analysis

### Anthropic (Claude)
- **Models**: claude-3-haiku-20240307, claude-3-sonnet-20240229, claude-3-opus-20240229
- **Requirements**: `ANTHROPIC_API_KEY` environment variable  
- **Usage**: Detailed reasoning and analysis

## Usage Examples

### Creating and Using an Agent

```python
from app.agents.base.factory import agent_factory
from app.agents.base.agent import AgentType

# Create a test agent with default configuration
agent = agent_factory.create_agent(AgentType.TEST)

# Process input
result = await agent.process({"input": "Hello, test agent!"})
print(result["output"])
```

### Custom Configuration

```python
from app.agents.base.agent import AgentConfig, AgentType
from app.agents.base.factory import agent_factory

# Custom configuration
config = AgentConfig(
    agent_type=AgentType.TEST,
    name="custom_test_agent",
    description="Custom test agent",
    model_provider="anthropic",
    model_name="claude-3-haiku-20240307",
    temperature=0.3,
    max_tokens=500,
    system_prompt="You are a helpful assistant specializing in resume analysis."
)

# Create agent with custom config
agent = agent_factory.create_agent(AgentType.TEST, config)
```

## Environment Setup

### Required Environment Variables

```bash
# OpenAI (optional)
export OPENAI_API_KEY="your-openai-api-key"

# Anthropic (optional)
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Agent Configuration (optional)
export AI_AGENT_DEFAULT_TEMPERATURE=0.7
export AI_AGENT_DEFAULT_MAX_TOKENS=1000
export AI_AGENT_DEFAULT_TIMEOUT=30
```

### Dependencies

The agent system requires the following packages:
- `langchain>=0.1.0`
- `langchain-core>=0.1.0`
- `langchain-openai>=0.0.5` (for OpenAI support)
- `langchain-anthropic>=0.1.0` (for Anthropic support)
- `openai>=1.6.0`
- `anthropic>=0.40.0`
- `pydantic>=2.5.0`

## Testing

### Running Tests

```bash
# Run all agent tests
pytest tests/test_agents.py -v

# Run only unit tests (no API keys required)
pytest tests/test_agents.py -v -k "not integration"

# Run integration tests (requires API keys)
pytest tests/test_agents.py -v -m integration
```

### Test Categories

1. **Unit Tests**: Test agent structure, configuration, and mocked functionality
2. **Integration Tests**: Test actual LLM provider connections (requires API keys)
3. **Mock Tests**: Test agent processing with mocked LLM responses

## Error Handling

The agent system handles several types of errors:

### Configuration Errors
- Missing API keys → `ValueError: Provider not available`
- Invalid model names → `ValueError: Model not supported`
- Invalid parameters → Pydantic validation errors

### Runtime Errors
- Network timeouts → Included in agent response as error message
- API rate limits → Handled by provider clients
- Invalid input → Validation error in agent response

### Example Error Response

```python
{
    "error": "Provider openai not available (missing API key)",
    "agent_name": "test_agent"
}
```

## Development Guidelines

### Creating New Agents

1. **Inherit from BaseAgent**:
   ```python
   class MyAgent(BaseAgent):
       def _initialize_llm(self):
           # Initialize your LLM
           pass
       
       def _build_chain(self):
           # Build your LangChain chain
           pass
       
       async def process(self, input_data):
           # Process input and return results
           pass
   ```

2. **Register with Factory**:
   ```python
   from app.agents.base.factory import agent_factory
   agent_factory.register_agent(AgentType.MY_AGENT, MyAgent)
   ```

3. **Add Configuration**:
   Update `AgentConfigManager._create_default_configs()` with default config.

4. **Write Tests**:
   Add comprehensive tests in `tests/test_agents.py`.

### Best Practices

- **Input Validation**: Always validate input in `validate_input()`
- **Error Handling**: Return structured error responses
- **Async Support**: Use async/await for LLM calls
- **Resource Management**: Respect timeout and token limits
- **Logging**: Use structured logging for debugging
- **Testing**: Write both unit and integration tests

## Configuration Reference

### AgentConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_type` | `AgentType` | Required | Type of agent |
| `name` | `str` | Required | Agent instance name |
| `description` | `str` | Required | Agent description |
| `model_provider` | `str` | `"openai"` | LLM provider |
| `model_name` | `str` | `"gpt-3.5-turbo"` | Model to use |
| `temperature` | `float` | `0.7` | Response randomness (0.0-2.0) |
| `max_tokens` | `int` | `None` | Maximum response tokens |
| `system_prompt` | `str` | `None` | System prompt for agent |
| `enabled` | `bool` | `True` | Whether agent is enabled |
| `timeout` | `int` | `30` | Timeout in seconds |

## Troubleshooting

### Common Issues

1. **"Module not found" errors**: Install missing LangChain packages
2. **"Provider not available"**: Set appropriate API key environment variable
3. **"Model not supported"**: Check available models in provider config
4. **Async test failures**: Ensure `@pytest.mark.asyncio` is used
5. **Import errors**: Check Python path and module structure

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger("langchain").setLevel(logging.DEBUG)
```

## Roadmap

### Sprint 2 (Planned)
- Resume analyzer agent implementation
- Skills extraction agent
- Integration with file upload system

### Sprint 3 (Planned)
- Experience analysis agent
- Feedback generation agent
- Multi-agent workflows with LangGraph

### Future Enhancements
- Agent monitoring and metrics
- Custom model fine-tuning
- Vector database integration
- Real-time agent orchestration