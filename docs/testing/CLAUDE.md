# Testing Strategy Guide

This file provides guidance for Claude Code when working with tests across the codebase.

## Quick Links
- Main overview: [`/CLAUDE.md`](/CLAUDE.md)
- Backend guide: [`/backend/CLAUDE.md`](/backend/CLAUDE.md)
- Frontend guide: [`/frontend/CLAUDE.md`](/frontend/CLAUDE.md)
- Memory optimization: [`/docs/design-system/testing-memory-optimization.md`](/docs/design-system/testing-memory-optimization.md)

## Test Organization Overview

### Backend Tests (57 test files)
- **Framework**: pytest
- **Location**: `/backend/app/` (co-located with source)
- **Naming**: `test_*.py` convention
- **Coverage**: 90%+ target

### Frontend Tests (51 test files)
- **Framework**: Vitest + React Testing Library
- **Location**: Co-located with components
- **Naming**: `*.test.ts(x)` convention
- **Coverage**: 80%+ target

### Integration Tests (200+ design system tests)
- **Framework**: Vitest with specialized configs
- **Location**: `integration.test.ts` files
- **Purpose**: End-to-end validation

## Frontend Testing Configuration

### Vitest Configuration Files

#### Base Configuration (`vitest.config.base.ts`)
```javascript
// Shared settings for all test types
- Memory optimization: 512MB per worker
- Garbage collection enabled
- Reporter configuration
```

#### Unit Tests (`vitest.config.unit.ts`)
```javascript
// For non-DOM tests
- Environment: 'node'
- Pool: 'vmThreads'
- Fast execution
```

#### DOM Tests (`vitest.config.dom.ts`)
```javascript
// For component tests
- Environment: 'jsdom'
- Pool: 'forks' (single execution)
- Setup file for DOM utilities
```

#### Design System Tests (`vitest.config.design-system.ts`)
```javascript
// For design system tests
- Extreme memory optimization
- Single file execution
- No coverage collection
```

### Running Frontend Tests
```bash
# All tests
npm run test

# Specific test types
npm run test:unit         # Unit tests only
npm run test:components   # Component tests
npm run test:integration  # Integration tests
npm run test:coverage     # With coverage report
npm run test:ui           # Vitest UI mode

# Design system specific
npm run test:design-system
npm run test:design-system:unit
npm run test:design-system:integration
```

## Backend Testing Patterns

### Test Structure
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestFeatureName:
    """Group related tests in classes"""
    
    @pytest.fixture
    def setup_data(self, db_session):
        """Setup test data"""
        # Create test data
        yield data
        # Cleanup
    
    def test_feature_behavior(self, setup_data):
        """Test specific behavior"""
        # Arrange
        data = setup_data
        
        # Act
        response = client.post("/api/endpoint", json=data)
        
        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True
```

### Common Fixtures
```python
# Database session
@pytest.fixture
def db_session():
    """Provide test database session"""
    from app.core.database import TestSessionLocal
    session = TestSessionLocal()
    yield session
    session.rollback()
    session.close()

# Authenticated client
@pytest.fixture
def auth_client(client, test_user):
    """Client with authentication"""
    token = create_test_token(test_user)
    client.headers["Authorization"] = f"Bearer {token}"
    return client

# Mock services
@pytest.fixture
def mock_email_service(monkeypatch):
    """Mock email sending"""
    mock = Mock()
    monkeypatch.setattr("app.services.email_service.send_email", mock)
    return mock
```

### Running Backend Tests
```bash
# All tests
pytest

# Specific file or directory
pytest app/api/test_auth.py
pytest app/tests/

# With coverage
pytest --cov=app --cov-report=html

# Specific test pattern
pytest -k "test_login"

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

## Frontend Testing Patterns

### Component Testing
```typescript
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

// Mock dependencies
vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    user: null,
    login: vi.fn(),
    logout: vi.fn()
  })
}))

describe('LoginForm', () => {
  it('should handle form submission', async () => {
    // Arrange
    const user = userEvent.setup()
    render(<LoginForm />)
    
    // Act
    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Log in' }))
    
    // Assert
    await waitFor(() => {
      expect(screen.getByText('Welcome back!')).toBeInTheDocument()
    })
  })
})
```

### Hook Testing
```typescript
import { renderHook, act } from '@testing-library/react'
import { useAuth } from '@/hooks/useAuth'

describe('useAuth', () => {
  it('should handle login flow', async () => {
    const { result } = renderHook(() => useAuth())
    
    expect(result.current.isAuthenticated).toBe(false)
    
    await act(async () => {
      await result.current.login({
        email: 'test@example.com',
        password: 'password123'
      })
    })
    
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user).toBeDefined()
  })
})
```

