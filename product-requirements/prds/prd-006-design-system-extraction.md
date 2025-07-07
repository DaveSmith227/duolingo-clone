# Design System Extraction PRD

## Overview

This PRD defines a comprehensive system for extracting design tokens from 1,000+ Mobbin reference screenshots using AI vision capabilities. The system will enable pixel-perfect UI implementation throughout the development cycle by automatically analyzing screenshots and generating a scalable, maintainable design system foundation. This approach eliminates manual design token extraction, ensures consistency across the application, and provides automated validation to maintain design fidelity.

## Goals

1. **Automate Design Token Extraction**: Use AI vision to analyze screenshots and extract colors, typography, spacing, shadows, and other design elements with 95%+ accuracy
2. **Create Scalable Foundation**: Build a design system architecture that can grow with the application without requiring expensive refactoring
3. **Enable Pixel-Perfect Implementation**: Generate design tokens that ensure UI implementation matches reference screenshots exactly
4. **Streamline Development Workflow**: Integrate extraction process into development cycle for iterative screen flow building
5. **Establish Single Source of Truth**: Create centralized design token management that serves both development and validation needs

## User Stories

1. **As a solopreneur developer**, I want to extract design tokens from screenshots automatically so that I can focus on building features rather than manually measuring and color-picking
2. **As a solopreneur developer**, I want to validate my UI implementation against reference screenshots so that I can ensure pixel-perfect accuracy without manual comparison
3. **As a solopreneur developer**, I want to iteratively build screen flows with consistent design tokens so that my application maintains visual coherence across all features
4. **As a solopreneur developer**, I want the design system to scale as I add new screens so that I don't need to refactor the foundation later
5. **As a solopreneur developer**, I want design tokens organized by component and screen so that I can quickly find and apply the right styles

## Functional Requirements

1. **Screenshot Analysis System**
   - The system must analyze PNG and JPG screenshots from the `/design-reference/` directory
   - The system must use AI vision (Claude/GPT-4V) to extract design elements
   - The system must automatically ignore and exclude Mobbin watermarks (black bottom banners)
   - The system must process iOS, web, and landing page screenshots with appropriate categorization

2. **Design Token Extraction**
   - The system must extract color palettes (primary, secondary, semantic colors)
   - The system must identify typography (font families, sizes, weights, line heights)
   - The system must measure spacing patterns (padding, margins, gaps)
   - The system must detect shadows (box shadows, text shadows with blur, spread, color)
   - The system must identify border radius values and patterns
   - The system must extract component-specific tokens (button heights, input styles, etc.)

3. **Token Organization and Storage**
   - The system must generate a structured design token hierarchy
   - The system must create TypeScript constants for type safety
   - The system must generate Tailwind CSS configuration extensions
   - The system must produce CSS custom properties for runtime flexibility
   - The system must maintain design token documentation with visual examples

4. **Validation System**
   - The system must use Puppeteer to capture implemented UI screenshots
   - The system must compare implementation against reference screenshots
   - The system must highlight visual differences and mismatches
   - The system must provide pixel-level accuracy metrics
   - The system must generate visual diff reports for review

5. **Integration and Workflow**
   - The system must integrate with the existing Next.js/Tailwind setup
   - The system must provide CLI commands for extraction and validation
   - The system must support incremental updates as new screenshots are added
   - The system must maintain version history of design token changes

## Non-Goals (Out of Scope)

1. Real-time design token extraction during development (batch processing only)
2. Automatic code generation for complete components (tokens only)
3. Design token extraction from non-screenshot sources (Figma, Sketch files)
4. Animation and transition timing extraction (static design elements only)
5. Automated fixing of design inconsistencies (reporting only)

## Design Considerations

