# Duolingo Clone PRD - Solopreneur Edition

## Executive Summary

Building a pixel-perfect Duolingo clone as a solopreneur using modern AI-assisted development tools (Cursor + Claude Code). This project leverages the recommended tech stack from our analysis: React/Next.js 15, FastAPI, React Native, and purpose-built AI infrastructure to create a feature-rich language learning platform.

## Product Vision

Create a fully-functional Duolingo clone that demonstrates the power of AI-assisted development while implementing core educational features including gamification, personalized learning paths, and real-time progress tracking.

## Tech Stack

### Frontend
- **Web**: Next.js 15 + React 18 + TypeScript
- **Mobile**: React Native (New Architecture) + Expo
- **Design System**: Custom Duolingo-inspired components using Tailwind CSS
- **State Management**: Zustand
- **Animations**: Framer Motion (web) + React Native Reanimated 3 (mobile)
- **Icons**: Lucide React + Custom SVGs
- **Sound**: Howler.js (web) + Expo AV (mobile)

### Backend
- **API**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 16 with pgvector extension
- **Cache**: Redis
- **Auth**: Supabase Auth
- **AI/ML**: OpenAI API + LangChain
- **Vector DB**: Qdrant (self-hosted)
- **File Storage**: Supabase Storage
- **Task Queue**: Celery + Redis
- **WebSockets**: FastAPI WebSockets

### Infrastructure
- **Hosting**: Vercel (frontend) + Railway (backend)
- **CDN**: Cloudflare
- **Monitoring**: Sentry + LogRocket
- **Analytics**: PostHog + Mixpanel
- **Error Tracking**: Sentry
- **Performance**: Lighthouse CI

### Development Tools
- **IDE**: Cursor with Claude integration
- **Version Control**: GitHub
- **CI/CD**: GitHub Actions
- **Testing**: Jest + React Testing Library + Playwright
- **Design Reference**: Screenshot collection + AI vision analysis
- **Component Documentation**: Storybook

## Design System & Screenshot-Based Development

### Screenshot Reference System
Since we're working without Figma files, we'll use a systematic approach to extract design details from Duolingo screenshots sourced from Mobbin and other references.

#### Screenshot Organization
```
/design-reference/
├── landing-page/
│   └── [Marketing landing page screenshots - highest priority]
├── ios/
│   ├── choosing-learning-goal/
│   │   └── [Screenshots showing goal selection flow]
│   ├── completing-first-lesson/
│   │   └── [Screenshots of first lesson experience]
│   ├── creating-profile/
│   │   └── [Profile creation flow screenshots]
│   ├── home/
│   │   └── [Home screen and navigation screenshots]
│   ├── jan-2025-full/
│   │   └── [Complete app flow screenshots from Jan 2025]
│   ├── onboarding/
│   │   └── [Onboarding flow screenshots]
│   └── section/
│       └── [Section/skill tree screenshots]
└── web/
    └── dec-2023-full/
        └── [~600 responsive web app screenshots from Dec 2023]
```

**Important Note**: All text content (headlines, copy, CTAs, etc.) must be identical to what appears in the screenshots. This ensures brand authenticity and proper messaging.

#### AI-Powered Design Extraction Workflow
1. **Visual Analysis Prompts**: Use Claude's vision capabilities to analyze screenshots
   - **Important**: Instruct Claude to ignore the black "curated by Mobbin" banner at the bottom of images
2. **Color Extraction**: Use AI to identify exact color values from screenshots (excluding watermarks)
3. **Spacing Patterns**: Have AI measure and document spacing consistency
4. **Component Identification**: Extract reusable patterns from multiple screenshots

#### Design Token Extraction Template
```markdown
For each screenshot, extract:
- Colors (hex values)
- Font sizes (estimated px)
- Spacing (margins/padding)
- Border radius values
- Shadow properties
- Animation duration/easing
```

### Enhanced Design System

