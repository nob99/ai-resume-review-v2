"""
Base agent abstract class for AI agents.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class AgentType(str, Enum):
    """Enumeration of agent types."""
    RESUME_ANALYZER = "resume_analyzer"
    SKILLS_EXTRACTOR = "skills_extractor"
    EXPERIENCE_ANALYZER = "experience_analyzer"
    FEEDBACK_GENERATOR = "feedback_generator"
    TEST = "test"


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    agent_type: AgentType
    name: str
    description: str
    model_provider: str = Field(default="openai", description="LLM provider (openai, anthropic)")
    model_name: str = Field(default="gpt-3.5-turbo", description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    system_prompt: Optional[str] = Field(default=None)
    enabled: bool = Field(default=True)
    timeout: int = Field(default=30, ge=1, description="Timeout in seconds")


class BaseAgent(ABC):
    """Abstract base class for all AI agents."""
    
    def __init__(self, config: AgentConfig):
        """Initialize the agent with configuration.
        
        Args:
            config: Agent configuration
        """
        self.config = config
        self.name = config.name
        self.agent_type = config.agent_type
        self._llm = None
        self._chain = None
    
    @property
    def llm(self):
        """Get the initialized LLM instance."""
        if self._llm is None:
            self._llm = self._initialize_llm()
        return self._llm
    
    @property
    def chain(self):
        """Get the initialized chain instance."""
        if self._chain is None:
            self._chain = self._build_chain()
        return self._chain
    
    @abstractmethod
    def _initialize_llm(self):
        """Initialize the LLM instance based on configuration.
        
        Returns:
            Initialized LLM instance
        """
        pass
    
    @abstractmethod
    def _build_chain(self):
        """Build the LangChain chain for this agent.
        
        Returns:
            LangChain chain instance
        """
        pass
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return results.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Processing results
        """
        pass
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data format.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            True if valid, False otherwise
        """
        return isinstance(input_data, dict)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics.
        
        Returns:
            Dictionary containing metrics
        """
        return {
            "agent_name": self.name,
            "agent_type": self.agent_type,
            "model_provider": self.config.model_provider,
            "model_name": self.config.model_name,
            "enabled": self.config.enabled
        }
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.name}', type='{self.agent_type}')"