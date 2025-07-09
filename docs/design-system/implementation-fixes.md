# Design System Implementation Fixes

This document provides step-by-step instructions for fixing the design system bugs.

## Step 1: Fix Backend Dependencies

### 1.1 Add Missing Python Package
```bash
cd backend
echo "qrcode==7.4.2" >> requirements.txt
pip install -r requirements.txt
```

### 1.2 Fix MFASettings Import
Check if `MFASettings` exists in `/backend/app/models/auth.py`. If not, either:
- Create the model
- Or comment out the import in `/backend/app/services/mfa_service.py`

## Step 2: Add Environment Variable Loading

### 2.1 Update Main Application
Edit `/backend/app/main.py`:
```python
# Add at the top of the file
from dotenv import load_dotenv

# Add before create_app()
load_dotenv()
```

### 2.2 Update AI Vision Client
Edit `/backend/app/services/ai_vision_client.py`:
```python
# Add at the top
import os
from dotenv import load_dotenv
load_dotenv()
```

## Step 3: Fix Design System Service

### 3.1 Fix Object Reference Bug
In `/backend/app/services/design_system_service.py`, replace all occurrences of:
```python
if not self.ai_client:
```
With:
```python
if not self._preferred_client or not self.ai_clients:
```

This affects lines: 209, 229, 247, 265

### 3.2 Fix Error Handling
Replace all return statements with empty defaults with proper exceptions:

```python
# Instead of:
return ExtractedColors(primary=[], secondary=[], semantic={}, neutrals=[], gradients=[])

# Use:
raise HTTPException(status_code=500, detail=f"Color extraction failed: {str(e)}")
```

### 3.3 Add Path Resolution
Add this method to the DesignSystemService class:
```python
def _resolve_image_path(self, image_path: str) -> Path:
    """Resolve image path relative to frontend if needed"""
    path = Path(image_path)
    if not path.is_absolute():
        # Assume relative to frontend directory
        frontend_dir = Path(__file__).parent.parent.parent.parent / "frontend"
        path = frontend_dir / image_path
    
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    
    return path
```

## Step 4: Fix AI Vision Client Media Type

### 4.1 Update ClaudeVisionClient
In `/backend/app/services/ai_vision_client.py`, modify the `analyze_image` method:

```python
# Add import
import mimetypes

# In analyze_image method (around line 140)
# Replace:
"media_type": "image/png",

# With:
mime_type, _ = mimetypes.guess_type(str(image_path))
media_type = mime_type or "image/png"
# Then use:
"media_type": media_type,
```

### 4.2 Update OpenAIVisionClient
Apply the same fix to the OpenAI client (around line 253).

## Step 5: Fix Frontend Integration

### 5.1 Fix Mock Authentication
In `/frontend/src/lib/design-system/extractor/tokenizer.ts`, update the `getAuthToken` method:

```typescript
private async getAuthToken(): Promise<string> {
  // For now, just return empty string if no auth
  // TODO: Integrate with Supabase
  return '';
}
```

### 5.2 Fix API Endpoint Configuration
In `/frontend/src/lib/design-system/cli/extract.ts`:

```typescript
// Add at the top
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Update line 73
const apiEndpoint = options.apiEndpoint || `${API_URL}/api/design-system`;
```

## Step 6: Test the Fixes

### 6.1 Start Backend
```bash
cd backend
python -m uvicorn app.main:app --reload
```

### 6.2 Test Design Token Extraction
```bash
cd frontend
npm run design:extract ../design-reference/landing-page/hero-section.png
```

## Quick Fix Script

Create `/backend/scripts/fix_design_system.py`:

```python
#!/usr/bin/env python3
import os
import re
from pathlib import Path

def fix_ai_client_references():
    """Fix self.ai_client to self.ai_clients references"""
    service_file = Path("app/services/design_system_service.py")
    content = service_file.read_text()
    
    # Replace self.ai_client with proper check
    content = re.sub(
        r'if not self\.ai_client:',
        'if not self._preferred_client or not self.ai_clients:',
        content
    )
    
    service_file.write_text(content)
    print("✓ Fixed ai_client references")

def add_dotenv_to_main():
    """Add dotenv loading to main.py"""
    main_file = Path("app/main.py")
    content = main_file.read_text()
    
    if 'from dotenv import load_dotenv' not in content:
        lines = content.split('\n')
        # Add import after other imports
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('from') or line.startswith('import'):
                import_index = i
        
        lines.insert(import_index + 1, 'from dotenv import load_dotenv')
        
        # Add load_dotenv() before create_app
        for i, line in enumerate(lines):
            if 'app = create_app()' in line:
                lines.insert(i, 'load_dotenv()')
                break
        
        main_file.write_text('\n'.join(lines))
        print("✓ Added dotenv loading to main.py")
    else:
        print("✓ dotenv already configured in main.py")

def main():
    os.chdir(Path(__file__).parent.parent)
    
    fix_ai_client_references()
    add_dotenv_to_main()
    
    print("\nNext steps:")
    print("1. Add 'qrcode==7.4.2' to requirements.txt")
    print("2. Run: pip install -r requirements.txt")
    print("3. Start the backend: uvicorn app.main:app --reload")
    print("4. Test token extraction from frontend")

if __name__ == "__main__":
    main()
```

Run the script:
```bash
cd backend
python scripts/fix_design_system.py
```

## Verification Checklist

- [ ] Backend starts without import errors
- [ ] `/health` endpoint returns 200 OK
- [ ] `/api/design-system/health` endpoint works
- [ ] Environment variables are loaded (check logs)
- [ ] Token extraction doesn't fall back to defaults
- [ ] Proper error messages when extraction fails
- [ ] Both JPEG and PNG images work
- [ ] Path resolution works for relative paths