#### Colors (Extended Palette from Screenshots)
```css
:root {
  /* Primary Green */
  --duo-green: #58CC02;
  --duo-green-light: #89E219;
  --duo-green-dark: #4CAF00;
  
  /* Secondary Colors */
  --duo-blue: #1CB0F6;
  --duo-blue-light: #4FC3F7;
  --duo-red: #FF4B4B;
  --duo-red-dark: #E53935;
  --duo-yellow: #FFC800;
  --duo-orange: #FF9600;
  --duo-purple: #CE82FF;
  --duo-dark-blue: #2B70C9;
  
  /* Neutrals */
  --duo-black: #4B4B4B;
  --duo-white: #FFFFFF;
  --duo-gray-100: #F7F7F7;
  --duo-gray-200: #E5E5E5;
  --duo-gray-300: #AFAFAF;
  --duo-gray-400: #777777;
  --duo-gray-500: #3C3C3C;
  
  /* Semantic Colors */
  --duo-success: #58CC02;
  --duo-error: #FF4B4B;
  --duo-warning: #FFC800;
  --duo-info: #1CB0F6;
  
  /* Gradients */
  --duo-gradient-green: linear-gradient(180deg, #89E219 0%, #58CC02 100%);
  --duo-gradient-blue: linear-gradient(180deg, #4FC3F7 0%, #1CB0F6 100%);
}
```

#### Typography System
```css
/* Font Face Definitions */
@font-face {
  font-family: 'Din Round';
  src: url('/fonts/DinRound-Regular.woff2') format('woff2');
  font-weight: 400;
}

@font-face {
  font-family: 'Din Round';
  src: url('/fonts/DinRound-Bold.woff2') format('woff2');
  font-weight: 700;
}

/* Typography Scale */
:root {
  --font-size-xs: 0.75rem;    /* 12px */
  --font-size-sm: 0.875rem;   /* 14px */
  --font-size-base: 1rem;     /* 16px */
  --font-size-lg: 1.125rem;   /* 18px */
  --font-size-xl: 1.5rem;     /* 24px */
  --font-size-2xl: 2rem;      /* 32px */
  --font-size-3xl: 3rem;      /* 48px */
  
  --line-height-tight: 1.2;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;
}
```

#### Animation System
```javascript
export const animations = {
  // Timing functions
  easing: {
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    smooth: 'cubic-bezier(0.4, 0, 0.2, 1)',
    sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',
  },
  
  // Durations
  duration: {
    instant: '100ms',
    fast: '200ms',
    normal: '300ms',
    slow: '500ms',
    sluggish: '700ms',
  },
  
  // Spring animations
  spring: {
    bouncy: { stiffness: 300, damping: 20 },
    smooth: { stiffness: 100, damping: 20 },
    slow: { stiffness: 50, damping: 20 },
  },
}
```

### Component Patterns (From Screenshot Analysis)
- **Rounded corners**: 8px (small), 12px (medium), 16px (large), 24px (XL), full (pills)
- **Shadows**: 
  - Small: `0 2px 4px rgba(0,0,0,0.1)`
  - Medium: `0 4px 12px rgba(0,0,0,0.15)`
  - Large: `0 8px 24px rgba(0,0,0,0.2)`
- **Buttons**: Pill-shaped with bold typography, 48px height standard
- **Cards**: Rounded rectangles with playful tilt animations on hover
- **Icons**: Consistent 24x24 or 32x32 sizing with 2px stroke width
- **Spacing**: 4px grid system (4, 8, 12, 16, 24, 32, 48, 64)

## Enhanced Core Features

### Phase 1: Foundation (Weeks 1-4)

#### 1.1 Landing Page
- Hero section with animated Duo mascot (Lottie animation)
- Parallax scrolling effects
- Feature highlights with micro-interactions
- Language selection carousel with flag animations
- Social proof section (user testimonials)
- Sign up/Login CTAs with confetti on success
- Responsive design (mobile-first)
- A/B testing framework setup

