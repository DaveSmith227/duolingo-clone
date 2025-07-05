"""
SQLAlchemy encrypted field types for sensitive data.
"""
from typing import Any, Optional
from sqlalchemy.types import TypeDecorator, String, Text
from sqlalchemy import func

from app.services.encryption_service import EncryptionService


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type for encrypted string fields.
    
    Usage:
        class User(Base):
            __tablename__ = 'users'
            
            id = Column(Integer, primary_key=True)
            email = Column(String(255))  # Not encrypted (needed for lookups)
            ssn = Column(EncryptedString(255))  # Encrypted
            phone = Column(EncryptedString(50))  # Encrypted
    """
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect: Any) -> Optional[str]:
        """Encrypt value before storing in database."""
        if value is None:
            return None
        
        encryption_service = get_encryption_service()
        return encryption_service.encrypt_field(value)
    
    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[str]:
        """Decrypt value when loading from database."""
        if value is None:
            return None
        
        encryption_service = get_encryption_service()
        try:
            return encryption_service.decrypt_field(value)
        except ValueError:
            # Return None if decryption fails (corrupted data)
            return None


class EncryptedText(TypeDecorator):
    """
    SQLAlchemy type for encrypted text (large) fields.
    
    Usage:
        class Document(Base):
            __tablename__ = 'documents'
            
            id = Column(Integer, primary_key=True)
            title = Column(String(255))  # Not encrypted
            content = Column(EncryptedText)  # Encrypted
    """
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect: Any) -> Optional[str]:
        """Encrypt value before storing in database."""
        if value is None:
            return None
        
        encryption_service = get_encryption_service()
        return encryption_service.encrypt_field(value)
    
    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[str]:
        """Decrypt value when loading from database."""
        if value is None:
            return None
        
        encryption_service = get_encryption_service()
        try:
            return encryption_service.decrypt_field(value)
        except ValueError:
            # Return None if decryption fails
            return None


class HashedString(TypeDecorator):
    """
    SQLAlchemy type for one-way hashed strings (searchable but not retrievable).
    
    Usage:
        class AuditLog(Base):
            __tablename__ = 'audit_logs'
            
            id = Column(Integer, primary_key=True)
            user_id = Column(String(36))
            ip_address_hash = Column(HashedString(64))  # Hashed for privacy
    """
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect: Any) -> Optional[str]:
        """Hash value before storing in database."""
        if value is None:
            return None
        
        encryption_service = get_encryption_service()
        return encryption_service.hash_sensitive_data(value)
    
    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[str]:
        """Return hash value as-is (cannot be reversed)."""
        return value


class EncryptedJSON(TypeDecorator):
    """
    SQLAlchemy type for encrypted JSON fields.
    
    Usage:
        class UserPreferences(Base):
            __tablename__ = 'user_preferences'
            
            id = Column(Integer, primary_key=True)
            user_id = Column(String(36))
            sensitive_settings = Column(EncryptedJSON)  # Encrypted JSON
    """
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Optional[dict], dialect: Any) -> Optional[str]:
        """Serialize and encrypt JSON before storing."""
        if value is None:
            return None
        
        import json
        json_str = json.dumps(value)
        
        encryption_service = get_encryption_service()
        return encryption_service.encrypt_field(json_str)
    
    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[dict]:
        """Decrypt and deserialize JSON when loading."""
        if value is None:
            return None
        
        encryption_service = get_encryption_service()
        try:
            decrypted = encryption_service.decrypt_field(value)
            import json
            return json.loads(decrypted)
        except (ValueError, json.JSONDecodeError):
            # Return None if decryption or parsing fails
            return None


# Utility functions for searching encrypted fields
def search_encrypted_field(model_class, field_name: str, search_value: str):
    """
    Helper to search for exact matches in encrypted fields.
    
    Note: This requires decrypting all values, which is slow.
    Consider using HashedString for searchable fields instead.
    
    Usage:
        users = session.query(User).filter(
            search_encrypted_field(User, 'ssn', '123-45-6789')
        ).all()
    """
    encryption_service = get_encryption_service()
    encrypted_value = encryption_service.encrypt_field(search_value)
    
    # This only works if the same value encrypts to the same result
    # (which it won't with random nonces). Use with caution.
    # Better to use hashed fields for searching.
    return getattr(model_class, field_name) == encrypted_value


def create_searchable_hash(value: str) -> str:
    """
    Create a searchable hash of a value.
    
    Usage:
        # Store both encrypted and hashed versions
        user.ssn_encrypted = sensitive_ssn  # Uses EncryptedString
        user.ssn_hash = create_searchable_hash(sensitive_ssn)  # For searching
    """
    encryption_service = get_encryption_service()
    return encryption_service.hash_sensitive_data(value)