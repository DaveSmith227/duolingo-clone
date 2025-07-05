"""
Tests for User Profile Sync Service

Unit tests for synchronizing user profiles between Supabase Auth
and the application database.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.user_sync import UserSyncService, get_user_sync_service
from app.models.user import User, OAuthProvider
from app.models.auth import SupabaseUser, AuthAuditLog


class TestUserSyncService:
    """Test cases for UserSyncService."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_db = Mock()
        self.mock_supabase = AsyncMock()
        
        # Create service with mocked dependencies
        self.service = UserSyncService(self.mock_db)
        self.service.supabase = self.mock_supabase
    
    async def test_sync_new_user_from_supabase(self):
        """Test syncing new user from Supabase Auth."""
        # Arrange
        supabase_user_data = {
            'id': '550e8400-e29b-41d4-a716-446655440000',
            'email': 'test@example.com',
            'email_confirmed_at': '2024-01-01T12:00:00Z',
            'user_metadata': {
                'full_name': 'John Doe',
                'avatar_url': 'https://example.com/avatar.jpg'
            },
            'app_metadata': {},
            'identities': [
                {
                    'provider': 'google',
                    'id': 'google_user_123',
                    'access_token': 'google_access_token',
                    'refresh_token': 'google_refresh_token',
                    'expires_in': 3600
                }
            ]
        }
        
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        self.mock_db.add = Mock()
        self.mock_db.flush = Mock()
        self.mock_db.commit = Mock()
        
        # Mock User creation
        mock_user = Mock()
        mock_user.id = 'user_123'
        mock_user.email = 'test@example.com'
        
        # Act
        with patch('app.services.user_sync.User', return_value=mock_user), \
             patch('app.services.user_sync.SupabaseUser') as mock_supabase_user_class, \
             patch('app.services.user_sync.OAuthProvider') as mock_oauth_class:
            
            mock_supabase_user = Mock()
            mock_supabase_user_class.return_value = mock_supabase_user
            
            result = await self.service.sync_user_from_supabase(supabase_user_data)
            
            # Assert
            assert result is not None
            app_user, supabase_user = result
            
            # Verify User creation
            assert app_user == mock_user
            
            # Verify database operations
            assert self.mock_db.add.call_count >= 2  # User + SupabaseUser + OAuth
            self.mock_db.flush.assert_called_once()
            self.mock_db.commit.assert_called_once()
            
            # Verify OAuth provider creation
            mock_oauth_class.assert_called_once()
    
    async def test_sync_existing_user_from_supabase(self):
        """Test syncing existing user from Supabase Auth."""
        # Arrange
        supabase_user_data = {
            'id': '550e8400-e29b-41d4-a716-446655440000',
            'email': 'updated@example.com',
            'email_confirmed_at': '2024-01-01T12:00:00Z',
            'user_metadata': {
                'full_name': 'John Updated',
                'avatar_url': 'https://example.com/new_avatar.jpg'
            },
            'identities': []
        }
        
        # Mock existing user
        mock_app_user = Mock()
        mock_app_user.id = 'user_123'
        mock_app_user.email = 'old@example.com'
        mock_app_user.name = 'John Doe'
        mock_app_user.is_email_verified = False
        
        mock_supabase_user = Mock()
        mock_supabase_user.user = mock_app_user
        mock_supabase_user.update_from_supabase = Mock()
        mock_supabase_user.mark_sync_success = Mock()
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        self.mock_db.commit = Mock()
        
        # Act
        result = await self.service.sync_user_from_supabase(supabase_user_data)
        
        # Assert
        app_user, supabase_user = result
        assert app_user == mock_app_user
        assert supabase_user == mock_supabase_user
        
        # Verify updates
        mock_supabase_user.update_from_supabase.assert_called_once_with(supabase_user_data)
        mock_supabase_user.mark_sync_success.assert_called_once()
        self.mock_db.commit.assert_called_once()
    
    async def test_sync_user_validation_error(self):
        """Test sync user with invalid data."""
        # Arrange - missing required fields
        invalid_data = {
            'email': 'test@example.com'
            # Missing 'id'
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="Supabase user ID is required"):
            await self.service.sync_user_from_supabase(invalid_data)
    
    async def test_create_new_user_missing_email(self):
        """Test creating new user without email."""
        # Arrange
        supabase_user_data = {
            'id': '550e8400-e29b-41d4-a716-446655440000'
            # Missing email
        }
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Email is required for user creation"):
            await self.service.sync_user_from_supabase(supabase_user_data)
    
    async def test_create_new_user_name_extraction(self):
        """Test user name extraction from metadata."""
        # Test cases for different metadata formats
        test_cases = [
            # Full name in metadata
            {
                'user_metadata': {'full_name': 'John Doe'},
                'expected_name': 'John Doe'
            },
            # Name in metadata
            {
                'user_metadata': {'name': 'Jane Smith'},
                'expected_name': 'Jane Smith'
            },
            # First and last name
            {
                'user_metadata': {'first_name': 'Bob', 'last_name': 'Johnson'},
                'expected_name': 'Bob Johnson'
            },
            # Only first name
            {
                'user_metadata': {'first_name': 'Alice'},
                'expected_name': 'Alice'
            },
            # No name metadata - use email prefix
            {
                'user_metadata': {},
                'expected_name': 'test'
            }
        ]
        
        for test_case in test_cases:
            # Arrange
            supabase_user_data = {
                'id': '550e8400-e29b-41d4-a716-446655440000',
                'email': 'test@example.com',
                'user_metadata': test_case['user_metadata'],
                'identities': []
            }
            
            self.mock_db.query.return_value.filter.return_value.first.return_value = None
            self.mock_db.add = Mock()
            self.mock_db.flush = Mock()
            self.mock_db.commit = Mock()
            
            # Act
            with patch('app.services.user_sync.User') as mock_user_class, \
                 patch('app.services.user_sync.SupabaseUser'):
                
                await self.service._create_new_user(supabase_user_data)
                
                # Assert
                user_creation_call = mock_user_class.call_args
                assert user_creation_call[1]['name'] == test_case['expected_name']
    
    async def test_handle_user_deletion(self):
        """Test handling user deletion from Supabase."""
        # Arrange
        supabase_id = '550e8400-e29b-41d4-a716-446655440000'
        
        mock_app_user = Mock()
        mock_app_user.email = 'test@example.com'
        mock_app_user.soft_delete = Mock()
        
        mock_supabase_user = Mock()
        mock_supabase_user.user = mock_app_user
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        self.mock_db.commit = Mock()
        
        # Act
        await self.service.handle_user_deletion(supabase_id)
        
        # Assert
        mock_app_user.soft_delete.assert_called_once()
        self.mock_db.commit.assert_called_once()
    
    async def test_handle_user_deletion_not_found(self):
        """Test handling deletion of non-existent user."""
        # Arrange
        supabase_id = 'non-existent-id'
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act - should not raise exception
        await self.service.handle_user_deletion(supabase_id)
        
        # Assert - no commit should be called
        self.mock_db.commit.assert_not_called()
    
    def test_get_user_by_supabase_id_found(self):
        """Test getting user by Supabase ID when user exists."""
        # Arrange
        supabase_id = '550e8400-e29b-41d4-a716-446655440000'
        
        mock_app_user = Mock()
        mock_supabase_user = Mock()
        mock_supabase_user.user = mock_app_user
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        
        # Act
        result = self.service.get_user_by_supabase_id(supabase_id)
        
        # Assert
        assert result == (mock_app_user, mock_supabase_user)
    
    def test_get_user_by_supabase_id_not_found(self):
        """Test getting user by Supabase ID when user doesn't exist."""
        # Arrange
        supabase_id = 'non-existent-id'
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = self.service.get_user_by_supabase_id(supabase_id)
        
        # Assert
        assert result is None
    
    async def test_sync_all_pending_users(self):
        """Test syncing all users with pending status."""
        # Arrange
        mock_pending_user1 = Mock()
        mock_pending_user1.user = Mock()
        mock_pending_user1.supabase_id = 'user1'
        
        mock_pending_user2 = Mock()
        mock_pending_user2.user = Mock()
        mock_pending_user2.supabase_id = 'user2'
        mock_pending_user2.mark_sync_error = Mock()
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_pending_user1, mock_pending_user2
        ]
        
        # Mock Supabase responses
        self.mock_supabase.get_user_profile.side_effect = [
            {'id': 'user1', 'email': 'user1@example.com'},  # Success
            None  # Failure for user2
        ]
        
        self.mock_db.commit = Mock()
        
        # Act
        with patch.object(self.service, '_update_existing_user', new_callable=AsyncMock) as mock_update:
            result = await self.service.sync_all_pending_users()
        
        # Assert
        assert result == 1  # Only one user synced successfully
        mock_update.assert_called_once()
        mock_pending_user2.mark_sync_error.assert_not_called()  # Since get_user_profile returned None
    
    def test_log_auth_event_success(self):
        """Test successful authentication event logging."""
        # Arrange
        mock_supabase_user = Mock()
        mock_supabase_user.id = 'user_123'
        
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        
        # Act
        with patch('app.services.user_sync.AuthAuditLog') as mock_audit_log:
            mock_log_instance = Mock()
            mock_audit_log.create_log.return_value = mock_log_instance
            
            self.service._log_auth_event(
                supabase_user=mock_supabase_user,
                event_type='sign_in',
                event_result='success',
                ip_address='192.168.1.1'
            )
        
        # Assert
        mock_audit_log.create_log.assert_called_once_with(
            event_type='sign_in',
            event_result='success',
            supabase_user_id='user_123',
            ip_address='192.168.1.1'
        )
        self.mock_db.add.assert_called_once_with(mock_log_instance)
        self.mock_db.commit.assert_called_once()
    
    def test_log_auth_event_failure(self):
        """Test authentication event logging failure handling."""
        # Arrange
        mock_supabase_user = Mock()
        self.mock_db.add.side_effect = Exception("Database error")
        
        # Act - should not raise exception
        with patch('app.services.user_sync.AuthAuditLog'), \
             patch('app.services.user_sync.logger') as mock_logger:
            
            self.service._log_auth_event(
                supabase_user=mock_supabase_user,
                event_type='sign_in',
                event_result='success'
            )
        
        # Assert
        mock_logger.error.assert_called_once()


