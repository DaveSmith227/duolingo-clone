"""
Input sanitization middleware to prevent XSS and injection attacks.
"""
import re
import html
from typing import Any, Dict, Union, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json


class SanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically sanitize user input.
    Prevents XSS and other injection attacks.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Fields that should not be sanitized
        self.skip_fields = {
            'password', 'current_password', 'new_password', 
            'confirm_password', 'token', 'refresh_token',
            'access_token', 'api_key', 'secret'
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request and sanitize input data."""
        # Only process POST, PUT, PATCH requests
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Get request body
                body = await request.body()
                if body:
                    # Parse JSON
                    data = json.loads(body)
                    # Sanitize data
                    sanitized_data = self.sanitize_data(data)
                    # Create new request with sanitized data
                    request._body = json.dumps(sanitized_data).encode()
            except:
                # If parsing fails, continue with original request
                pass
        
        response = await call_next(request)
        return response
    
    def sanitize_data(self, data: Any) -> Any:
        """
        Recursively sanitize data structure.
        
        Args:
            data: Input data (dict, list, or scalar)
            
        Returns:
            Sanitized data
        """
        if isinstance(data, dict):
            return {
                key: self.sanitize_data(value) 
                if key not in self.skip_fields 
                else value
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self.sanitize_data(item) for item in data]
        elif isinstance(data, str):
            return self.sanitize_string(data)
        else:
            return data
    
    def sanitize_string(self, value: str) -> str:
        """
        Sanitize string value to prevent XSS.
        
        Args:
            value: Input string
            
        Returns:
            Sanitized string
        """
        if not value:
            return value
        
        # HTML escape special characters
        value = html.escape(value)
        
        # Remove potentially dangerous patterns
        # Remove javascript: protocol
        value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
        
        # Remove on* event handlers
        value = re.sub(r'on\w+\s*=', '', value, flags=re.IGNORECASE)
        
        # Remove script tags
        value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove iframe tags
        value = re.sub(r'<iframe[^>]*>.*?</iframe>', '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove object and embed tags
        value = re.sub(r'<(object|embed)[^>]*>.*?</(object|embed)>', '', value, flags=re.IGNORECASE | re.DOTALL)
        
        return value.strip()


class SQLInjectionProtection:
    """
    Helper class to prevent SQL injection by validating input.
    """
    
    @staticmethod
    def is_safe_identifier(value: str) -> bool:
        """
        Check if a string is safe to use as SQL identifier.
        
        Args:
            value: String to check
            
        Returns:
            True if safe, False otherwise
        """
        # Only allow alphanumeric, underscore, and dash
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', value))
    
    @staticmethod
    def escape_like_pattern(pattern: str) -> str:
        """
        Escape special characters in LIKE patterns.
        
        Args:
            pattern: LIKE pattern
            
        Returns:
            Escaped pattern
        """
        # Escape special LIKE characters
        pattern = pattern.replace('\\', '\\\\')
        pattern = pattern.replace('%', '\\%')
        pattern = pattern.replace('_', '\\_')
        return pattern
    
    @staticmethod
    def validate_order_by(column: str, allowed_columns: List[str]) -> str:
        """
        Validate ORDER BY column against whitelist.
        
        Args:
            column: Column name to order by
            allowed_columns: List of allowed column names
            
        Returns:
            Validated column name
            
        Raises:
            ValueError: If column not in whitelist
        """
        if column not in allowed_columns:
            raise ValueError(f"Invalid sort column: {column}")
        return column


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators
    filename = filename.replace('/', '').replace('\\', '')
    
    # Remove special characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    # Remove leading dots
    filename = filename.lstrip('.')
    
    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:max_length - len(ext) - 1] + '.' + ext if ext else name[:max_length]
    
    return filename or 'unnamed'