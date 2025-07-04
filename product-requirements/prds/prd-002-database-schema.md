# Database Schema PRD - PostgreSQL Design

## Overview

This PRD defines the comprehensive PostgreSQL database schema for the Duolingo clone MVP. The schema supports multi-language courses, flexible course structures, user authentication, progress tracking, gamification features, and detailed analytics. The design prioritizes scalability, data integrity, and performance while maintaining the flexibility to expand beyond the MVP scope.

## Business Context

The database schema serves as the foundation for a language learning platform that must support:
- Multi-language course structure (Spanish for MVP, expandable to other languages)
- Flexible content hierarchy (languages → sections → units → lessons → exercises)
- User authentication with multiple providers (email/password, Google, TikTok)
- Comprehensive progress tracking and gamification (XP, streaks, hearts)
- Detailed analytics and user behavior tracking
- Audio content management for listening exercises

## Goals

### Primary Goals
1. **Scalability**: Support growth from MVP (Spanish language, 5 skills) to full platform (42+ languages)
2. **Flexibility**: Accommodate different course structures and exercise types
3. **Performance**: Ensure sub-3 second response times for all user operations
4. **Data Integrity**: Maintain consistent data relationships and constraints
5. **Analytics**: Enable comprehensive tracking of user learning patterns

### Secondary Goals
1. **Maintainability**: Clear, well-documented schema with logical organization
2. **Extensibility**: Easy addition of new exercise types and features
3. **Audit Trail**: Complete tracking of user actions and system changes
4. **Security**: Proper data protection and access control

## Functional Requirements

### User Management
- **FR-1**: Support multiple authentication methods (email/password, Google, TikTok)
- **FR-2**: Track user profile information (name, email, avatar, preferences)
- **FR-3**: Manage email verification status and password reset tokens
- **FR-4**: Store user preferences and learning goals
- **FR-5**: Implement hard delete functionality for user data

### Course Content Structure
- **FR-6**: Support hierarchical course structure: Languages → Sections → Units → Lessons → Exercises
- **FR-7**: Enable flexible exercise types (translation, multiple choice, listening)
- **FR-8**: Store exercise metadata (difficulty, time estimate, hints)
- **FR-9**: Support reusable exercises across different lessons/skills
- **FR-10**: Track lesson prerequisites and dependencies

### Progress Tracking & Gamification
- **FR-11**: Implement hearts system (5 hearts max, 4-hour regeneration)
- **FR-12**: Track XP earning and daily goals (10-50 XP targets)
- **FR-13**: Maintain streak counters for any XP-earning activity
- **FR-14**: Record detailed exercise performance (time, attempts, accuracy)
- **FR-15**: Store user answers for review and analytics

### Audio & Media Management
- **FR-16**: Store audio file metadata (paths, formats, quality levels)
- **FR-17**: Support multiple audio formats (MP3, WAV, OGG)
- **FR-18**: Enable quality-based audio serving (low/medium/high quality)

### Analytics & Auditing
- **FR-19**: Log all user actions with timestamps
- **FR-20**: Track lesson completion rates and performance metrics
- **FR-21**: Store detailed exercise interaction data
- **FR-22**: Maintain system audit logs for administrative actions

## Non-Functional Requirements

### Performance Requirements
- **NFR-1**: Database queries must complete within 100ms for 95% of operations
- **NFR-2**: Support concurrent access for 1000+ users during MVP
- **NFR-3**: Horizontal scaling capability for future growth
- **NFR-4**: Efficient indexing for all frequently queried fields

### Security Requirements
- **NFR-5**: All sensitive data must be encrypted at rest
- **NFR-6**: Password hashing using bcrypt with minimum 12 rounds
- **NFR-7**: Secure storage of OAuth tokens and session data
- **NFR-8**: Row-level security for user data access

### Availability Requirements
- **NFR-9**: 99.9% uptime target for database operations
- **NFR-10**: Automated backup every 6 hours with 30-day retention
- **NFR-11**: Point-in-time recovery capability
- **NFR-12**: Database replication for high availability

