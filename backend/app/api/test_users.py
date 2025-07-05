"""
Unit Tests for User Management Endpoints

Comprehensive test suite for user management API endpoints including
avatar uploads, user preferences, and extended user data management.
"""

import pytest
import tempfile
import os
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import UploadFile, status
from sqlalchemy.orm import Session
from PIL import Image

from app.main import app
from app.models.user import User
from app.schemas.users import (
    UserPreferencesRequest,
    UserPreferencesResponse,
    AvatarUploadResponse,
    UserPreferencesUpdateResponse
)
from app.services.file_upload_service import FileUploadService


class TestUsersAPI:
    """Test suite for users API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return MagicMock(spec=Session)
    
    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = MagicMock(spec=User)
        user.id = "test-user-123"
        user.email = "test@example.com"
        user.name = "Test User"
        user.avatar_url = None
        user.daily_xp_goal = 20
        user.timezone = "UTC"
        user.created_at = "2024-01-01T00:00:00Z"
        user.updated_at = "2024-01-01T00:00:00Z"
        return user
    
    @pytest.fixture
    def test_image_file(self):
        """Create a test image file."""
        # Create a small test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return UploadFile(
            filename="test_avatar.png",
            file=img_bytes,
            content_type="image/png"
        )
    
    @pytest.fixture
    def large_image_file(self):
        """Create a large test image file that exceeds size limit."""
        # Create a large image (simulated)
        img_bytes = BytesIO(b'0' * (6 * 1024 * 1024))  # 6MB
        
        return UploadFile(
            filename="large_avatar.png",
            file=img_bytes,
            content_type="image/png"
        )
    
    @pytest.fixture
    def invalid_file(self):
        """Create an invalid file (text file)."""
        file_content = BytesIO(b"This is not an image")
        
        return UploadFile(
            filename="invalid.txt",
            file=file_content,
            content_type="text/plain"
        )


class TestAvatarUpload(TestUsersAPI):
    """Test avatar upload endpoint."""
    
    @patch('app.api.users.get_current_user')
    @patch('app.api.users.get_db')
    @patch('app.services.file_upload_service.FileUploadService.upload_avatar')
    def test_upload_avatar_success(self, mock_upload, mock_get_db, mock_get_user, client, mock_db, mock_user, test_image_file):
        """Test successful avatar upload."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        mock_upload.return_value = "/uploads/avatars/test-user-123_abc123.png"
        
        # Act
        response = client.post(
            "/users/me/avatar",
            files={"avatar": ("test_avatar.png", test_image_file.file, "image/png")}
        )
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["message"] == "Avatar uploaded successfully"
        assert data["avatar_url"] == "/uploads/avatars/test-user-123_abc123.png"
        assert "uploaded_at" in data
        
        # Verify user avatar_url was updated
        assert mock_user.avatar_url == "/uploads/avatars/test-user-123_abc123.png"
        mock_db.commit.assert_called_once()
    
    @patch('app.api.users.get_current_user')
    @patch('app.api.users.get_db')
    @patch('app.services.file_upload_service.FileUploadService.upload_avatar')
    def test_upload_avatar_validation_error(self, mock_upload, mock_get_db, mock_get_user, client, mock_db, mock_user, large_image_file):
        """Test avatar upload with validation error."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        mock_upload.side_effect = ValueError("File size exceeds maximum allowed size of 5.0MB")
        
        # Act
        response = client.post(
            "/users/me/avatar",
            files={"avatar": ("large_avatar.png", large_image_file.file, "image/png")}
        )
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"]["error"] == "upload_validation_failed"
        assert "File size exceeds maximum" in data["detail"]["message"]
        
        # Verify database was not modified
        mock_db.commit.assert_not_called()
    
    @patch('app.api.users.get_current_user')
    @patch('app.api.users.get_db')
    @patch('app.services.file_upload_service.FileUploadService.upload_avatar')
    def test_upload_avatar_server_error(self, mock_upload, mock_get_db, mock_get_user, client, mock_db, mock_user, test_image_file):
        """Test avatar upload with server error."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        mock_upload.side_effect = Exception("Storage service unavailable")
        
        # Act
        response = client.post(
            "/users/me/avatar",
            files={"avatar": ("test_avatar.png", test_image_file.file, "image/png")}
        )
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"]["error"] == "upload_failed"
        assert data["detail"]["message"] == "Failed to upload avatar. Please try again."
        
        # Verify database rollback was called
        mock_db.rollback.assert_called_once()
    
    def test_upload_avatar_no_file(self, client):
        """Test avatar upload without file."""
        # Act
        response = client.post("/users/me/avatar")
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserPreferences(TestUsersAPI):
    """Test user preferences endpoints."""
    
    @patch('app.api.users.get_current_user')
    @patch('app.api.users.get_db')
    def test_get_user_preferences_success(self, mock_get_db, mock_get_user, client, mock_db, mock_user):
        """Test successful retrieval of user preferences."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        # Act
        response = client.get("/users/me/preferences")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == "test-user-123"
        assert data["daily_xp_goal"] == 20
        assert data["timezone"] == "UTC"
        assert data["language_interface"] == "en"
        assert data["learning_language"] == "es"
        assert data["difficulty_level"] == "intermediate"
        assert isinstance(data["lesson_reminders"], bool)
        assert isinstance(data["sound_effects"], bool)
        assert "created_at" in data
        assert "updated_at" in data
    
    @patch('app.api.users.get_current_user')
    @patch('app.api.users.get_db')
    def test_get_user_preferences_error(self, mock_get_db, mock_get_user, client, mock_db, mock_user):
        """Test user preferences retrieval with error."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        mock_get_db.side_effect = Exception("Database connection failed")
        
        # Act
        response = client.get("/users/me/preferences")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"]["error"] == "preferences_fetch_failed"
    
    @patch('app.api.users.get_current_user')
    @patch('app.api.users.get_db')
    def test_update_user_preferences_success(self, mock_get_db, mock_get_user, client, mock_db, mock_user):
        """Test successful update of user preferences."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        preferences_data = {
            "daily_xp_goal": 50,
            "timezone": "America/New_York",
            "language_interface": "es",
            "learning_language": "fr",
            "difficulty_level": "advanced",
            "lesson_reminders": False,
            "sound_effects": True,
            "auto_play_audio": False
        }
        
        # Act
        response = client.put("/users/me/preferences", json=preferences_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Preferences updated successfully"
        assert "daily_xp_goal" in data["updated_fields"]
        assert "timezone" in data["updated_fields"]
        assert len(data["updated_fields"]) >= 2  # At least the user table fields
        assert "updated_at" in data
        
        # Verify user object was updated
        assert mock_user.daily_xp_goal == 50
        assert mock_user.timezone == "America/New_York"
        mock_db.commit.assert_called_once()
    
    @patch('app.api.users.get_current_user')
    @patch('app.api.users.get_db')
    def test_update_user_preferences_partial(self, mock_get_db, mock_get_user, client, mock_db, mock_user):
        """Test partial update of user preferences."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        preferences_data = {
            "daily_xp_goal": 30,
            "sound_effects": False
        }
        
        # Act
        response = client.put("/users/me/preferences", json=preferences_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Preferences updated successfully"
        assert "daily_xp_goal" in data["updated_fields"]
        assert "sound_effects" in data["updated_fields"]
        
        # Verify only specified fields were updated
        assert mock_user.daily_xp_goal == 30
        mock_db.commit.assert_called_once()
    
    @patch('app.api.users.get_current_user')
    @patch('app.api.users.get_db')
    def test_update_user_preferences_no_changes(self, mock_get_db, mock_get_user, client, mock_db, mock_user):
        """Test update with no actual changes."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        preferences_data = {}  # No changes
        
        # Act
        response = client.put("/users/me/preferences", json=preferences_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "No changes were made"
        assert data["updated_fields"] == []
        
        # Verify no database operations
        mock_db.commit.assert_not_called()
    
    @patch('app.api.users.get_current_user')
    @patch('app.api.users.get_db')
    def test_update_user_preferences_invalid_data(self, mock_get_db, mock_get_user, client, mock_db, mock_user):
        """Test update with invalid preference data."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        preferences_data = {
            "daily_xp_goal": 150,  # Invalid: exceeds maximum
            "timezone": "Invalid/Timezone"
        }
        
        # Act
        response = client.put("/users/me/preferences", json=preferences_data)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Verify no database operations
        mock_db.commit.assert_not_called()
    
    @patch('app.api.users.get_current_user')
    @patch('app.api.users.get_db')
    def test_update_user_preferences_server_error(self, mock_get_db, mock_get_user, client, mock_db, mock_user):
        """Test update with server error."""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db
        mock_db.commit.side_effect = Exception("Database error")
        
        preferences_data = {
            "daily_xp_goal": 30
        }
        
        # Act
        response = client.put("/users/me/preferences", json=preferences_data)
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"]["error"] == "preferences_update_failed"
        
        # Verify rollback was called
        mock_db.rollback.assert_called_once()


