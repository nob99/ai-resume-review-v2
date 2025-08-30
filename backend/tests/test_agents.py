"""
Integration tests for AI agents.
"""

import pytest
import os
from unittest.mock import patch, AsyncMock
from app.agents.base.agent import AgentType, AgentConfig
from app.agents.base.factory import agent_factory
from app.agents.base.config import config_manager
from app.agents.base.test_agent import TestAgent


class TestAgentConfiguration:
    """Test agent configuration and management."""
    
    def test_agent_config_creation(self):
        """Test creating agent configurations."""
        config = AgentConfig(
            agent_type=AgentType.TEST,
            name="test_agent",
            description="Test agent",
            model_provider="openai",
            model_name="gpt-3.5-turbo"
        )
        
        assert config.agent_type == AgentType.TEST
        assert config.name == "test_agent"
        assert config.model_provider == "openai"
        assert config.temperature == 0.7  # default value
    
    def test_config_manager_default_configs(self):
        """Test that config manager has default configurations."""
        test_config = config_manager.get_config(AgentType.TEST)
        assert test_config is not None
        assert test_config.agent_type == AgentType.TEST
        assert test_config.name == "test_agent"
    
    def test_config_manager_available_providers(self):
        """Test getting available providers."""
        providers = config_manager.get_available_providers()
        assert "openai" in providers
        assert "anthropic" in providers
    
    def test_config_validation_without_api_keys(self):
        """Test config validation when API keys are not available."""
        config = AgentConfig(
            agent_type=AgentType.TEST,
            name="test_agent",
            description="Test agent",
            model_provider="openai",
            model_name="gpt-3.5-turbo"
        )
        
        # This should fail validation due to missing API keys
        is_valid, error_message = config_manager.validate_config(config)
        assert not is_valid
        assert "not available" in error_message.lower()


class TestAgentFactory:
    """Test agent factory functionality."""
    
    def test_agent_factory_registration(self):
        """Test that agent types are properly registered."""
        available_types = agent_factory.get_available_agent_types()
        assert AgentType.TEST in available_types
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key-for-testing"})
    def test_agent_creation_with_mock_api_key(self):
        """Test agent creation when API key is available."""
        config = AgentConfig(
            agent_type=AgentType.TEST,
            name="test_agent",
            description="Test agent",
            model_provider="openai",
            model_name="gpt-3.5-turbo"
        )
        
        # With mocked API key, this should not fail on creation
        agent = agent_factory.create_agent(AgentType.TEST, config)
        assert isinstance(agent, TestAgent)
        assert agent.name == "test_agent"
        assert agent.agent_type == AgentType.TEST
    
    def test_agent_creation_without_api_key_fails(self):
        """Test that agent creation fails without API keys."""
        with pytest.raises(ValueError, match="not available"):
            agent_factory.create_agent(AgentType.TEST)


class TestAgentFunctionality:
    """Test agent functionality with mocked dependencies."""
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key-for-testing"})
    @patch('app.agents.base.test_agent.ChatOpenAI')
    def test_test_agent_initialization(self, mock_openai):
        """Test that test agent initializes properly."""
        # Mock the ChatOpenAI class
        mock_llm_instance = AsyncMock()
        mock_openai.return_value = mock_llm_instance
        
        config = AgentConfig(
            agent_type=AgentType.TEST,
            name="test_agent",
            description="Test agent",
            model_provider="openai",
            model_name="gpt-3.5-turbo"
        )
        
        agent = TestAgent(config)
        
        # Access the llm property to trigger initialization
        llm = agent.llm
        
        # Verify ChatOpenAI was called with correct parameters
        mock_openai.assert_called_once_with(
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=None,
            timeout=30
        )
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key-for-testing"})
    @patch('app.agents.base.test_agent.ChatOpenAI')
    @pytest.mark.asyncio
    async def test_test_agent_process_with_mock(self, mock_openai):
        """Test agent processing with mocked LLM."""
        # Mock the entire chain response
        mock_chain = AsyncMock()
        mock_chain.ainvoke.return_value = "Hello, this is a test response!"
        
        config = AgentConfig(
            agent_type=AgentType.TEST,
            name="test_agent",
            description="Test agent",
            model_provider="openai",
            model_name="gpt-3.5-turbo"
        )
        
        agent = TestAgent(config)
        # Replace the chain with our mock
        agent._chain = mock_chain
        
        # Test processing
        input_data = {"input": "Hello, test agent!"}
        result = await agent.process(input_data)
        
        assert "output" in result
        assert result["output"] == "Hello, this is a test response!"
        assert result["agent_name"] == "test_agent"
        assert result["model_used"] == "gpt-3.5-turbo"
        assert result["provider"] == "openai"
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key-for-testing"})
    def test_test_agent_input_validation(self):
        """Test input validation functionality."""
        config = AgentConfig(
            agent_type=AgentType.TEST,
            name="test_agent",
            description="Test agent",
            model_provider="openai",
            model_name="gpt-3.5-turbo"
        )
        
        agent = TestAgent(config)
        
        # Valid input
        assert agent.validate_input({"input": "test message"})
        
        # Invalid inputs
        assert not agent.validate_input({})  # missing input key
        assert not agent.validate_input({"input": 123})  # non-string input
        assert not agent.validate_input("not a dict")  # not a dictionary
    
    def test_agent_metrics(self):
        """Test agent metrics functionality."""
        config = AgentConfig(
            agent_type=AgentType.TEST,
            name="test_agent",
            description="Test agent",
            model_provider="openai",
            model_name="gpt-3.5-turbo"
        )
        
        agent = TestAgent(config)
        metrics = agent.get_metrics()
        
        assert metrics["agent_name"] == "test_agent"
        assert metrics["agent_type"] == AgentType.TEST
        assert metrics["model_provider"] == "openai"
        assert metrics["model_name"] == "gpt-3.5-turbo"
        assert metrics["enabled"] is True


@pytest.mark.integration
class TestLangChainIntegration:
    """Integration tests that require actual API keys (skipped if not available)."""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), 
        reason="OpenAI API key not available"
    )
    @pytest.mark.asyncio
    async def test_real_openai_integration(self):
        """Test actual OpenAI integration (only runs if API key is available)."""
        config = AgentConfig(
            agent_type=AgentType.TEST,
            name="test_agent",
            description="Test agent",
            model_provider="openai",
            model_name="gpt-3.5-turbo",
            temperature=0.1,  # Low temperature for consistent results
            max_tokens=50
        )
        
        agent = TestAgent(config)
        
        # Test with a simple input
        input_data = {"input": "Say exactly: 'Integration test successful'"}
        result = await agent.process(input_data)
        
        assert "output" in result
        assert "error" not in result
        assert isinstance(result["output"], str)
        assert len(result["output"]) > 0
    
    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"), 
        reason="Anthropic API key not available"
    )
    @pytest.mark.asyncio
    async def test_real_anthropic_integration(self):
        """Test actual Anthropic integration (only runs if API key is available)."""
        config = AgentConfig(
            agent_type=AgentType.TEST,
            name="test_agent",
            description="Test agent",
            model_provider="anthropic",
            model_name="claude-3-haiku-20240307",
            temperature=0.1,
            max_tokens=50
        )
        
        agent = TestAgent(config)
        
        # Test with a simple input
        input_data = {"input": "Say exactly: 'Anthropic integration test successful'"}
        result = await agent.process(input_data)
        
        assert "output" in result
        assert "error" not in result
        assert isinstance(result["output"], str)
        assert len(result["output"]) > 0