## Technical Specifications

### Database Architecture

```sql
-- Core Database Tables and Relationships

-- ================================
-- USER MANAGEMENT
-- ================================

-- Users table with authentication support
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255), -- NULL for OAuth-only users
    name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    is_email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    password_reset_token VARCHAR(255),
    password_reset_expires_at TIMESTAMPTZ,
    daily_xp_goal INTEGER DEFAULT 20 CHECK (daily_xp_goal IN (10, 20, 30, 50)),
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ -- For soft delete if needed
);

-- OAuth providers for social login
CREATE TABLE oauth_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL, -- 'google', 'tiktok', 'facebook'
    provider_user_id VARCHAR(255) NOT NULL,
    access_token VARCHAR(1000),
    refresh_token VARCHAR(1000),
    token_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider, provider_user_id)
);

-- ================================
-- COURSE CONTENT STRUCTURE
-- ================================

-- Languages (e.g., Spanish, French, German)
CREATE TABLE languages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(10) UNIQUE NOT NULL, -- 'es', 'fr', 'de'
    name VARCHAR(100) NOT NULL, -- 'Spanish', 'French', 'German'
    native_name VARCHAR(100), -- 'Español', 'Français', 'Deutsch'
    flag_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Courses (e.g., Spanish for English speakers)
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_language_id UUID NOT NULL REFERENCES languages(id),
    to_language_id UUID NOT NULL REFERENCES languages(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty_level VARCHAR(20) DEFAULT 'beginner', -- 'beginner', 'intermediate', 'advanced'
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(from_language_id, to_language_id)
);

-- Sections (major divisions within courses, e.g., "Basic 1", "Greetings")
CREATE TABLE sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sort_order INTEGER NOT NULL,
    cefr_level VARCHAR(10), -- 'A1', 'A2', 'B1', 'B2', 'C1', 'C2'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(course_id, sort_order)
);

-- Units (individual learning units within sections)
CREATE TABLE units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sort_order INTEGER NOT NULL,
    icon_url VARCHAR(500),
    color VARCHAR(7), -- Hex color code
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(section_id, sort_order)
);

-- Lessons (individual lessons within units)
CREATE TABLE lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sort_order INTEGER NOT NULL,
    estimated_minutes INTEGER DEFAULT 5,
    xp_reward INTEGER DEFAULT 20,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(unit_id, sort_order)
);

-- Lesson prerequisites (defines lesson dependencies)
CREATE TABLE lesson_prerequisites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    prerequisite_lesson_id UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(lesson_id, prerequisite_lesson_id),
    CHECK (lesson_id != prerequisite_lesson_id)
);

-- Exercise types (translation, multiple_choice, listening, etc.)
CREATE TABLE exercise_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE, -- 'translation', 'multiple_choice', 'listening'
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Exercises (individual practice items)
CREATE TABLE exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exercise_type_id UUID NOT NULL REFERENCES exercise_types(id),
    prompt TEXT NOT NULL, -- The question or instruction
    correct_answer TEXT NOT NULL, -- The correct answer
    alternative_answers JSONB, -- Alternative correct answers
    explanation TEXT, -- Explanation for the answer
    hint TEXT, -- Hint to help users
    difficulty_level INTEGER DEFAULT 1 CHECK (difficulty_level BETWEEN 1 AND 5),
    estimated_seconds INTEGER DEFAULT 30,
    audio_url VARCHAR(500), -- For listening exercises
    image_url VARCHAR(500), -- For visual exercises
    metadata JSONB, -- Additional exercise-specific data
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Multiple choice options (for multiple choice exercises)
CREATE TABLE exercise_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exercise_id UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    option_text TEXT NOT NULL,
    is_correct BOOLEAN DEFAULT FALSE,
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(exercise_id, sort_order)
);

-- Lesson exercises (many-to-many relationship)
CREATE TABLE lesson_exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(lesson_id, exercise_id),
    UNIQUE(lesson_id, sort_order)
);

-- ================================
-- AUDIO & MEDIA MANAGEMENT
-- ================================

-- Audio files for exercises
CREATE TABLE audio_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exercise_id UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    file_path VARCHAR(500) NOT NULL,
    file_format VARCHAR(10) NOT NULL, -- 'mp3', 'wav', 'ogg'
    quality_level VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high'
    file_size_bytes BIGINT,
    duration_seconds INTEGER,
    sample_rate INTEGER,
    bit_rate INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ================================
-- USER PROGRESS & GAMIFICATION
-- ================================

-- User course enrollment
CREATE TABLE user_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),
    total_xp INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    hearts INTEGER DEFAULT 5 CHECK (hearts BETWEEN 0 AND 5),
    hearts_last_full_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, course_id)
);

-- User lesson progress
CREATE TABLE user_lesson_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lesson_id UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'locked', -- 'locked', 'available', 'in_progress', 'completed'
    completion_count INTEGER DEFAULT 0, -- Number of times completed
    best_score INTEGER DEFAULT 0, -- Best percentage score
    total_attempts INTEGER DEFAULT 0,
    total_time_seconds INTEGER DEFAULT 0,
    xp_earned INTEGER DEFAULT 0,
    hearts_lost INTEGER DEFAULT 0,
    first_completed_at TIMESTAMPTZ,
    last_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, lesson_id)
);

-- User exercise interactions (detailed tracking)
CREATE TABLE user_exercise_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    lesson_id UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    user_answer TEXT,
    is_correct BOOLEAN NOT NULL,
    attempt_number INTEGER DEFAULT 1,
    time_spent_seconds INTEGER DEFAULT 0,
    hints_used INTEGER DEFAULT 0,
    hearts_lost INTEGER DEFAULT 0,
    xp_earned INTEGER DEFAULT 0,
    interaction_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily XP tracking for streaks
CREATE TABLE user_daily_xp (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    xp_earned INTEGER DEFAULT 0,
    goal_met BOOLEAN DEFAULT FALSE,
    activities_completed INTEGER DEFAULT 0,
    time_spent_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Hearts regeneration tracking
CREATE TABLE user_hearts_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL, -- 'lost', 'gained', 'regenerated'
    hearts_before INTEGER NOT NULL,
    hearts_after INTEGER NOT NULL,
    reason VARCHAR(100), -- 'incorrect_answer', 'time_regeneration', 'practice_completed'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ================================
-- ACHIEVEMENTS & REWARDS
-- ================================

-- Achievement definitions
CREATE TABLE achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    icon_url VARCHAR(500),
    condition_type VARCHAR(50) NOT NULL, -- 'lesson_count', 'streak_days', 'xp_total', 'perfect_lessons'
    condition_value INTEGER NOT NULL,
    xp_reward INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User achievements
CREATE TABLE user_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_id UUID NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
    earned_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, achievement_id)
);

-- ================================
-- AUDIT & ANALYTICS
-- ================================

-- User activity audit log
CREATE TABLE user_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(100) NOT NULL, -- 'login', 'lesson_start', 'lesson_complete', 'exercise_answer'
    activity_data JSONB, -- Flexible data storage for activity details
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- System audit log
CREATE TABLE system_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL, -- 'user_delete', 'course_update', 'exercise_create'
    table_name VARCHAR(100),
    record_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ================================
-- INDEXES FOR PERFORMANCE
-- ================================

-- User table indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_deleted_at ON users(deleted_at) WHERE deleted_at IS NOT NULL;

-- OAuth providers indexes
CREATE INDEX idx_oauth_providers_user_id ON oauth_providers(user_id);
CREATE INDEX idx_oauth_providers_provider_user_id ON oauth_providers(provider, provider_user_id);

-- Course structure indexes
CREATE INDEX idx_courses_from_language ON courses(from_language_id);
CREATE INDEX idx_courses_to_language ON courses(to_language_id);
CREATE INDEX idx_sections_course_id ON sections(course_id);
CREATE INDEX idx_sections_sort_order ON sections(course_id, sort_order);
CREATE INDEX idx_units_section_id ON units(section_id);
CREATE INDEX idx_units_sort_order ON units(section_id, sort_order);
CREATE INDEX idx_lessons_unit_id ON lessons(unit_id);
CREATE INDEX idx_lessons_sort_order ON lessons(unit_id, sort_order);

-- Exercise indexes
CREATE INDEX idx_exercises_type ON exercises(exercise_type_id);
CREATE INDEX idx_exercises_difficulty ON exercises(difficulty_level);
CREATE INDEX idx_lesson_exercises_lesson_id ON lesson_exercises(lesson_id);
CREATE INDEX idx_lesson_exercises_exercise_id ON lesson_exercises(exercise_id);
CREATE INDEX idx_exercise_options_exercise_id ON exercise_options(exercise_id);

-- Audio files indexes
CREATE INDEX idx_audio_files_exercise_id ON audio_files(exercise_id);
CREATE INDEX idx_audio_files_quality ON audio_files(quality_level);

-- User progress indexes
CREATE INDEX idx_user_courses_user_id ON user_courses(user_id);
CREATE INDEX idx_user_courses_course_id ON user_courses(course_id);
CREATE INDEX idx_user_courses_last_active ON user_courses(last_active_at);
CREATE INDEX idx_user_lesson_progress_user_id ON user_lesson_progress(user_id);
CREATE INDEX idx_user_lesson_progress_lesson_id ON user_lesson_progress(lesson_id);
CREATE INDEX idx_user_lesson_progress_status ON user_lesson_progress(status);

-- User interactions indexes
CREATE INDEX idx_user_exercise_interactions_user_id ON user_exercise_interactions(user_id);
CREATE INDEX idx_user_exercise_interactions_exercise_id ON user_exercise_interactions(exercise_id);
CREATE INDEX idx_user_exercise_interactions_lesson_id ON user_exercise_interactions(lesson_id);
CREATE INDEX idx_user_exercise_interactions_date ON user_exercise_interactions(interaction_at);

-- Daily XP indexes
CREATE INDEX idx_user_daily_xp_user_id ON user_daily_xp(user_id);
CREATE INDEX idx_user_daily_xp_date ON user_daily_xp(date);
CREATE INDEX idx_user_daily_xp_user_date ON user_daily_xp(user_id, date);

-- Hearts log indexes
CREATE INDEX idx_user_hearts_log_user_id ON user_hearts_log(user_id);
CREATE INDEX idx_user_hearts_log_created_at ON user_hearts_log(created_at);

-- Achievements indexes
CREATE INDEX idx_user_achievements_user_id ON user_achievements(user_id);
CREATE INDEX idx_user_achievements_achievement_id ON user_achievements(achievement_id);

-- Audit log indexes
CREATE INDEX idx_user_activity_log_user_id ON user_activity_log(user_id);
CREATE INDEX idx_user_activity_log_activity_type ON user_activity_log(activity_type);
CREATE INDEX idx_user_activity_log_created_at ON user_activity_log(created_at);
CREATE INDEX idx_system_audit_log_admin_user_id ON system_audit_log(admin_user_id);
CREATE INDEX idx_system_audit_log_table_name ON system_audit_log(table_name);
CREATE INDEX idx_system_audit_log_created_at ON system_audit_log(created_at);

-- ================================
-- TRIGGERS FOR AUTOMATION
-- ================================

-- Update timestamps trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_oauth_providers_updated_at BEFORE UPDATE ON oauth_providers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_languages_updated_at BEFORE UPDATE ON languages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_courses_updated_at BEFORE UPDATE ON courses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sections_updated_at BEFORE UPDATE ON sections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_units_updated_at BEFORE UPDATE ON units
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lessons_updated_at BEFORE UPDATE ON lessons
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_exercises_updated_at BEFORE UPDATE ON exercises
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_audio_files_updated_at BEFORE UPDATE ON audio_files
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_courses_updated_at BEFORE UPDATE ON user_courses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_lesson_progress_updated_at BEFORE UPDATE ON user_lesson_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_daily_xp_updated_at BEFORE UPDATE ON user_daily_xp
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_achievements_updated_at BEFORE UPDATE ON achievements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================
-- INITIAL DATA SETUP
-- ================================

-- Insert initial languages
INSERT INTO languages (code, name, native_name, is_active, sort_order) VALUES
('en', 'English', 'English', true, 1),
('es', 'Spanish', 'Español', true, 2),
('fr', 'French', 'Français', true, 3),
('de', 'German', 'Deutsch', true, 4),
('it', 'Italian', 'Italiano', true, 5),
('pt', 'Portuguese', 'Português', true, 6);

-- Insert initial exercise types
INSERT INTO exercise_types (name, description, is_active) VALUES
('translation', 'Translate text from one language to another', true),
('multiple_choice', 'Choose the correct answer from multiple options', true),
('listening', 'Listen to audio and provide the correct response', true),
('speaking', 'Speak the correct pronunciation', false),
('writing', 'Write the correct text', false);

-- Insert initial achievements
INSERT INTO achievements (name, description, condition_type, condition_value, xp_reward, is_active) VALUES
('First Lesson', 'Complete your first lesson', 'lesson_count', 1, 50, true),
('Week Warrior', 'Maintain a 7-day streak', 'streak_days', 7, 100, true),
('Perfect Practice', 'Complete a lesson with no mistakes', 'perfect_lessons', 1, 75, true),
('XP Collector', 'Earn 50 total XP', 'xp_total', 50, 25, true),
('Skill Master', 'Complete your first skill', 'skills_completed', 1, 200, true);
```

