# Backend Development Guide

This file provides guidance for Claude Code when working with the backend codebase.

## Quick Links
- Main overview: [`/CLAUDE.md`](/CLAUDE.md)
- Testing guide: [`/docs/testing/CLAUDE.md`](/docs/testing/CLAUDE.md)
- Security guide: [`/docs/security/CLAUDE.md`](/docs/security/CLAUDE.md)

## Configuration Architecture

### Service-Oriented Design
The configuration system uses a service-oriented architecture following Sandi Metz principles:

```python
# ❌ DON'T: Direct settings access
from app.core.config import settings

# ✅ DO: Use ConfigServiceOrchestrator
from app.core.config.orchestrator import get_orchestrator
config = get_orchestrator()
database_url = config.database_dsn
```

### Key Configuration Services
- **ConfigServiceOrchestrator** (`/app/core/config/orchestrator.py`): Central coordinator
- **DatabaseConfigService** (`/app/core/config/database_service.py`): Database configuration
- **SecurityConfigService** (`/app/core/config/security_service.py`): Security settings
- **ConfigValidationService** (`/app/core/config/validation_service.py`): Validation orchestration

### Environment-Specific Validation
- Development: Relaxed security requirements
- Staging: Production-like with debug enabled
- Production: Strict security, no debug

### Configuration Scripts
```bash
python scripts/migrate_config.py      # Migrate between versions
python scripts/generate_config_docs.py # Generate documentation
python scripts/detect_secrets.py      # Scan for secrets
```

## API Architecture

### Modular Authentication Endpoints
Authentication is split into focused modules in `/app/api/auth/`:
- `auth_registration.py` - User registration
- `auth_login.py` - Login and token generation
- `auth_session.py` - Session management
- `auth_password.py` - Password reset/change
- `auth_verification.py` - Email/phone verification
- `auth_gdpr.py` - GDPR compliance endpoints
- `auth_mfa.py` - Multi-factor authentication

### Admin System Endpoints
- `/api/admin/users` - User management
- `/api/admin/analytics` - Dashboard metrics
- `/api/admin/audit` - Audit log viewer
- `/api/admin/bulk` - Bulk operations

### Design System API
- `/api/design-system/extract` - Token extraction
- `/api/design-system/validate` - Visual validation
- `/api/design-system/batch` - Batch processing

## Database Models

### Security-Enhanced Models
- **User** (`/app/models/user_secure.py`): Enhanced with field encryption
- **AuthSession** (`/app/models/auth_session_secure.py`): Session tracking
- **AuditLog** (`/app/models/audit.py`): Comprehensive audit trail
- **Role/Permission** (`/app/models/rbac.py`): RBAC implementation

### Field Encryption
```python
# Encrypted fields automatically handled
user.email  # Encrypted at database level
user.phone_number  # Encrypted at database level
```

## Services Layer

### Critical Services
- **AuthService** (`/app/services/auth_service.py`): Authentication logic
- **SessionManager** (`/app/services/session_manager_secure.py`): Session handling
- **EncryptionService** (`/app/services/encryption_service.py`): Field encryption
- **AuditLogger** (`/app/services/audit_logger.py`): Audit logging
- **AccountLockoutService** (`/app/services/account_lockout.py`): Brute force protection

### Service Patterns
```python
# Dependency injection pattern
class UserService:
    def __init__(self, db: Session, auth_service: AuthService):
        self.db = db
        self.auth = auth_service
```

## Testing Strategy

### Test Organization
- 57 test files following `test_*.py` convention
- Tests mirror source structure
- Comprehensive mocking for external services

### Common Test Patterns
```python
# FastAPI test client
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Database fixture
@pytest.fixture
def db_session():
    # Test database setup
    yield session
    # Cleanup

# Mock services
@patch('app.services.ai_vision_client.ClaudeVisionClient')
def test_with_mock(mock_client):
    mock_client.return_value.analyze_image.return_value = {...}
```

### Running Tests
```bash
pytest                    # All tests
pytest app/tests/         # Specific directory
pytest -k "test_auth"     # Pattern matching
pytest --cov             # With coverage
```

## Common Tasks

### Adding New Endpoints
1. Define Pydantic schema in `/app/schemas/`
2. Create endpoint in `/app/api/`
3. Implement service logic in `/app/services/`
4. Add repository if needed in `/app/repositories/`
5. Write tests following existing patterns

### Database Migrations
```bash
# Create migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Adding Configuration
1. Add to appropriate service (Database/Security/etc)
2. Update validation rules if needed
3. Run `python scripts/generate_config_docs.py`
4. Test with different environments

## Performance Considerations

### Database Optimization
- Use SQLAlchemy query optimization
- Implement proper indexes
- Use pagination for large datasets
- Connection pooling configured

### Caching Strategy
- Redis for session data
- Cache frequently accessed configs
- Implement cache invalidation

### API Performance
- Rate limiting on all endpoints
- Async endpoints where beneficial
- Proper error handling
- Response pagination

## Security Best Practices

### Authentication
- JWT tokens with proper expiration
- Refresh token rotation
- MFA for admin accounts
- Session invalidation on logout

### Data Protection
- Field-level encryption for PII
- Audit logging for compliance
- Input sanitization middleware
- SQL injection protection

### API Security
- Rate limiting per endpoint
- CORS properly configured
- Security headers middleware
- API key validation

## Debugging Tips

### Configuration Issues
```python
# Check current config
config = get_orchestrator()
print(config.model_dump())

# Validate specific service
config.database_service.validate_configuration()
```

### Database Queries
```python
# Enable SQL logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### API Debugging
```python
# Add to endpoint for debugging
import pdb; pdb.set_trace()

# Check request context
from fastapi import Request
async def endpoint(request: Request):
    print(request.headers)
```

## File Structure

```
/backend/
├── app/
│   ├── api/           # API endpoints
│   │   └── auth/      # Modular auth endpoints
│   ├── core/          # Core functionality
│   │   └── config/    # Configuration services
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   ├── repositories/  # Data access layer
│   ├── middleware/    # Request processing
│   └── tests/         # Test files (57+)
├── alembic/           # Database migrations
├── logs/              # Application logs
│   └── audit/         # Audit logs (daily rotation)
├── scripts/           # Utility scripts
└── requirements.txt   # Dependencies
```

## Important Reminders

- **NEVER** access settings directly, use ConfigServiceOrchestrator
- **ALWAYS** validate input through Pydantic schemas
- **NEVER** store secrets in code, use environment variables
- **ALWAYS** write tests for new functionality
- **NEVER** disable security features in production