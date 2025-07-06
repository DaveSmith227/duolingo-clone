"""
Audited Configuration Wrapper

Provides automatic audit logging for configuration access and modifications
by wrapping the Settings class with audit capabilities.
"""

from typing import Any, Dict, Optional, Set, Type, TypeVar
from functools import wraps
import inspect
from datetime import datetime

from pydantic_settings import BaseSettings

from .audit_logger import get_audit_logger, AuditAction
from .config import Settings


T = TypeVar('T', bound=BaseSettings)


class AuditedSettings:
    """
    Wrapper for Settings class that automatically logs all configuration
    access and modifications.
    """
    
    def __init__(self, settings: Settings):
        self._settings = settings
        self._audit_logger = get_audit_logger()
        self._access_count: Dict[str, int] = {}
        self._modification_history: Dict[str, list] = {}
        
        # Fields to exclude from auditing (system fields)
        self._excluded_fields = {
            "_env_file", "_env_file_encoding", "_case_sensitive",
            "_env_prefix", "_env_nested_delimiter", "__config__",
            "__fields__", "__validators__", "_access_count",
            "_modification_history", "_audit_logger", "_settings",
            "_excluded_fields"
        }
    
    def __getattribute__(self, name: str) -> Any:
        """Intercept attribute access for auditing."""
        # Handle internal attributes without auditing
        if name.startswith('_') or name in object.__getattribute__(self, '_excluded_fields'):
            return object.__getattribute__(self, name)
        
        # Special handling for methods
        if name in ['dict', 'json', 'export_safe', 'get_environment_info', 
                   'reload', '__class__', '__dict__', 'export_audit_safe',
                   'get_access_stats', 'get_modification_history']:
            # Return our own methods if they exist
            if hasattr(self, name):
                return object.__getattribute__(self, name)
            return getattr(object.__getattribute__(self, '_settings'), name)
        
        try:
            # Get the actual value from settings
            value = getattr(object.__getattribute__(self, '_settings'), name)
            
            # Track access count
            access_count = object.__getattribute__(self, '_access_count')
            access_count[name] = access_count.get(name, 0) + 1
            
            # Log the access
            audit_logger = object.__getattribute__(self, '_audit_logger')
            audit_logger.log_config_read(
                field_name=name,
                value=value if not self._is_sensitive_field(name) else "***",
                success=True,
                metadata={
                    "access_count": access_count[name],
                    "field_type": type(value).__name__
                }
            )
            
            return value
            
        except AttributeError as e:
            # Log failed access attempt
            audit_logger = object.__getattribute__(self, '_audit_logger')
            audit_logger.log_config_read(
                field_name=name,
                success=False,
                error_message=str(e),
                metadata={"error_type": "AttributeError"}
            )
            raise
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Intercept attribute setting for auditing."""
        # Handle internal attributes
        if name.startswith('_') or name == 'settings':
            object.__setattr__(self, name, value)
            return
        
        # Get old value for comparison
        old_value = None
        try:
            old_value = getattr(self._settings, name)
        except AttributeError:
            pass
        
        # Attempt to set the value
        try:
            setattr(self._settings, name, value)
            
            # Track modification history
            if name not in self._modification_history:
                self._modification_history[name] = []
            
            self._modification_history[name].append({
                "timestamp": datetime.utcnow().isoformat(),
                "old_value": old_value,
                "new_value": value
            })
            
            # Log the modification
            self._audit_logger.log_config_write(
                field_name=name,
                old_value=old_value if not self._is_sensitive_field(name) else "***",
                new_value=value if not self._is_sensitive_field(name) else "***",
                success=True,
                metadata={
                    "modification_count": len(self._modification_history[name]),
                    "value_type": type(value).__name__
                }
            )
            
        except Exception as e:
            # Log failed modification
            self._audit_logger.log_config_write(
                field_name=name,
                old_value=old_value,
                new_value=value,
                success=False,
                error_message=str(e),
                metadata={"error_type": type(e).__name__}
            )
            raise
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field contains sensitive data."""
        sensitive_patterns = [
            "password", "secret", "key", "token", "credential",
            "private", "auth", "jwt", "api", "supabase"
        ]
        field_lower = field_name.lower()
        return any(pattern in field_lower for pattern in sensitive_patterns)
    
    def get_access_stats(self) -> Dict[str, Any]:
        """Get statistics about configuration access."""
        total_accesses = sum(self._access_count.values())
        
        return {
            "total_accesses": total_accesses,
            "by_field": dict(self._access_count),
            "most_accessed": max(self._access_count.items(), 
                               key=lambda x: x[1])[0] if self._access_count else None,
            "fields_accessed": len(self._access_count),
            "fields_modified": len(self._modification_history),
            "total_modifications": sum(len(history) for history in 
                                     self._modification_history.values())
        }
    
    def get_modification_history(self, field_name: Optional[str] = None) -> Dict[str, Any]:
        """Get modification history for a field or all fields."""
        if field_name:
            return {
                field_name: self._modification_history.get(field_name, [])
            }
        return dict(self._modification_history)
    
    def export_audit_safe(self) -> Dict[str, Any]:
        """Export configuration with audit logging."""
        try:
            # Use the safe export method from settings
            config_dict = self._settings.export_safe()
            
            # Log the export
            self._audit_logger.log_config_export(
                export_format="dict",
                include_sensitive=False,
                success=True,
                metadata={
                    "fields_count": len(config_dict),
                    "access_stats": self.get_access_stats()
                }
            )
            
            return config_dict
            
        except Exception as e:
            self._audit_logger.log_config_export(
                export_format="dict",
                include_sensitive=False,
                success=False,
                error_message=str(e)
            )
            raise


