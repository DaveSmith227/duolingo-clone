"""Unit tests for AI Vision Client Service"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
import httpx
import base64

from app.services.ai_vision_client import (
    RateLimiter, 
    ClaudeVisionClient, 
    OpenAIVisionClient,
    AIVisionClientFactory,
    configure_ai_clients
)
from app.core.exceptions import ServiceError


class TestRateLimiter:
    """Test cases for RateLimiter"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_calls_within_limit(self):
        """Test that rate limiter allows calls within the limit"""
        # Arrange
        limiter = RateLimiter(max_calls=3, time_window=1)
        
        # Act - Make 3 calls quickly
        start_time = time.time()
        for _ in range(3):
            await limiter.acquire()
        end_time = time.time()
        
        # Assert - Should complete quickly (under 0.1s)
        assert end_time - start_time < 0.1
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_excess_calls(self):
        """Test that rate limiter blocks calls exceeding the limit"""
        # Arrange
        limiter = RateLimiter(max_calls=2, time_window=1)
        
        # Act - Make 3 calls
        start_time = time.time()
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()  # This should be delayed
        end_time = time.time()
        
        # Assert - Should take at least 1 second
        assert end_time - start_time >= 1.0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_cleans_old_calls(self):
        """Test that rate limiter removes old calls from tracking"""
        # Arrange
        limiter = RateLimiter(max_calls=2, time_window=0.5)
        
        # Act
        await limiter.acquire()
        await limiter.acquire()
        await asyncio.sleep(0.6)  # Wait for calls to expire
        
        # Assert - Should be able to make new calls without delay
        start_time = time.time()
        await limiter.acquire()
        end_time = time.time()
        
        assert end_time - start_time < 0.1