#### 1.2 Authentication System
- Email/password registration with real-time validation
- OAuth (Google, Apple, Facebook)
- Magic link authentication option
- Profile creation flow with avatar customization
- Onboarding questionnaire with progress indicator
- Goal setting (casual, regular, serious, intense)
- Timezone detection for streak calculations
- Welcome email sequence

#### 1.3 Basic Course Structure
- Language selection (start with 5 languages)
- Skill tree visualization with smooth pan/zoom
- Lesson nodes with progress indicators
- Locked/unlocked states with animation transitions
- XP and streak counters with number animations
- Crown system for skill mastery
- Bonus skills section
- Path selection (e.g., traveler, business, culture)

#### 1.4 Design System Implementation
- Component library setup with Storybook
- Screenshot-based component development
- Color token extraction from screenshots
- Typography system with fallback fonts
- Icon library with custom Duolingo icons
- Animation presets library
- Accessibility audit tools
- Dark mode support (future enhancement)

### Phase 2: Core Learning Experience (Weeks 5-8)

#### 2.1 Enhanced Lesson Types
- **Translation exercises** 
  - Drag-and-drop word bank with magnetic snap
  - Keyboard shortcuts for power users
  - Alternative correct answers
- **Multiple choice** questions
  - Image-based options
  - Audio-based options
  - Elimination mode for hints
- **Listening exercises**
  - Variable playback speed
  - Noise cancellation preprocessing
  - Visual waveform display
- **Speaking exercises**
  - Web Speech API integration
  - Pronunciation scoring
  - Visual mouth position guides
- **Writing exercises**
  - Smart keyboard with word suggestions
  - Handwriting recognition (tablet)
  - Accent mark shortcuts
- **Matching pairs**
  - Time attack mode
  - Memory game variant
  - Audio-to-text matching
- **Fill in the blanks**
  - Context clues highlighting
  - Progressive hints
- **Story exercises**
  - Interactive dialogues
  - Choose your own adventure

#### 2.2 Advanced Gamification Elements
- XP system with multipliers and combos
- Streak counter with milestone rewards
- Lives/Hearts system with timed regeneration
- League system (Bronze to Diamond to Legendary)
- Achievement badges with rarity tiers
- Progress quests with daily/weekly challenges
- Duo mascot interactions and encouragement
- Power-ups (streak freeze, double XP, heart refill)
- Seasonal events and limited-time challenges

#### 2.3 Audio & Haptics Enhancement
- 3D spatial audio for immersive experience
- Dynamic music that adapts to performance
- Character-specific voice acting
- Ambient sounds for different lesson themes
- Custom haptic patterns for different interactions
- Audio ducking during speech exercises
- Offline audio caching

#### 2.4 Advanced Progress Tracking
- Real-time progress synchronization
- Detailed mistake analysis with patterns
- Personalized weak spot identification
- Study session heatmaps
- Progress prediction algorithms
- Export progress reports (PDF)
- Parent/teacher dashboard (future)

### Phase 3: AI Integration (Weeks 9-12)

#### 3.1 Advanced Content Generation
- GPT-4 powered sentence generation
- Context-aware story creation
- Dynamic difficulty adjustment
- Personalized example sentences
- Cultural context integration
- Meme and pop culture references
- User interest-based content

#### 3.2 Smart Features Plus
- Advanced spaced repetition (SM-2 algorithm)
- Neural network-based error prediction
- Personalized learning pace optimization
- AI pronunciation coach
- Grammar pattern recognition
- Contextual hint generation
- Learning style adaptation

#### 3.3 Enhanced Social Features
- Study groups with shared goals
- Global classroom competitions
- Language exchange matching
- User-generated content sharing
- Achievement showcase profiles
- Streak rescue (friends can save your streak)
- Collaborative stories
- Live group lessons (future)

#### 3.4 Premium Plus Features
- AI conversation partner
- Unlimited skill tests
- Early access to new features
- Custom learning paths
- Priority support
- Family plan sharing
- Certification preparation
- No ads + exclusive content

