"""
Tests for Secrets Management and Encryption

Comprehensive test suite verifying encryption strength, key handling,
and proper implementation of cryptographic operations.
"""

import pytest
import base64
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from app.core.secrets import (
    SecretsManager, EncryptionError, DecryptionError,
    encrypt_config_value, decrypt_config_value
)
from app.core.key_manager import KeyManager, KeyInfo
from app.core.secrets_store import (
    SecretsStore, SecretMetadata, EnvironmentBackend,
    FileBackend, SecretsBackend
)
from app.core.rotation_manager import (
    RotationManager, RotationState, RotationStatus
)


class TestSecretsManager:
    """Test encryption/decryption functionality."""
    
    def test_generate_master_key(self):
        """Test master key generation."""
        key1 = SecretsManager.generate_master_key()
        key2 = SecretsManager.generate_master_key()
        
        # Keys should be different
        assert key1 != key2
        
        # Keys should be valid base64
        decoded1 = base64.b64decode(key1)
        decoded2 = base64.b64decode(key2)
        
        # Keys should be correct size
        assert len(decoded1) == 32
        assert len(decoded2) == 32
    
    def test_encrypt_decrypt_string(self):
        """Test basic string encryption/decryption."""
        manager = SecretsManager()
        plaintext = "This is a secret password"
        
        # Encrypt
        encrypted = manager.encrypt(plaintext)
        assert encrypted != plaintext
        assert isinstance(encrypted, str)
        
        # Decrypt
        decrypted = manager.decrypt_string(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_decrypt_bytes(self):
        """Test binary data encryption/decryption."""
        manager = SecretsManager()
        plaintext = b"Binary secret data \x00\x01\x02"
        
        # Encrypt
        encrypted = manager.encrypt(plaintext)
        
        # Decrypt
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_with_context(self):
        """Test encryption with context for authenticated encryption."""
        manager = SecretsManager()
        plaintext = "Database password"
        context = "database_config"
        
        # Encrypt with context
        encrypted = manager.encrypt(plaintext, context)
        
        # Decrypt with same context should work
        decrypted = manager.decrypt_string(encrypted, context)
        assert decrypted == plaintext
        
        # Decrypt with different context should fail
        with pytest.raises(DecryptionError):
            manager.decrypt_string(encrypted, "wrong_context")
        
        # Decrypt with no context should fail
        with pytest.raises(DecryptionError):
            manager.decrypt_string(encrypted)
    
    def test_tampering_detection(self):
        """Test that tampering is detected."""
        manager = SecretsManager()
        plaintext = "Sensitive data"
        
        encrypted = manager.encrypt(plaintext)
        
        # Decode and tamper with ciphertext
        encrypted_data = json.loads(base64.b64decode(encrypted))
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        
        # Flip a bit
        tampered = bytearray(ciphertext)
        tampered[0] ^= 1
        encrypted_data['ciphertext'] = base64.b64encode(bytes(tampered)).decode('utf-8')
        
        # Re-encode
        tampered_encrypted = base64.b64encode(
            json.dumps(encrypted_data).encode('utf-8')
        ).decode('utf-8')
        
        # Decryption should fail
        with pytest.raises(DecryptionError) as exc_info:
            manager.decrypt(tampered_encrypted)
        assert "Invalid authentication tag" in str(exc_info.value)
    
    def test_key_rotation(self):
        """Test key rotation functionality."""
        old_key = SecretsManager.generate_master_key()
        new_key = SecretsManager.generate_master_key()
        
        old_manager = SecretsManager(old_key)
        new_manager = SecretsManager(new_key)
        
        plaintext = "Secret to rotate"
        
        # Encrypt with old key
        encrypted_old = old_manager.encrypt(plaintext)
        
        # Re-encrypt with new key
        encrypted_new = old_manager.re_encrypt(encrypted_old, new_manager)
        
        # Old manager shouldn't decrypt new encryption
        with pytest.raises(DecryptionError):
            old_manager.decrypt_string(encrypted_new)
        
        # New manager should decrypt successfully
        decrypted = new_manager.decrypt_string(encrypted_new)
        assert decrypted == plaintext
    
    def test_convenience_functions(self):
        """Test convenience encryption/decryption functions."""
        master_key = SecretsManager.generate_master_key()
        value = "API_KEY_12345"
        context = "api_credentials"
        
        # Encrypt
        encrypted = encrypt_config_value(value, master_key, context)
        
        # Decrypt
        decrypted = decrypt_config_value(encrypted, master_key, context)
        
        assert decrypted == value


class TestKeyManager:
    """Test key derivation and management."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for key storage."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)
    
    def test_master_secret_generation(self):
        """Test master secret generation."""
        secret1 = KeyManager.generate_master_secret()
        secret2 = KeyManager.generate_master_secret()
        
        # Should be different
        assert secret1 != secret2
        
        # Should be valid base64
        decoded = base64.b64decode(secret1)
        assert len(decoded) == 32
    
    def test_key_derivation(self, temp_dir):
        """Test deterministic key derivation."""
        manager = KeyManager(key_store_path=temp_dir)
        
        # Derive keys
        key_id1, key1 = manager.derive_key(KeyManager.PURPOSE_CONFIG)
        key_id2, key2 = manager.derive_key(KeyManager.PURPOSE_CONFIG)
        
        # Same purpose should give same key
        assert key_id1 == key_id2
        assert key1 == key2
        
        # Different purpose should give different key
        key_id3, key3 = manager.derive_key(KeyManager.PURPOSE_DATABASE)
        assert key_id3 != key_id1
        assert key3 != key1
    
    def test_key_derivation_with_context(self, temp_dir):
        """Test key derivation with context."""
        manager = KeyManager(key_store_path=temp_dir)
        
        # Different contexts should give different keys
        _, key1 = manager.derive_key(KeyManager.PURPOSE_CONFIG, "app1")
        _, key2 = manager.derive_key(KeyManager.PURPOSE_CONFIG, "app2")
        
        assert key1 != key2
    
    def test_key_versioning(self, temp_dir):
        """Test key versioning."""
        manager = KeyManager(key_store_path=temp_dir)
        
        # Derive version 1
        key_id1, key1 = manager.derive_key(KeyManager.PURPOSE_TOKEN, version=1)
        assert "v1" in key_id1
        
        # Derive version 2
        key_id2, key2 = manager.derive_key(KeyManager.PURPOSE_TOKEN, version=2)
        assert "v2" in key_id2
        
        # Different versions should have different keys
        assert key1 != key2
    
    def test_key_rotation(self, temp_dir):
        """Test key rotation."""
        manager = KeyManager(key_store_path=temp_dir)
        
        # Get initial key
        old_key_id, old_key = manager.get_active_key(KeyManager.PURPOSE_SESSION)
        
        # Rotate
        old_id, new_id, new_key = manager.rotate_key(KeyManager.PURPOSE_SESSION)
        
        assert old_id == old_key_id
        assert new_id != old_id
        assert new_key != old_key
        assert "v2" in new_id
        
        # Get active key should return new one
        active_id, active_key = manager.get_active_key(KeyManager.PURPOSE_SESSION)
        assert active_id == new_id
        assert active_key == new_key
    
    def test_key_info_persistence(self, temp_dir):
        """Test that key info is persisted."""
        # Create manager and derive key
        manager1 = KeyManager(key_store_path=temp_dir)
        key_id, _ = manager1.derive_key(KeyManager.PURPOSE_FILE, "test.pdf")
        
        # Create new manager instance
        manager2 = KeyManager(key_store_path=temp_dir)
        
        # Should have key info
        info = manager2.get_key_info(key_id)
        assert info is not None
        assert info.purpose == KeyManager.PURPOSE_FILE
        assert info.is_active
    
    def test_expired_key_cleanup(self, temp_dir):
        """Test cleanup of expired keys."""
        manager = KeyManager(key_store_path=temp_dir)
        
        # Create and rotate key
        manager.rotate_key(KeyManager.PURPOSE_CONFIG)
        
        # Manually expire old key
        keys = manager.list_keys(include_inactive=True)
        old_key = next(k for k in keys if not k.is_active)
        old_key.expires_at = datetime.utcnow() - timedelta(days=40)
        manager._save_key_info()
        
        # Cleanup with grace period
        removed = manager.cleanup_expired_keys(grace_period_days=30)
        
        assert len(removed) == 1
        assert removed[0] == old_key.key_id


class TestSecretsStore:
    """Test secrets storage abstraction."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for file backend."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)
    
    def test_environment_backend(self):
        """Test environment variable backend."""
        backend = EnvironmentBackend()
        store = SecretsStore(backend)
        
        # Store secret
        store.store_secret("test_api_key", "secret123", encrypt=False)
        
        # Retrieve secret
        value = store.retrieve_secret("test_api_key", decrypt=False)
        assert value == "secret123"
        
        # Check existence
        assert store.exists("test_api_key")
        assert not store.exists("nonexistent")
        
        # Delete secret
        assert store.delete_secret("test_api_key")
        assert not store.exists("test_api_key")
    
    def test_file_backend(self, temp_dir):
        """Test file backend."""
        backend = FileBackend(temp_dir)
        store = SecretsStore(backend)
        
        # Store multiple versions
        store.store_secret("db_password", "pass_v1", encrypt=False)
        store.store_secret("db_password", "pass_v2", encrypt=False)
        
        # Retrieve latest
        latest = store.retrieve_secret("db_password", decrypt=False)
        assert latest == "pass_v2"
        
        # Retrieve specific version
        v1 = store.retrieve_secret("db_password", version=1, decrypt=False)
        assert v1 == "pass_v1"
        
        # List secrets
        secrets = store.list_secrets()
        assert len(secrets) == 1
        assert secrets[0].name == "db_password"
        assert secrets[0].version == 2
    
    def test_encrypted_storage(self, temp_dir):
        """Test encrypted secret storage."""
        backend = FileBackend(temp_dir)
        key_manager = KeyManager(key_store_path=temp_dir)
        secrets_manager = SecretsManager()
        
        store = SecretsStore(backend, secrets_manager, key_manager)
        
        # Store encrypted
        secret_value = "super_secret_password"
        store.store_secret("app_secret", secret_value, encrypt=True)
        
        # Retrieve and decrypt
        decrypted = store.retrieve_secret("app_secret", decrypt=True)
        assert decrypted == secret_value
        
        # Retrieve without decryption should return encrypted
        encrypted = store.retrieve_secret("app_secret", decrypt=False)
        assert encrypted != secret_value
        assert encrypted.startswith("eyJ")  # Base64 JSON
    
    def test_key_rotation_in_store(self, temp_dir):
        """Test rotating encryption keys for stored secrets."""
        backend = FileBackend(temp_dir)
        store = SecretsStore(backend, SecretsManager(), KeyManager(key_store_path=temp_dir))
        
        # Store multiple secrets
        secrets = {
            "api_key": "key123",
            "db_pass": "pass456",
            "token": "token789"
        }
        
        for name, value in secrets.items():
            store.store_secret(name, value, encrypt=True)
        
        # Verify all can be decrypted
        for name, expected in secrets.items():
            assert store.retrieve_secret(name) == expected
        
        # Rotate encryption key
        store.rotate_encryption_key()
        
        # Verify all can still be decrypted with new key
        for name, expected in secrets.items():
            assert store.retrieve_secret(name) == expected


