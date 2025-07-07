"""AI Vision Client Service

Manages AI vision API clients (Claude/OpenAI) with rate limiting, retry logic,
and proper error handling for design token extraction.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Union
from abc import ABC, abstractmethod
import logging
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_retry
)

from app.core.exceptions import ServiceError

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: int):
        """Initialize rate limiter
        
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a call"""
        async with self._lock:
            now = time.time()
            # Remove old calls outside the time window
            self.calls = [call_time for call_time in self.calls 
                         if now - call_time < self.time_window]
            
            if len(self.calls) >= self.max_calls:
                # Need to wait
                oldest_call = self.calls[0]
                wait_time = self.time_window - (now - oldest_call) + 0.1
                logger.info(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                # Recursive call after waiting
                await self.acquire()
            else:
                # Can make the call
                self.calls.append(now)


def log_retry_attempt(retry_state):
    """Log retry attempts"""
    logger.warning(
        f"Retrying {retry_state.fn.__name__}: attempt {retry_state.attempt_number}, "
        f"wait {retry_state.next_action.sleep} seconds"
    )


class AIVisionClient(ABC):
    """Abstract base class for AI vision clients"""
    
    @abstractmethod
    async def analyze_image(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """Analyze an image with the given prompt
        
        Args:
            image_data: Image data in bytes
            prompt: Analysis prompt
            
        Returns:
            Analysis results
        """
        pass


class ClaudeVisionClient(AIVisionClient):
    """Claude Vision API client with rate limiting and retry logic"""
    
    def __init__(self, api_key: str, rate_limit: Optional[Dict[str, int]] = None):
        """Initialize Claude Vision client
        
        Args:
            api_key: Anthropic API key
            rate_limit: Rate limit configuration (max_calls, time_window)
        """
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Set up rate limiter (default: 50 calls per minute)
        rate_config = rate_limit or {"max_calls": 50, "time_window": 60}
        self.rate_limiter = RateLimiter(**rate_config)
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, ServiceError)),
        before=log_retry_attempt
    )
    async def analyze_image(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """Analyze image using Claude Vision API
        
        Args:
            image_data: Image data in bytes
            prompt: Analysis prompt
            
        Returns:
            Analysis results from Claude
        """
        await self.rate_limiter.acquire()
        
        try:
            # Encode image to base64
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare request
            request_data = {
                "model": "claude-3-opus-20240229",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                ]
            }
            
            # Make request
            response = await self.client.post(
                self.base_url,
                json=request_data,
                headers=self.headers
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "success": True,
                "content": result.get("content", [{}])[0].get("text", ""),
                "usage": result.get("usage", {}),
                "model": result.get("model", "")
            }
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during Claude API call: {str(e)}")
            raise ServiceError(f"Claude API request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Claude API call: {str(e)}")
            raise ServiceError(f"Failed to analyze image: {str(e)}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client"""
        await self.client.aclose()


class OpenAIVisionClient(AIVisionClient):
    """OpenAI Vision API client with rate limiting and retry logic"""
    
    def __init__(self, api_key: str, rate_limit: Optional[Dict[str, int]] = None):
        """Initialize OpenAI Vision client
        
        Args:
            api_key: OpenAI API key
            rate_limit: Rate limit configuration (max_calls, time_window)
        """
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Set up rate limiter (default: 60 calls per minute)
        rate_config = rate_limit or {"max_calls": 60, "time_window": 60}
        self.rate_limiter = RateLimiter(**rate_config)
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, ServiceError)),
        before=log_retry_attempt
    )
    async def analyze_image(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """Analyze image using OpenAI Vision API
        
        Args:
            image_data: Image data in bytes
            prompt: Analysis prompt
            
        Returns:
            Analysis results from OpenAI
        """
        await self.rate_limiter.acquire()
        
        try:
            # Encode image to base64
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare request
            request_data = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4096
            }
            
            # Make request
            response = await self.client.post(
                self.base_url,
                json=request_data,
                headers=self.headers
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "success": True,
                "content": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "usage": result.get("usage", {}),
                "model": result.get("model", "")
            }
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during OpenAI API call: {str(e)}")
            raise ServiceError(f"OpenAI API request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI API call: {str(e)}")
            raise ServiceError(f"Failed to analyze image: {str(e)}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client"""
        await self.client.aclose()


class AIVisionClientFactory:
    """Factory for creating AI vision clients"""
    
    @staticmethod
    def create_client(
        provider: str, 
        api_key: str, 
        rate_limit: Optional[Dict[str, int]] = None
    ) -> AIVisionClient:
        """Create an AI vision client
        
        Args:
            provider: Provider name ('claude' or 'openai')
            api_key: API key for the provider
            rate_limit: Optional rate limit configuration
            
        Returns:
            AI vision client instance
            
        Raises:
            ValueError: If provider is not supported
        """
        if provider.lower() == 'claude':
            return ClaudeVisionClient(api_key, rate_limit)
        elif provider.lower() == 'openai':
            return OpenAIVisionClient(api_key, rate_limit)
        else:
            raise ValueError(f"Unsupported AI vision provider: {provider}")


# Update the DesignSystemService to use AI clients
async def configure_ai_clients(settings: Any) -> Dict[str, AIVisionClient]:
    """Configure AI vision clients based on settings
    
    Args:
        settings: Application settings
        
    Returns:
        Dictionary of configured AI clients
    """
    clients = {}
    
    # Configure Claude client if API key is available
    if hasattr(settings, 'anthropic_api_key') and settings.anthropic_api_key:
        clients['claude'] = AIVisionClientFactory.create_client(
            'claude',
            settings.anthropic_api_key,
            {"max_calls": 50, "time_window": 60}
        )
        logger.info("Configured Claude Vision client")
    
    # Configure OpenAI client if API key is available
    if hasattr(settings, 'openai_api_key') and settings.openai_api_key:
        clients['openai'] = AIVisionClientFactory.create_client(
            'openai',
            settings.openai_api_key,
            {"max_calls": 60, "time_window": 60}
        )
        logger.info("Configured OpenAI Vision client")
    
    if not clients:
        logger.warning("No AI vision clients configured - API keys missing")
    
    return clients