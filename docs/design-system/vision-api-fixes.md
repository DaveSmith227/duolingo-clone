# Design System Vision API Fixes and Learnings

This document captures the key fixes and learnings from implementing Claude Vision API for design token extraction in the Duolingo clone project.

## Overview

When implementing the design token extraction system, we encountered several issues that prevented the Claude Vision API from working correctly. This document outlines the problems encountered and their solutions, which should be incorporated into the main design system extraction process.

## Key Issues and Fixes

### 1. Environment Variable Loading

**Issue**: The API key was not being loaded from the `.env` file.

**Fix**: Add explicit environment variable loading using `python-dotenv`:

```python
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
```

This should be added at the module level before accessing any environment variables.

### 2. Dynamic Media Type Detection

**Issue**: The API was hardcoded to use `image/png` media type, but many screenshots were JPEG format, causing "Image does not match the provided media type" errors.

**Fix**: Implement dynamic media type detection based on file extension:

```python
# Detect media type from file extension
file_ext = full_path.suffix.lower()
media_type = "image/jpeg" if file_ext in ['.jpg', '.jpeg'] else "image/png"
```

### 3. Path Resolution

**Issue**: Relative paths were not being resolved correctly when the API was called from different contexts.

**Fix**: Implement proper path resolution relative to the frontend directory:

```python
full_path = Path(image_path)
if not full_path.is_absolute():
    # Make path relative to the frontend directory where npm script runs
    frontend_dir = Path(__file__).parent.parent / "frontend"
    full_path = frontend_dir / image_path
```

### 4. Error Handling Without Fallbacks

**Issue**: The original implementation was falling back to default tokens when API calls failed, masking the actual problems.

**Fix**: Remove fallback behavior and let errors propagate:

```python
except Exception as e:
    logger.error(f"Claude API error: {str(e)}")
    raise  # Let error propagate instead of returning defaults
```

### 5. Image Size Constraints

**Issue**: Claude Vision API has a maximum image dimension limit of 8000 pixels. The full landing page screenshot (2780x16384) exceeded this limit.

**Fix**: 
- Document the size constraint clearly
- Use smaller, component-specific screenshots for token extraction
- Consider implementing image resizing for oversized screenshots

### 6. Comprehensive Logging

**Issue**: Debugging was difficult without detailed logging throughout the pipeline.

**Fix**: Add comprehensive logging at each step:

```python
logger.info(f"Analyzing image for token type: {token_type}")
logger.info(f"API Key available: {bool(ANTHROPIC_API_KEY)}")
logger.info(f"API Key prefix: {ANTHROPIC_API_KEY[:20] if ANTHROPIC_API_KEY else 'No key'}")
logger.info(f"Reading image from: {full_path}")
logger.info(f"Image encoded, size: {len(image_base64)} chars, media type: {media_type}")
logger.info("Preparing to call Claude API")
logger.info(f"API response status: {response.status_code}")
```

## Implementation Recommendations

### 1. Update Backend Service

The existing `backend/app/services/design_system_service.py` should incorporate these fixes:

```python
# In the constructor or initialization
from dotenv import load_dotenv
load_dotenv()

# In the image analysis method
def analyze_image(self, image_path: str, token_type: str):
    # Implement dynamic media type detection
    # Add comprehensive logging
    # Remove any fallback to default tokens
    # Handle path resolution properly
```

### 2. Update AI Vision Client

The `backend/app/services/ai_vision_client.py` should:

- Validate image dimensions before sending to API
- Use dynamic media type detection
- Include proper error messages for size constraints

### 3. Frontend CLI Integration

The `frontend/src/lib/design-system/cli/extract.ts` should:

- Provide clear error messages when API fails
- Not proceed with default tokens if extraction fails
- Log the actual API responses for debugging

### 4. Environment Configuration

Add clear documentation about required environment variables:

```bash
# .env file in backend directory
ANTHROPIC_API_KEY="sk-ant-api03-..."  # Required for design token extraction
```

## Testing Recommendations

1. **Test with various image formats**: Ensure both JPEG and PNG files work correctly
2. **Test with oversized images**: Verify proper error handling for images exceeding 8000px
3. **Test without API key**: Ensure clear error message when API key is missing
4. **Test with invalid API key**: Verify proper error handling and messaging

## API Response Format

The Claude Vision API successfully extracts tokens in the following format:

```json
{
  "radii": {
    "scale": [
      {"value": "8px", "name": "sm"},
      {"value": "16px", "name": "md"},
      {"value": "32px", "name": "lg"},
      {"value": "9999px", "name": "full"}
    ],
    "componentRadii": {
      "button": "16px",
      "card": "20px",
      "dropdown": "12px"
    }
  }
}
```

## Conclusion

These fixes ensure that the design token extraction system uses actual AI vision analysis rather than falling back to defaults. The key principles are:

1. **Fail explicitly**: Don't hide API failures behind default values
2. **Log comprehensively**: Make debugging easier with detailed logs
3. **Handle formats dynamically**: Support both JPEG and PNG images
4. **Respect API limits**: Document and handle size constraints
5. **Configure properly**: Ensure environment variables are loaded correctly

By incorporating these fixes into the main design system extraction process defined in `/product-requirements/tasks/tasks-prd-006-design-system-extraction.md`, the system will be more robust and reliable.