"""
Unit Tests for Rate Limiter Service

Tests for Redis-based rate limiting with exponential backoff and brute force protection.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

from app.services.rate_limiter import (
    RateLimiter, 
    RateLimitResult, 
    RateLimitInfo, 
    RateLimitRule,
    get_rate_limiter,
    create_rate_limit_key
)


class TestRateLimitRule:
    """Test cases for RateLimitRule dataclass."""
    
    def test_rate_limit_rule_creation(self):
        """Test RateLimitRule creation with defaults."""
        rule = RateLimitRule(
            key_prefix="test",
            max_attempts=5,
            window_seconds=300
        )
        
        assert rule.key_prefix == "test"
        assert rule.max_attempts == 5
        assert rule.window_seconds == 300
        assert rule.lockout_seconds is None
        assert rule.exponential_backoff is False
        assert rule.backoff_multiplier == 2.0
        assert rule.max_backoff_seconds == 3600


class TestRateLimiter:
    """Test cases for RateLimiter class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis_mock = Mock()
        redis_mock.pipeline.return_value = redis_mock
        redis_mock.execute.return_value = [None, [], None]
        redis_mock.get.return_value = None  # No lockout by default
        redis_mock.delete.return_value = None
        redis_mock.setex.return_value = None
        redis_mock.zadd.return_value = None
        return redis_mock
    
    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """RateLimiter instance with mocked Redis."""
        return RateLimiter(redis_client=mock_redis)
    
    def test_init_rate_limiter(self, rate_limiter, mock_redis):
        """Test RateLimiter initialization."""
        assert rate_limiter.redis_client == mock_redis
        assert rate_limiter.settings is not None
        assert "login_attempts" in rate_limiter.RULES
    
    def test_predefined_rules(self, rate_limiter):
        """Test predefined rate limit rules."""
        rules = rate_limiter.RULES
        
        # Test login attempts rule
        login_rule = rules["login_attempts"]
        assert login_rule.max_attempts == 5
        assert login_rule.window_seconds == 900
        assert login_rule.lockout_seconds == 1800
        assert login_rule.exponential_backoff is True
        
        # Test password reset rule
        reset_rule = rules["password_reset"]
        assert reset_rule.max_attempts == 3
        assert reset_rule.window_seconds == 3600
        assert reset_rule.exponential_backoff is True
    
    def test_check_rate_limit_allowed(self, rate_limiter, mock_redis):
        """Test rate limit check when allowed."""
        # Mock no existing attempts
        mock_redis.execute.return_value = [None, [], None]
        
        result = rate_limiter.check_rate_limit("test_user", "login_attempts")
        
        assert result.result == RateLimitResult.ALLOWED
        assert result.remaining == 5
        assert result.total_attempts == 0
        assert result.lockout_expires is None
    
    def test_check_rate_limit_rate_limited(self, rate_limiter, mock_redis):
        """Test rate limit check when rate limited."""
        # Mock 5 recent attempts (at limit)
        now = time.time()
        attempts = [str(now - i * 60) for i in range(5)]  # 5 attempts in last 5 minutes
        mock_redis.execute.return_value = [None, attempts, None]
        
        result = rate_limiter.check_rate_limit("test_user", "login_attempts")
        
        assert result.result == RateLimitResult.RATE_LIMITED
        assert result.remaining == 0
        assert result.total_attempts == 5
        assert result.retry_after is not None
    
    def test_check_rate_limit_with_lockout(self, rate_limiter, mock_redis):
        """Test rate limit check when locked out."""
        # Mock active lockout
        lockout_data = {
            "attempts": 7,
            "expires": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
            "duration": 1800
        }
        mock_redis.get.return_value = json.dumps(lockout_data)
        
        result = rate_limiter.check_rate_limit("test_user", "login_attempts")
        
        assert result.result == RateLimitResult.BLOCKED
        assert result.remaining == 0
        assert result.total_attempts == 7
        assert result.lockout_expires is not None
        assert result.retry_after is not None
    
    def test_check_rate_limit_expired_lockout(self, rate_limiter, mock_redis):
        """Test rate limit check with expired lockout."""
        # Mock expired lockout
        lockout_data = {
            "attempts": 5,
            "expires": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
            "duration": 1800
        }
        mock_redis.get.return_value = json.dumps(lockout_data)
        mock_redis.execute.return_value = [None, [], None]
        
        result = rate_limiter.check_rate_limit("test_user", "login_attempts")
        
        assert result.result == RateLimitResult.ALLOWED
        # Verify lockout was cleared
        mock_redis.delete.assert_called()
    
    def test_check_rate_limit_unknown_rule(self, rate_limiter):
        """Test rate limit check with unknown rule."""
        with pytest.raises(ValueError, match="Unknown rate limit rule"):
            rate_limiter.check_rate_limit("test_user", "unknown_rule")
    
    def test_check_rate_limit_custom_rule(self, rate_limiter, mock_redis):
        """Test rate limit check with custom rule."""
        custom_rule = RateLimitRule(
            key_prefix="custom",
            max_attempts=3,
            window_seconds=600
        )
        mock_redis.execute.return_value = [None, [], None]
        
        result = rate_limiter.check_rate_limit(
            "test_user", 
            "unused", 
            custom_rule=custom_rule
        )
        
        assert result.result == RateLimitResult.ALLOWED
        assert result.remaining == 3
    
    def test_record_attempt_success(self, rate_limiter, mock_redis):
        """Test recording successful attempt."""
        result = rate_limiter.record_attempt("test_user", "login_attempts", success=True)
        
        assert result.result == RateLimitResult.ALLOWED
        assert result.remaining == 5
        # Verify attempts were cleared
        mock_redis.delete.assert_called()
    
    def test_record_attempt_failure(self, rate_limiter, mock_redis):
        """Test recording failed attempt."""
        # Mock current attempts
        mock_redis.execute.return_value = [None, ["123456789.0"], None]
        
        result = rate_limiter.record_attempt("test_user", "login_attempts", success=False)
        
        assert result.total_attempts == 1
        assert result.remaining == 4
        # Verify attempt was added
        mock_redis.zadd.assert_called()
    
    def test_record_attempt_triggers_lockout(self, rate_limiter, mock_redis):
        """Test recording attempt that triggers lockout."""
        # Mock 5 existing attempts (at threshold)
        now = time.time()
        attempts = [str(now - i * 60) for i in range(5)]
        mock_redis.execute.return_value = [None, attempts, None]
        mock_redis.get.return_value = "0"  # No previous backoff
        
        result = rate_limiter.record_attempt("test_user", "login_attempts", success=False)
        
        assert result.result == RateLimitResult.BLOCKED
        assert result.lockout_expires is not None
        assert result.retry_after is not None
        # Verify lockout was set
        mock_redis.setex.assert_called()
    
    def test_record_attempt_exponential_backoff(self, rate_limiter, mock_redis):
        """Test exponential backoff calculation."""
        # Mock existing attempts and previous backoff
        now = time.time()
        attempts = [str(now - i * 60) for i in range(5)]
        mock_redis.execute.return_value = [None, attempts, None]
        mock_redis.get.return_value = "2"  # 2 previous backoffs
        
        result = rate_limiter.record_attempt("test_user", "login_attempts", success=False)
        
        assert result.result == RateLimitResult.BLOCKED
        # Verify exponential backoff was applied (base 1800 * 2^2 = 7200, capped at 3600)
        call_args = mock_redis.setex.call_args
        lockout_duration = call_args[0][1]
        assert lockout_duration == 3600  # Capped at 1 hour (max_backoff_seconds)
    
    def test_get_lockout_info_active(self, rate_limiter, mock_redis):
        """Test getting active lockout info."""
        lockout_data = {
            "attempts": 5,
            "expires": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
            "duration": 1800
        }
        mock_redis.get.return_value = json.dumps(lockout_data)
        
        info = rate_limiter.get_lockout_info("test_user", "login_attempts")
        
        assert info is not None
        assert info["attempts"] == 5
        assert info["duration"] == 1800
    
    def test_get_lockout_info_none(self, rate_limiter, mock_redis):
        """Test getting lockout info when none exists."""
        mock_redis.get.return_value = None
        
        info = rate_limiter.get_lockout_info("test_user", "login_attempts")
        
        assert info is None
    
    def test_clear_rate_limits(self, rate_limiter, mock_redis):
        """Test clearing rate limits."""
        result = rate_limiter.clear_rate_limits("test_user", "login_attempts")
        
        assert result is True
        # Verify both attempts and lockout were cleared
        assert mock_redis.delete.call_count == 2
    
    def test_clear_rate_limits_unknown_rule(self, rate_limiter):
        """Test clearing rate limits with unknown rule."""
        result = rate_limiter.clear_rate_limits("test_user", "unknown_rule")
        
        assert result is False
    
    def test_redis_error_handling(self, rate_limiter, mock_redis):
        """Test handling Redis errors gracefully."""
        from redis.exceptions import RedisError
        mock_redis.execute.side_effect = RedisError("Connection failed")
        mock_redis.get.side_effect = RedisError("Connection failed")
        
        # Should fail open and allow the request
        result = rate_limiter.check_rate_limit("test_user", "login_attempts")
        
        assert result.result == RateLimitResult.ALLOWED
        assert result.remaining == 999  # Fail-open indicator


