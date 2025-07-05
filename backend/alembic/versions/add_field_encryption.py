"""Add field-level encryption to sensitive data

Revision ID: add_field_encryption
Revises: latest
Create Date: 2024-01-20

This migration adds field-level encryption to sensitive user data and converts
IP addresses to hashed values for privacy protection.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_field_encryption'
down_revision = 'latest'  # Update with actual revision
branch_labels = None
depends_on = None


def upgrade():
    """Apply field-level encryption changes."""
    
    # OAuth Provider - Encrypt tokens
    op.alter_column('oauth_providers', 'access_token',
                    type_=sa.String(2000),  # Increased for encryption
                    existing_type=sa.String(1000),
                    comment='OAuth access token (encrypted)')
    
    op.alter_column('oauth_providers', 'refresh_token',
                    type_=sa.String(2000),  # Increased for encryption
                    existing_type=sa.String(1000),
                    comment='OAuth refresh token (encrypted)')
    
    # Supabase User - Encrypt phone number
    op.alter_column('supabase_users', 'phone',
                    type_=sa.String(100),  # Increased for encryption
                    existing_type=sa.String(50),
                    comment='Phone number from Supabase Auth (encrypted)')
    
    # Auth Session - Convert IP to hash
    op.add_column('auth_sessions', 
                  sa.Column('ip_address_hash', sa.String(64), nullable=True,
                           comment='Hashed IP address for privacy protection'))
    
    # Copy and hash existing IP addresses
    op.execute("""
        UPDATE auth_sessions 
        SET ip_address_hash = encode(sha256(ip_address::bytea), 'hex')
        WHERE ip_address IS NOT NULL
    """)
    
    # Drop old IP column
    op.drop_column('auth_sessions', 'ip_address')
    
    # User Activity Log - Convert IP to hash
    op.add_column('user_activity_logs',
                  sa.Column('ip_address_hash', sa.String(64), nullable=True,
                           comment='Hashed IP address for privacy protection'))
    
    # Copy and hash existing IP addresses
    op.execute("""
        UPDATE user_activity_logs 
        SET ip_address_hash = encode(sha256(ip_address::bytea), 'hex')
        WHERE ip_address IS NOT NULL
    """)
    
    # Drop old IP column
    op.drop_column('user_activity_logs', 'ip_address')
    
    # System Admin Log - Convert IP to hash and encrypt states
    op.add_column('system_admin_logs',
                  sa.Column('ip_address_hash', sa.String(64), nullable=True,
                           comment='Hashed IP address for privacy protection'))
    
    # Copy and hash existing IP addresses
    op.execute("""
        UPDATE system_admin_logs 
        SET ip_address_hash = encode(sha256(ip_address::bytea), 'hex')
        WHERE ip_address IS NOT NULL
    """)
    
    # Drop old IP column
    op.drop_column('system_admin_logs', 'ip_address')
    
    # Note: before_state and after_state columns need manual encryption
    # as they contain JSON data that needs to be encrypted with the app key
    op.execute("""
        COMMENT ON COLUMN system_admin_logs.before_state IS 'State before the change (JSON format, encrypted)';
        COMMENT ON COLUMN system_admin_logs.after_state IS 'State after the change (JSON format, encrypted)';
    """)
    
    # Auth Events - Convert IP to hash
    op.add_column('auth_events',
                  sa.Column('ip_address_hash', sa.String(64), nullable=True, index=True,
                           comment='Hashed IP address for privacy protection'))
    
    # Copy and hash existing IP addresses
    op.execute("""
        UPDATE auth_events 
        SET ip_address_hash = encode(sha256(ip_address::bytea), 'hex')
        WHERE ip_address IS NOT NULL
    """)
    
    # Drop old IP column
    op.drop_column('auth_events', 'ip_address')
    
    # Create index on new hash columns
    op.create_index('idx_auth_events_ip_hash', 'auth_events', ['ip_address_hash'])


def downgrade():
    """Revert field-level encryption changes."""
    
    # OAuth Provider - Revert token columns
    op.alter_column('oauth_providers', 'access_token',
                    type_=sa.String(1000),
                    existing_type=sa.String(2000))
    
    op.alter_column('oauth_providers', 'refresh_token',
                    type_=sa.String(1000),
                    existing_type=sa.String(2000))
    
    # Supabase User - Revert phone column
    op.alter_column('supabase_users', 'phone',
                    type_=sa.String(50),
                    existing_type=sa.String(100))
    
    # Auth Session - Restore IP column
    op.add_column('auth_sessions',
                  sa.Column('ip_address', sa.String(45), nullable=True))
    op.drop_column('auth_sessions', 'ip_address_hash')
    
    # User Activity Log - Restore IP column
    op.add_column('user_activity_logs',
                  sa.Column('ip_address', sa.String(45), nullable=True))
    op.drop_column('user_activity_logs', 'ip_address_hash')
    
    # System Admin Log - Restore IP column
    op.add_column('system_admin_logs',
                  sa.Column('ip_address', sa.String(45), nullable=True))
    op.drop_column('system_admin_logs', 'ip_address_hash')
    
    # Auth Events - Restore IP column
    op.drop_index('idx_auth_events_ip_hash', 'auth_events')
    op.add_column('auth_events',
                  sa.Column('ip_address', sa.String(45), nullable=True, index=True))
    op.drop_column('auth_events', 'ip_address_hash')
    
    # Note: Encrypted data cannot be automatically restored without the encryption key