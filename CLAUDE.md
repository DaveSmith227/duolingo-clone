# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Duolingo clone built as a full-stack application with Next.js frontend and FastAPI backend. The project emphasizes pixel-perfect design implementation using screenshot references and AI-assisted development workflows.

## Architecture

### Security Architecture
- **Authentication**: Multi-factor authentication with Supabase integration
- **Authorization**: Role-based access control (RBAC) system
- **Data Protection**: Field-level encryption for sensitive data
- **Session Management**: Secure session handling with remember-me functionality
- **Audit Logging**: Comprehensive audit trail for all user actions
- **GDPR Compliance**: Data retention policies and account deletion workflows
- **Password Security**: Argon2 hashing with complexity requirements
- **Rate Limiting**: Brute force protection and API rate limiting

### Admin System
- **User Management**: Comprehensive user administration dashboard
- **Analytics Dashboard**: Real-time user engagement and authentication metrics
- **Bulk Operations**: Mass user actions with audit logging
- **System Monitoring**: Health checks and diagnostic tools
- **Audit Log Viewer**: Searchable audit trail with filtering
- **Data Export**: GDPR-compliant data export functionality

### Frontend (Next.js 15)
- **Location**: `/frontend/`
- **Framework**: Next.js 15.3.5 with App Router
- **Styling**: Tailwind CSS 4.0 with custom design tokens
- **State Management**: Zustand
- **Animations**: Framer Motion
- **Audio**: Howler.js for sound effects
- **Icons**: Lucide React
- **Testing**: Vitest with React Testing Library
- **Authentication**: Supabase Auth integration
- **Runtime**: React 19.0.0

### Backend (FastAPI/Python)
- **Location**: `/backend/`
- **Framework**: FastAPI 0.104.1 with Python 3.11+
- **Database**: PostgreSQL with SQLAlchemy 2.0
- **Authentication**: Supabase Auth with advanced security features
- **Security**: MFA, RBAC, field encryption, audit logging
- **Admin System**: User management, analytics dashboard, bulk operations
- **GDPR Compliance**: Data retention, account deletion, privacy controls
- **AI Integration**: OpenAI API + LangChain
- **Caching**: Redis
- **Task Queue**: Celery
- **Testing**: Comprehensive pytest test suite

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
npm run test         # Run Vitest tests
npm run test:ui      # Run Vitest with UI
npm run test:coverage # Run tests with coverage
npm run test:unit    # Run unit tests only
npm run test:components # Run component tests
```

### Backend
```bash
cd backend
# Setup virtual environment first
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # Start development server
pytest               # Run all tests
pytest app/tests/    # Run specific test directory
pytest --coverage    # Run with coverage
```

## Key Dependencies

### Frontend
- **Next.js 15.3.5**: React framework with App Router
- **React 19.0.0**: Latest React with concurrent features
- **Tailwind CSS 4.0**: Utility-first CSS framework
- **Framer Motion**: Animation library
- **Howler.js**: Audio library for sound effects
- **Zustand**: State management
- **Lucide React**: Icon library
- **Vitest**: Fast testing framework
- **React Testing Library**: Component testing utilities
- **Supabase**: Authentication and database client

### Backend
- **FastAPI 0.104.1**: Modern Python web framework
- **SQLAlchemy 2.0**: Database ORM with modern async support
- **PostgreSQL**: Primary database
- **Redis 5.0**: Caching and task queue
- **OpenAI 1.3.7**: AI content generation
- **LangChain**: AI workflow orchestration
- **Supabase 2.0.2**: Authentication and database integration
- **Pydantic 2.11+**: Data validation and settings management
- **PyJWT**: JSON Web Token handling
- **Argon2**: Password hashing
- **Pytest**: Comprehensive testing framework

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

### Security Guidelines
- **Authentication**: Always use MFA for admin accounts
- **Data Protection**: Encrypt sensitive fields at the database level
- **Session Management**: Implement secure session handling with proper expiration
- **Input Validation**: Sanitize all user inputs through middleware
- **Password Security**: Enforce strong password policies with Argon2 hashing
- **Audit Logging**: Log all sensitive operations for compliance
- **GDPR Compliance**: Follow data retention policies and provide data export
- **Rate Limiting**: Implement rate limiting to prevent abuse
- **Authorization**: Use RBAC to control access to admin features

### Testing Guidelines
- **Security Testing**: Test authentication flows and authorization
- **Component Testing**: Use Vitest and React Testing Library
- **API Testing**: Comprehensive pytest coverage for all endpoints
- **Admin Testing**: Test admin dashboard functionality thoroughly
- **Authentication Testing**: Test MFA, password reset, and session management

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
npm run test         # Run Vitest tests
npm run test:ui      # Run Vitest with UI
npm run test:coverage # Run tests with coverage
npm run test:components # Run component tests
```

### Backend Testing
```bash
cd backend
pytest               # Run Python tests
pytest app/tests/    # Run specific test directory
pytest --coverage    # Run with coverage
```

## File Structure

```
/frontend/
├── src/
│   ├── app/         # Next.js App Router pages
│   ├── components/  # Reusable UI components
│   │   ├── auth/    # Authentication components
│   │   ├── admin/   # Admin dashboard components
│   │   └── ui/      # Base UI components
│   ├── stores/      # Zustand state management
│   ├── hooks/       # Custom React hooks
│   ├── lib/         # Utility functions and configurations
│   └── __tests__/   # Test files
├── public/          # Static assets
└── package.json     # Dependencies and scripts

/backend/
├── app/
│   ├── api/         # API routes
│   │   └── auth/    # Modular authentication endpoints
│   ├── core/        # Core functionality and configuration
│   ├── models/      # Database models with security features
│   ├── schemas/     # Pydantic schemas
│   ├── services/    # Business logic services
│   ├── repositories/ # Data access layer
│   ├── middleware/  # Security and validation middleware
│   └── tests/       # Comprehensive test suite
├── alembic/         # Database migrations
├── requirements.txt # Python dependencies
└── scripts/         # Utility scripts

/design-reference/   # Screenshot references for UI implementation
├── landing-page/    # Marketing site screenshots (highest priority)
├── ios/             # iOS app screenshots
└── web/             # Web app screenshots

/docs/               # Project documentation
├── authentication/ # Auth system documentation
└── security/       # Security assessments and guides

/product-requirements/ # Product requirements and planning
├── prds/            # Product requirement documents
└── tasks/           # Task breakdowns and implementation guides
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

### Security Considerations
- **Data Encryption**: All sensitive data encrypted at rest and in transit
- **Session Security**: Secure session management with proper expiration
- **Admin Access Control**: Multi-factor authentication for admin accounts
- **Audit Trail**: Comprehensive logging for compliance and security monitoring
- **Rate Limiting**: Protection against brute force attacks
- **Input Sanitization**: All user inputs sanitized through middleware
- **GDPR Compliance**: Data retention policies and user data export capabilities
- **Security Headers**: Proper security headers in all responses

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

- All documentation files must use kebab-case filenames and be stored in the 'docs' folder or its subfolders.