## Enhanced Database Schema

### Additional Tables
```sql
-- User Preferences
CREATE TABLE user_preferences (
  user_id UUID PRIMARY KEY REFERENCES users(id),
  daily_goal INTEGER DEFAULT 10,
  reminder_time TIME,
  sound_effects BOOLEAN DEFAULT true,
  haptic_feedback BOOLEAN DEFAULT true,
  theme VARCHAR(20) DEFAULT 'light',
  notification_settings JSONB
);

-- Achievements
CREATE TABLE achievements (
  id UUID PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  icon_url VARCHAR(255),
  rarity VARCHAR(20), -- common, rare, epic, legendary
  requirements JSONB
);

-- User Achievements
CREATE TABLE user_achievements (
  user_id UUID REFERENCES users(id),
  achievement_id UUID REFERENCES achievements(id),
  earned_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (user_id, achievement_id)
);

-- Streaks
CREATE TABLE streaks (
  user_id UUID PRIMARY KEY REFERENCES users(id),
  current_streak INTEGER DEFAULT 0,
  longest_streak INTEGER DEFAULT 0,
  last_activity_date DATE,
  freeze_count INTEGER DEFAULT 0,
  streak_freeze_used_today BOOLEAN DEFAULT false
);

-- Leagues
CREATE TABLE leagues (
  id UUID PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  tier INTEGER NOT NULL, -- 1=Bronze, 2=Silver, etc.
  icon_url VARCHAR(255)
);

-- League Standings
CREATE TABLE league_standings (
  id UUID PRIMARY KEY,
  league_id UUID REFERENCES leagues(id),
  user_id UUID REFERENCES users(id),
  week_start_date DATE,
  xp_earned INTEGER DEFAULT 0,
  rank INTEGER
);

-- Audio Files
CREATE TABLE audio_files (
  id UUID PRIMARY KEY,
  exercise_id UUID REFERENCES exercises(id),
  language_code VARCHAR(5),
  voice_gender VARCHAR(10),
  file_url VARCHAR(255),
  duration_ms INTEGER
);

-- User Mistakes
CREATE TABLE user_mistakes (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  exercise_id UUID REFERENCES exercises(id),
  mistake_type VARCHAR(50),
  user_answer TEXT,
  correct_answer TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- AI Generated Content
CREATE TABLE ai_content (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  content_type VARCHAR(50),
  prompt TEXT,
  generated_content JSONB,
  feedback_score INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Enhanced API Endpoints

### Screenshot Reference System
- `POST /api/design/analyze-screenshot` - AI analysis of design elements
- `GET /api/design/components/{name}` - Get component design specs
- `POST /api/design/extract-colors` - Extract color palette from image

### Advanced Learning
- `POST /api/exercises/generate-adaptive` - Generate AI-adapted exercise
- `GET /api/users/{id}/learning-style` - Get identified learning style
- `POST /api/exercises/{id}/report-error` - Report content errors
- `GET /api/exercises/{id}/alternatives` - Get alternative correct answers

### Gamification Plus
- `POST /api/achievements/check` - Check for new achievements
- `GET /api/leagues/{id}/live-standings` - Real-time league updates
- `POST /api/streaks/rescue` - Friend streak rescue
- `GET /api/events/current` - Get active seasonal events

### Analytics
- `POST /api/analytics/session` - Track learning session
- `GET /api/analytics/insights` - Get personalized insights
- `POST /api/analytics/heatmap` - Submit interaction heatmap

## AI-Assisted Development Workflow

### Screenshot Analysis Prompts
```markdown
# Component Extraction (Landing Page Priority)
"Analyze this Duolingo landing page screenshot, IGNORING the black 'curated by Mobbin' banner:
1. Extract ALL text content exactly as written (headlines, subheadings, CTAs, etc.)
2. Identify the exact color values for all elements
3. Measure hero section heights and spacing
4. Document all button styles and states
5. Note the responsive breakpoints visible
6. List all images/illustrations that need to be recreated
IMPORTANT: All text must be reproduced exactly as shown in the screenshot."

