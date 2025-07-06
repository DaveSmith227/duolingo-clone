#!/usr/bin/env python3
"""
Demo script to demonstrate the configuration security system in action.

Shows RBAC, audit logging, and validation working together.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock

from app.core.config_rbac import ConfigRole, get_config_rbac, ConfigPermission
from app.core.audit_logger import configure_audit_logger, get_audit_logger, set_audit_context, clear_audit_context
from app.services.config_access_service import ConfigAccessService


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def demonstrate_rbac():
    """Demonstrate role-based access control."""
    print_section("Role-Based Access Control Demo")
    
    # Set up service
    service = ConfigAccessService()
    rbac = get_config_rbac()
    
    # Create different users
    users = {
        "viewer": Mock(id="viewer123", email="viewer@example.com", role="user", 
                      is_admin=False, is_super_admin=False),
        "developer": Mock(id="dev123", email="dev@example.com", role="developer",
                         is_admin=False, is_super_admin=False),
        "admin": Mock(id="admin123", email="admin@example.com", role="admin",
                     is_admin=True, is_super_admin=False)
    }
    
    # Assign roles
    rbac.assign_role(users["viewer"].id, ConfigRole.VIEWER.value)
    rbac.assign_role(users["developer"].id, ConfigRole.DEVELOPER.value)
    rbac.assign_role(users["admin"].id, ConfigRole.ADMIN.value)
    
    # Test access for each user
    for user_type, user in users.items():
        print(f"\n{user_type.upper()} ({user.email}):")
        print("-" * 40)
        
        # Try to read different fields
        fields_to_test = ["app_name", "debug", "jwt_secret"]
        for field in fields_to_test:
            try:
                # Mock the actual read since we don't have real config
                if rbac.check_field_access(user.id, field, ConfigPermission.READ, "development"):
                    print(f"  ✅ Can read '{field}'")
                else:
                    print(f"  ❌ Cannot read '{field}'")
            except:
                print(f"  ❌ Cannot read '{field}'")
        
        # Try to write
        try:
            if rbac.check_field_access(user.id, "debug", ConfigPermission.WRITE, "development"):
                print(f"  ✅ Can write to 'debug'")
            else:
                print(f"  ❌ Cannot write to 'debug'")
        except:
            print(f"  ❌ Cannot write to 'debug'")
        
        # Check export permission
        if rbac.check_permission(user.id, ConfigPermission.EXPORT):
            print(f"  ✅ Has export permission")
        else:
            print(f"  ❌ No export permission")


def demonstrate_audit_logging():
    """Demonstrate audit logging capabilities."""
    print_section("Audit Logging Demo")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Configure audit logger
        configure_audit_logger(log_dir=Path(tmpdir), enable_console=True)
        audit_logger = get_audit_logger()
        
        # Set audit context
        set_audit_context(
            user_id="demo_user",
            user_email="demo@example.com",
            ip_address="192.168.1.100",
            request_id="demo_request_123"
        )
        
        # Log various events
        print("Logging configuration events...")
        
        # Successful read
        audit_logger.log_config_read(
            field_name="app_name",
            value="Demo App",
            success=True
        )
        print("  ✅ Logged successful read of 'app_name'")
        
        # Failed read (sensitive field)
        audit_logger.log_config_read(
            field_name="jwt_secret",
            value=None,
            success=False,
            error_message="Access denied: insufficient permissions"
        )
        print("  ❌ Logged failed read of 'jwt_secret'")
        
        # Configuration change
        audit_logger.log_config_write(
            field_name="debug",
            old_value=True,
            new_value=False,
            success=True
        )
        print("  ✅ Logged configuration change for 'debug'")
        
        # Access denied event
        audit_logger.log_access_denied(
            action="write",
            resource="production_config",
            reason="User is not admin in production environment"
        )
        print("  🚫 Logged access denied event")
        
        clear_audit_context()
        
        # Query logs
        print("\nQuerying audit logs...")
        logs = audit_logger.query_logs(
            start_date=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        )
        
        print(f"  Found {len(logs)} audit events today")
        
        # Get summary
        summary = audit_logger.get_audit_summary()
        print(f"\nAudit Summary:")
        print(f"  Total events: {summary['total_events']}")
        print(f"  Failed operations: {summary['failed_operations']}")
        print(f"  Unique users: {summary['unique_users']}")


def demonstrate_security_validation():
    """Demonstrate security validation features."""
    print_section("Security Validation Demo")
    
    # Test secret detection
    print("Testing secret detection patterns...")
    
    test_strings = [
        ('api_key = "sk-1234567890abcdef1234567890abcdef"', True, "OpenAI API key"),
        ('password = "mysecretpassword123"', True, "Password"),
        ('db_url = "postgresql://user:pass123@localhost/db"', True, "Connection string"),
        ('api_key = os.environ["API_KEY"]', False, "Environment variable"),
        ('# Example: api_key = "test-key"', False, "Comment"),
    ]
    
    sys.path.insert(0, str(Path(__file__).parent))
    from detect_secrets import SecretDetector
    
    detector = SecretDetector()
    
    for test_str, should_detect, description in test_strings:
        results = detector.scan_line(test_str, 1, "test.py")
        detected = len(results) > 0
        
        if detected == should_detect:
            status = "✅ Correctly"
        else:
            status = "❌ Incorrectly"
        
        action = "detected" if detected else "ignored"
        print(f"  {status} {action}: {description}")
        print(f"    Line: {test_str[:50]}...")


def demonstrate_permission_matrix():
    """Show permission matrix for different roles."""
    print_section("Permission Matrix")
    
    rbac = get_config_rbac()
    
    # Create header
    roles = [ConfigRole.VIEWER, ConfigRole.OPERATOR, ConfigRole.DEVELOPER, 
             ConfigRole.ADMIN, ConfigRole.SECURITY_ADMIN, ConfigRole.SUPER_ADMIN]
    permissions = [ConfigPermission.READ, ConfigPermission.WRITE, 
                   ConfigPermission.EXPORT, ConfigPermission.ROTATE, 
                   ConfigPermission.AUDIT_VIEW]
    
    # Print matrix header
    print(f"{'Role':<15} | ", end="")
    for perm in permissions:
        print(f"{perm.value:<10}", end=" | ")
    print()
    print("-" * 80)
    
    # Print each role's permissions
    for role in roles:
        # Create a test user with this role
        test_user = f"test_{role.value}"
        rbac.assign_role(test_user, role.value)
        
        print(f"{role.value:<15} | ", end="")
        for perm in permissions:
            has_perm = rbac.check_permission(test_user, perm)
            symbol = "✅" if has_perm else "❌"
            print(f"{symbol:<10}", end=" | ")
        print()


def demonstrate_environment_restrictions():
    """Show how permissions change by environment."""
    print_section("Environment-Based Permissions")
    
    rbac = get_config_rbac()
    developer_id = "dev_test"
    rbac.assign_role(developer_id, ConfigRole.DEVELOPER.value)
    
    environments = ["development", "staging", "production"]
    test_fields = ["debug", "jwt_secret", "app_name"]
    
    print(f"Developer permissions across environments:\n")
    
    # Print header
    print(f"{'Field':<15} | ", end="")
    for env in environments:
        print(f"{env:<12}", end=" | ")
    print()
    print("-" * 60)
    
    # Check each field in each environment
    for field in test_fields:
        print(f"{field:<15} | ", end="")
        for env in environments:
            can_read = rbac.check_field_access(developer_id, field, ConfigPermission.READ, env)
            can_write = rbac.check_field_access(developer_id, field, ConfigPermission.WRITE, env)
            
            if can_write:
                symbol = "📝"  # Read/Write
            elif can_read:
                symbol = "👁️"   # Read only
            else:
                symbol = "🚫"  # No access
            
            print(f"{symbol:<12}", end=" | ")
        print()


def main():
    """Run all demonstrations."""
    print("\n🔐 Configuration Security System Demo")
    print("=" * 60)
    
    demonstrate_rbac()
    demonstrate_audit_logging()
    demonstrate_security_validation()
    demonstrate_permission_matrix()
    demonstrate_environment_restrictions()
    
    print_section("Demo Complete")
    print("The configuration security system provides:")
    print("  • Role-based access control with field-level permissions")
    print("  • Complete audit trail of all configuration access")
    print("  • Secret detection to prevent accidental commits")
    print("  • Environment-aware permission rules")
    print("  • Security validation and monitoring capabilities")
    print()


if __name__ == "__main__":
    main()