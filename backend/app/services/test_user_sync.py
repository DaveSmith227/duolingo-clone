"""
Tests for User Profile Sync Service

Unit tests for basic user synchronization functionality.
"""

import pytest
from unittest.mock import Mock
from app.services.user_sync import get_user_sync_service


class TestUserSyncServiceHelpers:
    """Test cases for helper functions."""
    
    def test_get_user_sync_service_provided_db(self):
        """Test getting UserSyncService with provided database session."""
        # Arrange
        mock_db_session = Mock()
        
        # Act
        service = get_user_sync_service(db=mock_db_session)
        
        # Assert
        assert service.db == mock_db_session