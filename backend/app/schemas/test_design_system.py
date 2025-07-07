"""Unit tests for Design System schemas"""

import pytest
from pydantic import ValidationError

from app.schemas.design_system import (
    ColorGradient,
    GradientDirection,
    SemanticColors,
    ColorTokens,
    FontWeight,
    TypographyToken,
    TypographyTokens,
    SpacingScale,
    ComponentSpacing,
    SpacingTokens,
    ShadowToken,
    ShadowTokens,
    RadiusScale,
    RadiusTokens,
    ComponentToken,
    DesignTokens,
    TokenType,
    TokenExtractionRequest,
    TokenExtractionResponse
)


class TestColorSchemas:
    """Test cases for color-related schemas"""
    
    def test_color_gradient_valid(self):
        """Test valid color gradient creation"""
        # Arrange & Act
        gradient = ColorGradient(
            name="primary-gradient",
            colors=["#1CB0F6", "#58CC02"],
            direction=GradientDirection.TO_RIGHT
        )
        
        # Assert
        assert gradient.name == "primary-gradient"
        assert len(gradient.colors) == 2
        assert gradient.direction == GradientDirection.TO_RIGHT
    
    def test_color_gradient_invalid_hex(self):
        """Test color gradient with invalid hex color"""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ColorGradient(
                name="invalid",
                colors=["#1CB0F6", "not-a-hex"],
                direction=GradientDirection.TO_RIGHT
            )
        
        assert "Invalid hex color" in str(exc_info.value)
    
    def test_color_gradient_too_few_colors(self):
        """Test color gradient with too few colors"""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ColorGradient(
                name="invalid",
                colors=["#1CB0F6"],  # Need at least 2
                direction=GradientDirection.TO_RIGHT
            )
    
    def test_semantic_colors_valid(self):
        """Test valid semantic colors"""
        # Arrange & Act
        colors = SemanticColors(
            success="#58CC02",
            error="#FF4B4B",
            warning="#FFA500",
            info="#1CB0F6"
        )
        
        # Assert
        assert colors.success == "#58CC02"
        assert colors.error == "#FF4B4B"
    
    def test_semantic_colors_optional(self):
        """Test semantic colors with optional fields"""
        # Arrange & Act
        colors = SemanticColors(success="#58CC02")
        
        # Assert
        assert colors.success == "#58CC02"
        assert colors.error is None
        assert colors.warning is None
    
    def test_color_tokens_complete(self):
        """Test complete color tokens"""
        # Arrange & Act
        tokens = ColorTokens(
            primary=["#1CB0F6", "#2B70C9"],
            secondary=["#58CC02", "#89E219"],
            semantic=SemanticColors(success="#58CC02", error="#FF4B4B"),
            neutrals=["#FFFFFF", "#000000", "#777777"],
            gradients=[
                ColorGradient(
                    name="hero-gradient",
                    colors=["#1CB0F6", "#2B70C9"],
                    direction=GradientDirection.TO_BOTTOM
                )
            ]
        )
        
        # Assert
        assert len(tokens.primary) == 2
        assert len(tokens.gradients) == 1
        assert tokens.semantic.success == "#58CC02"


class TestTypographySchemas:
    """Test cases for typography-related schemas"""
    
    def test_typography_token_valid(self):
        """Test valid typography token"""
        # Arrange & Act
        token = TypographyToken(
            name="heading-1",
            fontFamily="DIN Round Pro",
            fontSize="32px",
            fontWeight=FontWeight.BOLD,
            lineHeight="1.2",
            letterSpacing="0.02em"
        )
        
        # Assert
        assert token.name == "heading-1"
        assert token.fontWeight == FontWeight.BOLD
        assert token.fontSize == "32px"
    
    def test_typography_token_string_weight(self):
        """Test typography token with string font weight"""
        # Arrange & Act
        token = TypographyToken(
            name="custom",
            fontFamily="Arial",
            fontSize="16px",
            fontWeight="650"  # Custom weight value
        )
        
        # Assert
        assert token.fontWeight == "650"
    
    def test_typography_tokens_complete(self):
        """Test complete typography tokens"""
        # Arrange & Act
        tokens = TypographyTokens(
            fonts=["DIN Round Pro", "Arial"],
            sizes=["12px", "16px", "24px", "32px"],
            weights=[FontWeight.REGULAR, FontWeight.BOLD],
            lineHeights=["1", "1.2", "1.5"],
            styles=[
                TypographyToken(
                    name="body",
                    fontFamily="DIN Round Pro",
                    fontSize="16px",
                    fontWeight=FontWeight.REGULAR
                )
            ]
        )
        
        # Assert
        assert len(tokens.fonts) == 2
        assert len(tokens.sizes) == 4
        assert len(tokens.styles) == 1


class TestSpacingSchemas:
    """Test cases for spacing-related schemas"""
    
    def test_spacing_scale_valid(self):
        """Test valid spacing scale"""
        # Arrange & Act
        scale = SpacingScale(
            scale=["4px", "8px", "16px", "24px"],
            baseUnit="4px"
        )
        
        # Assert
        assert len(scale.scale) == 4
        assert scale.baseUnit == "4px"
    
    def test_spacing_scale_invalid_value(self):
        """Test spacing scale with invalid value"""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SpacingScale(scale=["4", "8px"])  # Missing unit
        
        assert "Invalid spacing value" in str(exc_info.value)
    
    def test_component_spacing_valid(self):
        """Test valid component spacing"""
        # Arrange & Act
        spacing = ComponentSpacing(
            padding={"top": "16px", "bottom": "16px", "left": "24px", "right": "24px"},
            margin={"bottom": "8px"},
            gap="12px"
        )
        
        # Assert
        assert spacing.padding["top"] == "16px"
        assert spacing.gap == "12px"


