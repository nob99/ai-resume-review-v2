"""
Simple test agent for LangChain integration testing.
"""

from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .agent import BaseAgent, AgentConfig


class TestAgent(BaseAgent):
    """Simple test agent to verify LangChain integration."""
    
    def _initialize_llm(self):
        """Initialize the LLM instance based on configuration."""
        if self.config.model_provider == "openai":
            return ChatOpenAI(
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                # API key will be loaded from environment variable OPENAI_API_KEY
            )
        elif self.config.model_provider == "anthropic":
            return ChatAnthropic(
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                # API key will be loaded from environment variable ANTHROPIC_API_KEY
            )
        else:
            raise ValueError(f"Unsupported model provider: {self.config.model_provider}")
    
    def _build_chain(self):
        """Build the LangChain chain for this agent."""
        # Create a simple prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.config.system_prompt or "You are a helpful test assistant."),
            ("human", "{input}")
        ])
        
        # Create the chain: prompt -> llm -> output parser
        chain = prompt | self.llm | StrOutputParser()
        return chain
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return results.
        
        Args:
            input_data: Should contain "input" key with text to process
            
        Returns:
            Dictionary with "output" key containing the response
        """
        if not self.validate_input(input_data):
            return {
                "error": "Invalid input format",
                "expected": "Dictionary with 'input' key"
            }
        
        if "input" not in input_data:
            return {
                "error": "Missing 'input' key in input_data"
            }
        
        try:
            # Process the input through the chain
            response = await self.chain.ainvoke({"input": input_data["input"]})
            
            return {
                "output": response,
                "agent_name": self.name,
                "model_used": self.config.model_name,
                "provider": self.config.model_provider
            }
            
        except Exception as e:
            return {
                "error": f"Processing failed: {str(e)}",
                "agent_name": self.name
            }
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data format.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            True if valid, False otherwise
        """
        return (
            isinstance(input_data, dict) and
            "input" in input_data and
            isinstance(input_data["input"], str)
        )