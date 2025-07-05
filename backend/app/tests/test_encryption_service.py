"""
Tests for encryption service.
"""
import pytest
import json
from app.services.encryption_service import EncryptionService
from app.models.encrypted_fields import (
    EncryptedString, EncryptedText, HashedString, EncryptedJSON
)


@pytest.fixture
def encryption_service():
    """Create encryption service instance."""
    return EncryptionService()


class TestEncryptionService:
    """Test encryption service functionality."""
    
    def test_encrypt_decrypt_string(self, encryption_service):
        """Test string encryption and decryption."""
        plaintext = "sensitive data"
        
        # Encrypt
        encrypted = encryption_service.encrypt_field(plaintext)
        assert encrypted \!= plaintext
        assert isinstance(encrypted, str)
        
        # Decrypt
        decrypted = encryption_service.decrypt_field(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_decrypt_bytes(self, encryption_service):
        """Test bytes encryption and decryption."""
        plaintext = b"binary data"
        
        # Encrypt
        encrypted = encryption_service.encrypt_field(plaintext)
        assert isinstance(encrypted, str)
        
        # Decrypt
        decrypted = encryption_service.decrypt_field(encrypted)
        assert decrypted == plaintext.decode()
    
    def test_encrypt_empty_string(self, encryption_service):
        """Test encryption of empty string."""
        plaintext = ""
        
        encrypted = encryption_service.encrypt_field(plaintext)
        decrypted = encryption_service.decrypt_field(encrypted)
        
        assert decrypted == plaintext
    
    def test_decrypt_invalid_data(self, encryption_service):
        """Test decryption with invalid data."""
        with pytest.raises(Exception):
            encryption_service.decrypt_field("invalid_encrypted_data")
    
    def test_hash_sensitive_data(self, encryption_service):
        """Test one-way hashing."""
        data = "user@example.com"
        
        # Hash data
        hash1 = encryption_service.hash_sensitive_data(data)
        hash2 = encryption_service.hash_sensitive_data(data)
        
        # Same input produces same hash
        assert hash1 == hash2
        
        # Hash is different from input
        assert hash1 \!= data
        
        # Different input produces different hash
        hash3 = encryption_service.hash_sensitive_data("different@example.com")
        assert hash3 \!= hash1
    
    def test_unique_encryption(self, encryption_service):
        """Test that same data encrypted twice produces different ciphertext."""
        plaintext = "test data"
        
        encrypted1 = encryption_service.encrypt_field(plaintext)
        encrypted2 = encryption_service.encrypt_field(plaintext)
        
        # Different ciphertext due to random nonce
        assert encrypted1 \!= encrypted2
        
        # But both decrypt to same value
        assert encryption_service.decrypt_field(encrypted1) == plaintext
        assert encryption_service.decrypt_field(encrypted2) == plaintext


class TestEncryptedFields:
    """Test encrypted field types."""
    
    def test_encrypted_string_field(self):
        """Test EncryptedString field type."""
        field = EncryptedString(100)
        
        # Test process_bind_param (encryption)
        encrypted = field.process_bind_param("test value", None)
        assert encrypted \!= "test value"
        assert isinstance(encrypted, str)
        
        # Test process_result_value (decryption)
        decrypted = field.process_result_value(encrypted, None)
        assert decrypted == "test value"
        
        # Test None handling
        assert field.process_bind_param(None, None) is None
        assert field.process_result_value(None, None) is None
    
    def test_encrypted_text_field(self):
        """Test EncryptedText field type."""
        field = EncryptedText()
        
        long_text = "This is a longer text that would typically be stored in a TEXT field." * 10
        
        # Test encryption/decryption
        encrypted = field.process_bind_param(long_text, None)
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == long_text
    
    def test_hashed_string_field(self):
        """Test HashedString field type."""
        field = HashedString(64)
        
        # Test hashing
        email = "user@example.com"
        hashed = field.process_bind_param(email, None)
        
        # Hash characteristics
        assert hashed \!= email
        assert len(hashed) == 64  # SHA-256 produces 64 hex chars
        
        # Same input produces same hash
        hashed2 = field.process_bind_param(email, None)
        assert hashed == hashed2
        
        # process_result_value returns hash as-is
        assert field.process_result_value(hashed, None) == hashed
    
    def test_encrypted_json_field(self):
        """Test EncryptedJSON field type."""
        field = EncryptedJSON()
        
        # Test with dict
        data = {"key": "value", "number": 123, "nested": {"a": 1}}
        
        encrypted = field.process_bind_param(data, None)
        assert isinstance(encrypted, str)
        assert encrypted \!= json.dumps(data)
        
        decrypted = field.process_result_value(encrypted, None)
        assert decrypted == data
        
        # Test with list
        list_data = [1, 2, 3, {"a": "b"}]
        encrypted = field.process_bind_param(list_data, None)
        decrypted = field.process_result_value(encrypted, None)
        assert decrypted == list_data
        
        # Test None handling
        assert field.process_bind_param(None, None) is None
        assert field.process_result_value(None, None) is None
    
    def test_encrypted_json_invalid_data(self):
        """Test EncryptedJSON with invalid JSON after decryption."""
        field = EncryptedJSON()
        
        # Manually create invalid encrypted data
        with pytest.raises(Exception):
            field.process_result_value("invalid_encrypted_json", None)
EOF < /dev/null