def create_audited_settings(settings: Settings) -> AuditedSettings:
    """Create an audited wrapper for settings."""
    return AuditedSettings(settings)


def audit_config_access(func):
    """Decorator to audit configuration access in functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        audit_logger = get_audit_logger()
        
        # Log function entry
        metadata = {
            "function": func.__name__,
            "module": func.__module__,
            "args_count": len(args),
            "kwargs_keys": list(kwargs.keys())
        }
        
        try:
            result = func(*args, **kwargs)
            
            # Log successful execution
            audit_logger.log_event(AuditAction.READ, 
                                 field_name=f"function:{func.__name__}",
                                 success=True,
                                 metadata=metadata)
            
            return result
            
        except Exception as e:
            # Log failed execution
            audit_logger.log_event(
                AuditAction.READ,
                field_name=f"function:{func.__name__}",
                success=False,
                error_message=str(e),
                metadata={**metadata, "error_type": type(e).__name__}
            )
            raise
    
    return wrapper


class AuditedConfigDict(dict):
    """
    Dictionary subclass that audits all access and modifications.
    Useful for configuration dictionaries.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._audit_logger = get_audit_logger()
        self._access_count: Dict[str, int] = {}
    
    def __getitem__(self, key):
        """Audit dictionary access."""
        value = super().__getitem__(key)
        
        # Track and log access
        self._access_count[key] = self._access_count.get(key, 0) + 1
        
        self._audit_logger.log_config_read(
            field_name=f"config_dict.{key}",
            value=value if not self._is_sensitive_key(key) else "***",
            success=True,
            metadata={"access_count": self._access_count[key]}
        )
        
        return value
    
    def __setitem__(self, key, value):
        """Audit dictionary modifications."""
        # Get old value
        old_value = self.get(key)
        
        # Set new value
        super().__setitem__(key, value)
        
        # Log modification
        self._audit_logger.log_config_write(
            field_name=f"config_dict.{key}",
            old_value=old_value if not self._is_sensitive_key(key) else "***",
            new_value=value if not self._is_sensitive_key(key) else "***",
            success=True
        )
    
    def _is_sensitive_key(self, key: str) -> bool:
        """Check if a key represents sensitive data."""
        sensitive_patterns = ["password", "secret", "key", "token", "auth"]
        key_lower = str(key).lower()
        return any(pattern in key_lower for pattern in sensitive_patterns)
    
    def get(self, key, default=None):
        """Override get to audit access."""
        try:
            return self[key]
        except KeyError:
            return default
    
    def pop(self, key, *args):
        """Audit key removal."""
        old_value = self.get(key)
        result = super().pop(key, *args)
        
        if old_value is not None:
            self._audit_logger.log_config_write(
                field_name=f"config_dict.{key}",
                old_value=old_value if not self._is_sensitive_key(key) else "***",
                new_value=None,
                success=True,
                metadata={"operation": "delete"}
            )
        
        return result