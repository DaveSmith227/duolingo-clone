"""Pydantic schemas for Design System data structures

These schemas define the structure and validation for design tokens
extracted from screenshots and used throughout the application.
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator, ConfigDict
from enum import Enum


class TokenType(str, Enum):
    """Enumeration of design token types"""
    COLORS = "colors"
    TYPOGRAPHY = "typography"
    SPACING = "spacing"
    SHADOWS = "shadows"
    RADII = "radii"
    COMPONENTS = "components"


class GradientDirection(str, Enum):
    """Gradient direction options"""
    TO_TOP = "to top"
    TO_RIGHT = "to right"
    TO_BOTTOM = "to bottom"
    TO_LEFT = "to left"
    TO_TOP_RIGHT = "to top right"
    TO_TOP_LEFT = "to top left"
    TO_BOTTOM_RIGHT = "to bottom right"
    TO_BOTTOM_LEFT = "to bottom left"
    RADIAL = "radial"


class ColorGradient(BaseModel):
    """Schema for color gradients"""
    name: str = Field(..., description="Gradient identifier")
    colors: List[str] = Field(..., min_items=2, description="List of hex color values")
    direction: GradientDirection = Field(GradientDirection.TO_RIGHT, description="Gradient direction")
    
    @validator('colors')
    def validate_hex_colors(cls, v):
        """Validate that all colors are valid hex values"""
        import re
        hex_pattern = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$')
        for color in v:
            if not hex_pattern.match(color):
                raise ValueError(f"Invalid hex color: {color}")
        return v


class SemanticColors(BaseModel):
    """Schema for semantic color tokens"""
    success: Optional[str] = Field(None, description="Success state color")
    error: Optional[str] = Field(None, description="Error state color")
    warning: Optional[str] = Field(None, description="Warning state color")
    info: Optional[str] = Field(None, description="Info state color")
    
    @validator('*')
    def validate_hex_color(cls, v):
        """Validate individual hex colors"""
        if v is not None:
            import re
            hex_pattern = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$')
            if not hex_pattern.match(v):
                raise ValueError(f"Invalid hex color: {v}")
        return v


class ColorTokens(BaseModel):
    """Schema for color design tokens"""
    primary: List[str] = Field(default_factory=list, description="Primary brand colors")
    secondary: List[str] = Field(default_factory=list, description="Secondary colors")
    semantic: SemanticColors = Field(default_factory=SemanticColors, description="Semantic color meanings")
    neutrals: List[str] = Field(default_factory=list, description="Neutral colors (grays, blacks, whites)")
    gradients: List[ColorGradient] = Field(default_factory=list, description="Color gradients")
    
    model_config = ConfigDict(from_attributes=True)


class FontWeight(str, Enum):
    """Common font weight values"""
    THIN = "100"
    EXTRA_LIGHT = "200"
    LIGHT = "300"
    REGULAR = "400"
    MEDIUM = "500"
    SEMI_BOLD = "600"
    BOLD = "700"
    EXTRA_BOLD = "800"
    BLACK = "900"


class TypographyToken(BaseModel):
    """Schema for individual typography style"""
    name: str = Field(..., description="Style name (e.g., 'heading-1', 'body-text')")
    fontFamily: str = Field(..., description="Font family name")
    fontSize: str = Field(..., description="Font size with unit (e.g., '16px', '1.2rem')")
    fontWeight: Union[FontWeight, str] = Field(..., description="Font weight")
    lineHeight: Optional[str] = Field(None, description="Line height with unit")
    letterSpacing: Optional[str] = Field(None, description="Letter spacing with unit")
    textTransform: Optional[str] = Field(None, description="Text transform (uppercase, lowercase, capitalize)")


class TypographyTokens(BaseModel):
    """Schema for typography design tokens"""
    fonts: List[str] = Field(default_factory=list, description="List of font families used")
    sizes: List[str] = Field(default_factory=list, description="Font size scale")
    weights: List[Union[FontWeight, str]] = Field(default_factory=list, description="Font weights used")
    lineHeights: List[str] = Field(default_factory=list, description="Line height scale")
    styles: List[TypographyToken] = Field(default_factory=list, description="Complete typography styles")
    
    model_config = ConfigDict(from_attributes=True)


class SpacingScale(BaseModel):
    """Schema for spacing scale"""
    scale: List[str] = Field(default_factory=list, description="Spacing values (e.g., '4px', '8px')")
    baseUnit: Optional[str] = Field(None, description="Base spacing unit if applicable")
    
    @validator('scale')
    def validate_spacing_values(cls, v):
        """Validate spacing values have units"""
        import re
        unit_pattern = re.compile(r'^\d+(\.\d+)?(px|rem|em|%)$')
        for value in v:
            if not unit_pattern.match(value):
                raise ValueError(f"Invalid spacing value: {value}")
        return v


class ComponentSpacing(BaseModel):
    """Schema for component-specific spacing"""
    padding: Optional[Dict[str, str]] = Field(None, description="Padding values")
    margin: Optional[Dict[str, str]] = Field(None, description="Margin values")
    gap: Optional[str] = Field(None, description="Gap/spacing between elements")


class SpacingTokens(BaseModel):
    """Schema for spacing design tokens"""
    scale: List[str] = Field(default_factory=list, description="General spacing scale")
    components: Dict[str, ComponentSpacing] = Field(
        default_factory=dict, 
        description="Component-specific spacing"
    )
    
    model_config = ConfigDict(from_attributes=True)


class ShadowToken(BaseModel):
    """Schema for individual shadow"""
    name: str = Field(..., description="Shadow identifier")
    value: str = Field(..., description="CSS shadow value")
    offsetX: Optional[str] = Field(None, description="Horizontal offset")
    offsetY: Optional[str] = Field(None, description="Vertical offset")
    blur: Optional[str] = Field(None, description="Blur radius")
    spread: Optional[str] = Field(None, description="Spread radius")
    color: Optional[str] = Field(None, description="Shadow color")
    inset: bool = Field(False, description="Whether shadow is inset")


class ShadowTokens(BaseModel):
    """Schema for shadow design tokens"""
    elevation: List[ShadowToken] = Field(
        default_factory=list, 
        description="Box shadow tokens for elevation"
    )
    text: List[ShadowToken] = Field(
        default_factory=list, 
        description="Text shadow tokens"
    )
    
    model_config = ConfigDict(from_attributes=True)


class RadiusScale(BaseModel):
    """Schema for border radius scale"""
    scale: List[str] = Field(default_factory=list, description="Radius values")
    
    @validator('scale')
    def validate_radius_values(cls, v):
        """Validate radius values"""
        import re
        unit_pattern = re.compile(r'^\d+(\.\d+)?(px|rem|em|%)?$|^full$')
        for value in v:
            if not unit_pattern.match(value):
                raise ValueError(f"Invalid radius value: {value}")
        return v


class RadiusTokens(BaseModel):
    """Schema for border radius design tokens"""
    scale: List[str] = Field(default_factory=list, description="General radius scale")
    components: Dict[str, str] = Field(
        default_factory=dict, 
        description="Component-specific radius values"
    )
    
    model_config = ConfigDict(from_attributes=True)


class ComponentToken(BaseModel):
    """Schema for component-specific design tokens"""
    name: str = Field(..., description="Component name")
    colors: Optional[Dict[str, str]] = Field(None, description="Component colors")
    typography: Optional[str] = Field(None, description="Typography style reference")
    spacing: Optional[ComponentSpacing] = Field(None, description="Component spacing")
    radius: Optional[str] = Field(None, description="Border radius")
    shadow: Optional[str] = Field(None, description="Shadow reference")
    states: Optional[Dict[str, Dict[str, Any]]] = Field(
        None, 
        description="State variations (hover, active, disabled)"
    )


class DesignTokens(BaseModel):
    """Complete design token collection"""
    colors: Optional[ColorTokens] = Field(None, description="Color tokens")
    typography: Optional[TypographyTokens] = Field(None, description="Typography tokens")
    spacing: Optional[SpacingTokens] = Field(None, description="Spacing tokens")
    shadows: Optional[ShadowTokens] = Field(None, description="Shadow tokens")
    radii: Optional[RadiusTokens] = Field(None, description="Border radius tokens")
    components: List[ComponentToken] = Field(default_factory=list, description="Component tokens")
    
    model_config = ConfigDict(from_attributes=True)


class TokenExtractionRequest(BaseModel):
    """Request schema for token extraction"""
    image_path: str = Field(..., description="Path to screenshot image")
    token_types: List[TokenType] = Field(
        default=[TokenType.COLORS, TokenType.TYPOGRAPHY, TokenType.SPACING, TokenType.SHADOWS, TokenType.RADII],
        description="Types of tokens to extract"
    )
    ignore_watermark: bool = Field(True, description="Whether to ignore Mobbin watermark")
    ai_provider: Optional[str] = Field(None, description="Preferred AI provider (claude/openai)")


class TokenExtractionResponse(BaseModel):
    """Response schema for token extraction"""
    success: bool = Field(..., description="Whether extraction was successful")
    tokens: Optional[DesignTokens] = Field(None, description="Extracted design tokens")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extraction metadata")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


class BatchExtractionRequest(BaseModel):
    """Request schema for batch token extraction"""
    image_paths: List[str] = Field(..., min_items=1, description="List of image paths")
    token_types: List[TokenType] = Field(
        default=[TokenType.COLORS, TokenType.TYPOGRAPHY, TokenType.SPACING, TokenType.SHADOWS, TokenType.RADII],
        description="Types of tokens to extract"
    )
    ignore_watermark: bool = Field(True, description="Whether to ignore Mobbin watermark")
    ai_provider: Optional[str] = Field(None, description="Preferred AI provider")


class BatchExtractionResponse(BaseModel):
    """Response schema for batch token extraction"""
    results: List[TokenExtractionResponse] = Field(..., description="Extraction results for each image")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary statistics")


class TokenValidationRequest(BaseModel):
    """Request schema for token validation"""
    tokens: DesignTokens = Field(..., description="Tokens to validate")
    strict_mode: bool = Field(False, description="Whether to use strict validation")


class TokenValidationResponse(BaseModel):
    """Response schema for token validation"""
    valid: bool = Field(..., description="Whether tokens are valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")