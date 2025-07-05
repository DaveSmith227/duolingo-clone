"""
Rate Limiting Service

Redis-based rate limiting with exponential backoff for authentication endpoints.
Implements sliding window rate limiting and brute force protection.
"""

import logging
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

import redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RateLimitResult(Enum):
    """Rate limit check results."""
    ALLOWED = "allowed"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"


@dataclass
class RateLimitInfo:
    """Rate limit information."""
    result: RateLimitResult
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None
    total_attempts: int = 0
    lockout_expires: Optional[datetime] = None


@dataclass
class RateLimitRule:
    """Rate limit rule configuration."""
    key_prefix: str
    max_attempts: int
    window_seconds: int
    lockout_seconds: Optional[int] = None
    exponential_backoff: bool = False
    backoff_multiplier: float = 2.0
    max_backoff_seconds: int = 3600  # 1 hour


class RateLimiter:
    """
    Redis-based rate limiter with exponential backoff.
    
    Implements sliding window rate limiting with support for:
    - Failed login attempt tracking
    - Exponential backoff for repeated failures
    - Account lockout protection
    - IP-based and user-based limits
    """
    
    # Predefined rate limit rules
    RULES = {
        "login_attempts": RateLimitRule(
            key_prefix="rate_limit:login",
            max_attempts=5,
            window_seconds=900,  # 15 minutes
            lockout_seconds=1800,  # 30 minutes lockout
            exponential_backoff=True,
            backoff_multiplier=2.0,
            max_backoff_seconds=3600  # 1 hour max
        ),
        "password_reset": RateLimitRule(
            key_prefix="rate_limit:password_reset",
            max_attempts=3,
            window_seconds=3600,  # 1 hour
            lockout_seconds=7200,  # 2 hours lockout
            exponential_backoff=True
        ),
        "registration": RateLimitRule(
            key_prefix="rate_limit:registration",
            max_attempts=3,
            window_seconds=3600,  # 1 hour
            exponential_backoff=False
        ),
        "token_refresh": RateLimitRule(
            key_prefix="rate_limit:token_refresh",
            max_attempts=10,
            window_seconds=300,  # 5 minutes
            exponential_backoff=False
        ),
        "general_auth": RateLimitRule(
            key_prefix="rate_limit:auth",
            max_attempts=20,
            window_seconds=300,  # 5 minutes
            exponential_backoff=False
        )
    }
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.settings = get_settings()
        self.redis_client = redis_client or self._create_redis_client()
        
    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client from configuration."""
        try:
            return redis.from_url(
                self.settings.redis_dsn,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        except Exception as e:
            logger.error(f"Failed to create Redis client: {str(e)}")
            raise
    
    def check_rate_limit(
        self,
        identifier: str,
        rule_name: str,
        custom_rule: Optional[RateLimitRule] = None
    ) -> RateLimitInfo:
        """
        Check if identifier is within rate limits.
        
        Args:
            identifier: Unique identifier (IP, user ID, email, etc.)
            rule_name: Name of the rate limit rule to apply
            custom_rule: Custom rule to use instead of predefined
            
        Returns:
            RateLimitInfo with current status and limits
        """
        try:
            rule = custom_rule or self.RULES.get(rule_name)
            if not rule:
                raise ValueError(f"Unknown rate limit rule: {rule_name}")
            
            now = datetime.now(timezone.utc)
            key = f"{rule.key_prefix}:{identifier}"
            lockout_key = f"{key}:lockout"
            
            # Check if currently locked out
            lockout_info = self._check_lockout(lockout_key)
            if lockout_info:
                return RateLimitInfo(
                    result=RateLimitResult.BLOCKED,
                    remaining=0,
                    reset_time=lockout_info["expires"],
                    retry_after=int((lockout_info["expires"] - now).total_seconds()),
                    total_attempts=lockout_info["attempts"],
                    lockout_expires=lockout_info["expires"]
                )
            
            # Get current attempt count
            attempts = self._get_attempts(key, rule.window_seconds)
            remaining = max(0, rule.max_attempts - len(attempts))
            
            # Calculate reset time
            if attempts:
                oldest_attempt = min(attempts)
                reset_time = datetime.fromtimestamp(oldest_attempt, timezone.utc) + timedelta(seconds=rule.window_seconds)
            else:
                reset_time = now + timedelta(seconds=rule.window_seconds)
            
            if len(attempts) >= rule.max_attempts:
                return RateLimitInfo(
                    result=RateLimitResult.RATE_LIMITED,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after=int((reset_time - now).total_seconds()),
                    total_attempts=len(attempts)
                )
            
            return RateLimitInfo(
                result=RateLimitResult.ALLOWED,
                remaining=remaining,
                reset_time=reset_time,
                total_attempts=len(attempts)
            )
            
        except RedisError as e:
            logger.error(f"Redis error in rate limiting: {str(e)}")
            # Fail open - allow request if Redis is unavailable
            return RateLimitInfo(
                result=RateLimitResult.ALLOWED,
                remaining=999,
                reset_time=now + timedelta(hours=1)
            )
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            raise
    
    def record_attempt(
        self,
        identifier: str,
        rule_name: str,
        success: bool = False,
        custom_rule: Optional[RateLimitRule] = None
    ) -> RateLimitInfo:
        """
        Record an attempt and update rate limits.
        
        Args:
            identifier: Unique identifier
            rule_name: Name of the rate limit rule
            success: Whether the attempt was successful
            custom_rule: Custom rule to use instead of predefined
            
        Returns:
            Updated RateLimitInfo
        """
        try:
            rule = custom_rule or self.RULES.get(rule_name)
            if not rule:
                raise ValueError(f"Unknown rate limit rule: {rule_name}")
            
            now = datetime.now(timezone.utc)
            timestamp = now.timestamp()
            key = f"{rule.key_prefix}:{identifier}"
            lockout_key = f"{key}:lockout"
            
            if success:
                # Clear attempts on successful authentication
                self._clear_attempts(key)
                self._clear_lockout(lockout_key)
                return RateLimitInfo(
                    result=RateLimitResult.ALLOWED,
                    remaining=rule.max_attempts,
                    reset_time=now + timedelta(seconds=rule.window_seconds)
                )
            
            # Record failed attempt
            self._add_attempt(key, timestamp, rule.window_seconds)
            
            # Get updated attempt count
            attempts = self._get_attempts(key, rule.window_seconds)
            total_attempts = len(attempts)
            
            # Check if lockout threshold exceeded
            if total_attempts >= rule.max_attempts and rule.lockout_seconds:
                lockout_duration = self._calculate_lockout_duration(
                    identifier, rule, total_attempts
                )
                lockout_expires = now + timedelta(seconds=lockout_duration)
                
                # Set lockout
                self._set_lockout(lockout_key, {
                    "attempts": total_attempts,
                    "expires": lockout_expires,
                    "duration": lockout_duration
                })
                
                logger.warning(
                    f"Rate limit lockout for {identifier}: {total_attempts} attempts, "
                    f"locked until {lockout_expires}"
                )
                
                return RateLimitInfo(
                    result=RateLimitResult.BLOCKED,
                    remaining=0,
                    reset_time=lockout_expires,
                    retry_after=lockout_duration,
                    total_attempts=total_attempts,
                    lockout_expires=lockout_expires
                )
            
            # Calculate remaining attempts and reset time
            remaining = max(0, rule.max_attempts - total_attempts)
            reset_time = datetime.fromtimestamp(min(attempts), timezone.utc) + timedelta(seconds=rule.window_seconds)
            
            result = RateLimitResult.RATE_LIMITED if remaining == 0 else RateLimitResult.ALLOWED
            retry_after = int((reset_time - now).total_seconds()) if result == RateLimitResult.RATE_LIMITED else None
            
            return RateLimitInfo(
                result=result,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=retry_after,
                total_attempts=total_attempts
            )
            
        except RedisError as e:
            logger.error(f"Redis error recording attempt: {str(e)}")
            # Fail open
            return RateLimitInfo(
                result=RateLimitResult.ALLOWED,
                remaining=999,
                reset_time=now + timedelta(hours=1)
            )
        except Exception as e:
            logger.error(f"Failed to record attempt: {str(e)}")
            raise
    
    def get_lockout_info(self, identifier: str, rule_name: str) -> Optional[Dict[str, Any]]:
        """
        Get current lockout information for identifier.
        
        Args:
            identifier: Unique identifier
            rule_name: Name of the rate limit rule
            
        Returns:
            Lockout information or None if not locked out
        """
        try:
            rule = self.RULES.get(rule_name)
            if not rule:
                return None
            
            key = f"{rule.key_prefix}:{identifier}"
            lockout_key = f"{key}:lockout"
            
            return self._check_lockout(lockout_key)
            
        except Exception as e:
            logger.error(f"Failed to get lockout info: {str(e)}")
            return None
    
    def clear_rate_limits(self, identifier: str, rule_name: str) -> bool:
        """
        Clear all rate limits for identifier.
        
        Args:
            identifier: Unique identifier
            rule_name: Name of the rate limit rule
            
        Returns:
            True if cleared successfully
        """
        try:
            rule = self.RULES.get(rule_name)
            if not rule:
                return False
            
            key = f"{rule.key_prefix}:{identifier}"
            lockout_key = f"{key}:lockout"
            
            self._clear_attempts(key)
            self._clear_lockout(lockout_key)
            
            logger.info(f"Cleared rate limits for {identifier} (rule: {rule_name})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear rate limits: {str(e)}")
            return False
    
    def _get_attempts(self, key: str, window_seconds: int) -> List[float]:
        """Get attempt timestamps within the window."""
        try:
            cutoff = time.time() - window_seconds
            
            # Remove old attempts and get current ones
            pipeline = self.redis_client.pipeline()
            pipeline.zremrangebyscore(key, 0, cutoff)
            pipeline.zrange(key, 0, -1)
            pipeline.expire(key, window_seconds)
            
            results = pipeline.execute()
            return [float(timestamp) for timestamp in results[1]]
            
        except RedisError:
            return []
    
    def _add_attempt(self, key: str, timestamp: float, window_seconds: int):
        """Add new attempt timestamp."""
        try:
            pipeline = self.redis_client.pipeline()
            pipeline.zadd(key, {str(timestamp): timestamp})
            pipeline.expire(key, window_seconds)
            pipeline.execute()
            
        except RedisError as e:
            logger.error(f"Failed to add attempt: {str(e)}")
    
    def _clear_attempts(self, key: str):
        """Clear all attempts for key."""
        try:
            self.redis_client.delete(key)
        except RedisError as e:
            logger.error(f"Failed to clear attempts: {str(e)}")
    
    def _check_lockout(self, lockout_key: str) -> Optional[Dict[str, Any]]:
        """Check if identifier is locked out."""
        try:
            lockout_data = self.redis_client.get(lockout_key)
            if not lockout_data:
                return None
            
            data = json.loads(lockout_data)
            expires = datetime.fromisoformat(data["expires"])
            
            # Check if lockout has expired
            if expires <= datetime.now(timezone.utc):
                self._clear_lockout(lockout_key)
                return None
            
            return {
                "attempts": data["attempts"],
                "expires": expires,
                "duration": data["duration"]
            }
            
        except RedisError:
            # Re-raise Redis errors to be handled at higher level
            raise
        except (json.JSONDecodeError, KeyError):
            return None
    
    def _set_lockout(self, lockout_key: str, lockout_data: Dict[str, Any]):
        """Set lockout for identifier."""
        try:
            data = {
                "attempts": lockout_data["attempts"],
                "expires": lockout_data["expires"].isoformat(),
                "duration": lockout_data["duration"]
            }
            
            self.redis_client.setex(
                lockout_key,
                lockout_data["duration"],
                json.dumps(data)
            )
            
        except RedisError as e:
            logger.error(f"Failed to set lockout: {str(e)}")
    
    def _clear_lockout(self, lockout_key: str):
        """Clear lockout for identifier."""
        try:
            self.redis_client.delete(lockout_key)
        except RedisError as e:
            logger.error(f"Failed to clear lockout: {str(e)}")
    
    def _calculate_lockout_duration(
        self,
        identifier: str,
        rule: RateLimitRule,
        current_attempts: int
    ) -> int:
        """Calculate lockout duration with exponential backoff."""
        if not rule.exponential_backoff:
            return rule.lockout_seconds or 0
        
        # Get previous lockout count for exponential backoff
        try:
            backoff_key = f"{rule.key_prefix}:{identifier}:backoff_count"
            backoff_count = int(self.redis_client.get(backoff_key) or 0)
            
            # Increment backoff count
            self.redis_client.setex(backoff_key, 86400, backoff_count + 1)  # 24h expiry
            
            # Calculate exponential backoff
            base_duration = rule.lockout_seconds or 0
            backoff_multiplier = rule.backoff_multiplier ** backoff_count
            duration = int(base_duration * backoff_multiplier)
            
            # Cap at maximum backoff
            return min(duration, rule.max_backoff_seconds)
            
        except RedisError:
            # Fallback to base duration
            return rule.lockout_seconds or 0


# Global rate limiter instance
rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get rate limiter instance.
    
    Returns:
        Global RateLimiter instance
    """
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = RateLimiter()
    return rate_limiter


def create_rate_limit_key(
    request_type: str,
    identifier: str,
    additional_context: Optional[str] = None
) -> str:
    """
    Create standardized rate limit key.
    
    Args:
        request_type: Type of request (login, register, etc.)
        identifier: Primary identifier (IP, user_id, email)
        additional_context: Additional context for the key
        
    Returns:
        Formatted rate limit key
    """
    key_parts = [request_type, identifier]
    if additional_context:
        key_parts.append(additional_context)
    
    return ":".join(key_parts)