"""
Comprehensive tests for AuthService.
Tests all authentication flows and edge cases.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.models.user import User, UserProfile
from app.models.auth import AuthSession
from app.core.exceptions import (
    ValidationError, DuplicateError, AuthenticationError,
    RateLimitExceededError, AccountLockedException
)


@pytest.fixture
def db_session():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def auth_service(db_session):
    """Create AuthService instance with mocked dependencies."""
    return AuthService(db_session)


@pytest.fixture
def sample_user():
    """Create sample user for testing."""
    user = User(
        id="user123",
        email="test@example.com",
        hashed_password="$argon2id$v=19$m=65536,t=3,p=4$...",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow()
    )
    user.profile = UserProfile(
        user_id="user123",
        first_name="Test",
        last_name="User"
    )
    return user


class TestAuthService:
    """Test suite for AuthService."""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, db_session):
        """Test successful user registration."""
        # Mock repository responses
        with patch.object(auth_service.user_repo, 'get_by_email', return_value=None):
            with patch.object(auth_service.user_repo, 'create') as mock_create:
                # Configure mock
                new_user = Mock(id="new123", email="new@example.com")
                new_user.profile = Mock(first_name="New", last_name="User")
                mock_create.return_value = new_user
                
                # Test registration
                user, session_data = await auth_service.register_user(
                    email="new@example.com",
                    password="StrongP@ss123",
                    first_name="New",
                    last_name="User",
                    client_info={"ip_address": "127.0.0.1"}
                )
                
                # Verify results
                assert user.id == "new123"
                assert session_data["access_token"]
                assert session_data["refresh_token"]
                assert session_data["expires_in"] == 900
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_service):
        """Test registration with duplicate email."""
        # Mock existing user
        with patch.object(auth_service.user_repo, 'get_by_email', return_value=Mock()):
            # Should raise DuplicateError
            with pytest.raises(DuplicateError):
                await auth_service.register_user(
                    email="existing@example.com",
                    password="StrongP@ss123",
                    first_name="Test",
                    last_name="User",
                    client_info={"ip_address": "127.0.0.1"}
                )
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, auth_service):
        """Test registration with weak password."""
        with patch.object(auth_service.user_repo, 'get_by_email', return_value=None):
            # Should raise ValidationError
            with pytest.raises(ValidationError) as exc_info:
                await auth_service.register_user(
                    email="test@example.com",
                    password="weak",
                    first_name="Test",
                    last_name="User",
                    client_info={"ip_address": "127.0.0.1"}
                )
            assert "Password must be at least 8 characters" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_login_success(self, auth_service, sample_user):
        """Test successful login."""
        # Mock repository and password verification
        with patch.object(auth_service.user_repo, 'get_by_email', return_value=sample_user):
            with patch.object(auth_service.password_security, 'verify_password', return_value=True):
                with patch.object(auth_service.account_lockout, 'check_account_status', return_value=True):
                    # Test login
                    user, session_data = await auth_service.login_user(
                        email="test@example.com",
                        password="correct_password",
                        client_info={"ip_address": "127.0.0.1"}
                    )
                    
                    # Verify results
                    assert user.id == "user123"
                    assert session_data["access_token"]
                    assert session_data["refresh_token"]
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, auth_service, sample_user):
        """Test login with invalid password."""
        # Mock repository and password verification
        with patch.object(auth_service.user_repo, 'get_by_email', return_value=sample_user):
            with patch.object(auth_service.password_security, 'verify_password', return_value=False):
                # Should raise AuthenticationError
                with pytest.raises(AuthenticationError):
                    await auth_service.login_user(
                        email="test@example.com",
                        password="wrong_password",
                        client_info={"ip_address": "127.0.0.1"}
                    )
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, auth_service):
        """Test login with non-existent user."""
        # Mock repository to return None
        with patch.object(auth_service.user_repo, 'get_by_email', return_value=None):
            # Should raise AuthenticationError
            with pytest.raises(AuthenticationError):
                await auth_service.login_user(
                    email="nonexistent@example.com",
                    password="any_password",
                    client_info={"ip_address": "127.0.0.1"}
                )
    
    @pytest.mark.asyncio
    async def test_login_locked_account(self, auth_service, sample_user):
        """Test login with locked account."""
        # Mock repository and lockout check
        with patch.object(auth_service.user_repo, 'get_by_email', return_value=sample_user):
            with patch.object(auth_service.account_lockout, 'check_account_status', return_value=False):
                # Should raise AccountLockedException
                with pytest.raises(AccountLockedException):
                    await auth_service.login_user(
                        email="test@example.com",
                        password="correct_password",
                        client_info={"ip_address": "127.0.0.1"}
                    )
    
    @pytest.mark.asyncio
    async def test_verify_mfa_success(self, auth_service, sample_user):
        """Test successful MFA verification."""
        # Mock MFA service
        with patch.object(auth_service.mfa_service, 'verify_totp_code', return_value=True):
            with patch.object(auth_service.user_repo, 'get_by_id', return_value=sample_user):
                # Test MFA verification
                user, session_data = await auth_service.verify_mfa(
                    user_id="user123",
                    code="123456",
                    client_info={"ip_address": "127.0.0.1"}
                )
                
                # Verify results
                assert user.id == "user123"
                assert session_data["access_token"]
    
    @pytest.mark.asyncio
    async def test_verify_mfa_invalid_code(self, auth_service):
        """Test MFA verification with invalid code."""
        # Mock MFA service
        with patch.object(auth_service.mfa_service, 'verify_totp_code', return_value=False):
            # Should raise AuthenticationError
            with pytest.raises(AuthenticationError):
                await auth_service.verify_mfa(
                    user_id="user123",
                    code="wrong_code",
                    client_info={"ip_address": "127.0.0.1"}
                )
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, auth_service):
        """Test rate limiting functionality."""
        # Mock rate limiter to exceed limit
        with patch.object(
            auth_service.rate_limiter, 
            'check_rate_limit',
            return_value={"allowed": False, "retry_after": 3600}
        ):
            # Should raise RateLimitExceededError
            with pytest.raises(RateLimitExceededError):
                await auth_service.login_user(
                    email="test@example.com",
                    password="password",
                    client_info={"ip_address": "127.0.0.1"}
                )
    
    @pytest.mark.asyncio
    async def test_session_creation(self, auth_service, sample_user):
        """Test session creation during login."""
        # Mock dependencies
        with patch.object(auth_service.user_repo, 'get_by_email', return_value=sample_user):
            with patch.object(auth_service.password_security, 'verify_password', return_value=True):
                with patch.object(auth_service.account_lockout, 'check_account_status', return_value=True):
                    with patch.object(auth_service.session_manager, 'create_session') as mock_create:
                        # Configure mock
                        mock_create.return_value = {
                            "access_token": "access_token_123",
                            "refresh_token": "refresh_token_123",
                            "expires_in": 900
                        }
                        
                        # Test login
                        user, session_data = await auth_service.login_user(
                            email="test@example.com",
                            password="password",
                            client_info={"ip_address": "127.0.0.1"}
                        )
                        
                        # Verify session creation was called
                        mock_create.assert_called_once()
                        assert session_data["access_token"] == "access_token_123"
EOF < /dev/null