# CLAUDE.md - Duolingo Clone Project Overview

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Navigation

For detailed domain-specific guidance, see:
- **Backend Development** → [`/backend/CLAUDE.md`](/backend/CLAUDE.md)
- **Frontend Development** → [`/frontend/CLAUDE.md`](/frontend/CLAUDE.md)
- **Design System** → [`/frontend/src/lib/design-system/CLAUDE.md`](/frontend/src/lib/design-system/CLAUDE.md)
- **Testing Guide** → [`/docs/testing/CLAUDE.md`](/docs/testing/CLAUDE.md)
- **Security Guide** → [`/docs/security/CLAUDE.md`](/docs/security/CLAUDE.md)

## Project Overview

This is a Duolingo clone built as a full-stack application with Next.js frontend and FastAPI backend. The project emphasizes pixel-perfect design implementation using screenshot references and AI-assisted development workflows.

## Core Architecture Summary

- **Frontend**: Next.js 15 with App Router, Tailwind CSS 4.0, React 19
- **Backend**: FastAPI with Python 3.11+, PostgreSQL, SQLAlchemy 2.0
- **Authentication**: Supabase Auth with MFA, RBAC, field encryption
- **Configuration**: Service-oriented architecture with ConfigServiceOrchestrator
- **Design System**: AI-powered token extraction and visual validation
- **Testing**: Comprehensive test coverage (343+ backend, 200+ frontend tests)

For detailed architecture documentation, see the domain-specific CLAUDE.md files linked above.

## Context Markers for AI

When working on:
- **Backend APIs or configuration** → See [`/backend/CLAUDE.md`](/backend/CLAUDE.md)
- **Frontend components or state** → See [`/frontend/CLAUDE.md`](/frontend/CLAUDE.md)
- **Design tokens or validation** → See [`/frontend/src/lib/design-system/CLAUDE.md`](/frontend/src/lib/design-system/CLAUDE.md)
- **Test failures or memory issues** → See [`/docs/testing/CLAUDE.md`](/docs/testing/CLAUDE.md)
- **Security or authentication** → See [`/docs/security/CLAUDE.md`](/docs/security/CLAUDE.md)

## Quick Start Commands

### Frontend
```bash
cd frontend
npm install
npm run dev          # Start development server
npm run test         # Run tests
npm run design:help  # Design system commands
```

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # Start server
pytest               # Run tests
```

For comprehensive command documentation, see the domain-specific CLAUDE.md files.

## Development Guidelines

### Critical Rules
- **NEVER** access configuration directly - use ConfigServiceOrchestrator
- **ALWAYS** extract design tokens before building new components
- **NEVER** create files unless absolutely necessary
- **ALWAYS** prefer editing existing files over creating new ones
- **NEVER** proactively create documentation files unless requested

### Performance Requirements
- Page load time < 3 seconds on 3G networks
- API response time < 200ms
- Test suite execution < 5 minutes
- Development memory usage < 2GB

### Common Pitfalls to Avoid

1. **Configuration Access**
   - ❌ DON'T: `from app.core.config import settings`
   - ✅ DO: Use ConfigServiceOrchestrator

2. **Design Implementation**
   - ❌ DON'T: Build UI without extracting design tokens
   - ✅ DO: Run `npm run design:extract` first

3. **Test Creation**
   - ❌ DON'T: Create test files without proper config
   - ✅ DO: Use appropriate Vitest configuration

4. **Security**
   - ❌ DON'T: Store secrets in code or config files
   - ✅ DO: Use environment variables and secret management

## MVP Scope & Priority

### P0 Features (Must Have)
- Landing page (pixel-perfect)
- User authentication (register/login)
- Core learning loop (3 exercise types)
- Progress tracking (XP, hearts, streaks)
- 5 Spanish skills with 15 lessons

### P1 Features (Nice to Have)
- Achievements system
- Statistics page
- Sound effects and animations
- Keyboard shortcuts

## File Structure Overview

See domain-specific CLAUDE.md files for detailed structure:
- Backend structure: [`/backend/CLAUDE.md`](/backend/CLAUDE.md)
- Frontend structure: [`/frontend/CLAUDE.md`](/frontend/CLAUDE.md)
- Design system: [`/frontend/src/lib/design-system/CLAUDE.md`](/frontend/src/lib/design-system/CLAUDE.md)

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
- Optimize admin dashboard for large datasets
- Use React.memo for expensive components

### Backend Optimization
- Implement Redis caching for frequently accessed data
- Use database connection pooling
- Optimize database queries with proper indexing
- Implement rate limiting for AI API calls
- Optimize admin analytics queries
- Use pagination for large result sets
- Implement database indexing for audit logs

## Important Notes

- **Text Fidelity**: Always reproduce text from screenshots exactly
- **Configuration**: Use ConfigServiceOrchestrator, never access settings directly
- **Design System**: Run design:extract before building new components
- **Testing**: Use appropriate Vitest config for test type
- **Security**: Never commit secrets, use environment variables

## Project Resources

- [MVP Development Plan](/product-requirements/prds/mvp-development-plan.md)
- [Design References](/design-reference/README.md)
- [Architecture Decision Records](/docs/architecture-design-review/)

---

**Remember**: When in doubt, check the domain-specific CLAUDE.md file for detailed guidance.