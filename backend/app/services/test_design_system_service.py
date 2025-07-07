"""Unit tests for Design System Service"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from pathlib import Path

from app.services.design_system_service import DesignSystemService, DesignTokenExtractor
from app.core.exceptions import ServiceError


class MockTokenExtractor(DesignTokenExtractor):
    """Mock implementation of DesignTokenExtractor for testing"""
    
    async def extract_colors(self, image_data: bytes) -> dict:
        return {"primary": ["#1CB0F6"], "secondary": ["#58CC02"]}
    
    async def extract_typography(self, image_data: bytes) -> dict:
        return {"fonts": ["DIN Round Pro"], "sizes": ["16px", "20px"]}
    
    async def extract_spacing(self, image_data: bytes) -> dict:
        return {"scale": ["4px", "8px", "16px"]}
    
    async def extract_shadows(self, image_data: bytes) -> dict:
        return {"elevation": ["0 2px 4px rgba(0,0,0,0.1)"]}


@pytest.fixture
def design_system_service():
    """Create a design system service instance for testing"""
    service = DesignSystemService()
    return service


@pytest.fixture
def service_with_ai_client():
    """Create a design system service with mocked AI client"""
    ai_client = Mock()
    service = DesignSystemService(ai_client=ai_client)
    return service


class TestDesignSystemService:
    """Test cases for DesignSystemService"""
    
    def test_init(self):
        """Test service initialization"""
        # Arrange & Act
        service = DesignSystemService()
        
        # Assert
        assert service.ai_client is None
        assert service._extractors == {}
        assert service._rate_limiter is None
        assert service._retry_config["max_retries"] == 3
    
    def test_init_with_ai_client(self):
        """Test service initialization with AI client"""
        # Arrange
        ai_client = Mock()
        
        # Act
        service = DesignSystemService(ai_client=ai_client)
        
        # Assert
        assert service.ai_client == ai_client
    
    def test_register_extractor(self, design_system_service):
        """Test registering a token extractor"""
        # Arrange
        extractor = MockTokenExtractor()
        
        # Act
        design_system_service.register_extractor("test", extractor)
        
        # Assert
        assert "test" in design_system_service._extractors
        assert design_system_service._extractors["test"] == extractor
    
    @pytest.mark.asyncio
    async def test_process_screenshot_file_not_found(self, design_system_service):
        """Test processing screenshot with non-existent file"""
        # Arrange
        fake_path = "/path/to/nonexistent.png"
        
        # Act & Assert
        with pytest.raises(ServiceError) as exc_info:
            await design_system_service.process_screenshot(fake_path)
        
        assert "Image not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_screenshot_no_ai_client(self, design_system_service):
        """Test processing screenshot without AI client"""
        # Arrange
        mock_data = b"fake image data"
        
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=mock_data)):
                # Act & Assert
                with pytest.raises(ServiceError) as exc_info:
                    await design_system_service.process_screenshot("/fake/path.png")
                
                assert "AI client not configured" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_screenshot_success(self, service_with_ai_client):
        """Test successful screenshot processing"""
        # Arrange
        mock_data = b"fake image data"
        service = service_with_ai_client
        
        # Mock the AI extraction methods
        service._extract_colors_with_ai = AsyncMock(return_value={"primary": ["#1CB0F6"]})
        service._extract_typography_with_ai = AsyncMock(return_value={"fonts": ["DIN Round Pro"]})
        service._extract_spacing_with_ai = AsyncMock(return_value={"scale": ["8px"]})
        service._extract_shadows_with_ai = AsyncMock(return_value={"elevation": ["none"]})
        service._extract_radii_with_ai = AsyncMock(return_value={"scale": ["8px"]})
        
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=mock_data)):
                # Act
                result = await service.process_screenshot("/fake/path.png")
        
        # Assert
        assert result["success"] is True
        assert "tokens" in result
        assert "metadata" in result
        assert result["tokens"]["colors"]["primary"] == ["#1CB0F6"]
        assert result["metadata"]["source"] == "/fake/path.png"
    
    @pytest.mark.asyncio
    async def test_process_screenshot_with_options(self, service_with_ai_client):
        """Test screenshot processing with custom options"""
        # Arrange
        mock_data = b"fake image data"
        service = service_with_ai_client
        options = {
            "ignore_watermark": True,
            "token_types": ["colors", "typography"]
        }
        
        # Mock methods
        service._remove_watermark = AsyncMock(return_value=mock_data)
        service._extract_colors_with_ai = AsyncMock(return_value={"primary": ["#1CB0F6"]})
        service._extract_typography_with_ai = AsyncMock(return_value={"fonts": ["DIN Round Pro"]})
        
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=mock_data)):
                # Act
                result = await service.process_screenshot("/fake/path.png", options)
        
        # Assert
        assert result["success"] is True
        assert "colors" in result["tokens"]
        assert "typography" in result["tokens"]
        assert "spacing" not in result["tokens"]
        service._remove_watermark.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_process(self, service_with_ai_client):
        """Test batch processing of screenshots"""
        # Arrange
        service = service_with_ai_client
        paths = ["/fake/path1.png", "/fake/path2.png"]
        
        # Mock process_screenshot
        service.process_screenshot = AsyncMock(side_effect=[
            {"success": True, "tokens": {"colors": {}}},
            ServiceError("Processing failed")
        ])
        
        # Act
        results = await service.batch_process(paths)
        
        # Assert
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "Processing failed" in results[1]["error"]
    
    def test_validate_tokens_empty(self, design_system_service):
        """Test token validation with empty tokens"""
        # Arrange
        tokens = {}
        
        # Act
        is_valid, errors = design_system_service.validate_tokens(tokens)
        
        # Assert
        assert is_valid is True
        assert errors == []
    
    def test_validate_tokens_with_data(self, design_system_service):
        """Test token validation with token data"""
        # Arrange
        tokens = {
            "colors": {"primary": ["#1CB0F6"]},
            "typography": {"fonts": ["DIN Round Pro"]},
            "spacing": {"scale": ["8px"]}
        }
        
        # Mock validation methods
        design_system_service._validate_color_tokens = Mock(return_value=[])
        design_system_service._validate_typography_tokens = Mock(return_value=[])
        design_system_service._validate_spacing_tokens = Mock(return_value=[])
        
        # Act
        is_valid, errors = design_system_service.validate_tokens(tokens)
        
        # Assert
        assert is_valid is True
        assert errors == []
        design_system_service._validate_color_tokens.assert_called_once()
        design_system_service._validate_typography_tokens.assert_called_once()
        design_system_service._validate_spacing_tokens.assert_called_once()
    
    def test_validate_tokens_with_errors(self, design_system_service):
        """Test token validation with validation errors"""
        # Arrange
        tokens = {"colors": {"primary": []}}
        
        # Mock validation to return errors
        design_system_service._validate_color_tokens = Mock(
            return_value=["Primary colors cannot be empty"]
        )
        
        # Act
        is_valid, errors = design_system_service.validate_tokens(tokens)
        
        # Assert
        assert is_valid is False
        assert len(errors) == 1
        assert "Primary colors cannot be empty" in errors