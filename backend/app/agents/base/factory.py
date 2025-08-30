"""
Agent factory for creating and managing agent instances.
"""

from typing import Dict, Optional, Type
from .agent import BaseAgent, AgentConfig, AgentType
from .test_agent import TestAgent
from .config import config_manager


class AgentFactory:
    """Factory class for creating agent instances."""
    
    def __init__(self):
        """Initialize the agent factory."""
        self._agent_classes: Dict[AgentType, Type[BaseAgent]] = {
            AgentType.TEST: TestAgent,
            # Additional agent types will be registered here
        }
    
    def register_agent(self, agent_type: AgentType, agent_class: Type[BaseAgent]):
        """Register an agent class for a specific type.
        
        Args:
            agent_type: The agent type to register
            agent_class: The agent class to register
        """
        self._agent_classes[agent_type] = agent_class
    
    def create_agent(self, agent_type: AgentType, config: Optional[AgentConfig] = None) -> BaseAgent:
        """Create an agent instance.
        
        Args:
            agent_type: Type of agent to create
            config: Optional custom configuration. If None, uses default config.
            
        Returns:
            Agent instance
            
        Raises:
            ValueError: If agent type is not registered or config is invalid
        """
        if agent_type not in self._agent_classes:
            raise ValueError(f"Agent type {agent_type} is not registered")
        
        # Use provided config or get default
        if config is None:
            config = config_manager.get_config(agent_type)
            if config is None:
                raise ValueError(f"No default configuration found for agent type {agent_type}")
        
        # Validate configuration
        is_valid, error_message = config_manager.validate_config(config)
        if not is_valid:
            raise ValueError(f"Invalid configuration: {error_message}")
        
        # Create and return agent instance
        agent_class = self._agent_classes[agent_type]
        return agent_class(config)
    
    def get_available_agent_types(self) -> list[AgentType]:
        """Get list of available agent types.
        
        Returns:
            List of registered agent types
        """
        return list(self._agent_classes.keys())
    
    def get_available_agent_types_with_providers(self) -> Dict[AgentType, list[str]]:
        """Get agent types with their available providers.
        
        Returns:
            Dictionary mapping agent types to available providers
        """
        available_providers = config_manager.get_available_providers_with_keys()
        result = {}
        
        for agent_type in self.get_available_agent_types():
            config = config_manager.get_config(agent_type)
            if config and config.model_provider in available_providers:
                result[agent_type] = available_providers
            else:
                result[agent_type] = []
        
        return result


# Global agent factory instance
agent_factory = AgentFactory()