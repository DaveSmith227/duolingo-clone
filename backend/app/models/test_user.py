"""
Unit Tests for User Management Models

Comprehensive test coverage for User and OAuthProvider models including
validation, constraints, relationships, and business logic.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.models.base import Base
from app.models.user import User, OAuthProvider


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        'email': 'test@example.com',
        'name': 'Test User',
        'password_hash': 'hashed_password_123',
        'daily_xp_goal': 30,
        'timezone': 'America/New_York'
    }


@pytest.fixture
def sample_oauth_data():
    """Sample OAuth provider data for testing."""
    return {
        'provider': 'google',
        'provider_user_id': 'google_user_123',
        'access_token': 'access_token_abc',
        'refresh_token': 'refresh_token_xyz'
    }


class TestUserModel:
    """Test cases for the User model."""
    
    def test_user_creation_with_valid_data(self, db_session, sample_user_data):
        """Test creating a user with valid data."""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email == 'test@example.com'
        assert user.name == 'Test User'
        assert user.daily_xp_goal == 30
        assert user.timezone == 'America/New_York'
        assert user.is_email_verified is False
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_user_email_validation_valid_emails(self, db_session):
        """Test user creation with various valid email formats."""
        valid_emails = [
            'user@example.com',
            'test.email@domain.co.uk',
            'user+label@example.org',
            'user123@test-domain.com'
        ]
        
        for email in valid_emails:
            user = User(email=email, name='Test User')
            db_session.add(user)
            db_session.commit()
            
            assert user.email == email.lower()
            db_session.delete(user)
            db_session.commit()
    
    def test_user_email_validation_invalid_emails(self, db_session):
        """Test user creation with invalid email formats."""
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'user@',
            'user..email@example.com',
            'user@example',
            ''
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email format|Email is required"):
                User(email=email, name='Test User')
    
    def test_user_email_uniqueness(self, db_session, sample_user_data):
        """Test that email addresses must be unique."""
        # Create first user
        user1 = User(**sample_user_data)
        db_session.add(user1)
        db_session.commit()
        
        # Try to create second user with same email
        user2_data = sample_user_data.copy()
        user2_data['name'] = 'Another User'
        user2 = User(**user2_data)
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_user_name_validation(self, db_session):
        """Test user name validation."""
        # Valid names
        valid_names = ['John', 'Mary Jane', 'José María', 'X']
        for name in valid_names:
            user = User(email=f'test{len(name)}@example.com', name=name)
            db_session.add(user)
            db_session.commit()
            assert user.name == name
            db_session.delete(user)
            db_session.commit()
        
        # Invalid names
        invalid_names = ['', '   ', None]
        for name in invalid_names:
            with pytest.raises(ValueError, match="Name is required"):
                User(email='test@example.com', name=name)
    
    def test_user_daily_xp_goal_validation(self, db_session):
        """Test daily XP goal validation."""
        # Valid XP goals
        valid_goals = [10, 20, 30, 50]
        for goal in valid_goals:
            user = User(
                email=f'test{goal}@example.com',
                name='Test User',
                daily_xp_goal=goal
            )
            db_session.add(user)
            db_session.commit()
            assert user.daily_xp_goal == goal
            db_session.delete(user)
            db_session.commit()
        
        # Invalid XP goals should be caught by database constraint
        invalid_goals = [5, 15, 40, 100]
        for goal in invalid_goals:
            user = User(
                email=f'invalid{goal}@example.com',
                name='Test User',
                daily_xp_goal=goal
            )
            db_session.add(user)
            with pytest.raises(IntegrityError):
                db_session.commit()
            db_session.rollback()
    
    def test_user_timezone_validation(self, db_session):
        """Test timezone validation."""
        # Valid timezones
        valid_timezones = ['UTC', 'America/New_York', 'Europe/London', 'Asia/Tokyo']
        for tz in valid_timezones:
            user = User(
                email=f'test_{tz.replace("/", "_")}@example.com',
                name='Test User',
                timezone=tz
            )
            db_session.add(user)
            db_session.commit()
            assert user.timezone == tz
            db_session.delete(user)
            db_session.commit()
        
        # Invalid timezone format
        with pytest.raises(ValueError, match="Invalid timezone format"):
            User(email='test@example.com', name='Test User', timezone='Invalid@Timezone!')
    
    def test_user_properties(self, db_session, sample_user_data):
        """Test user model properties."""
        # Test OAuth-only user
        oauth_user_data = sample_user_data.copy()
        oauth_user_data['password_hash'] = None
        oauth_user = User(**oauth_user_data)
        
        assert oauth_user.is_oauth_only is True
        assert oauth_user.has_verified_email is False
        
        # Test regular user
        regular_user = User(**sample_user_data)
        assert regular_user.is_oauth_only is False
        
        # Test email verification
        regular_user.is_email_verified = True
        assert regular_user.has_verified_email is True
    
    def test_user_password_reset_functionality(self, db_session, sample_user_data):
        """Test password reset token functionality."""
        user = User(**sample_user_data)
        
        # Initially no reset token
        assert user.is_password_reset_valid is False
        
        # Set valid reset token
        user.password_reset_token = 'reset_token_123'
        user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        assert user.is_password_reset_valid is True
        
        # Set expired reset token
        user.password_reset_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert user.is_password_reset_valid is False
        
        # Clear reset token
        user.clear_password_reset()
        assert user.password_reset_token is None
        assert user.password_reset_expires_at is None
    
    def test_user_email_verification_functionality(self, db_session, sample_user_data):
        """Test email verification functionality."""
        user = User(**sample_user_data)
        user.email_verification_token = 'verify_token_123'
        
        assert user.is_email_verified is False
        assert user.email_verification_token == 'verify_token_123'
        
        user.clear_email_verification()
        assert user.email_verification_token is None
        assert user.is_email_verified is True
    
    def test_user_soft_delete(self, db_session, sample_user_data):
        """Test soft delete functionality."""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        assert user.is_deleted is False
        assert user.deleted_at is None
        
        user.soft_delete()
        assert user.is_deleted is True
        assert user.deleted_at is not None
        
        user.restore()
        assert user.is_deleted is False
        assert user.deleted_at is None
    
    def test_user_string_representation(self, sample_user_data):
        """Test user string representation."""
        user = User(**sample_user_data)
        user.id = uuid.uuid4()
        
        repr_str = repr(user)
        assert 'User' in repr_str
        assert str(user.id) in repr_str
        assert user.email in repr_str
        assert user.name in repr_str


class TestOAuthProviderModel:
    """Test cases for the OAuthProvider model."""
    
    def test_oauth_provider_creation(self, db_session, sample_user_data, sample_oauth_data):
        """Test creating an OAuth provider with valid data."""
        # Create user first
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        # Create OAuth provider
        oauth_data = sample_oauth_data.copy()
        oauth_data['user_id'] = str(user.id)
        oauth_provider = OAuthProvider(**oauth_data)
        db_session.add(oauth_provider)
        db_session.commit()
        
        assert oauth_provider.id is not None
        assert oauth_provider.user_id == str(user.id)
        assert oauth_provider.provider == 'google'
        assert oauth_provider.provider_user_id == 'google_user_123'
        assert oauth_provider.access_token == 'access_token_abc'
        assert oauth_provider.refresh_token == 'refresh_token_xyz'
    
    def test_oauth_provider_validation(self, db_session, sample_user_data):
        """Test OAuth provider validation."""
        # Create user first
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        # Valid providers
        valid_providers = ['google', 'tiktok', 'facebook', 'apple']
        for provider in valid_providers:
            oauth = OAuthProvider(
                user_id=str(user.id),
                provider=provider,
                provider_user_id=f'{provider}_user_123'
            )
            db_session.add(oauth)
            db_session.commit()
            assert oauth.provider == provider
            db_session.delete(oauth)
            db_session.commit()
        
        # Invalid providers
        invalid_providers = ['twitter', 'linkedin', 'github', '']
        for provider in invalid_providers:
            with pytest.raises(ValueError, match="Provider must be one of|Provider is required"):
                OAuthProvider(
                    user_id=str(user.id),
                    provider=provider,
                    provider_user_id='user_123'
                )
    
    def test_oauth_provider_user_id_validation(self, db_session, sample_user_data):
        """Test OAuth provider user ID validation."""
        # Create user first
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        # Valid provider user IDs
        valid_ids = ['123456789', 'user_abc_123', 'long_identifier_string']
        for provider_user_id in valid_ids:
            oauth = OAuthProvider(
                user_id=str(user.id),
                provider='google',
                provider_user_id=provider_user_id
            )
            assert oauth.provider_user_id == provider_user_id
        
        # Invalid provider user IDs
        invalid_ids = ['', '   ', None]
        for provider_user_id in invalid_ids:
            with pytest.raises(ValueError, match="Provider user ID is required"):
                OAuthProvider(
                    user_id=str(user.id),
                    provider='google',
                    provider_user_id=provider_user_id
                )
    
    def test_oauth_provider_unique_constraint(self, db_session, sample_user_data):
        """Test unique constraint on provider + provider_user_id."""
        # Create user first
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        # Create first OAuth provider
        oauth1 = OAuthProvider(
            user_id=str(user.id),
            provider='google',
            provider_user_id='google_user_123'
        )
        db_session.add(oauth1)
        db_session.commit()
        
        # Try to create second OAuth provider with same provider + provider_user_id
        oauth2 = OAuthProvider(
            user_id=str(user.id),
            provider='google',
            provider_user_id='google_user_123'
        )
        db_session.add(oauth2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_oauth_provider_token_expiration(self, db_session, sample_user_data, sample_oauth_data):
        """Test token expiration functionality."""
        # Create user and OAuth provider
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        oauth_data = sample_oauth_data.copy()
        oauth_data['user_id'] = str(user.id)
        oauth_provider = OAuthProvider(**oauth_data)
        
        # No expiration time set
        assert oauth_provider.is_token_expired is False
        assert oauth_provider.needs_refresh is False
        
        # Set future expiration
        oauth_provider.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        assert oauth_provider.is_token_expired is False
        assert oauth_provider.needs_refresh is False
        
        # Set past expiration
        oauth_provider.token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert oauth_provider.is_token_expired is True
        assert oauth_provider.needs_refresh is True
        
        # Remove refresh token
        oauth_provider.refresh_token = None
        assert oauth_provider.needs_refresh is False
    
    def test_oauth_provider_update_tokens(self, db_session, sample_user_data, sample_oauth_data):
        """Test token update functionality."""
        # Create user and OAuth provider
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        oauth_data = sample_oauth_data.copy()
        oauth_data['user_id'] = str(user.id)
        oauth_provider = OAuthProvider(**oauth_data)
        
        # Update tokens without expiration
        oauth_provider.update_tokens('new_access_token')
        assert oauth_provider.access_token == 'new_access_token'
        assert oauth_provider.refresh_token == 'refresh_token_xyz'  # Unchanged
        
        # Update tokens with refresh token
        oauth_provider.update_tokens('newer_access_token', 'new_refresh_token')
        assert oauth_provider.access_token == 'newer_access_token'
        assert oauth_provider.refresh_token == 'new_refresh_token'
        
        # Update tokens with expiration
        with patch('app.models.user.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            
            oauth_provider.update_tokens('final_access_token', expires_in=3600)
            assert oauth_provider.access_token == 'final_access_token'
            expected_expiry = mock_now + timedelta(seconds=3600)
            assert oauth_provider.token_expires_at == expected_expiry
    
    def test_oauth_provider_relationship(self, db_session, sample_user_data, sample_oauth_data):
        """Test relationship between User and OAuthProvider."""
        # Create user
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        # Create OAuth providers
        for provider in ['google', 'tiktok']:
            oauth_data = sample_oauth_data.copy()
            oauth_data['user_id'] = str(user.id)
            oauth_data['provider'] = provider
            oauth_data['provider_user_id'] = f'{provider}_user_123'
            
            oauth_provider = OAuthProvider(**oauth_data)
            db_session.add(oauth_provider)
        
        db_session.commit()
        
        # Test relationship
        db_session.refresh(user)
        assert len(user.oauth_providers) == 2
        assert user.oauth_providers[0].provider in ['google', 'tiktok']
        assert user.oauth_providers[1].provider in ['google', 'tiktok']
        
        # Test back reference
        oauth_provider = user.oauth_providers[0]
        assert oauth_provider.user == user
    
    def test_oauth_provider_cascade_delete(self, db_session, sample_user_data, sample_oauth_data):
        """Test that OAuth providers are deleted when user is deleted."""
        # Create user and OAuth provider
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        oauth_data = sample_oauth_data.copy()
        oauth_data['user_id'] = str(user.id)
        oauth_provider = OAuthProvider(**oauth_data)
        db_session.add(oauth_provider)
        db_session.commit()
        
        oauth_provider_id = oauth_provider.id
        
        # Delete user
        db_session.delete(user)
        db_session.commit()
        
        # OAuth provider should be deleted too
        deleted_oauth = db_session.query(OAuthProvider).filter_by(id=oauth_provider_id).first()
        assert deleted_oauth is None
    
    def test_oauth_provider_string_representation(self, sample_user_data, sample_oauth_data):
        """Test OAuth provider string representation."""
        oauth_provider = OAuthProvider(**sample_oauth_data)
        oauth_provider.id = uuid.uuid4()
        oauth_provider.user_id = str(uuid.uuid4())
        
        repr_str = repr(oauth_provider)
        assert 'OAuthProvider' in repr_str
        assert str(oauth_provider.id) in repr_str
        assert oauth_provider.user_id in repr_str
        assert oauth_provider.provider in repr_str


class TestUserModelIntegration:
    """Integration tests for User and OAuthProvider models together."""
    
    def test_user_with_multiple_oauth_providers(self, db_session, sample_user_data):
        """Test user with multiple OAuth providers."""
        # Create user
        user = User(**sample_user_data)
        user.password_hash = None  # OAuth-only user
        db_session.add(user)
        db_session.commit()
        
        # Add multiple OAuth providers
        providers_data = [
            {'provider': 'google', 'provider_user_id': 'google_123'},
            {'provider': 'tiktok', 'provider_user_id': 'tiktok_456'},
            {'provider': 'facebook', 'provider_user_id': 'facebook_789'}
        ]
        
        for provider_data in providers_data:
            oauth = OAuthProvider(
                user_id=str(user.id),
                **provider_data
            )
            db_session.add(oauth)
        
        db_session.commit()
        db_session.refresh(user)
        
        assert user.is_oauth_only is True
        assert len(user.oauth_providers) == 3
        
        provider_names = [oauth.provider for oauth in user.oauth_providers]
        assert 'google' in provider_names
        assert 'tiktok' in provider_names
        assert 'facebook' in provider_names
    
    def test_user_model_to_dict_method(self, db_session, sample_user_data):
        """Test User model to_dict method."""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        user_dict = user.to_dict()
        
        assert user_dict['email'] == 'test@example.com'
        assert user_dict['name'] == 'Test User'
        assert user_dict['daily_xp_goal'] == 30
        assert user_dict['timezone'] == 'America/New_York'
        assert 'id' in user_dict
        assert 'created_at' in user_dict
        assert 'updated_at' in user_dict
        
        # Test excluding fields
        user_dict_exclude = user.to_dict(exclude_fields={'password_hash', 'email'})
        assert 'password_hash' not in user_dict_exclude
        assert 'email' not in user_dict_exclude
        assert 'name' in user_dict_exclude
    
    def test_user_model_update_from_dict(self, db_session, sample_user_data):
        """Test User model update_from_dict method."""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        
        original_id = user.id
        original_created_at = user.created_at
        
        update_data = {
            'name': 'Updated Name',
            'daily_xp_goal': 50,
            'timezone': 'Europe/London',
            'id': 'should_not_update',  # Should be excluded
            'created_at': datetime.now()  # Should be excluded
        }
        
        user.update_from_dict(update_data)
        
        assert user.name == 'Updated Name'
        assert user.daily_xp_goal == 50
        assert user.timezone == 'Europe/London'
        assert user.id == original_id  # Should not change
        assert user.created_at == original_created_at  # Should not change