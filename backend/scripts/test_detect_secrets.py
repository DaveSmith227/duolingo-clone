#!/usr/bin/env python3
"""
Tests for Secret Detection Script

Tests the secret detection patterns and functionality.
"""

import pytest
import tempfile
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from detect_secrets import SecretDetector, SecretType, DetectedSecret, format_detection_report


class TestSecretDetector:
    """Test the SecretDetector class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.detector = SecretDetector()
    
    def test_detect_api_key(self):
        """Test detection of API keys."""
        test_cases = [
            ('api_key = "sk-1234567890abcdef1234567890abcdef"', True),  # Should detect
            ('api_key = "example-api-key"', False),  # Should not detect (example)
            ('API_KEY = "abcdefghijklmnopqrstuvwxyz123456"', True),  # Should detect
            ('# api_key = "test-key"', False),  # Should not detect (test)
        ]
        
        for line, should_detect in test_cases:
            results = self.detector.scan_line(line, 1, "test.py")
            if should_detect:
                assert len(results) > 0, f"Should detect secret in: {line}"
                assert results[0].secret_type == SecretType.API_KEY
            else:
                assert len(results) == 0, f"Should not detect secret in: {line}"
    
    def test_detect_openai_key(self):
        """Test detection of OpenAI API keys."""
        # Real OpenAI key pattern - sk- followed by exactly 48 characters
        line = 'openai_key = "sk-' + 'a' * 48 + '"'
        results = self.detector.scan_line(line, 1, "test.py")
        
        assert len(results) == 1
        assert results[0].secret_type == SecretType.API_KEY
        assert "OpenAI" in results[0].description
    
    def test_detect_password(self):
        """Test detection of passwords."""
        test_cases = [
            ('password = "mysecretpassword123"', True),  # Should detect
            ('password = "password"', False),  # Should not detect (too obvious)
            ('db_password = "changeme"', False),  # Should not detect (default)
            ('PASSWORD = "ReallySecurePass123!"', True),  # Should detect
            ('password = os.environ["DB_PASSWORD"]', False),  # Should not detect (env var)
        ]
        
        for line, should_detect in test_cases:
            results = self.detector.scan_line(line, 1, "test.py")
            if should_detect:
                assert len(results) > 0, f"Should detect password in: {line}"
                assert results[0].secret_type == SecretType.PASSWORD
            else:
                assert len(results) == 0, f"Should not detect password in: {line}"
    
    def test_detect_connection_string(self):
        """Test detection of database connection strings."""
        test_cases = [
            ('db_url = "postgresql://user:secretpass@localhost:5432/db"', True),
            ('db_url = "postgresql://user:password@localhost:5432/db"', False),  # Common password
            ('REDIS_URL = "redis://default:mysecret@redis:6379"', True),
            ('# Example: postgresql://user:pass@host:5432/db', False),  # Comment
        ]
        
        for line, should_detect in test_cases:
            results = self.detector.scan_line(line, 1, "test.py")
            if should_detect:
                assert len(results) > 0, f"Should detect connection string in: {line}"
                assert results[0].secret_type == SecretType.CONNECTION_STRING
    
    def test_detect_jwt_secret(self):
        """Test detection of JWT secrets."""
        test_cases = [
            ('JWT_SECRET = "my-super-secret-jwt-key-123"', True),
            ('jwt_secret = "your-jwt-secret"', False),  # Placeholder
            ('JWT_SECRET = "abcdefghijklmnopqrstuvwxyz123456"', True),
        ]
        
        for line, should_detect in test_cases:
            results = self.detector.scan_line(line, 1, "test.py")
            if should_detect:
                assert len(results) > 0, f"Should detect JWT secret in: {line}"
                assert results[0].secret_type == SecretType.JWT_SECRET
    
    def test_detect_private_key(self):
        """Test detection of private keys."""
        private_key_line = "-----BEGIN RSA PRIVATE KEY-----"
        results = self.detector.scan_line(private_key_line, 1, "test.pem")
        
        assert len(results) == 1
        assert results[0].secret_type == SecretType.PRIVATE_KEY
        assert results[0].severity == "critical"
    
    def test_detect_aws_credentials(self):
        """Test detection of AWS credentials."""
        aws_key = 'aws_access_key = "AKIAIOSFODNN7EXAMPLE"'
        results = self.detector.scan_line(aws_key, 1, "test.py")
        
        assert len(results) == 1
        assert results[0].secret_type == SecretType.AWS_CREDENTIALS
        assert results[0].severity == "critical"
    
    def test_false_positives(self):
        """Test that false positives are not detected."""
        false_positive_cases = [
            'api_key = process.env.API_KEY',  # Environment variable
            'password = os.environ["PASSWORD"]',  # Python env var
            'secret = "${SECRET_KEY}"',  # Template variable
            'token = "<YOUR_TOKEN_HERE>"',  # Placeholder
            '# Example: api_key = "sk-1234"',  # Comment
            'Field(alias="api_key")',  # Pydantic field
            'def test_api_key():',  # Test function
        ]
        
        for line in false_positive_cases:
            results = self.detector.scan_line(line, 1, "test.py")
            assert len(results) == 0, f"Should not detect false positive in: {line}"
    
    def test_file_exclusion(self):
        """Test that certain files are excluded from scanning."""
        excluded_paths = [
            Path(".git/config"),
            Path("node_modules/package/index.js"),
            Path("venv/lib/python/site.py"),
            Path(".env.example"),
            Path("README.md"),
            Path("test_secrets.py"),
            Path("detect-secrets.py"),
        ]
        
        for path in excluded_paths:
            assert not self.detector.should_scan_file(path), f"Should exclude: {path}"
    
    def test_scan_file(self):
        """Test scanning an entire file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
