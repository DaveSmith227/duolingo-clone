"""
Models Module

This module contains all SQLAlchemy database models for the Duolingo clone
backend application.
"""

from .base import BaseModel, SoftDeleteModel, AuditModel, VersionedModel, ActiveRecordModel
from .user import User, OAuthProvider

__all__ = [
    'BaseModel',
    'SoftDeleteModel', 
    'AuditModel',
    'VersionedModel',
    'ActiveRecordModel',
    'User',
    'OAuthProvider',
]