class TestShadowSchemas:
    """Test cases for shadow-related schemas"""
    
    def test_shadow_token_valid(self):
        """Test valid shadow token"""
        # Arrange & Act
        shadow = ShadowToken(
            name="elevation-1",
            value="0 2px 4px rgba(0,0,0,0.1)",
            offsetX="0",
            offsetY="2px",
            blur="4px",
            color="rgba(0,0,0,0.1)"
        )
        
        # Assert
        assert shadow.name == "elevation-1"
        assert shadow.blur == "4px"
        assert not shadow.inset
    
    def test_shadow_tokens_complete(self):
        """Test complete shadow tokens"""
        # Arrange & Act
        tokens = ShadowTokens(
            elevation=[
                ShadowToken(
                    name="small",
                    value="0 1px 2px rgba(0,0,0,0.05)"
                )
            ],
            text=[
                ShadowToken(
                    name="subtle",
                    value="1px 1px 2px rgba(0,0,0,0.3)"
                )
            ]
        )
        
        # Assert
        assert len(tokens.elevation) == 1
        assert len(tokens.text) == 1


class TestRadiusSchemas:
    """Test cases for radius-related schemas"""
    
    def test_radius_scale_valid(self):
        """Test valid radius scale"""
        # Arrange & Act
        scale = RadiusScale(scale=["4px", "8px", "16px", "24px", "full"])
        
        # Assert
        assert len(scale.scale) == 5
        assert "full" in scale.scale
    
    def test_radius_scale_invalid_value(self):
        """Test radius scale with invalid value"""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            RadiusScale(scale=["4px", "invalid-radius"])
        
        assert "Invalid radius value" in str(exc_info.value)


class TestComponentSchemas:
    """Test cases for component-related schemas"""
    
    def test_component_token_complete(self):
        """Test complete component token"""
        # Arrange & Act
        component = ComponentToken(
            name="primary-button",
            colors={"background": "#1CB0F6", "text": "#FFFFFF"},
            typography="button-text",
            spacing=ComponentSpacing(padding={"all": "12px 24px"}),
            radius="24px",
            shadow="elevation-1",
            states={
                "hover": {"background": "#2B70C9"},
                "active": {"background": "#1A5FB4"},
                "disabled": {"opacity": "0.5"}
            }
        )
        
        # Assert
        assert component.name == "primary-button"
        assert component.colors["background"] == "#1CB0F6"
        assert "hover" in component.states


class TestDesignTokensSchema:
    """Test cases for complete design tokens schema"""
    
    def test_design_tokens_complete(self):
        """Test complete design tokens"""
        # Arrange & Act
        tokens = DesignTokens(
            colors=ColorTokens(primary=["#1CB0F6"]),
            typography=TypographyTokens(fonts=["DIN Round Pro"]),
            spacing=SpacingTokens(scale=["8px", "16px"]),
            shadows=ShadowTokens(),
            radii=RadiusTokens(scale=["8px", "16px"]),
            components=[
                ComponentToken(name="button", colors={"bg": "#1CB0F6"})
            ]
        )
        
        # Assert
        assert tokens.colors.primary[0] == "#1CB0F6"
        assert len(tokens.components) == 1
    
    def test_design_tokens_partial(self):
        """Test design tokens with optional fields"""
        # Arrange & Act
        tokens = DesignTokens(colors=ColorTokens(primary=["#1CB0F6"]))
        
        # Assert
        assert tokens.colors is not None
        assert tokens.typography is None
        assert tokens.spacing is None


class TestRequestResponseSchemas:
    """Test cases for request/response schemas"""
    
    def test_token_extraction_request_defaults(self):
        """Test token extraction request with defaults"""
        # Arrange & Act
        request = TokenExtractionRequest(image_path="/path/to/image.png")
        
        # Assert
        assert request.image_path == "/path/to/image.png"
        assert len(request.token_types) == 5
        assert request.ignore_watermark is True
        assert request.ai_provider is None
    
    def test_token_extraction_request_custom(self):
        """Test token extraction request with custom values"""
        # Arrange & Act
        request = TokenExtractionRequest(
            image_path="/path/to/image.png",
            token_types=[TokenType.COLORS, TokenType.TYPOGRAPHY],
            ignore_watermark=False,
            ai_provider="claude"
        )
        
        # Assert
        assert len(request.token_types) == 2
        assert TokenType.COLORS in request.token_types
        assert request.ai_provider == "claude"
    
    def test_token_extraction_response_success(self):
        """Test successful token extraction response"""
        # Arrange & Act
        response = TokenExtractionResponse(
            success=True,
            tokens=DesignTokens(colors=ColorTokens(primary=["#1CB0F6"])),
            metadata={"duration": 1.5, "provider": "claude"},
            errors=[]
        )
        
        # Assert
        assert response.success is True
        assert response.tokens.colors.primary[0] == "#1CB0F6"
        assert response.metadata["duration"] == 1.5
    
    def test_token_extraction_response_failure(self):
        """Test failed token extraction response"""
        # Arrange & Act
        response = TokenExtractionResponse(
            success=False,
            tokens=None,
            errors=["AI client not configured", "Image not found"]
        )
        
        # Assert
        assert response.success is False
        assert response.tokens is None
        assert len(response.errors) == 2