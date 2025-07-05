"""
Password Security Service

Comprehensive password security with proper hashing, validation, and policy enforcement.
"""

import logging
import re
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass
from passlib.context import CryptContext
from passlib.hash import argon2
from passlib.pwd import genword

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class PasswordStrength(Enum):
    """Password strength levels."""
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class PasswordViolationType(Enum):
    """Password policy violation types."""
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    NO_UPPERCASE = "no_uppercase"
    NO_LOWERCASE = "no_lowercase"
    NO_DIGITS = "no_digits"
    NO_SPECIAL_CHARS = "no_special_chars"
    CONTAINS_PERSONAL_INFO = "contains_personal_info"
    COMMON_PASSWORD = "common_password"
    DICTIONARY_WORD = "dictionary_word"
    SEQUENTIAL_CHARS = "sequential_chars"
    REPEATED_CHARS = "repeated_chars"
    PREVIOUSLY_USED = "previously_used"


@dataclass
class PasswordPolicy:
    """Password policy configuration."""
    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special_chars: bool = True
    min_special_chars: int = 1
    min_digits: int = 1
    min_uppercase: int = 1
    min_lowercase: int = 1
    prevent_common_passwords: bool = True
    prevent_dictionary_words: bool = True
    prevent_sequential_chars: bool = True
    prevent_repeated_chars: bool = True
    max_repeated_chars: int = 3
    prevent_personal_info: bool = True
    password_history_count: int = 5
    password_expiry_days: Optional[int] = None
    special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"


@dataclass
class PasswordValidationResult:
    """Password validation result."""
    is_valid: bool
    strength: PasswordStrength
    score: int  # 0-100
    violations: List[PasswordViolationType]
    suggestions: List[str]
    entropy: float


@dataclass
class PasswordHashResult:
    """Password hashing result."""
    hash: str
    algorithm: str
    cost_factor: int
    salt_length: int
    created_at: datetime