## Implementation Details

### Database Connection and Configuration
- **Connection Pool**: Configure connection pooling with minimum 5, maximum 20 connections
- **SSL Mode**: Require SSL connections in production
- **Character Set**: UTF-8 encoding for international character support
- **Collation**: Use case-insensitive collation for text searches

### Data Validation Rules
- **Email Validation**: Enforce valid email format using CHECK constraints
- **Password Strength**: Minimum 8 characters with complexity requirements
- **XP Values**: Ensure non-negative XP values with appropriate maximums
- **Hearts System**: Enforce 0-5 hearts range with regeneration logic
- **Streak Calculation**: Automatic streak increments based on daily XP goals

### Backup and Recovery Strategy
- **Automated Backups**: Daily full backups with 30-day retention
- **Point-in-Time Recovery**: 7-day recovery window for data restoration
- **Replication**: Master-slave replication for high availability
- **Monitoring**: Database performance monitoring with alerting

## Dependencies

### Technical Dependencies
- **PostgreSQL**: Version 14+ for advanced features and performance
- **pgcrypto**: Extension for UUID generation and encryption
- **pg_stat_statements**: Extension for query performance monitoring
- **Connection Pooling**: PgBouncer or similar for connection management

### Development Dependencies
- **Alembic**: Database migration management
- **SQLAlchemy**: ORM for Python backend integration
- **psycopg2**: PostgreSQL adapter for Python
- **Database Seeding**: Scripts for initial data population

