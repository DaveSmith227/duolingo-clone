"""
Configuration Inheritance System

Provides configuration inheritance capabilities where staging environments
can inherit from production configurations with selective overrides.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Set, List, Union
from pathlib import Path
from dataclasses import dataclass
from copy import deepcopy

from .environment import Environment, get_environment

logger = logging.getLogger(__name__)


@dataclass
class InheritanceRule:
    """Configuration inheritance rule."""
    source_env: Environment
    target_env: Environment
    inherit_fields: Set[str]
    exclude_fields: Set[str]
    override_values: Dict[str, Any]


class ConfigurationInheritance:
    """
    Manages configuration inheritance between environments.
    
    Supports staging inheriting from production with ability to override
    specific values while maintaining security and consistency.
    """
    
    # Default inheritance rules
    DEFAULT_RULES = {
        Environment.STAGING: InheritanceRule(
            source_env=Environment.PRODUCTION,
            target_env=Environment.STAGING,
            inherit_fields={
                # Security settings that should match production
                "password_min_length",
                "password_require_uppercase",
                "password_require_lowercase", 
                "password_require_digits",
                "password_require_special_chars",
                "password_prevent_common",
                "password_history_count",
                "require_email_verification",
                "csrf_protection_enabled",
                "rate_limiting_enabled",
                "login_rate_limit_attempts",
                "login_rate_limit_window_minutes",
                "lockout_max_failed_attempts",
                "lockout_duration_minutes",
                
                # Application settings
                "app_name",
                "app_version",
                "jwt_algorithm",
                "access_token_expire_minutes",
                "refresh_token_expire_days",
                
                # Database and Redis pool settings
                "db_pool_size",
                "db_max_overflow",
                
                # Email settings structure
                "smtp_port",
                "smtp_use_tls",
                "from_email",
            },
            exclude_fields={
                # Never inherit sensitive secrets
                "secret_key",
                "db_password",
                "redis_password",
                "supabase_service_role_key",
                "supabase_anon_key",
                "supabase_jwt_secret",
                "openai_api_key",
                "smtp_password",
                "google_client_secret",
                "apple_private_key_path",
                "facebook_app_secret",
                "tiktok_client_secret",
                
                # Environment-specific URLs and hosts
                "supabase_url",
                "database_url",
                "redis_url",
                "db_host",
                "redis_host",
                "smtp_host",
                "frontend_url",
                "oauth_redirect_url",
                "cors_origins",
                
                # Environment-specific flags
                "debug",
                "reload",
                "environment",
            },
            override_values={
                # Staging-specific overrides
                "debug": True,
                "cors_origins": ["http://localhost:3000", "https://staging.duolingoclone.com"],
                "require_email_verification": False,  # Relaxed for testing
            }
        )
    }
    
    def __init__(self, config_source: Optional[Path] = None):
        """
        Initialize configuration inheritance system.
        
        Args:
            config_source: Path to load inheritance rules from
        """
        self.rules: Dict[Environment, InheritanceRule] = {}
        self.production_config: Optional[Dict[str, Any]] = None
        
        # Load default rules
        self.rules.update(self.DEFAULT_RULES)
        
        # Load custom rules if provided
        if config_source and config_source.exists():
            self._load_rules_from_file(config_source)
    
    def _load_rules_from_file(self, config_file: Path):
        """Load inheritance rules from JSON file."""
        try:
            with config_file.open('r') as f:
                rules_data = json.load(f)
            
            for env_name, rule_data in rules_data.items():
                env = Environment(env_name)
                rule = InheritanceRule(
                    source_env=Environment(rule_data['source_env']),
                    target_env=env,
                    inherit_fields=set(rule_data.get('inherit_fields', [])),
                    exclude_fields=set(rule_data.get('exclude_fields', [])),
                    override_values=rule_data.get('override_values', {})
                )
                self.rules[env] = rule
                
            logger.info(f"Loaded inheritance rules from {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to load inheritance rules from {config_file}: {e}")
    
    def set_production_config(self, config: Dict[str, Any]):
        """Set the production configuration to inherit from."""
        self.production_config = deepcopy(config)
        logger.info("Production configuration set for inheritance")
    
    def apply_inheritance(self, current_config: Dict[str, Any], 
                         target_env: Environment) -> Dict[str, Any]:
        """
        Apply inheritance rules to configuration.
        
        Args:
            current_config: Current configuration
            target_env: Target environment
            
        Returns:
            Configuration with inheritance applied
        """
        if target_env not in self.rules:
            logger.debug(f"No inheritance rules for {target_env.value}")
            return current_config
        
        if not self.production_config:
            logger.warning("No production configuration available for inheritance")
            return current_config
        
        rule = self.rules[target_env]
        result_config = deepcopy(current_config)
        
        logger.info(f"Applying inheritance rules for {target_env.value}")
        
        # Apply inherited fields
        inherited_count = 0
        for field in rule.inherit_fields:
            if field in self.production_config and field not in rule.exclude_fields:
                # Only inherit if not explicitly set in current config
                if (field not in current_config or 
                    self._is_default_value(field, current_config[field])):
                    result_config[field] = self.production_config[field]
                    inherited_count += 1
                    logger.debug(f"Inherited {field} from production")
        
        # Apply overrides
        override_count = 0
        for field, value in rule.override_values.items():
            if field not in rule.exclude_fields:
                result_config[field] = value
                override_count += 1
                logger.debug(f"Applied override {field} = {value}")
        
        logger.info(
            f"Inheritance complete: {inherited_count} fields inherited, "
            f"{override_count} overrides applied"
        )
        
        return result_config
    
    def _is_default_value(self, field: str, value: Any) -> bool:
        """Check if a value appears to be a default value."""
        # Common default patterns that indicate the value wasn't explicitly set
        default_patterns = [
            "localhost",
            "127.0.0.1",
            "dev-",
            "development",
            "change-me",
            "default-",
            "password",  # Default passwords
            "",
            None,
        ]
        
        str_value = str(value).lower()
        return any(pattern in str_value for pattern in default_patterns)
    
    def validate_inheritance(self, config: Dict[str, Any], 
                           target_env: Environment) -> List[str]:
        """
        Validate that inheritance was applied correctly.
        
        Args:
            config: Configuration to validate
            target_env: Target environment
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if target_env not in self.rules or not self.production_config:
            return issues
        
        rule = self.rules[target_env]
        
        # Check that sensitive fields are not inherited
        for field in rule.exclude_fields:
            if (field in config and field in self.production_config and 
                config[field] == self.production_config[field]):
                
                # Allow if it's a non-sensitive field with same value intentionally
                if field not in {"secret_key", "db_password", "redis_password"}:
                    continue
                    
                issues.append(
                    f"Sensitive field '{field}' appears to be inherited from production"
                )
        
        # Check that required security settings are inherited
        security_fields = {
            "password_min_length", "require_email_verification", 
            "csrf_protection_enabled", "rate_limiting_enabled"
        }
        
        for field in security_fields.intersection(rule.inherit_fields):
            if field in self.production_config:
                if (field not in config or 
                    config[field] != self.production_config[field]):
                    # Check if there's a valid override
                    if field not in rule.override_values:
                        issues.append(
                            f"Security field '{field}' should be inherited from production"
                        )
        
        return issues
    
    def get_inheritance_report(self, config: Dict[str, Any], 
                              target_env: Environment) -> Dict[str, Any]:
        """
        Generate a report of inheritance application.
        
        Args:
            config: Configuration after inheritance
            target_env: Target environment
            
        Returns:
            Inheritance report
        """
        if target_env not in self.rules or not self.production_config:
            return {"status": "no_inheritance", "message": "No inheritance rules or production config"}
        
        rule = self.rules[target_env]
        
        inherited_fields = []
        overridden_fields = []
        excluded_fields = list(rule.exclude_fields)
        
        # Check inherited fields
        for field in rule.inherit_fields:
            if (field in config and field in self.production_config and 
                config[field] == self.production_config[field]):
                inherited_fields.append(field)
        
        # Check overridden fields
        for field, value in rule.override_values.items():
            if field in config and config[field] == value:
                overridden_fields.append(field)
        
        return {
            "status": "applied",
            "source_environment": rule.source_env.value,
            "target_environment": rule.target_env.value,
            "inherited_fields": inherited_fields,
            "overridden_fields": overridden_fields,
            "excluded_fields": excluded_fields,
            "total_inherit_rules": len(rule.inherit_fields),
            "total_exclude_rules": len(rule.exclude_fields),
            "total_override_rules": len(rule.override_values),
        }


