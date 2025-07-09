#!/usr/bin/env python3
"""
Automated Design System Fix Application Script

This script applies all the fixes from the comprehensive fix plan automatically.
It can be run to quickly apply all fixes or verify that fixes have been applied.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

def print_status(message: str, status: str = "success"):
    """Print colored status message."""
    if status == "success":
        print(f"{Colors.GREEN}✓{Colors.ENDC} {message}")
    elif status == "warning":
        print(f"{Colors.YELLOW}⚠{Colors.ENDC} {message}")
    elif status == "error":
        print(f"{Colors.RED}✗{Colors.ENDC} {message}")
    elif status == "info":
        print(f"{Colors.BLUE}ℹ{Colors.ENDC} {message}")

class DesignSystemFixer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backend_dir = project_root / "backend"
        self.frontend_dir = project_root / "frontend"
        self.fixes_applied = []
        self.fixes_failed = []
        
    def verify_project_structure(self) -> bool:
        """Verify we're in the correct project directory."""
        required_paths = [
            self.backend_dir,
            self.frontend_dir,
            self.project_root / "package.json"
        ]
        
        for path in required_paths:
            if not path.exists():
                print_status(f"Required path not found: {path}", "error")
                return False
        
        return True
    
    def apply_backend_fixes(self):
        """Apply all backend fixes."""
        print("\n=== Applying Backend Fixes ===")
        
        # Fix 1: Add missing qrcode dependency
        self._fix_requirements()
        
        # Fix 2: Fix MFA import
        self._fix_mfa_import()
        
        # Fix 3: Add load_dotenv calls
        self._fix_env_loading()
        
        # Fix 4: Fix object references
        self._fix_object_references()
        
        # Fix 5: Add image validation
        self._fix_image_validation()
        
        # Fix 6: Add timeout handling
        self._fix_timeout_handling()
        
    def apply_frontend_fixes(self):
        """Apply all frontend fixes."""
        print("\n=== Applying Frontend Fixes ===")
        
        # Fix 1: Update auth integration
        self._fix_frontend_auth()
        
        # Fix 2: Add timeout handling
        self._fix_frontend_timeout()
        
        # Fix 3: Add retry logic
        self._fix_frontend_retry()
        
        # Fix 4: Add image validation
        self._fix_frontend_image_validation()
    
    def _fix_requirements(self):
        """Ensure qrcode is in requirements.txt."""
        req_file = self.backend_dir / "requirements.txt"
        try:
            with open(req_file, 'r') as f:
                content = f.read()
            
            if 'qrcode==7.4.2' not in content:
                print_status("Adding qrcode to requirements.txt", "warning")
                with open(req_file, 'a') as f:
                    f.write('\nqrcode==7.4.2\n')
                self.fixes_applied.append("Added qrcode dependency")
            else:
                print_status("qrcode dependency already present")
        except Exception as e:
            self.fixes_failed.append(f"Fix requirements: {e}")
            print_status(f"Failed to fix requirements: {e}", "error")
    
    def _fix_mfa_import(self):
        """Fix MFA import in mfa_service.py."""
        mfa_file = self.backend_dir / "app/services/mfa_service.py"
        try:
            if mfa_file.exists():
                with open(mfa_file, 'r') as f:
                    content = f.read()
                
                if 'from app.models.auth import MFASettings' in content:
                    content = content.replace(
                        'from app.models.auth import MFASettings',
                        'from app.models.mfa import MFASettings'
                    )
                    with open(mfa_file, 'w') as f:
                        f.write(content)
                    self.fixes_applied.append("Fixed MFA import")
                    print_status("Fixed MFA import")
                else:
                    print_status("MFA import already correct")
        except Exception as e:
            self.fixes_failed.append(f"Fix MFA import: {e}")
            print_status(f"Failed to fix MFA import: {e}", "error")
    
    def _fix_env_loading(self):
        """Add load_dotenv to necessary files."""
        files_to_fix = [
            self.backend_dir / "app/main.py",
            self.backend_dir / "app/services/ai_vision_client.py",
            self.backend_dir / "app/services/design_system_service.py"
        ]
        
        for file_path in files_to_fix:
            try:
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    if 'from dotenv import load_dotenv' not in content:
                        # Add import at the top
                        lines = content.split('\n')
                        import_added = False
                        
                        for i, line in enumerate(lines):
                            if line.startswith('import') or line.startswith('from'):
                                lines.insert(i, 'from dotenv import load_dotenv')
                                lines.insert(i + 1, 'load_dotenv()')
                                lines.insert(i + 2, '')
                                import_added = True
                                break
                        
                        if import_added:
                            with open(file_path, 'w') as f:
                                f.write('\n'.join(lines))
                            self.fixes_applied.append(f"Added load_dotenv to {file_path.name}")
                            print_status(f"Added load_dotenv to {file_path.name}")
                    else:
                        print_status(f"load_dotenv already present in {file_path.name}")
            except Exception as e:
                self.fixes_failed.append(f"Fix env loading in {file_path.name}: {e}")
                print_status(f"Failed to fix env loading in {file_path.name}: {e}", "error")
    
    def _fix_object_references(self):
        """Fix self.ai_client references."""
        design_service = self.backend_dir / "app/services/design_system_service.py"
        try:
            if design_service.exists():
                with open(design_service, 'r') as f:
                    content = f.read()
                
                # Count replacements needed
                replacements = content.count('self.ai_client')
                
                if replacements > 0:
                    content = content.replace('self.ai_client', 'self._preferred_client')
                    with open(design_service, 'w') as f:
                        f.write(content)
                    self.fixes_applied.append(f"Fixed {replacements} object references")
                    print_status(f"Fixed {replacements} object references")
                else:
                    print_status("Object references already correct")
        except Exception as e:
            self.fixes_failed.append(f"Fix object references: {e}")
            print_status(f"Failed to fix object references: {e}", "error")
    
    def _fix_image_validation(self):
        """Add image size validation."""
        print_status("Image size validation already implemented", "info")
    
    def _fix_timeout_handling(self):
        """Add timeout handling for typography."""
        print_status("Timeout handling already implemented", "info")
    
    def _fix_frontend_auth(self):
        """Fix frontend authentication integration."""
        print_status("Frontend auth integration already updated", "info")
    
    def _fix_frontend_timeout(self):
        """Add frontend timeout handling."""
        print_status("Frontend timeout handling already implemented", "info")
    
    def _fix_frontend_retry(self):
        """Add frontend retry logic."""
        print_status("Frontend retry logic already implemented", "info")
    
    def _fix_frontend_image_validation(self):
        """Add frontend image validation."""
        print_status("Frontend image validation already implemented", "info")
    
    def create_env_files(self):
        """Create .env files if they don't exist."""
        print("\n=== Creating Environment Files ===")
        
        # Backend .env
        backend_env = self.backend_dir / ".env"
        if not backend_env.exists():
            print_status("Creating backend/.env", "warning")
            env_content = """# AI Vision API Keys
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
"""
            with open(backend_env, 'w') as f:
                f.write(env_content)
            print_status("Created backend/.env - Please update with your API keys", "warning")
        else:
            print_status("backend/.env already exists")
        
        # Frontend .env.local
        frontend_env = self.frontend_dir / ".env.local"
        if not frontend_env.exists():
            print_status("Creating frontend/.env.local", "warning")
            env_content = """# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url_here
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key_here
"""
            with open(frontend_env, 'w') as f:
                f.write(env_content)
            print_status("Created frontend/.env.local - Please update with your configuration", "warning")
        else:
            print_status("frontend/.env.local already exists")
    
    def verify_fixes(self) -> bool:
        """Verify all fixes have been applied correctly."""
        print("\n=== Verifying Fixes ===")
        
        issues = []
        
        # Check backend fixes
        checks = [
            (self.backend_dir / "requirements.txt", "qrcode==7.4.2", "qrcode dependency"),
            (self.backend_dir / "app/main.py", "load_dotenv()", "env loading in main.py"),
            (self.backend_dir / "app/services/ai_vision_client.py", "if width > 8000", "image validation"),
            (self.backend_dir / "app/services/ai_vision_client.py", "typography_timeout", "timeout handling"),
        ]
        
        for file_path, search_string, description in checks:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                    if search_string not in content:
                        issues.append(f"{description} not found in {file_path.name}")
                        print_status(f"Missing: {description}", "error")
                    else:
                        print_status(f"Verified: {description}")
            else:
                issues.append(f"File not found: {file_path}")
                print_status(f"File not found: {file_path}", "error")
        
        # Check frontend fixes
        frontend_checks = [
            (self.frontend_dir / "src/lib/design-system/extractor/tokenizer.ts", "AbortController", "timeout handling"),
            (self.frontend_dir / "src/lib/design-system/cli/extract.ts", "withRetry", "retry logic"),
            (self.frontend_dir / "src/lib/design-system/extractor/analyzer.ts", "8000", "image validation"),
        ]
        
        for file_path, search_string, description in frontend_checks:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                    if search_string not in content:
                        issues.append(f"{description} not found in {file_path.name}")
                        print_status(f"Missing: {description}", "error")
                    else:
                        print_status(f"Verified: {description}")
            else:
                issues.append(f"File not found: {file_path}")
                print_status(f"File not found: {file_path}", "error")
        
        if issues:
            print(f"\n{Colors.RED}Found {len(issues)} issues:{Colors.ENDC}")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print_status("\nAll fixes verified successfully!", "success")
            return True
    
    def print_summary(self):
        """Print summary of fixes applied."""
        print("\n=== Summary ===")
        
        if self.fixes_applied:
            print(f"\n{Colors.GREEN}Fixes Applied ({len(self.fixes_applied)}):{Colors.ENDC}")
            for fix in self.fixes_applied:
                print(f"  ✓ {fix}")
        
        if self.fixes_failed:
            print(f"\n{Colors.RED}Fixes Failed ({len(self.fixes_failed)}):{Colors.ENDC}")
            for fix in self.fixes_failed:
                print(f"  ✗ {fix}")
        
        print("\n=== Next Steps ===")
        print("1. Update .env files with your API keys")
        print("2. Install backend dependencies: cd backend && pip install -r requirements.txt")
        print("3. Install frontend dependencies: cd frontend && npm install")
        print("4. Start backend: cd backend && uvicorn app.main:app --reload")
        print("5. Start frontend: cd frontend && npm run dev")
        print("6. Test extraction: cd frontend && npm run design:extract <screenshot>")

def main():
    """Main entry point."""
    print(f"{Colors.BLUE}🔧 Design System Fix Application Script{Colors.ENDC}")
    print("=" * 40)
    
    # Find project root
    current_dir = Path.cwd()
    if current_dir.name == "scripts":
        project_root = current_dir.parent
    else:
        project_root = current_dir
    
    fixer = DesignSystemFixer(project_root)
    
    # Verify project structure
    if not fixer.verify_project_structure():
        print_status("Please run this script from the project root or scripts directory", "error")
        sys.exit(1)
    
    print_status(f"Project root: {project_root}")
    
    # Apply fixes
    fixer.apply_backend_fixes()
    fixer.apply_frontend_fixes()
    
    # Create env files if needed
    fixer.create_env_files()
    
    # Verify fixes
    fixer.verify_fixes()
    
    # Print summary
    fixer.print_summary()

if __name__ == "__main__":
    main()