### Infrastructure Dependencies
- **Cloud Provider**: AWS RDS, Google Cloud SQL, or Railway PostgreSQL
- **Monitoring**: DataDog, New Relic, or built-in cloud monitoring
- **Backup Storage**: S3 or equivalent for backup storage
- **Security**: SSL certificates and encrypted connections

## Acceptance Criteria

### Schema Validation
- **AC-1**: All table relationships must enforce referential integrity
- **AC-2**: Database must support concurrent connections without deadlocks
- **AC-3**: All indexes must improve query performance by >50%
- **AC-4**: Schema must validate against all required constraints

### Performance Benchmarks
- **AC-5**: User authentication queries complete within 50ms
- **AC-6**: Exercise loading queries complete within 100ms
- **AC-7**: Progress tracking updates complete within 200ms
- **AC-8**: Analytics queries complete within 500ms

### Data Integrity
- **AC-9**: All user data must be recoverable from backups
- **AC-10**: Audit logs must capture all critical user actions
- **AC-11**: Hearts regeneration logic must be mathematically consistent
- **AC-12**: Streak calculations must handle timezone changes correctly

### Scalability Requirements
- **AC-13**: Schema must support 10,000+ users without performance degradation
- **AC-14**: Database must handle 1,000+ concurrent connections
- **AC-15**: Storage must accommodate 1TB+ of user data and content
- **AC-16**: Query performance must remain consistent as data grows