class PasswordSecurity:
    """
    Comprehensive password security service.
    
    Handles password hashing, validation, policy enforcement, and security features.
    """
    
    # Common passwords list (top 1000 most common passwords)
    COMMON_PASSWORDS = {
        "password", "123456", "123456789", "12345", "qwerty", "abc123", "password123",
        "admin", "letmein", "welcome", "monkey", "dragon", "master", "shadow", "qwerty123",
        "111111", "000000", "123123", "1234567890", "superman", "batman", "trustno1",
        "login", "guest", "hello", "sunshine", "princess", "football", "baseball",
        "basketball", "soccer", "computer", "internet", "cookie", "chocolate", "coffee"
    }
    
    # Dictionary words (basic English words)
    DICTIONARY_WORDS = {
        "about", "above", "abuse", "actor", "acute", "admit", "adopt", "adult", "after",
        "again", "agent", "agree", "ahead", "alarm", "album", "alert", "alien", "align",
        "alike", "alive", "allow", "alone", "along", "alter", "among", "anger", "angle",
        "angry", "apart", "apple", "apply", "arena", "argue", "arise", "array", "arrow",
        "apart", "asset", "avoid", "award", "aware", "badly", "baker", "basic", "beach",
        "begin", "being", "below", "bench", "billy", "birth", "black", "blame", "blank",
        "blind", "block", "blood", "bloom", "blown", "blues", "blunt", "blush", "board",
        "boost", "booth", "bound", "brain", "brand", "brass", "brave", "bread", "break",
        "breed", "brick", "bride", "brief", "bring", "broad", "broke", "brown", "brush",
        "build", "built", "bunch", "burst", "buyer", "cable", "cache", "candy", "carry",
        "catch", "cause", "chain", "chair", "chaos", "charm", "chart", "chase", "cheap",
        "check", "chest", "chief", "child", "china", "chose", "chunk", "civic", "civil",
        "claim", "class", "clean", "clear", "click", "climb", "clock", "close", "cloud",
        "coach", "coast", "could", "count", "court", "cover", "craft", "crash", "crazy",
        "cream", "crime", "crisp", "cross", "crowd", "crown", "crude", "curve", "cycle",
        "daily", "dairy", "dance", "dated", "dealt", "death", "debut", "delay", "depth",
        "doing", "doubt", "dozen", "draft", "drama", "drank", "dream", "dress", "drill",
        "drink", "drive", "drove", "dying", "eager", "early", "earth", "eight", "elite",
        "empty", "enemy", "enjoy", "enter", "entry", "equal", "error", "event", "every",
        "exact", "exist", "extra", "faith", "false", "fault", "fiber", "field", "fifth",
        "fifty", "fight", "final", "first", "fixed", "flash", "fleet", "floor", "fluid",
        "focus", "force", "forth", "forty", "forum", "found", "frame", "frank", "fraud",
        "fresh", "front", "fruit", "fully", "funny", "giant", "given", "glass", "globe",
        "glory", "goods", "grace", "grade", "grain", "grand", "grant", "grass", "grave",
        "great", "green", "gross", "group", "grown", "guard", "guess", "guest", "guide",
        "happy", "harsh", "haste", "heart", "heavy", "hence", "horse", "hotel", "house",
        "human", "hurry", "image", "imply", "index", "inner", "input", "irony", "issue",
        "japan", "jimmy", "joint", "jones", "judge", "knife", "known", "label", "large",
        "laser", "later", "laugh", "layer", "learn", "lease", "least", "leave", "legal",
        "level", "lewis", "light", "limit", "links", "lives", "local", "loose", "lower",
        "lucky", "lunch", "lying", "magic", "major", "maker", "march", "maria", "match",
        "maybe", "mayor", "meant", "media", "metal", "might", "minor", "minus", "mixed",
        "model", "money", "month", "moral", "motor", "mount", "mouse", "mouth", "moved",
        "movie", "music", "needs", "never", "newly", "night", "noise", "north", "noted",
        "novel", "nurse", "occur", "ocean", "offer", "often", "order", "other", "ought",
        "outer", "owner", "paint", "panel", "paper", "party", "peace", "penny", "phone",
        "photo", "piano", "piece", "pilot", "pitch", "place", "plain", "plane", "plant",
        "plate", "point", "pound", "power", "press", "price", "pride", "prime", "print",
        "prior", "prize", "proof", "proud", "prove", "queen", "quick", "quiet", "quite",
        "radio", "raise", "range", "rapid", "ratio", "reach", "ready", "realm", "rebel",
        "refer", "relax", "repay", "reply", "right", "rigid", "risky", "rival", "river",
        "robin", "roger", "roman", "rough", "round", "route", "royal", "rural", "safer",
        "saint", "salad", "sales", "same", "sarah", "sauce", "scale", "scare", "scene",
        "scope", "score", "sense", "serve", "seven", "shall", "shame", "shape", "share",
        "sharp", "sheet", "shelf", "shell", "shift", "shine", "shirt", "shock", "shoot",
        "short", "shown", "sides", "sight", "silly", "since", "sixth", "sixty", "sized",
        "skill", "sleep", "slide", "small", "smart", "smile", "smith", "smoke", "snake",
        "snow", "solid", "solve", "songs", "sorry", "sound", "south", "space", "spare",
        "speak", "speed", "spend", "spent", "split", "spoke", "sport", "staff", "stage",
        "stake", "stand", "start", "state", "stays", "steal", "steam", "steel", "steep",
        "steer", "stern", "stick", "still", "stock", "stone", "stood", "store", "storm",
        "story", "strip", "stuck", "study", "stuff", "style", "sugar", "suite", "super",
        "sweet", "swept", "swift", "swing", "swiss", "table", "taken", "taste", "taxes",
        "teach", "team", "teeth", "terry", "texas", "thank", "theft", "their", "theme",
        "there", "these", "thick", "thing", "think", "third", "those", "three", "threw",
        "throw", "thumb", "tiger", "tight", "timer", "tiny", "tired", "title", "today",
        "token", "topic", "total", "touch", "tough", "tower", "track", "trade", "train",
        "treat", "trend", "trial", "tribe", "trick", "tried", "tries", "truly", "trunk",
        "trust", "truth", "trying", "tumor", "uncle", "under", "undue", "union", "unity",
        "until", "upper", "upset", "urban", "urged", "usage", "used", "user", "using",
        "usual", "valid", "value", "video", "virus", "visit", "vital", "vocal", "voice",
        "waste", "watch", "water", "wheel", "where", "which", "while", "white", "whole",
        "whose", "woman", "women", "world", "worry", "worse", "worst", "worth", "would",
        "write", "wrong", "wrote", "young", "yours", "youth"
    }
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize password hashing context with Argon2
        self.pwd_context = CryptContext(
            schemes=["argon2"],
            default="argon2",
            argon2__memory_cost=65536,  # 64 MB
            argon2__time_cost=3,        # 3 iterations
            argon2__parallelism=2,      # 2 threads
            argon2__hash_len=32,        # 32 byte hash
            argon2__salt_len=16,        # 16 byte salt
            deprecated="auto"
        )
        
        # Load password policy from settings
        self.policy = PasswordPolicy(
            min_length=getattr(self.settings, 'password_min_length', 8),
            max_length=getattr(self.settings, 'password_max_length', 128),
            require_uppercase=getattr(self.settings, 'password_require_uppercase', True),
            require_lowercase=getattr(self.settings, 'password_require_lowercase', True),
            require_digits=getattr(self.settings, 'password_require_digits', True),
            require_special_chars=getattr(self.settings, 'password_require_special_chars', True),
            prevent_common_passwords=getattr(self.settings, 'password_prevent_common', True),
            password_history_count=getattr(self.settings, 'password_history_count', 5),
            password_expiry_days=getattr(self.settings, 'password_expiry_days', None)
        )
    
    def hash_password(self, password: str) -> PasswordHashResult:
        """
        Hash a password using Argon2.
        
        Args:
            password: Plain text password
            
        Returns:
            Password hash result with metadata
        """
        try:
            # Generate hash
            password_hash = self.pwd_context.hash(password)
            
            return PasswordHashResult(
                hash=password_hash,
                algorithm="argon2",
                cost_factor=3,  # time_cost
                salt_length=16,
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to hash password: {str(e)}")
            raise
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password
            hashed_password: Stored password hash
            
        Returns:
            True if password matches
        """
        try:
            return self.pwd_context.verify(password, hashed_password)
        except Exception as e:
            logger.error(f"Failed to verify password: {str(e)}")
            return False
    
    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if password hash needs to be updated.
        
        Args:
            hashed_password: Stored password hash
            
        Returns:
            True if hash should be updated
        """
        try:
            return self.pwd_context.needs_update(hashed_password)
        except Exception as e:
            logger.error(f"Failed to check rehash need: {str(e)}")
            return False
    
    def validate_password(
        self,
        password: str,
        user_info: Optional[Dict[str, Any]] = None,
        password_history: Optional[List[str]] = None
    ) -> PasswordValidationResult:
        """
        Validate password against security policy.
        
        Args:
            password: Password to validate
            user_info: User information for personal info checks
            password_history: List of previous password hashes
            
        Returns:
            Validation result with score and suggestions
        """
        violations = []
        suggestions = []
        score = 0
        
        # Length checks
        if len(password) < self.policy.min_length:
            violations.append(PasswordViolationType.TOO_SHORT)
            suggestions.append(f"Password must be at least {self.policy.min_length} characters long")
        else:
            score += min(20, (len(password) - self.policy.min_length) * 2)
        
        if len(password) > self.policy.max_length:
            violations.append(PasswordViolationType.TOO_LONG)
            suggestions.append(f"Password must be no longer than {self.policy.max_length} characters")
        
        # Character requirements
        if self.policy.require_uppercase:
            uppercase_count = sum(1 for c in password if c.isupper())
            if uppercase_count < self.policy.min_uppercase:
                violations.append(PasswordViolationType.NO_UPPERCASE)
                suggestions.append("Password must contain at least one uppercase letter")
            else:
                score += min(10, uppercase_count * 3)
        
        if self.policy.require_lowercase:
            lowercase_count = sum(1 for c in password if c.islower())
            if lowercase_count < self.policy.min_lowercase:
                violations.append(PasswordViolationType.NO_LOWERCASE)
                suggestions.append("Password must contain at least one lowercase letter")
            else:
                score += min(10, lowercase_count * 2)
        
        if self.policy.require_digits:
            digit_count = sum(1 for c in password if c.isdigit())
            if digit_count < self.policy.min_digits:
                violations.append(PasswordViolationType.NO_DIGITS)
                suggestions.append("Password must contain at least one digit")
            else:
                score += min(15, digit_count * 5)
        
        if self.policy.require_special_chars:
            special_count = sum(1 for c in password if c in self.policy.special_chars)
            if special_count < self.policy.min_special_chars:
                violations.append(PasswordViolationType.NO_SPECIAL_CHARS)
                suggestions.append(f"Password must contain at least {self.policy.min_special_chars} special character(s)")
            else:
                score += min(20, special_count * 7)
        
        # Pattern checks
        if self.policy.prevent_common_passwords:
            if password.lower() in self.COMMON_PASSWORDS:
                violations.append(PasswordViolationType.COMMON_PASSWORD)
                suggestions.append("Password is too common, please choose a more unique password")
                score -= 30
        
        if self.policy.prevent_dictionary_words:
            if password.lower() in self.DICTIONARY_WORDS:
                violations.append(PasswordViolationType.DICTIONARY_WORD)
                suggestions.append("Avoid using dictionary words in your password")
                score -= 20
        
        if self.policy.prevent_sequential_chars:
            if self._has_sequential_chars(password):
                violations.append(PasswordViolationType.SEQUENTIAL_CHARS)
                suggestions.append("Avoid sequential characters (e.g., 123, abc)")
                score -= 15
        
        if self.policy.prevent_repeated_chars:
            if self._has_repeated_chars(password, self.policy.max_repeated_chars):
                violations.append(PasswordViolationType.REPEATED_CHARS)
                suggestions.append(f"Avoid repeating characters more than {self.policy.max_repeated_chars} times")
                score -= 10
        
        # Personal information checks
        if self.policy.prevent_personal_info and user_info:
            if self._contains_personal_info(password, user_info):
                violations.append(PasswordViolationType.CONTAINS_PERSONAL_INFO)
                suggestions.append("Don't use personal information in your password")
                score -= 25
        
        # Password history check
        if password_history:
            for old_hash in password_history[-self.policy.password_history_count:]:
                if self.verify_password(password, old_hash):
                    violations.append(PasswordViolationType.PREVIOUSLY_USED)
                    suggestions.append("Password has been used recently, please choose a different password")
                    score -= 40
                    break
        
        # Calculate entropy
        entropy = self._calculate_entropy(password)
        score += min(25, int(entropy / 2))
        
        # Determine strength
        strength = self._determine_strength(score, len(violations))
        
        # Cap score at 100
        score = min(100, max(0, score))
        
        return PasswordValidationResult(
            is_valid=len(violations) == 0,
            strength=strength,
            score=score,
            violations=violations,
            suggestions=suggestions,
            entropy=entropy
        )
    
    def generate_secure_password(
        self,
        length: int = 16,
        include_uppercase: bool = True,
        include_lowercase: bool = True,
        include_digits: bool = True,
        include_special_chars: bool = True,
        exclude_ambiguous: bool = True
    ) -> str:
        """
        Generate a cryptographically secure password.
        
        Args:
            length: Password length
            include_uppercase: Include uppercase letters
            include_lowercase: Include lowercase letters
            include_digits: Include digits
            include_special_chars: Include special characters
            exclude_ambiguous: Exclude ambiguous characters (0, O, l, I, etc.)
            
        Returns:
            Generated secure password
        """
        charset = ""
        
        if include_lowercase:
            charset += string.ascii_lowercase
        if include_uppercase:
            charset += string.ascii_uppercase
        if include_digits:
            charset += string.digits
        if include_special_chars:
            charset += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        if exclude_ambiguous:
            # Remove ambiguous characters
            ambiguous = "0O1lI|`"
            charset = "".join(c for c in charset if c not in ambiguous)
        
        if not charset:
            raise ValueError("No character sets selected for password generation")
        
        # Generate password ensuring at least one character from each required set
        password = []
        
        # Ensure at least one character from each required set
        if include_lowercase:
            password.append(secrets.choice(string.ascii_lowercase))
        if include_uppercase:
            password.append(secrets.choice(string.ascii_uppercase))
        if include_digits:
            password.append(secrets.choice(string.digits))
        if include_special_chars:
            password.append(secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?"))
        
        # Fill remaining length with random characters
        for _ in range(length - len(password)):
            password.append(secrets.choice(charset))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        
        return "".join(password)
    
    def check_password_expiry(self, password_created_at: datetime) -> Dict[str, Any]:
        """
        Check if password has expired.
        
        Args:
            password_created_at: When password was created
            
        Returns:
            Expiry information
        """
        if not self.policy.password_expiry_days:
            return {
                "is_expired": False,
                "expires_at": None,
                "days_until_expiry": None
            }
        
        expires_at = password_created_at + timedelta(days=self.policy.password_expiry_days)
        now = datetime.now(timezone.utc)
        
        is_expired = now > expires_at
        days_until_expiry = (expires_at - now).days if not is_expired else 0
        
        return {
            "is_expired": is_expired,
            "expires_at": expires_at,
            "days_until_expiry": days_until_expiry
        }
    
    def _has_sequential_chars(self, password: str, min_length: int = 3) -> bool:
        """Check for sequential characters."""
        password_lower = password.lower()
        
        for i in range(len(password_lower) - min_length + 1):
            sequence = password_lower[i:i + min_length]
            
            # Check for ascending sequences
            if all(ord(sequence[j]) == ord(sequence[j-1]) + 1 for j in range(1, len(sequence))):
                return True
            
            # Check for descending sequences
            if all(ord(sequence[j]) == ord(sequence[j-1]) - 1 for j in range(1, len(sequence))):
                return True
        
        return False
    
    def _has_repeated_chars(self, password: str, max_repeats: int) -> bool:
        """Check for repeated characters."""
        count = 1
        for i in range(1, len(password)):
            if password[i] == password[i-1]:
                count += 1
                if count > max_repeats:
                    return True
            else:
                count = 1
        return False
    
    def _contains_personal_info(self, password: str, user_info: Dict[str, Any]) -> bool:
        """Check if password contains personal information."""
        password_lower = password.lower()
        
        # Check common personal info fields
        personal_fields = ['email', 'username', 'first_name', 'last_name', 'name']
        
        for field in personal_fields:
            if field in user_info and user_info[field]:
                value = str(user_info[field]).lower()
                
                # Check if password contains the value
                if len(value) >= 3 and value in password_lower:
                    return True
                
                # Check if password contains parts of email (before @)
                if field == 'email' and '@' in value:
                    email_part = value.split('@')[0]
                    if len(email_part) >= 3 and email_part in password_lower:
                        return True
        
        return False
    
    def _calculate_entropy(self, password: str) -> float:
        """Calculate password entropy."""
        charset_size = 0
        
        if any(c.islower() for c in password):
            charset_size += 26
        if any(c.isupper() for c in password):
            charset_size += 26
        if any(c.isdigit() for c in password):
            charset_size += 10
        if any(c in self.policy.special_chars for c in password):
            charset_size += len(self.policy.special_chars)
        
        if charset_size == 0:
            return 0.0
        
        import math
        return len(password) * math.log2(charset_size)
    
    def _determine_strength(self, score: int, violation_count: int) -> PasswordStrength:
        """Determine password strength based on score and violations."""
        if violation_count > 0:
            return PasswordStrength.VERY_WEAK
        
        if score >= 90:
            return PasswordStrength.VERY_STRONG
        elif score >= 70:
            return PasswordStrength.STRONG
        elif score >= 50:
            return PasswordStrength.MEDIUM
        elif score >= 30:
            return PasswordStrength.WEAK
        else:
            return PasswordStrength.VERY_WEAK
    
    async def check_password_history(
        self,
        supabase_user_id: str,
        new_password: str
    ) -> bool:
        """
        Check if password was recently used.
        
        Args:
            supabase_user_id: User ID
            new_password: New password to check
            
        Returns:
            True if password was recently used, False otherwise
        """
        try:
            from app.models.auth import PasswordHistory
            from app.api.deps import get_db
            
            # Get database session
            db = next(get_db())
            
            # Get recent password history
            recent_passwords = db.query(PasswordHistory).filter(
                PasswordHistory.supabase_user_id == supabase_user_id
            ).order_by(PasswordHistory.created_at.desc()).limit(
                self.policy.password_history_count
            ).all()
            
            # Check against each recent password
            for password_record in recent_passwords:
                if self.verify_password(new_password, password_record.password_hash):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking password history: {str(e)}")
            return False
    
    async def update_user_password(
        self,
        supabase_user_id: str,
        password_hash: str,
        algorithm: str = 'argon2'
    ) -> None:
        """
        Update user password and maintain password history.
        
        Args:
            supabase_user_id: User ID
            password_hash: New password hash
            algorithm: Hashing algorithm used
        """
        try:
            from app.models.auth import PasswordHistory
            from app.api.deps import get_db
            
            # Get database session
            db = next(get_db())
            
            # Mark all current passwords as not current
            db.query(PasswordHistory).filter(
                PasswordHistory.supabase_user_id == supabase_user_id,
                PasswordHistory.is_current == True
            ).update({"is_current": False})
            
            # Create new password history entry
            new_password_record = PasswordHistory.create_password_entry(
                supabase_user_id=supabase_user_id,
                password_hash=password_hash,
                algorithm=algorithm,
                is_current=True
            )
            
            db.add(new_password_record)
            
            # Clean up old password history (keep only last N passwords)
            old_passwords = db.query(PasswordHistory).filter(
                PasswordHistory.supabase_user_id == supabase_user_id
            ).order_by(PasswordHistory.created_at.desc()).offset(
                self.policy.password_history_count
            ).all()
            
            for old_password in old_passwords:
                db.delete(old_password)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating user password: {str(e)}")
            db.rollback()
            raise


# Global password security instance
password_security: Optional[PasswordSecurity] = None


def get_password_security() -> PasswordSecurity:
    """
    Get password security service instance.
    
    Returns:
        PasswordSecurity instance
    """
    global password_security
    if password_security is None:
        password_security = PasswordSecurity()
    return password_security


# Convenience functions

def hash_password(password: str) -> str:
    """Hash a password."""
    return get_password_security().hash_password(password).hash


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password."""
    return get_password_security().verify_password(password, hashed_password)


def validate_password(password: str, user_info: Optional[Dict[str, Any]] = None) -> PasswordValidationResult:
    """Validate a password."""
    return get_password_security().validate_password(password, user_info)


def generate_secure_password(length: int = 16) -> str:
    """Generate a secure password."""
    return get_password_security().generate_secure_password(length)