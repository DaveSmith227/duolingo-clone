#!/bin/bash

# Design System Comprehensive Fix Script
# This script applies all fixes for the design system issues

set -e  # Exit on error

echo "🔧 Design System Fix Script"
echo "=========================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if we're in the project root
if [ ! -f "package.json" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    print_error "This script must be run from the project root directory"
    exit 1
fi

echo "Phase 1: Backend Dependencies"
echo "-----------------------------"

# Check if backend venv exists
if [ ! -d "backend/venv" ]; then
    print_warning "Backend virtual environment not found. Creating..."
    cd backend
    python -m venv venv
    source venv/bin/activate || . venv/Scripts/activate
    pip install -r requirements.txt
    cd ..
    print_status "Backend virtual environment created"
else
    print_status "Backend virtual environment exists"
fi

echo ""
echo "Phase 2: Environment Variables"
echo "------------------------------"

# Check for .env files
if [ ! -f "backend/.env" ]; then
    print_warning "Backend .env file not found. Creating from example..."
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        print_status "Created backend/.env from example"
        print_warning "Please update backend/.env with your API keys"
    else
        cat > backend/.env << EOF
# AI Vision API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Database
DATABASE_URL=sqlite:///./app.db

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Supabase
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
EOF
        print_status "Created backend/.env template"
        print_warning "Please update backend/.env with your actual API keys"
    fi
else
    print_status "Backend .env file exists"
fi

if [ ! -f "frontend/.env.local" ]; then
    print_warning "Frontend .env.local file not found. Creating..."
    cat > frontend/.env.local << EOF
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url_here
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key_here
EOF
    print_status "Created frontend/.env.local template"
    print_warning "Please update frontend/.env.local with your actual configuration"
else
    print_status "Frontend .env.local file exists"
fi

echo ""
echo "Phase 3: Verifying Python Dependencies"
echo "--------------------------------------"

cd backend
source venv/bin/activate || . venv/Scripts/activate 2>/dev/null || true

# Check for missing dependencies
missing_deps=""
python -c "import qrcode" 2>/dev/null || missing_deps="$missing_deps qrcode"
python -c "import dotenv" 2>/dev/null || missing_deps="$missing_deps python-dotenv"
python -c "import PIL" 2>/dev/null || missing_deps="$missing_deps Pillow"

if [ -n "$missing_deps" ]; then
    print_warning "Installing missing dependencies: $missing_deps"
    pip install qrcode==7.4.2 python-dotenv Pillow
    print_status "Dependencies installed"
else
    print_status "All Python dependencies are installed"
fi

cd ..

echo ""
echo "Phase 4: Frontend Dependencies"
echo "------------------------------"

cd frontend
if [ ! -d "node_modules" ]; then
    print_warning "Frontend dependencies not installed. Installing..."
    npm install
    print_status "Frontend dependencies installed"
else
    print_status "Frontend dependencies exist"
fi

cd ..

echo ""
echo "Phase 5: Testing Backend Startup"
echo "--------------------------------"

# Test if backend can start
cd backend
python -c "
import os
import sys
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check for API keys
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if not anthropic_key and not openai_key:
        print('❌ No AI API keys configured. Please add at least one API key to backend/.env')
        sys.exit(1)
    
    # Try importing main modules
    from app.main import app
    from app.services.design_system_service import DesignSystemService
    from app.services.ai_vision_client import AIVisionClient
    
    print('✓ Backend modules loaded successfully')
    
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    print_status "Backend modules load successfully"
else
    print_error "Backend startup test failed"
    print_warning "Please check the error messages above"
fi

cd ..

echo ""
echo "Phase 6: Creating Fix Verification Script"
echo "-----------------------------------------"

cat > verify-fixes.py << 'EOF'
#!/usr/bin/env python
"""Verify that all design system fixes have been applied correctly."""

import os
import sys
import subprocess
from pathlib import Path

def check_file_contains(filepath, search_string):
    """Check if a file contains a specific string."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            return search_string in content
    except:
        return False

def verify_fixes():
    """Verify all fixes have been applied."""
    issues = []
    
    # Check backend fixes
    print("Checking backend fixes...")
    
    # 1. Check load_dotenv in main.py
    if not check_file_contains('backend/app/main.py', 'load_dotenv()'):
        issues.append("backend/app/main.py missing load_dotenv() call")
    
    # 2. Check MFA import fix
    if check_file_contains('backend/app/services/mfa_service.py', 'from app.models.auth import MFASettings'):
        issues.append("backend/app/services/mfa_service.py has incorrect MFA import")
    
    # 3. Check image size validation
    if not check_file_contains('backend/app/services/ai_vision_client.py', 'if width > 8000 or height > 8000'):
        issues.append("backend/app/services/ai_vision_client.py missing image size validation")
    
    # 4. Check timeout handling
    if not check_file_contains('backend/app/services/ai_vision_client.py', 'self.typography_timeout'):
        issues.append("backend/app/services/ai_vision_client.py missing typography timeout")
    
    # Check frontend fixes
    print("\nChecking frontend fixes...")
    
    # 5. Check auth integration
    if not check_file_contains('frontend/src/lib/design-system/extractor/tokenizer.ts', 'import(@\'/lib/supabase\')'):
        issues.append("frontend tokenizer.ts missing Supabase auth integration")
    
    # 6. Check timeout handling
    if not check_file_contains('frontend/src/lib/design-system/extractor/tokenizer.ts', 'AbortController'):
        issues.append("frontend tokenizer.ts missing timeout handling")
    
    # 7. Check API retry logic
    if not check_file_contains('frontend/src/lib/design-system/cli/extract.ts', 'withRetry'):
        issues.append("frontend extract.ts missing retry logic")
    
    # Report results
    if issues:
        print(f"\n❌ Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\n✅ All fixes verified successfully!")
        return True

if __name__ == "__main__":
    success = verify_fixes()
    sys.exit(0 if success else 1)
EOF

chmod +x verify-fixes.py
print_status "Created verification script"

echo ""
echo "Phase 7: Running Verification"
echo "-----------------------------"

python verify-fixes.py

echo ""
echo "Phase 8: Quick Test Commands"
echo "----------------------------"

print_status "Backend startup test:"
echo "  cd backend && uvicorn app.main:app --reload"
echo ""

print_status "Frontend startup test:"
echo "  cd frontend && npm run dev"
echo ""

print_status "Design system extraction test:"
echo "  cd frontend && npm run design:extract <screenshot-path>"
echo ""

echo "======================================"
echo "Fix script completed!"
echo ""
echo "Next steps:"
echo "1. Update .env files with your API keys"
echo "2. Start the backend: cd backend && uvicorn app.main:app --reload"
echo "3. Start the frontend: cd frontend && npm run dev"
echo "4. Test token extraction with a screenshot"
echo ""
print_warning "Remember to check the error messages above if any fixes failed"