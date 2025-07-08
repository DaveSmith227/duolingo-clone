# Security Implementation Guide

This file provides guidance for Claude Code when working with security features across the codebase.

## Quick Links
- Main overview: [`/CLAUDE.md`](/CLAUDE.md)
- Backend security: [`/backend/CLAUDE.md`](/backend/CLAUDE.md#security-best-practices)
- Security assessments: [`/docs/security/`](/docs/security/)

## Security Architecture Overview

### Multi-Layer Security Model
1. **Authentication Layer**: Supabase Auth with JWT
2. **Authorization Layer**: Role-Based Access Control (RBAC)
3. **Data Protection Layer**: Field-level encryption
4. **Session Layer**: Secure session management
5. **Audit Layer**: Comprehensive logging
6. **Network Layer**: Rate limiting and sanitization

## Authentication System

### Multi-Factor Authentication (MFA)
```python
# Backend implementation
from app.services.mfa_service import MFAService

# Enable MFA for user
await mfa_service.enable_mfa(user_id, method="totp")

# Verify MFA token
is_valid = await mfa_service.verify_token(user_id, token)
```

### Password Security
- **Algorithm**: Argon2 (winner of Password Hashing Competition)
- **Requirements**: 
  - Minimum 8 characters
  - At least one uppercase, lowercase, number, special character
  - Not in common passwords list
  - No user info (email, name)

```python
# Password validation
from app.services.password_security import PasswordSecurityService

strength = password_service.check_strength(password)
is_valid = password_service.validate_requirements(password, user_context)
```

### Session Management
```python
# Secure session configuration
SESSION_CONFIG = {
    "lifetime": 3600,  # 1 hour
    "refresh_window": 300,  # 5 minutes
    "max_sessions_per_user": 5,
    "remember_me_duration": 2592000,  # 30 days
    "secure_cookie": True,
    "httponly": True,
    "samesite": "strict"
}
```

## Authorization (RBAC)

### Role Hierarchy
```
SUPER_ADMIN
    ↓
  ADMIN
    ↓
MODERATOR
    ↓
  USER
```

### Permission System
```python
# Permission checking
from app.services.rbac import check_permission

@requires_permission("users:write")
async def update_user(user_id: int):
    # Only users with 'users:write' permission
    pass

# Dynamic permission checking
can_edit = await check_permission(
    user_id=current_user.id,
    resource="lesson",
    action="edit",
    resource_id=lesson_id
)
```

### Access Control Lists
```python
# Define resource permissions
PERMISSIONS = {
    "admin_dashboard": ["ADMIN", "SUPER_ADMIN"],
    "user_management": ["ADMIN", "SUPER_ADMIN"],
    "content_moderation": ["MODERATOR", "ADMIN", "SUPER_ADMIN"],
    "audit_logs": ["SUPER_ADMIN"]
}
```

## Data Protection

### Field-Level Encryption
```python
# Automatic encryption for sensitive fields
class User(Base):
    email = Column(EncryptedType(String))  # Encrypted
    phone_number = Column(EncryptedType(String))  # Encrypted
    name = Column(String)  # Not encrypted
```

### Encryption Service
```python
# Manual encryption when needed
from app.services.encryption_service import EncryptionService

encrypted = encryption_service.encrypt_field(sensitive_data)
decrypted = encryption_service.decrypt_field(encrypted_data)
```

### Key Management
- **Master Key**: Stored in environment variable
- **Key Rotation**: Quarterly rotation schedule
- **Key Derivation**: Per-field keys derived from master
- **Backup**: Encrypted key backup in secure storage

## Security Middleware

### Input Sanitization
```python
# Automatic XSS and SQL injection prevention
from app.middleware.sanitization import SanitizationMiddleware

# Applied to all requests automatically
# Sanitizes: query params, body, headers
```

### Rate Limiting
```python
# Endpoint-specific rate limits
from app.middleware.rate_limiting import RateLimiter

@router.post("/login")
@RateLimiter(max_calls=5, time_window=300)  # 5 attempts per 5 minutes
async def login():
    pass

@router.post("/api/expensive-operation")
@RateLimiter(max_calls=10, time_window=3600)  # 10 per hour
async def expensive_operation():
    pass
```

### Security Headers
```python
# Automatically applied headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}
```

## Account Security

### Account Lockout
```python
# Progressive lockout strategy
LOCKOUT_CONFIG = {
    "attempts_before_lockout": 5,
    "lockout_duration_minutes": [5, 15, 30, 60, 120],  # Progressive
    "detection_methods": [
        "ip_address",
        "user_agent",
        "device_fingerprint"
    ]
}
```

### Password Reset Security
1. Token expires in 15 minutes
2. One-time use only
3. Invalidates all sessions on reset
4. Notification sent to user
5. Rate limited to 3 requests per hour

### Account Recovery
```python
# Multi-step verification
recovery_steps = [
    "verify_email",
    "security_questions",
    "backup_code",
    "admin_verification"  # Last resort
]
```

## Audit Logging

### What Gets Logged
```python
AUDIT_EVENTS = [
    # Authentication
    "login_success", "login_failure", "logout",
    "password_change", "password_reset",
    
    # Authorization
    "permission_granted", "permission_denied",
    "role_assigned", "role_removed",
    
    # Data Access
    "sensitive_data_accessed", "bulk_export",
    "admin_action", "user_deletion",
    
    # Security Events
    "mfa_enabled", "mfa_disabled",
    "account_locked", "suspicious_activity"
]
```

### Audit Log Structure
```python
{
    "timestamp": "2024-01-15T10:30:00Z",
    "user_id": 123,
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "event_type": "login_success",
    "resource": "auth",
    "details": {
        "method": "password",
        "mfa_used": true
    },
    "risk_score": 0.2
}
```

### Log Retention
- **Standard Events**: 90 days
- **Security Events**: 1 year
- **Compliance Events**: 7 years
- **Daily rotation with compression**

## GDPR Compliance

### Data Subject Rights
```python
# Right to Access
user_data = await gdpr_service.export_user_data(user_id)

# Right to Erasure
await gdpr_service.delete_user_data(user_id, reason="user_request")

# Right to Rectification
await gdpr_service.update_user_data(user_id, corrections)

# Right to Portability
export_file = await gdpr_service.generate_portable_export(user_id)
```

### Data Retention
```python
RETENTION_POLICIES = {
    "user_profiles": 365 * 2,  # 2 years after last activity
    "learning_data": 365 * 3,  # 3 years
    "payment_data": 365 * 7,   # 7 years (legal requirement)
    "audit_logs": 365 * 1,     # 1 year
    "temp_data": 30           # 30 days
}
```

### Consent Management
```python
# Track consent
await consent_service.record_consent(
    user_id=user_id,
    consent_type="marketing",
    granted=True,
    ip_address=request.client.host
)

# Check consent
has_consent = await consent_service.check_consent(
    user_id=user_id,
    consent_type="analytics"
)
```

## Security Testing

### Penetration Testing Checklist
- [ ] SQL Injection
- [ ] XSS (Stored and Reflected)
- [ ] CSRF
- [ ] Authentication Bypass
- [ ] Authorization Flaws
- [ ] Session Hijacking
- [ ] Insecure Direct Object References
- [ ] Security Misconfiguration
- [ ] Sensitive Data Exposure
- [ ] API Security

### Security Test Examples
```python
# Test SQL injection protection
def test_sql_injection_prevention():
    malicious_input = "'; DROP TABLE users; --"
    response = client.post("/api/search", json={"query": malicious_input})
    assert response.status_code == 200
    # Verify tables still exist

# Test XSS protection
def test_xss_prevention():
    xss_payload = "<script>alert('XSS')</script>"
    response = client.post("/api/comment", json={"text": xss_payload})
    # Verify sanitized in response
    assert "<script>" not in response.json()["text"]
```

## Incident Response

### Security Incident Procedure
1. **Detect**: Automated alerts or manual discovery
2. **Contain**: Isolate affected systems
3. **Assess**: Determine scope and impact
4. **Notify**: Alert security team and stakeholders
5. **Remediate**: Fix vulnerability
6. **Review**: Post-mortem and improvements

### Emergency Procedures
```python
# Emergency shutdown
await security_service.emergency_shutdown(reason="breach_detected")

# Force logout all users
await session_service.invalidate_all_sessions()

# Disable specific features
await feature_flags.disable("payment_processing")
```

## Security Monitoring

### Real-time Alerts
```python
ALERT_THRESHOLDS = {
    "failed_logins": {"count": 10, "window": 300},  # 10 in 5 min
    "api_errors": {"rate": 0.05},  # 5% error rate
    "new_admin_access": {"immediate": True},
    "bulk_data_export": {"rows": 1000},
    "permission_escalation": {"immediate": True}
}
```

### Security Metrics
- Failed login attempts
- Account lockouts
- Permission denials
- API rate limit hits
- Encryption/decryption operations
- Audit log volume
- Security header compliance

## Development Security Guidelines

### Secret Management
```bash
# ❌ DON'T: Hardcode secrets
API_KEY = "sk_live_abcd1234"

# ✅ DO: Use environment variables
API_KEY = os.getenv("API_KEY")

# ✅ DO: Use secret detection
python scripts/detect_secrets.py
```

### Secure Coding Practices
1. **Input Validation**: Always validate and sanitize
2. **Output Encoding**: Encode data for the context
3. **Authentication**: Verify identity on every request
4. **Authorization**: Check permissions for resources
5. **Cryptography**: Use established libraries
6. **Error Handling**: Don't expose sensitive info
7. **Logging**: Log security events, not passwords

### Security Review Checklist
- [ ] No hardcoded secrets
- [ ] Input validation implemented
- [ ] Authentication required
- [ ] Authorization checks in place
- [ ] Sensitive data encrypted
- [ ] Rate limiting configured
- [ ] Audit logging added
- [ ] Error messages sanitized
- [ ] Security headers set
- [ ] Tests include security cases

## Important Security Reminders

- **NEVER** store passwords in plain text
- **ALWAYS** use parameterized queries
- **NEVER** trust user input
- **ALWAYS** validate on the server side
- **NEVER** expose internal errors to users
- **ALWAYS** use HTTPS in production
- **NEVER** log sensitive data
- **ALWAYS** keep dependencies updated