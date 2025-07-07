"""Unit tests for Design System API endpoints"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from pathlib import Path
import tempfile
import os

from app.api.design_system import (
    extract_tokens,
    extract_tokens_from_upload,
    batch_extract_tokens,
    validate_tokens,
    health_check,
    get_supported_tokens,
    get_design_service
)
from app.schemas.design_system import (
    TokenExtractionRequest,
    TokenExtractionResponse,
    BatchExtractionRequest,
    TokenValidationRequest,
    DesignTokens,
    ColorTokens,
    TokenType
)
from app.schemas.users import User
from app.services.design_system_service import DesignSystemService


@pytest.fixture
def mock_user():
    """Create a mock authenticated user"""
    return User(
        id=1,
        email="test@example.com",
        is_active=True,
        is_superuser=False
    )


@pytest.fixture
def mock_design_service():
    """Create a mock design system service"""
    service = Mock(spec=DesignSystemService)
    service.ai_clients = {"claude": Mock(), "openai": Mock()}
    return service


@pytest.fixture
def mock_extraction_request():
    """Create a mock token extraction request"""
    return TokenExtractionRequest(
        image_path="/test/image.png",
        token_types=[TokenType.COLORS, TokenType.TYPOGRAPHY],
        ignore_watermark=True,
        ai_provider="claude"
    )


class TestExtractTokens:
    """Test cases for extract_tokens endpoint"""
    
    @pytest.mark.asyncio
    async def test_extract_tokens_success(self, mock_user, mock_design_service, mock_extraction_request):
        """Test successful token extraction"""
        # Arrange
        mock_design_service.process_screenshot = AsyncMock(return_value={
            "success": True,
            "tokens": {
                "colors": {"primary": ["#1CB0F6"], "secondary": [], "semantic": {}, "neutrals": [], "gradients": []},
                "typography": {"fonts": ["DIN Round Pro"], "sizes": [], "weights": [], "lineHeights": [], "styles": []}
            },
            "metadata": {"source": "/test/image.png", "extracted_types": ["colors", "typography"]}
        })
        
        with patch("pathlib.Path.exists", return_value=True):
            # Act
            response = await extract_tokens(mock_extraction_request, mock_user, mock_design_service)
        
        # Assert
        assert response.success is True
        assert response.tokens is not None
        assert response.tokens.colors.primary == ["#1CB0F6"]
        assert response.metadata["source"] == "/test/image.png"
        assert len(response.errors) == 0
    
    @pytest.mark.asyncio
    async def test_extract_tokens_image_not_found(self, mock_user, mock_design_service, mock_extraction_request):
        """Test extraction with non-existent image"""
        # Arrange
        with patch("pathlib.Path.exists", return_value=False):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await extract_tokens(mock_extraction_request, mock_user, mock_design_service)
            
            assert exc_info.value.status_code == 404
            assert "Image not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_extract_tokens_service_error(self, mock_user, mock_design_service, mock_extraction_request):
        """Test extraction with service error"""
        # Arrange
        mock_design_service.process_screenshot = AsyncMock(side_effect=Exception("AI service error"))
        
        with patch("pathlib.Path.exists", return_value=True):
            # Act
            response = await extract_tokens(mock_extraction_request, mock_user, mock_design_service)
        
        # Assert
        assert response.success is False
        assert response.tokens is None
        assert "AI service error" in response.errors[0]
    
    @pytest.mark.asyncio
    async def test_extract_tokens_partial_failure(self, mock_user, mock_design_service, mock_extraction_request):
        """Test extraction with partial failure"""
        # Arrange
        mock_design_service.process_screenshot = AsyncMock(return_value={
            "success": False,
            "error": "Failed to extract typography tokens"
        })
        
        with patch("pathlib.Path.exists", return_value=True):
            # Act
            response = await extract_tokens(mock_extraction_request, mock_user, mock_design_service)
        
        # Assert
        assert response.success is False
        assert response.tokens is None
        assert "Failed to extract typography tokens" in response.errors[0]


class TestExtractTokensFromUpload:
    """Test cases for extract_tokens_from_upload endpoint"""
    
    @pytest.mark.asyncio
    async def test_upload_success(self, mock_user, mock_design_service):
        """Test successful file upload and extraction"""
        # Arrange
        mock_file = Mock()
        mock_file.content_type = "image/png"
        mock_file.filename = "test.png"
        mock_file.read = AsyncMock(return_value=b"fake image data")
        
        mock_design_service.process_screenshot = AsyncMock(return_value={
            "success": True,
            "tokens": {"colors": {"primary": ["#1CB0F6"]}},
            "metadata": {}
        })
        
        with patch("app.api.design_system.extract_tokens") as mock_extract:
            mock_extract.return_value = TokenExtractionResponse(
                success=True,
                tokens=DesignTokens(colors=ColorTokens(primary=["#1CB0F6"])),
                metadata={},
                errors=[]
            )
            
            # Act
            response = await extract_tokens_from_upload(
                file=mock_file,
                token_types="colors",
                ignore_watermark=True,
                ai_provider="claude",
                current_user=mock_user,
                service=mock_design_service
            )
        
        # Assert
        assert response.success is True
        assert response.tokens.colors.primary == ["#1CB0F6"]
    
    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, mock_user, mock_design_service):
        """Test upload with non-image file"""
        # Arrange
        mock_file = Mock()
        mock_file.content_type = "text/plain"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await extract_tokens_from_upload(
                file=mock_file,
                current_user=mock_user,
                service=mock_design_service
            )
        
        assert exc_info.value.status_code == 400
        assert "File must be an image" in str(exc_info.value.detail)


class TestBatchExtractTokens:
    """Test cases for batch_extract_tokens endpoint"""
    
    @pytest.mark.asyncio
    async def test_batch_extract_success(self, mock_user, mock_design_service):
        """Test successful batch extraction"""
        # Arrange
        request = BatchExtractionRequest(
            image_paths=["/test/image1.png", "/test/image2.png"],
            token_types=[TokenType.COLORS],
            ignore_watermark=True
        )
        
        with patch("app.api.design_system.extract_tokens") as mock_extract:
            mock_extract.side_effect = [
                TokenExtractionResponse(success=True, tokens=DesignTokens(), metadata={}, errors=[]),
                TokenExtractionResponse(success=True, tokens=DesignTokens(), metadata={}, errors=[])
            ]
            
            # Act
            response = await batch_extract_tokens(
                request, 
                background_tasks=Mock(),
                current_user=mock_user,
                service=mock_design_service
            )
        
        # Assert
        assert len(response.results) == 2
        assert response.summary["total"] == 2
        assert response.summary["successful"] == 2
        assert response.summary["failed"] == 0
    
    @pytest.mark.asyncio
    async def test_batch_extract_partial_failure(self, mock_user, mock_design_service):
        """Test batch extraction with some failures"""
        # Arrange
        request = BatchExtractionRequest(
            image_paths=["/test/image1.png", "/test/image2.png"],
            token_types=[TokenType.COLORS]
        )
        
        with patch("app.api.design_system.extract_tokens") as mock_extract:
            mock_extract.side_effect = [
                TokenExtractionResponse(success=True, tokens=DesignTokens(), metadata={}, errors=[]),
                TokenExtractionResponse(success=False, tokens=None, metadata={}, errors=["Failed"])
            ]
            
            # Act
            response = await batch_extract_tokens(
                request,
                background_tasks=Mock(),
                current_user=mock_user,
                service=mock_design_service
            )
        
        # Assert
        assert response.summary["successful"] == 1
        assert response.summary["failed"] == 1


class TestValidateTokens:
    """Test cases for validate_tokens endpoint"""
    
    @pytest.mark.asyncio
    async def test_validate_tokens_valid(self, mock_user, mock_design_service):
        """Test validation of valid tokens"""
        # Arrange
        request = TokenValidationRequest(
            tokens=DesignTokens(colors=ColorTokens(primary=["#1CB0F6"])),
            strict_mode=False
        )
        
        mock_design_service.validate_tokens = Mock(return_value=(True, []))
        
        # Act
        response = await validate_tokens(request, mock_user, mock_design_service)
        
        # Assert
        assert response.valid is True
        assert len(response.errors) == 0
        assert len(response.warnings) == 0
    
    @pytest.mark.asyncio
    async def test_validate_tokens_strict_mode(self, mock_user, mock_design_service):
        """Test validation in strict mode"""
        # Arrange
        request = TokenValidationRequest(
            tokens=DesignTokens(colors=ColorTokens(primary=[])),  # Empty primary colors
            strict_mode=True
        )
        
        mock_design_service.validate_tokens = Mock(return_value=(True, []))
        
        # Act
        response = await validate_tokens(request, mock_user, mock_design_service)
        
        # Assert
        assert response.valid is False  # Fails strict validation
        assert "No primary colors defined" in response.warnings
    
    @pytest.mark.asyncio
    async def test_validate_tokens_with_errors(self, mock_user, mock_design_service):
        """Test validation with errors"""
        # Arrange
        request = TokenValidationRequest(
            tokens=DesignTokens(),
            strict_mode=False
        )
        
        mock_design_service.validate_tokens = Mock(return_value=(False, ["Invalid color format"]))
        
        # Act
        response = await validate_tokens(request, mock_user, mock_design_service)
        
        # Assert
        assert response.valid is False
        assert "Invalid color format" in response.errors


class TestHealthCheck:
    """Test cases for health check endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_design_service):
        """Test healthy service status"""
        # Act
        response = await health_check(mock_design_service)
        
        # Assert
        assert response["status"] == "healthy"
        assert response["service"] == "design-system"
        assert "claude" in response["ai_clients"]
        assert "openai" in response["ai_clients"]
        assert response["ai_configured"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_no_ai_clients(self):
        """Test health check with no AI clients"""
        # Arrange
        service = Mock(spec=DesignSystemService)
        service.ai_clients = {}
        
        # Act
        response = await health_check(service)
        
        # Assert
        assert response["status"] == "healthy"
        assert response["ai_configured"] is False
        assert len(response["ai_clients"]) == 0
    
    @pytest.mark.asyncio
    async def test_health_check_error(self):
        """Test health check with error"""
        # Arrange
        service = Mock(spec=DesignSystemService)
        service.ai_clients = Mock(side_effect=Exception("Service error"))
        
        # Act
        response = await health_check(service)
        
        # Assert
        assert response["status"] == "unhealthy"
        assert "error" in response


class TestSupportedTokens:
    """Test cases for supported tokens endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_supported_tokens(self):
        """Test getting list of supported token types"""
        # Act
        response = await get_supported_tokens()
        
        # Assert
        assert "token_types" in response
        assert len(response["token_types"]) == 6  # All TokenType enum values
        
        # Check first token type
        first_type = response["token_types"][0]
        assert first_type["type"] == TokenType.COLORS
        assert "description" in first_type
        assert "Color palettes" in first_type["description"]


class TestGetDesignService:
    """Test cases for get_design_service dependency"""
    
    @pytest.mark.asyncio
    async def test_get_design_service_singleton(self):
        """Test that service is created as singleton"""
        # Arrange
        with patch("app.api.design_system.get_settings") as mock_settings:
            with patch("app.api.design_system.configure_ai_clients") as mock_configure:
                mock_configure.return_value = {"claude": Mock()}
                
                # Act
                service1 = await get_design_service()
                service2 = await get_design_service()
                
                # Assert
                assert service1 is service2  # Same instance
                mock_configure.assert_called_once()  # Only configured once