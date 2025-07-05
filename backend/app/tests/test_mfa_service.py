"""
Tests for MFA service.
"""
import pytest
import pyotp
import qrcode
from unittest.mock import Mock, patch
from datetime import datetime
from app.services.mfa_service import MFAService
from app.models.mfa import UserMFA, MFABackupCode


@pytest.fixture
def db_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mfa_service(db_session):
    """Create MFA service instance."""
    return MFAService(db_session)


class TestMFAService:
    """Test MFA service functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_totp_secret(self, mfa_service, db_session):
        """Test TOTP secret generation."""
        user_id = "user123"
        
        # Mock database query
        db_session.query().filter().first.return_value = None
        
        # Generate secret
        result = await mfa_service.generate_totp_secret(user_id)
        
        # Verify result structure
        assert 'secret' in result
        assert 'qr_code' in result
        assert 'backup_codes' in result
        
        # Verify secret format
        assert len(result['secret']) == 32
        assert result['secret'].isalnum()
        
        # Verify QR code is base64
        assert result['qr_code'].startswith('data:image/png;base64,')
        
        # Verify backup codes
        assert len(result['backup_codes']) == 10
        for code in result['backup_codes']:
            assert len(code) == 8
            assert code.isalnum()
        
        # Verify database operations
        assert db_session.add.called
        assert db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_generate_totp_secret_existing_user(self, mfa_service, db_session):
        """Test TOTP secret generation for user with existing MFA."""
        user_id = "user123"
        
        # Mock existing MFA record
        existing_mfa = Mock(is_enabled=False)
        db_session.query().filter().first.return_value = existing_mfa
        
        # Generate new secret
        result = await mfa_service.generate_totp_secret(user_id)
        
        # Verify existing record was updated
        assert existing_mfa.secret_key is not None
        assert db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_verify_totp_code_valid(self, mfa_service, db_session):
        """Test TOTP code verification with valid code."""
        user_id = "user123"
        secret = pyotp.random_base32()
        
        # Generate valid code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Mock MFA record
        mfa_record = Mock(
            secret_key=secret,
            is_enabled=True,
            last_used_code=None
        )
        db_session.query().filter().first.return_value = mfa_record
        
        # Verify code
        result = await mfa_service.verify_totp_code(user_id, valid_code)
        
        assert result is True
        assert mfa_record.last_used_code == valid_code
        assert mfa_record.last_used_at is not None
        assert db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_verify_totp_code_invalid(self, mfa_service, db_session):
        """Test TOTP code verification with invalid code."""
        user_id = "user123"
        secret = pyotp.random_base32()
        
        # Mock MFA record
        mfa_record = Mock(
            secret_key=secret,
            is_enabled=True,
            last_used_code=None
        )
        db_session.query().filter().first.return_value = mfa_record
        
        # Verify invalid code
        result = await mfa_service.verify_totp_code(user_id, "123456")
        
        assert result is False
        assert mfa_record.last_used_code is None
        assert not db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_verify_totp_code_reuse_prevention(self, mfa_service, db_session):
        """Test TOTP code reuse prevention."""
        user_id = "user123"
        secret = pyotp.random_base32()
        
        # Generate valid code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Mock MFA record with same code already used
        mfa_record = Mock(
            secret_key=secret,
            is_enabled=True,
            last_used_code=valid_code
        )
        db_session.query().filter().first.return_value = mfa_record
        
        # Try to reuse code
        result = await mfa_service.verify_totp_code(user_id, valid_code)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_totp_code_disabled_mfa(self, mfa_service, db_session):
        """Test TOTP verification when MFA is disabled."""
        user_id = "user123"
        
        # Mock disabled MFA record
        mfa_record = Mock(is_enabled=False)
        db_session.query().filter().first.return_value = mfa_record
        
        # Try to verify code
        result = await mfa_service.verify_totp_code(user_id, "123456")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_totp_code_no_mfa(self, mfa_service, db_session):
        """Test TOTP verification when no MFA record exists."""
        user_id = "user123"
        
        # No MFA record
        db_session.query().filter().first.return_value = None
        
        # Try to verify code
        result = await mfa_service.verify_totp_code(user_id, "123456")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_backup_code_valid(self, mfa_service, db_session):
        """Test backup code verification with valid code."""
        user_id = "user123"
        backup_code = "ABCD1234"
        
        # Mock unused backup code
        code_record = Mock(
            user_id=user_id,
            code_hash=MFAService._hash_code(backup_code),
            is_used=False
        )
        
        # Mock query
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = code_record
        db_session.query.return_value = query_mock
        
        # Verify code
        result = await mfa_service.verify_backup_code(user_id, backup_code)
        
        assert result is True
        assert code_record.is_used is True
        assert code_record.used_at is not None
        assert db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_verify_backup_code_already_used(self, mfa_service, db_session):
        """Test backup code verification with already used code."""
        user_id = "user123"
        backup_code = "ABCD1234"
        
        # Mock used backup code
        code_record = Mock(
            user_id=user_id,
            code_hash=MFAService._hash_code(backup_code),
            is_used=True,
            used_at=datetime.utcnow()
        )
        
        # Mock query
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = code_record
        db_session.query.return_value = query_mock
        
        # Try to reuse code
        result = await mfa_service.verify_backup_code(user_id, backup_code)
        
        assert result is False
        assert not db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_verify_backup_code_invalid(self, mfa_service, db_session):
        """Test backup code verification with invalid code."""
        user_id = "user123"
        
        # Mock query returning no match
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None
        db_session.query.return_value = query_mock
        
        # Verify invalid code
        result = await mfa_service.verify_backup_code(user_id, "INVALID1")
        
        assert result is False
        assert not db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_enable_mfa(self, mfa_service, db_session):
        """Test enabling MFA for user."""
        user_id = "user123"
        
        # Mock MFA record
        mfa_record = Mock(is_enabled=False)
        db_session.query().filter().first.return_value = mfa_record
        
        # Enable MFA
        result = await mfa_service.enable_mfa(user_id)
        
        assert result is True
        assert mfa_record.is_enabled is True
        assert mfa_record.enabled_at is not None
        assert db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_disable_mfa(self, mfa_service, db_session):
        """Test disabling MFA for user."""
        user_id = "user123"
        
        # Mock MFA record
        mfa_record = Mock(is_enabled=True)
        db_session.query().filter().first.return_value = mfa_record
        
        # Mock backup codes query
        db_session.query().filter().delete.return_value = 5
        
        # Disable MFA
        result = await mfa_service.disable_mfa(user_id)
        
        assert result is True
        assert mfa_record.is_enabled is False
        assert mfa_record.secret_key is None
        assert db_session.commit.called
    
    def test_generate_backup_codes(self, mfa_service):
        """Test backup code generation."""
        codes = mfa_service._generate_backup_codes()
        
        assert len(codes) == 10
        
        # Check format
        for code in codes:
            assert len(code) == 8
            assert code.isalnum()
            assert code.isupper()
        
        # Check uniqueness
        assert len(set(codes)) == 10
    
    def test_hash_code(self):
        """Test code hashing."""
        code = "ABCD1234"
        
        hash1 = MFAService._hash_code(code)
        hash2 = MFAService._hash_code(code)
        
        # Same input produces same hash
        assert hash1 == hash2
        
        # Hash characteristics
        assert len(hash1) == 64  # SHA-256 hex digest
        assert hash1 \!= code
        
        # Different input produces different hash
        hash3 = MFAService._hash_code("DIFFERENT")
        assert hash3 \!= hash1
EOF < /dev/null