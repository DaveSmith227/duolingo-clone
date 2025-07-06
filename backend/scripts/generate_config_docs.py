#!/usr/bin/env python3

"""
Configuration Documentation Generator

Automatically generates comprehensive documentation from configuration schemas,
including examples, validation rules, and environment-specific requirements.

Usage:
    python scripts/generate_config_docs.py [--output-dir docs] [--format markdown]
    
Features:
- Extracts configuration from Pydantic models
- Generates examples and validation rules
- Creates environment-specific documentation
- Outputs in multiple formats (Markdown, HTML, JSON)
- Includes security guidelines and best practices
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pydantic import BaseModel, Field
    from pydantic.fields import FieldInfo
    from app.core.config import Settings
    from app.core.config_validators import ConfigurationBusinessRuleValidator
    from app.core.env_validators import (
        SecurityLevelValidator, URLValidator, BooleanSecurityValidator
    )
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the backend directory with virtual environment activated")
    sys.exit(1)


class ConfigDocGenerator:
    """Generates documentation from Pydantic configuration models."""
    
    def __init__(self, config_class: Type[BaseModel]):
        self.config_class = config_class
        self.schema = config_class.model_json_schema()
        self.validators = self._extract_validators()
        
    def _extract_validators(self) -> Dict[str, List[str]]:
        """Extract validation information from the model."""
        validators = {}
        
        # Get field validators from the model
        for field_name, field_info in self.config_class.model_fields.items():
            field_validators = []
            
            # Extract constraints from field
            if hasattr(field_info, 'constraints'):
                constraints = field_info.constraints
                if constraints.get('min_length'):
                    field_validators.append(f"Min length: {constraints['min_length']}")
                if constraints.get('max_length'):
                    field_validators.append(f"Max length: {constraints['max_length']}")
                if constraints.get('pattern'):
                    field_validators.append(f"Pattern: {constraints['pattern']}")
            
            # Extract from annotation
            if hasattr(field_info, 'annotation'):
                annotation = field_info.annotation
                if hasattr(annotation, '__args__'):
                    # Handle Union types (Optional)
                    args = getattr(annotation, '__args__', ())
                    if len(args) == 2 and type(None) in args:
                        field_validators.append("Optional")
            
            if field_validators:
                validators[field_name] = field_validators
                
        return validators
    
    def _get_field_info(self, field_name: str) -> Dict[str, Any]:
        """Get comprehensive information about a field."""
        properties = self.schema.get('properties', {})
        field_schema = properties.get(field_name, {})
        
        # Get field from model
        field_info = self.config_class.model_fields.get(field_name)
        
        info = {
            'name': field_name,
            'type': field_schema.get('type', 'unknown'),
            'description': field_schema.get('description', ''),
            'default': field_schema.get('default'),
            'required': field_name in self.schema.get('required', []),
            'validators': self.validators.get(field_name, []),
            'examples': [],
            'security_level': 'standard',
            'environments': ['development', 'staging', 'production']
        }
        
        # Determine security level
        field_lower = field_name.lower()
        if any(sensitive in field_lower for sensitive in 
               ['secret', 'key', 'password', 'token', 'credential', 'private']):
            info['security_level'] = 'sensitive'
        elif any(config in field_lower for config in 
                ['db_', 'database', 'redis', 'smtp']):
            info['security_level'] = 'configuration'
        
        # Add examples based on field name and type
        info['examples'] = self._generate_examples(field_name, info['type'], info['security_level'])
        
        return info
    
    def _generate_examples(self, field_name: str, field_type: str, security_level: str) -> List[Dict[str, str]]:
        """Generate examples for different environments."""
        examples = []
        
        if security_level == 'sensitive':
            examples = [
                {'environment': 'development', 'value': 'dev-secret-key-change-in-production', 'note': 'Development only'},
                {'environment': 'staging', 'value': '********', 'note': 'Use staging secrets'},
                {'environment': 'production', 'value': '********', 'note': 'Use production secrets from secure store'}
            ]
        elif field_name.lower().startswith('db_'):
            if 'host' in field_name.lower():
                examples = [
                    {'environment': 'development', 'value': 'localhost', 'note': 'Local database'},
                    {'environment': 'staging', 'value': 'staging-db.company.com', 'note': 'Staging database'},
                    {'environment': 'production', 'value': 'prod-db.company.com', 'note': 'Production database'}
                ]
            elif 'port' in field_name.lower():
                examples = [
                    {'environment': 'all', 'value': '5432', 'note': 'Standard PostgreSQL port'}
                ]
            elif 'name' in field_name.lower():
                examples = [
                    {'environment': 'development', 'value': 'duolingo_clone_dev', 'note': 'Development database'},
                    {'environment': 'staging', 'value': 'duolingo_clone_staging', 'note': 'Staging database'},
                    {'environment': 'production', 'value': 'duolingo_clone', 'note': 'Production database'}
                ]
        elif field_name.lower() == 'debug':
            examples = [
                {'environment': 'development', 'value': 'true', 'note': 'Enable debug mode'},
                {'environment': 'staging', 'value': 'false', 'note': 'Disable for staging'},
                {'environment': 'production', 'value': 'false', 'note': 'MUST be false in production'}
            ]
        elif field_name.lower() == 'environment':
            examples = [
                {'environment': 'development', 'value': 'development', 'note': 'Development environment'},
                {'environment': 'staging', 'value': 'staging', 'note': 'Staging environment'},
                {'environment': 'production', 'value': 'production', 'note': 'Production environment'}
            ]
        elif 'url' in field_name.lower():
            if 'cors' in field_name.lower():
                examples = [
                    {'environment': 'development', 'value': 'http://localhost:3000,http://127.0.0.1:3000', 'note': 'Local development'},
                    {'environment': 'production', 'value': 'https://yourdomain.com', 'note': 'Production domain only'}
                ]
            elif 'frontend' in field_name.lower():
                examples = [
                    {'environment': 'development', 'value': 'http://localhost:3000', 'note': 'Local frontend'},
                    {'environment': 'production', 'value': 'https://yourdomain.com', 'note': 'Production frontend'}
                ]
            else:
                examples = [
                    {'environment': 'development', 'value': 'http://localhost:8000', 'note': 'Local development'},
                    {'environment': 'production', 'value': 'https://api.yourdomain.com', 'note': 'Production API'}
                ]
        elif field_type == 'integer':
            examples = [{'environment': 'all', 'value': '8000', 'note': 'Standard port'}]
        elif field_type == 'boolean':
            examples = [
                {'environment': 'development', 'value': 'true', 'note': 'Enabled in development'},
                {'environment': 'production', 'value': 'false', 'note': 'Consider security implications'}
            ]
        else:
            examples = [{'environment': 'all', 'value': 'example_value', 'note': 'Update as needed'}]
        
        return examples
    
    def generate_markdown(self) -> str:
        """Generate Markdown documentation."""
        doc = []
        
        # Header
        doc.append("# Configuration Documentation")
        doc.append("")
        doc.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc.append(f"Configuration Class: `{self.config_class.__name__}`")
        doc.append("")
        
        # Table of Contents
        doc.append("## Table of Contents")
        doc.append("")
        
        # Group fields by category
        categories = self._categorize_fields()
        
        for category in categories:
            doc.append(f"- [{category['name']}](#{category['name'].lower().replace(' ', '-')})")
        
        doc.append("- [Environment-Specific Guidelines](#environment-specific-guidelines)")
        doc.append("- [Security Best Practices](#security-best-practices)")
        doc.append("- [Validation Rules](#validation-rules)")
        doc.append("")
        
        # Generate sections for each category
        for category in categories:
            doc.append(f"## {category['name']}")
            doc.append("")
            doc.append(category['description'])
            doc.append("")
            
            # Create table
            doc.append("| Variable | Type | Required | Description | Default |")
            doc.append("|----------|------|----------|-------------|---------|")
            
            for field_info in category['fields']:
                required = "✅" if field_info['required'] else "❌"
                default = str(field_info['default']) if field_info['default'] is not None else "-"
                if len(default) > 30:
                    default = default[:27] + "..."
                
                doc.append(f"| `{field_info['name']}` | {field_info['type']} | {required} | {field_info['description']} | `{default}` |")
            
            doc.append("")
            
            # Detailed field documentation
            for field_info in category['fields']:
                doc.append(f"### `{field_info['name']}`")
                doc.append("")
                doc.append(f"**Type:** {field_info['type']}")
                doc.append(f"**Required:** {'Yes' if field_info['required'] else 'No'}")
                doc.append(f"**Security Level:** {field_info['security_level'].title()}")
                doc.append("")
                
                if field_info['description']:
                    doc.append(f"**Description:** {field_info['description']}")
                    doc.append("")
                
                if field_info['validators']:
                    doc.append("**Validation Rules:**")
                    for validator in field_info['validators']:
                        doc.append(f"- {validator}")
                    doc.append("")
                
                # Examples
                doc.append("**Examples:**")
                doc.append("")
                for example in field_info['examples']:
                    env = example['environment']
                    value = example['value']
                    note = example['note']
                    
                    if field_info['security_level'] == 'sensitive' and value != 'dev-secret-key-change-in-production':
                        value = '********'
                    
                    doc.append(f"- **{env.title()}:** `{value}` - {note}")
                
                doc.append("")
                doc.append("---")
                doc.append("")
        
        # Environment-specific guidelines
        doc.extend(self._generate_environment_guidelines())
        
        # Security best practices
        doc.extend(self._generate_security_guidelines())
        
        # Validation rules
        doc.extend(self._generate_validation_documentation())
        
        return "\n".join(doc)
    
    def _categorize_fields(self) -> List[Dict[str, Any]]:
        """Categorize configuration fields by their purpose."""
        categories = {
            'Application Settings': {
                'description': 'Basic application configuration and metadata.',
                'patterns': ['app_', 'environment', 'debug', 'version'],
                'fields': []
            },
            'Server Configuration': {
                'description': 'HTTP server and network configuration.',
                'patterns': ['host', 'port', 'reload', 'cors_'],
                'fields': []
            },
            'Database Settings': {
                'description': 'Database connection and configuration options.',
                'patterns': ['db_', 'database_url'],
                'fields': []
            },
            'Security Configuration': {
                'description': 'Authentication, authorization, and security settings.',
                'patterns': ['secret', 'jwt_', 'password_', 'session_', 'csrf_', 'lockout_'],
                'fields': []
            },
            'External Services': {
                'description': 'Third-party service integrations and API configurations.',
                'patterns': ['supabase_', 'openai_', 'redis_', 'smtp_', 'oauth_'],
                'fields': []
            },
            'Rate Limiting': {
                'description': 'Rate limiting and throttling configuration.',
                'patterns': ['rate_limit', 'login_rate', 'password_reset_rate', 'registration_rate'],
                'fields': []
            },
            'Logging and Monitoring': {
                'description': 'Logging, monitoring, and observability settings.',
                'patterns': ['log_', 'sentry_'],
                'fields': []
            },
            'Other Settings': {
                'description': 'Miscellaneous configuration options.',
                'patterns': [],
                'fields': []
            }
        }
        
        # Get all field info
        all_fields = []
        for field_name in self.schema.get('properties', {}):
            all_fields.append(self._get_field_info(field_name))
        
        # Categorize fields
        for field_info in all_fields:
            categorized = False
            field_name_lower = field_info['name'].lower()
            
            for category_name, category_info in categories.items():
                if category_name == 'Other Settings':
                    continue
                
                for pattern in category_info['patterns']:
                    if pattern in field_name_lower:
                        category_info['fields'].append(field_info)
                        categorized = True
                        break
                
                if categorized:
                    break
            
            if not categorized:
                categories['Other Settings']['fields'].append(field_info)
        
        # Convert to list and filter empty categories
        result = []
        for name, info in categories.items():
            if info['fields']:
                result.append({
                    'name': name,
                    'description': info['description'],
                    'fields': sorted(info['fields'], key=lambda x: x['name'])
                })
        
        return result
    
    def _generate_environment_guidelines(self) -> List[str]:
        """Generate environment-specific configuration guidelines."""
        doc = []
        
        doc.append("## Environment-Specific Guidelines")
        doc.append("")
        doc.append("Different environments have different security and performance requirements.")
        doc.append("")
        
        environments = {
            'Development': {
                'purpose': 'Local development and testing',
                'guidelines': [
                    'DEBUG=true for detailed error messages',
                    'Use SQLite database (DATABASE_URL not required)',
                    'Relaxed security settings for ease of development',
                    'Use localhost URLs for all services',
                    'Email verification can be disabled',
                    'Rate limiting can be relaxed',
                    'Use development API keys (not production secrets)'
                ]
            },
            'Staging': {
                'purpose': 'Pre-production testing and validation',
                'guidelines': [
                    'DEBUG=false to match production behavior',
                    'Use production-like PostgreSQL database',
                    'Moderate security settings',
                    'Use staging URLs and API keys',
                    'Enable email verification',
                    'Test OAuth integrations',
                    'Monitor performance and logs'
                ]
            },
            'Production': {
                'purpose': 'Live application serving real users',
                'guidelines': [
                    'DEBUG=false (CRITICAL - never enable in production)',
                    'Strong SECRET_KEY (minimum 32 characters)',
                    'PostgreSQL database required',
                    'All URLs must use HTTPS',
                    'Email verification enabled',
                    'Strong password policies enforced',
                    'Rate limiting enabled',
                    'All OAuth providers configured',
                    'Comprehensive logging enabled',
                    'Regular security audits'
                ]
            }
        }
        
        for env_name, env_info in environments.items():
            doc.append(f"### {env_name} Environment")
            doc.append("")
            doc.append(f"**Purpose:** {env_info['purpose']}")
            doc.append("")
            doc.append("**Configuration Guidelines:**")
            for guideline in env_info['guidelines']:
                doc.append(f"- {guideline}")
            doc.append("")
        
        return doc
    
    def _generate_security_guidelines(self) -> List[str]:
        """Generate security best practices documentation."""
        doc = []
        
        doc.append("## Security Best Practices")
        doc.append("")
        
        sections = {
            'Secret Management': [
                'Never commit .env files or secrets to version control',
                'Use environment variables or secure vaults for all secrets',
                'Rotate secrets regularly (every 90 days minimum)',
                'Use different secrets for each environment',
                'Generate cryptographically secure random secrets (min 32 chars)',
                'Audit secret access and changes'
            ],
            'Database Security': [
                'Use dedicated database users with minimal privileges',
                'Enable database encryption at rest and in transit',
                'Regular database backups with encryption',
                'Monitor database access logs',
                'Use connection pooling with limits',
                'Validate all database inputs'
            ],
            'Network Security': [
                'Use HTTPS for all production traffic',
                'Configure proper CORS origins',
                'Implement rate limiting on all endpoints',
                'Use secure headers (HSTS, CSP, etc.)',
                'Monitor for suspicious traffic patterns',
                'Regular security scans and penetration testing'
            ],
            'Authentication & Authorization': [
                'Enforce strong password policies',
                'Implement multi-factor authentication',
                'Use secure session management',
                'Regular access reviews and cleanup',
                'Monitor failed authentication attempts',
                'Implement account lockout mechanisms'
            ]
        }
        
        for section_name, practices in sections.items():
            doc.append(f"### {section_name}")
            doc.append("")
            for practice in practices:
                doc.append(f"- {practice}")
            doc.append("")
        
        return doc
    
    def _generate_validation_documentation(self) -> List[str]:
        """Generate validation rules documentation."""
        doc = []
        
        doc.append("## Validation Rules")
        doc.append("")
        doc.append("The configuration system includes comprehensive validation to ensure security and correctness.")
        doc.append("")
        
        doc.append("### Automatic Validation")
        doc.append("")
        doc.append("The following validations are applied automatically:")
        doc.append("")
        doc.append("- **Type validation:** All values must match their declared types")
        doc.append("- **Required fields:** Missing required fields will cause startup failure")
        doc.append("- **Format validation:** URLs, emails, and other formats are validated")
        doc.append("- **Security validation:** Production environments have stricter requirements")
        doc.append("- **Cross-field validation:** Some fields are validated against others")
        doc.append("")
        
        doc.append("### Environment-Specific Validation")
        doc.append("")
        doc.append("| Validation | Development | Staging | Production |")
        doc.append("|------------|-------------|---------|------------|")
        doc.append("| DEBUG must be false | ❌ | ✅ | ✅ |")
        doc.append("| HTTPS required | ❌ | ✅ | ✅ |")
        doc.append("| Strong SECRET_KEY | ❌ | ✅ | ✅ |")
        doc.append("| Email verification | ❌ | ⚠️ | ✅ |")
        doc.append("| PostgreSQL required | ❌ | ✅ | ✅ |")
        doc.append("| Rate limiting | ❌ | ✅ | ✅ |")
        doc.append("")
        doc.append("Legend: ✅ Required, ⚠️ Recommended, ❌ Optional")
        doc.append("")
        
        return doc
    
    def generate_json(self) -> Dict[str, Any]:
        """Generate JSON documentation."""
        categories = self._categorize_fields()
        
        return {
            'generated_at': datetime.now().isoformat(),
            'config_class': self.config_class.__name__,
            'schema': self.schema,
            'categories': categories,
            'total_fields': len(self.schema.get('properties', {})),
            'required_fields': len(self.schema.get('required', [])),
            'optional_fields': len(self.schema.get('properties', {})) - len(self.schema.get('required', []))
        }
    
    def generate_html(self) -> str:
        """Generate HTML documentation."""
        markdown_content = self.generate_markdown()
        
        # Simple markdown to HTML conversion
        html_content = markdown_content
        html_content = html_content.replace('# ', '<h1>').replace('\n', '</h1>\n', 1)
        html_content = html_content.replace('## ', '<h2>').replace('\n', '</h2>\n')
        html_content = html_content.replace('### ', '<h3>').replace('\n', '</h3>\n')
        
        # Wrap in basic HTML structure
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configuration Documentation</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        .toc {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
        .security {{ background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 10px 0; }}
        .warning {{ background-color: #f8d7da; padding: 10px; border-left: 4px solid #dc3545; margin: 10px 0; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
        
        return html


def main():
    """Main function to generate configuration documentation."""
    parser = argparse.ArgumentParser(description='Generate configuration documentation')
    parser.add_argument('--output-dir', '-o', default='docs/generated', 
                       help='Output directory for documentation files')
    parser.add_argument('--format', '-f', choices=['markdown', 'html', 'json', 'all'], 
                       default='all', help='Output format')
    parser.add_argument('--config-class', '-c', default='Settings',
                       help='Configuration class name to document')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔧 Generating configuration documentation...")
    print(f"📂 Output directory: {output_dir}")
    print(f"📝 Format: {args.format}")
    print("")
    
    try:
        # Get configuration class
        if args.config_class == 'Settings':
            config_class = Settings
        else:
            # Try to import custom class
            module = __import__('app.core.config', fromlist=[args.config_class])
            config_class = getattr(module, args.config_class)
        
        # Generate documentation
        generator = ConfigDocGenerator(config_class)
        
        # Generate requested formats
        if args.format in ['markdown', 'all']:
            print("📄 Generating Markdown documentation...")
            markdown_content = generator.generate_markdown()
            markdown_file = output_dir / 'configuration.md'
            markdown_file.write_text(markdown_content, encoding='utf-8')
            print(f"✅ Markdown documentation saved to: {markdown_file}")
        
        if args.format in ['html', 'all']:
            print("🌐 Generating HTML documentation...")
            html_content = generator.generate_html()
            html_file = output_dir / 'configuration.html'
            html_file.write_text(html_content, encoding='utf-8')
            print(f"✅ HTML documentation saved to: {html_file}")
        
        if args.format in ['json', 'all']:
            print("📊 Generating JSON documentation...")
            json_content = generator.generate_json()
            json_file = output_dir / 'configuration.json'
            json_file.write_text(json.dumps(json_content, indent=2), encoding='utf-8')
            print(f"✅ JSON documentation saved to: {json_file}")
        
        print("")
        print("🎉 Documentation generation completed successfully!")
        print("")
        print("📖 View your documentation:")
        if args.format in ['markdown', 'all']:
            print(f"   Markdown: {markdown_file}")
        if args.format in ['html', 'all']:
            print(f"   HTML: {html_file}")
        if args.format in ['json', 'all']:
            print(f"   JSON: {json_file}")
        
    except Exception as e:
        print(f"❌ Error generating documentation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())