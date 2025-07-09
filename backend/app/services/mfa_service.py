"""
Multi-Factor Authentication (MFA) service implementation.
Supports TOTP (Time-based One-Time Password) authentication.
"""
import pyotp
import qrcode
import io
import base64
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.mfa import MFASettings, MFABackupCodes
from app.core.config import get_settings


class MFAService:
    """Service for managing multi-factor authentication."""
    
    def __init__(self, db: Session, settings = None):
        self.db = db
        self.settings = settings or get_settings()
        self.issuer_name = "Duolingo Clone"
    
    async def generate_totp_secret(self, user_id: str) -> Dict[str, str]:
        """Generate a new TOTP secret for user."""
        # Generate random secret
        secret = pyotp.random_base32()
        
        # Check if user already has MFA settings
        mfa_settings = self.db.query(MFASettings).filter(
            MFASettings.user_id == user_id
        ).first()
        
        if mfa_settings:
            # Update existing settings
            mfa_settings.totp_secret = secret
            mfa_settings.is_enabled = False  # Not enabled until verified
            mfa_settings.updated_at = datetime.utcnow()
        else:
            # Create new MFA settings
            mfa_settings = MFASettings(
                user_id=user_id,
                totp_secret=secret,
                is_enabled=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.db.add(mfa_settings)
        
        self.db.commit()
        
        return {
            "secret": secret,
            "qr_code": await self._generate_qr_code(user_id, secret)
        }
    
    async def _generate_qr_code(self, user_id: str, secret: str) -> str:
        """Generate QR code for TOTP setup."""
        # Get user email for the QR code
        from app.models.user import User
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Create TOTP URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=self.issuer_name
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Convert to base64 image
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    
    async def verify_totp_code(
        self, 
        user_id: str, 
        code: str,
        enable_on_success: bool = False
    ) -> bool:
        """Verify a TOTP code for user."""
        mfa_settings = self.db.query(MFASettings).filter(
            MFASettings.user_id == user_id
        ).first()
        
        if not mfa_settings or not mfa_settings.totp_secret:
            return False
        
        # Create TOTP instance
        totp = pyotp.TOTP(mfa_settings.totp_secret)
        
        # Verify with 1 window tolerance (30 seconds before/after)
        is_valid = totp.verify(code, valid_window=1)
        
        if is_valid and enable_on_success and not mfa_settings.is_enabled:
            # Enable MFA on first successful verification
            mfa_settings.is_enabled = True
            mfa_settings.enabled_at = datetime.utcnow()
            mfa_settings.last_used_at = datetime.utcnow()
            
            # Generate backup codes
            await self._generate_backup_codes(user_id)
            
            self.db.commit()
        elif is_valid and mfa_settings.is_enabled:
            # Update last used timestamp
            mfa_settings.last_used_at = datetime.utcnow()
            self.db.commit()
        
        return is_valid
    
    async def _generate_backup_codes(self, user_id: str) -> list[str]:
        """Generate backup codes for MFA recovery."""
        # Delete existing backup codes
        self.db.query(MFABackupCodes).filter(
            MFABackupCodes.user_id == user_id
        ).delete()
        
        # Generate 10 backup codes
        codes = []
        for _ in range(10):
            code = pyotp.random_base32()[:8]  # 8-character codes
            codes.append(code)
            
            backup_code = MFABackupCodes(
                user_id=user_id,
                code_hash=self._hash_backup_code(code),
                is_used=False,
                created_at=datetime.utcnow()
            )
            self.db.add(backup_code)
        
        self.db.commit()
        return codes
    
    def _hash_backup_code(self, code: str) -> str:
        """Hash backup code for storage."""
        import hashlib
        return hashlib.sha256(code.encode()).hexdigest()
    
    async def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify and consume a backup code."""
        code_hash = self._hash_backup_code(code)
        
        backup_code = self.db.query(MFABackupCodes).filter(
            MFABackupCodes.user_id == user_id,
            MFABackupCodes.code_hash == code_hash,
            MFABackupCodes.is_used == False
        ).first()
        
        if backup_code:
            # Mark as used
            backup_code.is_used = True
            backup_code.used_at = datetime.utcnow()
            self.db.commit()
            return True
        
        return False
    
    async def disable_mfa(self, user_id: str) -> bool:
        """Disable MFA for user."""
        mfa_settings = self.db.query(MFASettings).filter(
            MFASettings.user_id == user_id
        ).first()
        
        if mfa_settings:
            mfa_settings.is_enabled = False
            mfa_settings.totp_secret = None
            mfa_settings.disabled_at = datetime.utcnow()
            
            # Delete backup codes
            self.db.query(MFABackupCodes).filter(
                MFABackupCodes.user_id == user_id
            ).delete()
            
            self.db.commit()
            return True
        
        return False
    
    async def is_mfa_enabled(self, user_id: str) -> bool:
        """Check if MFA is enabled for user."""
        mfa_settings = self.db.query(MFASettings).filter(
            MFASettings.user_id == user_id,
            MFASettings.is_enabled == True
        ).first()
        
        return mfa_settings is not None
    
    async def get_mfa_status(self, user_id: str) -> Dict[str, Any]:
        """Get MFA status and settings for user."""
        mfa_settings = self.db.query(MFASettings).filter(
            MFASettings.user_id == user_id
        ).first()
        
        if not mfa_settings:
            return {
                "enabled": False,
                "method": None,
                "backup_codes_remaining": 0
            }
        
        # Count remaining backup codes
        backup_codes_remaining = self.db.query(MFABackupCodes).filter(
            MFABackupCodes.user_id == user_id,
            MFABackupCodes.is_used == False
        ).count()
        
        return {
            "enabled": mfa_settings.is_enabled,
            "method": "totp" if mfa_settings.totp_secret else None,
            "backup_codes_remaining": backup_codes_remaining,
            "last_used_at": mfa_settings.last_used_at,
            "enabled_at": mfa_settings.enabled_at
        }
    
    async def regenerate_backup_codes(self, user_id: str) -> Optional[list[str]]:
        """Regenerate backup codes for user."""
        mfa_settings = self.db.query(MFASettings).filter(
            MFASettings.user_id == user_id,
            MFASettings.is_enabled == True
        ).first()
        
        if not mfa_settings:
            return None
        
        return await self._generate_backup_codes(user_id)