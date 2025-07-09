# Landing Page Components PRD

## Introduction/Overview

This PRD defines the requirements for implementing a pixel-perfect clone of Duolingo's landing page components. The landing page serves as the primary entry point for new users and must effectively communicate the value proposition while providing clear pathways to registration. All components must exactly match the design reference screenshots provided in `/design-reference/landing-page/`.

## Goals

1. **Pixel-Perfect Implementation**: Achieve 100% visual fidelity to Duolingo's landing page design
2. **Conversion Optimization**: Enable A/B testing for language selection and page variations
3. **Performance**: Ensure page loads in under 3 seconds on 3G networks
4. **Accessibility**: Support screen readers and keyboard navigation
5. **Analytics Integration**: Track user interactions for data-driven optimization

## User Stories

### First-Time Visitor
- **As a first-time visitor**, I want to immediately understand what Duolingo offers so that I can decide if it's right for me
- **As a first-time visitor**, I want to see available languages so that I can verify my target language is supported
- **As a first-time visitor**, I want a clear call-to-action so that I can start learning quickly

### Returning Visitor
- **As a returning visitor**, I want to easily access my account so that I can continue learning
- **As a returning visitor**, I want the page to load quickly so that I don't waste time waiting

### Mobile User
- **As a mobile user**, I want all content to be easily readable and tappable so that I can navigate without zooming
- **As a mobile user**, I want the language carousel to be swipeable so that I can browse languages naturally

### Accessibility User
- **As a screen reader user**, I want all images to have descriptive alt text so that I understand the content
- **As a keyboard user**, I want to navigate all interactive elements without a mouse

## Functional Requirements

