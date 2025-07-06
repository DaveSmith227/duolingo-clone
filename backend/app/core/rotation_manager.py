"""
Secret Rotation Manager

Provides zero-downtime secret rotation capabilities with support for
grace periods and automatic rollback on failure.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
import json
from pathlib import Path

from .secrets_store import SecretsStore, SecretMetadata
from .key_manager import KeyManager

logger = logging.getLogger(__name__)


class RotationState(Enum):
    """States for secret rotation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    GRACE_PERIOD = "grace_period"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RotationStatus:
    """Status of a secret rotation."""
    
    def __init__(self, secret_name: str, state: RotationState,
                 old_version: int, new_version: int,
                 started_at: datetime, grace_period_ends: Optional[datetime] = None,
                 completed_at: Optional[datetime] = None,
                 error: Optional[str] = None):
        self.secret_name = secret_name
        self.state = state
        self.old_version = old_version
        self.new_version = new_version
        self.started_at = started_at
        self.grace_period_ends = grace_period_ends
        self.completed_at = completed_at
        self.error = error
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'secret_name': self.secret_name,
            'state': self.state.value,
            'old_version': self.old_version,
            'new_version': self.new_version,
            'started_at': self.started_at.isoformat(),
            'grace_period_ends': self.grace_period_ends.isoformat() if self.grace_period_ends else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RotationStatus':
        """Create from dictionary."""
        return cls(
            secret_name=data['secret_name'],
            state=RotationState(data['state']),
            old_version=data['old_version'],
            new_version=data['new_version'],
            started_at=datetime.fromisoformat(data['started_at']),
            grace_period_ends=datetime.fromisoformat(data['grace_period_ends']) if data.get('grace_period_ends') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            error=data.get('error')
        )


