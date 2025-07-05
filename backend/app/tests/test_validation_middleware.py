"""
Tests for validation middleware.
"""
import pytest
from fastapi import HTTPException
from app.middleware.validation import (
    ValidationRules, InputValidator, validate_request,
    validate_query_params, Validators
)
from app.core.exceptions import ValidationError as AppValidationError


class TestValidationRules:
    """Test validation rules."""
    
    def test_email_valid(self):
        """Test valid email addresses."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "first+last@company.org"
        ]
        for email in valid_emails:
            assert ValidationRules.email(email) == email.lower()
    
    def test_email_invalid(self):
        """Test invalid email addresses."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@.com",
            "user @example.com"
        ]
        for email in invalid_emails:
            with pytest.raises(ValueError):
                ValidationRules.email(email)
    
    def test_password_valid(self):
        """Test valid passwords."""
        valid_passwords = [
            "StrongP@ss123",
            "C0mpl3x\!Pass",
            "Secure#Pass2023"
        ]
        for password in valid_passwords:
            assert ValidationRules.password(password) == password
    
    def test_password_invalid(self):
        """Test invalid passwords."""
        test_cases = [
            ("short", "at least 8 characters"),
            ("alllowercase123\!", "uppercase letter"),
            ("ALLUPPERCASE123\!", "lowercase letter"),
            ("NoNumbers\!", "number"),
            ("NoSpecial123", "special character")
        ]
        for password, expected_error in test_cases:
            with pytest.raises(ValueError) as exc_info:
                ValidationRules.password(password)
            assert expected_error in str(exc_info.value)
    
    def test_username_valid(self):
        """Test valid usernames."""
        valid_usernames = [
            "user123",
            "test_user",
            "name-with-dash",
            "abc"
        ]
        for username in valid_usernames:
            assert ValidationRules.username(username) == username
    
    def test_username_invalid(self):
        """Test invalid usernames."""
        test_cases = [
            ("ab", "3-30 characters"),
            ("a" * 31, "3-30 characters"),
            ("user@name", "letters, numbers, - and _"),
            ("user space", "letters, numbers, - and _")
        ]
        for username, expected_error in test_cases:
            with pytest.raises(ValueError) as exc_info:
                ValidationRules.username(username)
            assert expected_error in str(exc_info.value)
    
    def test_name_valid(self):
        """Test valid names."""
        valid_names = [
            "John",
            "Mary-Jane",
            "O'Brien",
            "Jean-Pierre"
        ]
        for name in valid_names:
            assert ValidationRules.name(name) == name.strip()
    
    def test_name_invalid(self):
        """Test invalid names."""
        test_cases = [
            ("", "1-50 characters"),
            ("a" * 51, "1-50 characters"),
            ("Name123", "invalid characters"),
            ("Name@Email", "invalid characters")
        ]
        for name, expected_error in test_cases:
            with pytest.raises(ValueError) as exc_info:
                ValidationRules.name(name)
            assert expected_error in str(exc_info.value)
    
    def test_phone_valid(self):
        """Test valid phone numbers."""
        valid_phones = [
            "1234567890",
            "+1-234-567-8900",
            "(123) 456-7890",
            "123 456 7890"
        ]
        expected = [
            "1234567890",
            "12345678900",
            "1234567890",
            "1234567890"
        ]
        for phone, expected_clean in zip(valid_phones, expected):
            assert ValidationRules.phone(phone) == expected_clean
    
    def test_phone_invalid(self):
        """Test invalid phone numbers."""
        test_cases = [
            ("123", "10-15 digits"),
            ("1" * 16, "10-15 digits"),
            ("123-abc-4567", "only digits"),
            ("phone123", "only digits")
        ]
        for phone, expected_error in test_cases:
            with pytest.raises(ValueError) as exc_info:
                ValidationRules.phone(phone)
            assert expected_error in str(exc_info.value)


class TestInputValidator:
    """Test InputValidator class."""
    
    def test_validate_success(self):
        """Test successful validation."""
        rules = {
            'email': [ValidationRules.email],
            'password': [ValidationRules.password]
        }
        validator = InputValidator(rules)
        
        data = {
            'email': 'TEST@EXAMPLE.COM',
            'password': 'ValidP@ss123'
        }
        
        result = validator.validate(data)
        assert result['email'] == 'test@example.com'
        assert result['password'] == 'ValidP@ss123'
    
    def test_validate_optional_fields(self):
        """Test validation with optional fields."""
        rules = {
            'email': [ValidationRules.email],
            'phone': [ValidationRules.phone]
        }
        validator = InputValidator(rules)
        
        # Only email provided
        data = {'email': 'test@example.com'}
        result = validator.validate(data)
        assert result == {'email': 'test@example.com'}
        assert 'phone' not in result
    
    def test_validate_errors(self):
        """Test validation errors."""
        rules = {
            'email': [ValidationRules.email],
            'password': [ValidationRules.password]
        }
        validator = InputValidator(rules)
        
        data = {
            'email': 'invalid-email',
            'password': 'weak'
        }
        
        with pytest.raises(AppValidationError) as exc_info:
            validator.validate(data)
        
        errors = exc_info.value.details
        assert 'email' in errors
        assert 'password' in errors
    
    def test_validate_multiple_validators(self):
        """Test multiple validators per field."""
        def lowercase(value):
            return value.lower()
        
        def max_length(value):
            if len(value) > 10:
                raise ValueError("Too long")
            return value
        
        rules = {
            'username': [lowercase, max_length]
        }
        validator = InputValidator(rules)
        
        # Valid username
        result = validator.validate({'username': 'TESTUSER'})
        assert result['username'] == 'testuser'
        
        # Too long username
        with pytest.raises(AppValidationError):
            validator.validate({'username': 'verylongusername'})


class TestValidators:
    """Test pre-configured validators."""
    
    def test_registration_validator(self):
        """Test registration validator configuration."""
        validators = Validators.registration_validator()
        
        assert 'email' in validators
        assert 'password' in validators
        assert 'first_name' in validators
        assert 'last_name' in validators
        
        # All should have validation functions
        for field, funcs in validators.items():
            assert len(funcs) > 0
            assert callable(funcs[0])
    
    def test_login_validator(self):
        """Test login validator configuration."""
        validators = Validators.login_validator()
        
        assert 'email' in validators
        assert 'password' in validators
        
        # Test password required validation
        password_validator = validators['password'][0]
        with pytest.raises(ValueError) as exc_info:
            password_validator('')
        assert "Password required" in str(exc_info.value)
    
    def test_profile_update_validator(self):
        """Test profile update validator configuration."""
        validators = Validators.profile_update_validator()
        
        assert 'first_name' in validators
        assert 'last_name' in validators
        assert 'username' in validators
        assert 'phone' in validators
EOF < /dev/null