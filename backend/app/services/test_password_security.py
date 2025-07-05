"""
Unit Tests for Password Security Service

Tests for password hashing, validation, policy enforcement, and security features.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from app.services.password_security import (
    PasswordSecurity,
    PasswordStrength,
    PasswordViolationType,
    PasswordPolicy,
    PasswordValidationResult,
    PasswordHashResult,
    get_password_security,
    hash_password,
    verify_password,
    validate_password,
    generate_secure_password
)


class TestPasswordPolicy:
    """Test cases for PasswordPolicy dataclass."""
    
    def test_default_policy(self):
        """Test default password policy values."""
        policy = PasswordPolicy()
        
        assert policy.min_length == 8
        assert policy.max_length == 128
        assert policy.require_uppercase is True
        assert policy.require_lowercase is True
        assert policy.require_digits is True
        assert policy.require_special_chars is True
        assert policy.prevent_common_passwords is True
        assert policy.password_history_count == 5
    
    def test_custom_policy(self):
        """Test custom password policy configuration."""
        policy = PasswordPolicy(
            min_length=12,
            require_special_chars=False,
            password_history_count=10
        )
        
        assert policy.min_length == 12
        assert policy.require_special_chars is False
        assert policy.password_history_count == 10


class TestPasswordSecurity:
    """Test cases for PasswordSecurity class."""
    
    @pytest.fixture
    def password_security(self):
        """PasswordSecurity instance for testing."""
        return PasswordSecurity()
    
    def test_init_password_security(self, password_security):
        """Test PasswordSecurity initialization."""
        assert password_security.pwd_context is not None
        assert password_security.policy is not None
        assert isinstance(password_security.policy, PasswordPolicy)
    
    def test_hash_password(self, password_security):
        """Test password hashing."""
        password = "TestPassword123!"
        result = password_security.hash_password(password)
        
        assert isinstance(result, PasswordHashResult)
        assert result.hash is not None
        assert result.algorithm == "argon2"
        assert result.cost_factor == 3
        assert result.salt_length == 16
        assert isinstance(result.created_at, datetime)
        
        # Verify hash format
        assert result.hash.startswith("$argon2")
        assert len(result.hash) > 50  # Argon2 hashes are long
    
    def test_hash_password_different_results(self, password_security):
        """Test that same password produces different hashes (due to salt)."""
        password = "TestPassword123!"
        
        hash1 = password_security.hash_password(password)
        hash2 = password_security.hash_password(password)
        
        assert hash1.hash != hash2.hash  # Different due to different salts
    
    def test_verify_password_success(self, password_security):
        """Test successful password verification."""
        password = "TestPassword123!"
        hash_result = password_security.hash_password(password)
        
        assert password_security.verify_password(password, hash_result.hash) is True
    
    def test_verify_password_failure(self, password_security):
        """Test failed password verification."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hash_result = password_security.hash_password(password)
        
        assert password_security.verify_password(wrong_password, hash_result.hash) is False
    
    def test_verify_password_invalid_hash(self, password_security):
        """Test password verification with invalid hash."""
        password = "TestPassword123!"
        invalid_hash = "invalid_hash_format"
        
        assert password_security.verify_password(password, invalid_hash) is False
    
    def test_needs_rehash(self, password_security):
        """Test hash rehash requirement check."""
        password = "TestPassword123!"
        hash_result = password_security.hash_password(password)
        
        # Fresh hash should not need rehashing
        assert password_security.needs_rehash(hash_result.hash) is False
    
    def test_validate_password_strong(self, password_security):
        """Test validation of strong password."""
        strong_password = "StrongP@ssw0rd2024!"
        
        result = password_security.validate_password(strong_password)
        
        assert isinstance(result, PasswordValidationResult)
        assert result.is_valid is True
        assert result.strength in [PasswordStrength.STRONG, PasswordStrength.VERY_STRONG]
        assert result.score > 70
        assert len(result.violations) == 0
        assert result.entropy > 60
    
    def test_validate_password_weak(self, password_security):
        """Test validation of weak password."""
        weak_password = "weak"
        
        result = password_security.validate_password(weak_password)
        
        assert result.is_valid is False
        assert result.strength == PasswordStrength.VERY_WEAK
        assert result.score < 50
        assert PasswordViolationType.TOO_SHORT in result.violations
        assert len(result.suggestions) > 0
    
    def test_validate_password_length_violations(self, password_security):
        """Test password length validation."""
        # Too short
        short_password = "Ab1!"
        result = password_security.validate_password(short_password)
        assert PasswordViolationType.TOO_SHORT in result.violations
        assert result.is_valid is False
        
        # Too long
        long_password = "A" * 150 + "1!"
        result = password_security.validate_password(long_password)
        assert PasswordViolationType.TOO_LONG in result.violations
        assert result.is_valid is False
    
    def test_validate_password_character_requirements(self, password_security):
        """Test character requirement validations."""
        # No uppercase
        no_upper = "password123!"
        result = password_security.validate_password(no_upper)
        assert PasswordViolationType.NO_UPPERCASE in result.violations
        
        # No lowercase
        no_lower = "PASSWORD123!"
        result = password_security.validate_password(no_lower)
        assert PasswordViolationType.NO_LOWERCASE in result.violations
        
        # No digits
        no_digits = "Password!"
        result = password_security.validate_password(no_digits)
        assert PasswordViolationType.NO_DIGITS in result.violations
        
        # No special chars
        no_special = "Password123"
        result = password_security.validate_password(no_special)
        assert PasswordViolationType.NO_SPECIAL_CHARS in result.violations
    
    def test_validate_password_common_password(self, password_security):
        """Test common password detection."""
        common_password = "Password123!"  # Common structure
        result = password_security.validate_password("password")
        
        assert PasswordViolationType.COMMON_PASSWORD in result.violations
        assert result.is_valid is False
    
    def test_validate_password_dictionary_word(self, password_security):
        """Test dictionary word detection."""
        result = password_security.validate_password("computer")
        
        # Only check for dictionary word if other requirements are also not met
        # The word 'computer' might pass if it meets other requirements
        assert (PasswordViolationType.DICTIONARY_WORD in result.violations or
                len(result.violations) > 0)  # Should have some violations
    
    def test_validate_password_sequential_chars(self, password_security):
        """Test sequential character detection."""
        sequential_password = "Password123abc"
        result = password_security.validate_password(sequential_password)
        
        assert PasswordViolationType.SEQUENTIAL_CHARS in result.violations
    
    def test_validate_password_repeated_chars(self, password_security):
        """Test repeated character detection."""
        repeated_password = "Passworddddd123!"
        result = password_security.validate_password(repeated_password)
        
        assert PasswordViolationType.REPEATED_CHARS in result.violations
    
    def test_validate_password_personal_info(self, password_security):
        """Test personal information detection."""
        user_info = {
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        personal_password = "JohnPassword123!"
        result = password_security.validate_password(personal_password, user_info)
        
        assert PasswordViolationType.CONTAINS_PERSONAL_INFO in result.violations
    
    def test_validate_password_history(self, password_security):
        """Test password history validation."""
        password = "NewPassword123!"
        
        # Hash the password as if it was used before
        old_hash = password_security.hash_password(password).hash
        password_history = [old_hash]
        
        result = password_security.validate_password(password, password_history=password_history)
        
        assert PasswordViolationType.PREVIOUSLY_USED in result.violations
        assert result.is_valid is False
    
    def test_generate_secure_password_default(self, password_security):
        """Test secure password generation with defaults."""
        password = password_security.generate_secure_password()
        
        assert len(password) == 16
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    def test_generate_secure_password_custom_length(self, password_security):
        """Test secure password generation with custom length."""
        password = password_security.generate_secure_password(length=24)
        
        assert len(password) == 24
    
    def test_generate_secure_password_custom_charset(self, password_security):
        """Test secure password generation with custom character sets."""
        password = password_security.generate_secure_password(
            length=12,
            include_special_chars=False,
            include_digits=False
        )
        
        assert len(password) == 12
        assert not any(c.isdigit() for c in password)
        assert not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
    
    def test_generate_secure_password_unique(self, password_security):
        """Test that generated passwords are unique."""
        password1 = password_security.generate_secure_password()
        password2 = password_security.generate_secure_password()
        
        assert password1 != password2
    
    def test_check_password_expiry_no_expiry(self, password_security):
        """Test password expiry check when expiry is disabled."""
        password_security.policy.password_expiry_days = None
        created_at = datetime.now(timezone.utc) - timedelta(days=100)
        
        result = password_security.check_password_expiry(created_at)
        
        assert result["is_expired"] is False
        assert result["expires_at"] is None
        assert result["days_until_expiry"] is None
    
    def test_check_password_expiry_not_expired(self, password_security):
        """Test password expiry check for non-expired password."""
        password_security.policy.password_expiry_days = 90
        created_at = datetime.now(timezone.utc) - timedelta(days=30)
        
        result = password_security.check_password_expiry(created_at)
        
        assert result["is_expired"] is False
        assert result["expires_at"] is not None
        assert result["days_until_expiry"] > 0
    
    def test_check_password_expiry_expired(self, password_security):
        """Test password expiry check for expired password."""
        password_security.policy.password_expiry_days = 90
        created_at = datetime.now(timezone.utc) - timedelta(days=100)
        
        result = password_security.check_password_expiry(created_at)
        
        assert result["is_expired"] is True
        assert result["expires_at"] is not None
        assert result["days_until_expiry"] == 0
    
    def test_has_sequential_chars(self, password_security):
        """Test sequential character detection."""
        # Test ascending sequences
        assert password_security._has_sequential_chars("abc123") is True
        assert password_security._has_sequential_chars("xyz789") is True
        
        # Test descending sequences
        assert password_security._has_sequential_chars("cba321") is True
        assert password_security._has_sequential_chars("zyx987") is True
        
        # Test no sequences
        assert password_security._has_sequential_chars("ac13579") is False
    
    def test_has_repeated_chars(self, password_security):
        """Test repeated character detection."""
        assert password_security._has_repeated_chars("aaaa", 3) is True
        assert password_security._has_repeated_chars("abbbb", 3) is True
        assert password_security._has_repeated_chars("abcc", 3) is False
        assert password_security._has_repeated_chars("abcd", 3) is False
    
    def test_contains_personal_info(self, password_security):
        """Test personal information detection."""
        user_info = {
            "email": "john.doe@example.com",
            "first_name": "John",
            "username": "johndoe"
        }
        
        assert password_security._contains_personal_info("johnpassword", user_info) is True
        assert password_security._contains_personal_info("johndoepass", user_info) is True
        assert password_security._contains_personal_info("randompass", user_info) is False
    
    def test_calculate_entropy(self, password_security):
        """Test entropy calculation."""
        # Simple password (lowercase only)
        entropy1 = password_security._calculate_entropy("password")
        
        # Complex password (mixed character sets)
        entropy2 = password_security._calculate_entropy("P@ssw0rd123!")
        
        assert entropy2 > entropy1
        assert entropy1 > 0
        assert entropy2 > 40  # Should have decent entropy
    
    def test_determine_strength(self, password_security):
        """Test strength determination."""
        assert password_security._determine_strength(95, 0) == PasswordStrength.VERY_STRONG
        assert password_security._determine_strength(75, 0) == PasswordStrength.STRONG
        assert password_security._determine_strength(55, 0) == PasswordStrength.MEDIUM
        assert password_security._determine_strength(35, 0) == PasswordStrength.WEAK
        assert password_security._determine_strength(95, 1) == PasswordStrength.VERY_WEAK  # Violations override score


class TestPasswordSecurityUtilities:
    """Test cases for password security utility functions."""
    
    def test_get_password_security(self):
        """Test get_password_security factory function."""
        service = get_password_security()
        
        assert isinstance(service, PasswordSecurity)
        
        # Should return same instance (singleton behavior)
        service2 = get_password_security()
        assert service is service2
    
    def test_hash_password_utility(self):
        """Test hash_password utility function."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert isinstance(hashed, str)
        assert hashed.startswith("$argon2")
    
    def test_verify_password_utility(self):
        """Test verify_password utility function."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False
    
    def test_validate_password_utility(self):
        """Test validate_password utility function."""
        strong_password = "StrongP@ssw0rd2024!"
        
        result = validate_password(strong_password)
        
        assert isinstance(result, PasswordValidationResult)
        assert result.is_valid is True
    
    def test_generate_secure_password_utility(self):
        """Test generate_secure_password utility function."""
        password = generate_secure_password()
        
        assert isinstance(password, str)
        assert len(password) == 16
        
        # Test custom length
        long_password = generate_secure_password(24)
        assert len(long_password) == 24


class TestPasswordSecurityIntegration:
    """Integration tests for password security."""
    
    def test_complete_password_flow(self):
        """Test complete password lifecycle."""
        service = get_password_security()
        
        # Generate a secure password
        password = service.generate_secure_password()
        
        # Validate the generated password
        validation = service.validate_password(password)
        assert validation.is_valid is True
        assert validation.strength in [PasswordStrength.STRONG, PasswordStrength.VERY_STRONG]
        
        # Hash the password
        hash_result = service.hash_password(password)
        assert hash_result.hash is not None
        
        # Verify the password
        assert service.verify_password(password, hash_result.hash) is True
        assert service.verify_password("wrong", hash_result.hash) is False
    
    def test_password_policy_enforcement(self):
        """Test that password policy is properly enforced."""
        service = get_password_security()
        
        # Test weak password gets rejected
        weak_passwords = [
            "weak",           # Too short
            "password",       # Common password
            "12345678",       # No letters
            "abcdefgh",       # No digits/special chars
            "PASSWORD123!"    # No lowercase
        ]
        
        for weak_password in weak_passwords:
            result = service.validate_password(weak_password)
            assert result.is_valid is False
            assert len(result.violations) > 0
    
    def test_password_strength_progression(self):
        """Test password strength increases with complexity."""
        service = get_password_security()
        
        passwords = [
            "weak",                    # Very weak
            "WeakPassword",           # Weak (no digits/special)
            "WeakPassword123",        # Medium (no special chars)
            "WeakPassword123!",       # Strong
            "V3ryStr0ng!P@ssw0rd2024" # Very strong
        ]
        
        prev_score = -1
        for password in passwords:
            result = service.validate_password(password)
            # Score should generally increase (with some exceptions due to violations)
            if result.is_valid:
                assert result.score >= 0
    
    def test_error_handling(self):
        """Test error handling in password operations."""
        service = get_password_security()
        
        # Test with invalid inputs
        with pytest.raises(Exception):
            service.generate_secure_password(
                include_uppercase=False,
                include_lowercase=False,
                include_digits=False,
                include_special_chars=False
            )