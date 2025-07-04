# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Duolingo clone built as a full-stack application with Next.js frontend and FastAPI backend. The project emphasizes pixel-perfect design implementation using screenshot references and AI-assisted development workflows.

## Architecture

### Frontend (Next.js 15)
- **Location**: `/frontend/`
- **Framework**: Next.js 15 with App Router
- **Styling**: Tailwind CSS with custom design tokens
- **State Management**: Zustand
- **Animations**: Framer Motion
- **Audio**: Howler.js for sound effects
- **Icons**: Lucide React

### Backend (FastAPI/Python)
- **Location**: `/backend/`
- **Framework**: FastAPI with Python 3.11+
- **Database**: PostgreSQL with SQLAlchemy
- **Authentication**: Supabase Auth
- **AI Integration**: OpenAI API + LangChain
- **Caching**: Redis
- **Task Queue**: Celery

### Design System
- **Screenshot References**: `/design-reference/` - Contains iOS and web screenshots for pixel-perfect implementation
- **Priority Order**: Landing page → iOS onboarding → profile creation → home → lesson completion
- **Important**: Ignore black "curated by Mobbin" banners in screenshots
- **Text Fidelity**: All text content must match screenshots exactly

## Development Commands

### Frontend
```bash
cd frontend
npm run dev          # Start development server with Turbopack
npm run build        # Build for production
npm run lint         # Run ESLint
npm run start        # Start production server
```

### Backend
```bash
cd backend
# Setup virtual environment first
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # Start development server
```

## Key Dependencies

### Frontend
- **Next.js 15**: React framework with App Router
- **Tailwind CSS**: Utility-first CSS framework
- **Framer Motion**: Animation library
- **Howler.js**: Audio library for sound effects
- **Zustand**: State management
- **Lucide React**: Icon library

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Database ORM
- **PostgreSQL**: Primary database
- **Redis**: Caching and task queue
- **OpenAI**: AI content generation
- **LangChain**: AI workflow orchestration

## Development Guidelines

### Screenshot-Based Development
1. **Primary Reference**: Use screenshots in `/design-reference/` for all UI components
2. **Text Extraction**: Extract all text content exactly as shown (headlines, CTAs, copy)
3. **Color Extraction**: Use AI vision to identify exact color values
4. **Responsive Design**: Reference both iOS and web screenshots for responsive behavior
5. **Ignore Watermarks**: Always ignore "curated by Mobbin" banners

### MVP Scope Enforcement
- Focus on P0 features only during initial development
- Landing page is highest priority (Week 1)
- Core learning loop: translation, multiple choice, listening exercises
- Basic gamification: XP, hearts, streaks
- Essential user flows: registration, profile creation, lesson completion

### Code Quality Standards
- Use TypeScript for all React components
- Implement mobile-first responsive design
- Follow Next.js 15 App Router patterns
- Use custom design tokens extracted from screenshots
- Implement proper error boundaries

### Design System Implementation
- Extract design tokens from screenshots before building components
- Use consistent spacing system (4px grid: 4, 8, 12, 16, 24, 32, 48, 64)
- Implement Duolingo's signature rounded corners (8px, 12px, 16px, 24px)
- Use pill-shaped buttons with 48px standard height
- Apply consistent shadows and color system

## Testing Strategy

### Frontend Testing
```bash
cd frontend
npm run test         # Run Jest tests
npm run test:e2e     # Run Playwright tests
npm run storybook    # Start Storybook for component testing
```

### Backend Testing
```bash
cd backend
pytest               # Run Python tests
pytest app/tests/    # Run specific test directory
```

## File Structure

```
/frontend/
├── src/app/         # Next.js App Router pages
├── src/components/  # Reusable UI components
├── src/lib/         # Utility functions and configurations
└── public/          # Static assets

/backend/
├── app/
│   ├── api/         # API routes
│   ├── core/        # Core functionality
│   ├── models/      # Database models
│   └── schemas/     # Pydantic schemas
└── requirements.txt # Python dependencies

/design-reference/   # Screenshot references for UI implementation
├── landing-page/    # Marketing site screenshots (highest priority)
├── ios/             # iOS app screenshots
└── web/             # Web app screenshots
```

## AI Integration Points

### Content Generation
- Use OpenAI API for exercise content generation
- Implement LangChain for AI workflow orchestration
- Generate personalized learning content based on user progress

### Screenshot Analysis
- Use AI vision capabilities to extract design specifications
- Analyze color palettes, spacing, and typography from screenshots
- Generate component specifications from visual references

## Performance Considerations

### Frontend Optimization
- Use Next.js Image component for optimized images
- Implement code splitting for exercise types
- Cache API responses for offline functionality
- Optimize bundle size with dynamic imports

### Backend Optimization
- Implement Redis caching for frequently accessed data
- Use database connection pooling
- Optimize database queries with proper indexing
- Implement rate limiting for AI API calls

## Common Development Patterns

### Component Development
1. Analyze screenshot references first
2. Extract design tokens (colors, spacing, typography)
3. Build component with TypeScript
4. Implement responsive behavior
5. Add to Storybook for documentation

### API Development
1. Define Pydantic schemas for request/response
2. Implement FastAPI endpoints with proper error handling
3. Add database operations with SQLAlchemy
4. Include comprehensive tests
5. Document API endpoints

## Important Notes

- **Text Fidelity**: Always reproduce text from screenshots exactly
- **MVP Focus**: Prioritize core learning experience over advanced features
- **Responsive Design**: Ensure mobile-first approach with proper breakpoints
- **Performance**: Optimize for 3G networks and older devices
- **Accessibility**: Implement proper ARIA labels and keyboard navigation