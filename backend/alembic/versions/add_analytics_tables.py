"""add_analytics_tables

Revision ID: add_analytics_tables
Revises: e6734d9e75b4
Create Date: 2025-01-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.types import TypeDecorator, CHAR


# revision identifiers, used by Alembic.
revision = 'add_analytics_tables'
down_revision = 'e6734d9e75b4'
branch_labels = None
depends_on = None


class UUID(TypeDecorator):
    """Platform-independent UUID type."""
    impl = CHAR
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))


def upgrade():
    """Create analytics tables."""
    
    # Create analytics_events table
    op.create_table(
        'analytics_events',
        sa.Column('id', UUID(), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_name', sa.String(100), nullable=False),
        sa.Column('event_category', sa.String(50), nullable=False),
        sa.Column('course_id', sa.String(36), sa.ForeignKey('courses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('lesson_id', sa.String(36), sa.ForeignKey('lessons.id', ondelete='SET NULL'), nullable=True),
        sa.Column('exercise_id', sa.String(36), sa.ForeignKey('exercises.id', ondelete='SET NULL'), nullable=True),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('is_success', sa.Boolean(), nullable=True),
        sa.Column('user_level', sa.Integer(), nullable=True),
        sa.Column('user_xp', sa.Integer(), nullable=True),
        sa.Column('user_streak', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(36), nullable=True),
        sa.Column('device_type', sa.String(20), nullable=True),
        sa.Column('platform', sa.String(20), nullable=True),
        sa.Column('event_metadata', sa.Text(), nullable=True),
        sa.Column('event_timestamp', sa.DateTime(), nullable=False),
        sa.CheckConstraint('duration >= 0', name='check_duration_non_negative'),
        sa.CheckConstraint('user_level >= 0', name='check_user_level_non_negative'),
        sa.CheckConstraint('user_xp >= 0', name='check_user_xp_non_negative'),
        sa.CheckConstraint('user_streak >= 0', name='check_user_streak_non_negative'),
    )
    
    # Create indexes for analytics_events
    op.create_index('idx_analytics_events_user_id', 'analytics_events', ['user_id'])
    op.create_index('idx_analytics_events_event_type', 'analytics_events', ['event_type'])
    op.create_index('idx_analytics_events_event_category', 'analytics_events', ['event_category'])
    op.create_index('idx_analytics_events_course_id', 'analytics_events', ['course_id'])
    op.create_index('idx_analytics_events_lesson_id', 'analytics_events', ['lesson_id'])
    op.create_index('idx_analytics_events_exercise_id', 'analytics_events', ['exercise_id'])
    op.create_index('idx_analytics_events_session_id', 'analytics_events', ['session_id'])
    op.create_index('idx_analytics_events_event_timestamp', 'analytics_events', ['event_timestamp'])
    op.create_index('idx_user_event_type_timestamp', 'analytics_events', ['user_id', 'event_type', 'event_timestamp'])
    op.create_index('idx_event_category_timestamp', 'analytics_events', ['event_category', 'event_timestamp'])
    op.create_index('idx_course_event_timestamp', 'analytics_events', ['course_id', 'event_timestamp'])
    op.create_index('idx_lesson_event_timestamp', 'analytics_events', ['lesson_id', 'event_timestamp'])
    op.create_index('idx_session_timestamp', 'analytics_events', ['session_id', 'event_timestamp'])
    
    # Create user_progress_snapshots table
    op.create_table(
        'user_progress_snapshots',
        sa.Column('id', UUID(), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('course_id', sa.String(36), sa.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('total_xp', sa.Integer(), default=0, nullable=False),
        sa.Column('current_streak', sa.Integer(), default=0, nullable=False),
        sa.Column('lessons_completed', sa.Integer(), default=0, nullable=False),
        sa.Column('exercises_completed', sa.Integer(), default=0, nullable=False),
        sa.Column('total_time_spent', sa.Integer(), default=0, nullable=False),
        sa.Column('correct_answers', sa.Integer(), default=0, nullable=False),
        sa.Column('total_answers', sa.Integer(), default=0, nullable=False),
        sa.Column('accuracy_percentage', sa.Float(), default=0.0, nullable=False),
        sa.Column('days_active', sa.Integer(), default=0, nullable=False),
        sa.Column('sessions_count', sa.Integer(), default=0, nullable=False),
        sa.Column('avg_session_duration', sa.Float(), default=0.0, nullable=False),
        sa.Column('hints_used', sa.Integer(), default=0, nullable=False),
        sa.Column('exercises_skipped', sa.Integer(), default=0, nullable=False),
        sa.Column('snapshot_date', sa.DateTime(), nullable=False),
        sa.Column('snapshot_type', sa.String(20), default='daily', nullable=False),
        sa.UniqueConstraint('user_id', 'course_id', 'snapshot_date', 'snapshot_type', name='unique_user_course_snapshot'),
        sa.CheckConstraint('total_xp >= 0', name='check_total_xp_non_negative'),
        sa.CheckConstraint('current_streak >= 0', name='check_current_streak_non_negative'),
        sa.CheckConstraint('lessons_completed >= 0', name='check_lessons_completed_non_negative'),
        sa.CheckConstraint('exercises_completed >= 0', name='check_exercises_completed_non_negative'),
        sa.CheckConstraint('total_time_spent >= 0', name='check_total_time_spent_non_negative'),
        sa.CheckConstraint('correct_answers >= 0', name='check_correct_answers_non_negative'),
        sa.CheckConstraint('total_answers >= 0', name='check_total_answers_non_negative'),
        sa.CheckConstraint('accuracy_percentage >= 0.0', name='check_accuracy_percentage_min'),
        sa.CheckConstraint('accuracy_percentage <= 100.0', name='check_accuracy_percentage_max'),
        sa.CheckConstraint('days_active >= 0', name='check_days_active_non_negative'),
        sa.CheckConstraint('sessions_count >= 0', name='check_sessions_count_non_negative'),
        sa.CheckConstraint('avg_session_duration >= 0.0', name='check_avg_session_duration_non_negative'),
        sa.CheckConstraint('hints_used >= 0', name='check_hints_used_non_negative'),
        sa.CheckConstraint('exercises_skipped >= 0', name='check_exercises_skipped_non_negative'),
    )
    
    # Create indexes for user_progress_snapshots
    op.create_index('idx_user_progress_snapshots_user_id', 'user_progress_snapshots', ['user_id'])
    op.create_index('idx_user_progress_snapshots_course_id', 'user_progress_snapshots', ['course_id'])
    op.create_index('idx_user_progress_snapshots_snapshot_date', 'user_progress_snapshots', ['snapshot_date'])
    op.create_index('idx_user_snapshot_date', 'user_progress_snapshots', ['user_id', 'snapshot_date'])
    op.create_index('idx_course_snapshot_date', 'user_progress_snapshots', ['course_id', 'snapshot_date'])
    op.create_index('idx_snapshot_type_date', 'user_progress_snapshots', ['snapshot_type', 'snapshot_date'])
    
    # Create user_learning_stats table
    op.create_table(
        'user_learning_stats',
        sa.Column('id', UUID(), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('course_id', sa.String(36), sa.ForeignKey('courses.id', ondelete='CASCADE'), nullable=True),
        sa.Column('total_study_time', sa.Integer(), default=0, nullable=False),
        sa.Column('avg_daily_study_time', sa.Float(), default=0.0, nullable=False),
        sa.Column('study_days_count', sa.Integer(), default=0, nullable=False),
        sa.Column('total_lessons_completed', sa.Integer(), default=0, nullable=False),
        sa.Column('total_exercises_completed', sa.Integer(), default=0, nullable=False),
        sa.Column('total_xp_earned', sa.Integer(), default=0, nullable=False),
        sa.Column('overall_accuracy', sa.Float(), default=0.0, nullable=False),
        sa.Column('best_streak', sa.Integer(), default=0, nullable=False),
        sa.Column('current_streak', sa.Integer(), default=0, nullable=False),
        sa.Column('total_sessions', sa.Integer(), default=0, nullable=False),
        sa.Column('avg_session_duration', sa.Float(), default=0.0, nullable=False),
        sa.Column('total_hints_used', sa.Integer(), default=0, nullable=False),
        sa.Column('total_exercises_skipped', sa.Integer(), default=0, nullable=False),
        sa.Column('first_activity_date', sa.DateTime(), nullable=True),
        sa.Column('last_activity_date', sa.DateTime(), nullable=True),
        sa.Column('last_calculated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'course_id', name='unique_user_course_stats'),
        sa.CheckConstraint('total_study_time >= 0', name='check_total_study_time_non_negative'),
        sa.CheckConstraint('avg_daily_study_time >= 0.0', name='check_avg_daily_study_time_non_negative'),
        sa.CheckConstraint('study_days_count >= 0', name='check_study_days_count_non_negative'),
        sa.CheckConstraint('total_lessons_completed >= 0', name='check_total_lessons_completed_non_negative'),
        sa.CheckConstraint('total_exercises_completed >= 0', name='check_total_exercises_completed_non_negative'),
        sa.CheckConstraint('total_xp_earned >= 0', name='check_total_xp_earned_non_negative'),
        sa.CheckConstraint('overall_accuracy >= 0.0', name='check_overall_accuracy_min'),
        sa.CheckConstraint('overall_accuracy <= 100.0', name='check_overall_accuracy_max'),
        sa.CheckConstraint('best_streak >= 0', name='check_best_streak_non_negative'),
        sa.CheckConstraint('current_streak >= 0', name='check_current_streak_non_negative'),
        sa.CheckConstraint('total_sessions >= 0', name='check_total_sessions_non_negative'),
        sa.CheckConstraint('avg_session_duration >= 0.0', name='check_avg_session_duration_non_negative'),
        sa.CheckConstraint('total_hints_used >= 0', name='check_total_hints_used_non_negative'),
        sa.CheckConstraint('total_exercises_skipped >= 0', name='check_total_exercises_skipped_non_negative'),
    )
    
    # Create indexes for user_learning_stats
    op.create_index('idx_user_learning_stats_user_id', 'user_learning_stats', ['user_id'])
    op.create_index('idx_user_learning_stats_course_id', 'user_learning_stats', ['course_id'])
    op.create_index('idx_user_last_calculated', 'user_learning_stats', ['user_id', 'last_calculated_at'])
    op.create_index('idx_course_last_calculated', 'user_learning_stats', ['course_id', 'last_calculated_at'])


def downgrade():
    """Drop analytics tables."""
    
    # Drop indexes first
    op.drop_index('idx_course_last_calculated', table_name='user_learning_stats')
    op.drop_index('idx_user_last_calculated', table_name='user_learning_stats')
    op.drop_index('idx_user_learning_stats_course_id', table_name='user_learning_stats')
    op.drop_index('idx_user_learning_stats_user_id', table_name='user_learning_stats')
    
    op.drop_index('idx_snapshot_type_date', table_name='user_progress_snapshots')
    op.drop_index('idx_course_snapshot_date', table_name='user_progress_snapshots')
    op.drop_index('idx_user_snapshot_date', table_name='user_progress_snapshots')
    op.drop_index('idx_user_progress_snapshots_snapshot_date', table_name='user_progress_snapshots')
    op.drop_index('idx_user_progress_snapshots_course_id', table_name='user_progress_snapshots')
    op.drop_index('idx_user_progress_snapshots_user_id', table_name='user_progress_snapshots')
    
    op.drop_index('idx_session_timestamp', table_name='analytics_events')
    op.drop_index('idx_lesson_event_timestamp', table_name='analytics_events')
    op.drop_index('idx_course_event_timestamp', table_name='analytics_events')
    op.drop_index('idx_event_category_timestamp', table_name='analytics_events')
    op.drop_index('idx_user_event_type_timestamp', table_name='analytics_events')
    op.drop_index('idx_analytics_events_event_timestamp', table_name='analytics_events')
    op.drop_index('idx_analytics_events_session_id', table_name='analytics_events')
    op.drop_index('idx_analytics_events_exercise_id', table_name='analytics_events')
    op.drop_index('idx_analytics_events_lesson_id', table_name='analytics_events')
    op.drop_index('idx_analytics_events_course_id', table_name='analytics_events')
    op.drop_index('idx_analytics_events_event_category', table_name='analytics_events')
    op.drop_index('idx_analytics_events_event_type', table_name='analytics_events')
    op.drop_index('idx_analytics_events_user_id', table_name='analytics_events')
    
    # Drop tables
    op.drop_table('user_learning_stats')
    op.drop_table('user_progress_snapshots')
    op.drop_table('analytics_events')