class TestUserSyncServiceHelpers:
    """Test cases for helper functions."""
    
    @patch('app.services.user_sync.get_db')
    def test_get_user_sync_service_default_db(self, mock_get_db):
        """Test getting UserSyncService with default database session."""
        # Arrange
        mock_db_session = Mock()
        mock_get_db.return_value = iter([mock_db_session])
        
        # Act
        service = get_user_sync_service()
        
        # Assert
        assert isinstance(service, UserSyncService)
        assert service.db == mock_db_session
    
    def test_get_user_sync_service_provided_db(self):
        """Test getting UserSyncService with provided database session."""
        # Arrange
        mock_db_session = Mock()
        
        # Act
        service = get_user_sync_service(db=mock_db_session)
        
        # Assert
        assert isinstance(service, UserSyncService)
        assert service.db == mock_db_session


class TestUserSyncIntegration:
    """Integration test cases for user sync functionality."""
    
    async def test_complete_user_sync_flow(self):
        """Test complete user synchronization flow."""
        # This would be an integration test that tests the complete flow
        # with real database connections (using test database)
        pass
    
    async def test_oauth_provider_sync(self):
        """Test OAuth provider synchronization."""
        # Test syncing OAuth provider information
        pass
    
    async def test_concurrent_user_sync(self):
        """Test handling concurrent user sync operations."""
        # Test race conditions and concurrent access
        pass