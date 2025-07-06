"""
Secrets Storage Abstraction Layer

Provides a unified interface for storing and retrieving encrypted secrets
across different storage backends (environment variables, files, cloud providers).
"""

import os
import json
import base64
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .secrets import SecretsManager
from .key_manager import KeyManager

logger = logging.getLogger(__name__)


class SecretMetadata:
    """Metadata for a stored secret."""
    
    def __init__(self, name: str, version: int = 1, 
                 created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None,
                 description: Optional[str] = None,
                 tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.version = version
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.description = description
        self.tags = tags or {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'description': self.description,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SecretMetadata':
        """Create from dictionary."""
        return cls(
            name=data['name'],
            version=data.get('version', 1),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            description=data.get('description'),
            tags=data.get('tags', {})
        )


class SecretsBackend(ABC):
    """Abstract base class for secrets storage backends."""
    
    @abstractmethod
    def store(self, name: str, value: str, metadata: Optional[SecretMetadata] = None) -> None:
        """Store a secret."""
        pass
    
    @abstractmethod
    def retrieve(self, name: str, version: Optional[int] = None) -> Optional[str]:
        """Retrieve a secret."""
        pass
    
    @abstractmethod
    def exists(self, name: str) -> bool:
        """Check if a secret exists."""
        pass
    
    @abstractmethod
    def delete(self, name: str, version: Optional[int] = None) -> bool:
        """Delete a secret."""
        pass
    
    @abstractmethod
    def list_secrets(self) -> List[SecretMetadata]:
        """List all secrets."""
        pass
    
    @abstractmethod
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        """Get metadata for a secret."""
        pass


class EnvironmentBackend(SecretsBackend):
    """Store secrets in environment variables."""
    
    def __init__(self, prefix: str = "SECRET_"):
        self.prefix = prefix
        self._metadata_cache: Dict[str, SecretMetadata] = {}
    
    def _get_env_key(self, name: str) -> str:
        """Get environment variable name."""
        return f"{self.prefix}{name.upper()}"
    
    def store(self, name: str, value: str, metadata: Optional[SecretMetadata] = None) -> None:
        """Store secret in environment variable."""
        env_key = self._get_env_key(name)
        os.environ[env_key] = value
        
        # Cache metadata
        if metadata:
            self._metadata_cache[name] = metadata
        else:
            self._metadata_cache[name] = SecretMetadata(name)
        
        logger.info(f"Stored secret '{name}' in environment")
    
    def retrieve(self, name: str, version: Optional[int] = None) -> Optional[str]:
        """Retrieve secret from environment variable."""
        env_key = self._get_env_key(name)
        value = os.environ.get(env_key)
        
        if value:
            logger.debug(f"Retrieved secret '{name}' from environment")
        
        return value
    
    def exists(self, name: str) -> bool:
        """Check if secret exists in environment."""
        env_key = self._get_env_key(name)
        return env_key in os.environ
    
    def delete(self, name: str, version: Optional[int] = None) -> bool:
        """Delete secret from environment."""
        env_key = self._get_env_key(name)
        if env_key in os.environ:
            del os.environ[env_key]
            self._metadata_cache.pop(name, None)
            logger.info(f"Deleted secret '{name}' from environment")
            return True
        return False
    
    def list_secrets(self) -> List[SecretMetadata]:
        """List secrets in environment."""
        secrets = []
        for key in os.environ:
            if key.startswith(self.prefix):
                name = key[len(self.prefix):].lower()
                metadata = self._metadata_cache.get(name, SecretMetadata(name))
                secrets.append(metadata)
        return secrets
    
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        """Get metadata for a secret."""
        if self.exists(name):
            return self._metadata_cache.get(name, SecretMetadata(name))
        return None


class FileBackend(SecretsBackend):
    """Store secrets in encrypted files."""
    
    def __init__(self, base_path: Path, file_extension: str = ".secret"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.file_extension = file_extension
        self.metadata_file = self.base_path / "metadata.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from file."""
        self._metadata: Dict[str, SecretMetadata] = {}
        if self.metadata_file.exists():
            try:
                with self.metadata_file.open('r') as f:
                    data = json.load(f)
                    for name, meta_dict in data.items():
                        self._metadata[name] = SecretMetadata.from_dict(meta_dict)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
    
    def _save_metadata(self):
        """Save metadata to file."""
        data = {
            name: meta.to_dict() 
            for name, meta in self._metadata.items()
        }
        with self.metadata_file.open('w') as f:
            json.dump(data, f, indent=2)
    
    def _get_file_path(self, name: str, version: Optional[int] = None) -> Path:
        """Get file path for a secret."""
        if version:
            filename = f"{name}_v{version}{self.file_extension}"
        else:
            filename = f"{name}{self.file_extension}"
        return self.base_path / filename
    
    def store(self, name: str, value: str, metadata: Optional[SecretMetadata] = None) -> None:
        """Store secret in file."""
        # Determine version
        if metadata:
            version = metadata.version
        else:
            # Get next version
            existing = self.get_metadata(name)
            version = existing.version + 1 if existing else 1
            metadata = SecretMetadata(name, version=version)
        
        # Write to file
        file_path = self._get_file_path(name, version)
        file_path.write_text(value)
        
        # Update metadata
        self._metadata[name] = metadata
        self._save_metadata()
        
        logger.info(f"Stored secret '{name}' version {version} to file")
    
    def retrieve(self, name: str, version: Optional[int] = None) -> Optional[str]:
        """Retrieve secret from file."""
        if not version:
            # Get latest version
            metadata = self.get_metadata(name)
            if not metadata:
                return None
            version = metadata.version
        
        file_path = self._get_file_path(name, version)
        if file_path.exists():
            value = file_path.read_text()
            logger.debug(f"Retrieved secret '{name}' version {version} from file")
            return value
        
        return None
    
    def exists(self, name: str) -> bool:
        """Check if secret exists."""
        return name in self._metadata
    
    def delete(self, name: str, version: Optional[int] = None) -> bool:
        """Delete secret file."""
        if version:
            # Delete specific version
            file_path = self._get_file_path(name, version)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted secret '{name}' version {version}")
                return True
        else:
            # Delete all versions
            deleted = False
            for file_path in self.base_path.glob(f"{name}*{self.file_extension}"):
                file_path.unlink()
                deleted = True
            
            if deleted:
                self._metadata.pop(name, None)
                self._save_metadata()
                logger.info(f"Deleted all versions of secret '{name}'")
            
            return deleted
        
        return False
    
    def list_secrets(self) -> List[SecretMetadata]:
        """List all secrets."""
        return list(self._metadata.values())
    
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        """Get metadata for a secret."""
        return self._metadata.get(name)


class CloudBackend(SecretsBackend):
    """Base class for cloud provider backends."""
    
    def __init__(self, provider: str):
        self.provider = provider
        logger.info(f"Initialized {provider} backend")


class AWSSecretsManagerBackend(CloudBackend):
    """AWS Secrets Manager backend (placeholder for future implementation)."""
    
    def __init__(self):
        super().__init__("AWS Secrets Manager")
        # TODO: Implement AWS Secrets Manager integration
        logger.warning("AWS Secrets Manager backend not yet implemented")
    
    def store(self, name: str, value: str, metadata: Optional[SecretMetadata] = None) -> None:
        raise NotImplementedError("AWS Secrets Manager backend not yet implemented")
    
    def retrieve(self, name: str, version: Optional[int] = None) -> Optional[str]:
        raise NotImplementedError("AWS Secrets Manager backend not yet implemented")
    
    def exists(self, name: str) -> bool:
        raise NotImplementedError("AWS Secrets Manager backend not yet implemented")
    
    def delete(self, name: str, version: Optional[int] = None) -> bool:
        raise NotImplementedError("AWS Secrets Manager backend not yet implemented")
    
    def list_secrets(self) -> List[SecretMetadata]:
        raise NotImplementedError("AWS Secrets Manager backend not yet implemented")
    
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        raise NotImplementedError("AWS Secrets Manager backend not yet implemented")


class SecretsStore:
    """
    High-level secrets storage interface with encryption.
    """
    
    def __init__(self, backend: SecretsBackend, 
                 secrets_manager: Optional[SecretsManager] = None,
                 key_manager: Optional[KeyManager] = None):
        """
        Initialize secrets store.
        
        Args:
            backend: Storage backend to use
            secrets_manager: SecretsManager for encryption
            key_manager: KeyManager for key derivation
        """
        self.backend = backend
        self.secrets_manager = secrets_manager
        self.key_manager = key_manager
        
        # If encryption is enabled, ensure both managers are available
        if self.secrets_manager and not self.key_manager:
            self.key_manager = KeyManager()
        elif self.key_manager and not self.secrets_manager:
            # Get encryption key from key manager
            _, key = self.key_manager.get_active_key(KeyManager.PURPOSE_CONFIG)
            master_key = base64.b64encode(key).decode('utf-8')
            self.secrets_manager = SecretsManager(master_key)
    
    def store_secret(self, name: str, value: str, 
                    description: Optional[str] = None,
                    tags: Optional[Dict[str, str]] = None,
                    encrypt: bool = True) -> None:
        """
        Store a secret with optional encryption.
        
        Args:
            name: Secret name
            value: Secret value
            description: Optional description
            tags: Optional tags
            encrypt: Whether to encrypt the value
        """
        # Create metadata
        existing = self.backend.get_metadata(name)
        version = existing.version + 1 if existing else 1
        
        metadata = SecretMetadata(
            name=name,
            version=version,
            description=description,
            tags=tags
        )
        
        # Encrypt if requested
        if encrypt and self.secrets_manager:
            encrypted_value = self.secrets_manager.encrypt(value, context=name)
            self.backend.store(name, encrypted_value, metadata)
            logger.info(f"Stored encrypted secret '{name}' version {version}")
        else:
            self.backend.store(name, value, metadata)
            logger.info(f"Stored plaintext secret '{name}' version {version}")
    
    def retrieve_secret(self, name: str, version: Optional[int] = None,
                       decrypt: bool = True) -> Optional[str]:
        """
        Retrieve a secret with optional decryption.
        
        Args:
            name: Secret name
            version: Optional version
            decrypt: Whether to decrypt the value
            
        Returns:
            Secret value or None if not found
        """
        stored_value = self.backend.retrieve(name, version)
        if not stored_value:
            return None
        
        # Decrypt if requested and value appears encrypted
        if decrypt and self.secrets_manager and stored_value.startswith('eyJ'):
            try:
                decrypted_value = self.secrets_manager.decrypt_string(stored_value, context=name)
                logger.debug(f"Retrieved and decrypted secret '{name}'")
                return decrypted_value
            except Exception as e:
                logger.warning(f"Failed to decrypt secret '{name}': {e}")
                return stored_value
        
        return stored_value
    
    def exists(self, name: str) -> bool:
        """Check if a secret exists."""
        return self.backend.exists(name)
    
    def delete_secret(self, name: str, version: Optional[int] = None) -> bool:
        """Delete a secret."""
        return self.backend.delete(name, version)
    
    def list_secrets(self) -> List[SecretMetadata]:
        """List all secrets."""
        return self.backend.list_secrets()
    
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        """Get metadata for a secret."""
        return self.backend.get_metadata(name)
    
    def rotate_encryption_key(self) -> None:
        """Rotate encryption keys for all secrets."""
        if not self.key_manager or not self.secrets_manager:
            raise ValueError("Encryption not enabled")
        
        # Rotate key in key manager
        old_key_id, new_key_id, new_key = self.key_manager.rotate_key(KeyManager.PURPOSE_CONFIG)
        
        # Create new secrets manager with new key
        new_master_key = base64.b64encode(new_key).decode('utf-8')
        new_secrets_manager = SecretsManager(new_master_key)
        
        # Re-encrypt all secrets
        for metadata in self.list_secrets():
            # Retrieve with old key
            value = self.retrieve_secret(metadata.name, decrypt=True)
            if value:
                # Store with new key
                encrypted_value = new_secrets_manager.encrypt(value, context=metadata.name)
                self.backend.store(metadata.name, encrypted_value, metadata)
        
        # Update secrets manager
        self.secrets_manager = new_secrets_manager
        
        logger.info(f"Rotated encryption keys: {old_key_id} -> {new_key_id}")