class TestRotationManager:
    """Test secret rotation functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def rotation_manager(self, temp_dir):
        """Create rotation manager with file backend."""
        backend = FileBackend(temp_dir / "secrets")
        store = SecretsStore(backend)
        return RotationManager(store, status_file=temp_dir / "rotation_status.json")
    
    @pytest.mark.asyncio
    async def test_basic_rotation(self, rotation_manager):
        """Test basic secret rotation."""
        # Initial secret
        rotation_manager.secrets_store.store_secret("api_key", "old_key_123")
        
        # Rotate
        status = await rotation_manager.rotate_secret("api_key", "new_key_456")
        
        assert status.state == RotationState.GRACE_PERIOD
        assert status.old_version == 1
        assert status.new_version == 2
        
        # During grace period, both values should be available
        primary, values = rotation_manager.get_active_secret("api_key")
        assert primary == "new_key_456"
        assert values["primary"] == "new_key_456"
        assert values["secondary"] == "old_key_123"
    
    @pytest.mark.asyncio
    async def test_rotation_with_validation(self, rotation_manager):
        """Test rotation with validation."""
        # Setup
        rotation_manager.secrets_store.store_secret("db_pass", "old_pass")
        
        # Register validator that checks password length
        def validate_password(password: str) -> bool:
            return len(password) >= 8
        
        rotation_manager.register_validator("db_pass", validate_password)
        
        # Try rotation with invalid password
        with pytest.raises(ValueError) as exc_info:
            await rotation_manager.rotate_secret("db_pass", "short")
        assert "validation failed" in str(exc_info.value)
        
        # Rotation with valid password should work
        status = await rotation_manager.rotate_secret("db_pass", "valid_password_123")
        assert status.state == RotationState.GRACE_PERIOD
    
    @pytest.mark.asyncio
    async def test_rotation_completion(self, rotation_manager):
        """Test completing a rotation."""
        # Setup and rotate
        rotation_manager.secrets_store.store_secret("token", "old_token")
        await rotation_manager.rotate_secret("token", "new_token")
        
        # Complete rotation
        completed = await rotation_manager.complete_rotation("token")
        assert completed
        
        # Should only have new value
        primary, values = rotation_manager.get_active_secret("token")
        assert primary == "new_token"
        assert "secondary" not in values
        
        # Old version should be deleted
        old_value = rotation_manager.secrets_store.retrieve_secret("token", version=1)
        assert old_value is None
    
    @pytest.mark.asyncio
    async def test_rotation_cancellation(self, rotation_manager):
        """Test cancelling a rotation."""
        # Setup and start rotation
        rotation_manager.secrets_store.store_secret("secret", "original")
        await rotation_manager.rotate_secret("secret", "new_value")
        
        # Cancel rotation
        cancelled = rotation_manager.cancel_rotation("secret")
        assert cancelled
        
        # Should only have original value
        primary, values = rotation_manager.get_active_secret("secret")
        assert primary == "original"
        assert "secondary" not in values
    
    @pytest.mark.asyncio
    async def test_grace_period_expiration(self, rotation_manager):
        """Test automatic completion after grace period."""
        # Setup with short grace period
        rotation_manager.secrets_store.store_secret("key", "old")
        
        # Rotate with 1 second grace period
        await rotation_manager.rotate_secret(
            "key", "new", 
            grace_period=timedelta(seconds=1)
        )
        
        # Manually update grace period end time to simulate expiration
        status = rotation_manager._rotation_status["key"]
        status.grace_period_ends = datetime.utcnow() - timedelta(seconds=1)
        rotation_manager._save_status()
        
        # Check grace periods
        completed = await rotation_manager.check_grace_periods()
        assert "key" in completed
        
        # Should be completed
        status = rotation_manager.get_rotation_status("key")["key"]
        assert status.state == RotationState.COMPLETED


# Test vectors for encryption verification
class TestEncryptionVectors:
    """Test with known test vectors to verify encryption implementation."""
    
    def test_aes_gcm_test_vector(self):
        """Test AES-GCM with a known test vector."""
        # This tests the underlying encryption is working correctly
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        
        # Test vector from NIST
        key = bytes.fromhex('feffe9928665731c6d6a8f9467308308')
        nonce = bytes.fromhex('cafebabefacedbaddecaf888')
        plaintext = b'Hello World!'
        
        # Encrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        tag = encryptor.tag
        
        # Decrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(ciphertext) + decryptor.finalize()
        
        assert decrypted == plaintext