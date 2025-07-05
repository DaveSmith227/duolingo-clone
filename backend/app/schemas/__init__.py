"""
Schemas Module

This module contains all Pydantic schemas for request/response validation
in the Duolingo clone backend application.
"""

from .analytics import (
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
    SnapshotTypeEnum,
)

__all__ = [
    'AnalyticsEventRequest',
    'AnalyticsEventBatchRequest',
    'AnalyticsEventResponse',
    'UserProgressRequest',
    'UserProgressResponse',
    'CourseCompletionRequest',
    'CourseCompletionResponse',
    'LessonCompletionRequest',
    'LessonCompletionResponse',
    'UserStatsRequest',
    'UserStatsResponse',
    'AnalyticsMetricsResponse',
    'AnalyticsErrorResponse',
    'AnalyticsQueryParams',
    'EventTypeEnum',
    'EventCategoryEnum',
    'DeviceTypeEnum',
    'PlatformEnum',
    'SnapshotTypeEnum',
]