class TestRateLimiterIntegration:
    """Integration tests for rate limiter functionality."""
    
    @pytest.fixture
    def rate_limiter_with_real_redis(self):
        """Rate limiter with real Redis (for integration tests)."""
        # This would require actual Redis instance for integration testing
        pass
    
    def test_complete_rate_limiting_flow(self):
        """Test complete flow from allowed to rate limited to locked out."""
        # This would test the full flow with actual Redis
        pass
    
    def test_concurrent_rate_limiting(self):
        """Test rate limiting under concurrent access."""
        # This would test thread safety and race conditions
        pass


def test_get_rate_limiter():
    """Test get_rate_limiter factory function."""
    limiter = get_rate_limiter()
    
    assert isinstance(limiter, RateLimiter)
    # Should return same instance on subsequent calls
    assert get_rate_limiter() is limiter


def test_create_rate_limit_key():
    """Test rate limit key creation."""
    key = create_rate_limit_key("login", "user123")
    assert key == "login:user123"
    
    key_with_context = create_rate_limit_key("login", "192.168.1.1", "failed")
    assert key_with_context == "login:192.168.1.1:failed"
    
    key_no_context = create_rate_limit_key("register", "test@example.com", None)
    assert key_no_context == "register:test@example.com"


class TestRateLimitInfo:
    """Test cases for RateLimitInfo dataclass."""
    
    def test_rate_limit_info_creation(self):
        """Test RateLimitInfo creation."""
        now = datetime.now(timezone.utc)
        info = RateLimitInfo(
            result=RateLimitResult.ALLOWED,
            remaining=5,
            reset_time=now,
            total_attempts=2
        )
        
        assert info.result == RateLimitResult.ALLOWED
        assert info.remaining == 5
        assert info.reset_time == now
        assert info.retry_after is None
        assert info.total_attempts == 2
        assert info.lockout_expires is None


class TestRateLimiterErrorHandling:
    """Test error handling in rate limiter."""
    
    @pytest.fixture
    def mock_redis_with_errors(self):
        """Mock Redis client that raises errors."""
        redis_mock = Mock()
        redis_mock.pipeline.return_value = redis_mock
        return redis_mock
    
    def test_redis_connection_failure(self):
        """Test handling Redis connection failure during initialization."""
        with patch('app.services.rate_limiter.redis.from_url') as mock_from_url:
            mock_from_url.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception):
                RateLimiter()
    
    def test_json_decode_error_in_lockout(self, mock_redis_with_errors):
        """Test handling JSON decode error in lockout check."""
        rate_limiter = RateLimiter(redis_client=mock_redis_with_errors)
        mock_redis_with_errors.get.return_value = "invalid json"
        
        info = rate_limiter.get_lockout_info("test_user", "login_attempts")
        
        assert info is None
    
    def test_missing_rule_data(self, mock_redis_with_errors):
        """Test handling missing rule data."""
        rate_limiter = RateLimiter(redis_client=mock_redis_with_errors)
        
        with pytest.raises(ValueError):
            rate_limiter.check_rate_limit("test_user", "nonexistent_rule")