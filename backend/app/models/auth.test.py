"""
Tests for Authentication Models

Unit tests for Supabase user sync, authentication sessions,
and audit logging models.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError

from app.models.auth import SupabaseUser, AuthSession, AuthAuditLog
from app.models.user import User


class TestSupabaseUser:
    """Test cases for SupabaseUser model."""
    
    def test_create_supabase_user(self, db_session, sample_user):
        """Test creating a Supabase user."""
        supabase_user = SupabaseUser(
            supabase_id='550e8400-e29b-41d4-a716-446655440000',
            app_user_id=sample_user.id,
            email='test@example.com',
            provider='email'
        )
        
        db_session.add(supabase_user)
        db_session.commit()
        
        assert supabase_user.id is not None
        assert supabase_user.supabase_id == '550e8400-e29b-41d4-a716-446655440000'
        assert supabase_user.email == 'test@example.com'
        assert supabase_user.sync_status == 'synced'
        assert supabase_user.last_sync_at is not None
    
    def test_supabase_user_unique_constraint(self, db_session, sample_user):
        """Test unique constraint on supabase_id."""
        supabase_id = '550e8400-e29b-41d4-a716-446655440000'
        
        # Create first user
        user1 = SupabaseUser(
            supabase_id=supabase_id,
            app_user_id=sample_user.id,
            email='test1@example.com',
            provider='email'
        )
        db_session.add(user1)
        db_session.commit()
        
        # Create second user with same supabase_id
        user2 = SupabaseUser(
            supabase_id=supabase_id,
            app_user_id=sample_user.id,
            email='test2@example.com',
            provider='email'
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_validate_sync_status(self, db_session, sample_user):
        """Test sync status validation."""
        supabase_user = SupabaseUser(
            supabase_id='550e8400-e29b-41d4-a716-446655440000',
            app_user_id=sample_user.id,
            email='test@example.com',
            provider='email'
        )
        
        # Valid status
        supabase_user.sync_status = 'pending'
        assert supabase_user.sync_status == 'pending'
        
        # Invalid status
        with pytest.raises(ValueError, match="Sync status must be one of"):
            supabase_user.sync_status = 'invalid'
    
    def test_validate_provider(self, db_session, sample_user):
        """Test provider validation."""
        supabase_user = SupabaseUser(
            supabase_id='550e8400-e29b-41d4-a716-446655440000',
            app_user_id=sample_user.id,
            email='test@example.com',
            provider='email'
        )
        
        # Valid providers
        valid_providers = ['email', 'google', 'facebook', 'apple', 'github', 'twitter']
        for provider in valid_providers:
            supabase_user.provider = provider
            assert supabase_user.provider == provider
        
        # Invalid provider
        with pytest.raises(ValueError, match="Provider must be one of"):
            supabase_user.provider = 'invalid'
    
    def test_mark_sync_success(self, db_session, sample_user):
        """Test marking sync as successful."""
        supabase_user = SupabaseUser(
            supabase_id='550e8400-e29b-41d4-a716-446655440000',
            app_user_id=sample_user.id,
            email='test@example.com',
            provider='email',
            sync_status='pending',
            sync_error='Previous error'
        )
        
        supabase_user.mark_sync_success()
        
        assert supabase_user.sync_status == 'synced'
        assert supabase_user.sync_error is None
        assert supabase_user.last_sync_at is not None
    
    def test_mark_sync_error(self, db_session, sample_user):
        """Test marking sync as error."""
        supabase_user = SupabaseUser(
            supabase_id='550e8400-e29b-41d4-a716-446655440000',
            app_user_id=sample_user.id,
            email='test@example.com',
            provider='email'
        )
        
        error_message = "Sync failed due to network error"
        supabase_user.mark_sync_error(error_message)
        
        assert supabase_user.sync_status == 'error'
        assert supabase_user.sync_error == error_message
    
    def test_update_from_supabase(self, db_session, sample_user):
        """Test updating user data from Supabase."""
        supabase_user = SupabaseUser(
            supabase_id='550e8400-e29b-41d4-a716-446655440000',
            app_user_id=sample_user.id,
            email='old@example.com',
            provider='email'
        )
        
        supabase_data = {
            'email': 'new@example.com',
            'email_confirmed_at': '2024-01-01T12:00:00Z',
            'phone': '+1234567890',
            'phone_confirmed_at': '2024-01-01T12:00:00Z',
            'last_sign_in_at': '2024-01-01T12:00:00Z',
            'user_metadata': {'name': 'John Doe'},
            'app_metadata': {'role': 'user'},
            'identities': [{'provider': 'google'}]
        }
        
        supabase_user.update_from_supabase(supabase_data)
        
        assert supabase_user.email == 'new@example.com'
        assert supabase_user.email_verified is True
        assert supabase_user.phone == '+1234567890'
        assert supabase_user.phone_verified is True
        assert supabase_user.provider == 'google'
        assert supabase_user.user_metadata == {'name': 'John Doe'}
        assert supabase_user.app_metadata == {'role': 'user'}


class TestAuthSession:
    """Test cases for AuthSession model."""
    
    def test_create_auth_session(self, db_session, sample_supabase_user):
        """Test creating an authentication session."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        session = AuthSession(
            supabase_user_id=sample_supabase_user.id,
            session_id='session_123',
            access_token='access_token_123',
            refresh_token='refresh_token_123',
            expires_at=expires_at,
            user_agent='Mozilla/5.0',
            ip_address='192.168.1.1'
        )
        
        db_session.add(session)
        db_session.commit()
        
        assert session.id is not None
        assert session.session_id == 'session_123'
        assert session.is_active is True
        assert session.token_type == 'bearer'
    
    def test_session_unique_constraint(self, db_session, sample_supabase_user):
        """Test unique constraint on session_id."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        session_id = 'session_123'
        
        # Create first session
        session1 = AuthSession(
            supabase_user_id=sample_supabase_user.id,
            session_id=session_id,
            access_token='access_token_1',
            expires_at=expires_at
        )
        db_session.add(session1)
        db_session.commit()
        
        # Create second session with same session_id
        session2 = AuthSession(
            supabase_user_id=sample_supabase_user.id,
            session_id=session_id,
            access_token='access_token_2',
            expires_at=expires_at
        )
        db_session.add(session2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_is_expired_property(self, db_session, sample_supabase_user):
        """Test session expiration check."""
        # Expired session
        expired_session = AuthSession(
            supabase_user_id=sample_supabase_user.id,
            session_id='expired_session',
            access_token='token',
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        # Valid session
        valid_session = AuthSession(
            supabase_user_id=sample_supabase_user.id,
            session_id='valid_session',
            access_token='token',
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        assert expired_session.is_expired is True
        assert valid_session.is_expired is False
    
    def test_is_valid_property(self, db_session, sample_supabase_user):
        """Test session validity check."""
        # Valid session
        valid_session = AuthSession(
            supabase_user_id=sample_supabase_user.id,
            session_id='valid_session',
            access_token='token',
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=True
        )
        
        # Inactive session
        inactive_session = AuthSession(
            supabase_user_id=sample_supabase_user.id,
            session_id='inactive_session',
            access_token='token',
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=False
        )
        
        # Invalidated session
        invalidated_session = AuthSession(
            supabase_user_id=sample_supabase_user.id,
            session_id='invalidated_session',
            access_token='token',
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=True,
            invalidated_at=datetime.now(timezone.utc)
        )
        
        assert valid_session.is_valid is True
        assert inactive_session.is_valid is False
        assert invalidated_session.is_valid is False
    
    def test_invalidate_session(self, db_session, sample_supabase_user):
        """Test session invalidation."""
        session = AuthSession(
            supabase_user_id=sample_supabase_user.id,
            session_id='test_session',
            access_token='token',
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        session.invalidate('user_logout')
        
        assert session.is_active is False
        assert session.invalidated_at is not None
        assert session.invalidation_reason == 'user_logout'
    
    def test_extend_expiration(self, db_session, sample_supabase_user):
        """Test extending session expiration."""
        original_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        session = AuthSession(
            supabase_user_id=sample_supabase_user.id,
            session_id='test_session',
            access_token='token',
            expires_at=original_expires
        )
        
        session.extend_expiration(3600)  # 1 hour
        
        assert session.expires_at > original_expires


class TestAuthAuditLog:
    """Test cases for AuthAuditLog model."""
    
    def test_create_audit_log(self, db_session, sample_supabase_user):
        """Test creating an audit log entry."""
        log_entry = AuthAuditLog(
            supabase_user_id=sample_supabase_user.id,
            event_type='sign_in',
            event_result='success',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0',
            provider='email',
            session_id='session_123'
        )
        
        db_session.add(log_entry)
        db_session.commit()
        
        assert log_entry.id is not None
        assert log_entry.event_type == 'sign_in'
        assert log_entry.event_result == 'success'
        assert log_entry.risk_score == 0
    
    def test_validate_event_type(self, db_session):
        """Test event type validation."""
        log_entry = AuthAuditLog(
            event_type='sign_in',
            event_result='success'
        )
        
        # Valid event types
        valid_types = [
            'sign_up', 'sign_in', 'sign_out', 'password_reset', 'password_change',
            'email_verification', 'phone_verification', 'oauth_link', 'oauth_unlink',
            'session_refresh', 'session_invalidate', 'account_delete', 'profile_update'
        ]
        
        for event_type in valid_types:
            log_entry.event_type = event_type
            assert log_entry.event_type == event_type
        
        # Invalid event type
        with pytest.raises(ValueError, match="Event type must be one of"):
            log_entry.event_type = 'invalid_event'
    
    def test_validate_event_result(self, db_session):
        """Test event result validation."""
        log_entry = AuthAuditLog(
            event_type='sign_in',
            event_result='success'
        )
        
        # Valid results
        valid_results = ['success', 'failure', 'error']
        for result in valid_results:
            log_entry.event_result = result
            assert log_entry.event_result == result
        
        # Invalid result
        with pytest.raises(ValueError, match="Event result must be one of"):
            log_entry.event_result = 'invalid_result'
    
    def test_validate_risk_score(self, db_session):
        """Test risk score validation."""
        log_entry = AuthAuditLog(
            event_type='sign_in',
            event_result='success'
        )
        
        # Valid risk scores
        log_entry.risk_score = 0
        assert log_entry.risk_score == 0
        
        log_entry.risk_score = 50
        assert log_entry.risk_score == 50
        
        log_entry.risk_score = 100
        assert log_entry.risk_score == 100
        
        # Invalid risk scores
        with pytest.raises(ValueError, match="Risk score must be between 0 and 100"):
            log_entry.risk_score = -1
        
        with pytest.raises(ValueError, match="Risk score must be between 0 and 100"):
            log_entry.risk_score = 101
    
    def test_create_log_class_method(self, db_session, sample_supabase_user):
        """Test creating log entry using class method."""
        log_entry = AuthAuditLog.create_log(
            event_type='sign_in',
            event_result='success',
            supabase_user_id=sample_supabase_user.id,
            ip_address='192.168.1.1',
            risk_score=25
        )
        
        assert log_entry.event_type == 'sign_in'
        assert log_entry.event_result == 'success'
        assert log_entry.supabase_user_id == sample_supabase_user.id
        assert log_entry.ip_address == '192.168.1.1'
        assert log_entry.risk_score == 25
    
    def test_audit_log_without_user(self, db_session):
        """Test creating audit log for anonymous events."""
        log_entry = AuthAuditLog(
            supabase_user_id=None,
            event_type='sign_up',
            event_result='failure',
            ip_address='192.168.1.1',
            error_message='Invalid email format'
        )
        
        db_session.add(log_entry)
        db_session.commit()
        
        assert log_entry.id is not None
        assert log_entry.supabase_user_id is None
        assert log_entry.error_message == 'Invalid email format'