# Responsive Design Analysis (Web Dec 2023)
"I have ~600 web screenshots from Dec 2023. Help me analyze:
1. Identify all unique responsive breakpoints
2. How components adapt from desktop to tablet to mobile
3. Which elements stack vs. remain side-by-side
4. Font size scaling across breakpoints
5. Navigation changes between screen sizes
6. Ensure text content remains identical across all versions"

# Design System Extraction from Screenshot Sets
"I have these Duolingo screenshot folders:
- iOS: choosing-learning-goal, completing-first-lesson, creating-profile, home, onboarding, section
- Web: dec-2023-full
- Full flows: iOS jan-2025-full

For each screenshot set, help me:
1. Identify common design patterns across screens
2. Extract a consistent color palette
3. Document spacing/grid system
4. List all UI components that appear multiple times
5. Note platform-specific differences (iOS vs Web)"

# Cross-Platform Component Analysis
"Compare iOS and Web screenshots (ignoring Mobbin watermarks):
1. What components look identical across platforms?
2. What platform-specific adaptations exist?
3. How does navigation differ?
4. Are the color systems consistent?
5. What responsive patterns can we identify?"
```

### Enhanced Cursor + Claude Workflow

#### Phase-Specific Prompts (Using Mobbin Screenshots)
```markdown
# Week 1: Landing Page First - Exact Recreation
"Using the landing-page/ screenshots:
1. Extract EVERY piece of text exactly as written
2. Create a component for each section matching the screenshot
3. Ensure responsive behavior matches the ~600 web screenshots
4. Use the exact button text, headlines, and marketing copy
5. Match colors, spacing, and typography precisely

Example: If the hero says 'The free, fun, and effective way to learn a language!' - use that exact text."

# Week 2-3: MVP Core Features
"Focus on the essential learning loop:
- Use 'Completing first lesson' screenshots for exercise UI
- Implement only translation, multiple choice, and listening
- Create a simplified 5-skill tree
- Basic XP and hearts only
- Skip complex animations for MVP"

# Week 3-4: Profile & Goals - Using iOS Creating Profile/Choosing Learning Goal
"Based on the iOS profile creation and goal selection screenshots:
- Build the avatar selection component
- Create the daily goal selector (5, 10, 15, 20 min options)
- Match the card-based selection UI
- Implement the progress flow between screens
- Extract and apply consistent spacing patterns"

# Week 5-6: Home & Navigation - Using iOS Home Screenshots
"Analyze the iOS Home screenshots to build:
- Bottom navigation bar with exact icons and active states
- Skill tree/path visualization
- Lesson node components (locked/unlocked/in-progress states)
- Hearts and streak displays in header
- League position indicator"

# Week 7-8: Lessons - Using iOS Completing First Lesson
"From the 'Completing the first lesson' screenshots:
- Build all exercise type components shown
- Match the progress bar styling at top
- Implement correct/incorrect answer feedback
- Create the word bank for translation exercises
- Build the lesson complete celebration screen"

# Week 9-12: Full Experience - Using Jan 2025 Full Flow
"Using the complete iOS Jan 2025 screenshots:
- Identify any UI updates from earlier versions
- Build missing components not in other folders
- Ensure consistency across all screens
- Implement proper navigation flow
- Add polish and micro-interactions"

# Web Adaptation - Using Web Dec 2023 Screenshots
"Adapt the mobile UI to web using Dec 2023 web screenshots:
- Identify layout differences for larger screens
- Adjust navigation from bottom bar to sidebar/header
- Implement responsive breakpoints
- Ensure feature parity with mobile
- Optimize interactions for mouse/keyboard"
```

### Testing Strategy
```markdown
# Visual Regression Testing
- Screenshot comparison tests
- Component visual testing with Storybook
- Cross-browser rendering checks
- Mobile device testing matrix