## Testing Strategy

### Unit Testing
- **Schema Validation**: Test all constraints and relationships
- **Data Types**: Validate all field types and sizes
- **Triggers**: Test all automated triggers and functions
- **Indexes**: Verify index effectiveness and coverage

### Integration Testing
- **API Integration**: Test all database operations through API endpoints
- **Transaction Testing**: Validate ACID properties and transaction isolation
- **Migration Testing**: Test all database migrations and rollbacks
- **Backup Testing**: Validate backup and recovery procedures

### Performance Testing
- **Load Testing**: Simulate 1,000+ concurrent users
- **Stress Testing**: Test database limits and failure modes
- **Query Optimization**: Analyze and optimize slow queries
- **Capacity Planning**: Test storage and connection limits

### Security Testing
- **Access Control**: Test row-level security and permissions
- **Injection Testing**: Validate SQL injection prevention
- **Encryption**: Test data encryption at rest and in transit
- **Audit Compliance**: Verify audit log completeness and integrity

## Deployment Considerations

### Environment Configuration
- **Development**: Local PostgreSQL with sample data
- **Staging**: Cloud database with production-like data
- **Production**: High-availability setup with monitoring

### Migration Strategy
- **Database Migrations**: Use Alembic for version-controlled schema changes
- **Data Seeding**: Automated scripts for initial data population
- **Rollback Procedures**: Tested rollback plans for failed deployments
- **Zero-Downtime**: Blue-green deployment strategy for schema updates