class RotationManager:
    """
    Manages secret rotation with zero downtime.
    """
    
    def __init__(self, secrets_store: SecretsStore,
                 status_file: Optional[Path] = None,
                 default_grace_period_hours: int = 24):
        """
        Initialize rotation manager.
        
        Args:
            secrets_store: SecretsStore instance
            status_file: Path to store rotation status
            default_grace_period_hours: Default grace period in hours
        """
        self.secrets_store = secrets_store
        self.default_grace_period = timedelta(hours=default_grace_period_hours)
        
        # Status tracking
        self.status_file = status_file or Path.home() / '.duolingo_clone' / 'rotation_status.json'
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self._rotation_status: Dict[str, RotationStatus] = self._load_status()
        
        # Validation callbacks
        self._validators: Dict[str, Callable] = {}
    
    def _load_status(self) -> Dict[str, RotationStatus]:
        """Load rotation status from file."""
        if not self.status_file.exists():
            return {}
        
        try:
            with self.status_file.open('r') as f:
                data = json.load(f)
            
            return {
                name: RotationStatus.from_dict(status_data)
                for name, status_data in data.items()
            }
        except Exception as e:
            logger.error(f"Failed to load rotation status: {e}")
            return {}
    
    def _save_status(self):
        """Save rotation status to file."""
        data = {
            name: status.to_dict()
            for name, status in self._rotation_status.items()
        }
        
        with self.status_file.open('w') as f:
            json.dump(data, f, indent=2)
    
    def register_validator(self, secret_name: str, validator: Callable[[str], bool]):
        """
        Register a validation function for a secret.
        
        Args:
            secret_name: Secret name
            validator: Function that validates the secret value
        """
        self._validators[secret_name] = validator
        logger.info(f"Registered validator for secret '{secret_name}'")
    
    async def rotate_secret(self, secret_name: str, new_value: str,
                          grace_period: Optional[timedelta] = None,
                          validate_old: bool = True) -> RotationStatus:
        """
        Rotate a secret with grace period.
        
        Args:
            secret_name: Name of the secret to rotate
            new_value: New secret value
            grace_period: Grace period duration
            validate_old: Whether to validate old secret still works
            
        Returns:
            RotationStatus object
        """
        grace_period = grace_period or self.default_grace_period
        
        # Get current metadata
        current_metadata = self.secrets_store.get_metadata(secret_name)
        if not current_metadata:
            # First time storing this secret
            self.secrets_store.store_secret(secret_name, new_value)
            return RotationStatus(
                secret_name=secret_name,
                state=RotationState.COMPLETED,
                old_version=0,
                new_version=1,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
        
        old_version = current_metadata.version
        new_version = old_version + 1
        
        # Create rotation status
        status = RotationStatus(
            secret_name=secret_name,
            state=RotationState.PENDING,
            old_version=old_version,
            new_version=new_version,
            started_at=datetime.utcnow(),
            grace_period_ends=datetime.utcnow() + grace_period
        )
        
        self._rotation_status[secret_name] = status
        self._save_status()
        
        try:
            # Validate old secret if requested
            if validate_old and secret_name in self._validators:
                old_value = self.secrets_store.retrieve_secret(secret_name)
                if old_value and not self._validators[secret_name](old_value):
                    raise ValueError("Old secret validation failed")
            
            # Update state to in progress
            status.state = RotationState.IN_PROGRESS
            self._save_status()
            
            # Store new version
            self.secrets_store.store_secret(
                secret_name, 
                new_value,
                description=f"Rotated from version {old_version}"
            )
            
            # Validate new secret if validator registered
            if secret_name in self._validators:
                if not self._validators[secret_name](new_value):
                    raise ValueError("New secret validation failed")
            
            # Enter grace period
            status.state = RotationState.GRACE_PERIOD
            self._save_status()
            
            logger.info(f"Secret '{secret_name}' rotation entered grace period until {status.grace_period_ends}")
            
            return status
            
        except Exception as e:
            # Mark as failed
            status.state = RotationState.FAILED
            status.error = str(e)
            self._save_status()
            
            logger.error(f"Secret rotation failed for '{secret_name}': {e}")
            
            # Attempt rollback if new version was stored
            try:
                if self.secrets_store.backend.retrieve(secret_name, new_version):
                    self.secrets_store.backend.delete(secret_name, new_version)
                    status.state = RotationState.ROLLED_BACK
                    self._save_status()
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
            
            raise
    
    def get_active_secret(self, secret_name: str) -> Tuple[str, Dict[str, Any]]:
        """
        Get the active secret value(s) during rotation.
        
        During grace period, returns both old and new values.
        
        Args:
            secret_name: Secret name
            
        Returns:
            Tuple of (primary_value, {"primary": value, "secondary": optional_value})
        """
        status = self._rotation_status.get(secret_name)
        
        # No rotation in progress
        if not status or status.state == RotationState.COMPLETED:
            value = self.secrets_store.retrieve_secret(secret_name)
            if not value:
                raise ValueError(f"Secret '{secret_name}' not found")
            return value, {"primary": value}
        
        # Rotation failed or rolled back
        if status.state in (RotationState.FAILED, RotationState.ROLLED_BACK):
            value = self.secrets_store.retrieve_secret(secret_name, status.old_version)
            if not value:
                raise ValueError(f"Secret '{secret_name}' not found")
            return value, {"primary": value}
        
        # During grace period - return both values
        if status.state == RotationState.GRACE_PERIOD:
            new_value = self.secrets_store.retrieve_secret(secret_name, status.new_version)
            old_value = self.secrets_store.retrieve_secret(secret_name, status.old_version)
            
            if not new_value:
                raise ValueError(f"New secret version not found for '{secret_name}'")
            
            # Primary is new, secondary is old for backward compatibility
            return new_value, {
                "primary": new_value,
                "secondary": old_value
            }
        
        # In progress - return old value
        old_value = self.secrets_store.retrieve_secret(secret_name, status.old_version)
        if not old_value:
            raise ValueError(f"Secret '{secret_name}' not found")
        return old_value, {"primary": old_value}
    
    async def complete_rotation(self, secret_name: str) -> bool:
        """
        Complete a rotation after grace period.
        
        Args:
            secret_name: Secret name
            
        Returns:
            True if completed successfully
        """
        status = self._rotation_status.get(secret_name)
        if not status:
            logger.warning(f"No rotation in progress for '{secret_name}'")
            return False
        
        if status.state != RotationState.GRACE_PERIOD:
            logger.warning(f"Secret '{secret_name}' not in grace period (state: {status.state})")
            return False
        
        try:
            # Delete old version
            self.secrets_store.delete_secret(secret_name, status.old_version)
            
            # Update status
            status.state = RotationState.COMPLETED
            status.completed_at = datetime.utcnow()
            self._save_status()
            
            logger.info(f"Completed rotation for secret '{secret_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete rotation for '{secret_name}': {e}")
            status.error = str(e)
            self._save_status()
            return False
    
    async def check_grace_periods(self) -> List[str]:
        """
        Check for expired grace periods and complete rotations.
        
        Returns:
            List of secrets that were completed
        """
        completed = []
        now = datetime.utcnow()
        
        for secret_name, status in list(self._rotation_status.items()):
            if (status.state == RotationState.GRACE_PERIOD and 
                status.grace_period_ends and 
                now > status.grace_period_ends):
                
                logger.info(f"Grace period expired for '{secret_name}', completing rotation")
                
                if await self.complete_rotation(secret_name):
                    completed.append(secret_name)
        
        return completed
    
    def get_rotation_status(self, secret_name: Optional[str] = None) -> Dict[str, RotationStatus]:
        """
        Get rotation status for secrets.
        
        Args:
            secret_name: Specific secret or None for all
            
        Returns:
            Dictionary of secret name to RotationStatus
        """
        if secret_name:
            status = self._rotation_status.get(secret_name)
            return {secret_name: status} if status else {}
        
        return dict(self._rotation_status)
    
    def cancel_rotation(self, secret_name: str) -> bool:
        """
        Cancel an in-progress rotation.
        
        Args:
            secret_name: Secret name
            
        Returns:
            True if cancelled successfully
        """
        status = self._rotation_status.get(secret_name)
        if not status:
            return False
        
        if status.state not in (RotationState.PENDING, RotationState.IN_PROGRESS, RotationState.GRACE_PERIOD):
            logger.warning(f"Cannot cancel rotation in state {status.state}")
            return False
        
        try:
            # Delete new version if it exists
            if status.state in (RotationState.IN_PROGRESS, RotationState.GRACE_PERIOD):
                self.secrets_store.delete_secret(secret_name, status.new_version)
            
            # Update status
            status.state = RotationState.ROLLED_BACK
            status.completed_at = datetime.utcnow()
            self._save_status()
            
            logger.info(f"Cancelled rotation for secret '{secret_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel rotation for '{secret_name}': {e}")
            return False