# Performance Testing
- Lighthouse CI thresholds
- Bundle size monitoring
- Animation performance profiling
- API response time tracking

# User Testing
- A/B test framework setup
- Session recording integration
- Heatmap analysis
- User feedback collection
```

## Implementation Best Practices

### Code Organization
```
src/
├── components/
│   ├── ui/              # Base UI components
│   ├── exercises/       # Exercise-specific components
│   ├── gamification/   # Badges, XP, streaks
│   └── animations/      # Reusable animations
├── features/
│   ├── auth/           # Authentication flow
│   ├── lessons/        # Lesson logic
│   ├── progress/       # Progress tracking
│   └── social/         # Social features
├── hooks/
│   ├── useSound.ts     # Sound effect hook
│   ├── useHaptic.ts    # Haptic feedback
│   └── useAnimation.ts # Animation utilities
└── lib/
    ├── ai/             # AI integration
    ├── api/            # API client
    └── design-system/  # Design tokens
```

### Performance Optimizations
1. **Image Optimization**
   - Use Next.js Image component
   - Implement progressive loading
   - Optimize screenshot references
   
2. **Code Splitting**
   - Route-based splitting
   - Component lazy loading
   - Dynamic imports for exercises

3. **Caching Strategy**
   - Static asset caching
   - API response caching
   - Offline lesson caching

### Accessibility Checklist
- [ ] Keyboard navigation for all interactions
- [ ] Screen reader announcements for XP gains
- [ ] High contrast mode support
- [ ] Reduced motion preferences
- [ ] Focus indicators on all interactive elements
- [ ] ARIA labels for gamification elements
- [ ] Alternative text for all images
- [ ] Captions for audio content

## Success Metrics (Enhanced)

### User Engagement
- **Daily Active Users (DAU)**: Target 60% of registered users
- **Session Length**: Average 15-20 minutes per session
- **Lessons per Session**: Average 3-5 lessons completed
- **Retention Rate**: 40% Day 7, 25% Day 30
- **Friend Invites**: 2.5 average per active user
- **Premium Conversion**: 5% of active users

### Learning Outcomes
- **Lesson Completion Rate**: >80% of started lessons
- **Mistake Rate**: <20% on review exercises
- **Streak Maintenance**: 30% of users maintain 7+ day streaks
- **Skill Progression**: Users complete 1-2 skills per week
- **Accuracy Improvement**: 15% increase after 30 days
- **Speaking Confidence**: 70% report improvement

### Technical Performance
- **Page Load Time**: <2 seconds on 3G
- **Time to Interactive**: <3 seconds
- **API Response Time**: <200ms for 95% of requests
- **Crash Rate**: <0.1% of sessions
- **Screenshot Analysis Time**: <5 seconds per image
- **AI Response Time**: <1 second for hints

## Risk Mitigation

### Technical Risks
- **Screenshot Quality**: Use multiple screenshots per component
- **Design Inconsistency**: Create component library early
- **Performance Issues**: Regular performance audits
- **AI API Costs**: Implement caching and rate limiting

### User Experience Risks
- **Learning Curve**: Progressive disclosure of features
- **Motivation Drop**: Enhanced gamification and social features
- **Content Quality**: User reporting and AI validation
- **Platform Differences**: Shared component library

## Conclusion

This enhanced PRD incorporates screenshot-based design development, making it ideal for solopreneurs using AI-assisted tools without access to Figma files. The additions include:

1. **Screenshot Reference System**: Organized approach to design extraction
2. **AI-Powered Workflows**: Specific prompts for design analysis
3. **Enhanced Features**: More sophisticated gamification and AI integration
4. **Performance Focus**: Detailed optimization strategies
5. **Testing Framework**: Comprehensive testing approach
6. **Accessibility First**: Built-in accessibility considerations

By following this PRD and leveraging AI tools effectively, you can create a pixel-perfect Duolingo clone that rivals the original in both functionality and user experience.