## Relevant Files

- `frontend/src/app/page.tsx` - Home page component that will be replaced with new landing page
- `frontend/src/app/page.test.tsx` - Tests for the home page
- `frontend/src/components/landing/Header.tsx` - Landing page header with sticky navigation
- `frontend/src/components/landing/Header.test.tsx` - Tests for header component
- `frontend/src/components/landing/HeroSection.tsx` - Hero section with CTAs and illustration
- `frontend/src/components/landing/HeroSection.test.tsx` - Tests for hero section
- `frontend/src/components/landing/LanguageCarousel.tsx` - Scrollable language selection carousel
- `frontend/src/components/landing/LanguageCarousel.test.tsx` - Tests for language carousel
- `frontend/src/components/landing/FeatureSection.tsx` - Reusable feature section component
- `frontend/src/components/landing/FeatureSection.test.tsx` - Tests for feature sections
- `frontend/src/components/landing/CTASection.tsx` - Call-to-action section component
- `frontend/src/components/landing/CTASection.test.tsx` - Tests for CTA sections
- `frontend/src/components/landing/Footer.tsx` - Multi-column footer component
- `frontend/src/components/landing/Footer.test.tsx` - Tests for footer
- `frontend/src/lib/analytics/tracker.ts` - Analytics event tracking utilities
- `frontend/src/lib/analytics/ab-testing.ts` - A/B testing infrastructure
- `frontend/src/lib/design-system/tokens/landing-page.json` - Extracted design tokens
- `frontend/src/hooks/useScrollPosition.ts` - Custom hook for scroll-based header behavior
- `frontend/src/hooks/useAnalytics.ts` - Analytics tracking hook
- `frontend/public/images/landing/` - Directory for extracted landing page images

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `MyComponent.tsx` and `MyComponent.test.tsx` in the same directory).
- Use `npx jest [optional/path/to/test/file]` to run tests. Running without a path executes all tests found by the Jest configuration.
- Each sub-task includes Definition of Done (DoD) criteria to help junior developers understand when a task is complete.
- File suggestions are informed by existing codebase patterns and available dependencies.

## Tasks

- [ ] 1.0 Extract Design Tokens and Assets
  - [x] 1.1 Fix design system bugs to enable token extraction:
    - Add `qrcode==7.4.2` to requirements.txt
    - Fix `self.ai_client` references to `self._preferred_client or self.ai_clients` in design_system_service.py
    - Add `from dotenv import load_dotenv; load_dotenv()` to backend services
    - Implement dynamic media type detection for JPEG/PNG support
    - Remove error masking with fallback defaults
    - Fix path resolution for relative image paths
    - **Note**: See `/docs/design-system/implementation-fixes.md` for detailed fix instructions
  - [ ] 1.2 Extract design tokens from all landing page screenshots in `/design-reference/landing-page/` using `npm run design:extract` (DoD: All colors, typography, spacing, and shadows extracted via Claude Vision API)
  - [ ] 1.3 Extract and optimize images from screenshots for hero illustration, feature sections, and device mockups (DoD: Images saved in `/public/images/landing/` with proper naming conventions and optimized file sizes)
  - [ ] 1.4 Extract flag icons for language carousel from screenshots or source from icon libraries (DoD: All 7 language flag icons available in appropriate format)
  - [ ] 1.5 Configure Tailwind CSS with extracted design tokens (DoD: Custom colors, spacing, and typography available as Tailwind classes from generated token files)
  - [ ] 1.6 Document all extracted tokens and their usage in design system (DoD: Token documentation includes examples and usage guidelines)

- [ ] 2.0 Implement Core Layout Components
  - [ ] 2.1 Create Header component with Duolingo logo and initial nav structure (DoD: Header renders with correct green color #58CC02, logo links to homepage)
  - [ ] 2.2 Implement sticky header behavior with scroll detection using useScrollPosition hook (DoD: Header becomes sticky on scroll with modified styling per screenshot 06)
  - [ ] 2.3 Add conditional "GET STARTED" button in header that appears only after scrolling past hero (DoD: Button appears/disappears based on scroll position, smooth transition)
  - [ ] 2.4 Build HeroSection component with heading, subheading, and dual CTA buttons (DoD: Text matches exactly "The free, fun, and effective way to learn a language!", buttons styled per design)
  - [ ] 2.5 Create responsive Footer component with multi-column layout and social links (DoD: All footer sections present, links organized by category, language selector at bottom)

- [ ] 3.0 Build Interactive Features
  - [ ] 3.1 Implement LanguageCarousel component with horizontal scrolling (DoD: Shows 7 languages with smooth scroll, partial next/prev items visible)
  - [ ] 3.2 Add left/right navigation arrows to carousel with proper click handlers (DoD: Arrows functional, disabled states at carousel ends)
  - [ ] 3.3 Create touch-friendly swipe gestures for mobile carousel using Framer Motion (DoD: Natural swipe on touch devices, momentum scrolling)
  - [ ] 3.4 Build reusable FeatureSection component accepting props for different content (DoD: Single component handles all 4 feature sections with proper layout variations)
  - [ ] 3.5 Implement CTASection component for "learn anytime, anywhere", Power Duo, and other CTA sections (DoD: All CTA sections render with correct backgrounds and layouts)
  - [ ] 3.6 Add hover states and micro-animations to buttons and interactive elements (DoD: Smooth transitions on hover, active states for better UX)

- [ ] 4.0 Integrate Analytics and A/B Testing
  - [ ] 4.1 Set up PostHog analytics with Next.js using environment variables (DoD: PostHog initialized, events tracked in development)
  - [ ] 4.2 Implement analytics event tracking for all CTA buttons and language carousel clicks (DoD: Custom events fire with proper event names and properties)
  - [ ] 4.3 Create A/B testing infrastructure with feature flags for page variations (DoD: Can serve different component variations based on user segment)
  - [ ] 4.4 Add scroll depth tracking to measure user engagement (DoD: Tracks 25%, 50%, 75%, 100% scroll milestones)
  - [ ] 4.5 Implement GTM container setup with data layer for flexible tracking (DoD: GTM container ID configured, custom events pushed to data layer)
  - [ ] 4.6 Create analytics dashboard mockup showing key metrics (DoD: Visual representation of conversion rate, language clicks, scroll depth)

- [ ] 5.0 Optimize Performance and Accessibility
  - [ ] 5.1 Implement lazy loading for below-the-fold images using Next/Image (DoD: Images load only when approaching viewport, loading placeholders shown)
  - [ ] 5.2 Add proper semantic HTML structure and heading hierarchy (DoD: Correct h1/h2/h3 usage, semantic sections)
  - [ ] 5.3 Ensure all interactive elements have proper ARIA labels and keyboard navigation (DoD: Tab navigation works, screen reader announces all elements correctly)
  - [ ] 5.4 Optimize bundle size with code splitting for heavy components (DoD: Initial bundle < 200KB, route-based code splitting implemented)
  - [ ] 5.5 Add focus indicators and skip navigation link (DoD: Visible focus rings, skip to main content link)
  - [ ] 5.6 Run Lighthouse audit and fix any issues to achieve 95+ accessibility score (DoD: All Lighthouse categories green, Core Web Vitals passing)
  - [ ] 5.7 Test page load performance on simulated 3G network (DoD: Page interactive within 3 seconds on slow 3G)
  - [ ] 5.8 Implement responsive design for all breakpoints (mobile, tablet, desktop) (DoD: Layout adapts properly at 768px and 1024px breakpoints, no horizontal scroll)