"""
Base LLM Interface
==================

Abstract base class for all LLM integrations used in the AI analysis workflow.
This ensures consistent interfaces across different LLM providers and makes
it easy to switch between providers or add new ones.

The interface is designed to work seamlessly with LangGraph workflows
and provides async support for high-performance processing.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator
from pydantic import BaseModel
import time
import asyncio
import logging

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Standardized response model for all LLM interactions."""
    
    content: str
    model: str
    usage_stats: Optional[Dict[str, Any]] = None
    response_time_ms: int
    timestamp: str
    
    class Config:
        frozen = True


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    
    def __init__(self, message: str, provider: str, error_code: Optional[str] = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        super().__init__(f"LLM Error ({provider}): {message}")


class LLMRateLimitError(LLMError):
    """Raised when LLM API rate limits are exceeded."""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when LLM API authentication fails."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM API requests timeout."""
    pass


class BaseLLM(ABC):
    """
    Abstract base class for all LLM integrations.
    
    This interface defines the contract that all LLM providers must implement
    to work with our AI analysis workflow. It provides both sync and async
    methods for maximum flexibility.
    """
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "gpt-4", 
        max_tokens: int = 4000,
        temperature: float = 0.3,
        timeout_seconds: int = 30
    ):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self._request_count = 0
        self._total_tokens = 0
        
    @abstractmethod
    async def ainvoke(
        self, 
        prompt: str, 
        **kwargs
    ) -> LLMResponse:
        """
        Async method to invoke the LLM with a prompt.
        
        Args:
            prompt: The input prompt for the LLM
            **kwargs: Additional model-specific parameters
            
        Returns:
            LLMResponse: Standardized response with content and metadata
            
        Raises:
            LLMError: Base LLM error for any issues
            LLMRateLimitError: When rate limits are exceeded
            LLMAuthenticationError: When authentication fails
            LLMTimeoutError: When request times out
        """
        pass
    
    @abstractmethod
    def invoke(
        self, 
        prompt: str, 
        **kwargs
    ) -> LLMResponse:
        """
        Synchronous method to invoke the LLM with a prompt.
        
        Args:
            prompt: The input prompt for the LLM
            **kwargs: Additional model-specific parameters
            
        Returns:
            LLMResponse: Standardized response with content and metadata
        """
        pass
    
    @abstractmethod
    async def astream(
        self, 
        prompt: str, 
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Async streaming method for real-time LLM responses.
        
        Args:
            prompt: The input prompt for the LLM
            **kwargs: Additional model-specific parameters
            
        Yields:
            str: Partial response chunks as they arrive
        """
        pass
    
    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """
        Get the token count for a given text using the model's tokenizer.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Number of tokens in the text
        """
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate that the LLM connection is working properly.
        
        Returns:
            bool: True if connection is valid, False otherwise
        """
        pass
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for this LLM instance."""
        return {
            "provider": self.__class__.__name__,
            "model": self.model,
            "total_requests": self._request_count,
            "total_tokens_used": self._total_tokens,
            "average_tokens_per_request": (
                self._total_tokens / self._request_count 
                if self._request_count > 0 else 0
            ),
            "configuration": {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "timeout_seconds": self.timeout_seconds
            }
        }
    
    def _track_usage(self, token_count: int) -> None:
        """Track usage statistics for monitoring."""
        self._request_count += 1
        self._total_tokens += token_count
        
        if self._request_count % 10 == 0:  # Log every 10 requests
            logger.info(
                f"LLM Usage Update: {self._request_count} requests, "
                f"{self._total_tokens} tokens total"
            )
    
    def _create_response(
        self, 
        content: str, 
        start_time: float,
        usage_stats: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Create standardized LLM response."""
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return LLMResponse(
            content=content,
            model=self.model,
            usage_stats=usage_stats,
            response_time_ms=response_time_ms,
            timestamp=str(time.time())
        )
    
    def _handle_api_error(self, error: Exception) -> LLMError:
        """Convert provider-specific errors to standardized LLM errors."""
        error_str = str(error).lower()
        
        if "rate limit" in error_str or "429" in error_str:
            return LLMRateLimitError(
                message=str(error),
                provider=self.__class__.__name__,
                error_code="RATE_LIMIT"
            )
        elif "unauthorized" in error_str or "401" in error_str:
            return LLMAuthenticationError(
                message=str(error),
                provider=self.__class__.__name__,
                error_code="AUTH_FAILED"
            )
        elif "timeout" in error_str:
            return LLMTimeoutError(
                message=str(error),
                provider=self.__class__.__name__,
                error_code="TIMEOUT"
            )
        else:
            return LLMError(
                message=str(error),
                provider=self.__class__.__name__,
                error_code="UNKNOWN"
            )


class MockLLM(BaseLLM):
    """
    Mock LLM implementation for testing and development.
    
    This implementation returns predefined responses and doesn't make
    actual API calls, making it useful for testing and development.
    """
    
    def __init__(self, mock_responses: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(api_key="mock-key", **kwargs)
        self.mock_responses = mock_responses or {}
        self.default_response = (
            "This is a mock LLM response for testing purposes. "
            "In production, this would be replaced with actual LLM output "
            "containing structured analysis of the resume."
        )
    
    async def ainvoke(self, prompt: str, **kwargs) -> LLMResponse:
        """Return mock response based on prompt keywords."""
        start_time = time.time()
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        # Find appropriate mock response
        response_content = self.default_response
        for keyword, response in self.mock_responses.items():
            if keyword.lower() in prompt.lower():
                response_content = response
                break
        
        # Track usage
        token_count = len(response_content.split())
        self._track_usage(token_count)
        
        return self._create_response(
            content=response_content,
            start_time=start_time,
            usage_stats={"tokens_used": token_count}
        )
    
    def invoke(self, prompt: str, **kwargs) -> LLMResponse:
        """Synchronous mock response."""
        start_time = time.time()
        
        # Simulate processing delay
        time.sleep(0.1)
        
        response_content = self.default_response
        for keyword, response in self.mock_responses.items():
            if keyword.lower() in prompt.lower():
                response_content = response
                break
        
        token_count = len(response_content.split())
        self._track_usage(token_count)
        
        return self._create_response(
            content=response_content,
            start_time=start_time,
            usage_stats={"tokens_used": token_count}
        )
    
    async def astream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Mock streaming response."""
        response = await self.ainvoke(prompt, **kwargs)
        words = response.content.split()
        
        for word in words:
            yield word + " "
            await asyncio.sleep(0.01)  # Simulate streaming delay
    
    def get_token_count(self, text: str) -> int:
        """Mock token counting (simple word count)."""
        return len(text.split())
    
    async def validate_connection(self) -> bool:
        """Mock connection validation."""
        return True