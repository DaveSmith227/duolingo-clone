# review-tasks

You are given the following context:
$ARGUMENTS

## Code Review and Testing Command

You are tasked with conducting a thorough code review using adapted Sandi Metz principles for complex interactive applications, focusing on object-oriented design principles, code clarity, and maintainability. Additionally, you will test any UI-related changes using Puppeteer.

### Review Approach

Follow adapted Sandi Metz principles for complex interactive applications:

1. **Classes should be reasonably sized** - Look for classes with too many responsibilities (flag >200 lines)
2. **Methods should be focused** - Identify methods that do too much (flag >10 lines, allow complexity for game logic/animations)
3. **Objects should have a single responsibility** - Check for violations of SRP (most important principle)
4. **Depend on abstractions, not concretions** - Look for tight coupling
5. **Code should tell a story** - Assess readability and intention-revealing names
6. **Duplication is far cheaper than the wrong abstraction** - Identify premature abstractions
7. **Allow complexity where justified** - Game logic, media handling, animations, and interactive features may need more complexity

### Review Process

1. **Analyze the requested features** - Understand what was supposed to be built
2. **Review code structure** - Examine overall architecture and organization
3. **Check design patterns** - Look for appropriate use of patterns vs over-engineering
4. **Assess naming** - Ensure names reveal intent and are consistent
5. **Evaluate method and class sizes** - Flag methods >10 lines or classes >200 lines (relaxed for complex UI components and game logic)
6. **Test UI changes** - Use Puppeteer to verify UI functionality works as expected
7. **Provide specific, actionable feedback** - Give concrete suggestions for improvement

### Testing Protocol

For code changes:
1. **Unit Tests** - Write tests for utility functions and isolated components
2. **Integration Tests** - Test component interactions and data flow
3. **UI Tests** - Use Puppeteer to verify:
   - Functionality works as expected
   - UI elements render correctly
   - User interactions behave properly
   - Accessibility considerations
4. **Performance Tests** - Verify refactored code maintains performance
5. **Type Safety** - Run TypeScript compilation to catch type errors
6. **Lint Tests** - Ensure code style consistency

### Test Implementation

Create comprehensive test suites that describe expected behavior:

1. **Describe what the code should do** - Write clear test descriptions
2. **Test edge cases** - Include boundary conditions and error scenarios
3. **Mock dependencies** - Isolate units under test
4. **Verify behavior** - Test outcomes, not implementation details
5. **Performance assertions** - Ensure optimization goals are met

#### Testing Framework Setup

For Next.js 15 projects, establish the following testing environment:

```bash
# Install testing dependencies
npm install --save-dev jest @testing-library/react @testing-library/jest-dom @testing-library/user-event jest-environment-jsdom

# Install Puppeteer for E2E testing
npm install --save-dev puppeteer @types/puppeteer

# Install additional testing utilities
npm install --save-dev @testing-library/react-hooks msw
```

Create `jest.config.js`:
```javascript
const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testEnvironment: 'jest-environment-jsdom',
  collectCoverageFrom: [
    'app/**/*.{js,jsx,ts,tsx}',
    'lib/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
  ],
  testMatch: [
    '**/__tests__/**/*.(js|jsx|ts|tsx)',
    '**/*.(test|spec).(js|jsx|ts|tsx)'
  ]
}

module.exports = createJestConfig(customJestConfig)
```

Create `jest.setup.js`:
```javascript
import '@testing-library/jest-dom'

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      back: jest.fn(),
    }
  },
  useSearchParams() {
    return new URLSearchParams()
  },
  usePathname() {
    return '/'
  }
}))
```

#### Test Structure and Descriptions

**Component Tests** - Describe UI behavior and user interactions (allowing for complex game components):
```javascript
describe('LessonQuestionCard Component', () => {
  it('should render all question types correctly', () => {
    // Test that component renders expected elements
  })
  
  it('should handle audio playback and speech recognition', () => {
    // Test media functionality (complex by nature)
  })
  
  it('should manage game state transitions properly', () => {
    // Test complex state management for interactive features
  })
  
  it('should handle animations and feedback smoothly', () => {
    // Test complex animation sequences
  })
  
  it('should respond to mobile viewport changes', () => {
    // Test responsive design behavior
  })
})
```

**Utility Function Tests** - Describe logic and edge cases (allowing for complex game utilities):
```javascript
describe('calculateXP utility function', () => {
  it('should calculate XP correctly for different question types', () => {
    // Test complex calculation logic with multiple parameters
  })
  
  it('should handle streak multipliers and bonus conditions', () => {
    // Test complex game logic with multiple inputs
  })
  
  it('should return appropriate values for edge cases', () => {
    // Test boundary conditions with complex parameters
  })
})
```

**Integration Tests** - Describe user workflows:
```javascript
describe('User Authentication Flow', () => {
  it('should complete login process successfully', () => {
    // Test complete user journey
  })
  
  it('should handle authentication errors gracefully', () => {
    // Test error states and recovery
  })
  
  it('should maintain session state across page transitions', () => {
    // Test state persistence
  })
})
```

**Performance Tests** - Describe optimization goals:
```javascript
describe('Page Load Performance', () => {
  it('should load homepage within 2 seconds', () => {
    // Test Core Web Vitals metrics
  })
  
  it('should lazy load components below the fold', () => {
    // Test code splitting and lazy loading
  })
  
  it('should optimize image loading and rendering', () => {
    // Test image optimization strategies
  })
})
```

### Test Execution

1. **Set up test environment** - Install Jest, Testing Library, and Puppeteer
2. **Configure test scripts** - Add test commands to package.json
3. **Run unit tests** - Test individual components and utilities
4. **Execute integration tests** - Test component interactions and data flow
5. **Launch Puppeteer E2E tests** - Test complete user workflows
6. **Run full test suite** - Ensure no regressions across all test types
7. **Generate coverage reports** - Verify test coverage meets standards
8. **Performance testing** - Validate optimization goals are met

#### Test Scripts for package.json

Add these scripts to enable comprehensive testing:

```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:e2e": "jest --config=jest.e2e.config.js",
    "test:all": "npm run test && npm run test:e2e"
  }
}
```

### Deliverables

Provide:
1. **Overall assessment** - High-level review of the implementation
2. **Specific issues** - Concrete problems with code references (file:line)
3. **Refactoring suggestions** - How to improve the code following adapted Sandi principles
4. **Test results** - Puppeteer test outcomes and any issues found
5. **Recommended next steps** - Prioritized list of improvements

Remember: Be direct and specific in feedback, focusing on maintainability and clarity over cleverness. Allow for necessary complexity in interactive features, game logic, animations, and media handling while maintaining the core principles of single responsibility and testability.