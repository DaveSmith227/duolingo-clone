"""
Data Retention Policy Service

Service for managing data retention policies, automatic cleanup of inactive
accounts, and user notification for GDPR compliance.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import json

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_, or_

from app.models.user import User
from app.models.auth import SupabaseUser, AuthSession
from app.models.progress import UserCourse
from app.models.gamification import UserDailyXP
from app.models.privacy import UserConsent, ConsentAuditLog
from app.services.gdpr_service import GDPRService
from app.services.audit_logger import get_audit_logger, AuditEventType, AuditSeverity

logger = logging.getLogger(__name__)


class DataRetentionService:
    """Service for data retention policy management."""
    
    def __init__(self, db: Session):
        self.db = db
        self.audit_logger = get_audit_logger()
        self.gdpr_service = GDPRService(db)
        
        # Default retention periods (in days)
        self.default_retention_periods = {
            "inactive_account_deletion": 730,  # 2 years
            "inactive_account_warning": 660,   # 22 months (2 month warning)
            "session_cleanup": 30,             # 30 days for expired sessions
            "audit_log_retention": 2555,       # 7 years for audit logs
            "consent_log_retention": 2555,     # 7 years for consent logs
            "password_reset_cleanup": 1,       # 1 day for expired reset tokens
            "verification_token_cleanup": 7    # 7 days for expired verification tokens
        }
    
    def find_inactive_accounts(
        self,
        inactive_days: int = None,
        include_recent_auth: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find accounts that have been inactive for specified period.
        
        Args:
            inactive_days: Number of days to consider inactive (default from config)
            include_recent_auth: Whether to check recent authentication activity
            
        Returns:
            List of inactive account information
        """
        if inactive_days is None:
            inactive_days = self.default_retention_periods["inactive_account_deletion"]
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=inactive_days)
        
        try:
            # Find users who haven't updated their profile since cutoff
            inactive_users_query = self.db.query(User).filter(
                User.updated_at < cutoff_date,
                User.deleted_at.is_(None)  # Exclude soft-deleted users
            )
            
            inactive_users = inactive_users_query.all()
            
            truly_inactive = []
            
            for user in inactive_users:
                # Check for recent course activity
                recent_course_activity = self.db.query(UserCourse).filter(
                    UserCourse.user_id == user.id,
                    UserCourse.last_activity_date > cutoff_date
                ).first()
                
                if recent_course_activity:
                    continue  # User has recent course activity
                
                # Check for recent daily XP
                recent_xp = self.db.query(UserDailyXP).filter(
                    UserDailyXP.user_id == user.id,
                    UserDailyXP.date > cutoff_date.date()
                ).first()
                
                if recent_xp:
                    continue  # User has recent XP activity
                
                # Check for recent authentication if requested
                if include_recent_auth:
                    supabase_user = self.db.query(SupabaseUser).filter(
                        SupabaseUser.app_user_id == user.id
                    ).first()
                    
                    if supabase_user:
                        recent_auth = self.db.query(AuthSession).filter(
                            AuthSession.supabase_user_id == supabase_user.id,
                            AuthSession.created_at > cutoff_date
                        ).first()
                        
                        if recent_auth:
                            continue  # User has recent authentication
                
                # Calculate actual inactive days
                last_activity = user.updated_at
                if user.updated_at:
                    inactive_duration = (datetime.now(timezone.utc) - user.updated_at).days
                else:
                    inactive_duration = None
                
                truly_inactive.append({
                    "user_id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_activity": user.updated_at.isoformat() if user.updated_at else None,
                    "inactive_days": inactive_duration,
                    "account_age_days": (datetime.now(timezone.utc) - user.created_at).days if user.created_at else None
                })
            
            logger.info(f"Found {len(truly_inactive)} inactive accounts (inactive for {inactive_days}+ days)")
            return truly_inactive
            
        except Exception as e:
            logger.error(f"Failed to find inactive accounts: {e}")
            raise
    
    def find_accounts_for_warning(
        self,
        warning_days: int = None
    ) -> List[Dict[str, Any]]:
        """
        Find accounts that should receive inactivity warnings.
        
        Args:
            warning_days: Days of inactivity before warning (default from config)
            
        Returns:
            List of accounts requiring warnings
        """
        if warning_days is None:
            warning_days = self.default_retention_periods["inactive_account_warning"]
        
        # Find accounts that need warnings (approaching deletion)
        warning_accounts = self.find_inactive_accounts(
            inactive_days=warning_days,
            include_recent_auth=True
        )
        
        # Filter out accounts that have already been warned recently
        # (This would require a separate warning tracking table in production)
        
        logger.info(f"Found {len(warning_accounts)} accounts requiring inactivity warnings")
        return warning_accounts
    
    async def send_inactivity_warnings(
        self,
        accounts: List[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Send inactivity warnings to users.
        
        Args:
            accounts: Specific accounts to warn (if None, finds automatically)
            dry_run: If True, don't actually send emails
            
        Returns:
            Warning results summary
        """
        if accounts is None:
            accounts = self.find_accounts_for_warning()
        
        warning_results = {
            "total_accounts": len(accounts),
            "warnings_sent": 0,
            "warnings_failed": 0,
            "dry_run": dry_run,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "results": []
        }
        
        try:
            for account in accounts:
                user_id = account["user_id"]
                email = account["email"]
                
                try:
                    if not dry_run:
                        # In a real implementation, this would send an email
                        # For now, we'll just log the warning
                        await self._send_warning_email(
                            user_id=user_id,
                            email=email,
                            inactive_days=account["inactive_days"]
                        )
                    
                    # Log warning event
                    await self.audit_logger.log_authentication_event(
                        event_type="inactivity_warning_sent",
                        success=True,
                        user_id=user_id,
                        metadata={
                            "email": email,
                            "inactive_days": account["inactive_days"],
                            "dry_run": dry_run
                        },
                        severity=AuditSeverity.LOW
                    )
                    
                    warning_results["warnings_sent"] += 1
                    warning_results["results"].append({
                        "user_id": user_id,
                        "email": email,
                        "status": "sent" if not dry_run else "would_send",
                        "inactive_days": account["inactive_days"]
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to send warning to user {user_id}: {e}")
                    warning_results["warnings_failed"] += 1
                    warning_results["results"].append({
                        "user_id": user_id,
                        "email": email,
                        "status": "failed",
                        "error": str(e)
                    })
            
            logger.info(f"Inactivity warning process completed: {warning_results['warnings_sent']} sent, {warning_results['warnings_failed']} failed")
            return warning_results
            
        except Exception as e:
            logger.error(f"Failed to send inactivity warnings: {e}")
            raise
    
    async def _send_warning_email(
        self,
        user_id: str,
        email: str,
        inactive_days: int
    ) -> None:
        """
        Send inactivity warning email to user.
        
        In a real implementation, this would integrate with an email service.
        """
        logger.info(f"Sending inactivity warning to {email} (user: {user_id}, inactive: {inactive_days} days)")
        
        # In production, this would:
        # 1. Generate warning email content
        # 2. Send via email service (SendGrid, SES, etc.)
        # 3. Track email delivery status
        # 4. Store warning record in database
        
        # For now, just simulate the email sending
        pass
    
    async def cleanup_inactive_accounts(
        self,
        inactive_days: int = None,
        dry_run: bool = False,
        max_deletions: int = 100
    ) -> Dict[str, Any]:
        """
        Automatically delete inactive accounts.
        
        Args:
            inactive_days: Days of inactivity before deletion
            dry_run: If True, don't actually delete accounts
            max_deletions: Maximum number of accounts to delete in one run
            
        Returns:
            Cleanup results summary
        """
        if inactive_days is None:
            inactive_days = self.default_retention_periods["inactive_account_deletion"]
        
        # Find inactive accounts
        inactive_accounts = self.find_inactive_accounts(inactive_days)
        
        # Limit number of deletions for safety
        accounts_to_delete = inactive_accounts[:max_deletions]
        
        cleanup_results = {
            "total_inactive_found": len(inactive_accounts),
            "accounts_to_delete": len(accounts_to_delete),
            "accounts_deleted": 0,
            "deletions_failed": 0,
            "dry_run": dry_run,
            "inactive_threshold_days": inactive_days,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "results": []
        }
        
        try:
            for account in accounts_to_delete:
                user_id = account["user_id"]
                email = account["email"]
                
                try:
                    if not dry_run:
                        # Perform actual account deletion
                        deletion_result = await self.gdpr_service.delete_user_account(
                            user_id=user_id,
                            reason="automatic_cleanup_inactive_account"
                        )
                        
                        cleanup_results["accounts_deleted"] += 1
                        cleanup_results["results"].append({
                            "user_id": user_id,
                            "email": email,
                            "status": "deleted",
                            "inactive_days": account["inactive_days"],
                            "records_deleted": deletion_result["total_records_deleted"]
                        })
                    else:
                        cleanup_results["results"].append({
                            "user_id": user_id,
                            "email": email,
                            "status": "would_delete",
                            "inactive_days": account["inactive_days"]
                        })
                    
                    # Log cleanup event
                    await self.audit_logger.log_authentication_event(
                        event_type="account_cleanup",
                        success=True,
                        user_id=user_id,
                        metadata={
                            "email": email,
                            "inactive_days": account["inactive_days"],
                            "dry_run": dry_run,
                            "cleanup_reason": "automatic_data_retention"
                        },
                        severity=AuditSeverity.HIGH
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to delete inactive account {user_id}: {e}")
                    cleanup_results["deletions_failed"] += 1
                    cleanup_results["results"].append({
                        "user_id": user_id,
                        "email": email,
                        "status": "failed",
                        "error": str(e),
                        "inactive_days": account["inactive_days"]
                    })
            
            logger.info(f"Account cleanup completed: {cleanup_results['accounts_deleted']} deleted, {cleanup_results['deletions_failed']} failed")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Failed to cleanup inactive accounts: {e}")
            raise
    
    def cleanup_expired_sessions(
        self,
        expired_days: int = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up expired authentication sessions.
        
        Args:
            expired_days: Days after expiration to clean up
            dry_run: If True, don't actually delete sessions
            
        Returns:
            Cleanup results
        """
        if expired_days is None:
            expired_days = self.default_retention_periods["session_cleanup"]
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=expired_days)
        
        try:
            # Find expired sessions to clean up
            expired_sessions_query = self.db.query(AuthSession).filter(
                or_(
                    AuthSession.expires_at < cutoff_date,
                    and_(
                        AuthSession.is_active == False,
                        AuthSession.invalidated_at < cutoff_date
                    )
                )
            )
            
            expired_count = expired_sessions_query.count()
            
            cleanup_results = {
                "expired_sessions_found": expired_count,
                "sessions_deleted": 0,
                "dry_run": dry_run,
                "cutoff_date": cutoff_date.isoformat(),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
            if not dry_run and expired_count > 0:
                # Delete expired sessions
                deleted_count = expired_sessions_query.delete(synchronize_session=False)
                self.db.commit()
                cleanup_results["sessions_deleted"] = deleted_count
            
            logger.info(f"Session cleanup: {cleanup_results['sessions_deleted']} sessions deleted")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            self.db.rollback()
            raise
    
    def cleanup_old_audit_logs(
        self,
        retention_days: int = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up old audit logs beyond retention period.
        
        Args:
            retention_days: Days to retain audit logs
            dry_run: If True, don't actually delete logs
            
        Returns:
            Cleanup results
        """
        if retention_days is None:
            retention_days = self.default_retention_periods["audit_log_retention"]
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        try:
            # Find old audit logs (but keep critical security events longer)
            old_logs_query = self.db.query(ConsentAuditLog).filter(
                ConsentAuditLog.created_at < cutoff_date,
                # Keep certain critical events longer
                ~ConsentAuditLog.event_type.in_([
                    'account_delete', 'data_export_requested', 'consent_given'
                ])
            )
            
            old_count = old_logs_query.count()
            
            cleanup_results = {
                "old_logs_found": old_count,
                "logs_deleted": 0,
                "dry_run": dry_run,
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat(),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
            if not dry_run and old_count > 0:
                # Delete old audit logs
                deleted_count = old_logs_query.delete(synchronize_session=False)
                self.db.commit()
                cleanup_results["logs_deleted"] = deleted_count
            
            logger.info(f"Audit log cleanup: {cleanup_results['logs_deleted']} logs deleted")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Failed to cleanup old audit logs: {e}")
            self.db.rollback()
            raise
    
    async def run_full_retention_cleanup(
        self,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Run comprehensive data retention cleanup.
        
        Args:
            dry_run: If True, don't actually delete data
            
        Returns:
            Complete cleanup results
        """
        cleanup_results = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "cleanup_tasks": {}
        }
        
        try:
            # 1. Send inactivity warnings
            logger.info("Starting inactivity warning process...")
            warning_results = await self.send_inactivity_warnings(dry_run=dry_run)
            cleanup_results["cleanup_tasks"]["inactivity_warnings"] = warning_results
            
            # 2. Clean up inactive accounts
            logger.info("Starting inactive account cleanup...")
            account_cleanup = await self.cleanup_inactive_accounts(dry_run=dry_run)
            cleanup_results["cleanup_tasks"]["inactive_accounts"] = account_cleanup
            
            # 3. Clean up expired sessions
            logger.info("Starting expired session cleanup...")
            session_cleanup = self.cleanup_expired_sessions(dry_run=dry_run)
            cleanup_results["cleanup_tasks"]["expired_sessions"] = session_cleanup
            
            # 4. Clean up old audit logs
            logger.info("Starting audit log cleanup...")
            audit_cleanup = self.cleanup_old_audit_logs(dry_run=dry_run)
            cleanup_results["cleanup_tasks"]["old_audit_logs"] = audit_cleanup
            
            cleanup_results["completed_at"] = datetime.now(timezone.utc).isoformat()
            cleanup_results["success"] = True
            
            logger.info("Full retention cleanup completed successfully")
            return cleanup_results
            
        except Exception as e:
            cleanup_results["completed_at"] = datetime.now(timezone.utc).isoformat()
            cleanup_results["success"] = False
            cleanup_results["error"] = str(e)
            
            logger.error(f"Failed to run full retention cleanup: {e}")
            raise
    
    def get_retention_statistics(self) -> Dict[str, Any]:
        """
        Get data retention statistics.
        
        Returns:
            Statistics about data retention status
        """
        try:
            stats = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "user_statistics": {},
                "session_statistics": {},
                "audit_statistics": {}
            }
            
            # User statistics
            total_users = self.db.query(User).filter(User.deleted_at.is_(None)).count()
            inactive_2_years = len(self.find_inactive_accounts(inactive_days=730))
            inactive_22_months = len(self.find_inactive_accounts(inactive_days=660))
            
            stats["user_statistics"] = {
                "total_active_users": total_users,
                "inactive_2_years": inactive_2_years,
                "inactive_22_months": inactive_22_months,
                "eligible_for_deletion": inactive_2_years,
                "eligible_for_warning": inactive_22_months - inactive_2_years
            }
            
            # Session statistics
            cutoff_30_days = datetime.now(timezone.utc) - timedelta(days=30)
            expired_sessions = self.db.query(AuthSession).filter(
                or_(
                    AuthSession.expires_at < cutoff_30_days,
                    and_(
                        AuthSession.is_active == False,
                        AuthSession.invalidated_at < cutoff_30_days
                    )
                )
            ).count()
            
            total_sessions = self.db.query(AuthSession).count()
            
            stats["session_statistics"] = {
                "total_sessions": total_sessions,
                "expired_sessions_eligible_for_cleanup": expired_sessions
            }
            
            # Audit statistics
            cutoff_7_years = datetime.now(timezone.utc) - timedelta(days=2555)
            old_audit_logs = self.db.query(ConsentAuditLog).filter(
                ConsentAuditLog.created_at < cutoff_7_years
            ).count()
            
            total_audit_logs = self.db.query(ConsentAuditLog).count()
            
            stats["audit_statistics"] = {
                "total_audit_logs": total_audit_logs,
                "old_logs_eligible_for_cleanup": old_audit_logs
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get retention statistics: {e}")
            raise


def get_data_retention_service(db: Session) -> DataRetentionService:
    """Get data retention service instance."""
    return DataRetentionService(db)