class TestFileUploadService:
    """Test file upload service functionality."""
    
    @pytest.fixture
    def file_service(self):
        """Create file upload service instance."""
        return FileUploadService()
    
    @pytest.fixture
    def valid_png_content(self):
        """Create valid PNG content."""
        img = Image.new('RGB', (100, 100), color='blue')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
    
    @pytest.fixture
    def valid_jpeg_content(self):
        """Create valid JPEG content."""
        img = Image.new('RGB', (100, 100), color='green')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()
    
    def test_file_extension_extraction(self, file_service):
        """Test file extension extraction."""
        assert file_service._get_file_extension("avatar.png") == "png"
        assert file_service._get_file_extension("avatar.JPEG") == "jpeg"
        assert file_service._get_file_extension("avatar.WebP") == "webp"
        assert file_service._get_file_extension("avatar") == "png"  # Default
        assert file_service._get_file_extension("") == "png"  # Default
    
    def test_image_content_validation_png(self, file_service, valid_png_content):
        """Test PNG image content validation."""
        # Should not raise exception
        file_service._validate_image_content(valid_png_content, "png")
    
    def test_image_content_validation_jpeg(self, file_service, valid_jpeg_content):
        """Test JPEG image content validation."""
        # Should not raise exception
        file_service._validate_image_content(valid_jpeg_content, "jpg")
    
    def test_image_content_validation_invalid(self, file_service):
        """Test invalid image content validation."""
        invalid_content = b"This is not an image"
        
        with pytest.raises(ValueError, match="File is not a valid image"):
            file_service._validate_image_content(invalid_content, "png")
    
    @pytest.mark.asyncio
    async def test_process_avatar_image(self, file_service, valid_png_content):
        """Test avatar image processing."""
        processed_content = await file_service._process_avatar_image(valid_png_content)
        assert isinstance(processed_content, bytes)
        assert len(processed_content) > 0
    
    @pytest.mark.asyncio
    async def test_avatar_upload_validation_empty_file(self, file_service):
        """Test avatar upload with empty file."""
        empty_file = MagicMock(spec=UploadFile)
        empty_file.filename = "test.png"
        empty_file.content_type = "image/png"
        empty_file.read.return_value = b""
        empty_file.seek = MagicMock()
        
        with pytest.raises(ValueError, match="File is empty"):
            await file_service._validate_avatar_file(empty_file)
    
    @pytest.mark.asyncio
    async def test_avatar_upload_validation_large_file(self, file_service):
        """Test avatar upload with oversized file."""
        large_file = MagicMock(spec=UploadFile)
        large_file.filename = "large.png"
        large_file.content_type = "image/png"
        large_file.read.return_value = b"0" * (6 * 1024 * 1024)  # 6MB
        large_file.seek = MagicMock()
        
        with pytest.raises(ValueError, match="File size exceeds maximum"):
            await file_service._validate_avatar_file(large_file)
    
    @pytest.mark.asyncio
    async def test_avatar_upload_validation_invalid_type(self, file_service):
        """Test avatar upload with invalid file type."""
        invalid_file = MagicMock(spec=UploadFile)
        invalid_file.filename = "test.txt"
        invalid_file.content_type = "text/plain"
        invalid_file.read.return_value = b"text content"
        invalid_file.seek = MagicMock()
        
        with pytest.raises(ValueError, match="Invalid file type"):
            await file_service._validate_avatar_file(invalid_file)
    
    def test_get_file_info_nonexistent(self, file_service):
        """Test getting info for non-existent file."""
        result = file_service.get_file_info("/nonexistent/path.png")
        assert result is None
    
    def test_delete_avatar_security(self, file_service):
        """Test avatar deletion security checks."""
        # Should reject files outside avatar directory
        result = file_service.delete_avatar("/etc/passwd")
        assert result is False
        
        result = file_service.delete_avatar("../../../etc/passwd")
        assert result is False
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    def test_delete_avatar_success(self, mock_unlink, mock_exists, file_service):
        """Test successful avatar deletion."""
        mock_exists.return_value = True
        
        result = file_service.delete_avatar("uploads/avatars/test_avatar.png")
        
        assert result is True
        mock_unlink.assert_called_once()
    
    @patch('pathlib.Path.exists')
    def test_delete_avatar_not_found(self, mock_exists, file_service):
        """Test avatar deletion when file doesn't exist."""
        mock_exists.return_value = False
        
        result = file_service.delete_avatar("uploads/avatars/nonexistent.png")
        
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])