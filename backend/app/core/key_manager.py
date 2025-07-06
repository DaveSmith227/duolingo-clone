"""
Key Management System

Provides secure key derivation, storage, and lifecycle management
for encryption keys used throughout the application.
"""

import os
import base64
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

from .secrets import SecretsManager

logger = logging.getLogger(__name__)


class KeyInfo:
    """Information about a managed key."""
    
    def __init__(self, key_id: str, purpose: str, created_at: datetime,
                 expires_at: Optional[datetime] = None, 
                 rotated_from: Optional[str] = None):
        self.key_id = key_id
        self.purpose = purpose
        self.created_at = created_at
        self.expires_at = expires_at
        self.rotated_from = rotated_from
        self.is_active = True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'key_id': self.key_id,
            'purpose': self.purpose,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'rotated_from': self.rotated_from,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'KeyInfo':
        """Create from dictionary."""
        info = cls(
            key_id=data['key_id'],
            purpose=data['purpose'],
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            rotated_from=data.get('rotated_from')
        )
        info.is_active = data.get('is_active', True)
        return info


class KeyManager:
    """
    Manages encryption keys with secure derivation and lifecycle management.
    """
    
    # Key purposes
    PURPOSE_CONFIG = "config_encryption"
    PURPOSE_DATABASE = "database_field_encryption"
    PURPOSE_SESSION = "session_encryption"
    PURPOSE_TOKEN = "token_encryption"
    PURPOSE_FILE = "file_encryption"
    
    # Key derivation parameters
    MASTER_KEY_SIZE = 32  # 256 bits
    CONTEXT_HASH_SIZE = 16  # 128 bits
    DEFAULT_KEY_LIFETIME_DAYS = 90
    
    def __init__(self, master_secret: Optional[str] = None, 
                 key_store_path: Optional[Path] = None):
        """
        Initialize key manager.
        
        Args:
            master_secret: Base64-encoded master secret or None to load from env
            key_store_path: Path to store key metadata
        """
        # Load or generate master secret
        if master_secret:
            self._master_secret = base64.b64decode(master_secret)
        else:
            # Try to load from environment
            env_secret = os.environ.get('MASTER_KEY_SECRET')
            if env_secret:
                self._master_secret = base64.b64decode(env_secret)
            else:
                # Generate new master secret
                self._master_secret = os.urandom(self.MASTER_KEY_SIZE)
                logger.warning("Generated new master secret - ensure it's stored securely!")
        
        # Initialize key store
        self.key_store_path = key_store_path or Path.home() / '.duolingo_clone' / 'keys'
        self.key_store_path.mkdir(parents=True, exist_ok=True)
        
        # Load key metadata
        self._key_info: Dict[str, KeyInfo] = self._load_key_info()
        
        # Cache for derived keys
        self._key_cache: Dict[str, bytes] = {}
    
    def _load_key_info(self) -> Dict[str, KeyInfo]:
        """Load key metadata from storage."""
        info_file = self.key_store_path / 'key_info.json'
        if not info_file.exists():
            return {}
        
        try:
            with info_file.open('r') as f:
                data = json.load(f)
            
            return {
                key_id: KeyInfo.from_dict(info_data)
                for key_id, info_data in data.items()
            }
        except Exception as e:
            logger.error(f"Failed to load key info: {e}")
            return {}
    
    def _save_key_info(self):
        """Save key metadata to storage."""
        info_file = self.key_store_path / 'key_info.json'
        
        data = {
            key_id: info.to_dict()
            for key_id, info in self._key_info.items()
        }
        
        with info_file.open('w') as f:
            json.dump(data, f, indent=2)
    
    def derive_key(self, purpose: str, context: Optional[str] = None,
                   version: Optional[int] = None) -> Tuple[str, bytes]:
        """
        Derive a key for specific purpose and context.
        
        Args:
            purpose: Key purpose (e.g., PURPOSE_CONFIG)
            context: Additional context for derivation
            version: Specific version or None for latest
            
        Returns:
            Tuple of (key_id, key_bytes)
        """
        # Generate key ID
        key_id = self._generate_key_id(purpose, context, version)
        
        # Check cache
        if key_id in self._key_cache:
            return key_id, self._key_cache[key_id]
        
        # Derive key using HKDF-like approach
        # Step 1: Extract - create intermediate key material
        ikm_input = self._master_secret + purpose.encode('utf-8')
        if context:
            ikm_input += context.encode('utf-8')
        if version is not None:
            ikm_input += version.to_bytes(4, 'big')
        
        ikm = hashlib.sha256(ikm_input).digest()
        
        # Step 2: Expand - derive final key
        info = f"{purpose}:{context or 'default'}:v{version or 1}".encode('utf-8')
        
        # Use HMAC-based expansion
        import hmac
        
        t = b''
        okm = b''
        counter = 1
        
        while len(okm) < 32:  # AES-256 key size
            t = hmac.new(
                ikm, 
                t + info + bytes([counter]), 
                hashlib.sha256
            ).digest()
            okm += t
            counter += 1
        
        key = okm[:32]
        
        # Cache the key
        self._key_cache[key_id] = key
        
        # Record key info if new
        if key_id not in self._key_info:
            self._key_info[key_id] = KeyInfo(
                key_id=key_id,
                purpose=purpose,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=self.DEFAULT_KEY_LIFETIME_DAYS)
            )
            self._save_key_info()
        
        return key_id, key
    
    def _generate_key_id(self, purpose: str, context: Optional[str], 
                        version: Optional[int]) -> str:
        """Generate unique key identifier."""
        parts = [purpose]
        
        if context:
            # Hash context to fixed size
            context_hash = hashlib.sha256(context.encode('utf-8')).hexdigest()[:16]
            parts.append(context_hash)
        
        parts.append(f"v{version or 1}")
        
        return "_".join(parts)
    
    def get_active_key(self, purpose: str, context: Optional[str] = None) -> Tuple[str, bytes]:
        """
        Get the current active key for a purpose.
        
        Args:
            purpose: Key purpose
            context: Optional context
            
        Returns:
            Tuple of (key_id, key_bytes)
        """
        # Find latest version for this purpose/context
        matching_keys = [
            (info.key_id, info)
            for info in self._key_info.values()
            if info.purpose == purpose and info.is_active
        ]
        
        if not matching_keys:
            # Create new key
            return self.derive_key(purpose, context)
        
        # Sort by creation date and get latest
        matching_keys.sort(key=lambda x: x[1].created_at, reverse=True)
        latest_key_id = matching_keys[0][0]
        
        # Extract version from key_id
        version = int(latest_key_id.split('_v')[-1])
        
        return self.derive_key(purpose, context, version)
    
    def rotate_key(self, purpose: str, context: Optional[str] = None) -> Tuple[str, str, bytes]:
        """
        Rotate a key by creating a new version.
        
        Args:
            purpose: Key purpose
            context: Optional context
            
        Returns:
            Tuple of (old_key_id, new_key_id, new_key_bytes)
        """
        # Get current key
        old_key_id, _ = self.get_active_key(purpose, context)
        
        # Extract version and increment
        old_version = int(old_key_id.split('_v')[-1])
        new_version = old_version + 1
        
        # Derive new key
        new_key_id, new_key = self.derive_key(purpose, context, new_version)
        
        # Update key info
        if old_key_id in self._key_info:
            self._key_info[old_key_id].is_active = False
        
        self._key_info[new_key_id] = KeyInfo(
            key_id=new_key_id,
            purpose=purpose,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=self.DEFAULT_KEY_LIFETIME_DAYS),
            rotated_from=old_key_id
        )
        
        self._save_key_info()
        
        logger.info(f"Rotated key for {purpose}: {old_key_id} -> {new_key_id}")
        
        return old_key_id, new_key_id, new_key
    
    def get_key_info(self, key_id: str) -> Optional[KeyInfo]:
        """Get information about a specific key."""
        return self._key_info.get(key_id)
    
    def list_keys(self, purpose: Optional[str] = None, 
                  include_inactive: bool = False) -> List[KeyInfo]:
        """
        List all managed keys.
        
        Args:
            purpose: Filter by purpose
            include_inactive: Include inactive/rotated keys
            
        Returns:
            List of KeyInfo objects
        """
        keys = list(self._key_info.values())
        
        if purpose:
            keys = [k for k in keys if k.purpose == purpose]
        
        if not include_inactive:
            keys = [k for k in keys if k.is_active]
        
        return sorted(keys, key=lambda k: k.created_at, reverse=True)
    
    def cleanup_expired_keys(self, grace_period_days: int = 30) -> List[str]:
        """
        Remove expired keys from cache and metadata.
        
        Args:
            grace_period_days: Days after expiration before removal
            
        Returns:
            List of removed key IDs
        """
        removed = []
        cutoff = datetime.utcnow() - timedelta(days=grace_period_days)
        
        for key_id, info in list(self._key_info.items()):
            if info.expires_at and info.expires_at < cutoff and not info.is_active:
                # Remove from cache
                self._key_cache.pop(key_id, None)
                
                # Remove from metadata
                del self._key_info[key_id]
                
                removed.append(key_id)
                logger.info(f"Removed expired key: {key_id}")
        
        if removed:
            self._save_key_info()
        
        return removed
    
    def export_master_secret(self) -> str:
        """
        Export the master secret (use with extreme caution).
        
        Returns:
            Base64-encoded master secret
        """
        logger.warning("Master secret exported - ensure secure handling!")
        return base64.b64encode(self._master_secret).decode('utf-8')
    
    @classmethod
    def generate_master_secret(cls) -> str:
        """
        Generate a new master secret.
        
        Returns:
            Base64-encoded master secret
        """
        secret = os.urandom(cls.MASTER_KEY_SIZE)
        return base64.b64encode(secret).decode('utf-8')


# Global instance for convenience
_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """Get or create the global key manager instance."""
    global _key_manager
    
    if _key_manager is None:
        _key_manager = KeyManager()
    
    return _key_manager


def initialize_key_manager(master_secret: Optional[str] = None,
                          key_store_path: Optional[Path] = None):
    """Initialize the global key manager with specific settings."""
    global _key_manager
    
    _key_manager = KeyManager(master_secret, key_store_path)
    logger.info("Key manager initialized")