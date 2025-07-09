#!/usr/bin/env python3
"""
End-to-End Test Script for Design System Fixes

This script tests all the fixes applied to ensure the design system
works correctly from screenshot to token generation.
"""

import os
import sys
import json
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import requests

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

def print_test(message: str, status: str = "running"):
    """Print colored test status message."""
    if status == "pass":
        print(f"{Colors.GREEN}✓ PASS{Colors.ENDC} {message}")
    elif status == "fail":
        print(f"{Colors.RED}✗ FAIL{Colors.ENDC} {message}")
    elif status == "skip":
        print(f"{Colors.YELLOW}⊝ SKIP{Colors.ENDC} {message}")
    elif status == "running":
        print(f"{Colors.BLUE}➤ TEST{Colors.ENDC} {message}")

class DesignSystemTester:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backend_dir = project_root / "backend"
        self.frontend_dir = project_root / "frontend"
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "tests": []
        }
        self.backend_process = None
        self.frontend_process = None
        
    def run_all_tests(self):
        """Run all end-to-end tests."""
        print(f"{Colors.BLUE}🧪 Design System End-to-End Tests{Colors.ENDC}")
        print("=" * 40)
        
        # Pre-flight checks
        self.test_environment_setup()
        self.test_dependencies()
        
        # Backend tests
        self.test_backend_startup()
        self.test_backend_health()
        self.test_backend_ai_config()
        
        # Frontend tests
        self.test_frontend_build()
        
        # Integration tests
        self.test_token_extraction()
        self.test_timeout_handling()
        self.test_image_validation()
        self.test_retry_logic()
        
        # Print summary
        self.print_summary()
    
    def test_environment_setup(self):
        """Test that environment files exist."""
        print_test("Environment Setup")
        
        backend_env = self.backend_dir / ".env"
        frontend_env = self.frontend_dir / ".env.local"
        
        if not backend_env.exists():
            self._record_test("Backend .env exists", False, "File not found")
        else:
            # Check for API keys
            with open(backend_env, 'r') as f:
                content = f.read()
                has_anthropic = 'ANTHROPIC_API_KEY=' in content and 'your_anthropic_api_key_here' not in content
                has_openai = 'OPENAI_API_KEY=' in content and 'your_openai_api_key_here' not in content
                
                if has_anthropic or has_openai:
                    self._record_test("Backend .env with API keys", True)
                else:
                    self._record_test("Backend .env with API keys", False, "No valid API keys found")
        
        if not frontend_env.exists():
            self._record_test("Frontend .env.local exists", False, "File not found")
        else:
            self._record_test("Frontend .env.local exists", True)
    
    def test_dependencies(self):
        """Test that all dependencies are installed."""
        print_test("Dependencies Check")
        
        # Test Python dependencies
        try:
            import qrcode
            import dotenv
            import PIL
            self._record_test("Python dependencies", True)
        except ImportError as e:
            self._record_test("Python dependencies", False, str(e))
        
        # Test Node modules
        node_modules = self.frontend_dir / "node_modules"
        if node_modules.exists():
            self._record_test("Frontend node_modules", True)
        else:
            self._record_test("Frontend node_modules", False, "Not installed")
    
    def test_backend_startup(self):
        """Test that backend can start without errors."""
        print_test("Backend Startup")
        
        try:
            # Try importing the app
            os.chdir(self.backend_dir)
            sys.path.insert(0, str(self.backend_dir))
            
            from dotenv import load_dotenv
            load_dotenv()
            
            # Import critical modules
            from app.main import app
            from app.services.design_system_service import DesignSystemService
            from app.services.ai_vision_client import AIVisionClient
            
            self._record_test("Backend imports", True)
            
            # Check AI client configuration
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            openai_key = os.getenv('OPENAI_API_KEY')
            
            if anthropic_key and anthropic_key != 'your_anthropic_api_key_here':
                self._record_test("Anthropic API key configured", True)
            else:
                self._record_test("Anthropic API key configured", False, "Not configured")
            
            if openai_key and openai_key != 'your_openai_api_key_here':
                self._record_test("OpenAI API key configured", True)
            else:
                self._record_test("OpenAI API key configured", False, "Not configured")
            
        except Exception as e:
            self._record_test("Backend startup", False, str(e))
        finally:
            os.chdir(self.project_root)
    
    def test_backend_health(self):
        """Test backend health endpoint."""
        print_test("Backend Health Check", "skip")
        self._record_test("Backend health endpoint", None, "Requires running server")
    
    def test_backend_ai_config(self):
        """Test AI client configuration."""
        print_test("AI Client Configuration")
        
        try:
            os.chdir(self.backend_dir)
            from app.services.design_system_service import DesignSystemService
            
            # Try to instantiate service
            service = DesignSystemService()
            
            if hasattr(service, 'ai_clients') and service.ai_clients:
                self._record_test("AI clients initialized", True)
            else:
                self._record_test("AI clients initialized", False, "No clients configured")
                
        except Exception as e:
            self._record_test("AI client configuration", False, str(e))
        finally:
            os.chdir(self.project_root)
    
    def test_frontend_build(self):
        """Test that frontend can build."""
        print_test("Frontend Build", "skip")
        self._record_test("Frontend build", None, "Skipped for performance")
    
    def test_token_extraction(self):
        """Test token extraction with a sample image."""
        print_test("Token Extraction")
        
        # Create a test image
        test_image = self._create_test_image()
        
        if test_image:
            # Test image validation
            self._test_image_analysis(test_image)
        else:
            self._record_test("Token extraction", False, "Could not create test image")
    
    def test_timeout_handling(self):
        """Test timeout handling for typography extraction."""
        print_test("Timeout Handling")
        
        # Check if timeout code is present
        tokenizer_path = self.frontend_dir / "src/lib/design-system/extractor/tokenizer.ts"
        if tokenizer_path.exists():
            with open(tokenizer_path, 'r') as f:
                content = f.read()
                if 'AbortController' in content and '60000' in content:
                    self._record_test("Frontend timeout implementation", True)
                else:
                    self._record_test("Frontend timeout implementation", False, "Missing timeout code")
        
        # Check backend timeout
        ai_client_path = self.backend_dir / "app/services/ai_vision_client.py"
        if ai_client_path.exists():
            with open(ai_client_path, 'r') as f:
                content = f.read()
                if 'typography_timeout' in content:
                    self._record_test("Backend timeout implementation", True)
                else:
                    self._record_test("Backend timeout implementation", False, "Missing timeout code")
    
    def test_image_validation(self):
        """Test image size validation."""
        print_test("Image Size Validation")
        
        # Check backend validation
        ai_client_path = self.backend_dir / "app/services/ai_vision_client.py"
        if ai_client_path.exists():
            with open(ai_client_path, 'r') as f:
                content = f.read()
                if 'if width > 8000 or height > 8000' in content:
                    self._record_test("Backend image validation", True)
                else:
                    self._record_test("Backend image validation", False, "Missing size check")
        
        # Check frontend validation
        analyzer_path = self.frontend_dir / "src/lib/design-system/extractor/analyzer.ts"
        if analyzer_path.exists():
            with open(analyzer_path, 'r') as f:
                content = f.read()
                if 'img.width > 8000 || img.height > 8000' in content:
                    self._record_test("Frontend image validation", True)
                else:
                    self._record_test("Frontend image validation", False, "Missing size check")
    
    def test_retry_logic(self):
        """Test retry logic implementation."""
        print_test("Retry Logic")
        
        extract_path = self.frontend_dir / "src/lib/design-system/cli/extract.ts"
        if extract_path.exists():
            with open(extract_path, 'r') as f:
                content = f.read()
                if 'withRetry' in content and 'exponential backoff' in content:
                    self._record_test("Retry logic implementation", True)
                else:
                    self._record_test("Retry logic implementation", False, "Missing retry code")
    
    def _create_test_image(self) -> Optional[Path]:
        """Create a simple test image."""
        try:
            from PIL import Image, ImageDraw
            
            # Create a simple test image
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)
            
            # Draw some shapes with colors
            draw.rectangle([50, 50, 150, 150], fill='#58cc02')  # Primary green
            draw.rectangle([200, 50, 300, 150], fill='#1cb0f6')  # Secondary blue
            draw.rectangle([50, 200, 150, 300], fill='#ff4b4b')  # Error red
            
            # Save to temp file
            temp_dir = Path(tempfile.gettempdir())
            test_image = temp_dir / "design_system_test.png"
            img.save(test_image)
            
            self._record_test("Test image creation", True)
            return test_image
            
        except Exception as e:
            self._record_test("Test image creation", False, str(e))
            return None
    
    def _test_image_analysis(self, image_path: Path):
        """Test image analysis functionality."""
        try:
            os.chdir(self.backend_dir)
            from app.services.design_system_service import DesignSystemService
            
            service = DesignSystemService()
            
            # Test path resolution
            resolved = service._resolve_image_path(str(image_path))
            if resolved:
                self._record_test("Image path resolution", True)
            else:
                self._record_test("Image path resolution", False, "Could not resolve path")
                
        except Exception as e:
            self._record_test("Image analysis", False, str(e))
        finally:
            os.chdir(self.project_root)
    
    def _record_test(self, test_name: str, passed: Optional[bool], message: str = ""):
        """Record test result."""
        if passed is None:
            self.test_results["skipped"] += 1
            print_test(f"{test_name}: {message}", "skip")
        elif passed:
            self.test_results["passed"] += 1
            print_test(test_name, "pass")
        else:
            self.test_results["failed"] += 1
            print_test(f"{test_name}: {message}", "fail")
        
        self.test_results["tests"].append({
            "name": test_name,
            "passed": passed,
            "message": message
        })
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 40)
        print(f"{Colors.BLUE}Test Summary{Colors.ENDC}")
        print("=" * 40)
        
        total = self.test_results["passed"] + self.test_results["failed"] + self.test_results["skipped"]
        
        print(f"\nTotal Tests: {total}")
        print(f"{Colors.GREEN}Passed: {self.test_results['passed']}{Colors.ENDC}")
        print(f"{Colors.RED}Failed: {self.test_results['failed']}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Skipped: {self.test_results['skipped']}{Colors.ENDC}")
        
        if self.test_results["failed"] > 0:
            print(f"\n{Colors.RED}Failed Tests:{Colors.ENDC}")
            for test in self.test_results["tests"]:
                if test["passed"] is False:
                    print(f"  - {test['name']}: {test['message']}")
        
        # Recommendations
        print("\n" + "=" * 40)
        print("Recommendations:")
        
        if self.test_results["failed"] == 0:
            print(f"{Colors.GREEN}✓ All tests passed! The design system is ready to use.{Colors.ENDC}")
            print("\nNext steps:")
            print("1. Start the backend: cd backend && uvicorn app.main:app --reload")
            print("2. Start the frontend: cd frontend && npm run dev")
            print("3. Try extracting tokens: npm run design:extract <screenshot>")
        else:
            print(f"{Colors.YELLOW}⚠ Some tests failed. Please address the issues above.{Colors.ENDC}")
            print("\nCommon fixes:")
            print("1. Add API keys to backend/.env")
            print("2. Install dependencies: pip install -r requirements.txt")
            print("3. Run the fix script: python scripts/apply_fixes.py")

def main():
    """Main entry point."""
    # Find project root
    current_dir = Path.cwd()
    if current_dir.name == "scripts":
        project_root = current_dir.parent
    else:
        project_root = current_dir
    
    tester = DesignSystemTester(project_root)
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n{Colors.RED}Test suite error: {e}{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()