### API Mocking
```typescript
import { rest } from 'msw'
import { setupServer } from 'msw/node'

const server = setupServer(
  rest.post('/api/auth/login', (req, res, ctx) => {
    return res(
      ctx.json({
        token: 'mock-token',
        user: { id: 1, email: 'test@example.com' }
      })
    )
  })
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

## Memory Optimization

### JavaScript Heap Issues
**Problem**: Tests failing with "JavaScript heap out of memory"

**Solutions Applied**:
1. **Separate Test Configurations**
   - Different configs for unit, DOM, and integration tests
   - Appropriate environments for each test type

2. **Memory Limits**
   ```json
   {
     "scripts": {
       "test": "NODE_OPTIONS='--max-old-space-size=4096' vitest"
     }
   }
   ```

3. **Pool Configuration**
   - vmThreads for unit tests (lightweight)
   - forks for DOM tests (isolated)
   - Single file execution for heavy tests

4. **Garbage Collection**
   ```javascript
   // In test setup
   afterEach(() => {
     if (global.gc) {
       global.gc()
     }
   })
   ```

### Best Practices for Memory-Efficient Tests
1. **Clean Up After Tests**
   ```typescript
   afterEach(() => {
     cleanup() // React Testing Library cleanup
     vi.clearAllMocks()
     vi.resetModules()
   })
   ```

2. **Avoid Memory Leaks**
   ```typescript
   // ❌ DON'T: Leave timers running
   setTimeout(() => {}, 1000)
   
   // ✅ DO: Clear timers
   const timer = setTimeout(() => {}, 1000)
   afterEach(() => clearTimeout(timer))
   ```

3. **Use Appropriate Test Runners**
   ```bash
   # For simple unit tests
   npm run test:unit
   
   # For DOM-heavy tests
   npm run test:components
   
   # For memory-intensive tests
   npm run test:design-system
   ```

## Integration Testing

### Design System Integration Tests
```typescript
describe('Design System Pipeline', () => {
  it('should extract and generate tokens', async () => {
    // Complete pipeline test
    const mockImage = createMockImage()
    const tokens = await extractTokens(mockImage)
    const categorized = await categorizeTokens(tokens)
    const generated = await generateCode(categorized)
    
    expect(generated.typescript).toContain('export const colors')
    expect(generated.tailwind).toContain('extend')
    expect(generated.css).toContain(':root')
  })
})
```

### API Integration Tests
```python
class TestUserFlow:
    """Test complete user journey"""
    
    def test_registration_to_first_lesson(self, client):
        # Register
        register_response = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "password": "SecurePass123!"
        })
        assert register_response.status_code == 201
        
        # Login
        login_response = client.post("/api/auth/login", json={
            "email": "new@example.com",
            "password": "SecurePass123!"
        })
        token = login_response.json()["access_token"]
        
        # Access protected resource
        client.headers["Authorization"] = f"Bearer {token}"
        lesson_response = client.get("/api/lessons/1")
        assert lesson_response.status_code == 200
```

## Test Data Management

### Frontend Test Data
```typescript
// Test data factories
export const createMockUser = (overrides = {}) => ({
  id: 1,
  email: 'test@example.com',
  name: 'Test User',
  role: 'user',
  ...overrides
})

// Use in tests
const adminUser = createMockUser({ role: 'admin' })
```

### Backend Test Data
```python
# Factory pattern
class UserFactory:
    @staticmethod
    def create(**kwargs):
        defaults = {
            "email": "test@example.com",
            "password_hash": "hashed",
            "is_active": True
        }
        return User(**{**defaults, **kwargs})

# Use in tests
admin_user = UserFactory.create(role="admin")
```

## Debugging Failed Tests

### Frontend Debugging
```typescript
// Add debug output
import { debug } from '@testing-library/react'

test('component render', () => {
  const { container } = render(<Component />)
  debug(container) // Prints DOM structure
})

// Increase timeout for async operations
test('async operation', async () => {
  await waitFor(() => {
    expect(element).toBeInTheDocument()
  }, { timeout: 5000 })
})
```

### Backend Debugging
```python
# Print request/response
def test_api_endpoint(client):
    response = client.post("/api/endpoint", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
# Use pytest debugging
pytest --pdb  # Drop into debugger on failure
pytest -s     # Show print statements
```

## CI/CD Test Configuration

### GitHub Actions
```yaml
- name: Backend Tests
  run: |
    cd backend
    pytest --cov=app --cov-report=xml
    
- name: Frontend Tests
  run: |
    cd frontend
    npm run test:coverage
```

### Pre-commit Hooks
```bash
# Run affected tests only
npm run test -- --changed
pytest --testmon
```

## Performance Testing

### Load Testing
```python
# Using locust for API load testing
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def test_endpoint(self):
        self.client.get("/api/health")
```

### Frontend Performance
```typescript
// Measure component render time
import { measureRender } from '@/test/utils'

test('performance', async () => {
  const renderTime = await measureRender(<ExpensiveComponent />)
  expect(renderTime).toBeLessThan(100) // ms
})
```

## Important Testing Rules

- **ALWAYS** clean up after tests (timers, mocks, DOM)
- **NEVER** use real API endpoints in tests
- **ALWAYS** test error cases and edge conditions
- **NEVER** skip flaky tests - fix them
- **ALWAYS** use appropriate test configuration
- **NEVER** commit console.log in tests