"""
Field-Level Encryption Service

Provides encryption for sensitive data fields using AES-256-GCM.
"""
import base64
import os
from typing import Optional, Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive field data."""
    
    def __init__(self, settings = None):
        self.settings = settings or get_settings()
        self._key = self._derive_key()
    
    def _derive_key(self) -> bytes:
        """Derive encryption key from master key."""
        # Get master key from settings/environment
        master_key = self.settings.encryption_master_key
        if not master_key:
            raise ValueError("ENCRYPTION_MASTER_KEY not set in environment")
        
        # Use PBKDF2 to derive a key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=b'duolingo-clone-salt',  # In production, use unique salt per deployment
            iterations=100000,
            backend=default_backend()
        )
        
        return kdf.derive(master_key.encode())
    
    def encrypt_field(self, plaintext: Union[str, bytes]) -> str:
        """
        Encrypt a field value using AES-256-GCM.
        
        Args:
            plaintext: The value to encrypt
            
        Returns:
            Base64-encoded encrypted value with format: nonce:ciphertext:tag
        """
        if not plaintext:
            return ""
        
        # Convert to bytes if string
        if isinstance(plaintext, str):
            plaintext_bytes = plaintext.encode('utf-8')
        else:
            plaintext_bytes = plaintext
        
        # Generate random nonce (96 bits for GCM)
        nonce = os.urandom(12)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self._key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt and get tag
        ciphertext = encryptor.update(plaintext_bytes) + encryptor.finalize()
        
        # Combine nonce, ciphertext, and tag
        encrypted_data = nonce + ciphertext + encryptor.tag
        
        # Return base64 encoded
        return base64.urlsafe_b64encode(encrypted_data).decode('ascii')
    
    def decrypt_field(self, encrypted: str) -> str:
        """
        Decrypt a field value.
        
        Args:
            encrypted: Base64-encoded encrypted value
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted:
            return ""
        
        try:
            # Decode from base64
            encrypted_data = base64.urlsafe_b64decode(encrypted.encode('ascii'))
            
            # Extract components
            nonce = encrypted_data[:12]
            tag = encrypted_data[-16:]
            ciphertext = encrypted_data[12:-16]
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(self._key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt
            plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            # Log decryption failure but don't expose details
            print(f"Decryption failed: {type(e).__name__}")
            raise ValueError("Failed to decrypt field")
    
    def encrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data
            fields: List of field names to encrypt
            
        Returns:
            Dictionary with specified fields encrypted
        """
        encrypted_data = data.copy()
        
        for field in fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt_field(encrypted_data[field])
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields: List of field names to decrypt
            
        Returns:
            Dictionary with specified fields decrypted
        """
        decrypted_data = data.copy()
        
        for field in fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt_field(decrypted_data[field])
                except ValueError:
                    # Keep encrypted value if decryption fails
                    pass
        
        return decrypted_data
    
    def hash_sensitive_data(self, data: str) -> str:
        """
        One-way hash for sensitive data that needs to be searchable but not retrievable.
        
        Args:
            data: Data to hash
            
        Returns:
            Hex-encoded SHA-256 hash
        """
        if not data:
            return ""
        
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(data.encode('utf-8'))
        digest.update(self._key)  # Add key as salt
        
        return digest.finalize().hex()
    
    def verify_hash(self, data: str, hash_value: str) -> bool:
        """
        Verify data against a hash.
        
        Args:
            data: Original data
            hash_value: Hash to verify against
            
        Returns:
            True if data matches hash
        """
        return self.hash_sensitive_data(data) == hash_value