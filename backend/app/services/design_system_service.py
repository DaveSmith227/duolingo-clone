"""Design System Service for AI Vision Processing

This service handles AI-powered design token extraction from screenshots.
It provides methods for analyzing images and extracting design elements
like colors, typography, spacing, shadows, and component-specific tokens.
"""

from dotenv import load_dotenv
load_dotenv()

from typing import List, Dict, Any, Optional, Tuple
import base64
from pathlib import Path
import logging
from abc import ABC, abstractmethod
import os
import time
import asyncio
import json

from fastapi import HTTPException
from app.core.exceptions import ServiceError
from app.interfaces.auth_service_interface import IAuthService
from app.services.ai_vision_client import AIVisionClient, configure_ai_clients, ClaudeVisionClient, OpenAIVisionClient

logger = logging.getLogger(__name__)


class DesignTokenExtractor(ABC):
    """Abstract base class for design token extraction"""
    
    @abstractmethod
    async def extract_colors(self, image_data: bytes) -> Dict[str, Any]:
        """Extract color tokens from image"""
        pass
    
    @abstractmethod
    async def extract_typography(self, image_data: bytes) -> Dict[str, Any]:
        """Extract typography tokens from image"""
        pass
    
    @abstractmethod
    async def extract_spacing(self, image_data: bytes) -> Dict[str, Any]:
        """Extract spacing tokens from image"""
        pass
    
    @abstractmethod
    async def extract_shadows(self, image_data: bytes) -> Dict[str, Any]:
        """Extract shadow tokens from image"""
        pass