### Architecture Overview
```
/design-system/
├── extractor/              # AI vision extraction logic
│   ├── analyzer.ts         # Screenshot analysis engine
│   ├── tokenizer.ts        # Token extraction and categorization
│   └── ai-prompts.ts       # Structured prompts for AI vision
├── tokens/                 # Generated design tokens
│   ├── colors.ts          # Color palette definitions
│   ├── typography.ts      # Font system definitions
│   ├── spacing.ts         # Spacing scale definitions
│   ├── shadows.ts         # Shadow definitions
│   ├── radii.ts          # Border radius definitions
│   └── components.ts      # Component-specific tokens
├── validator/             # Validation system
│   ├── puppeteer-capture.ts
│   ├── visual-diff.ts
│   └── reports.ts
├── config/               # Configuration files
│   ├── tailwind-tokens.js # Tailwind config extension
│   └── css-variables.css  # CSS custom properties
└── docs/                 # Generated documentation
    └── token-reference.md # Visual token documentation
```

### Token Structure Example
```typescript
// Example of extracted color tokens
export const colors = {
  primary: {
    50: '#e6f7ff',
    100: '#bae7ff',
    500: '#1890ff', // Duolingo blue
    600: '#096dd9',
    700: '#0050b3',
  },
  success: {
    DEFAULT: '#52c41a', // Green for correct answers
    light: '#f6ffed',
    dark: '#389e0d',
  },
  error: {
    DEFAULT: '#ff4d4f', // Red for incorrect answers
    light: '#fff1f0',
    dark: '#cf1322',
  },
  // ... more colors
} as const;
```

## Technical Considerations

### AI Vision Integration
- Use Claude API with vision capabilities for screenshot analysis
- Implement structured prompts that guide consistent token extraction
- Batch process screenshots to optimize API usage and costs
- Cache analysis results to avoid redundant processing

### Validation Approach
- Puppeteer captures at multiple viewport sizes (mobile, tablet, desktop)
- Use perceptual hashing for initial similarity detection
- Implement pixel-by-pixel comparison for detailed validation
- Generate visual reports highlighting differences with overlays

### Scalability Design
- Token naming convention that supports growth (BEM-style naming)
- Modular token files that can be extended without breaking changes
- Semantic token layer above raw values for flexibility
- Component token inheritance from base design tokens

## Success Metrics

1. **Extraction Accuracy**: 95%+ accuracy in color and spacing extraction
2. **Development Speed**: 70% reduction in time spent on design implementation
3. **Design Consistency**: 100% of UI components use extracted design tokens
4. **Validation Coverage**: Automated validation for 90%+ of implemented screens
5. **Token Reusability**: Average token reuse across 5+ components

## Open Questions

1. Should the system support extracting micro-animations from screenshot sequences?
2. How should conflicting design tokens between iOS and web be resolved?
3. Should the system generate Storybook stories for design token documentation?
4. What threshold for visual differences should trigger validation failures?
5. Should extracted tokens be committed to version control or generated on-demand?

## Testing Strategy

### Unit Tests
- Token extraction accuracy tests with known screenshot inputs
- Token formatting and structure validation
- AI prompt consistency and output parsing

### Integration Tests
- End-to-end extraction workflow from screenshots to generated files
- Tailwind configuration integration and build process
- Puppeteer validation workflow with sample components

### Visual Regression Tests
- Baseline screenshot comparison for token application
- Cross-browser rendering consistency validation
- Responsive design token application across viewports

## Deployment Considerations

### Development Environment
- AI API keys stored in environment variables
- Local caching of extraction results for offline development
- Git hooks for design token validation before commits

### CI/CD Integration
- Automated extraction on new screenshot additions
- Visual regression tests in pull request checks
- Design token documentation generation and deployment

## Timeline

### Phase 1: Foundation (Week 1 - Days 1-2)
- Set up AI vision integration with Claude API
- Implement basic color and typography extraction
- Create initial token file structure

### Phase 2: Comprehensive Extraction (Week 1 - Days 3-4)
- Add spacing, shadow, and radius extraction
- Implement Mobbin watermark detection and exclusion
- Generate Tailwind configuration integration

### Phase 3: Validation System (Week 1 - Days 5-6)
- Implement Puppeteer screenshot capture
- Build visual comparison engine
- Create validation reporting system

### Phase 4: Integration (Week 1 - Day 7)
- Integrate with development workflow
- Create CLI commands for extraction and validation
- Generate initial design token documentation

### Ongoing: Iterative Improvement
- Refine extraction accuracy based on usage
- Expand token categories as needed
- Optimize performance and API usage