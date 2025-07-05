"""
Input validation middleware for API endpoints.
Provides centralized validation with clear error messages.
"""
from typing import Callable, Dict, Any, Optional, List
from functools import wraps
import re
from fastapi import HTTPException, Request, status
from pydantic import BaseModel, ValidationError
import json

from app.core.exceptions import ValidationError as AppValidationError


class ValidationRules:
    """Common validation rules for reuse across endpoints."""
    
    @staticmethod
    def email(value: str) -> str:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, value):
            raise ValueError("Invalid email format")
        return value.lower()
    
    @staticmethod
    def password(value: str) -> str:
        """Validate password strength."""
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', value):
            raise ValueError("Password must contain uppercase letter")
        if not re.search(r'[a-z]', value):
            raise ValueError("Password must contain lowercase letter")
        if not re.search(r'[0-9]', value):
            raise ValueError("Password must contain number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValueError("Password must contain special character")
        return value
    
    @staticmethod
    def username(value: str) -> str:
        """Validate username format."""
        if len(value) < 3 or len(value) > 30:
            raise ValueError("Username must be 3-30 characters")
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise ValueError("Username can only contain letters, numbers, - and _")
        return value
    
    @staticmethod
    def name(value: str) -> str:
        """Validate name format."""
        if len(value) < 1 or len(value) > 50:
            raise ValueError("Name must be 1-50 characters")
        if not re.match(r"^[a-zA-Z\s'-]+$", value):
            raise ValueError("Name contains invalid characters")
        return value.strip()
    
    @staticmethod
    def phone(value: str) -> str:
        """Validate phone number format."""
        # Remove common formatting characters
        cleaned = re.sub(r'[\s\-\(\)\+]', '', value)
        if not cleaned.isdigit():
            raise ValueError("Phone number must contain only digits")
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError("Phone number must be 10-15 digits")
        return cleaned


class InputValidator:
    """Main validator class for request data."""
    
    def __init__(self, rules: Dict[str, List[Callable]]):
        """
        Initialize validator with field rules.
        
        Args:
            rules: Dict mapping field names to list of validation functions
        """
        self.rules = rules
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data against configured rules.
        
        Returns:
            Cleaned and validated data
        
        Raises:
            AppValidationError: If validation fails
        """
        errors = {}
        cleaned_data = {}
        
        for field, validators in self.rules.items():
            value = data.get(field)
            
            # Skip optional fields that aren't provided
            if value is None and field not in data:
                continue
            
            try:
                # Apply all validators in sequence
                for validator in validators:
                    value = validator(value)
                cleaned_data[field] = value
            except ValueError as e:
                errors[field] = str(e)
        
        if errors:
            raise AppValidationError(
                "Validation failed",
                details=errors
            )
        
        return cleaned_data


def validate_request(**field_validators):
    """
    Decorator for validating request data.
    
    Usage:
        @validate_request(
            email=[ValidationRules.email],
            password=[ValidationRules.password]
        )
        async def login(request: Request, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get request data
            try:
                body = await request.json()
            except:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON in request body"
                )
            
            # Validate
            validator = InputValidator(field_validators)
            try:
                cleaned_data = validator.validate(body)
                # Add cleaned data to request state
                request.state.validated_data = cleaned_data
            except AppValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=e.details
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def validate_query_params(**param_validators):
    """
    Decorator for validating query parameters.
    
    Usage:
        @validate_query_params(
            page=[lambda x: int(x) if int(x) > 0 else ValueError("Page must be positive")],
            limit=[lambda x: min(int(x), 100)]
        )
        async def list_items(request: Request, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get query params
            params = dict(request.query_params)
            
            # Validate
            validator = InputValidator(param_validators)
            try:
                cleaned_params = validator.validate(params)
                # Add cleaned params to request state
                request.state.validated_params = cleaned_params
            except AppValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=e.details
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# Common validator combinations
class Validators:
    """Pre-configured validators for common use cases."""
    
    @staticmethod
    def registration_validator():
        """Validator for user registration."""
        return {
            'email': [ValidationRules.email],
            'password': [ValidationRules.password],
            'first_name': [ValidationRules.name],
            'last_name': [ValidationRules.name]
        }
    
    @staticmethod
    def login_validator():
        """Validator for user login."""
        return {
            'email': [ValidationRules.email],
            'password': [lambda x: x if x else ValueError("Password required")]
        }
    
    @staticmethod
    def profile_update_validator():
        """Validator for profile updates."""
        return {
            'first_name': [ValidationRules.name],
            'last_name': [ValidationRules.name],
            'username': [ValidationRules.username],
            'phone': [ValidationRules.phone]
        }