# Frontend Development Guide

This file provides guidance for Claude Code when working with the frontend codebase.

## Quick Links
- Main overview: [`/CLAUDE.md`](/CLAUDE.md)
- Design system: [`/frontend/src/lib/design-system/CLAUDE.md`](/frontend/src/lib/design-system/CLAUDE.md)
- Testing guide: [`/docs/testing/CLAUDE.md`](/docs/testing/CLAUDE.md)

## Architecture Overview

### Tech Stack
- **Framework**: Next.js 15.3.5 with App Router
- **React**: Version 19.0.0 with concurrent features
- **Styling**: Tailwind CSS 4.0 with custom design tokens
- **State Management**: Zustand 5.0.6
- **Animations**: Framer Motion
- **Audio**: Howler.js
- **Icons**: Lucide React
- **Testing**: Vitest with React Testing Library

## Component Architecture

### Directory Structure
```
/src/
├── app/              # Next.js App Router pages
│   ├── layout.tsx    # Root layout
│   ├── page.tsx      # Home page
│   └── admin/        # Admin dashboard
├── components/       # Reusable components
│   ├── auth/         # Authentication components
│   ├── admin/        # Admin-specific components
│   └── ui/           # Base UI components
├── stores/           # Zustand stores
├── hooks/            # Custom React hooks
└── lib/              # Utilities and configurations
```

### Component Patterns

#### Authentication Components
Located in `/src/components/auth/`:
- **LoginForm**: Email/password login with remember me
- **RegisterForm**: Multi-step registration with validation
- **PasswordResetForm**: Password reset flow
- **ProfileManagement**: User profile editing
- **ProtectedRoute**: Route authentication guard

#### Admin Dashboard
Located in `/src/components/admin/`:
- **AdminAnalyticsDashboard**: Real-time metrics
- **AdminUserManagement**: User CRUD operations
- **AuditLogViewer**: Searchable audit trail
- **BulkUserActionDialog**: Mass user operations

### State Management

#### Auth Store (Zustand)
```typescript
// ❌ DON'T: Direct localStorage access
localStorage.setItem('user', JSON.stringify(user))

// ✅ DO: Use Zustand store
import { useAuthStore } from '@/stores/authStore'
const { user, login, logout } = useAuthStore()
```

#### Store Pattern
```typescript
interface AuthStore {
  user: User | null
  isLoading: boolean
  error: string | null
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
}
```

## Testing Infrastructure

### Test Configuration Files
- `vitest.config.base.ts` - Base configuration
- `vitest.config.unit.ts` - Unit tests (Node environment)
- `vitest.config.dom.ts` - DOM tests (jsdom)
- `vitest.config.design-system.ts` - Design system tests
- `vitest.config.integration.ts` - Integration tests

### Test Organization
- 51 test files following `*.test.ts(x)` pattern
- Tests co-located with components
- Integration tests in `__tests__/` directories

### Common Test Patterns
```typescript
// Component testing
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock Zustand store
import { useAuthStore } from '@/stores/authStore'
vi.mock('@/stores/authStore')

// Test example
test('login form submission', async () => {
  const user = userEvent.setup()
  render(<LoginForm />)
  
  await user.type(screen.getByLabelText('Email'), 'test@example.com')
  await user.type(screen.getByLabelText('Password'), 'password123')
  await user.click(screen.getByRole('button', { name: 'Log in' }))
  
  expect(useAuthStore.getState().login).toHaveBeenCalled()
})
```

### Running Tests
```bash
npm run test              # All tests
npm run test:unit         # Unit tests only
npm run test:components   # Component tests
npm run test:coverage     # With coverage
npm run test:ui           # Vitest UI
```

## Design System Integration

### Token Extraction Workflow
1. **Before building ANY UI component**:
   ```bash
   npm run design:extract <screenshot-path>
   ```
2. Review generated tokens in `/src/lib/design-system/tokens/`
3. Use tokens in components via Tailwind classes

### Using Design Tokens
```tsx
// ❌ DON'T: Hardcode values
<div className="bg-[#58cc02] rounded-[12px]">

// ✅ DO: Use design tokens
<div className="bg-primary rounded-button">
```

### Visual Validation
```bash
npm run design:validate <url>  # Validate against screenshot
npm run design:cache --stats   # Check cache status
```

## Common Development Tasks

### Creating a New Page
1. Create file in `/src/app/[route]/page.tsx`
2. Add layout if needed in `layout.tsx`
3. Use design tokens from screenshots
4. Implement responsive design
5. Add loading and error states

### Creating a Component
1. Extract design tokens from screenshot
2. Create component file with TypeScript
3. Add component test file
4. Use proper TypeScript interfaces
5. Implement responsive behavior

### Adding API Integration
```typescript
// Use built-in fetch with proper error handling
async function fetchData() {
  try {
    const response = await fetch('/api/endpoint', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}
```

## Performance Optimization

### Image Optimization
```tsx
// ❌ DON'T: Regular img tag
<img src="/hero.jpg" alt="Hero" />

// ✅ DO: Next.js Image component
import Image from 'next/image'
<Image src="/hero.jpg" alt="Hero" width={1200} height={600} priority />
```

### Code Splitting
```tsx
// Dynamic imports for large components
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <Skeleton />,
  ssr: false,
})
```

### Memo and Callbacks
```tsx
// Memoize expensive components
const ExpensiveList = memo(({ items }) => {
  return items.map(item => <Item key={item.id} {...item} />)
})

// Use callbacks for stable references
const handleClick = useCallback(() => {
  // handle click
}, [dependency])
```

## Styling Guidelines

### Tailwind CSS Usage
- Mobile-first approach: Start with mobile styles
- Use design system tokens via Tailwind config
- Consistent spacing: 4px grid system
- Responsive utilities: `sm:`, `md:`, `lg:`, `xl:`

### Component Styling Pattern
```tsx
// Use clsx for conditional classes
import clsx from 'clsx'

<button
  className={clsx(
    'px-4 py-2 rounded-button font-medium',
    'bg-primary text-white',
    'hover:bg-primary-hover active:scale-95',
    'disabled:opacity-50 disabled:cursor-not-allowed',
    className
  )}
>
```

## Debugging Tips

### React DevTools
- Install React Developer Tools extension
- Check component props and state
- Profile performance issues

### Network Debugging
```typescript
// Add request interceptor for debugging
if (process.env.NODE_ENV === 'development') {
  window.fetch = new Proxy(window.fetch, {
    apply: (target, thisArg, args) => {
      console.log('Fetch:', args[0])
      return target.apply(thisArg, args)
    }
  })
}
```

### State Debugging
```typescript
// Zustand devtools
import { devtools } from 'zustand/middleware'

const useStore = create(
  devtools(
    (set) => ({
      // store implementation
    }),
    { name: 'app-store' }
  )
)
```

## Build and Deployment

### Development
```bash
npm run dev        # Start dev server
npm run build      # Production build
npm run start      # Start production server
npm run lint       # Run ESLint
```

### Environment Variables
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-key
```

### Production Checklist
- [ ] All design tokens extracted
- [ ] Visual validation passing
- [ ] Tests passing with coverage
- [ ] Lighthouse score > 90
- [ ] No console errors
- [ ] Environment variables set

## Important Reminders

- **ALWAYS** extract design tokens before building UI
- **NEVER** hardcode colors, spacing, or sizes
- **ALWAYS** write tests for new components
- **NEVER** use `any` type in TypeScript
- **ALWAYS** handle loading and error states
- **NEVER** expose sensitive data in client code