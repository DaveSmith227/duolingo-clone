"""
Models Module

This module contains all SQLAlchemy database models for the Duolingo clone
backend application.
"""

from .base import BaseModel, SoftDeleteModel, AuditModel, VersionedModel, ActiveRecordModel
from .user import User, OAuthProvider
from .course import Language, Course, Section, Unit, Lesson, LessonPrerequisite
from .exercise import ExerciseType, Exercise, ExerciseOption, LessonExercise, AudioFile
from .progress import UserCourse, UserLessonProgress, UserExerciseInteraction
from .gamification import UserDailyXP, UserHeartsLog, Achievement, UserAchievement
from .audit import UserActivityLog, SystemAuditLog
from .analytics import AnalyticsEvent, UserProgressSnapshot, UserLearningStats, EventType

__all__ = [
    'BaseModel',
    'SoftDeleteModel', 
    'AuditModel',
    'VersionedModel',
    'ActiveRecordModel',
    'User',
    'OAuthProvider',
    'Language',
    'Course',
    'Section',
    'Unit',
    'Lesson',
    'LessonPrerequisite',
    'ExerciseType',
    'Exercise',
    'ExerciseOption',
    'LessonExercise',
    'AudioFile',
    'UserCourse',
    'UserLessonProgress',
    'UserExerciseInteraction',
    'UserDailyXP',
    'UserHeartsLog',
    'Achievement',
    'UserAchievement',
    'UserActivityLog',
    'SystemAuditLog',
    'AnalyticsEvent',
    'UserProgressSnapshot',
    'UserLearningStats',
    'EventType',
]