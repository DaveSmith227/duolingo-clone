#!/usr/bin/env python3
"""
Secret Detection Script for Pre-commit Hooks

Scans files for potential secrets and sensitive information to prevent
them from being committed to the repository.
"""

import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Pattern, Tuple
from dataclasses import dataclass
from enum import Enum


class SecretType(Enum):
    """Types of secrets that can be detected."""
    API_KEY = "api_key"
    PASSWORD = "password"
    SECRET_KEY = "secret_key"
    TOKEN = "token"
    PRIVATE_KEY = "private_key"
    CONNECTION_STRING = "connection_string"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"
    AWS_CREDENTIALS = "aws_credentials"
    GITHUB_TOKEN = "github_token"
    SUPABASE_KEY = "supabase_key"
    JWT_SECRET = "jwt_secret"


@dataclass
class SecretPattern:
    """Pattern definition for detecting secrets."""
    type: SecretType
    pattern: Pattern[str]
    description: str
    severity: str = "high"
    exclude_patterns: List[Pattern[str]] = None
    
    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = []


@dataclass
class DetectedSecret:
    """Information about a detected secret."""
    file_path: str
    line_number: int
    line_content: str
    secret_type: SecretType
    matched_text: str
    severity: str
    description: str


class SecretDetector:
    """Main class for detecting secrets in files."""
    
    def __init__(self):
        self.patterns = self._initialize_patterns()
        self.excluded_files = self._get_excluded_files()
        self.false_positive_patterns = self._get_false_positive_patterns()
    
    def _initialize_patterns(self) -> List[SecretPattern]:
        """Initialize all secret detection patterns."""
        return [
            # API Keys
            SecretPattern(
                type=SecretType.API_KEY,
                pattern=re.compile(r'["\']?api[_-]?key["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', re.IGNORECASE),
                description="Generic API key pattern",
                exclude_patterns=[
                    re.compile(r'(example|sample|test|demo|dummy)', re.IGNORECASE),
                    re.compile(r'\.example'),
                ]
            ),
            
            # OpenAI API Keys
            SecretPattern(
                type=SecretType.API_KEY,
                pattern=re.compile(r'sk-[a-zA-Z0-9]{48}'),
                description="OpenAI API key",
                severity="critical"
            ),
            
            # Supabase Keys
            SecretPattern(
                type=SecretType.SUPABASE_KEY,
                pattern=re.compile(r'eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+'),
                description="Supabase JWT/Anon key",
                exclude_patterns=[
                    re.compile(r'\.test\.|test_|_test|example|sample', re.IGNORECASE),
                ]
            ),
            
            # Generic Passwords
            SecretPattern(
                type=SecretType.PASSWORD,
                pattern=re.compile(r'["\']?password["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE),
                description="Password assignment",
                exclude_patterns=[
                    re.compile(r'^(password|changeme|default|example|test|demo)$', re.IGNORECASE),
                    re.compile(r'\$\{.*\}'),  # Template variables
                    re.compile(r'os\.environ'),  # Environment variables
                ]
            ),
            
            # Secret Keys
            SecretPattern(
                type=SecretType.SECRET_KEY,
                pattern=re.compile(r'["\']?secret[_-]?key["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-]{16,})["\']', re.IGNORECASE),
                description="Secret key pattern",
                exclude_patterns=[
                    re.compile(r'(dev-secret-key|change-me|your-secret-key)', re.IGNORECASE),
                    re.compile(r'\.example'),
                ]
            ),
            
            # JWT Secrets
            SecretPattern(
                type=SecretType.JWT_SECRET,
                pattern=re.compile(r'["\']?jwt[_-]?secret["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE),
                description="JWT secret",
                exclude_patterns=[
                    re.compile(r'^(your-jwt-secret|change-me|secret)$', re.IGNORECASE),
                ]
            ),
            
            # Database Connection Strings
            SecretPattern(
                type=SecretType.CONNECTION_STRING,
                pattern=re.compile(r'(postgresql|postgres|mysql|mongodb|redis)://[^:]+:([^@]+)@[^/\s]+', re.IGNORECASE),
                description="Database connection string with password",
                exclude_patterns=[
                    re.compile(r'^(password|pass|changeme)$', re.IGNORECASE),
                ]
            ),
            
            # Private Keys
            SecretPattern(
                type=SecretType.PRIVATE_KEY,
                pattern=re.compile(r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'),
                description="Private key header",
                severity="critical"
            ),
            
            # SSH Keys
            SecretPattern(
                type=SecretType.SSH_KEY,
                pattern=re.compile(r'ssh-(rsa|dss|ed25519) [a-zA-Z0-9+/]{100,}'),
                description="SSH key",
                severity="critical"
            ),
            
            # AWS Credentials
            SecretPattern(
                type=SecretType.AWS_CREDENTIALS,
                pattern=re.compile(r'AKIA[0-9A-Z]{16}'),
                description="AWS Access Key ID",
                severity="critical"
            ),
            
            # GitHub Tokens
            SecretPattern(
                type=SecretType.GITHUB_TOKEN,
                pattern=re.compile(r'ghp_[a-zA-Z0-9]{36}'),
                description="GitHub Personal Access Token",
                severity="critical"
            ),
            
            # Generic Bearer Tokens
            SecretPattern(
                type=SecretType.TOKEN,
                pattern=re.compile(r'bearer\s+([a-zA-Z0-9_\-\.]{20,})', re.IGNORECASE),
                description="Bearer token",
                exclude_patterns=[
                    re.compile(r'(example|sample|test|demo)', re.IGNORECASE),
                ]
            ),
        ]
    
    def _get_excluded_files(self) -> List[Pattern[str]]:
        """Get patterns for files that should be excluded from scanning."""
        return [
            re.compile(r'\.git/'),
            re.compile(r'\.pytest_cache/'),
            re.compile(r'__pycache__/'),
            re.compile(r'\.pyc$'),
            re.compile(r'\.example$'),
            re.compile(r'\.md$'),
            re.compile(r'\.txt$'),
            re.compile(r'\.json$'),
            re.compile(r'\.lock$'),
            re.compile(r'node_modules/'),
            re.compile(r'venv/'),
            re.compile(r'\.env\.example'),
            re.compile(r'detect_secrets\.py$'),  # This file
            re.compile(r'test_.*\.py$'),  # Test files
            re.compile(r'.*/tests?/'),  # Test directories
        ]
    
    def _get_false_positive_patterns(self) -> List[Pattern[str]]:
        """Get patterns that indicate false positives."""
        return [
            re.compile(r'process\.env\.[A-Z_]+'),  # Environment variable references
            re.compile(r'os\.environ\[["\'][A-Z_]+["\']\]'),  # Python env vars
            re.compile(r'os\.getenv\(["\'][A-Z_]+["\']'),  # Python getenv
            re.compile(r'\$\{[A-Z_]+\}'),  # Template variables
            re.compile(r'<[A-Z_]+>'),  # Placeholder variables
            re.compile(r'Field\(.*alias='),  # Pydantic field definitions
            re.compile(r'@.*\.setter'),  # Python property setters
            re.compile(r'def test_'),  # Test functions
        ]
    
    def should_scan_file(self, file_path: Path) -> bool:
        """Check if a file should be scanned."""
        # Check if file is excluded
        for pattern in self.excluded_files:
            if pattern.search(str(file_path)):
                return False
        
        # Only scan text files
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)  # Try to read first 1KB
            return True
        except (UnicodeDecodeError, IOError):
            return False
    
    def is_false_positive(self, line: str, matched_text: str) -> bool:
        """Check if a detection is likely a false positive."""
        # Check false positive patterns
        for pattern in self.false_positive_patterns:
            if pattern.search(line):
                return True
        
        # Check if it's a variable reference
        if matched_text.startswith('$') or matched_text.startswith('${'):
            return True
        
        # Check if it's in a comment explaining usage
        if any(comment in line for comment in ['# Example:', '// Example:', '/* Example:', '* Example:']):
            return True
        
        return False
    
    def scan_line(self, line: str, line_number: int, file_path: str) -> List[DetectedSecret]:
        """Scan a single line for secrets."""
        detected = []
        
        for secret_pattern in self.patterns:
            matches = secret_pattern.pattern.finditer(line)
            
            for match in matches:
                matched_text = match.group(0)
                
                # Extract the actual secret value if captured
                secret_value = match.group(1) if match.groups() else matched_text
                
                # Check exclude patterns against the secret value
                excluded = False
                for exclude_pattern in secret_pattern.exclude_patterns:
                    if exclude_pattern.match(secret_value):
                        excluded = True
                        break
                
                if excluded:
                    continue
                
                # Check if it's a false positive
                if self.is_false_positive(line, matched_text):
                    continue
                
                detected.append(DetectedSecret(
                    file_path=file_path,
                    line_number=line_number,
                    line_content=line.strip(),
                    secret_type=secret_pattern.type,
                    matched_text=secret_value[:20] + "..." if len(secret_value) > 20 else secret_value,
                    severity=secret_pattern.severity,
                    description=secret_pattern.description
                ))
        
        return detected
    
    def scan_file(self, file_path: Path) -> List[DetectedSecret]:
        """Scan a file for secrets."""
        if not self.should_scan_file(file_path):
            return []
        
        detected = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_number, line in enumerate(f, 1):
                    detected.extend(self.scan_line(line, line_number, str(file_path)))
        except Exception as e:
            print(f"Error scanning {file_path}: {e}", file=sys.stderr)
        
        return detected
    
    def scan_files(self, file_paths: List[str]) -> List[DetectedSecret]:
        """Scan multiple files for secrets."""
        all_detected = []
        
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            if file_path.exists():
                all_detected.extend(self.scan_file(file_path))
        
        return all_detected


def format_detection_report(detections: List[DetectedSecret]) -> str:
    """Format detection results for display."""
    if not detections:
        return "✅ No secrets detected!"
    
    report = ["🚨 POTENTIAL SECRETS DETECTED 🚨\n"]
    report.append(f"Found {len(detections)} potential secret(s) in {len(set(d.file_path for d in detections))} file(s)\n")
    
    # Group by file
    by_file: Dict[str, List[DetectedSecret]] = {}
    for detection in detections:
        if detection.file_path not in by_file:
            by_file[detection.file_path] = []
        by_file[detection.file_path].append(detection)
    
    for file_path, file_detections in by_file.items():
        report.append(f"\n📄 {file_path}")
        report.append("-" * (len(file_path) + 4))
        
        for detection in file_detections:
            severity_icon = "🔴" if detection.severity == "critical" else "🟡"
            report.append(f"\n{severity_icon} Line {detection.line_number}: {detection.description}")
            report.append(f"   Type: {detection.secret_type.value}")
            report.append(f"   Found: {detection.matched_text}")
            report.append(f"   Line: {detection.line_content[:80]}...")
    
    report.append("\n\n❌ COMMIT BLOCKED: Remove or secure these secrets before committing!")
    report.append("\nSuggestions:")
    report.append("  • Move secrets to environment variables")
    report.append("  • Use .env files (and add to .gitignore)")
    report.append("  • Use a secrets management service")
    report.append("  • For examples/tests, use clearly fake values")
    
    return "\n".join(report)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Detect secrets in files")
    parser.add_argument('files', nargs='*', help='Files to scan')
    parser.add_argument('--all', action='store_true', help='Scan all files in repository')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--baseline', help='Baseline file for known secrets')
    parser.add_argument('--update-baseline', action='store_true', help='Update baseline with new detections')
    
    args = parser.parse_args()
    
    detector = SecretDetector()
    
    # Get files to scan
    if args.all:
        # Scan all files in repository
        files = []
        for pattern in ['**/*.py', '**/*.js', '**/*.ts', '**/*.jsx', '**/*.tsx', 
                       '**/*.env', '**/*.conf', '**/*.config', '**/*.yml', '**/*.yaml']:
            files.extend([str(p) for p in Path('.').glob(pattern)])
    else:
        files = args.files if args.files else []
    
    if not files:
        print("No files to scan", file=sys.stderr)
        return 0
    
    # Scan files
    detections = detector.scan_files(files)
    
    # Load baseline if provided
    baseline_secrets = set()
    if args.baseline and Path(args.baseline).exists():
        with open(args.baseline, 'r') as f:
            baseline_data = json.load(f)
            for item in baseline_data.get('secrets', []):
                baseline_secrets.add(f"{item['file']}:{item['line']}:{item['type']}")
    
    # Filter out baselined secrets
    new_detections = []
    for detection in detections:
        key = f"{detection.file_path}:{detection.line_number}:{detection.secret_type.value}"
        if key not in baseline_secrets:
            new_detections.append(detection)
    
    # Update baseline if requested
    if args.update_baseline and args.baseline:
        baseline_data = {
            'secrets': [
                {
                    'file': d.file_path,
                    'line': d.line_number,
                    'type': d.secret_type.value,
                    'severity': d.severity
                }
                for d in detections
            ]
        }
        with open(args.baseline, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        print(f"Updated baseline with {len(detections)} entries")
        return 0
    
    # Output results
    if args.json:
        results = {
            'detected': len(new_detections),
            'secrets': [
                {
                    'file': d.file_path,
                    'line': d.line_number,
                    'type': d.secret_type.value,
                    'severity': d.severity,
                    'description': d.description,
                    'matched': d.matched_text
                }
                for d in new_detections
            ]
        }
        print(json.dumps(results, indent=2))
    else:
        print(format_detection_report(new_detections))
    
    # Return non-zero exit code if secrets detected
    return 1 if new_detections else 0


if __name__ == '__main__':
    sys.exit(main())