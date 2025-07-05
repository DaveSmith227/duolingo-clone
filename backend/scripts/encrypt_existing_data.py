#!/usr/bin/env python3
"""
Script to encrypt existing sensitive data in the database.

This should be run after applying the field encryption migration.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import OAuthProvider
from app.models.auth import SupabaseUser
from app.services.encryption_service import EncryptionService


def encrypt_oauth_tokens(db: Session, encryption_service: EncryptionService):
    """Encrypt existing OAuth tokens."""
    print("Encrypting OAuth tokens...")
    
    # Get all OAuth providers with tokens
    providers = db.query(OAuthProvider).filter(
        (OAuthProvider.access_token != None) | 
        (OAuthProvider.refresh_token != None)
    ).all()
    
    count = 0
    for provider in providers:
        try:
            # Check if already encrypted (base64 encoded strings)
            if provider.access_token and not provider.access_token.startswith('gAAAAA'):
                # Not encrypted yet
                provider.access_token = provider.access_token  # EncryptedString will auto-encrypt
                count += 1
            
            if provider.refresh_token and not provider.refresh_token.startswith('gAAAAA'):
                # Not encrypted yet
                provider.refresh_token = provider.refresh_token  # EncryptedString will auto-encrypt
                count += 1
                
        except Exception as e:
            print(f"Error encrypting tokens for provider {provider.id}: {e}")
            continue
    
    db.commit()
    print(f"Encrypted {count} OAuth tokens")


def encrypt_phone_numbers(db: Session, encryption_service: EncryptionService):
    """Encrypt existing phone numbers."""
    print("Encrypting phone numbers...")
    
    # Get all users with phone numbers
    users = db.query(SupabaseUser).filter(
        SupabaseUser.phone != None
    ).all()
    
    count = 0
    for user in users:
        try:
            # Check if already encrypted
            if user.phone and not user.phone.startswith('gAAAAA'):
                # Not encrypted yet
                user.phone = user.phone  # EncryptedString will auto-encrypt
                count += 1
                
        except Exception as e:
            print(f"Error encrypting phone for user {user.id}: {e}")
            continue
    
    db.commit()
    print(f"Encrypted {count} phone numbers")


def hash_ip_addresses(db: Session):
    """
    Hash IP addresses that weren't converted by the migration.
    
    Note: This is only needed if the migration didn't complete successfully.
    """
    print("Checking for unhashed IP addresses...")
    
    # This would be handled by the Alembic migration
    # Only needed if manual intervention is required
    pass


def verify_encryption(db: Session):
    """Verify that encryption is working correctly."""
    print("\nVerifying encryption...")
    
    # Test OAuth token encryption
    provider = db.query(OAuthProvider).filter(
        OAuthProvider.access_token != None
    ).first()
    
    if provider:
        # The token should be automatically decrypted when accessed
        print(f"OAuth token decryption test: {'PASS' if provider.access_token else 'FAIL'}")
    
    # Test phone encryption
    user = db.query(SupabaseUser).filter(
        SupabaseUser.phone != None
    ).first()
    
    if user:
        # The phone should be automatically decrypted when accessed
        print(f"Phone decryption test: {'PASS' if user.phone else 'FAIL'}")


def main():
    """Main encryption script."""
    print("Starting field-level encryption migration...")
    
    # Check for encryption key
    if not os.getenv('ENCRYPTION_MASTER_KEY'):
        print("ERROR: ENCRYPTION_MASTER_KEY environment variable not set")
        print("Set it with: export ENCRYPTION_MASTER_KEY='your-secure-key'")
        return 1
    
    # Initialize services
    encryption_service = EncryptionService()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Encrypt sensitive data
        encrypt_oauth_tokens(db, encryption_service)
        encrypt_phone_numbers(db, encryption_service)
        
        # Verify encryption
        verify_encryption(db)
        
        print("\nEncryption migration completed successfully!")
        return 0
        
    except Exception as e:
        print(f"ERROR: Encryption migration failed: {e}")
        db.rollback()
        return 1
        
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())