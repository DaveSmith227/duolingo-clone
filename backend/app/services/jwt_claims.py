"""
JWT Claims Management Service

Service for managing custom JWT claims for role-based access control
and integration with Supabase Auth.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import jwt
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.auth import SupabaseUser
from app.models.rbac import Role, Permission, UserRoleAssignment
from app.core.config import get_settings
from app.core.supabase import get_supabase_client

logger = logging.getLogger(__name__)


class JWTClaimsService:
    """
    Service for managing custom JWT claims and role-based access control.
    
    Handles JWT token generation with custom claims, role validation,
    and integration with Supabase Auth for seamless authentication.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.supabase = get_supabase_client()
    
    def generate_custom_claims(self, user: User) -> Dict[str, Any]:
        """
        Generate custom JWT claims for a user.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary of custom claims
        """
        try:
            # Get user's active roles
            user_roles = self.get_user_active_roles(user.id)
            
            # Build role claims
            role_claims = []
            all_permissions = set()
            highest_priority = 0
            primary_role = None
            
            for role in user_roles:
                role_claim = role.get_jwt_claims()
                role_claims.append(role_claim)
                
                # Collect all permissions
                for perm in role.permissions:
                    all_permissions.add(perm.name)
                
                # Track highest priority role as primary
                if role.priority > highest_priority:
                    highest_priority = role.priority
                    primary_role = role
            
            # Build custom claims
            custom_claims = {
                'user_id': user.id,
                'email': user.email,
                'name': user.name,
                'email_verified': user.is_email_verified,
                'roles': [role.name for role in user_roles],
                'role_details': role_claims,
                'permissions': list(all_permissions),
                'primary_role': primary_role.name if primary_role else 'user',
                'role_priority': highest_priority,
                'claims_version': '1.0',
                'claims_issued_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add user metadata
            if hasattr(user, 'timezone') and user.timezone:
                custom_claims['timezone'] = user.timezone
            
            if hasattr(user, 'daily_xp_goal') and user.daily_xp_goal:
                custom_claims['daily_xp_goal'] = user.daily_xp_goal
            
            return custom_claims
            
        except Exception as e:
            logger.error(f"Failed to generate custom claims for user {user.id}: {str(e)}")
            # Return minimal claims on error
            return {
                'user_id': user.id,
                'email': user.email,
                'roles': ['user'],
                'permissions': ['profile.view', 'profile.edit', 'learning.courses.access'],
                'primary_role': 'user',
                'error': 'failed_to_load_roles'
            }
    
    def get_user_active_roles(self, user_id: str) -> List[Role]:
        """
        Get all active roles for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of active Role instances
        """
        try:
            # Query through user_roles table for active assignments
            role_assignments = self.db.query(UserRoleAssignment).filter(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.is_active == True
            ).all()
            
            active_roles = []
            for assignment in role_assignments:
                # Check if assignment is still valid (not expired)
                if assignment.is_valid and assignment.role.is_active:
                    active_roles.append(assignment.role)
            
            # If no roles assigned, assign default 'user' role
            if not active_roles:
                default_role = self.db.query(Role).filter(Role.name == 'user').first()
                if default_role:
                    # Auto-assign default role
                    self.assign_role_to_user(user_id, default_role.id)
                    active_roles.append(default_role)
            
            # Sort by priority (highest first)
            active_roles.sort(key=lambda r: r.priority, reverse=True)
            return active_roles
            
        except Exception as e:
            logger.error(f"Failed to get active roles for user {user_id}: {str(e)}")
            return []
    
    def assign_role_to_user(self, user_id: str, role_id: str, assigned_by: str = None, 
                           expires_in_days: Optional[int] = None, context: Dict[str, Any] = None) -> UserRoleAssignment:
        """
        Assign a role to a user.
        
        Args:
            user_id: User ID
            role_id: Role ID
            assigned_by: User ID of who assigned the role
            expires_in_days: Number of days until assignment expires
            context: Additional context for the assignment
            
        Returns:
            UserRoleAssignment instance
        """
        try:
            # Check if assignment already exists
            existing = self.db.query(UserRoleAssignment).filter(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role_id == role_id,
                UserRoleAssignment.is_active == True
            ).first()
            
            if existing:
                logger.info(f"Role {role_id} already assigned to user {user_id}")
                return existing
            
            # Create new assignment
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            
            assignment = UserRoleAssignment(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by,
                expires_at=expires_at,
                context=context
            )
            
            self.db.add(assignment)
            self.db.commit()
            
            logger.info(f"Assigned role {role_id} to user {user_id}")
            return assignment
            
        except Exception as e:
            logger.error(f"Failed to assign role {role_id} to user {user_id}: {str(e)}")
            self.db.rollback()
            raise
    
    def revoke_role_from_user(self, user_id: str, role_id: str, revoked_by: str = None) -> bool:
        """
        Revoke a role from a user.
        
        Args:
            user_id: User ID
            role_id: Role ID
            revoked_by: User ID of who revoked the role
            
        Returns:
            True if role was revoked, False if not found
        """
        try:
            assignment = self.db.query(UserRoleAssignment).filter(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role_id == role_id,
                UserRoleAssignment.is_active == True
            ).first()
            
            if not assignment:
                logger.warning(f"No active role assignment found for user {user_id} and role {role_id}")
                return False
            
            assignment.revoke(revoked_by)
            self.db.commit()
            
            logger.info(f"Revoked role {role_id} from user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke role {role_id} from user {user_id}: {str(e)}")
            self.db.rollback()
            raise
    
    def check_user_permission(self, user_id: str, permission: str, resource_id: str = None) -> bool:
        """
        Check if a user has a specific permission.
        
        Args:
            user_id: User ID
            permission: Permission name to check
            resource_id: Resource ID for scoped permissions
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            user_roles = self.get_user_active_roles(user_id)
            
            for role in user_roles:
                if role.has_permission(permission, resource_id=resource_id):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check permission {permission} for user {user_id}: {str(e)}")
            return False
    
    def validate_jwt_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token and extract claims.
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary of claims if valid, None otherwise
        """
        try:
            # Decode token using Supabase JWT secret
            decoded = jwt.decode(
                token,
                self.settings.supabase_jwt_secret,
                algorithms=['HS256'],
                options={'verify_exp': True}
            )
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to validate JWT token: {str(e)}")
            return None
    
    def refresh_user_claims(self, user_id: str) -> Dict[str, Any]:
        """
        Refresh custom claims for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated custom claims
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Generate fresh claims
            custom_claims = self.generate_custom_claims(user)
            
            # Update Supabase user metadata with custom claims
            supabase_user = self.db.query(SupabaseUser).filter(
                SupabaseUser.app_user_id == user_id
            ).first()
            
            if supabase_user and self.supabase.is_configured():
                try:
                    # Note: Supabase admin operations would need to be implemented separately
                    # For now, we'll just log that the update would happen
                    logger.info(f"Would update Supabase app metadata for user {supabase_user.supabase_id}")
                except Exception as e:
                    logger.error(f"Failed to update Supabase app metadata: {str(e)}")
            
            return custom_claims
            
        except Exception as e:
            logger.error(f"Failed to refresh claims for user {user_id}: {str(e)}")
            raise
    
    def create_role(self, name: str, display_name: str, description: str = None, 
                   permissions: List[str] = None, priority: int = 100) -> Role:
        """
        Create a new role.
        
        Args:
            name: Role name
            display_name: Human-readable role name
            description: Role description
            permissions: List of permission names to assign
            priority: Role priority
            
        Returns:
            Created Role instance
        """
        try:
            role = Role(
                name=name,
                display_name=display_name,
                description=description,
                priority=priority
            )
            
            self.db.add(role)
            self.db.flush()  # Get the ID
            
            # Assign permissions if provided
            if permissions:
                for perm_name in permissions:
                    permission = self.db.query(Permission).filter(
                        Permission.name == perm_name
                    ).first()
                    if permission:
                        role.permissions.append(permission)
            
            self.db.commit()
            
            logger.info(f"Created role: {name}")
            return role
            
        except Exception as e:
            logger.error(f"Failed to create role {name}: {str(e)}")
            self.db.rollback()
            raise
    
    def get_role_hierarchy(self) -> List[Dict[str, Any]]:
        """
        Get role hierarchy sorted by priority.
        
        Returns:
            List of role dictionaries with hierarchy information
        """
        try:
            roles = self.db.query(Role).filter(Role.is_active == True).order_by(
                Role.priority.desc()
            ).all()
            
            hierarchy = []
            for role in roles:
                hierarchy.append({
                    'id': role.id,
                    'name': role.name,
                    'display_name': role.display_name,
                    'role_type': role.role_type.value,
                    'priority': role.priority,
                    'permissions': [perm.name for perm in role.permissions],
                    'permission_count': len(role.permissions)
                })
            
            return hierarchy
            
        except Exception as e:
            logger.error(f"Failed to get role hierarchy: {str(e)}")
            return []


def get_jwt_claims_service(db: Session) -> JWTClaimsService:
    """
    Get JWTClaimsService instance.
    
    Args:
        db: Database session
        
    Returns:
        JWTClaimsService instance
    """
    return JWTClaimsService(db)