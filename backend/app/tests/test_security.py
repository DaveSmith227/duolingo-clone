"""
Security Tests

Test suite for JWT authentication, password hashing, and security utilities.
Tests all security functions including token generation, validation, and password handling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import jwt

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_access_token,
    verify_refresh_token,
    get_password_hash,
    verify_password,
    create_token_pair,
    extract_token_from_header,
    generate_secure_token,
    is_token_expired,
    get_token_subject,
    create_password_reset_token,
    verify_password_reset_token,
    ALGORITHM
)


class TestJWTTokenGeneration:
    """Test JWT token generation functions."""
    
    @patch('app.core.security.get_settings')
    def test_create_access_token_default_expiration(self, mock_get_settings):
        """Test creating access token with default expiration."""
        mock_settings = MagicMock()
        mock_settings.access_token_expire_minutes = 30
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_settings.app_name = "Test App"
        mock_get_settings.return_value = mock_settings
        
        user_data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(user_data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token structure
        payload = jwt.decode(token, mock_settings.secret_key, algorithms=[ALGORITHM])
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
        assert payload["iss"] == "Test App"
        assert "exp" in payload
        assert "iat" in payload
    
    @patch('app.core.security.get_settings')
    def test_create_access_token_custom_expiration(self, mock_get_settings):
        """Test creating access token with custom expiration."""
        mock_settings = MagicMock()
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_settings.app_name = "Test App"
        mock_get_settings.return_value = mock_settings
        
        user_data = {"sub": "user123"}
        custom_expiry = timedelta(minutes=60)
        token = create_access_token(user_data, expires_delta=custom_expiry)
        
        payload = jwt.decode(token, mock_settings.secret_key, algorithms=[ALGORITHM])
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + custom_expiry
        
        # Allow 5 second tolerance for test execution time
        assert abs((exp_time - expected_exp).total_seconds()) < 5
    
    @patch('app.core.security.get_settings')
    def test_create_refresh_token(self, mock_get_settings):
        """Test creating refresh token."""
        mock_settings = MagicMock()
        mock_settings.refresh_token_expire_days = 7
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_settings.app_name = "Test App"
        mock_get_settings.return_value = mock_settings
        
        user_data = {"sub": "user123"}
        token = create_refresh_token(user_data)
        
        payload = jwt.decode(token, mock_settings.secret_key, algorithms=[ALGORITHM])
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"
        assert payload["iss"] == "Test App"
    
    @patch('app.core.security.get_settings')
    def test_create_token_pair(self, mock_get_settings):
        """Test creating token pair (access + refresh)."""
        mock_settings = MagicMock()
        mock_settings.access_token_expire_minutes = 30
        mock_settings.refresh_token_expire_days = 7
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_settings.app_name = "Test App"
        mock_get_settings.return_value = mock_settings
        
        user_data = {"sub": "user123"}
        tokens = create_token_pair(user_data)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        
        # Verify both tokens are valid
        access_payload = jwt.decode(tokens["access_token"], mock_settings.secret_key, algorithms=[ALGORITHM])
        refresh_payload = jwt.decode(tokens["refresh_token"], mock_settings.secret_key, algorithms=[ALGORITHM])
        
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"
        assert access_payload["sub"] == refresh_payload["sub"]


class TestJWTTokenValidation:
    """Test JWT token validation functions."""
    
    @patch('app.core.security.get_settings')
    def test_verify_valid_token(self, mock_get_settings):
        """Test verifying valid token."""
        mock_settings = MagicMock()
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_get_settings.return_value = mock_settings
        
        # Create a test token
        payload = {
            "sub": "user123",
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, mock_settings.secret_key, algorithm=ALGORITHM)
        
        # Verify token
        verified_payload = verify_token(token)
        
        assert verified_payload is not None
        assert verified_payload["sub"] == "user123"
        assert verified_payload["type"] == "access"
    
    @patch('app.core.security.get_settings')
    def test_verify_expired_token(self, mock_get_settings):
        """Test verifying expired token."""
        mock_settings = MagicMock()
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_get_settings.return_value = mock_settings
        
        # Create expired token
        payload = {
            "sub": "user123",
            "type": "access",
            "exp": datetime.utcnow() - timedelta(minutes=30),  # Expired
            "iat": datetime.utcnow() - timedelta(minutes=60)
        }
        token = jwt.encode(payload, mock_settings.secret_key, algorithm=ALGORITHM)
        
        # Verify token
        verified_payload = verify_token(token)
        
        assert verified_payload is None
    
    @patch('app.core.security.get_settings')
    def test_verify_invalid_signature(self, mock_get_settings):
        """Test verifying token with invalid signature."""
        mock_settings = MagicMock()
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_get_settings.return_value = mock_settings
        
        # Create token with different secret
        payload = {
            "sub": "user123",
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, "different-secret-key", algorithm=ALGORITHM)
        
        # Verify token
        verified_payload = verify_token(token)
        
        assert verified_payload is None
    
    @patch('app.core.security.get_settings')
    def test_verify_access_token_specifically(self, mock_get_settings):
        """Test verifying access token specifically."""
        mock_settings = MagicMock()
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_get_settings.return_value = mock_settings
        
        # Create access token
        access_payload = {
            "sub": "user123",
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow()
        }
        access_token = jwt.encode(access_payload, mock_settings.secret_key, algorithm=ALGORITHM)
        
        # Create refresh token
        refresh_payload = {
            "sub": "user123",
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=7),
            "iat": datetime.utcnow()
        }
        refresh_token = jwt.encode(refresh_payload, mock_settings.secret_key, algorithm=ALGORITHM)
        
        # Test access token verification
        verified_access = verify_access_token(access_token)
        assert verified_access is not None
        assert verified_access["type"] == "access"
        
        # Test refresh token should fail access verification
        verified_refresh = verify_access_token(refresh_token)
        assert verified_refresh is None
    
    @patch('app.core.security.get_settings')
    def test_verify_refresh_token_specifically(self, mock_get_settings):
        """Test verifying refresh token specifically."""
        mock_settings = MagicMock()
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_get_settings.return_value = mock_settings
        
        # Create refresh token
        refresh_payload = {
            "sub": "user123",
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=7),
            "iat": datetime.utcnow()
        }
        refresh_token = jwt.encode(refresh_payload, mock_settings.secret_key, algorithm=ALGORITHM)
        
        # Test refresh token verification
        verified_refresh = verify_refresh_token(refresh_token)
        assert verified_refresh is not None
        assert verified_refresh["type"] == "refresh"


class TestPasswordHashing:
    """Test password hashing and verification functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert hashed != password  # Should be hashed
        assert len(hashed) > 20  # Bcrypt hashes are long
        assert hashed.startswith("$2b$")  # Bcrypt format
    
    def test_hash_empty_password(self):
        """Test hashing empty password raises error."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            get_password_hash("")
    
    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password_456"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_empty_password(self):
        """Test verifying empty password."""
        hashed = get_password_hash("test_password")
        
        assert verify_password("", hashed) is False
        assert verify_password("password", "") is False
    
    def test_password_hash_uniqueness(self):
        """Test that same password produces different hashes."""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2  # Should be different due to salt
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestTokenUtilities:
    """Test token utility functions."""
    
    def test_extract_token_from_header_valid(self):
        """Test extracting token from valid Authorization header."""
        token = "eyJhbGciOiJIUzI1NiJ9.test.token"
        header = f"Bearer {token}"
        
        extracted = extract_token_from_header(header)
        assert extracted == token
    
    def test_extract_token_from_header_invalid_scheme(self):
        """Test extracting token from invalid scheme."""
        token = "eyJhbGciOiJIUzI1NiJ9.test.token"
        header = f"Basic {token}"
        
        extracted = extract_token_from_header(header)
        assert extracted is None
    
    def test_extract_token_from_header_malformed(self):
        """Test extracting token from malformed header."""
        header = "BearerToken"
        
        extracted = extract_token_from_header(header)
        assert extracted is None
    
    def test_extract_token_from_header_empty(self):
        """Test extracting token from empty header."""
        extracted = extract_token_from_header("")
        assert extracted is None
        
        extracted = extract_token_from_header(None)
        assert extracted is None
    
    def test_generate_secure_token(self):
        """Test generating secure random token."""
        token = generate_secure_token()
        
        assert token is not None
        assert len(token) == 64  # 32 bytes as hex = 64 chars
        assert isinstance(token, str)
        
        # Generate another token to ensure uniqueness
        token2 = generate_secure_token()
        assert token != token2
    
    def test_generate_secure_token_custom_length(self):
        """Test generating secure token with custom length."""
        token = generate_secure_token(16)
        
        assert len(token) == 32  # 16 bytes as hex = 32 chars
    
    def test_is_token_expired_valid(self):
        """Test checking if valid token is expired."""
        # Create non-expired token
        payload = {
            "sub": "user123",
            "exp": datetime.utcnow() + timedelta(minutes=30)
        }
        token = jwt.encode(payload, "secret", algorithm=ALGORITHM)
        
        assert is_token_expired(token) is False
    
    def test_is_token_expired_expired(self):
        """Test checking if expired token is expired."""
        # Create expired token
        payload = {
            "sub": "user123",
            "exp": datetime.utcnow() - timedelta(minutes=30)
        }
        token = jwt.encode(payload, "secret", algorithm=ALGORITHM)
        
        assert is_token_expired(token) is True
    
    def test_is_token_expired_invalid(self):
        """Test checking if invalid token is expired."""
        invalid_token = "invalid.token.here"
        
        assert is_token_expired(invalid_token) is True
    
    def test_get_token_subject_valid(self):
        """Test getting subject from valid token."""
        payload = {
            "sub": "user123",
            "exp": datetime.utcnow() + timedelta(minutes=30)
        }
        token = jwt.encode(payload, "secret", algorithm=ALGORITHM)
        
        subject = get_token_subject(token)
        assert subject == "user123"
    
    def test_get_token_subject_no_subject(self):
        """Test getting subject from token without subject."""
        payload = {
            "exp": datetime.utcnow() + timedelta(minutes=30)
        }
        token = jwt.encode(payload, "secret", algorithm=ALGORITHM)
        
        subject = get_token_subject(token)
        assert subject is None
    
    def test_get_token_subject_invalid(self):
        """Test getting subject from invalid token."""
        invalid_token = "invalid.token.here"
        
        subject = get_token_subject(invalid_token)
        assert subject is None


class TestPasswordResetTokens:
    """Test password reset token functionality."""
    
    @patch('app.core.security.get_settings')
    def test_create_password_reset_token(self, mock_get_settings):
        """Test creating password reset token."""
        mock_settings = MagicMock()
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_settings.app_name = "Test App"
        mock_get_settings.return_value = mock_settings
        
        user_id = "user123"
        token = create_password_reset_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token structure
        payload = jwt.decode(token, mock_settings.secret_key, algorithms=[ALGORITHM])
        assert payload["sub"] == user_id
        assert payload["type"] == "password_reset"
        assert payload["iss"] == "Test App"
        
        # Verify expiration (should be 1 hour)
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + timedelta(hours=1)
        assert abs((exp_time - expected_exp).total_seconds()) < 5
    
    @patch('app.core.security.get_settings')
    def test_verify_password_reset_token_valid(self, mock_get_settings):
        """Test verifying valid password reset token."""
        mock_settings = MagicMock()
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_settings.app_name = "Test App"
        mock_get_settings.return_value = mock_settings
        
        user_id = "user123"
        token = create_password_reset_token(user_id)
        
        # Verify token
        verified_user_id = verify_password_reset_token(token)
        assert verified_user_id == user_id
    
    @patch('app.core.security.get_settings')
    def test_verify_password_reset_token_expired(self, mock_get_settings):
        """Test verifying expired password reset token."""
        mock_settings = MagicMock()
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_get_settings.return_value = mock_settings
        
        # Create expired token
        payload = {
            "sub": "user123",
            "type": "password_reset",
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
            "iat": datetime.utcnow() - timedelta(hours=2)
        }
        token = jwt.encode(payload, mock_settings.secret_key, algorithm=ALGORITHM)
        
        # Verify token
        verified_user_id = verify_password_reset_token(token)
        assert verified_user_id is None
    
    @patch('app.core.security.get_settings')
    def test_verify_password_reset_token_wrong_type(self, mock_get_settings):
        """Test verifying token with wrong type."""
        mock_settings = MagicMock()
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_get_settings.return_value = mock_settings
        
        # Create access token instead of password reset
        payload = {
            "sub": "user123",
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, mock_settings.secret_key, algorithm=ALGORITHM)
        
        # Verify token
        verified_user_id = verify_password_reset_token(token)
        assert verified_user_id is None


class TestTokenEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch('app.core.security.get_settings')
    def test_token_creation_with_jwt_error(self, mock_get_settings):
        """Test token creation when JWT encoding fails."""
        mock_settings = MagicMock()
        mock_settings.secret_key = None  # Invalid secret
        mock_get_settings.return_value = mock_settings
        
        user_data = {"sub": "user123"}
        
        with pytest.raises(Exception):
            create_access_token(user_data)
    
    def test_verify_token_with_invalid_format(self):
        """Test verifying token with invalid format."""
        invalid_tokens = [
            "invalid",
            "not.a.jwt",
            "still.not.valid.jwt.format",
            "",
            None
        ]
        
        for token in invalid_tokens:
            if token is not None:
                result = verify_token(token)
                assert result is None
    
    @patch('app.core.security.get_settings')
    def test_verify_token_with_missing_type(self, mock_get_settings):
        """Test verifying token without type field (should be allowed for backward compatibility)."""
        mock_settings = MagicMock()
        mock_settings.secret_key = "test-secret-key-32-characters-long"
        mock_get_settings.return_value = mock_settings
        
        # Create token without type
        payload = {
            "sub": "user123",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, mock_settings.secret_key, algorithm=ALGORITHM)
        
        # Verify token (should succeed for backward compatibility)
        result = verify_token(token)
        assert result is not None
        assert result["sub"] == "user123"
    
    def test_password_verification_edge_cases(self):
        """Test password verification edge cases."""
        # Test with None values
        assert verify_password(None, "hash") is False
        assert verify_password("password", None) is False
        assert verify_password(None, None) is False
        
        # Test with invalid hash format
        assert verify_password("password", "invalid_hash") is False
        
        # Test with very long password
        long_password = "a" * 1000
        hashed = get_password_hash(long_password)
        assert verify_password(long_password, hashed) is True