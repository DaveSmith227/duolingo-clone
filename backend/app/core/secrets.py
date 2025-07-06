"""
Secrets Management and Encryption Module

Provides secure encryption/decryption for sensitive configuration values
using AES-256-GCM encryption with authenticated encryption.
"""

import base64
import secrets
from typing import Optional, Tuple, Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag
import json
import logging

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption operations fail"""
    pass


class DecryptionError(Exception):
    """Raised when decryption operations fail"""
    pass


class SecretsManager:
    """
    Manages encryption and decryption of secrets using AES-256-GCM.
    """
    
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits for GCM
    TAG_SIZE = 16  # 128 bits
    SALT_SIZE = 32  # 256 bits
    ITERATIONS = 100_000  # PBKDF2 iterations
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize the secrets manager.
        
        Args:
            master_key: Base64-encoded master key or None to generate
        """
        if master_key:
            try:
                self._master_key = base64.b64decode(master_key)
                if len(self._master_key) != self.KEY_SIZE:
                    raise ValueError(f"Master key must be {self.KEY_SIZE} bytes")
            except Exception as e:
                raise ValueError(f"Invalid master key: {e}")
        else:
            self._master_key = self.generate_key()
    
    @classmethod
    def generate_key(cls) -> bytes:
        """Generate a new cryptographically secure key."""
        return secrets.token_bytes(cls.KEY_SIZE)
    
    @classmethod
    def generate_master_key(cls) -> str:
        """Generate a new base64-encoded master key."""
        return base64.b64encode(cls.generate_key()).decode('utf-8')
    
    def derive_key(self, salt: bytes, info: Optional[bytes] = None) -> bytes:
        """
        Derive a key from the master key using PBKDF2.
        
        Args:
            salt: Salt for key derivation
            info: Optional context information
            
        Returns:
            Derived key bytes
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            iterations=self.ITERATIONS,
            backend=default_backend()
        )
        
        key_material = self._master_key
        if info:
            key_material = self._master_key + info
            
        return kdf.derive(key_material)
    
    def encrypt(self, plaintext: Union[str, bytes], context: Optional[str] = None) -> str:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt (string or bytes)
            context: Optional context for key derivation
            
        Returns:
            Base64-encoded encrypted data with metadata
        """
        try:
            # Convert string to bytes if needed
            if isinstance(plaintext, str):
                plaintext_bytes = plaintext.encode('utf-8')
            else:
                plaintext_bytes = plaintext
            
            # Generate salt and nonce
            salt = secrets.token_bytes(self.SALT_SIZE)
            nonce = secrets.token_bytes(self.NONCE_SIZE)
            
            # Derive encryption key
            context_bytes = context.encode('utf-8') if context else None
            key = self.derive_key(salt, context_bytes)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Add associated data if context provided
            if context_bytes:
                encryptor.authenticate_additional_data(context_bytes)
            
            # Encrypt data
            ciphertext = encryptor.update(plaintext_bytes) + encryptor.finalize()
            
            # Package encrypted data with metadata
            encrypted_data = {
                'version': 1,
                'salt': base64.b64encode(salt).decode('utf-8'),
                'nonce': base64.b64encode(nonce).decode('utf-8'),
                'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
                'tag': base64.b64encode(encryptor.tag).decode('utf-8'),
                'context': context
            }
            
            # Encode as base64 JSON
            return base64.b64encode(
                json.dumps(encrypted_data).encode('utf-8')
            ).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}")
    
    def decrypt(self, encrypted_data: str, context: Optional[str] = None) -> bytes:
        """
        Decrypt data encrypted with AES-256-GCM.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            context: Optional context for key derivation (must match encryption)
            
        Returns:
            Decrypted data as bytes
        """
        try:
            # Decode base64 JSON
            encrypted_json = json.loads(
                base64.b64decode(encrypted_data).decode('utf-8')
            )
            
            # Extract components
            version = encrypted_json.get('version', 1)
            if version != 1:
                raise ValueError(f"Unsupported encryption version: {version}")
            
            salt = base64.b64decode(encrypted_json['salt'])
            nonce = base64.b64decode(encrypted_json['nonce'])
            ciphertext = base64.b64decode(encrypted_json['ciphertext'])
            tag = base64.b64decode(encrypted_json['tag'])
            stored_context = encrypted_json.get('context')
            
            # Verify context matches
            if context != stored_context:
                raise ValueError("Context mismatch")
            
            # Derive decryption key
            context_bytes = context.encode('utf-8') if context else None
            key = self.derive_key(salt, context_bytes)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Add associated data if context provided
            if context_bytes:
                decryptor.authenticate_additional_data(context_bytes)
            
            # Decrypt data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext
            
        except InvalidTag:
            logger.error("Authentication tag verification failed")
            raise DecryptionError("Invalid authentication tag - data may be tampered")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt data: {e}")
    
    def decrypt_string(self, encrypted_data: str, context: Optional[str] = None) -> str:
        """
        Decrypt data and return as string.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            context: Optional context for key derivation
            
        Returns:
            Decrypted string
        """
        plaintext_bytes = self.decrypt(encrypted_data, context)
        return plaintext_bytes.decode('utf-8')
    
    def rotate_key(self, new_master_key: str) -> 'SecretsManager':
        """
        Create a new SecretsManager instance with a new master key.
        
        Args:
            new_master_key: Base64-encoded new master key
            
        Returns:
            New SecretsManager instance
        """
        return SecretsManager(new_master_key)
    
    def re_encrypt(self, encrypted_data: str, new_manager: 'SecretsManager', 
                   context: Optional[str] = None) -> str:
        """
        Re-encrypt data with a new key (for key rotation).
        
        Args:
            encrypted_data: Data encrypted with current key
            new_manager: SecretsManager with new key
            context: Optional context
            
        Returns:
            Data encrypted with new key
        """
        # Decrypt with current key
        plaintext = self.decrypt(encrypted_data, context)
        
        # Encrypt with new key
        return new_manager.encrypt(plaintext, context)


def encrypt_config_value(value: str, master_key: str, 
                        context: Optional[str] = None) -> str:
    """
    Convenience function to encrypt a configuration value.
    
    Args:
        value: Value to encrypt
        master_key: Base64-encoded master key
        context: Optional context (e.g., "database_password")
        
    Returns:
        Encrypted value
    """
    manager = SecretsManager(master_key)
    return manager.encrypt(value, context)


def decrypt_config_value(encrypted_value: str, master_key: str,
                        context: Optional[str] = None) -> str:
    """
    Convenience function to decrypt a configuration value.
    
    Args:
        encrypted_value: Encrypted value
        master_key: Base64-encoded master key
        context: Optional context (must match encryption)
        
    Returns:
        Decrypted value
    """
    manager = SecretsManager(master_key)
    return manager.decrypt_string(encrypted_value, context)