class TestClaudeVisionClient:
    """Test cases for ClaudeVisionClient"""
    
    @pytest.fixture
    def claude_client(self):
        """Create a Claude client for testing"""
        return ClaudeVisionClient(api_key="test-key", rate_limit={"max_calls": 10, "time_window": 1})
    
    @pytest.mark.asyncio
    async def test_analyze_image_success(self, claude_client):
        """Test successful image analysis"""
        # Arrange
        image_data = b"fake image data"
        prompt = "Extract design tokens"
        mock_response = {
            "content": [{"text": "Analysis results"}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "model": "claude-3-opus"
        }
        
        with patch.object(claude_client.client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )
            
            # Act
            result = await claude_client.analyze_image(image_data, prompt)
        
        # Assert
        assert result["success"] is True
        assert result["content"] == "Analysis results"
        assert result["usage"]["input_tokens"] == 100
        
        # Verify request format
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert request_data["model"] == "claude-3-opus-20240229"
        assert len(request_data["messages"][0]["content"]) == 2
    
    @pytest.mark.asyncio
    async def test_analyze_image_http_error(self, claude_client):
        """Test handling of HTTP errors"""
        # Arrange
        image_data = b"fake image data"
        prompt = "Extract design tokens"
        
        with patch.object(claude_client.client, 'post') as mock_post:
            mock_post.side_effect = httpx.HTTPError("Connection failed")
            
            # Act & Assert
            with pytest.raises(ServiceError) as exc_info:
                await claude_client.analyze_image(image_data, prompt)
            
            assert "Claude API request failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_analyze_image_retry_on_error(self, claude_client):
        """Test retry logic on errors"""
        # Arrange
        image_data = b"fake image data"
        prompt = "Extract design tokens"
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.HTTPError("Temporary error")
            return Mock(
                status_code=200,
                json=Mock(return_value={"content": [{"text": "Success"}]}),
                raise_for_status=Mock()
            )
        
        with patch.object(claude_client.client, 'post', side_effect=side_effect):
            # Act
            result = await claude_client.analyze_image(image_data, prompt)
        
        # Assert
        assert call_count == 3
        assert result["content"] == "Success"
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality"""
        # Arrange & Act
        async with ClaudeVisionClient(api_key="test-key") as client:
            assert client.api_key == "test-key"
            assert client.client is not None
        
        # Assert - Client should be closed
        assert client.client.is_closed


class TestOpenAIVisionClient:
    """Test cases for OpenAIVisionClient"""
    
    @pytest.fixture
    def openai_client(self):
        """Create an OpenAI client for testing"""
        return OpenAIVisionClient(api_key="test-key", rate_limit={"max_calls": 10, "time_window": 1})
    
    @pytest.mark.asyncio
    async def test_analyze_image_success(self, openai_client):
        """Test successful image analysis"""
        # Arrange
        image_data = b"fake image data"
        prompt = "Extract design tokens"
        mock_response = {
            "choices": [{"message": {"content": "Analysis results"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model": "gpt-4-vision"
        }
        
        with patch.object(openai_client.client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )
            
            # Act
            result = await openai_client.analyze_image(image_data, prompt)
        
        # Assert
        assert result["success"] is True
        assert result["content"] == "Analysis results"
        assert result["usage"]["prompt_tokens"] == 100
        
        # Verify request format
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert request_data["model"] == "gpt-4-vision-preview"
    
    @pytest.mark.asyncio
    async def test_analyze_image_api_error(self, openai_client):
        """Test handling of API errors"""
        # Arrange
        image_data = b"fake image data"
        prompt = "Extract design tokens"
        
        with patch.object(openai_client.client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=400,
                raise_for_status=Mock(side_effect=httpx.HTTPStatusError(
                    "Bad Request", request=Mock(), response=Mock()
                ))
            )
            
            # Act & Assert
            with pytest.raises(ServiceError) as exc_info:
                await openai_client.analyze_image(image_data, prompt)
            
            assert "OpenAI API request failed" in str(exc_info.value)


class TestAIVisionClientFactory:
    """Test cases for AIVisionClientFactory"""
    
    def test_create_claude_client(self):
        """Test creating Claude client"""
        # Act
        client = AIVisionClientFactory.create_client("claude", "test-key")
        
        # Assert
        assert isinstance(client, ClaudeVisionClient)
        assert client.api_key == "test-key"
    
    def test_create_openai_client(self):
        """Test creating OpenAI client"""
        # Act
        client = AIVisionClientFactory.create_client("openai", "test-key")
        
        # Assert
        assert isinstance(client, OpenAIVisionClient)
        assert client.api_key == "test-key"
    
    def test_create_client_with_rate_limit(self):
        """Test creating client with custom rate limit"""
        # Act
        rate_limit = {"max_calls": 5, "time_window": 30}
        client = AIVisionClientFactory.create_client("claude", "test-key", rate_limit)
        
        # Assert
        assert client.rate_limiter.max_calls == 5
        assert client.rate_limiter.time_window == 30
    
    def test_create_client_invalid_provider(self):
        """Test error handling for invalid provider"""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            AIVisionClientFactory.create_client("invalid", "test-key")
        
        assert "Unsupported AI vision provider" in str(exc_info.value)


class TestConfigureAIClients:
    """Test cases for configure_ai_clients function"""
    
    @pytest.mark.asyncio
    async def test_configure_with_both_clients(self):
        """Test configuring both Claude and OpenAI clients"""
        # Arrange
        mock_settings = Mock(
            anthropic_api_key="claude-key",
            openai_api_key="openai-key"
        )
        
        # Act
        with patch('app.services.ai_vision_client.AIVisionClientFactory.create_client') as mock_create:
            mock_create.side_effect = [
                Mock(spec=ClaudeVisionClient),
                Mock(spec=OpenAIVisionClient)
            ]
            clients = await configure_ai_clients(mock_settings)
        
        # Assert
        assert len(clients) == 2
        assert 'claude' in clients
        assert 'openai' in clients
        mock_create.assert_any_call('claude', 'claude-key', {"max_calls": 50, "time_window": 60})
        mock_create.assert_any_call('openai', 'openai-key', {"max_calls": 60, "time_window": 60})
    
    @pytest.mark.asyncio
    async def test_configure_with_claude_only(self):
        """Test configuring only Claude client"""
        # Arrange
        mock_settings = Mock(
            anthropic_api_key="claude-key",
            openai_api_key=None
        )
        
        # Act
        clients = await configure_ai_clients(mock_settings)
        
        # Assert
        assert len(clients) == 1
        assert 'claude' in clients
        assert 'openai' not in clients
    
    @pytest.mark.asyncio
    async def test_configure_with_no_clients(self):
        """Test configuration with no API keys"""
        # Arrange
        mock_settings = Mock(
            anthropic_api_key=None,
            openai_api_key=None
        )
        
        # Act
        clients = await configure_ai_clients(mock_settings)
        
        # Assert
        assert len(clients) == 0