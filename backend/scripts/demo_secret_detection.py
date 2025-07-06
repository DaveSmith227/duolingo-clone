#!/usr/bin/env python3
"""
Demo script to show secret detection in action
"""

import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from detect_secrets import SecretDetector, format_detection_report


def demo_secret_detection():
    """Demonstrate secret detection capabilities."""
    
    # Create a sample file with various secrets
    sample_code = '''
# Configuration file
import os

# Good practices - these won't be detected
API_KEY = os.environ["API_KEY"]
DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "default")
JWT_SECRET = "${JWT_SECRET_KEY}"

# Bad practices - these WILL be detected
OPENAI_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456789012345678"
PASSWORD = "mysupersecretpassword123"
DB_URL = "postgresql://admin:realPassword123@db.example.com:5432/prod"
JWT_SECRET = "my-production-jwt-secret-key-that-should-not-be-here"
AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
GITHUB_TOKEN = "ghp_1234567890abcdef1234567890abcdef1234"

# False positives that won't be detected
EXAMPLE_KEY = "example-api-key"
TEST_PASSWORD = "password"
# Example: api_key = "sk-test123"
'''
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(sample_code)
        temp_file = Path(f.name)
    
    try:
        print("🔍 Scanning sample file for secrets...\n")
        print("File contents:")
        print("-" * 60)
        print(sample_code)
        print("-" * 60)
        print()
        
        # Scan the file
        detector = SecretDetector()
        results = detector.scan_file(temp_file)
        
        # Show results
        print(format_detection_report(results))
        
        print("\n\n📊 Summary:")
        print(f"   • Total secrets found: {len(results)}")
        print(f"   • Critical severity: {sum(1 for r in results if r.severity == 'critical')}")
        print(f"   • High severity: {sum(1 for r in results if r.severity == 'high')}")
        
        if results:
            print("\n❌ This file would be BLOCKED from committing!")
        else:
            print("\n✅ This file would be allowed to commit.")
            
    finally:
        # Clean up
        temp_file.unlink()


if __name__ == "__main__":
    demo_secret_detection()