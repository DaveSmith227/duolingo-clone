"""
User Repository

Handles all user-related database operations.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for user-related database operations."""
    
    def __init__(self, db: Session):
        """Initialize user repository."""
        super().__init__(User, db)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User's email
            
        Returns:
            User or None if not found
        """
        return await self.find_one(email=email.lower())
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: User's username
            
        Returns:
            User or None if not found
        """
        return await self.find_one(username=username.lower())
    
    async def search_users(
        self,
        query: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[User]:
        """
        Search users by email, name, or username.
        
        Args:
            query: Search query
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of matching users
        """
        search_term = f"%{query}%"
        
        results = self.db.query(User).filter(
            or_(
                User.email.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.username.ilike(search_term)
            )
        ).offset(skip).limit(limit).all()
        
        return results
    
    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get all active users.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of active users
        """
        return await self.get_all(skip=skip, limit=limit, filters={"is_active": True})
    
    async def get_verified_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get all verified users.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of verified users
        """
        return await self.get_all(skip=skip, limit=limit, filters={"is_verified": True})
    
    async def create_user(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        **kwargs
    ) -> User:
        """
        Create new user.
        
        Args:
            email: User's email
            password_hash: Hashed password
            first_name: User's first name
            last_name: User's last name
            **kwargs: Additional user attributes
            
        Returns:
            Created user
        """
        user_data = {
            "email": email.lower(),
            "password_hash": password_hash,
            "first_name": first_name,
            "last_name": last_name,
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            **kwargs
        }
        
        return await self.create(**user_data)
    
    async def update_password(self, user_id: str, password_hash: str) -> bool:
        """
        Update user's password.
        
        Args:
            user_id: User ID
            password_hash: New password hash
            
        Returns:
            True if updated, False if user not found
        """
        user = await self.update(
            user_id,
            password_hash=password_hash,
            updated_at=datetime.utcnow()
        )
        return user is not None
    
    async def update_last_login(
        self,
        user_id: str,
        ip_address: str
    ) -> bool:
        """
        Update user's last login information.
        
        Args:
            user_id: User ID
            ip_address: Login IP address
            
        Returns:
            True if updated, False if user not found
        """
        user = await self.update(
            user_id,
            last_login_at=datetime.utcnow(),
            last_login_ip=ip_address
        )
        return user is not None
    
    async def verify_email(self, user_id: str) -> bool:
        """
        Mark user's email as verified.
        
        Args:
            user_id: User ID
            
        Returns:
            True if verified, False if user not found
        """
        user = await self.update(
            user_id,
            is_verified=True,
            verified_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return user is not None
    
    async def activate_user(self, user_id: str) -> bool:
        """
        Activate user account.
        
        Args:
            user_id: User ID
            
        Returns:
            True if activated, False if user not found
        """
        user = await self.update(
            user_id,
            is_active=True,
            updated_at=datetime.utcnow()
        )
        return user is not None
    
    async def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate user account.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deactivated, False if user not found
        """
        user = await self.update(
            user_id,
            is_active=False,
            updated_at=datetime.utcnow()
        )
        return user is not None
    
    async def get_users_by_role(
        self,
        role: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get users by role.
        
        Args:
            role: User role
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of users with specified role
        """
        return await self.get_all(skip=skip, limit=limit, filters={"role": role})
    
    async def update_user_profile(
        self,
        user_id: str,
        profile_data: Dict[str, Any]
    ) -> Optional[User]:
        """
        Update user profile information.
        
        Args:
            user_id: User ID
            profile_data: Profile data to update
            
        Returns:
            Updated user or None if not found
        """
        # Add updated timestamp
        profile_data["updated_at"] = datetime.utcnow()
        
        return await self.update(user_id, **profile_data)
    
    async def get_users_created_between(
        self,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get users created between dates.
        
        Args:
            start_date: Start date
            end_date: End date
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of users created in date range
        """
        return self.db.query(User).filter(
            and_(
                User.created_at >= start_date,
                User.created_at <= end_date
            )
        ).offset(skip).limit(limit).all()
    
    async def count_by_role(self) -> Dict[str, int]:
        """
        Count users by role.
        
        Returns:
            Dictionary with role counts
        """
        result = {}
        roles = ["user", "admin", "moderator", "instructor"]
        
        for role in roles:
            count = await self.count(filters={"role": role})
            result[role] = count
        
        return result