class DesignSystemService:
    """Service for processing design system screenshots and extracting tokens"""
    
    def __init__(self, ai_clients: Optional[Dict[str, AIVisionClient]] = None):
        """Initialize with proper dependency injection"""
        # Load environment variables
        load_dotenv()
        
        # Get API keys
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if not anthropic_key and not openai_key:
            logger.error("No AI API keys configured")
            raise ValueError("At least one AI API key must be configured")
        
        # Initialize clients if not provided
        if ai_clients:
            self.ai_clients = ai_clients
        else:
            self.ai_clients = {}
            if anthropic_key:
                self.ai_clients['claude'] = ClaudeVisionClient(api_key=anthropic_key)
                logger.info("Claude Vision client initialized")
            if openai_key:
                self.ai_clients['openai'] = OpenAIVisionClient(api_key=openai_key)
                logger.info("OpenAI Vision client initialized")
        
        self._preferred_client = 'claude' if 'claude' in self.ai_clients else ('openai' if 'openai' in self.ai_clients else None)
        self._extractors: Dict[str, DesignTokenExtractor] = {}
    
    def register_extractor(self, name: str, extractor: DesignTokenExtractor) -> None:
        """Register a token extractor
        
        Args:
            name: Name of the extractor
            extractor: Extractor instance
        """
        self._extractors[name] = extractor
    
    def _get_ai_client(self) -> Any:
        """Get AI client"""
        if not self._preferred_client or not self.ai_clients:
            raise ServiceError("No AI client configured")
        
        if self._preferred_client in self.ai_clients:
            return self.ai_clients[self._preferred_client]
        
        raise ServiceError(f"AI client '{self._preferred_client}' not available")
    
    def _resolve_image_path(self, image_path: str) -> Path:
        """Resolve image path relative to frontend if needed"""
        path = Path(image_path)
        if not path.is_absolute():
            # Try multiple resolution strategies
            # 1. Relative to current working directory
            if path.exists():
                return path.resolve()
            
            # 2. Relative to frontend directory
            frontend_dir = Path(__file__).parent.parent.parent.parent / "frontend"
            frontend_path = frontend_dir / image_path
            if frontend_path.exists():
                return frontend_path.resolve()
            
            # 3. Relative to project root
            project_root = Path(__file__).parent.parent.parent.parent.parent
            root_path = project_root / image_path
            if root_path.exists():
                return root_path.resolve()
        
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        
        return path.resolve()
    
    async def process_screenshot(self, image_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a screenshot and extract design tokens
        
        Args:
            image_path: Path to the screenshot image
            options: Processing options (e.g., ignore_watermark, token_types)
            
        Returns:
            Dictionary containing extracted design tokens
            
        Raises:
            ServiceError: If processing fails
        """
        try:
            # Resolve image path
            resolved_path = self._resolve_image_path(image_path)
            logger.info(f"Starting token extraction for image: {image_path}")
            logger.info(f"Image resolved to: {resolved_path}")
            
            # Validate image dimensions before processing
            from PIL import Image
            with Image.open(resolved_path) as img:
                width, height = img.size
                if width > 8000 or height > 8000:
                    raise ServiceError(f"Image dimensions too large: {width}x{height}. Maximum allowed is 8000x8000 pixels")
                logger.info(f"Image dimensions: {width}x{height}")
            
            # Read image data
            with open(resolved_path, 'rb') as f:
                image_data = f.read()
            
            image_size = os.path.getsize(resolved_path)
            logger.info(f"Image size: {image_size} bytes")
            logger.info(f"Using AI client: {self._preferred_client}")
            
            # Check for Mobbin watermark if needed
            if options and options.get('ignore_watermark', True):
                image_data = await self._remove_watermark(image_data)
            
            # Extract tokens based on requested types
            token_types = options.get('token_types', ['colors', 'typography', 'spacing', 'shadows', 'radii'])
            results = {}
            
            for token_type in token_types:
                start_time = time.time()
                logger.info(f"Starting {token_type} extraction")
                
                if token_type == 'colors':
                    results['colors'] = await self._extract_colors_with_ai(resolved_path, token_type)
                elif token_type == 'typography':
                    results['typography'] = await self._extract_typography_with_ai(resolved_path, token_type)
                elif token_type == 'spacing':
                    results['spacing'] = await self._extract_spacing_with_ai(resolved_path, token_type)
                elif token_type == 'shadows':
                    results['shadows'] = await self._extract_shadows_with_ai(resolved_path, token_type)
                elif token_type == 'radii':
                    results['radii'] = await self._extract_radii_with_ai(resolved_path, token_type)
                
                elapsed_time = time.time() - start_time
                logger.info(f"Completed {token_type} extraction in {elapsed_time:.2f}s")
            
            return {
                "success": True,
                "tokens": results,
                "metadata": {
                    "source": str(resolved_path),
                    "extracted_types": token_types
                }
            }
            
        except ServiceError as e:
            # Re-raise ServiceError with original message
            logger.error(f"Service error during screenshot processing: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to process screenshot: {str(e)}")
            raise ServiceError(f"Screenshot processing failed: {str(e)}")
    
    async def _remove_watermark(self, image_data: bytes) -> bytes:
        """Remove Mobbin watermark from image
        
        Args:
            image_data: Original image data
            
        Returns:
            Image data with watermark removed
        """
        try:
            from PIL import Image, ImageDraw
            import io
            
            # Convert bytes to PIL Image
            img = Image.open(io.BytesIO(image_data))
            width, height = img.size
            
            # Mobbin watermark is typically in the bottom-right corner
            # Create a mask to cover the watermark area (approximately 200x50 pixels)
            watermark_width = min(200, width // 4)
            watermark_height = min(50, height // 10)
            
            # Clone the area above the watermark to cover it
            if width > watermark_width and height > watermark_height:
                # Get the region just above the watermark
                source_region = img.crop((
                    width - watermark_width,
                    height - watermark_height * 2,
                    width,
                    height - watermark_height
                ))
                
                # Paste it over the watermark area
                img.paste(source_region, (width - watermark_width, height - watermark_height))
                
                # Optional: Blur the edges for a smoother blend
                draw = ImageDraw.Draw(img)
                # Add a subtle gradient to blend the edges
                for i in range(5):
                    alpha = int(255 * (1 - i / 5))
                    draw.rectangle([
                        width - watermark_width - i,
                        height - watermark_height - i,
                        width - watermark_width + i,
                        height - watermark_height + i
                    ], outline=(255, 255, 255, alpha))
            
            # Convert back to bytes
            output = io.BytesIO()
            img.save(output, format=img.format or 'PNG')
            return output.getvalue()
            
        except Exception as e:
            logger.warning(f"Failed to remove watermark: {str(e)}. Returning original image.")
            # Return original image if watermark removal fails
            return image_data
    
    async def _extract_colors_with_ai(self, image_path: Path, token_type: str) -> Dict[str, Any]:
        """Extract color tokens using AI vision
        
        Args:
            image_path: Path to the image file
            token_type: Type of token being extracted
            
        Returns:
            Dictionary of color tokens
        """
        if not self._preferred_client or not self.ai_clients:
            raise ServiceError("No AI client configured")
        
        logger.info(f"Using AI client: {self._preferred_client}")
        logger.info(f"Available clients: {list(self.ai_clients.keys())}")
        client = self._get_ai_client()
        
        # Structured prompt for color extraction
        prompt = """Analyze this UI screenshot and extract all color values used.
        
        Return a JSON object with the following structure:
        {
            "primary": ["#hex1", "#hex2"],  // Main brand colors
            "secondary": ["#hex3", "#hex4"],  // Supporting colors
            "semantic": {
                "success": "#hex",
                "error": "#hex",
                "warning": "#hex",
                "info": "#hex"
            },
            "neutrals": ["#hex5", "#hex6"],  // Grays, blacks, whites
            "gradients": [{
                "name": "gradient1",
                "colors": ["#hex7", "#hex8"],
                "direction": "to right"
            }]
        }
        
        Extract exact hex color values. Include transparency values if present (e.g., #RRGGBBAA).
        """
        
        try:
            logger.info(f"Calling analyze_image for {image_path}")
            result = await client.analyze_image(image_path, prompt, token_type)
            logger.info(f"AI result keys: {list(result.keys()) if result else 'None'}")
            # Parse JSON from response
            content = result.get("content", "{}")
            logger.info(f"Content length: {len(content)}")
            if content:
                logger.debug(f"Content preview: {content[:100]}...")
            parsed = json.loads(content)
            logger.info(f"Successfully parsed colors: {list(parsed.keys()) if isinstance(parsed, dict) else type(parsed)}")
            return parsed
        except ServiceError as e:
            # Re-raise with clear error message
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            logger.error(f"Invalid JSON content: {content[:500] if 'content' in locals() else 'No content'}")
            raise HTTPException(
                status_code=500,
                detail=f"Color extraction failed - Invalid JSON response: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to extract colors: {str(e)}", exc_info=True)
            logger.error(f"Exception type: {type(e).__name__}")
            
            # Extract original error from RetryError
            error_msg = str(e)
            if hasattr(e, '__cause__') and e.__cause__:
                error_msg = str(e.__cause__)
            elif 'RetryError' in str(type(e)) and hasattr(e, 'last_attempt'):
                # Try to get the original exception from tenacity RetryError
                try:
                    if hasattr(e.last_attempt, 'exception'):
                        original_error = e.last_attempt.exception()
                        if original_error:
                            error_msg = str(original_error)
                except:
                    pass
            
            # Pass through ServiceError messages
            if isinstance(e, ServiceError) or 'insufficient credits' in error_msg.lower():
                raise ServiceError(error_msg)
            
            raise HTTPException(
                status_code=500,
                detail=f"Color extraction failed: {error_msg}"
            )
    
    async def _extract_typography_with_ai(self, image_path: Path, token_type: str) -> Dict[str, Any]:
        """Extract typography tokens using AI vision
        
        Args:
            image_path: Path to the image file
            token_type: Type of token being extracted
            
        Returns:
            Dictionary of typography tokens
        """
        if not self._preferred_client or not self.ai_clients:
            logger.error("No AI client configured for extraction")
            raise HTTPException(status_code=500, detail="AI client not configured")
        
        logger.info("Starting typography extraction (this may take up to 60 seconds)")
        start_time = time.time()
        
        # Log progress at intervals
        async def log_progress():
            elapsed = 0
            while elapsed < 60:
                await asyncio.sleep(10)
                elapsed = time.time() - start_time
                if elapsed < 60:
                    logger.info(f"Typography extraction in progress... {elapsed:.1f}s elapsed")
        
        client = self._get_ai_client()
        
        # Structured prompt for typography extraction
        prompt = """Analyze this UI screenshot and extract all typography styles.
        
        Return a JSON object with:
        {
            "fonts": ["font-family names"],
            "sizes": ["16px", "24px", etc.],
            "weights": ["400", "600", "700"],
            "lineHeights": ["1.5", "1.2"],
            "styles": [{
                "name": "heading-1",
                "fontFamily": "Inter",
                "fontSize": "32px",
                "fontWeight": "700",
                "lineHeight": "1.2"
            }]
        }
        
        Extract exact values used in the UI.
        """
        
        # Run extraction with progress logging
        progress_task = asyncio.create_task(log_progress())
        try:
            result = await client.analyze_image(image_path, prompt, token_type)
            progress_task.cancel()
            
            elapsed = time.time() - start_time
            logger.info(f"Typography extraction completed in {elapsed:.1f}s")
            
            content = result.get("content", "{}")
            logger.info(f"AI response content length: {len(content)}")
            logger.info(f"AI response preview: {content[:200]}...")
            
            # Handle cases where AI returns JSON followed by explanatory text
            # Find the end of the JSON object
            if content.strip().startswith('{'):
                # Find matching closing brace
                brace_count = 0
                json_end = -1
                for i, char in enumerate(content):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > 0:
                    json_content = content[:json_end]
                    logger.info(f"Extracted JSON content: {json_content}")
                    return json.loads(json_content)
            
            # Fallback to original parsing
            return json.loads(content)
        except Exception as e:
            progress_task.cancel()
            error_msg = f"Failed to extract typography: {str(e)}"
            logger.error(error_msg, exc_info=True)
            logger.error(f"Full exception type: {type(e).__name__}")
            logger.error(f"Exception details: {repr(e)}")
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
        finally:
            progress_task.cancel()
    
    async def _extract_spacing_with_ai(self, image_path: Path, token_type: str) -> Dict[str, Any]:
        """Extract spacing tokens using AI vision
        
        Args:
            image_path: Path to the image file
            token_type: Type of token being extracted
            
        Returns:
            Dictionary of spacing tokens
        """
        if not self._preferred_client or not self.ai_clients:
            logger.error("No AI client configured for extraction")
            raise HTTPException(status_code=500, detail="AI client not configured")
        
        client = self._get_ai_client()
        
        # Structured prompt for spacing extraction
        prompt = """Analyze this UI screenshot and extract spacing values.
        
        Return a JSON object with:
        {
            "scale": ["4px", "8px", "16px", "24px", "32px"],
            "componentSpacing": {
                "button": {"padding": "12px 24px"},
                "card": {"padding": "16px", "gap": "12px"}
            }
        }
        """
        
        try:
            result = await client.analyze_image(image_path, prompt, token_type)
            content = result.get("content", "{}")
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to extract spacing: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Spacing extraction failed: {str(e)}"
            )
    
    async def _extract_shadows_with_ai(self, image_path: Path, token_type: str) -> Dict[str, Any]:
        """Extract shadow tokens using AI vision
        
        Args:
            image_path: Path to the image file
            token_type: Type of token being extracted
            
        Returns:
            Dictionary of shadow tokens
        """
        if not self._preferred_client or not self.ai_clients:
            logger.error("No AI client configured for extraction")
            raise HTTPException(status_code=500, detail="AI client not configured")
        
        client = self._get_ai_client()
        
        # Structured prompt for shadow extraction
        prompt = """Analyze this UI screenshot and extract shadow styles.
        
        Return a JSON object with:
        {
            "elevation": {
                "sm": [{"offsetX": "0", "offsetY": "1px", "blur": "3px", "color": "rgba(0,0,0,0.1)"}],
                "md": [{"offsetX": "0", "offsetY": "4px", "blur": "6px", "color": "rgba(0,0,0,0.1)"}]
            },
            "textShadows": []
        }
        """
        
        try:
            result = await client.analyze_image(image_path, prompt, token_type)
            content = result.get("content", "{}")
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to extract shadows: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Shadow extraction failed: {str(e)}"
            )
    
    async def _extract_radii_with_ai(self, image_path: Path, token_type: str) -> Dict[str, Any]:
        """Extract border radius tokens using AI vision
        
        Args:
            image_path: Path to the image file
            token_type: Type of token being extracted
            
        Returns:
            Dictionary of radius tokens
        """
        if not self._preferred_client or not self.ai_clients:
            logger.error("No AI client configured for extraction")
            raise HTTPException(status_code=500, detail="AI client not configured")
        
        client = self._get_ai_client()
        
        # Structured prompt for radius extraction
        prompt = """Analyze this UI screenshot and extract border radius values.
        
        Return a JSON object with:
        {
            "scale": ["0", "4px", "8px", "12px", "16px", "full"],
            "componentRadii": {
                "button": "8px",
                "card": "12px",
                "input": "4px"
            }
        }
        """
        
        try:
            result = await client.analyze_image(image_path, prompt, token_type)
            content = result.get("content", "{}")
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to extract radii: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Radius extraction failed: {str(e)}"
            )
    
    async def batch_process(self, image_paths: List[str], options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Process multiple screenshots in batch
        
        Args:
            image_paths: List of image paths
            options: Processing options
            
        Returns:
            List of extraction results
        """
        results = []
        for path in image_paths:
            try:
                result = await self.process_screenshot(path, options)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {path}: {str(e)}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "source": path
                })
        
        return results
    
    def validate_tokens(self, tokens: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate extracted tokens
        
        Args:
            tokens: Dictionary of extracted tokens
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate color tokens
        if 'colors' in tokens:
            color_errors = self._validate_color_tokens(tokens['colors'])
            errors.extend(color_errors)
        
        # Validate typography tokens
        if 'typography' in tokens:
            typo_errors = self._validate_typography_tokens(tokens['typography'])
            errors.extend(typo_errors)
        
        # Validate spacing tokens
        if 'spacing' in tokens:
            spacing_errors = self._validate_spacing_tokens(tokens['spacing'])
            errors.extend(spacing_errors)
        
        return len(errors) == 0, errors
    
    def _validate_color_tokens(self, colors: Dict[str, Any]) -> List[str]:
        """Validate color token structure"""
        errors = []
        
        # Validate hex color format
        def is_valid_hex(color: str) -> bool:
            if not isinstance(color, str):
                return False
            # Support both #RGB and #RRGGBB formats, with optional alpha
            import re
            return bool(re.match(r'^#([A-Fa-f0-9]{3}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$', color))
        
        # Check primary colors
        if 'primary' in colors:
            if not isinstance(colors['primary'], list):
                errors.append("Primary colors must be a list")
            else:
                for i, color in enumerate(colors['primary']):
                    if not is_valid_hex(color):
                        errors.append(f"Invalid hex color in primary[{i}]: {color}")
        
        # Check secondary colors
        if 'secondary' in colors:
            if not isinstance(colors['secondary'], list):
                errors.append("Secondary colors must be a list")
            else:
                for i, color in enumerate(colors['secondary']):
                    if not is_valid_hex(color):
                        errors.append(f"Invalid hex color in secondary[{i}]: {color}")
        
        # Check semantic colors
        if 'semantic' in colors:
            if not isinstance(colors['semantic'], dict):
                errors.append("Semantic colors must be a dictionary")
            else:
                for key, color in colors['semantic'].items():
                    if not is_valid_hex(color):
                        errors.append(f"Invalid hex color in semantic.{key}: {color}")
        
        # Check neutrals
        if 'neutrals' in colors:
            if not isinstance(colors['neutrals'], list):
                errors.append("Neutral colors must be a list")
            else:
                for i, color in enumerate(colors['neutrals']):
                    if not is_valid_hex(color):
                        errors.append(f"Invalid hex color in neutrals[{i}]: {color}")
        
        # Check gradients
        if 'gradients' in colors:
            if not isinstance(colors['gradients'], list):
                errors.append("Gradients must be a list")
            else:
                for i, gradient in enumerate(colors['gradients']):
                    if not isinstance(gradient, dict):
                        errors.append(f"Gradient[{i}] must be a dictionary")
                        continue
                    
                    if 'colors' not in gradient:
                        errors.append(f"Gradient[{i}] missing 'colors' field")
                    elif not isinstance(gradient['colors'], list):
                        errors.append(f"Gradient[{i}].colors must be a list")
                    else:
                        for j, color in enumerate(gradient['colors']):
                            if not is_valid_hex(color):
                                errors.append(f"Invalid hex color in gradient[{i}].colors[{j}]: {color}")
                    
                    if 'direction' in gradient and not isinstance(gradient['direction'], str):
                        errors.append(f"Gradient[{i}].direction must be a string")
        
        return errors
    
    def _validate_typography_tokens(self, typography: Dict[str, Any]) -> List[str]:
        """Validate typography token structure"""
        errors = []
        
        # Valid font weights
        valid_weights = ['100', '200', '300', '400', '500', '600', '700', '800', '900', 
                        'normal', 'bold', 'lighter', 'bolder']
        
        # Validate fonts
        if 'fonts' in typography:
            if not isinstance(typography['fonts'], list):
                errors.append("Fonts must be a list")
            elif len(typography['fonts']) == 0:
                errors.append("At least one font family must be specified")
        
        # Validate sizes
        if 'sizes' in typography:
            if not isinstance(typography['sizes'], list):
                errors.append("Font sizes must be a list")
            else:
                import re
                size_pattern = re.compile(r'^\d+(\.\d+)?(px|rem|em|pt)$')
                for i, size in enumerate(typography['sizes']):
                    if not isinstance(size, str) or not size_pattern.match(size):
                        errors.append(f"Invalid font size format at sizes[{i}]: {size}")
        
        # Validate weights
        if 'weights' in typography:
            if not isinstance(typography['weights'], list):
                errors.append("Font weights must be a list")
            else:
                for i, weight in enumerate(typography['weights']):
                    if str(weight) not in valid_weights:
                        errors.append(f"Invalid font weight at weights[{i}]: {weight}")
        
        # Validate line heights
        if 'lineHeights' in typography:
            if not isinstance(typography['lineHeights'], list):
                errors.append("Line heights must be a list")
            else:
                for i, height in enumerate(typography['lineHeights']):
                    try:
                        float(height)
                    except (ValueError, TypeError):
                        errors.append(f"Invalid line height at lineHeights[{i}]: {height}")
        
        # Validate styles
        if 'styles' in typography:
            if not isinstance(typography['styles'], list):
                errors.append("Typography styles must be a list")
            else:
                for i, style in enumerate(typography['styles']):
                    if not isinstance(style, dict):
                        errors.append(f"Style[{i}] must be a dictionary")
                        continue
                    
                    if 'name' not in style:
                        errors.append(f"Style[{i}] missing 'name' field")
                    
                    if 'fontSize' in style:
                        size_pattern = re.compile(r'^\d+(\.\d+)?(px|rem|em|pt)$')
                        if not size_pattern.match(str(style['fontSize'])):
                            errors.append(f"Invalid fontSize in style[{i}]: {style['fontSize']}")
                    
                    if 'fontWeight' in style and str(style['fontWeight']) not in valid_weights:
                        errors.append(f"Invalid fontWeight in style[{i}]: {style['fontWeight']}")
                    
                    if 'lineHeight' in style:
                        try:
                            float(style['lineHeight'])
                        except (ValueError, TypeError):
                            errors.append(f"Invalid lineHeight in style[{i}]: {style['lineHeight']}")
        
        return errors
    
    def _validate_spacing_tokens(self, spacing: Dict[str, Any]) -> List[str]:
        """Validate spacing token structure"""
        errors = []
        
        import re
        # Pattern for valid spacing values (e.g., "16px", "1rem", "2em")
        spacing_pattern = re.compile(r'^\d+(\.\d+)?(px|rem|em|%)$')
        
        # Pattern for compound spacing (e.g., "12px 24px")
        compound_pattern = re.compile(r'^(\d+(\.\d+)?(px|rem|em|%)\s*){1,4}$')
        
        # Validate scale
        if 'scale' in spacing:
            if not isinstance(spacing['scale'], list):
                errors.append("Spacing scale must be a list")
            else:
                for i, value in enumerate(spacing['scale']):
                    if not isinstance(value, str) or not spacing_pattern.match(value):
                        errors.append(f"Invalid spacing value in scale[{i}]: {value}")
                
                # Check if scale values are in ascending order
                try:
                    numeric_values = []
                    for value in spacing['scale']:
                        match = re.match(r'^(\d+(\.\d+)?)', value)
                        if match:
                            numeric_values.append(float(match.group(1)))
                    
                    if numeric_values != sorted(numeric_values):
                        errors.append("Spacing scale values should be in ascending order")
                except:
                    pass  # Skip ordering check if parsing fails
        
        # Validate component spacing
        if 'componentSpacing' in spacing:
            if not isinstance(spacing['componentSpacing'], dict):
                errors.append("Component spacing must be a dictionary")
            else:
                for component, values in spacing['componentSpacing'].items():
                    if not isinstance(values, dict):
                        errors.append(f"Component spacing for '{component}' must be a dictionary")
                        continue
                    
                    for prop, value in values.items():
                        if not isinstance(value, str):
                            errors.append(f"Spacing value for {component}.{prop} must be a string")
                        elif not (spacing_pattern.match(value) or compound_pattern.match(value)):
                            errors.append(f"Invalid spacing value for {component}.{prop}: {value}")
        
        return errors