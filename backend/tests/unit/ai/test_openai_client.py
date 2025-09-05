"""
Unit Tests for OpenAI Client
=============================

Tests for the OpenAI client integration including API calls,
error handling, retry logic, and usage tracking.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage
from app.ai.integrations.openai_client import OpenAIClient
from app.ai.integrations.base_llm import LLMResponse, LLMRateLimitError, LLMAuthenticationError, LLMTimeoutError


@pytest.fixture
def openai_client():
    """Create OpenAI client for testing."""
    return OpenAIClient(
        api_key="test-api-key",
        model="gpt-4",
        max_tokens=2000,
        temperature=0.3,
        timeout_seconds=10,
        max_retries=2
    )


@pytest.fixture
def mock_openai_response():
    """Create mock OpenAI API response."""
    return ChatCompletion(
        id="chatcmpl-test123",
        choices=[
            {
                "index": 0,
                "message": ChatCompletionMessage(
                    role="assistant",
                    content="Test response from OpenAI API"
                ),
                "finish_reason": "stop"
            }
        ],
        created=1234567890,
        model="gpt-4",
        object="chat.completion",
        usage=CompletionUsage(
            completion_tokens=50,
            prompt_tokens=100,
            total_tokens=150
        )
    )


class TestOpenAIClient:
    """Test OpenAI client functionality."""
    
    def test_client_initialization(self):
        """Test OpenAI client initializes correctly."""
        client = OpenAIClient(
            api_key="test-key",
            model="gpt-4",
            max_tokens=4000,
            temperature=0.5,
            timeout_seconds=30,
            max_retries=3
        )
        
        assert client.api_key == "test-key"
        assert client.model == "gpt-4"
        assert client.max_tokens == 4000
        assert client.temperature == 0.5
        assert client.timeout_seconds == 30
        assert client.max_retries == 3
        assert client.client is not None
        assert client.async_client is not None
    
    def test_count_tokens(self, openai_client):
        """Test token counting functionality."""
        text = "This is a test message for token counting."
        
        token_count = openai_client._count_tokens(text)
        
        assert isinstance(token_count, int)
        assert token_count > 0
        assert token_count < 50  # Should be reasonable for short text
    
    def test_count_tokens_empty_text(self, openai_client):
        """Test token counting with empty text."""
        token_count = openai_client._count_tokens("")
        assert token_count == 0
    
    @pytest.mark.asyncio
    async def test_validate_connection_success(self, openai_client):
        """Test successful connection validation."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        
        with patch.object(openai_client.async_client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = await openai_client.validate_connection()
            
            assert result is True
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, openai_client):
        """Test connection validation failure."""
        with patch.object(openai_client.async_client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("Connection failed")
            
            result = await openai_client.validate_connection()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_ainvoke_success(self, openai_client, mock_openai_response):
        """Test successful async API call."""
        prompt = "Analyze this resume for technical skills."
        
        with patch.object(openai_client.async_client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_openai_response
            
            response = await openai_client.ainvoke(prompt)
            
            assert isinstance(response, LLMResponse)
            assert response.content == "Test response from OpenAI API"
            assert response.model == "gpt-4"
            assert response.usage_stats is not None
            assert response.usage_stats["total_tokens"] == 150
            assert response.response_time_ms > 0
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ainvoke_with_system_message(self, openai_client, mock_openai_response):
        """Test async API call with system message."""
        prompt = "Analyze this resume."
        system_message = "You are a professional resume analyzer."
        
        with patch.object(openai_client.async_client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_openai_response
            
            response = await openai_client.ainvoke(prompt, system_message=system_message)
            
            assert isinstance(response, LLMResponse)
            # Check that system message was included in the call
            call_args = mock_create.call_args
            messages = call_args[1]["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == system_message
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == prompt
    
    def test_invoke_success(self, openai_client, mock_openai_response):
        """Test successful sync API call."""
        prompt = "Analyze this resume for technical skills."
        
        with patch.object(openai_client.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_openai_response
            
            response = openai_client.invoke(prompt)
            
            assert isinstance(response, LLMResponse)
            assert response.content == "Test response from OpenAI API"
            assert response.model == "gpt-4"
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ainvoke_rate_limit_error(self, openai_client):
        """Test handling of rate limit errors."""
        from openai import RateLimitError
        
        with patch.object(openai_client.async_client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(),
                body={}
            )
            
            with pytest.raises(LLMRateLimitError) as exc_info:
                await openai_client.ainvoke("Test prompt")
            
            assert "rate limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_ainvoke_authentication_error(self, openai_client):
        """Test handling of authentication errors."""
        from openai import AuthenticationError
        
        with patch.object(openai_client.async_client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = AuthenticationError(
                message="Invalid API key",
                response=MagicMock(),
                body={}
            )
            
            with pytest.raises(LLMAuthenticationError) as exc_info:
                await openai_client.ainvoke("Test prompt")
            
            assert "authentication" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_ainvoke_timeout_error(self, openai_client):
        """Test handling of timeout errors."""
        import asyncio
        
        with patch.object(openai_client.async_client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = asyncio.TimeoutError("Request timed out")
            
            with pytest.raises(LLMTimeoutError) as exc_info:
                await openai_client.ainvoke("Test prompt")
            
            assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_ainvoke_retry_logic(self, openai_client, mock_openai_response):
        """Test retry logic on API failures."""
        prompt = "Test prompt"
        
        with patch.object(openai_client.async_client.chat.completions, 'create') as mock_create:
            # First call fails, second succeeds
            mock_create.side_effect = [
                Exception("Temporary failure"),
                mock_openai_response
            ]
            
            with patch('asyncio.sleep', return_value=None):  # Skip actual delays
                response = await openai_client.ainvoke(prompt)
            
            assert isinstance(response, LLMResponse)
            assert mock_create.call_count == 2  # Original call + 1 retry
    
    @pytest.mark.asyncio
    async def test_ainvoke_max_retries_exceeded(self, openai_client):
        """Test behavior when max retries are exceeded."""
        prompt = "Test prompt"
        
        with patch.object(openai_client.async_client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("Persistent failure")
            
            with patch('asyncio.sleep', return_value=None):  # Skip actual delays
                with pytest.raises(Exception) as exc_info:
                    await openai_client.ainvoke(prompt)
                
                assert "Persistent failure" in str(exc_info.value)
                # Should try: original + max_retries attempts
                assert mock_create.call_count == openai_client.max_retries + 1
    
    @pytest.mark.asyncio
    async def test_astream_success(self, openai_client):
        """Test successful streaming API call."""
        prompt = "Stream this response"
        
        # Mock streaming response
        mock_stream_response = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello "))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content="world!"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=""))])
        ]
        
        async def mock_stream():
            for chunk in mock_stream_response:
                yield chunk
        
        with patch.object(openai_client.async_client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_stream()
            
            chunks = []
            async for chunk in openai_client.astream(prompt):
                chunks.append(chunk)
            
            assert len(chunks) == 3
            assert chunks[0] == "Hello "
            assert chunks[1] == "world!"
            assert chunks[2] == ""
    
    def test_get_usage_stats(self, openai_client):
        """Test getting usage statistics."""
        # Simulate some usage
        openai_client._total_tokens = 1500
        openai_client._total_requests = 10
        
        stats = openai_client.get_usage_stats()
        
        assert isinstance(stats, dict)
        assert "total_tokens" in stats
        assert "total_requests" in stats
        assert "model" in stats
        assert stats["total_tokens"] == 1500
        assert stats["total_requests"] == 10
        assert stats["model"] == "gpt-4"
    
    def test_prepare_messages_user_only(self, openai_client):
        """Test message preparation with user message only."""
        prompt = "Analyze this resume"
        
        messages = openai_client._prepare_messages(prompt)
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == prompt
    
    def test_prepare_messages_with_system(self, openai_client):
        """Test message preparation with system message."""
        prompt = "Analyze this resume"
        system_message = "You are a resume expert"
        
        messages = openai_client._prepare_messages(prompt, system_message)
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == system_message
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == prompt
    
    def test_calculate_retry_delay(self, openai_client):
        """Test retry delay calculation."""
        # Base delay should be 1.0 seconds
        delay_1 = openai_client._calculate_retry_delay(1)
        delay_2 = openai_client._calculate_retry_delay(2)
        delay_3 = openai_client._calculate_retry_delay(3)
        
        assert delay_1 == 2.0  # base_delay * 2^1
        assert delay_2 == 4.0  # base_delay * 2^2
        assert delay_3 == 8.0  # base_delay * 2^3
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling_with_retry(self, openai_client, mock_openai_response):
        """Test rate limit handling with successful retry."""
        from openai import RateLimitError
        
        prompt = "Test prompt"
        
        with patch.object(openai_client.async_client.chat.completions, 'create') as mock_create:
            # First call hits rate limit, second succeeds
            mock_create.side_effect = [
                RateLimitError(
                    message="Rate limit exceeded",
                    response=MagicMock(),
                    body={}
                ),
                mock_openai_response
            ]
            
            with patch('asyncio.sleep', return_value=None):  # Skip actual delays
                response = await openai_client.ainvoke(prompt)
            
            assert isinstance(response, LLMResponse)
            assert mock_create.call_count == 2  # Original + 1 retry
    
    def test_usage_tracking(self, openai_client, mock_openai_response):
        """Test that usage statistics are tracked correctly."""
        prompt = "Test prompt"
        initial_tokens = openai_client._total_tokens
        initial_requests = openai_client._total_requests
        
        with patch.object(openai_client.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_openai_response
            
            response = openai_client.invoke(prompt)
        
        assert openai_client._total_tokens == initial_tokens + 150  # From mock usage
        assert openai_client._total_requests == initial_requests + 1
        assert isinstance(response, LLMResponse)
    
    def test_extract_usage_stats(self, openai_client, mock_openai_response):
        """Test extraction of usage statistics from OpenAI response."""
        usage_stats = openai_client._extract_usage_stats(mock_openai_response)
        
        assert isinstance(usage_stats, dict)
        assert usage_stats["completion_tokens"] == 50
        assert usage_stats["prompt_tokens"] == 100
        assert usage_stats["total_tokens"] == 150