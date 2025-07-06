"""
Database Configuration Service

Handles database-related configuration, connection string building,
and database-specific validation following the Single Responsibility Principle.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator

from ..environment import Environment


class DatabaseConfig(BaseModel):
    """Database configuration model."""
    database_url: Optional[str] = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "duolingo_clone"
    db_user: str = "postgres"
    db_password: str = "password"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    @field_validator("db_host")
    @classmethod
    def validate_host(cls, v):
        """Validate host is not empty."""
        if not v or not v.strip():
            raise ValueError("Database host cannot be empty")
        return v


class DatabaseValidationResult(BaseModel):
    """Database validation result."""
    field: str
    message: str
    severity: str  # "error", "warning", "info"


class DatabaseConfigService:
    """
    Service responsible for database configuration management.
    
    Responsibilities:
    - Database connection string construction
    - Database configuration validation
    - Environment-specific database requirements
    """
    
    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize with configuration dictionary."""
        db_config = {
            key.replace('db_', ''): value 
            for key, value in config_dict.items() 
            if key.startswith(('db_', 'database_'))
        }
        
        # Handle special cases
        if 'database_url' in config_dict:
            db_config['database_url'] = config_dict['database_url']
        
        self.config = DatabaseConfig(**db_config)
    
    def build_dsn(self, environment: Environment) -> str:
        """
        Build database connection string based on environment.
        
        Args:
            environment: Current environment
            
        Returns:
            Database connection string
        """
        if self.config.database_url:
            return self.config.database_url
        
        # Use SQLite for development/test, PostgreSQL for production/staging
        if environment in [Environment.DEVELOPMENT, Environment.TEST]:
            return "sqlite:///./app.db"
        
        return (
            f"postgresql://{self.config.db_user}:{self.config.db_password}"
            f"@{self.config.db_host}:{self.config.db_port}/{self.config.db_name}"
        )
    
    def validate_for_environment(self, environment: Environment) -> List[DatabaseValidationResult]:
        """
        Validate database configuration for specific environment.
        
        Args:
            environment: Environment to validate for
            
        Returns:
            List of validation results
        """
        results = []
        
        if environment == Environment.PRODUCTION:
            results.extend(self._validate_production_database())
        elif environment == Environment.STAGING:
            results.extend(self._validate_staging_database())
        elif environment == Environment.DEVELOPMENT:
            results.extend(self._validate_development_database())
        
        return results
    
    def _validate_production_database(self) -> List[DatabaseValidationResult]:
        """Validate production database requirements."""
        results = []
        
        # Require proper database configuration
        if not self.config.database_url:
            required_fields = ["db_host", "db_port", "db_name", "db_user", "db_password"]
            missing = [
                field for field in required_fields 
                if not getattr(self.config, field)
            ]
            if missing:
                results.append(DatabaseValidationResult(
                    field="database_config",
                    message=f"Missing database configuration: {', '.join(missing)}",
                    severity="error"
                ))
        
        # Warn about SQLite in production
        dsn = self.build_dsn(Environment.PRODUCTION)
        if "sqlite" in dsn.lower():
            results.append(DatabaseValidationResult(
                field="database_url",
                message="SQLite is not recommended for production use",
                severity="warning"
            ))
        
        # Check pool size for production
        if self.config.db_pool_size < 5:
            results.append(DatabaseValidationResult(
                field="db_pool_size",
                message="Database pool size should be at least 5 for production",
                severity="warning"
            ))
        
        return results
    
    def _validate_staging_database(self) -> List[DatabaseValidationResult]:
        """Validate staging database requirements."""
        results = []
        
        # Check if using production-like database
        if not self.config.database_url and "localhost" in self.config.db_host:
            results.append(DatabaseValidationResult(
                field="db_host",
                message="Consider using a dedicated staging database server",
                severity="warning"
            ))
        
        return results
    
    def _validate_development_database(self) -> List[DatabaseValidationResult]:
        """Validate development database requirements."""
        results = []
        
        # SQLite is fine for development
        if self.config.database_url and "postgresql" in self.config.database_url:
            results.append(DatabaseValidationResult(
                field="database_url",
                message="PostgreSQL in development may slow down startup",
                severity="info"
            ))
        
        return results
    
    def get_safe_config(self) -> Dict[str, Any]:
        """Get database configuration with sensitive data redacted."""
        config_dict = self.config.model_dump()
        
        # Redact sensitive fields
        if config_dict.get("db_password"):
            config_dict["db_password"] = "***REDACTED***"
            
        if config_dict.get("database_url"):
            # Redact password from URL
            url = config_dict["database_url"]
            if "@" in url and "://" in url:
                scheme, rest = url.split("://", 1)
                if "@" in rest:
                    creds, host_part = rest.split("@", 1)
                    if ":" in creds:
                        user, _ = creds.split(":", 1)
                        config_dict["database_url"] = f"{scheme}://{user}:***@{host_part}"
        
        return config_dict
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for debugging."""
        return {
            "has_database_url": bool(self.config.database_url),
            "db_host": self.config.db_host,
            "db_port": self.config.db_port,
            "db_name": self.config.db_name,
            "pool_size": self.config.db_pool_size,
            "max_overflow": self.config.db_max_overflow
        }