# Configuration file
API_KEY = "sk-1234567890abcdef1234567890abcdef"
PASSWORD = "mysecretpassword123"
DB_URL = "postgresql://user:secret@localhost:5432/db"

# These should not be detected
EXAMPLE_KEY = "example-api-key"
TEST_PASSWORD = "password"
ENV_SECRET = os.environ["SECRET_KEY"]
""")
            f.flush()
            
            results = self.detector.scan_file(Path(f.name))
            
            # Should detect 3 secrets
            assert len(results) == 3
            
            # Check types
            types = [r.secret_type for r in results]
            assert SecretType.API_KEY in types
            assert SecretType.PASSWORD in types
            assert SecretType.CONNECTION_STRING in types
            
            # Clean up
            Path(f.name).unlink()


class TestDetectionReport:
    """Test the detection report formatting."""
    
    def test_format_no_detections(self):
        """Test report when no secrets are detected."""
        report = format_detection_report([])
        assert "No secrets detected" in report
        assert "✅" in report
    
    def test_format_with_detections(self):
        """Test report with detected secrets."""
        detections = [
            DetectedSecret(
                file_path="config.py",
                line_number=10,
                line_content='API_KEY = "sk-secret123"',
                secret_type=SecretType.API_KEY,
                matched_text="sk-secret123",
                severity="high",
                description="API key detected"
            ),
            DetectedSecret(
                file_path="settings.py",
                line_number=20,
                line_content='password = "mysecret"',
                secret_type=SecretType.PASSWORD,
                matched_text="mysecret",
                severity="high",
                description="Password detected"
            ),
        ]
        
        report = format_detection_report(detections)
        
        assert "POTENTIAL SECRETS DETECTED" in report
        assert "Found 2 potential secret(s)" in report
        assert "config.py" in report
        assert "settings.py" in report
        assert "API key detected" in report
        assert "Password detected" in report
        assert "COMMIT BLOCKED" in report


class TestSecretPatterns:
    """Test specific secret patterns."""
    
    def test_supabase_jwt_pattern(self):
        """Test Supabase JWT pattern detection."""
        detector = SecretDetector()
        
        # Supabase JWTs start with "eyJ"
        supabase_jwt = 'SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRlc3QiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYxNjY0MjQyMiwiZXhwIjoxOTMyMjE4NDIyfQ.abcdefghijklmnop"'
        results = detector.scan_line(supabase_jwt, 1, "test.env")
        
        assert len(results) == 1
        assert results[0].secret_type == SecretType.SUPABASE_KEY
    
    def test_github_token_pattern(self):
        """Test GitHub token pattern detection."""
        detector = SecretDetector()
        
        github_token = 'github_token = "ghp_1234567890abcdef1234567890abcdef1234"'
        results = detector.scan_line(github_token, 1, "test.py")
        
        assert len(results) == 1
        assert results[0].secret_type == SecretType.GITHUB_TOKEN
        assert results[0].severity == "critical"
    
    def test_bearer_token_pattern(self):
        """Test Bearer token pattern detection."""
        detector = SecretDetector()
        
        bearer_token = 'Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456'
        results = detector.scan_line(bearer_token, 1, "test.py")
        
        assert len(results) == 1
        assert results[0].secret_type == SecretType.TOKEN


if __name__ == '__main__':
    pytest.main([__file__, '-v'])