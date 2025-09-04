"""
OpenAI Client Integration
=========================

OpenAI GPT-4 integration for the AI analysis workflow.
This client implements the BaseLLM interface and provides
robust error handling, retry logic, and usage tracking.

Features:
- Async and sync API support
- Automatic retry with exponential backoff
- Token counting and usage monitoring
- Structured error handling
- Streaming support for real-time responses
"""

import asyncio
import time
import logging
from typing import Any, Dict, Optional, AsyncGenerator
from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletion
import tiktoken

from .base_llm import BaseLLM, LLMResponse, LLMError, LLMRateLimitError, LLMAuthenticationError, LLMTimeoutError

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLM):
    """
    OpenAI GPT-4 client implementing the BaseLLM interface.
    
    This client provides production-ready integration with OpenAI's API,
    including proper error handling, retry logic, and monitoring.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        max_tokens: int = 4000,
        temperature: float = 0.3,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        base_delay: float = 1.0
    ):
        """
        Initialize OpenAI client with configuration.
        
        Args:
            api_key: OpenAI API key
            model: Model name (gpt-4, gpt-4-turbo, etc.)
            max_tokens: Maximum tokens for response
            temperature: Response randomness (0.0-1.0)
            timeout_seconds: Request timeout
            max_retries: Maximum retry attempts
            base_delay: Base delay for exponential backoff
        """
        super().__init__(api_key, model, max_tokens, temperature, timeout_seconds)
        
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        # Initialize OpenAI clients
        self.async_client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout_seconds
        )
        self.sync_client = OpenAI(
            api_key=api_key,
            timeout=timeout_seconds
        )
        
        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback for unknown models
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
        logger.info(f"OpenAI client initialized with model: {model}")
    
    async def ainvoke(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Async invoke OpenAI API with retry logic.
        
        Args:
            prompt: Input prompt for the model
            **kwargs: Additional parameters (system_message, etc.)
            
        Returns:
            LLMResponse: Standardized response with content and metadata
        """
        start_time = time.time()
        last_error = None
        
        # Extract additional parameters
        system_message = kwargs.get("system_message", "You are a professional resume analysis expert.")
        custom_temperature = kwargs.get("temperature", self.temperature)
        custom_max_tokens = kwargs.get("max_tokens", self.max_tokens)
        
        for attempt in range(self.max_retries + 1):
            try:
                # Prepare messages
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
                
                logger.debug(f"OpenAI API call attempt {attempt + 1}/{self.max_retries + 1}")
                
                # Make API call
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=custom_max_tokens,
                    temperature=custom_temperature,
                    timeout=self.timeout_seconds
                )
                
                # Extract response content
                content = response.choices[0].message.content or ""
                
                # Track usage
                usage_stats = None
                if response.usage:
                    usage_stats = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                    self._track_usage(response.usage.total_tokens)
                
                logger.debug(f"OpenAI API call successful after {attempt + 1} attempts")
                
                return self._create_response(
                    content=content,
                    start_time=start_time,
                    usage_stats=usage_stats
                )
                
            except Exception as e:
                last_error = e
                logger.warning(f"OpenAI API call attempt {attempt + 1} failed: {str(e)}")
                
                # Convert to standardized error
                llm_error = self._handle_api_error(e)
                
                # Don't retry on authentication errors
                if isinstance(llm_error, LLMAuthenticationError):
                    raise llm_error
                
                # Don't retry on final attempt
                if attempt == self.max_retries:
                    break
                
                # Calculate delay with exponential backoff
                delay = self.base_delay * (2 ** attempt)
                
                # Add jitter to prevent thundering herd
                import random
                delay *= (0.5 + random.random() * 0.5)
                
                logger.info(f"Retrying OpenAI API call in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
        
        # All retries exhausted
        if last_error:
            raise self._handle_api_error(last_error)
        else:
            raise LLMError(
                message="OpenAI API call failed after all retries",
                provider="OpenAI",
                error_code="MAX_RETRIES_EXCEEDED"
            )
    
    def invoke(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Synchronous invoke OpenAI API.
        
        Args:
            prompt: Input prompt for the model
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse: Standardized response
        """
        start_time = time.time()
        
        # Extract additional parameters
        system_message = kwargs.get("system_message", "You are a professional resume analysis expert.")
        custom_temperature = kwargs.get("temperature", self.temperature)
        custom_max_tokens = kwargs.get("max_tokens", self.max_tokens)
        
        try:
            # Prepare messages
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            # Make API call
            response = self.sync_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=custom_max_tokens,
                temperature=custom_temperature,
                timeout=self.timeout_seconds
            )
            
            # Extract response content
            content = response.choices[0].message.content or ""
            
            # Track usage
            usage_stats = None
            if response.usage:
                usage_stats = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                self._track_usage(response.usage.total_tokens)
            
            return self._create_response(
                content=content,
                start_time=start_time,
                usage_stats=usage_stats
            )
            
        except Exception as e:
            raise self._handle_api_error(e)
    
    async def astream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        Async streaming OpenAI API call.
        
        Args:
            prompt: Input prompt for the model
            **kwargs: Additional parameters
            
        Yields:
            str: Partial response chunks as they arrive
        """
        system_message = kwargs.get("system_message", "You are a professional resume analysis expert.")
        custom_temperature = kwargs.get("temperature", self.temperature)
        custom_max_tokens = kwargs.get("max_tokens", self.max_tokens)
        
        try:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            stream = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=custom_max_tokens,
                temperature=custom_temperature,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise self._handle_api_error(e)
    
    def get_token_count(self, text: str) -> int:
        """
        Get accurate token count for text using tiktoken.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Number of tokens
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {str(e)}, falling back to word count")
            # Fallback to approximate word count * 1.3
            return int(len(text.split()) * 1.3)
    
    async def validate_connection(self) -> bool:
        """
        Validate OpenAI API connection.
        
        Returns:
            bool: True if connection is valid
        """
        try:
            test_response = await self.ainvoke(
                "Hello", 
                max_tokens=5,
                system_message="Respond with just 'Hi'"
            )
            return bool(test_response.content)
        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {str(e)}")
            return False
    
    def _handle_api_error(self, error: Exception) -> LLMError:
        """
        Convert OpenAI-specific errors to standardized LLM errors.
        
        Args:
            error: Original OpenAI exception
            
        Returns:
            LLMError: Standardized error
        """
        error_str = str(error).lower()
        
        # OpenAI-specific error handling
        if hasattr(error, 'status_code'):
            status_code = error.status_code
            
            if status_code == 429:
                return LLMRateLimitError(
                    message=f"OpenAI API rate limit exceeded: {str(error)}",
                    provider="OpenAI",
                    error_code="RATE_LIMIT_429"
                )
            elif status_code == 401:
                return LLMAuthenticationError(
                    message=f"OpenAI API authentication failed: {str(error)}",
                    provider="OpenAI", 
                    error_code="AUTH_401"
                )
            elif status_code == 408 or status_code == 504:
                return LLMTimeoutError(
                    message=f"OpenAI API timeout: {str(error)}",
                    provider="OpenAI",
                    error_code=f"TIMEOUT_{status_code}"
                )
        
        # Fallback to parent class error handling
        return super()._handle_api_error(error)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration."""
        return {
            "provider": "OpenAI",
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "base_delay": self.base_delay,
            "supports_streaming": True,
            "supports_system_messages": True
        }