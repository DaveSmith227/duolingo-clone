"""API endpoints for Design System operations

Provides REST API endpoints for extracting design tokens from screenshots
and managing design system data.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
import os
import tempfile
import logging
from pathlib import Path

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.schemas.design_system import (
    TokenExtractionRequest,
    TokenExtractionResponse,
    BatchExtractionRequest,
    BatchExtractionResponse,
    TokenValidationRequest,
    TokenValidationResponse,
    DesignTokens
)
from app.schemas.users import User
from app.services.design_system_service import DesignSystemService
from app.services.ai_vision_client import configure_ai_clients

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/design-system", tags=["design-system"])

# Global service instance
_design_service: Optional[DesignSystemService] = None


async def get_design_service() -> DesignSystemService:
    """Get or create the design system service with AI clients"""
    global _design_service
    
    if _design_service is None:
        settings = get_settings()
        ai_clients = await configure_ai_clients(settings)
        _design_service = DesignSystemService(ai_clients=ai_clients)
    
    return _design_service


@router.post("/extract", response_model=TokenExtractionResponse)
async def extract_tokens(
    request: TokenExtractionRequest,
    current_user: User = Depends(get_current_user),
    service: DesignSystemService = Depends(get_design_service)
) -> TokenExtractionResponse:
    """Extract design tokens from a screenshot
    
    Requires authentication. Processes the image at the given path and extracts
    the requested token types using AI vision.
    
    Args:
        request: Token extraction request with image path and options
        current_user: Authenticated user
        service: Design system service instance
        
    Returns:
        TokenExtractionResponse with extracted tokens or errors
    """
    try:
        logger.info(f"User {current_user.email} extracting tokens from {request.image_path}")
        
        # Validate image path
        image_path = Path(request.image_path)
        if not image_path.exists():
            raise HTTPException(status_code=404, detail=f"Image not found: {request.image_path}")
        
        # Process screenshot
        options = {
            "ignore_watermark": request.ignore_watermark,
            "token_types": [t.value for t in request.token_types],
            "ai_provider": request.ai_provider
        }
        
        result = await service.process_screenshot(str(image_path), options)
        
        if result["success"]:
            # Convert to DesignTokens schema
            tokens = DesignTokens(**result["tokens"])
            return TokenExtractionResponse(
                success=True,
                tokens=tokens,
                metadata=result["metadata"],
                errors=[]
            )
        else:
            return TokenExtractionResponse(
                success=False,
                tokens=None,
                metadata={},
                errors=[result.get("error", "Unknown error")]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract tokens: {str(e)}")
        return TokenExtractionResponse(
            success=False,
            tokens=None,
            metadata={},
            errors=[str(e)]
        )


@router.post("/extract-upload", response_model=TokenExtractionResponse)
async def extract_tokens_from_upload(
    file: UploadFile = File(...),
    token_types: str = "colors,typography,spacing,shadows,radii",
    ignore_watermark: bool = True,
    ai_provider: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: DesignSystemService = Depends(get_design_service)
) -> TokenExtractionResponse:
    """Extract design tokens from an uploaded screenshot
    
    Requires authentication. Accepts an image file upload and extracts
    the requested token types.
    
    Args:
        file: Uploaded image file
        token_types: Comma-separated list of token types to extract
        ignore_watermark: Whether to ignore Mobbin watermarks
        ai_provider: Preferred AI provider (claude/openai)
        current_user: Authenticated user
        service: Design system service instance
        
    Returns:
        TokenExtractionResponse with extracted tokens or errors
    """
    try:
        logger.info(f"User {current_user.email} uploading file for token extraction")
        
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file.flush()
            
            # Create extraction request
            from app.schemas.design_system import TokenType
            token_type_list = [TokenType(t.strip()) for t in token_types.split(",")]
            
            request = TokenExtractionRequest(
                image_path=tmp_file.name,
                token_types=token_type_list,
                ignore_watermark=ignore_watermark,
                ai_provider=ai_provider
            )
            
            # Extract tokens
            response = await extract_tokens(request, current_user, service)
            
            # Clean up temp file
            os.unlink(tmp_file.name)
            
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process uploaded file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-extract", response_model=BatchExtractionResponse)
async def batch_extract_tokens(
    request: BatchExtractionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: DesignSystemService = Depends(get_design_service)
) -> BatchExtractionResponse:
    """Extract design tokens from multiple screenshots
    
    Requires authentication. Processes multiple images in batch.
    
    Args:
        request: Batch extraction request with image paths and options
        background_tasks: FastAPI background tasks
        current_user: Authenticated user
        service: Design system service instance
        
    Returns:
        BatchExtractionResponse with results for each image
    """
    try:
        logger.info(f"User {current_user.email} batch extracting from {len(request.image_paths)} images")
        
        results = []
        success_count = 0
        
        for image_path in request.image_paths:
            single_request = TokenExtractionRequest(
                image_path=image_path,
                token_types=request.token_types,
                ignore_watermark=request.ignore_watermark,
                ai_provider=request.ai_provider
            )
            
            result = await extract_tokens(single_request, current_user, service)
            results.append(result)
            
            if result.success:
                success_count += 1
        
        summary = {
            "total": len(request.image_paths),
            "successful": success_count,
            "failed": len(request.image_paths) - success_count
        }
        
        return BatchExtractionResponse(
            results=results,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Batch extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=TokenValidationResponse)
async def validate_tokens(
    request: TokenValidationRequest,
    current_user: User = Depends(get_current_user),
    service: DesignSystemService = Depends(get_design_service)
) -> TokenValidationResponse:
    """Validate design tokens
    
    Requires authentication. Validates the structure and values of design tokens.
    
    Args:
        request: Token validation request
        current_user: Authenticated user
        service: Design system service instance
        
    Returns:
        TokenValidationResponse with validation results
    """
    try:
        logger.info(f"User {current_user.email} validating design tokens")
        
        # Convert tokens to dict for validation
        tokens_dict = request.tokens.model_dump(exclude_none=True)
        
        # Validate tokens
        is_valid, errors = service.validate_tokens(tokens_dict)
        
        # Additional strict validation if requested
        warnings = []
        if request.strict_mode:
            # Check for empty arrays
            if tokens_dict.get("colors", {}).get("primary", []) == []:
                warnings.append("No primary colors defined")
            
            if tokens_dict.get("typography", {}).get("fonts", []) == []:
                warnings.append("No fonts defined")
            
            if tokens_dict.get("spacing", {}).get("scale", []) == []:
                warnings.append("No spacing scale defined")
        
        return TokenValidationResponse(
            valid=is_valid and (not request.strict_mode or len(warnings) == 0),
            errors=errors,
            warnings=warnings
        )
        
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        return TokenValidationResponse(
            valid=False,
            errors=[str(e)],
            warnings=[]
        )


@router.get("/health")
async def health_check(
    service: DesignSystemService = Depends(get_design_service)
) -> dict:
    """Health check endpoint for design system service
    
    Returns the status of the design system service and available AI clients.
    """
    try:
        ai_clients = list(service.ai_clients.keys()) if service.ai_clients else []
        
        return {
            "status": "healthy",
            "service": "design-system",
            "ai_clients": ai_clients,
            "ai_configured": len(ai_clients) > 0
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "design-system",
            "error": str(e)
        }


@router.get("/supported-tokens")
async def get_supported_tokens() -> dict:
    """Get list of supported token types
    
    Returns the token types that can be extracted and their descriptions.
    """
    from app.schemas.design_system import TokenType
    
    return {
        "token_types": [
            {
                "type": TokenType.COLORS,
                "description": "Color palettes including primary, secondary, semantic, and gradients"
            },
            {
                "type": TokenType.TYPOGRAPHY,
                "description": "Font families, sizes, weights, and complete text styles"
            },
            {
                "type": TokenType.SPACING,
                "description": "Spacing scale and component-specific padding/margin values"
            },
            {
                "type": TokenType.SHADOWS,
                "description": "Box shadows and text shadows with elevation levels"
            },
            {
                "type": TokenType.RADII,
                "description": "Border radius values and component-specific rounded corners"
            },
            {
                "type": TokenType.COMPONENTS,
                "description": "Component-specific design tokens including states and variations"
            }
        ]
    }