# Global inheritance manager
_inheritance_manager: Optional[ConfigurationInheritance] = None


def get_inheritance_manager() -> ConfigurationInheritance:
    """Get or create the global inheritance manager."""
    global _inheritance_manager
    
    if _inheritance_manager is None:
        _inheritance_manager = ConfigurationInheritance()
    
    return _inheritance_manager


def apply_config_inheritance(config: Dict[str, Any], 
                           environment: Optional[Environment] = None) -> Dict[str, Any]:
    """
    Apply configuration inheritance for the current environment.
    
    Args:
        config: Current configuration
        environment: Target environment (auto-detected if None)
        
    Returns:
        Configuration with inheritance applied
    """
    if environment is None:
        environment = get_environment()
    
    manager = get_inheritance_manager()
    return manager.apply_inheritance(config, environment)


def set_production_baseline(config: Dict[str, Any]):
    """Set the production configuration as baseline for inheritance."""
    manager = get_inheritance_manager()
    manager.set_production_config(config)


def validate_inheritance_application(config: Dict[str, Any], 
                                   environment: Optional[Environment] = None) -> List[str]:
    """Validate that configuration inheritance was applied correctly."""
    if environment is None:
        environment = get_environment()
    
    manager = get_inheritance_manager()
    return manager.validate_inheritance(config, environment)


def get_inheritance_report(config: Dict[str, Any], 
                          environment: Optional[Environment] = None) -> Dict[str, Any]:
    """Get inheritance application report."""
    if environment is None:
        environment = get_environment()
    
    manager = get_inheritance_manager()
    return manager.get_inheritance_report(config, environment)