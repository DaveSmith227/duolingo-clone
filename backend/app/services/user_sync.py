"""
User Profile Sync Service

Service for synchronizing user profiles between Supabase Auth
and the application database.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User, OAuthProvider
from app.models.auth import SupabaseUser, AuthAuditLog
from app.core.supabase import get_supabase_client
from app.core.database import get_db_session

logger = logging.getLogger(__name__)


class UserSyncService:
    """
    Service for synchronizing user data between Supabase Auth and application database.
    
    Handles user creation, updates, and profile synchronization to ensure
    consistency between authentication and application data.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.supabase = get_supabase_client()
    
    async def sync_user_from_supabase(self, supabase_user_data: Dict[str, Any]) -> Tuple[User, SupabaseUser]:
        """
        Sync user from Supabase Auth to application database.
        
        Args:
            supabase_user_data: User data from Supabase Auth
            
        Returns:
            Tuple of (User, SupabaseUser) instances
            
        Raises:
            ValueError: If user data is invalid
            IntegrityError: If database constraints are violated
        """
        try:
            supabase_id = supabase_user_data.get('id')
            if not supabase_id:
                raise ValueError("Supabase user ID is required")
            
            # Check if Supabase user already exists
            supabase_user = self.db.query(SupabaseUser).filter(
                SupabaseUser.supabase_id == supabase_id
            ).first()
            
            if supabase_user:
                # Update existing user
                app_user = supabase_user.user
                await self._update_existing_user(app_user, supabase_user, supabase_user_data)
            else:
                # Create new user
                app_user, supabase_user = await self._create_new_user(supabase_user_data)
            
            # Log successful sync
            self._log_auth_event(
                supabase_user=supabase_user,
                event_type='profile_update',
                event_result='success',
                metadata={'action': 'user_sync'}
            )
            
            return app_user, supabase_user
            
        except Exception as e:
            logger.error(f"User sync failed for Supabase ID {supabase_user_data.get('id', 'unknown')}: {str(e)}")
            
            # Log failed sync if we have a Supabase user
            if 'supabase_user' in locals():
                self._log_auth_event(
                    supabase_user=supabase_user,
                    event_type='profile_update',
                    event_result='error',
                    error_message=str(e)
                )
            
            raise
    
    async def _create_new_user(self, supabase_user_data: Dict[str, Any]) -> Tuple[User, SupabaseUser]:
        """
        Create new user in application database from Supabase data.
        
        Args:
            supabase_user_data: User data from Supabase Auth
            
        Returns:
            Tuple of (User, SupabaseUser) instances
        """
        email = supabase_user_data.get('email')
        if not email:
            raise ValueError("Email is required for user creation")
        
        # Extract user metadata
        user_metadata = supabase_user_data.get('user_metadata', {})
        app_metadata = supabase_user_data.get('app_metadata', {})
        
        # Build user name from metadata or email
        name = (
            user_metadata.get('full_name') or
            user_metadata.get('name') or
            f"{user_metadata.get('first_name', '')} {user_metadata.get('last_name', '')}".strip() or
            email.split('@')[0]
        )
        
        # Create application user
        app_user = User(
            email=email,
            name=name,
            avatar_url=user_metadata.get('avatar_url') or user_metadata.get('picture'),
            is_email_verified=supabase_user_data.get('email_confirmed_at') is not None,
            timezone=user_metadata.get('timezone', 'UTC')
        )
        
        self.db.add(app_user)
        self.db.flush()  # Get the ID without committing
        
        # Create Supabase user record
        supabase_user = SupabaseUser(
            supabase_id=supabase_user_data['id'],
            app_user_id=app_user.id,
            email=email,
            email_verified=supabase_user_data.get('email_confirmed_at') is not None,
            phone=supabase_user_data.get('phone'),
            phone_verified=supabase_user_data.get('phone_confirmed_at') is not None,
            user_metadata=user_metadata,
            app_metadata=app_metadata
        )
        
        # Update from Supabase data
        supabase_user.update_from_supabase(supabase_user_data)
        supabase_user.mark_sync_success()
        
        self.db.add(supabase_user)
        
        # Create OAuth provider records if applicable
        identities = supabase_user_data.get('identities', [])
        for identity in identities:
            provider_name = identity.get('provider')
            if provider_name and provider_name != 'email':
                oauth_provider = OAuthProvider(
                    user_id=app_user.id,
                    provider=provider_name,
                    provider_user_id=identity.get('id', ''),
                    access_token=identity.get('access_token'),
                    refresh_token=identity.get('refresh_token')
                )
                
                # Set token expiration if available
                if identity.get('expires_in'):
                    oauth_provider.update_tokens(
                        access_token=identity.get('access_token', ''),
                        refresh_token=identity.get('refresh_token'),
                        expires_in=identity.get('expires_in')
                    )
                
                self.db.add(oauth_provider)
        
        self.db.commit()
        
        logger.info(f"Created new user: {app_user.email} (Supabase ID: {supabase_user.supabase_id})")
        return app_user, supabase_user
    
    async def _update_existing_user(self, app_user: User, supabase_user: SupabaseUser, 
                                   supabase_user_data: Dict[str, Any]):
        """
        Update existing user with data from Supabase.
        
        Args:
            app_user: Application User instance
            supabase_user: SupabaseUser instance
            supabase_user_data: Updated user data from Supabase Auth
        """
        try:
            # Update Supabase user record
            supabase_user.update_from_supabase(supabase_user_data)
            
            # Update application user if needed
            user_metadata = supabase_user_data.get('user_metadata', {})
            
            # Update email verification status
            if supabase_user_data.get('email_confirmed_at'):
                app_user.is_email_verified = True
                app_user.clear_email_verification()
            
            # Update avatar if provided in metadata
            if user_metadata.get('avatar_url') or user_metadata.get('picture'):
                app_user.avatar_url = user_metadata.get('avatar_url') or user_metadata.get('picture')
            
            # Update name if provided and different
            if user_metadata.get('full_name') and user_metadata['full_name'] != app_user.name:
                app_user.name = user_metadata['full_name']
            elif user_metadata.get('name') and user_metadata['name'] != app_user.name:
                app_user.name = user_metadata['name']
            
            # Update timezone if provided
            if user_metadata.get('timezone'):
                app_user.timezone = user_metadata['timezone']
            
            # Update OAuth provider tokens
            identities = supabase_user_data.get('identities', [])
            for identity in identities:
                provider_name = identity.get('provider')
                if provider_name and provider_name != 'email':
                    oauth_provider = self.db.query(OAuthProvider).filter(
                        OAuthProvider.user_id == app_user.id,
                        OAuthProvider.provider == provider_name
                    ).first()
                    
                    if oauth_provider:
                        # Update tokens
                        if identity.get('access_token'):
                            oauth_provider.update_tokens(
                                access_token=identity.get('access_token'),
                                refresh_token=identity.get('refresh_token'),
                                expires_in=identity.get('expires_in')
                            )
                    else:
                        # Create new OAuth provider record
                        oauth_provider = OAuthProvider(
                            user_id=app_user.id,
                            provider=provider_name,
                            provider_user_id=identity.get('id', ''),
                            access_token=identity.get('access_token'),
                            refresh_token=identity.get('refresh_token')
                        )
                        
                        if identity.get('expires_in'):
                            oauth_provider.update_tokens(
                                access_token=identity.get('access_token', ''),
                                refresh_token=identity.get('refresh_token'),
                                expires_in=identity.get('expires_in')
                            )
                        
                        self.db.add(oauth_provider)
            
            supabase_user.mark_sync_success()
            self.db.commit()
            
            logger.info(f"Updated user: {app_user.email} (Supabase ID: {supabase_user.supabase_id})")
            
        except Exception as e:
            supabase_user.mark_sync_error(str(e))
            self.db.commit()
            raise
    
    async def handle_user_deletion(self, supabase_id: str):
        """
        Handle user deletion from Supabase Auth.
        
        Args:
            supabase_id: Supabase user ID
        """
        try:
            supabase_user = self.db.query(SupabaseUser).filter(
                SupabaseUser.supabase_id == supabase_id
            ).first()
            
            if not supabase_user:
                logger.warning(f"Attempted to delete non-existent Supabase user: {supabase_id}")
                return
            
            app_user = supabase_user.user
            
            # Log deletion event
            self._log_auth_event(
                supabase_user=supabase_user,
                event_type='account_delete',
                event_result='success',
                metadata={'action': 'user_deletion'}
            )
            
            # Soft delete the application user (if using soft delete)
            if hasattr(app_user, 'soft_delete'):
                app_user.soft_delete()
            else:
                # Hard delete if no soft delete available
                self.db.delete(app_user)
            
            self.db.commit()
            
            logger.info(f"Deleted user: {app_user.email} (Supabase ID: {supabase_id})")
            
        except Exception as e:
            logger.error(f"User deletion failed for Supabase ID {supabase_id}: {str(e)}")
            raise
    
    def get_user_by_supabase_id(self, supabase_id: str) -> Optional[Tuple[User, SupabaseUser]]:
        """
        Get user by Supabase ID.
        
        Args:
            supabase_id: Supabase user ID
            
        Returns:
            Tuple of (User, SupabaseUser) if found, None otherwise
        """
        supabase_user = self.db.query(SupabaseUser).filter(
            SupabaseUser.supabase_id == supabase_id
        ).first()
        
        if supabase_user:
            return supabase_user.user, supabase_user
        return None
    
    def _log_auth_event(self, supabase_user: Optional[SupabaseUser], event_type: str, 
                       event_result: str, **kwargs):
        """
        Log authentication event for audit purposes.
        
        Args:
            supabase_user: SupabaseUser instance (optional)
            event_type: Type of authentication event
            event_result: Result of the event
            **kwargs: Additional log fields
        """
        try:
            log_entry = AuthAuditLog.create_log(
                event_type=event_type,
                event_result=event_result,
                supabase_user_id=supabase_user.id if supabase_user else None,
                **kwargs
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log auth event: {str(e)}")
    
    async def sync_all_pending_users(self) -> int:
        """
        Sync all users with pending sync status.
        
        Returns:
            Number of users successfully synced
        """
        pending_users = self.db.query(SupabaseUser).filter(
            SupabaseUser.sync_status == 'pending'
        ).all()
        
        synced_count = 0
        for supabase_user in pending_users:
            try:
                # Get fresh user data from Supabase
                user_data = await self.supabase.get_user_profile(supabase_user.supabase_id)
                if user_data:
                    await self._update_existing_user(
                        supabase_user.user, 
                        supabase_user, 
                        user_data
                    )
                    synced_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to sync pending user {supabase_user.supabase_id}: {str(e)}")
                supabase_user.mark_sync_error(str(e))
                self.db.commit()
        
        logger.info(f"Synced {synced_count} pending users")
        return synced_count


def get_user_sync_service(db: Session = None) -> UserSyncService:
    """
    Get UserSyncService instance.
    
    Args:
        db: Database session (will get from dependency if not provided)
        
    Returns:
        UserSyncService instance
    """
    if db is None:
        db = next(get_db_session())
    return UserSyncService(db)