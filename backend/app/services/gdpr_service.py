"""
GDPR Compliance Service

Service for handling GDPR compliance requirements including account deletion,
data export, consent management, and data retention policies.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import json

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User, OAuthProvider
from app.models.auth import SupabaseUser, AuthSession, AuthAuditLog, PasswordHistory, PasswordResetToken
from app.models.progress import UserCourse, UserLessonProgress, UserExerciseInteraction
from app.models.gamification import UserDailyXP, UserHeartsLog, UserAchievement
from app.models.rbac import UserRoleAssignment
from app.services.audit_logger import get_audit_logger, AuditEventType, AuditSeverity
from app.core.supabase import get_supabase_client

logger = logging.getLogger(__name__)


class GDPRService:
    """Service for GDPR compliance operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.audit_logger = get_audit_logger()
        self.supabase_client = get_supabase_client()
    
    async def delete_user_account(
        self,
        user_id: str,
        ip_address: str = None,
        user_agent: str = None,
        reason: str = "user_request"
    ) -> Dict[str, Any]:
        """
        Delete user account and all associated data with complete cascade removal.
        
        Args:
            user_id: ID of user to delete
            ip_address: IP address of requester
            user_agent: User agent of requester
            reason: Reason for deletion
            
        Returns:
            Dictionary with deletion results and statistics
            
        Raises:
            ValueError: If user not found
            Exception: If deletion fails
        """
        try:
            # Find user and supabase user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User not found: {user_id}")
            
            supabase_user = self.db.query(SupabaseUser).filter(
                SupabaseUser.app_user_id == user_id
            ).first()
            
            # Collect deletion statistics
            deletion_stats = {
                "user_id": user_id,
                "email": user.email,
                "deletion_started_at": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "tables_processed": [],
                "records_deleted": {}
            }
            
            # Start transaction for atomic deletion
            with self.db.begin():
                # 1. Delete OAuth providers
                oauth_count = self.db.query(OAuthProvider).filter(
                    OAuthProvider.user_id == user_id
                ).count()
                if oauth_count > 0:
                    self.db.query(OAuthProvider).filter(
                        OAuthProvider.user_id == user_id
                    ).delete()
                    deletion_stats["records_deleted"]["oauth_providers"] = oauth_count
                    deletion_stats["tables_processed"].append("oauth_providers")
                
                # 2. Delete authentication data if supabase_user exists
                if supabase_user:
                    supabase_user_id = supabase_user.id
                    
                    # Delete auth sessions
                    auth_sessions_count = self.db.query(AuthSession).filter(
                        AuthSession.supabase_user_id == supabase_user_id
                    ).count()
                    if auth_sessions_count > 0:
                        self.db.query(AuthSession).filter(
                            AuthSession.supabase_user_id == supabase_user_id
                        ).delete()
                        deletion_stats["records_deleted"]["auth_sessions"] = auth_sessions_count
                        deletion_stats["tables_processed"].append("auth_sessions")
                    
                    # Delete password history
                    password_history_count = self.db.query(PasswordHistory).filter(
                        PasswordHistory.supabase_user_id == supabase_user_id
                    ).count()
                    if password_history_count > 0:
                        self.db.query(PasswordHistory).filter(
                            PasswordHistory.supabase_user_id == supabase_user_id
                        ).delete()
                        deletion_stats["records_deleted"]["password_history"] = password_history_count
                        deletion_stats["tables_processed"].append("password_history")
                    
                    # Delete password reset tokens
                    reset_tokens_count = self.db.query(PasswordResetToken).filter(
                        PasswordResetToken.supabase_user_id == supabase_user.supabase_id
                    ).count()
                    if reset_tokens_count > 0:
                        self.db.query(PasswordResetToken).filter(
                            PasswordResetToken.supabase_user_id == supabase_user.supabase_id
                        ).delete()
                        deletion_stats["records_deleted"]["password_reset_tokens"] = reset_tokens_count
                        deletion_stats["tables_processed"].append("password_reset_tokens")
                    
                    # Anonymize auth audit logs (keep for security but remove PII)
                    auth_logs_count = self.db.query(AuthAuditLog).filter(
                        AuthAuditLog.supabase_user_id == supabase_user_id
                    ).count()
                    if auth_logs_count > 0:
                        # Anonymize rather than delete for security compliance
                        self.db.query(AuthAuditLog).filter(
                            AuthAuditLog.supabase_user_id == supabase_user_id
                        ).update({
                            "supabase_user_id": None,
                            "user_agent": "ANONYMIZED",
                            "event_metadata": json.dumps({"anonymized": True})
                        })
                        deletion_stats["records_deleted"]["auth_audit_logs_anonymized"] = auth_logs_count
                        deletion_stats["tables_processed"].append("auth_audit_logs")
                
                # 3. Delete learning progress data
                # User course enrollments
                user_courses_count = self.db.query(UserCourse).filter(
                    UserCourse.user_id == user_id
                ).count()
                if user_courses_count > 0:
                    self.db.query(UserCourse).filter(
                        UserCourse.user_id == user_id
                    ).delete()
                    deletion_stats["records_deleted"]["user_courses"] = user_courses_count
                    deletion_stats["tables_processed"].append("user_courses")
                
                # User lesson progress
                lesson_progress_count = self.db.query(UserLessonProgress).filter(
                    UserLessonProgress.user_id == user_id
                ).count()
                if lesson_progress_count > 0:
                    self.db.query(UserLessonProgress).filter(
                        UserLessonProgress.user_id == user_id
                    ).delete()
                    deletion_stats["records_deleted"]["user_lesson_progress"] = lesson_progress_count
                    deletion_stats["tables_processed"].append("user_lesson_progress")
                
                # User exercise interactions
                exercise_interactions_count = self.db.query(UserExerciseInteraction).filter(
                    UserExerciseInteraction.user_id == user_id
                ).count()
                if exercise_interactions_count > 0:
                    self.db.query(UserExerciseInteraction).filter(
                        UserExerciseInteraction.user_id == user_id
                    ).delete()
                    deletion_stats["records_deleted"]["user_exercise_interactions"] = exercise_interactions_count
                    deletion_stats["tables_processed"].append("user_exercise_interactions")
                
                # 4. Delete gamification data
                # Daily XP records
                daily_xp_count = self.db.query(UserDailyXP).filter(
                    UserDailyXP.user_id == user_id
                ).count()
                if daily_xp_count > 0:
                    self.db.query(UserDailyXP).filter(
                        UserDailyXP.user_id == user_id
                    ).delete()
                    deletion_stats["records_deleted"]["user_daily_xp"] = daily_xp_count
                    deletion_stats["tables_processed"].append("user_daily_xp")
                
                # Hearts logs
                hearts_log_count = self.db.query(UserHeartsLog).filter(
                    UserHeartsLog.user_id == user_id
                ).count()
                if hearts_log_count > 0:
                    self.db.query(UserHeartsLog).filter(
                        UserHeartsLog.user_id == user_id
                    ).delete()
                    deletion_stats["records_deleted"]["user_hearts_log"] = hearts_log_count
                    deletion_stats["tables_processed"].append("user_hearts_log")
                
                # User achievements
                achievements_count = self.db.query(UserAchievement).filter(
                    UserAchievement.user_id == user_id
                ).count()
                if achievements_count > 0:
                    self.db.query(UserAchievement).filter(
                        UserAchievement.user_id == user_id
                    ).delete()
                    deletion_stats["records_deleted"]["user_achievements"] = achievements_count
                    deletion_stats["tables_processed"].append("user_achievements")
                
                # 5. Delete RBAC data
                role_assignments_count = self.db.query(UserRoleAssignment).filter(
                    UserRoleAssignment.user_id == user_id
                ).count()
                if role_assignments_count > 0:
                    self.db.query(UserRoleAssignment).filter(
                        UserRoleAssignment.user_id == user_id
                    ).delete()
                    deletion_stats["records_deleted"]["user_role_assignments"] = role_assignments_count
                    deletion_stats["tables_processed"].append("user_role_assignments")
                
                # 6. Delete Supabase user record
                if supabase_user:
                    self.db.delete(supabase_user)
                    deletion_stats["records_deleted"]["supabase_user"] = 1
                    deletion_stats["tables_processed"].append("supabase_users")
                
                # 7. Finally delete the main user record (soft delete)
                if hasattr(user, 'soft_delete'):
                    user.soft_delete()
                else:
                    self.db.delete(user)
                deletion_stats["records_deleted"]["main_user"] = 1
                deletion_stats["tables_processed"].append("users")
                
                # Commit all deletions
                self.db.commit()
            
            # 8. Delete from Supabase Auth (external system)
            supabase_deletion_result = None
            if supabase_user and supabase_user.supabase_id:
                try:
                    supabase_deletion_result = await self._delete_from_supabase_auth(
                        supabase_user.supabase_id
                    )
                    deletion_stats["supabase_auth_deleted"] = True
                except Exception as e:
                    logger.warning(f"Failed to delete from Supabase Auth: {e}")
                    deletion_stats["supabase_auth_deleted"] = False
                    deletion_stats["supabase_auth_error"] = str(e)
            
            deletion_stats["deletion_completed_at"] = datetime.now(timezone.utc).isoformat()
            deletion_stats["total_records_deleted"] = sum(deletion_stats["records_deleted"].values())
            
            # Log account deletion event
            await self.audit_logger.log_authentication_event(
                event_type=AuditEventType.ACCOUNT_DELETED,
                success=True,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "deletion_stats": deletion_stats,
                    "reason": reason
                },
                severity=AuditSeverity.HIGH
            )
            
            logger.info(f"Successfully deleted user account {user_id}: {deletion_stats['total_records_deleted']} records")
            return deletion_stats
            
        except Exception as e:
            # Log deletion failure
            await self.audit_logger.log_authentication_event(
                event_type=AuditEventType.ACCOUNT_DELETED,
                success=False,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(e),
                metadata={"reason": reason},
                severity=AuditSeverity.HIGH
            )
            
            logger.error(f"Failed to delete user account {user_id}: {e}")
            self.db.rollback()
            raise
    
    async def _delete_from_supabase_auth(self, supabase_user_id: str) -> Dict[str, Any]:
        """
        Delete user from Supabase Auth.
        
        Args:
            supabase_user_id: Supabase user ID to delete
            
        Returns:
            Deletion result from Supabase
        """
        try:
            # Use Supabase admin API to delete user
            result = self.supabase_client.auth.admin.delete_user(supabase_user_id)
            logger.info(f"Deleted user from Supabase Auth: {supabase_user_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete user from Supabase Auth {supabase_user_id}: {e}")
            raise
    
    async def export_user_data(
        self,
        user_id: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        Export all user data in JSON format for GDPR compliance.
        
        Args:
            user_id: ID of user to export data for
            ip_address: IP address of requester
            user_agent: User agent of requester
            
        Returns:
            Complete user data export
            
        Raises:
            ValueError: If user not found
        """
        try:
            # Find user and supabase user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User not found: {user_id}")
            
            supabase_user = self.db.query(SupabaseUser).filter(
                SupabaseUser.app_user_id == user_id
            ).first()
            
            export_data = {
                "export_info": {
                    "user_id": user_id,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "export_format": "JSON",
                    "gdpr_compliance": True
                },
                "personal_data": {
                    "profile": {
                        "id": user.id,
                        "email": user.email,
                        "name": user.name,
                        "avatar_url": user.avatar_url,
                        "is_email_verified": user.is_email_verified,
                        "daily_xp_goal": user.daily_xp_goal,
                        "timezone": user.timezone,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                        "updated_at": user.updated_at.isoformat() if user.updated_at else None
                    }
                }
            }
            
            # Add Supabase user data if exists
            if supabase_user:
                export_data["personal_data"]["authentication"] = {
                    "supabase_id": supabase_user.supabase_id,
                    "email": supabase_user.email,
                    "email_verified": supabase_user.email_verified,
                    "phone": supabase_user.phone,
                    "phone_verified": supabase_user.phone_verified,
                    "provider": supabase_user.provider,
                    "last_sign_in_at": supabase_user.last_sign_in_at.isoformat() if supabase_user.last_sign_in_at else None,
                    "user_metadata": supabase_user.user_metadata,
                    "app_metadata": supabase_user.app_metadata
                }
            
            # Add OAuth providers
            oauth_providers = self.db.query(OAuthProvider).filter(
                OAuthProvider.user_id == user_id
            ).all()
            if oauth_providers:
                export_data["personal_data"]["oauth_providers"] = [
                    {
                        "provider": provider.provider,
                        "provider_user_id": provider.provider_user_id,
                        "created_at": provider.created_at.isoformat() if provider.created_at else None
                    }
                    for provider in oauth_providers
                ]
            
            # Add learning progress data
            user_courses = self.db.query(UserCourse).filter(
                UserCourse.user_id == user_id
            ).all()
            if user_courses:
                export_data["learning_data"] = {
                    "course_enrollments": [
                        {
                            "course_id": course.course_id,
                            "total_xp": course.total_xp,
                            "current_streak": course.current_streak,
                            "longest_streak": course.longest_streak,
                            "current_hearts": course.current_hearts,
                            "max_hearts": course.max_hearts,
                            "completion_percentage": course.completion_percentage,
                            "enrolled_at": course.enrolled_at.isoformat() if course.enrolled_at else None,
                            "last_activity_date": course.last_activity_date.isoformat() if course.last_activity_date else None
                        }
                        for course in user_courses
                    ]
                }
            
            # Add lesson progress
            lesson_progress = self.db.query(UserLessonProgress).filter(
                UserLessonProgress.user_id == user_id
            ).all()
            if lesson_progress:
                if "learning_data" not in export_data:
                    export_data["learning_data"] = {}
                export_data["learning_data"]["lesson_progress"] = [
                    {
                        "lesson_id": progress.lesson_id,
                        "status": progress.status,
                        "attempts": progress.attempts,
                        "best_score": progress.best_score,
                        "last_score": progress.last_score,
                        "xp_earned": progress.xp_earned,
                        "time_spent": progress.time_spent,
                        "first_completed_at": progress.first_completed_at.isoformat() if progress.first_completed_at else None,
                        "last_attempted_at": progress.last_attempted_at.isoformat() if progress.last_attempted_at else None
                    }
                    for progress in lesson_progress
                ]
            
            # Add exercise interactions (last 1000 for data size management)
            exercise_interactions = self.db.query(UserExerciseInteraction).filter(
                UserExerciseInteraction.user_id == user_id
            ).order_by(UserExerciseInteraction.created_at.desc()).limit(1000).all()
            if exercise_interactions:
                if "learning_data" not in export_data:
                    export_data["learning_data"] = {}
                export_data["learning_data"]["exercise_interactions"] = [
                    {
                        "exercise_id": interaction.exercise_id,
                        "lesson_id": interaction.lesson_id,
                        "interaction_type": interaction.interaction_type,
                        "is_correct": interaction.is_correct,
                        "time_taken": interaction.time_taken,
                        "xp_earned": interaction.xp_earned,
                        "hints_used": interaction.hints_used,
                        "attempt_number": interaction.attempt_number,
                        "created_at": interaction.created_at.isoformat() if interaction.created_at else None
                    }
                    for interaction in exercise_interactions
                ]
            
            # Add gamification data
            daily_xp = self.db.query(UserDailyXP).filter(
                UserDailyXP.user_id == user_id
            ).order_by(UserDailyXP.date.desc()).limit(365).all()  # Last year
            if daily_xp:
                export_data["gamification_data"] = {
                    "daily_xp_records": [
                        {
                            "date": record.date.isoformat(),
                            "course_id": record.course_id,
                            "xp_earned": record.xp_earned,
                            "daily_goal": record.daily_goal,
                            "goal_met": record.goal_met,
                            "lessons_completed": record.lessons_completed,
                            "exercises_completed": record.exercises_completed,
                            "time_spent": record.time_spent,
                            "streak_count": record.streak_count
                        }
                        for record in daily_xp
                    ]
                }
            
            # Add achievements
            achievements = self.db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id
            ).all()
            if achievements:
                if "gamification_data" not in export_data:
                    export_data["gamification_data"] = {}
                export_data["gamification_data"]["achievements"] = [
                    {
                        "achievement_id": achievement.achievement_id,
                        "earned_at": achievement.earned_at.isoformat() if achievement.earned_at else None,
                        "progress": achievement.progress,
                        "is_completed": achievement.is_completed,
                        "current_value": achievement.current_value,
                        "target_value": achievement.target_value,
                        "xp_awarded": achievement.xp_awarded,
                        "hearts_awarded": achievement.hearts_awarded,
                        "course_id": achievement.course_id
                    }
                    for achievement in achievements
                ]
            
            # Add role assignments
            role_assignments = self.db.query(UserRoleAssignment).filter(
                UserRoleAssignment.user_id == user_id
            ).all()
            if role_assignments:
                export_data["access_data"] = {
                    "role_assignments": [
                        {
                            "role_id": assignment.role_id,
                            "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
                            "assigned_by": assignment.assigned_by,
                            "expires_at": assignment.expires_at.isoformat() if assignment.expires_at else None,
                            "is_active": assignment.is_active
                        }
                        for assignment in role_assignments
                    ]
                }
            
            # Log data export event
            await self.audit_logger.log_authentication_event(
                event_type="data_export",
                success=True,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "export_sections": list(export_data.keys()),
                    "data_size_kb": len(json.dumps(export_data)) / 1024
                },
                severity=AuditSeverity.MEDIUM
            )
            
            logger.info(f"Successfully exported data for user {user_id}")
            return export_data
            
        except Exception as e:
            # Log export failure
            await self.audit_logger.log_authentication_event(
                event_type="data_export",
                success=False,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(e),
                severity=AuditSeverity.MEDIUM
            )
            
            logger.error(f"Failed to export data for user {user_id}: {e}")
            raise
    
    def find_inactive_users(self, inactive_days: int = 730) -> List[Dict[str, Any]]:
        """
        Find users inactive for specified number of days for data retention cleanup.
        
        Args:
            inactive_days: Number of days of inactivity (default 730 = 2 years)
            
        Returns:
            List of inactive user information
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=inactive_days)
        
        # Find users who haven't had any activity since cutoff date
        inactive_users = self.db.query(User).filter(
            User.updated_at < cutoff_date
        ).all()
        
        # Filter further by checking if they have any recent learning activity
        truly_inactive = []
        for user in inactive_users:
            # Check for recent course activity
            recent_course_activity = self.db.query(UserCourse).filter(
                UserCourse.user_id == user.id,
                UserCourse.last_activity_date > cutoff_date
            ).first()
            
            if not recent_course_activity:
                # Check for recent daily XP
                recent_xp = self.db.query(UserDailyXP).filter(
                    UserDailyXP.user_id == user.id,
                    UserDailyXP.date > cutoff_date.date()
                ).first()
                
                if not recent_xp:
                    truly_inactive.append({
                        "user_id": user.id,
                        "email": user.email,
                        "last_activity": user.updated_at.isoformat() if user.updated_at else None,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                        "inactive_days": (datetime.now(timezone.utc) - user.updated_at).days if user.updated_at else None
                    })
        
        logger.info(f"Found {len(truly_inactive)} inactive users (inactive for {inactive_days}+ days)")
        return truly_inactive


def get_gdpr_service(db: Session) -> GDPRService:
    """Get GDPR service instance."""
    return GDPRService(db)