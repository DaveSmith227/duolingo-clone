# Design System Developer Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Workflow](#development-workflow)
3. [Component Implementation](#component-implementation)
4. [Token Usage](#token-usage)
5. [Visual Validation](#visual-validation)
6. [Testing Strategy](#testing-strategy)
7. [Performance Guidelines](#performance-guidelines)
8. [Best Practices](#best-practices)

## Quick Start

### Setup for New Developers

1. **Clone and Install**
   ```bash
   git clone <repository-url>
   cd duolingo-clone/frontend
   npm install
   ```

2. **Initialize Design System**
   ```bash
   npm run design:init
   ```

3. **Extract Initial Tokens**
   ```bash
   npm run design:extract:batch --input-dir ./design-reference
   ```

4. **Start Development Server**
   ```bash
   npm run dev
   ```

5. **Validate Your First Component**
   ```bash
   npm run design:validate http://localhost:3000
   ```

## Development Workflow

### Daily Development Process

#### 1. Start with Design Reference
Before implementing any component, extract tokens from the design:

```bash
# Extract tokens from new design screenshot
npm run design:extract design-reference/new-component/button.png --verbose

# Review generated tokens
cat src/lib/design-system/tokens/generated/colors.ts
```

#### 2. Implement Component
Create your component using the extracted tokens:

```typescript
// components/ui/button.tsx
import { tokens } from '@/lib/design-system/tokens/generated';

interface ButtonProps {
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

export function Button({ variant = 'primary', size = 'md', children }: ButtonProps) {
  return (
    <button
      className={`
        px-${tokens.spacing[size]} 
        py-${tokens.spacing.sm}
        bg-${tokens.colors[variant][500]}
        text-${tokens.colors.white}
        rounded-${tokens.radii[size]}
        font-${tokens.typography.weights.medium}
      `}
    >
      {children}
    </button>
  );
}
```

#### 3. Validate Implementation
```bash
# Validate specific page
npm run design:validate http://localhost:3000/button-demo

# Run comprehensive validation
npm run design:validate:batch validation-config.json
```

#### 4. Update Documentation
```bash
# Generate updated documentation
npm run design:extract:batch --format docs
```

### Branch-Based Workflow

#### Feature Branch Setup
```bash
# Create feature branch
git checkout -b feature/new-button-component

# Extract tokens for your feature
npm run design:extract design-reference/buttons/ --output-dir ./tokens/buttons

# Implement component
# ... development work ...

# Validate before commit
npm run design:validate:batch
```

#### Pre-Commit Validation
Git hooks automatically run:
- Visual validation on changed components
- Token consistency checks
- Performance regression tests

#### Pull Request Process
1. **Automated CI Validation**
   - Visual regression tests
   - Token consistency verification
   - Performance benchmarks

2. **Manual Review Checklist**
   - [ ] Design tokens match specifications
   - [ ] Visual validation passes
   - [ ] Component follows naming conventions
   - [ ] Performance within acceptable bounds

## Component Implementation

### Using Design Tokens

#### Token Import Patterns
```typescript
// Recommended: Import specific token categories
import { colors, spacing, typography } from '@/lib/design-system/tokens/generated';

// Alternative: Import all tokens
import { tokens } from '@/lib/design-system/tokens/generated';

// CSS Variables (for dynamic theming)
import '@/lib/design-system/tokens/generated/tokens.css';
```

#### Tailwind Integration
```typescript
// tailwind.config.js automatically includes design tokens
export default {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      // Tokens automatically injected here
    }
  }
};
```

#### Component Variants with Tokens
```typescript
// Using class-variance-authority with design tokens
import { cva } from 'class-variance-authority';
import { tokens } from '@/lib/design-system/tokens/generated';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md font-medium transition-colors',
  {
    variants: {
      variant: {
        primary: `bg-primary-500 text-white hover:bg-primary-600`,
        secondary: `bg-secondary-100 text-secondary-900 hover:bg-secondary-200`,
        outline: `border border-primary-300 bg-transparent hover:bg-primary-50`
      },
      size: {
        sm: `h-9 px-3 text-sm`,
        md: `h-10 px-4 py-2`,
        lg: `h-11 px-8 py-2`
      }
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md'
    }
  }
);
```

### Responsive Design with Tokens

#### Breakpoint Management
```typescript
// Use responsive spacing tokens
<div className={`
  p-${tokens.spacing.responsive.xs.md}
  md:p-${tokens.spacing.responsive.md.lg}
  lg:p-${tokens.spacing.responsive.lg.xl}
`}>
  Content
</div>
```

#### Responsive Typography
```typescript
// Responsive text scaling
<h1 className={`
  text-${tokens.typography.responsive.mobile.sizes.h1}
  md:text-${tokens.typography.responsive.tablet.sizes.h1}
  lg:text-${tokens.typography.responsive.desktop.sizes.h1}
`}>
  Heading
</h1>
```

## Token Usage

### Token Categories

#### Colors
```typescript
// Semantic colors (recommended)
import { colors } from '@/lib/design-system/tokens/generated';

const successColor = colors.semantic.success;
const primaryColor = colors.semantic.primary;

// Base colors (for custom variants)
const blueScale = colors.base.blue; // { 50: '#...', 100: '#...', ... }
```

#### Typography
```typescript
import { typography } from '@/lib/design-system/tokens/generated';

// Font families
const headingFont = typography.families.heading; // 'Inter, sans-serif'
const bodyFont = typography.families.body;

// Font sizes
const textSizes = typography.sizes; // { xs: '0.75rem', sm: '0.875rem', ... }

// Font weights
const weights = typography.weights; // { light: 300, medium: 500, ... }
```

#### Spacing
```typescript
import { spacing } from '@/lib/design-system/tokens/generated';

// Base spacing scale
const spacingScale = spacing.base; // { xs: '0.25rem', sm: '0.5rem', ... }

// Responsive spacing
const responsiveSpacing = spacing.responsive.lg; // { xs: '1rem', sm: '1.25rem', ... }
```

#### Shadows and Effects
```typescript
import { shadows, effects } from '@/lib/design-system/tokens/generated';

// Elevation shadows
const cardShadow = shadows.elevation.medium;
const modalShadow = shadows.elevation.high;

// Interactive effects
const hoverEffect = effects.hover.scale;
const focusRing = effects.focus.ring;
```

### Token Naming Conventions

#### Semantic vs Base Tokens
```typescript
// ✅ Preferred: Use semantic tokens
color: colors.semantic.primary
background: colors.semantic.surface.primary

// ⚠️ Use with caution: Base tokens for custom variants
color: colors.base.blue[500]
```

#### Component-Specific Tokens
```typescript
// Component tokens inherit from semantic tokens
const buttonTokens = {
  primary: {
    background: colors.semantic.primary,
    text: colors.semantic.onPrimary,
    border: 'transparent'
  },
  secondary: {
    background: colors.semantic.secondary,
    text: colors.semantic.onSecondary,
    border: colors.semantic.border.secondary
  }
};
```

## Visual Validation

### Setting Up Validation

#### Create Reference Screenshots
1. **Capture Reference Images**
   ```bash
   # Manual capture of key states
   npm run design:validate:capture http://localhost:3000/button-demo --output reference/
   
   # Batch capture with different viewports
   npm run design:validate:batch-capture validation-config.json
   ```

2. **Configure Validation Rules**
   ```json
   // validation-config.json
   {
     "baseUrl": "http://localhost:3000",
     "pages": [
       {
         "path": "/components/button",
         "name": "button-component",
         "selectors": [".button-demo"],
         "variants": ["default", "hover", "focus", "disabled"]
       }
     ],
     "viewports": ["mobile", "tablet", "desktop"],
     "threshold": 0.05,
     "outputDir": "./validation-reports"
   }
   ```

#### Validation in Development
```bash
# Quick validation during development
npm run design:validate http://localhost:3000/your-component

# Comprehensive validation before commit
npm run design:validate:batch validation-config.json

# Check specific component states
npm run design:validate:compare reference/button-primary.png actual/button-primary.png
```

### Handling Validation Failures

#### Common Failure Types
1. **Color Mismatches**: Check token usage and CSS specificity
2. **Spacing Issues**: Verify responsive token application
3. **Typography Differences**: Ensure correct font loading and fallbacks
4. **State Inconsistencies**: Validate hover, focus, and disabled states

#### Debugging Process
```bash
# Generate detailed diff reports
npm run design:validate http://localhost:3000/component --format html --verbose

# Capture current state for comparison
npm run design:validate:capture http://localhost:3000/component --selector .component

# Update reference if design intentionally changed
npm run design:validate:update-reference validation-config.json
```

## Testing Strategy

### Unit Testing with Design Tokens

```typescript
// components/__tests__/button.test.tsx
import { render, screen } from '@testing-library/react';
import { Button } from '../button';
import { tokens } from '@/lib/design-system/tokens/generated';

describe('Button', () => {
  it('applies correct primary variant styles', () => {
    render(<Button variant="primary">Click me</Button>);
    
    const button = screen.getByRole('button');
    const styles = getComputedStyle(button);
    
    expect(styles.backgroundColor).toBe(tokens.colors.semantic.primary);
    expect(styles.color).toBe(tokens.colors.semantic.onPrimary);
  });

  it('uses correct spacing tokens', () => {
    render(<Button size="lg">Large Button</Button>);
    
    const button = screen.getByRole('button');
    const styles = getComputedStyle(button);
    
    expect(styles.paddingLeft).toBe(tokens.spacing.lg);
    expect(styles.paddingRight).toBe(tokens.spacing.lg);
  });
});
```

### Visual Regression Testing

```typescript
// tests/visual/button.visual.test.ts
import { test, expect } from '@playwright/test';

test.describe('Button Visual Tests', () => {
  test('button variants match design', async ({ page }) => {
    await page.goto('/components/button-demo');
    
    // Test primary variant
    await expect(page.locator('[data-testid="button-primary"]')).toHaveScreenshot('button-primary.png');
    
    // Test hover state
    await page.locator('[data-testid="button-primary"]').hover();
    await expect(page.locator('[data-testid="button-primary"]')).toHaveScreenshot('button-primary-hover.png');
    
    // Test focus state
    await page.locator('[data-testid="button-primary"]').focus();
    await expect(page.locator('[data-testid="button-primary"]')).toHaveScreenshot('button-primary-focus.png');
  });
});
```

### Performance Testing

```typescript
// tests/performance/token-usage.perf.test.ts
import { test, expect } from '@playwright/test';

test.describe('Token Performance', () => {
  test('page loads with acceptable performance', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/');
    
    // Wait for design tokens to load
    await page.waitForSelector('[data-tokens-loaded]');
    
    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(1000); // 1 second threshold
  });
  
  test('token bundle size is acceptable', async ({ page }) => {
    await page.goto('/');
    
    const tokenBundle = await page.evaluate(() => {
      return performance.getEntriesByName('tokens.css')[0]?.transferSize;
    });
    
    expect(tokenBundle).toBeLessThan(50000); // 50KB threshold
  });
});
```

## Performance Guidelines

### Token Bundle Optimization

#### Lazy Loading Tokens
```typescript
// Load tokens only when needed
const loadTokens = async () => {
  const { tokens } = await import('@/lib/design-system/tokens/generated');
  return tokens;
};

// Component-specific token loading
const loadButtonTokens = async () => {
  const { buttonTokens } = await import('@/lib/design-system/tokens/components/button');
  return buttonTokens;
};
```

#### Tree Shaking
```typescript
// ✅ Good: Import only needed tokens
import { colors, spacing } from '@/lib/design-system/tokens/generated';

// ❌ Avoid: Importing entire token object
import { tokens } from '@/lib/design-system/tokens/generated';
const { colors, spacing } = tokens; // Runtime destructuring
```

### CSS Performance

#### Critical CSS Extraction
```css
/* Critical tokens loaded inline */
:root {
  --color-primary: #3b82f6;
  --spacing-base: 1rem;
  --font-family-base: 'Inter', sans-serif;
}

/* Non-critical tokens loaded asynchronously */
@import url('./tokens/extended.css') (prefers-reduced-motion: no-preference);
```

#### CSS Custom Properties Strategy
```typescript
// Use CSS custom properties for dynamic theming
const ThemeProvider = ({ theme, children }) => {
  const cssVariables = Object.entries(theme).reduce((vars, [key, value]) => {
    vars[`--${key}`] = value;
    return vars;
  }, {});

  return (
    <div style={cssVariables}>
      {children}
    </div>
  );
};
```

### Runtime Performance

#### Memoization Strategies
```typescript
import { useMemo } from 'react';
import { tokens } from '@/lib/design-system/tokens/generated';

const Button = ({ variant, size, children }) => {
  const buttonStyles = useMemo(() => ({
    backgroundColor: tokens.colors.semantic[variant],
    padding: `${tokens.spacing[size]} ${tokens.spacing.lg}`,
    fontSize: tokens.typography.sizes[size]
  }), [variant, size]);

  return (
    <button style={buttonStyles}>
      {children}
    </button>
  );
};
```

## Best Practices

### Token Management

#### 1. Semantic Token Priority
```typescript
// ✅ Use semantic tokens for component logic
const buttonColor = tokens.colors.semantic.primary;

// ✅ Use base tokens for one-off customizations
const customBlue = tokens.colors.base.blue[600];

// ❌ Avoid hardcoded values
const wrongColor = '#3b82f6';
```

#### 2. Responsive Design Patterns
```typescript
// ✅ Use responsive token objects
const responsiveSpacing = {
  mobile: tokens.spacing.responsive.xs,
  tablet: tokens.spacing.responsive.md,
  desktop: tokens.spacing.responsive.lg
};

// ✅ Mobile-first approach
<div className={`
  p-${responsiveSpacing.mobile}
  md:p-${responsiveSpacing.tablet}
  lg:p-${responsiveSpacing.desktop}
`}>
```

#### 3. Component Token Composition
```typescript
// ✅ Create component-specific token collections
const cardTokens = {
  background: tokens.colors.semantic.surface.primary,
  border: tokens.colors.semantic.border.subtle,
  shadow: tokens.shadows.elevation.low,
  radius: tokens.radii.md,
  padding: tokens.spacing.lg
};

const Card = ({ children }) => (
  <div
    style={{
      backgroundColor: cardTokens.background,
      border: `1px solid ${cardTokens.border}`,
      boxShadow: cardTokens.shadow,
      borderRadius: cardTokens.radius,
      padding: cardTokens.padding
    }}
  >
    {children}
  </div>
);
```

### Development Workflow

#### 1. Design-First Approach
- Always start with design reference extraction
- Validate tokens before implementation
- Test across all target viewports

#### 2. Incremental Development
- Extract tokens for one component at a time
- Validate each component independently
- Build up complexity gradually

#### 3. Continuous Validation
- Run validation on every build
- Use visual regression testing in CI
- Monitor performance metrics

### Code Organization

#### 1. Token File Structure
```
src/lib/design-system/tokens/
├── generated/           # Auto-generated tokens
│   ├── index.ts        # Main token export
│   ├── colors.ts       # Color tokens
│   ├── typography.ts   # Typography tokens
│   └── spacing.ts      # Spacing tokens
├── components/         # Component-specific tokens
│   ├── button.ts      # Button component tokens
│   └── card.ts        # Card component tokens
└── themes/            # Theme variations
    ├── light.ts       # Light theme
    └── dark.ts        # Dark theme
```

#### 2. Component Integration
```typescript
// ✅ Clear token usage in components
import { buttonTokens } from '@/lib/design-system/tokens/components/button';
import { baseTokens } from '@/lib/design-system/tokens/generated';

export const Button = ({ variant, size, children }) => {
  const variantStyles = buttonTokens.variants[variant];
  const sizeStyles = buttonTokens.sizes[size];
  
  return (
    <button
      className={`
        ${variantStyles.background}
        ${variantStyles.text}
        ${sizeStyles.padding}
        ${sizeStyles.fontSize}
      `}
    >
      {children}
    </button>
  );
};
```

### Error Handling

#### 1. Token Fallbacks
```typescript
// ✅ Provide fallbacks for missing tokens
const getColor = (path: string, fallback: string) => {
  try {
    return tokens.colors[path] || fallback;
  } catch {
    return fallback;
  }
};

const buttonColor = getColor('semantic.primary', '#3b82f6');
```

#### 2. Validation Error Recovery
```bash
# Handle validation failures gracefully
npm run design:validate http://localhost:3000 || echo "Validation failed, check reports"

# Provide alternative validation strategies
npm run design:validate:fallback --threshold 0.2
```

## Migration and Updates

### Token Version Migration

When design tokens are updated, use the migration system:

```bash
# Check compatibility before migrating
npm run design:migrate:check

# Perform migration with backup
npm run design:migrate --backup

# Validate after migration
npm run design:validate:batch
```

### Component Updates

When updating components to use new tokens:

1. **Extract new tokens first**
2. **Update component implementation**
3. **Run visual validation**
4. **Update tests**
5. **Document changes**

This guide provides a comprehensive foundation for developers working with the design system. For specific API documentation, see the [Design System CLI Documentation](./DESIGN_SYSTEM_CLI.md).