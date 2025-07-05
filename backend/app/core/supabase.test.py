"""
Tests for Supabase Client Configuration

Unit tests for Supabase client initialization, OAuth provider management,
and user operations.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.core.supabase import SupabaseClient, get_supabase_client, init_supabase
from app.core.config import Settings
from gotrue.errors import AuthError


class TestSupabaseClient:
    """Test cases for SupabaseClient class."""
    
    def setup_method(self):
        """Reset singleton instance before each test."""
        SupabaseClient._instance = None
        SupabaseClient._client = None
    
    @patch('app.core.supabase.get_settings')
    @patch('app.core.supabase.create_client')
    def test_initialize_client_success(self, mock_create_client, mock_get_settings):
        """Test successful Supabase client initialization."""
        # Arrange
        mock_settings = Mock()
        mock_settings.has_supabase_config = True
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_anon_key = "test-anon-key"
        mock_get_settings.return_value = mock_settings
        
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        
        # Act
        supabase_client = SupabaseClient()
        
        # Assert
        assert supabase_client.client == mock_client
        assert supabase_client.is_configured() is True
        mock_create_client.assert_called_once()
    
    @patch('app.core.supabase.get_settings')
    def test_initialize_client_incomplete_config(self, mock_get_settings):
        """Test Supabase client initialization with incomplete configuration."""
        # Arrange
        mock_settings = Mock()
        mock_settings.has_supabase_config = False
        mock_get_settings.return_value = mock_settings
        
        # Act
        supabase_client = SupabaseClient()
        
        # Assert
        assert supabase_client.client is None
        assert supabase_client.is_configured() is False
    
    @patch('app.core.supabase.get_settings')
    @patch('app.core.supabase.create_client')
    def test_singleton_pattern(self, mock_create_client, mock_get_settings):
        """Test that SupabaseClient follows singleton pattern."""
        # Arrange
        mock_settings = Mock()
        mock_settings.has_supabase_config = True
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_anon_key = "test-anon-key"
        mock_get_settings.return_value = mock_settings
        
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        
        # Act
        client1 = SupabaseClient()
        client2 = SupabaseClient()
        
        # Assert
        assert client1 is client2
        assert mock_create_client.call_count == 1
    
    @patch('app.core.supabase.get_settings')
    @patch('app.core.supabase.create_client')
    def test_auth_property(self, mock_create_client, mock_get_settings):
        """Test auth property returns Supabase auth client."""
        # Arrange
        mock_settings = Mock()
        mock_settings.has_supabase_config = True
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_anon_key = "test-anon-key"
        mock_get_settings.return_value = mock_settings
        
        mock_auth = Mock()
        mock_client = Mock()
        mock_client.auth = mock_auth
        mock_create_client.return_value = mock_client
        
        # Act
        supabase_client = SupabaseClient()
        auth_client = supabase_client.auth
        
        # Assert
        assert auth_client == mock_auth
    
    def test_auth_property_not_configured(self):
        """Test auth property raises error when client not configured."""
        # Arrange
        supabase_client = SupabaseClient()
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Supabase client not initialized"):
            _ = supabase_client.auth
    
    @patch('app.core.supabase.get_settings')
    @patch('app.core.supabase.create_client')
    async def test_sign_in_with_oauth_success(self, mock_create_client, mock_get_settings):
        """Test successful OAuth sign-in initiation."""
        # Arrange
        mock_settings = Mock()
        mock_settings.has_supabase_config = True
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_anon_key = "test-anon-key"
        mock_settings.oauth_callback_url = "http://localhost:3000/auth/callback"
        mock_get_settings.return_value = mock_settings
        
        mock_auth = AsyncMock()
        mock_auth.sign_in_with_oauth.return_value = {"url": "https://provider.com/oauth"}
        mock_client = Mock()
        mock_client.auth = mock_auth
        mock_create_client.return_value = mock_client
        
        # Act
        supabase_client = SupabaseClient()
        result = await supabase_client.sign_in_with_oauth("google")
        
        # Assert
        assert result == {"url": "https://provider.com/oauth"}
        mock_auth.sign_in_with_oauth.assert_called_once_with({
            "provider": "google",
            "options": {
                "redirect_to": "http://localhost:3000/auth/callback",
                "scopes": "openid email profile"
            }
        })
    
    async def test_sign_in_with_oauth_not_configured(self):
        """Test OAuth sign-in raises error when client not configured."""
        # Arrange
        supabase_client = SupabaseClient()
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Supabase client not initialized"):
            await supabase_client.sign_in_with_oauth("google")
    
    @patch('app.core.supabase.get_settings')
    @patch('app.core.supabase.create_client')
    async def test_handle_oauth_callback_success(self, mock_create_client, mock_get_settings):
        """Test successful OAuth callback handling."""
        # Arrange
        mock_settings = Mock()
        mock_settings.has_supabase_config = True
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_anon_key = "test-anon-key"
        mock_get_settings.return_value = mock_settings
        
        mock_auth = AsyncMock()
        mock_auth.exchange_code_for_session.return_value = {"session": "test-session"}
        mock_client = Mock()
        mock_client.auth = mock_auth
        mock_create_client.return_value = mock_client
        
        # Act
        supabase_client = SupabaseClient()
        result = await supabase_client.handle_oauth_callback("test-code", "test-state")
        
        # Assert
        assert result == {"session": "test-session"}
        mock_auth.exchange_code_for_session.assert_called_once_with({
            "auth_code": "test-code",
            "code_verifier": "test-state"
        })
    
    @patch('app.core.supabase.get_settings')
    @patch('app.core.supabase.create_client')
    async def test_get_user_success(self, mock_create_client, mock_get_settings):
        """Test successful user retrieval."""
        # Arrange
        mock_settings = Mock()
        mock_settings.has_supabase_config = True
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_anon_key = "test-anon-key"
        mock_get_settings.return_value = mock_settings
        
        mock_user_response = Mock()
        mock_user_response.user = {"id": "test-user-id", "email": "test@example.com"}
        
        mock_auth = AsyncMock()
        mock_auth.get_user.return_value = mock_user_response
        mock_client = Mock()
        mock_client.auth = mock_auth
        mock_create_client.return_value = mock_client
        
        # Act
        supabase_client = SupabaseClient()
        result = await supabase_client.get_user()
        
        # Assert
        assert result == {"id": "test-user-id", "email": "test@example.com"}
    
    @patch('app.core.supabase.get_settings')
    @patch('app.core.supabase.create_client')
    async def test_get_user_not_authenticated(self, mock_create_client, mock_get_settings):
        """Test user retrieval when not authenticated."""
        # Arrange
        mock_settings = Mock()
        mock_settings.has_supabase_config = True
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_anon_key = "test-anon-key"
        mock_get_settings.return_value = mock_settings
        
        mock_auth = AsyncMock()
        mock_auth.get_user.side_effect = AuthError("User not authenticated")
        mock_client = Mock()
        mock_client.auth = mock_auth
        mock_create_client.return_value = mock_client
        
        # Act
        supabase_client = SupabaseClient()
        result = await supabase_client.get_user()
        
        # Assert
        assert result is None
    
    def test_get_provider_scopes(self):
        """Test OAuth provider scope mapping."""
        # Arrange
        supabase_client = SupabaseClient()
        
        # Act & Assert
        assert supabase_client._get_provider_scopes("google") == "openid email profile"
        assert supabase_client._get_provider_scopes("facebook") == "email public_profile"
        assert supabase_client._get_provider_scopes("apple") == "email name"
        assert supabase_client._get_provider_scopes("tiktok") == "user.info.basic user.info.profile"
        assert supabase_client._get_provider_scopes("unknown") == "openid email profile"


class TestSupabaseHelperFunctions:
    """Test cases for Supabase helper functions."""
    
    def setup_method(self):
        """Reset global client before each test."""
        global _supabase_client
        import app.core.supabase
        app.core.supabase._supabase_client = None
    
    @patch('app.core.supabase.SupabaseClient')
    def test_get_supabase_client_creates_singleton(self, mock_supabase_client):
        """Test get_supabase_client creates and returns singleton."""
        # Arrange
        mock_instance = Mock()
        mock_supabase_client.return_value = mock_instance
        
        # Act
        client1 = get_supabase_client()
        client2 = get_supabase_client()
        
        # Assert
        assert client1 == mock_instance
        assert client2 == mock_instance
        assert mock_supabase_client.call_count == 1
    
    @patch('app.core.supabase.get_supabase_client')
    def test_init_supabase_configured(self, mock_get_client):
        """Test init_supabase with configured client."""
        # Arrange
        mock_client = Mock()
        mock_client.is_configured.return_value = True
        mock_get_client.return_value = mock_client
        
        # Act
        init_supabase()
        
        # Assert
        mock_get_client.assert_called_once()
        mock_client.is_configured.assert_called_once()
    
    @patch('app.core.supabase.get_supabase_client')
    def test_init_supabase_not_configured(self, mock_get_client):
        """Test init_supabase with unconfigured client."""
        # Arrange
        mock_client = Mock()
        mock_client.is_configured.return_value = False
        mock_get_client.return_value = mock_client
        
        # Act
        init_supabase()
        
        # Assert
        mock_get_client.assert_called_once()
        mock_client.is_configured.assert_called_once()