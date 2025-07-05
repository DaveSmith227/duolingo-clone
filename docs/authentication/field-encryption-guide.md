# Field-Level Encryption Implementation Guide

## Overview
This guide explains how to implement field-level encryption for sensitive data in the Duolingo clone application.

## Setup

### 1. Environment Configuration
Add encryption master key to your environment:
```bash
# .env
ENCRYPTION_MASTER_KEY=your-very-secure-master-key-minimum-32-chars
```

### 2. Install Dependencies
```bash
pip install cryptography
```

## Implementation

### Basic Encrypted Fields
```python
from app.models.encrypted_fields import EncryptedString, EncryptedText

class User(BaseModel):
    # Regular fields
    email = Column(String(255), unique=True)
    
    # Encrypted fields
    phone_number = Column(EncryptedString(50))
    ssn = Column(EncryptedString(20))
    medical_notes = Column(EncryptedText)
```

### Searchable Encrypted Fields
For fields that need to be searchable, store both encrypted and hashed versions:

```python
from app.models.encrypted_fields import EncryptedString, HashedString, create_searchable_hash

class User(BaseModel):
    # Store both versions
    ssn_encrypted = Column(EncryptedString(20))
    ssn_hash = Column(HashedString(64), index=True)
    
    def set_ssn(self, ssn: str):
        self.ssn_encrypted = ssn
        self.ssn_hash = create_searchable_hash(ssn)
```

Search by hash:
```python
# Find user by SSN
ssn_to_find = "123-45-6789"
search_hash = create_searchable_hash(ssn_to_find)
user = session.query(User).filter(User.ssn_hash == search_hash).first()
```

### Encrypted JSON Fields
```python
from app.models.encrypted_fields import EncryptedJSON

class UserPreferences(BaseModel):
    sensitive_settings = Column(EncryptedJSON)

# Usage
prefs = UserPreferences()
prefs.sensitive_settings = {
    "payment_method": "card",
    "card_last_four": "1234",
    "billing_address": "123 Main St"
}
```

## What to Encrypt

### Always Encrypt
- Government IDs (SSN, passport numbers)
- Financial data (bank accounts, credit cards)
- Medical/health information
- Precise location data
- Personal addresses
- Phone numbers
- Date of birth
- Biometric data

### Consider Encrypting
- Full names (depending on requirements)
- Email addresses (if not used for login)
- IP addresses (or use hashing)
- User preferences with PII
- Audit log details

### Do NOT Encrypt
- Primary keys/IDs
- Fields used for indexing/searching
- Timestamps
- Boolean flags
- Enum/status fields
- Foreign keys

## Migration Strategy

### 1. Add New Encrypted Columns
```sql
ALTER TABLE users ADD COLUMN phone_encrypted VARCHAR(255);
ALTER TABLE users ADD COLUMN phone_hash VARCHAR(64);
```

### 2. Migrate Existing Data
```python
from app.services.encryption_service import EncryptionService

encryption_service = EncryptionService()

# Batch process existing records
for user in session.query(User).yield_per(100):
    if user.phone_number and not user.phone_encrypted:
        user.phone_encrypted = user.phone_number  # Auto-encrypted
        user.phone_hash = create_searchable_hash(user.phone_number)

session.commit()
```

### 3. Update Application Code
```python
# Old
user.phone_number = "555-1234"

# New
user.phone_encrypted = "555-1234"
user.phone_hash = create_searchable_hash("555-1234")
```

### 4. Remove Old Columns
After verifying encryption works:
```sql
ALTER TABLE users DROP COLUMN phone_number;
ALTER TABLE users RENAME COLUMN phone_encrypted TO phone_number;
```

## Performance Considerations

### Indexing
- Cannot index encrypted fields directly
- Use hashed fields for exact match searches
- Consider partial encryption for range queries

### Caching
- Cache decrypted values in application memory
- Set appropriate TTLs
- Clear cache on updates

### Bulk Operations
```python
# Efficient bulk decryption
users = session.query(User).all()
for user in users:
    # Decryption happens on access
    print(user.phone_number)  # Decrypted automatically
```

## Security Best Practices

### Key Management
1. **Never** commit encryption keys to version control
2. Use different keys for different environments
3. Rotate keys periodically
4. Store keys in secure key management service

### Key Rotation
```python
# Example key rotation script
def rotate_encryption_key(old_key, new_key):
    old_service = EncryptionService(master_key=old_key)
    new_service = EncryptionService(master_key=new_key)
    
    for user in session.query(User).yield_per(100):
        if user.ssn_encrypted:
            # Decrypt with old key
            plaintext = old_service.decrypt_field(user.ssn_encrypted)
            # Re-encrypt with new key
            user.ssn_encrypted = new_service.encrypt_field(plaintext)
    
    session.commit()
```

### Access Control
- Limit database access to encrypted fields
- Audit all access to sensitive data
- Implement field-level permissions

### Compliance
- Document all encrypted fields
- Implement right to be forgotten (GDPR)
- Enable encryption at rest for database
- Use TLS for data in transit

## Testing

### Unit Tests
```python
def test_encryption_service():
    service = EncryptionService()
    
    # Test encryption/decryption
    plaintext = "sensitive-data"
    encrypted = service.encrypt_field(plaintext)
    decrypted = service.decrypt_field(encrypted)
    
    assert decrypted == plaintext
    assert encrypted != plaintext
```

### Integration Tests
```python
def test_encrypted_model_field():
    user = User()
    user.ssn = "123-45-6789"
    
    session.add(user)
    session.commit()
    
    # Verify encrypted in database
    raw_query = "SELECT ssn_encrypted FROM users WHERE id = :id"
    result = session.execute(raw_query, {"id": user.id}).first()
    
    assert result.ssn_encrypted != "123-45-6789"  # Should be encrypted
    assert user.ssn == "123-45-6789"  # Should decrypt automatically
```

## Monitoring

### Audit Encryption Operations
```python
@event.listens_for(EncryptedString, "process_bind_param", propagate=True)
def audit_encryption(value, dialect):
    logger.info("Encrypting field value")
    return value

@event.listens_for(EncryptedString, "process_result_value", propagate=True)
def audit_decryption(value, dialect):
    logger.info("Decrypting field value")
    return value
```

### Performance Metrics
- Track encryption/decryption time
- Monitor cache hit rates
- Alert on decryption failures

## Troubleshooting

### Common Issues

1. **Decryption Failures**
   - Check key hasn't changed
   - Verify data isn't corrupted
   - Ensure proper base64 encoding

2. **Performance Issues**
   - Implement caching
   - Use batch operations
   - Consider async encryption

3. **Search Problems**
   - Use hashed fields for exact matches
   - Cannot do partial matches on encrypted data
   - Consider external search service for complex queries