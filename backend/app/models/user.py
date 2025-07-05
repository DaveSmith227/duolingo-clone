"""
User Management Models

SQLAlchemy models for user authentication, profile management, and OAuth integration
for the Duolingo clone backend application.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
import re

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel, SoftDeleteModel
from app.models.encrypted_fields import EncryptedString, HashedString


class User(SoftDeleteModel):
    """
    User model with authentication fields and profile information.
    
    Supports both email/password authentication and OAuth providers.
    Includes user preferences and learning goals.
    """
    
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User's email address (unique identifier)"
    )
    
    password_hash = Column(
        String(255),
        nullable=True,
        doc="Hashed password (NULL for OAuth-only users)"
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="User's display name"
    )
    
    avatar_url = Column(
        String(500),
        nullable=True,
        doc="URL to user's avatar image"
    )
    
    is_email_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether user's email has been verified"
    )
    
    email_verification_token = Column(
        String(255),
        nullable=True,
        doc="Token for email verification process"
    )
    
    password_reset_token = Column(
        String(255),
        nullable=True,
        doc="Token for password reset process"
    )
    
    password_reset_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Expiration time for password reset token"
    )
    
    daily_xp_goal = Column(
        Integer,
        default=20,
        nullable=False,
        doc="User's daily XP goal (10, 20, 30, or 50)"
    )
    
    timezone = Column(
        String(50),
        default='UTC',
        nullable=False,
        doc="User's timezone (e.g., 'UTC', 'America/New_York')"
    )
    
    # Relationships
    oauth_providers = relationship(
        "OAuthProvider",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="OAuth providers associated with this user"
    )
    
    # Table constraints
    __table_args__ = (
        CheckConstraint(
            daily_xp_goal.in_([10, 20, 30, 50]),
            name="valid_daily_xp_goal"
        ),
    )
    
    def __init__(self, **kwargs):
        """Initialize User with validation."""
        # Set defaults for fields that need them
        if 'is_email_verified' not in kwargs:
            kwargs['is_email_verified'] = False
        if 'daily_xp_goal' not in kwargs:
            kwargs['daily_xp_goal'] = 20
        if 'timezone' not in kwargs:
            kwargs['timezone'] = 'UTC'
        
        # Validate and set email manually to ensure validation runs
        email = kwargs.pop('email', None)
        name = kwargs.pop('name', None)
        timezone_val = kwargs.pop('timezone', 'UTC')
        
        # Initialize with remaining kwargs
        super().__init__(**kwargs)
        
        # Now set validated fields - always set them to trigger validation
        self.email = email  # This will trigger the validator
        self.name = name    # This will trigger the validator
        self.timezone = timezone_val  # This will trigger the validator
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format."""
        if not email:
            raise ValueError("Email is required")
        
        # Email validation that allows common valid formats but prevents edge cases
        # Allows: letters, numbers, dots, underscores, percent, hyphens, plus signs
        email_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9._+%-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$'
        
        # Check for consecutive dots which are invalid
        if '..' in email:
            raise ValueError("Invalid email format")
        
        # Check basic pattern
        if not re.match(email_pattern, email.lower()):
            raise ValueError("Invalid email format")
        
        return email.lower()
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate user name."""
        if name is None or not str(name).strip():
            raise ValueError("Name is required")
        
        name = str(name).strip()
        if len(name) < 1:
            raise ValueError("Name must be at least 1 character long")
        if len(name) > 255:
            raise ValueError("Name must be less than 255 characters")
        
        return name
    
    @validates('timezone')
    def validate_timezone(self, key, timezone_str):
        """Validate timezone string."""
        if not timezone_str:
            return 'UTC'
        
        # Basic timezone validation (simplified)
        valid_timezone_pattern = r'^[A-Za-z_/]+$'
        if not re.match(valid_timezone_pattern, timezone_str):
            raise ValueError("Invalid timezone format")
        
        return timezone_str
    
    @property
    def is_oauth_only(self) -> bool:
        """Check if user uses only OAuth authentication."""
        return self.password_hash is None
    
    @property
    def has_verified_email(self) -> bool:
        """Check if user has verified their email."""
        return bool(self.is_email_verified)
    
    @property
    def is_password_reset_valid(self) -> bool:
        """Check if password reset token is still valid."""
        if not self.password_reset_token or not self.password_reset_expires_at:
            return False
        return self.password_reset_expires_at > datetime.now(timezone.utc)
    
    def clear_password_reset(self):
        """Clear password reset token and expiration."""
        self.password_reset_token = None
        self.password_reset_expires_at = None
    
    def clear_email_verification(self):
        """Clear email verification token and mark as verified."""
        self.email_verification_token = None
        self.is_email_verified = True
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"


class OAuthProvider(BaseModel):
    """
    OAuth provider model for social login integration.
    
    Stores OAuth provider information and tokens for users who authenticate
    through Google, TikTok, Facebook, or other OAuth providers.
    """
    
    user_id = Column(
        String(36),  # UUID as string
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Foreign key to users table"
    )
    
    provider = Column(
        String(50),
        nullable=False,
        doc="OAuth provider name (google, tiktok, facebook)"
    )
    
    provider_user_id = Column(
        String(255),
        nullable=False,
        doc="User ID from the OAuth provider"
    )
    
    access_token = Column(
        EncryptedString(2000),  # Increased size for encrypted data
        nullable=True,
        doc="OAuth access token (encrypted)"
    )
    
    refresh_token = Column(
        EncryptedString(2000),  # Increased size for encrypted data
        nullable=True,
        doc="OAuth refresh token (encrypted)"
    )
    
    token_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Expiration time for access token"
    )
    
    # Relationships
    user = relationship(
        "User",
        back_populates="oauth_providers",
        doc="User associated with this OAuth provider"
    )
    
    # Table constraints
    __table_args__ = (
        # Unique constraint on provider + provider_user_id
        # This ensures one account per provider per external user ID
        UniqueConstraint('provider', 'provider_user_id', name='uq_oauth_provider_user'),
        CheckConstraint(
            "provider IN ('google', 'tiktok', 'facebook', 'apple')",
            name="valid_oauth_provider"
        ),
    )
    
    def __init__(self, **kwargs):
        """Initialize OAuthProvider with validation."""
        # Extract fields that need validation
        provider = kwargs.pop('provider', None)
        provider_user_id = kwargs.pop('provider_user_id', None)
        
        # Initialize with remaining kwargs
        super().__init__(**kwargs)
        
        # Set validated fields - this will trigger validators
        # Always set these fields to trigger validation, even for None values
        self.provider = provider  # This will trigger the validator
        self.provider_user_id = provider_user_id  # This will trigger the validator
    
    @validates('provider')
    def validate_provider(self, key, provider):
        """Validate OAuth provider name."""
        if not provider:
            raise ValueError("Provider is required")
        
        valid_providers = ['google', 'tiktok', 'facebook', 'apple']
        provider = provider.lower()
        
        if provider not in valid_providers:
            raise ValueError(f"Provider must be one of: {', '.join(valid_providers)}")
        
        return provider
    
    @validates('provider_user_id')
    def validate_provider_user_id(self, key, provider_user_id):
        """Validate provider user ID."""
        if provider_user_id is None or not str(provider_user_id).strip():
            raise ValueError("Provider user ID is required")
        
        return str(provider_user_id).strip()
    
    @property
    def is_token_expired(self) -> bool:
        """Check if access token has expired."""
        if not self.token_expires_at:
            return False
        return self.token_expires_at <= datetime.now(timezone.utc)
    
    @property
    def needs_refresh(self) -> bool:
        """Check if token needs to be refreshed."""
        return self.is_token_expired and self.refresh_token is not None
    
    def update_tokens(self, access_token: str, refresh_token: Optional[str] = None, 
                     expires_in: Optional[int] = None):
        """
        Update OAuth tokens.
        
        Args:
            access_token: New access token
            refresh_token: New refresh token (optional)
            expires_in: Token expiration time in seconds from now
        """
        self.access_token = access_token
        
        if refresh_token:
            self.refresh_token = refresh_token
        
        if expires_in:
            self.token_expires_at = datetime.now(timezone.utc).replace(
                microsecond=0
            ) + timedelta(seconds=expires_in)
    
    def __repr__(self) -> str:
        return f"<OAuthProvider(id={self.id}, user_id={self.user_id}, provider={self.provider})>"