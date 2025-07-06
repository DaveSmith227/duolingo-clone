"""
Environment Detection and Management

Provides robust environment detection based on multiple environment variables
and context clues. Supports the NODE_ENV convention from Node.js ecosystem
alongside our ENVIRONMENT variable for consistent cross-platform detection.
"""

import os
import logging
import warnings
from enum import Enum
from typing import Optional, Dict, Any, List
from functools import lru_cache

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Supported application environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class EnvironmentDetector:
    """
    Detects and validates application environment from multiple sources.
    """
    
    # Environment variable names in order of precedence
    ENV_VAR_NAMES = [
        "ENVIRONMENT",  # Our primary variable
        "NODE_ENV",     # Node.js convention for compatibility
        "APP_ENV",      # Alternative naming
        "DEPLOY_ENV",   # Deployment-specific
    ]
    
    # Default environments for different contexts
    DEFAULT_BY_CONTEXT = {
        "pytest": Environment.TEST,
        "uvicorn": Environment.DEVELOPMENT,
        "gunicorn": Environment.PRODUCTION,
    }
    
    def __init__(self):
        self._detected_env: Optional[Environment] = None
        self._detection_source: Optional[str] = None
        self._detection_confidence: float = 0.0
        self._context_hints: Dict[str, Any] = {}
    
    @lru_cache(maxsize=1)
    def detect_environment(self) -> Environment:
        """
        Detect the current environment using multiple strategies.
        
        Returns:
            Environment enum value
        """
        if self._detected_env:
            return self._detected_env
        
        # Strategy 1: Direct environment variable lookup
        env = self._detect_from_env_vars()
        if env:
            self._detected_env = env
            return env
        
        # Strategy 2: Context-based detection
        env = self._detect_from_context()
        if env:
            self._detected_env = env
            return env
        
        # Strategy 3: Inference from other environment variables
        env = self._detect_from_inference()
        if env:
            self._detected_env = env
            return env
        
        # Default fallback
        logger.warning(
            "Could not detect environment from any source, defaulting to development. "
            "Set ENVIRONMENT or NODE_ENV to specify explicitly."
        )
        self._detected_env = Environment.DEVELOPMENT
        self._detection_source = "default_fallback"
        self._detection_confidence = 0.1
        
        return self._detected_env
    
    def _detect_from_env_vars(self) -> Optional[Environment]:
        """Detect environment from environment variables."""
        for var_name in self.ENV_VAR_NAMES:
            value = os.environ.get(var_name)
            if value:
                try:
                    env = Environment(value.lower())
                    self._detection_source = var_name
                    self._detection_confidence = 1.0
                    logger.info(f"Environment detected from {var_name}: {env.value}")
                    return env
                except ValueError:
                    logger.warning(
                        f"Invalid environment value '{value}' in {var_name}. "
                        f"Valid values: {[e.value for e in Environment]}"
                    )
        
        return None
    
    def _detect_from_context(self) -> Optional[Environment]:
        """Detect environment from execution context."""
        # Check command line or process context
        import sys
        
        # Check if running under pytest
        if "pytest" in sys.modules or "pytest" in " ".join(sys.argv):
            self._detection_source = "pytest_context"
            self._detection_confidence = 0.9
            self._context_hints["test_runner"] = "pytest"
            logger.info("Environment detected from pytest context: test")
            return Environment.TEST
        
        # Check for common server contexts
        server_process = self._get_server_process_name()
        if server_process in self.DEFAULT_BY_CONTEXT:
            env = self.DEFAULT_BY_CONTEXT[server_process]
            self._detection_source = f"{server_process}_process"
            self._detection_confidence = 0.7
            self._context_hints["server_process"] = server_process
            logger.info(f"Environment detected from {server_process} process: {env.value}")
            return env
        
        return None
    
    def _detect_from_inference(self) -> Optional[Environment]:
        """Infer environment from other environmental clues."""
        clues = []
        
        # Check for production-like indicators
        if os.environ.get("PRODUCTION") == "true":
            clues.append(("PRODUCTION=true", Environment.PRODUCTION, 0.8))
        
        if os.environ.get("DEBUG") == "false":
            clues.append(("DEBUG=false", Environment.PRODUCTION, 0.6))
        
        # Check for development-like indicators
        if os.environ.get("DEBUG") == "true":
            clues.append(("DEBUG=true", Environment.DEVELOPMENT, 0.7))
        
        if os.environ.get("RELOAD") == "true":
            clues.append(("RELOAD=true", Environment.DEVELOPMENT, 0.6))
        
        # Check for staging-like indicators
        staging_keywords = ["staging", "stage", "pre-prod", "preprod"]
        for var_name, var_value in os.environ.items():
            if any(keyword in var_name.lower() or keyword in str(var_value).lower() 
                   for keyword in staging_keywords):
                clues.append((f"{var_name}={var_value}", Environment.STAGING, 0.5))
        
        # Check for test-like indicators
        test_keywords = ["test", "testing", "ci"]
        for var_name, var_value in os.environ.items():
            if any(keyword in var_name.lower() or keyword in str(var_value).lower() 
                   for keyword in test_keywords):
                clues.append((f"{var_name}={var_value}", Environment.TEST, 0.6))
        
        # Sort by confidence and pick the highest
        if clues:
            clues.sort(key=lambda x: x[2], reverse=True)
            best_clue, env, confidence = clues[0]
            
            if confidence > 0.5:
                self._detection_source = f"inference_{best_clue}"
                self._detection_confidence = confidence
                self._context_hints["inference_clues"] = clues
                logger.info(f"Environment inferred from {best_clue}: {env.value}")
                return env
        
        return None
    
    def _get_server_process_name(self) -> Optional[str]:
        """Get the name of the server process."""
        import sys
        
        # Check sys.argv for server indicators
        argv_str = " ".join(sys.argv)
        
        if "uvicorn" in argv_str:
            return "uvicorn"
        elif "gunicorn" in argv_str:
            return "gunicorn"
        elif "python -m" in argv_str and "fastapi" in argv_str:
            return "fastapi"
        
        return None
    
    def get_detection_info(self) -> Dict[str, Any]:
        """Get detailed information about environment detection."""
        return {
            "environment": self._detected_env.value if self._detected_env else None,
            "source": self._detection_source,
            "confidence": self._detection_confidence,
            "context_hints": self._context_hints,
            "available_env_vars": {
                var: os.environ.get(var) 
                for var in self.ENV_VAR_NAMES 
                if os.environ.get(var)
            }
        }
    
    def validate_environment_consistency(self) -> List[str]:
        """
        Validate that environment variables are consistent.
        
        Returns:
            List of consistency issues found
        """
        issues = []
        
        # Check for conflicting environment variables
        env_values = {}
        for var_name in self.ENV_VAR_NAMES:
            value = os.environ.get(var_name)
            if value:
                env_values[var_name] = value.lower()
        
        if len(set(env_values.values())) > 1:
            issues.append(
                f"Conflicting environment variables: {env_values}. "
                f"Ensure all environment variables specify the same environment."
            )
        
        # Check for environment-specific variable conflicts
        current_env = self.detect_environment()
        
        if current_env == Environment.PRODUCTION:
            if os.environ.get("DEBUG", "").lower() == "true":
                issues.append("DEBUG=true in production environment")
            
            if os.environ.get("RELOAD", "").lower() == "true":
                issues.append("RELOAD=true in production environment")
        
        elif current_env == Environment.DEVELOPMENT:
            if os.environ.get("DEBUG", "").lower() == "false":
                issues.append("DEBUG=false in development environment (warning)")
        
        return issues
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.detect_environment() == Environment.DEVELOPMENT
    
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.detect_environment() == Environment.STAGING
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.detect_environment() == Environment.PRODUCTION
    
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.detect_environment() == Environment.TEST
    
    def get_environment_name(self) -> str:
        """Get the environment name as a string."""
        return self.detect_environment().value


# Global detector instance
_detector = EnvironmentDetector()

# Convenience functions
def get_environment() -> Environment:
    """Get the current environment."""
    return _detector.detect_environment()

def get_environment_name() -> str:
    """Get the current environment name."""
    return _detector.get_environment_name()

def is_development() -> bool:
    """Check if running in development."""
    return _detector.is_development()

def is_staging() -> bool:
    """Check if running in staging."""
    return _detector.is_staging()

def is_production() -> bool:
    """Check if running in production."""
    return _detector.is_production()

def is_testing() -> bool:
    """Check if running in test environment."""
    return _detector.is_testing()

def get_detection_info() -> Dict[str, Any]:
    """Get environment detection information."""
    return _detector.get_detection_info()

def validate_environment_consistency() -> List[str]:
    """Validate environment variable consistency."""
    return _detector.validate_environment_consistency()

def reset_detection_cache():
    """Reset the environment detection cache (useful for testing)."""
    global _detector
    _detector = EnvironmentDetector()