### 1. Header Navigation Component
- The header must include the Duolingo logo (exact green color: #58CC02)
- Header must be sticky on scroll with modified styling (reference: 06-nav-bar-after-scroll.png)
- Logo must link to homepage (current page)
- "GET STARTED" button must appear in top right nav bar only when user scrolls past hero section
- The button should not be visible in nav bar on initial page load

### 2. Hero Section Component
- Display animated character illustration exactly as shown in design
- Heading text: "The free, fun, and effective way to learn a language!"
- Primary CTA button: "GET STARTED" with green background (#58CC02)
- Secondary CTA button: "I ALREADY HAVE AN ACCOUNT" with white background
- Maintain exact spacing and typography from reference

### 3. Language Carousel Component
- Display language options with flag icons and names
- Languages shown: ENGLISH, SPANISH, FRENCH, GERMAN, ITALIAN, PORTUGUESE, DUTCH
- Left and right navigation arrows for scrolling
- Each language must be clickable and trackable for A/B testing
- Smooth horizontal scrolling animation
- Show partial next/previous items to indicate scrollability
- Position at bottom of viewport for tablet and desktop views (not sticky)
- Hide completely on mobile views (below 768px)
- Should scroll away with page content (not remain fixed)

### 4. Feature Sections Components
- **"free. fun. effective."** section with mobile app mockup
- **"backed by science"** section with research illustration
- **"stay motivated"** section with streak/achievement graphics
- **"personalized learning"** section with adaptive learning illustration
- Each section must match exact layout, colors, and copy from screenshots

### 5. Call-to-Action Sections
- **"learn anytime, anywhere"** with device illustrations
- **Power Duo section** with mascot characters and "LEARN MORE" button
- **Duolingo English Test** section with dark background
- **Duolingo for Schools** section with education graphics
- **Duolingo ABC** and **Duolingo Math** subsections

### 6. Footer Component
- **Final CTA**: "learn a language with duolingo" with "GET STARTED" button
- Multi-column footer with links organized by category
- Social media icons
- Language selector at bottom
- Copyright information

### 7. A/B Testing Infrastructure
- Track clicks on each language in the carousel
- Support for multiple page variations
- Event tracking for all CTAs
- Integration points for analytics platforms
- Ability to serve different variations based on user segments

## Non-Goals (Out of Scope)

- User authentication functionality (login/register forms)
- Course content or lesson pages
- Pricing information or premium features
- User testimonials or reviews
- Blog content or news sections
- Community features or forums
- Mobile app download flows
- Actual language learning functionality

## Design Considerations

### Visual Fidelity Requirements
- All colors must match exactly from screenshots
- Typography must match including font families, sizes, and weights
- Spacing and layout must be pixel-perfect
- Animations should match Duolingo's playful style
- Images and illustrations must be extracted from screenshots

### Responsive Design
- Desktop breakpoint: 1024px and above
- Tablet breakpoint: 768px to 1023px
- Mobile breakpoint: below 768px
- Language carousel must be touch-friendly on mobile
- All text must remain readable at all breakpoints

### Component Architecture
- Each major section should be a separate, reusable component
- Components should accept props for A/B testing variations
- Use CSS modules or styled-components for scoped styling
- Implement lazy loading for below-the-fold images

## Technical Considerations

### Frontend Stack
- Next.js 15 with App Router
- React 19 with TypeScript
- Tailwind CSS 4.0 for styling
- Framer Motion for animations (carousel, hover effects)
- Next/Image for optimized image loading

### Performance Requirements
- Largest Contentful Paint (LCP) < 2.5s
- First Input Delay (FID) < 100ms
- Cumulative Layout Shift (CLS) < 0.1
- Total page weight < 1MB (excluding fonts)
- Implement critical CSS inlining

### SEO Considerations
- Semantic HTML structure
- Proper heading hierarchy (h1, h2, h3)
- Meta descriptions and Open Graph tags
- Structured data for organization
- Sitemap generation

### Analytics Integration
- GTM container for flexibility
- Custom events for:
  - Language carousel clicks
  - CTA button clicks
  - Scroll depth tracking
  - Time on page
- A/B test variant tracking

### Accessibility Requirements
- WCAG 2.1 AA compliance
- Skip navigation link
- Proper ARIA labels
- Keyboard navigation support
- Focus indicators
- Alt text for all images

## Success Metrics

### Primary Metrics
- **Conversion Rate**: Percentage of visitors who click "GET STARTED"
- **Language Interest**: Click-through rates on language options
- **Page Load Time**: Must be < 3 seconds on 3G
- **Bounce Rate**: Target < 40%

### Secondary Metrics
- **Engagement Rate**: Percentage scrolling past hero section
- **A/B Test Lift**: Improvement in conversion from variations
- **Accessibility Score**: Lighthouse accessibility score > 95
- **SEO Performance**: Core Web Vitals all in "Good" range

### A/B Testing Metrics
- Language carousel click distribution
- CTA button click rates by variation
- Scroll depth by variation
- Time to first interaction

## Open Questions

1. **Image Assets**: ✅ Extract images from screenshots using AI vision tools
2. **Font Licensing**: ✅ Use Din Round font family (as specified in PRD-000) - obtain from font providers or use similar open-source alternatives like Nunito
3. **Animation Timing**: ✅ Based on research: Use ease-out for elements entering screen, 200-300ms for fast transitions, 500ms for normal transitions, cubic-bezier easing for smooth natural motion
4. **Analytics Platform**: Which specific analytics platform should we integrate with?
5. **A/B Testing Tool**: ✅ Use Posthog (free tier) for A/B testing - provides both analytics and experimentation features
6. **Cookie Consent**: ✅ Not needed - no compliance banners required
7. **Loading States**: How should components appear while data is loading?
8. **Error States**: How should the page handle JavaScript errors gracefully?

## Dependencies

### Design Dependencies
- Access to all screenshots in `/design-reference/landing-page/`
- Design token extraction from PRD-006
- Color palette and typography specifications

### Technical Dependencies
- Next.js project setup and configuration
- Tailwind CSS configuration with custom design tokens
- Image optimization pipeline
- Analytics and A/B testing platform accounts

### Content Dependencies
- Exact copy for all text elements
- Alt text for all images
- Language names and flag icons
- Legal/compliance approved footer links

## Testing Strategy

### Unit Tests
- Each component renders correctly
- Props are properly passed and utilized
- Event handlers fire correctly
- Accessibility attributes are present

### Integration Tests
- Navigation between sections works
- Language carousel scrolls properly
- Sticky header behaves correctly on scroll
- A/B testing variants load correctly

### Visual Regression Tests
- Screenshot comparison with design references
- Cross-browser visual consistency
- Responsive layout at all breakpoints

### Performance Tests
- Page load time on various network speeds
- Bundle size analysis
- Image optimization verification
- Critical rendering path optimization

### Accessibility Tests
- Automated accessibility scanning
- Keyboard navigation testing
- Screen reader compatibility
- Color contrast verification

## Implementation Timeline

### Phase 1: Setup and Foundation (2 days)
- Extract design tokens from screenshots
- Set up component structure
- Configure Tailwind with custom tokens
- Implement base layout components

### Phase 2: Core Components (3 days)
- Header navigation with sticky behavior
- Hero section with CTAs
- Language carousel with interactions
- Feature sections

### Phase 3: Remaining Sections (2 days)
- Call-to-action sections
- Footer component
- Mobile responsiveness
- Animations and transitions

### Phase 4: Testing and Optimization (2 days)
- A/B testing integration
- Analytics implementation
- Performance optimization
- Accessibility fixes

### Total Estimated Time: 9 days

## Risk Factors

1. **Design Fidelity**: Achieving pixel-perfect match may require multiple iterations
2. **Performance**: Large images could impact load times
3. **Browser Compatibility**: CSS features may not work in all browsers
4. **A/B Testing Complexity**: Multiple variations could complicate codebase

## Deployment Considerations

- CDN configuration for static assets
- Image optimization and compression
- Environment variables for analytics keys
- A/B testing feature flags
- Monitoring and error tracking setup