### Monitoring and Alerting
- **Performance Monitoring**: Query performance and resource usage
- **Error Alerting**: Database errors and connection issues
- **Capacity Monitoring**: Storage usage and connection limits
- **Backup Monitoring**: Backup success and recovery testing

## Timeline

### Week 1: Foundation (Days 1-7)
- **Day 1-2**: Database setup and basic schema creation
- **Day 3-4**: User management and authentication tables
- **Day 5-6**: Course structure and content tables
- **Day 7**: Initial data seeding and testing

### Week 2: Advanced Features (Days 8-14)
- **Day 8-9**: Progress tracking and gamification tables
- **Day 10-11**: Audio and media management tables
- **Day 12-13**: Audit and analytics tables
- **Day 14**: Performance optimization and indexing

### Week 3: Testing and Deployment (Days 15-21)
- **Day 15-16**: Comprehensive testing and validation
- **Day 17-18**: Performance tuning and optimization
- **Day 19-20**: Production deployment and monitoring setup
- **Day 21**: Final validation and documentation

## Risk Mitigation

### Technical Risks
- **Data Loss**: Automated backups and replication
- **Performance Issues**: Comprehensive indexing and query optimization
- **Scaling Challenges**: Horizontal scaling preparation and connection pooling
- **Security Vulnerabilities**: Regular security audits and updates

### Operational Risks
- **Migration Failures**: Tested rollback procedures and staging validation
- **Downtime**: High-availability setup and maintenance windows
- **Data Corruption**: Integrity checks and recovery procedures
- **Compliance Issues**: Audit trails and data retention policies

## Success Metrics

### Performance Metrics
- **Query Response Time**: <100ms for 95% of queries
- **Concurrent Users**: Support 1,000+ simultaneous connections
- **Uptime**: 99.9% availability target
- **Data Integrity**: Zero data loss incidents

### Business Metrics
- **User Growth**: Database scales with user acquisition
- **Feature Adoption**: Analytics enable feature usage tracking
- **Learning Outcomes**: Progress tracking enables learning analytics
- **Retention**: Gamification data supports user retention strategies

This comprehensive database schema provides the foundation for a scalable, performant, and feature-rich language learning platform while maintaining the flexibility to grow beyond the MVP scope.