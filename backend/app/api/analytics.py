"""
Analytics API Endpoints

FastAPI endpoints for analytics event tracking, user progress, and statistics
for the Duolingo clone backend application.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

from app.api.deps import get_db, get_current_user, require_admin_role
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    AnalyticsEventRequest,
    AnalyticsEventBatchRequest,
    AnalyticsEventResponse,
    UserProgressRequest,
    UserProgressResponse,
    CourseCompletionRequest,
    CourseCompletionResponse,
    LessonCompletionRequest,
    LessonCompletionResponse,
    UserStatsRequest,
    UserStatsResponse,
    AnalyticsMetricsResponse,
    AnalyticsErrorResponse,
    AnalyticsQueryParams,
    EventTypeEnum,
    EventCategoryEnum,
    DeviceTypeEnum,
    PlatformEnum,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post(
    "/events",
    response_model=AnalyticsEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track Learning Event",
    description="Record a single learning analytics event for the authenticated user"
)
async def track_analytics_event(
    event: AnalyticsEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalyticsEventResponse:
    """
    Track a single analytics event.
    
    Records learning events such as lesson starts, completions, exercise attempts,
    and other user interactions for analytics and personalization.
    
    Args:
        event: Analytics event data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Created analytics event with metadata
        
    Raises:
        HTTPException: If event creation fails
    """
    try:
        analytics_service = AnalyticsService(db)
        created_event = analytics_service.create_analytics_event(
            str(current_user.id),
            event
        )
        
        return AnalyticsEventResponse.from_orm(created_event)
        
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event data: constraint violation"
        )
    except OperationalError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error"
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create analytics event: {str(e)}"
        )


@router.post(
    "/events/batch",
    response_model=List[AnalyticsEventResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Track Multiple Learning Events",
    description="Record multiple learning analytics events in a single batch for the authenticated user"
)
async def track_analytics_events_batch(
    events_batch: AnalyticsEventBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[AnalyticsEventResponse]:
    """
    Track multiple analytics events in a batch.
    
    Efficiently records multiple learning events to reduce API calls
    and improve performance for client applications.
    
    Args:
        events_batch: Batch of analytics events data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List of created analytics events with metadata
        
    Raises:
        HTTPException: If batch creation fails
    """
    try:
        analytics_service = AnalyticsService(db)
        created_events = analytics_service.create_analytics_events_batch(
            str(current_user.id),
            events_batch.events
        )
        
        return [AnalyticsEventResponse.from_orm(event) for event in created_events]
        
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid batch event data: constraint violation"
        )
    except OperationalError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error"
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create analytics events batch: {str(e)}"
        )


@router.get(
    "/progress",
    response_model=UserProgressResponse,
    summary="Get User Progress Summary",
    description="Get comprehensive progress summary including XP, streaks, completion rates, and learning statistics"
)
async def get_user_progress(
    course_id: Optional[str] = Query(None, description="Course ID to filter progress"),
    include_global_stats: bool = Query(False, description="Include global statistics across all courses"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UserProgressResponse:
    """
    Get user progress summary.
    
    Returns comprehensive progress data including XP, streaks, completion rates,
    accuracy metrics, and learning statistics for dashboard display.
    
    Args:
        course_id: Optional course ID to filter progress
        include_global_stats: Whether to include global statistics
        db: Database session
        current_user: Authenticated user
        
    Returns:
        User progress summary with all relevant metrics
        
    Raises:
        HTTPException: If progress retrieval fails
    """
    try:
        analytics_service = AnalyticsService(db)
        progress = analytics_service.get_user_progress(
            str(current_user.id),
            course_id,
            include_global_stats
        )
        
        return progress
        
    except OperationalError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error"
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user progress: {str(e)}"
        )


@router.post(
    "/course-completion",
    response_model=CourseCompletionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track Course Completion",
    description="Record course completion with all required metadata and analytics tracking"
)
async def track_course_completion(
    completion: CourseCompletionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CourseCompletionResponse:
    """
    Track course completion.
    
    Records course completion with comprehensive metrics including final score,
    time spent, XP earned, and achievement unlocks.
    
    Args:
        completion: Course completion data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Course completion tracking results with achievements
        
    Raises:
        HTTPException: If course completion tracking fails
    """
    try:
        analytics_service = AnalyticsService(db)
        completion_result = analytics_service.track_course_completion(
            str(current_user.id),
            completion
        )
        
        return CourseCompletionResponse(**completion_result)
        
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course completion data: constraint violation"
        )
    except OperationalError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error"
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track course completion: {str(e)}"
        )


@router.post(
    "/lesson-completion",
    response_model=LessonCompletionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track Lesson Completion",
    description="Record lesson completion with detailed metrics including score, time, accuracy, and XP earned"
)
async def track_lesson_completion(
    completion: LessonCompletionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> LessonCompletionResponse:
    """
    Track lesson completion.
    
    Records lesson completion with detailed metrics including score, time spent,
    accuracy rate, XP earned, and learning analytics.
    
    Args:
        completion: Lesson completion data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Lesson completion tracking results with detailed metrics
        
    Raises:
        HTTPException: If lesson completion tracking fails
    """
    try:
        analytics_service = AnalyticsService(db)
        completion_result = analytics_service.track_lesson_completion(
            str(current_user.id),
            completion
        )
        
        return LessonCompletionResponse(**completion_result)
        
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid lesson completion data: constraint violation"
        )
    except OperationalError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error"
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track lesson completion: {str(e)}"
        )


@router.get(
    "/user-stats",
    response_model=UserStatsResponse,
    summary="Get User Dashboard Statistics",
    description="Get comprehensive user statistics for dashboard display including progress, performance, and engagement metrics"
)
async def get_user_stats(
    course_id: Optional[str] = Query(None, description="Course ID to filter statistics"),
    include_global_stats: bool = Query(True, description="Include global statistics across all courses"),
    include_historical: bool = Query(False, description="Include historical progress snapshots"),
    date_range_start: Optional[datetime] = Query(None, description="Start date for historical data"),
    date_range_end: Optional[datetime] = Query(None, description="End date for historical data"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UserStatsResponse:
    """
    Get comprehensive user statistics.
    
    Returns detailed user statistics for dashboard display including learning
    progress, performance metrics, engagement data, and historical trends.
    
    Args:
        course_id: Optional course ID to filter statistics
        include_global_stats: Whether to include global statistics
        include_historical: Whether to include historical data
        date_range_start: Start date for historical data
        date_range_end: End date for historical data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Comprehensive user statistics with optional historical data
        
    Raises:
        HTTPException: If statistics retrieval fails
    """
    try:
        analytics_service = AnalyticsService(db)
        user_stats = analytics_service.get_user_stats(
            str(current_user.id),
            course_id,
            include_global_stats,
            include_historical
        )
        
        return user_stats
        
    except OperationalError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error"
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user statistics: {str(e)}"
        )


@router.get(
    "/events",
    response_model=List[AnalyticsEventResponse],
    summary="Get User Analytics Events",
    description="Retrieve user's analytics events with optional filtering and pagination"
)
async def get_analytics_events(
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    lesson_id: Optional[str] = Query(None, description="Filter by lesson ID"),
    exercise_id: Optional[str] = Query(None, description="Filter by exercise ID"),
    event_type: Optional[EventTypeEnum] = Query(None, description="Filter by event type"),
    event_category: Optional[EventCategoryEnum] = Query(None, description="Filter by event category"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    device_type: Optional[DeviceTypeEnum] = Query(None, description="Filter by device type"),
    platform: Optional[PlatformEnum] = Query(None, description="Filter by platform"),
    date_start: Optional[datetime] = Query(None, description="Start date for events"),
    date_end: Optional[datetime] = Query(None, description="End date for events"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[AnalyticsEventResponse]:
    """
    Get user analytics events with filtering.
    
    Retrieves the user's analytics events with comprehensive filtering options
    for analysis and debugging purposes.
    
    Args:
        course_id: Filter by course ID
        lesson_id: Filter by lesson ID
        exercise_id: Filter by exercise ID
        event_type: Filter by event type
        event_category: Filter by event category
        session_id: Filter by session ID
        device_type: Filter by device type
        platform: Filter by platform
        date_start: Start date for events
        date_end: End date for events
        limit: Maximum number of events to return
        offset: Number of events to skip
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List of filtered analytics events
        
    Raises:
        HTTPException: If event retrieval fails
    """
    try:
        # Create query parameters object
        query_params = AnalyticsQueryParams(
            course_id=course_id,
            lesson_id=lesson_id,
            exercise_id=exercise_id,
            event_type=event_type,
            event_category=event_category,
            session_id=session_id,
            device_type=device_type,
            platform=platform,
            date_start=date_start,
            date_end=date_end,
            limit=limit,
            offset=offset
        )
        
        analytics_service = AnalyticsService(db)
        events = analytics_service.get_analytics_events(
            str(current_user.id),
            query_params
        )
        
        return [AnalyticsEventResponse.from_orm(event) for event in events]
        
    except OperationalError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error"
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics events: {str(e)}"
        )


@router.get(
    "/metrics",
    response_model=AnalyticsMetricsResponse,
    summary="Get Analytics Metrics",
    description="Get aggregated analytics metrics for reporting and insights (admin only)"
)
async def get_analytics_metrics(
    date_start: Optional[datetime] = Query(None, description="Start date for metrics"),
    date_end: Optional[datetime] = Query(None, description="End date for metrics"),
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    db: Session = Depends(get_db),
    admin_user_payload: dict = Depends(require_admin_role)
) -> AnalyticsMetricsResponse:
    """
    Get aggregated analytics metrics.
    
    Returns aggregated analytics metrics for reporting and insights.
    This endpoint is typically used by administrators for platform analytics.
    
    Args:
        date_start: Start date for metrics
        date_end: End date for metrics
        course_id: Filter by course ID
        db: Database session
        admin_user_payload: Admin user payload (validated)
        
    Returns:
        Aggregated analytics metrics
        
    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        analytics_service = AnalyticsService(db)
        metrics_data = analytics_service.get_aggregated_metrics(
            date_start=date_start,
            date_end=date_end,
            course_id=course_id
        )
        
        return AnalyticsMetricsResponse(**metrics_data)
        
    except OperationalError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error"
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics metrics: {str(e)}"
        )


# Health check endpoint for analytics service
@router.get(
    "/health",
    summary="Analytics Service Health Check",
    description="Check the health status of the analytics service"
)
async def analytics_health_check(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Analytics service health check.
    
    Verifies that the analytics service is operational and can access
    the database and perform basic operations.
    
    Args:
        db: Database session
        
    Returns:
        Health check status and metrics
        
    Raises:
        HTTPException: If health check fails
    """
    try:
        # Test database connectivity
        from app.models.analytics import AnalyticsEvent
        event_count = db.query(AnalyticsEvent).count()
        
        return {
            "status": "healthy",
            "service": "analytics",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "total_events": event_count,
            "version": "1.0.0"
        }
        
    except OperationalError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error occurred"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Analytics service unhealthy: {str(e)}"
        )