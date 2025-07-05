"""
Analytics Service

Business logic service for analytics event processing, progress calculations,
and user statistics for the Duolingo clone backend application.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc

from app.models.analytics import AnalyticsEvent, UserProgressSnapshot, UserLearningStats, EventType
from app.models.progress import UserCourse, UserLessonProgress, UserExerciseInteraction
from app.models.user import User
from app.models.course import Course, Lesson
from app.models.exercise import Exercise
from app.schemas.analytics import (
    AnalyticsEventRequest,
    UserProgressResponse,
    CourseCompletionRequest,
    LessonCompletionRequest,
    UserStatsResponse,
    AnalyticsQueryParams,
)


class AnalyticsService:
    """Service class for analytics operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_analytics_event(
        self,
        user_id: str,
        event_request: AnalyticsEventRequest
    ) -> AnalyticsEvent:
        """
        Create a new analytics event.
        
        Args:
            user_id: ID of the user who triggered the event
            event_request: Event data from the request
            
        Returns:
            Created AnalyticsEvent instance
        """
        # Get user context for the event
        user_context = self._get_user_context(user_id, event_request.course_id)
        
        # Create analytics event
        analytics_event = AnalyticsEvent(
            user_id=user_id,
            event_type=event_request.event_type.value,
            event_name=event_request.event_type.value.replace('_', ' ').title(),
            event_category=event_request.event_category.value,
            course_id=str(event_request.course_id) if event_request.course_id else None,
            lesson_id=str(event_request.lesson_id) if event_request.lesson_id else None,
            exercise_id=str(event_request.exercise_id) if event_request.exercise_id else None,
            value=event_request.value,
            duration=event_request.duration,
            is_success=event_request.is_success,
            user_level=user_context.get('level'),
            user_xp=user_context.get('xp'),
            user_streak=user_context.get('streak'),
            session_id=event_request.session_id,
            device_type=event_request.device_type.value if event_request.device_type else None,
            platform=event_request.platform.value if event_request.platform else None,
            event_timestamp=datetime.utcnow()
        )
        
        # Set metadata if provided
        if event_request.event_metadata:
            analytics_event.set_metadata_dict(event_request.event_metadata)
        
        self.db.add(analytics_event)
        self.db.commit()
        self.db.refresh(analytics_event)
        
        return analytics_event
    
    def create_analytics_events_batch(
        self,
        user_id: str,
        events: List[AnalyticsEventRequest]
    ) -> List[AnalyticsEvent]:
        """
        Create multiple analytics events in a batch.
        
        Args:
            user_id: ID of the user who triggered the events
            events: List of event data from the request
            
        Returns:
            List of created AnalyticsEvent instances
        """
        created_events = []
        
        for event_request in events:
            analytics_event = self.create_analytics_event(user_id, event_request)
            created_events.append(analytics_event)
        
        return created_events
    
    def get_user_progress(
        self,
        user_id: str,
        course_id: Optional[str] = None,
        include_global_stats: bool = False
    ) -> UserProgressResponse:
        """
        Get user progress summary.
        
        Args:
            user_id: ID of the user
            course_id: Optional course ID to filter progress
            include_global_stats: Whether to include global statistics
            
        Returns:
            UserProgressResponse with progress data
        """
        # Get user course data
        user_course = None
        if course_id:
            user_course = self.db.query(UserCourse).filter(
                UserCourse.user_id == user_id,
                UserCourse.course_id == course_id
            ).first()
        
        # Get overall user progress
        if include_global_stats or not course_id:
            user_courses = self.db.query(UserCourse).filter(
                UserCourse.user_id == user_id
            ).all()
            
            # Calculate global stats
            total_xp = sum(uc.total_xp for uc in user_courses)
            current_streak = max((uc.current_streak for uc in user_courses), default=0)
            longest_streak = max((uc.longest_streak for uc in user_courses), default=0)
            hearts_remaining = sum(uc.current_hearts for uc in user_courses)
        else:
            total_xp = user_course.total_xp if user_course else 0
            current_streak = user_course.current_streak if user_course else 0
            longest_streak = user_course.longest_streak if user_course else 0
            hearts_remaining = user_course.current_hearts if user_course else 0
        
        # Get lesson progress
        lessons_completed = self._get_lessons_completed(user_id, course_id)
        exercises_completed = self._get_exercises_completed(user_id, course_id)
        
        # Get total study time
        total_study_time = self._get_total_study_time(user_id, course_id)
        
        # Calculate accuracy
        accuracy_percentage = self._calculate_accuracy(user_id, course_id)
        
        # Get activity stats
        days_active = self._get_days_active(user_id, course_id)
        
        # Calculate level and XP to next level
        level = self._calculate_level(total_xp)
        xp_to_next_level = self._calculate_xp_to_next_level(total_xp)
        
        # Calculate completion percentage
        completion_percentage = self._calculate_completion_percentage(user_id, course_id)
        
        # Get last activity date
        last_activity_date = self._get_last_activity_date(user_id, course_id)
        
        return UserProgressResponse(
            user_id=user_id,
            course_id=course_id,
            total_xp=total_xp,
            current_streak=current_streak,
            longest_streak=longest_streak,
            lessons_completed=lessons_completed,
            exercises_completed=exercises_completed,
            total_study_time=total_study_time,
            accuracy_percentage=accuracy_percentage,
            days_active=days_active,
            hearts_remaining=hearts_remaining,
            level=level,
            xp_to_next_level=xp_to_next_level,
            completion_percentage=completion_percentage,
            last_activity_date=last_activity_date,
            created_at=datetime.utcnow()
        )
    
    def track_course_completion(
        self,
        user_id: str,
        completion_request: CourseCompletionRequest
    ) -> Dict[str, Any]:
        """
        Track course completion with analytics.
        
        Args:
            user_id: ID of the user
            completion_request: Course completion data
            
        Returns:
            Dictionary with completion tracking results
        """
        # Create course completion event
        event_request = AnalyticsEventRequest(
            event_type=EventType.COURSE_COMPLETED,
            event_category="learning",
            course_id=completion_request.course_id,
            value=completion_request.final_score,
            duration=completion_request.total_time_spent,
            is_success=True,
            event_metadata=completion_request.metadata
        )
        
        analytics_event = self.create_analytics_event(user_id, event_request)
        
        # Update user course progress
        user_course = self.db.query(UserCourse).filter(
            UserCourse.user_id == user_id,
            UserCourse.course_id == str(completion_request.course_id)
        ).first()
        
        if user_course:
            user_course.completion_percentage = 100.0
            user_course.total_xp += completion_request.total_xp_earned or 0
            self.db.commit()
        
        # Create progress snapshot
        self._create_progress_snapshot(user_id, str(completion_request.course_id))
        
        return {
            'event_id': analytics_event.id,
            'user_id': user_id,
            'course_id': completion_request.course_id,
            'completion_date': completion_request.completion_date or datetime.utcnow(),
            'final_score': completion_request.final_score,
            'total_time_spent': completion_request.total_time_spent or 0,
            'total_xp_earned': completion_request.total_xp_earned or 0,
            'achievements_unlocked': [],  # TODO: Implement achievements
            'created_at': analytics_event.created_at
        }
    
    def track_lesson_completion(
        self,
        user_id: str,
        completion_request: LessonCompletionRequest
    ) -> Dict[str, Any]:
        """
        Track lesson completion with analytics.
        
        Args:
            user_id: ID of the user
            completion_request: Lesson completion data
            
        Returns:
            Dictionary with completion tracking results
        """
        # Create lesson completion event
        event_request = AnalyticsEventRequest(
            event_type=EventType.LESSON_COMPLETE,
            event_category="learning",
            lesson_id=completion_request.lesson_id,
            value=completion_request.score,
            duration=completion_request.time_spent,
            is_success=completion_request.score >= 60.0,  # Passing score threshold
            event_metadata=completion_request.metadata
        )
        
        analytics_event = self.create_analytics_event(user_id, event_request)
        
        # Update lesson progress
        lesson_progress = self.db.query(UserLessonProgress).filter(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == str(completion_request.lesson_id)
        ).first()
        
        if lesson_progress:
            lesson_progress.complete_lesson(
                completion_request.score,
                completion_request.xp_earned,
                completion_request.time_spent
            )
            self.db.commit()
        
        # Calculate accuracy
        accuracy_percentage = 0.0
        if completion_request.exercises_completed > 0:
            accuracy_percentage = (completion_request.exercises_correct / completion_request.exercises_completed) * 100.0
        
        return {
            'event_id': analytics_event.id,
            'user_id': user_id,
            'lesson_id': completion_request.lesson_id,
            'completion_date': completion_request.completion_date or datetime.utcnow(),
            'score': completion_request.score,
            'time_spent': completion_request.time_spent,
            'xp_earned': completion_request.xp_earned,
            'exercises_completed': completion_request.exercises_completed,
            'exercises_correct': completion_request.exercises_correct,
            'accuracy_percentage': accuracy_percentage,
            'hints_used': completion_request.hints_used,
            'hearts_lost': completion_request.hearts_lost,
            'achievements_unlocked': [],  # TODO: Implement achievements
            'created_at': analytics_event.created_at
        }
    
    def get_user_stats(
        self,
        user_id: str,
        course_id: Optional[str] = None,
        include_global_stats: bool = True,
        include_historical: bool = False
    ) -> UserStatsResponse:
        """
        Get comprehensive user statistics.
        
        Args:
            user_id: ID of the user
            course_id: Optional course ID to filter stats
            include_global_stats: Whether to include global statistics
            include_historical: Whether to include historical data
            
        Returns:
            UserStatsResponse with comprehensive statistics
        """
        # Get or create user learning stats
        user_stats = self.db.query(UserLearningStats).filter(
            UserLearningStats.user_id == user_id,
            UserLearningStats.course_id == course_id
        ).first()
        
        if not user_stats:
            user_stats = self._calculate_user_stats(user_id, course_id)
        
        # Get recent progress data
        progress_data = self.get_user_progress(user_id, course_id, include_global_stats)
        
        # Get historical snapshots if requested
        historical_snapshots = None
        if include_historical:
            historical_snapshots = self._get_progress_snapshots(user_id, course_id)
        
        return UserStatsResponse(
            user_id=user_id,
            course_id=course_id,
            total_xp=user_stats.total_xp_earned,
            current_streak=user_stats.current_streak,
            longest_streak=user_stats.best_streak,
            level=self._calculate_level(user_stats.total_xp_earned),
            xp_to_next_level=self._calculate_xp_to_next_level(user_stats.total_xp_earned),
            lessons_completed=user_stats.total_lessons_completed,
            exercises_completed=user_stats.total_exercises_completed,
            courses_completed=self._get_courses_completed(user_id),
            completion_percentage=progress_data.completion_percentage,
            total_study_time=user_stats.total_study_time,
            avg_daily_study_time=user_stats.avg_daily_study_time,
            study_days_count=user_stats.study_days_count,
            total_sessions=user_stats.total_sessions,
            avg_session_duration=user_stats.avg_session_duration,
            overall_accuracy=user_stats.overall_accuracy,
            total_hints_used=user_stats.total_hints_used,
            total_exercises_skipped=user_stats.total_exercises_skipped,
            last_activity_date=user_stats.last_activity_date,
            first_activity_date=user_stats.first_activity_date,
            achievements_earned=0,  # TODO: Implement achievements
            badges_earned=0,  # TODO: Implement badges
            hearts_remaining=progress_data.hearts_remaining,
            historical_snapshots=historical_snapshots,
            last_calculated_at=user_stats.last_calculated_at,
            created_at=user_stats.created_at
        )
    
    def get_analytics_events(
        self,
        user_id: str,
        query_params: AnalyticsQueryParams
    ) -> List[AnalyticsEvent]:
        """
        Get analytics events with filtering.
        
        Args:
            user_id: ID of the user
            query_params: Query parameters for filtering
            
        Returns:
            List of filtered AnalyticsEvent instances
        """
        query = self.db.query(AnalyticsEvent).filter(
            AnalyticsEvent.user_id == user_id
        )
        
        # Apply filters
        if query_params.course_id:
            query = query.filter(AnalyticsEvent.course_id == str(query_params.course_id))
        
        if query_params.lesson_id:
            query = query.filter(AnalyticsEvent.lesson_id == str(query_params.lesson_id))
        
        if query_params.exercise_id:
            query = query.filter(AnalyticsEvent.exercise_id == str(query_params.exercise_id))
        
        if query_params.event_type:
            query = query.filter(AnalyticsEvent.event_type == query_params.event_type.value)
        
        if query_params.event_category:
            query = query.filter(AnalyticsEvent.event_category == query_params.event_category.value)
        
        if query_params.session_id:
            query = query.filter(AnalyticsEvent.session_id == query_params.session_id)
        
        if query_params.device_type:
            query = query.filter(AnalyticsEvent.device_type == query_params.device_type.value)
        
        if query_params.platform:
            query = query.filter(AnalyticsEvent.platform == query_params.platform.value)
        
        if query_params.date_start:
            query = query.filter(AnalyticsEvent.event_timestamp >= query_params.date_start)
        
        if query_params.date_end:
            query = query.filter(AnalyticsEvent.event_timestamp <= query_params.date_end)
        
        # Apply pagination
        query = query.order_by(desc(AnalyticsEvent.event_timestamp))
        query = query.offset(query_params.offset).limit(query_params.limit)
        
        return query.all()
    
    # Private helper methods
    def _get_user_context(self, user_id: str, course_id: Optional[str] = None) -> Dict[str, Any]:
        """Get user context for analytics events."""
        context = {'level': 1, 'xp': 0, 'streak': 0}
        
        if course_id:
            user_course = self.db.query(UserCourse).filter(
                UserCourse.user_id == user_id,
                UserCourse.course_id == course_id
            ).first()
            
            if user_course:
                context['xp'] = user_course.total_xp
                context['streak'] = user_course.current_streak
                context['level'] = self._calculate_level(user_course.total_xp)
        
        return context
    
    def _get_lessons_completed(self, user_id: str, course_id: Optional[str] = None) -> int:
        """Get number of lessons completed by user."""
        query = self.db.query(func.count(UserLessonProgress.id)).filter(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.status == 'completed'
        )
        
        if course_id:
            # Join with lessons to filter by course
            query = query.join(Lesson).filter(Lesson.course_id == course_id)
        
        return query.scalar() or 0
    
    def _get_exercises_completed(self, user_id: str, course_id: Optional[str] = None) -> int:
        """Get number of exercises completed by user."""
        query = self.db.query(func.count(UserExerciseInteraction.id)).filter(
            UserExerciseInteraction.user_id == user_id,
            UserExerciseInteraction.interaction_type == 'complete'
        )
        
        if course_id:
            # Join with exercises and lessons to filter by course
            query = query.join(Exercise).join(Lesson).filter(Lesson.course_id == course_id)
        
        return query.scalar() or 0
    
    def _get_total_study_time(self, user_id: str, course_id: Optional[str] = None) -> int:
        """Get total study time in seconds."""
        query = self.db.query(func.sum(UserLessonProgress.time_spent)).filter(
            UserLessonProgress.user_id == user_id
        )
        
        if course_id:
            query = query.join(Lesson).filter(Lesson.course_id == course_id)
        
        return query.scalar() or 0
    
    def _calculate_accuracy(self, user_id: str, course_id: Optional[str] = None) -> float:
        """Calculate user's accuracy percentage."""
        query = self.db.query(
            func.count(UserExerciseInteraction.id).label('total'),
            func.sum(func.case([(UserExerciseInteraction.is_correct == True, 1)], else_=0)).label('correct')
        ).filter(
            UserExerciseInteraction.user_id == user_id,
            UserExerciseInteraction.interaction_type == 'attempt'
        )
        
        if course_id:
            query = query.join(Exercise).join(Lesson).filter(Lesson.course_id == course_id)
        
        result = query.first()
        
        if result.total and result.total > 0:
            return (result.correct / result.total) * 100.0
        
        return 0.0
    
    def _get_days_active(self, user_id: str, course_id: Optional[str] = None) -> int:
        """Get number of days user has been active."""
        query = self.db.query(func.count(func.distinct(func.date(AnalyticsEvent.event_timestamp)))).filter(
            AnalyticsEvent.user_id == user_id,
            AnalyticsEvent.event_category == 'learning'
        )
        
        if course_id:
            query = query.filter(AnalyticsEvent.course_id == course_id)
        
        return query.scalar() or 0
    
    def _calculate_level(self, total_xp: int) -> int:
        """Calculate user level based on XP."""
        # Simple level calculation: 1000 XP per level
        return max(1, (total_xp // 1000) + 1)
    
    def _calculate_xp_to_next_level(self, total_xp: int) -> int:
        """Calculate XP needed to reach next level."""
        current_level = self._calculate_level(total_xp)
        next_level_xp = current_level * 1000
        return next_level_xp - total_xp
    
    def _calculate_completion_percentage(self, user_id: str, course_id: Optional[str] = None) -> float:
        """Calculate course completion percentage."""
        if not course_id:
            return 0.0
        
        user_course = self.db.query(UserCourse).filter(
            UserCourse.user_id == user_id,
            UserCourse.course_id == course_id
        ).first()
        
        return user_course.completion_percentage if user_course else 0.0
    
    def _get_last_activity_date(self, user_id: str, course_id: Optional[str] = None) -> Optional[datetime]:
        """Get last activity date for user."""
        query = self.db.query(func.max(AnalyticsEvent.event_timestamp)).filter(
            AnalyticsEvent.user_id == user_id
        )
        
        if course_id:
            query = query.filter(AnalyticsEvent.course_id == course_id)
        
        return query.scalar()
    
    def _get_courses_completed(self, user_id: str) -> int:
        """Get number of courses completed by user."""
        return self.db.query(func.count(UserCourse.id)).filter(
            UserCourse.user_id == user_id,
            UserCourse.completion_percentage == 100.0
        ).scalar() or 0
    
    def _calculate_user_stats(self, user_id: str, course_id: Optional[str] = None) -> UserLearningStats:
        """Calculate and store user learning statistics."""
        # Get progress data
        progress_data = self.get_user_progress(user_id, course_id)
        
        # Create new user learning stats
        user_stats = UserLearningStats(
            user_id=user_id,
            course_id=course_id,
            total_study_time=progress_data.total_study_time,
            avg_daily_study_time=progress_data.total_study_time / max(progress_data.days_active, 1),
            study_days_count=progress_data.days_active,
            total_lessons_completed=progress_data.lessons_completed,
            total_exercises_completed=progress_data.exercises_completed,
            total_xp_earned=progress_data.total_xp,
            overall_accuracy=progress_data.accuracy_percentage,
            best_streak=progress_data.longest_streak,
            current_streak=progress_data.current_streak,
            total_sessions=0,  # TODO: Calculate from sessions
            avg_session_duration=0.0,  # TODO: Calculate from sessions
            total_hints_used=0,  # TODO: Calculate from interactions
            total_exercises_skipped=0,  # TODO: Calculate from interactions
            first_activity_date=None,  # TODO: Calculate from events
            last_activity_date=progress_data.last_activity_date,
            last_calculated_at=datetime.utcnow()
        )
        
        self.db.add(user_stats)
        self.db.commit()
        self.db.refresh(user_stats)
        
        return user_stats
    
    def _create_progress_snapshot(self, user_id: str, course_id: str) -> UserProgressSnapshot:
        """Create a progress snapshot for the user."""
        progress_data = self.get_user_progress(user_id, course_id)
        
        snapshot = UserProgressSnapshot(
            user_id=user_id,
            course_id=course_id,
            total_xp=progress_data.total_xp,
            current_streak=progress_data.current_streak,
            lessons_completed=progress_data.lessons_completed,
            exercises_completed=progress_data.exercises_completed,
            total_time_spent=progress_data.total_study_time,
            correct_answers=0,  # TODO: Calculate from interactions
            total_answers=0,  # TODO: Calculate from interactions
            accuracy_percentage=progress_data.accuracy_percentage,
            days_active=progress_data.days_active,
            sessions_count=0,  # TODO: Calculate from sessions
            avg_session_duration=0.0,  # TODO: Calculate from sessions
            hints_used=0,  # TODO: Calculate from interactions
            exercises_skipped=0,  # TODO: Calculate from interactions
            snapshot_date=datetime.utcnow(),
            snapshot_type='daily'
        )
        
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        
        return snapshot
    
    def _get_progress_snapshots(self, user_id: str, course_id: Optional[str] = None) -> List[UserProgressSnapshot]:
        """Get progress snapshots for historical data."""
        query = self.db.query(UserProgressSnapshot).filter(
            UserProgressSnapshot.user_id == user_id
        )
        
        if course_id:
            query = query.filter(UserProgressSnapshot.course_id == course_id)
        
        return query.order_by(desc(UserProgressSnapshot.snapshot_date)).limit(30).all()