#!/usr/bin/env python3

"""
Configuration Migration Tool

Provides tools to migrate configuration between different versions of the application,
handle breaking changes, and ensure backward compatibility.

Features:
- Version detection and migration planning
- Automatic configuration backup and restore
- Field renaming and transformation
- Validation of migrated configuration
- Rollback capability
- Environment-specific migration rules
- Migration history tracking

Usage:
    python scripts/migrate_config.py --from-version 0.1.0 --to-version 0.2.0
    python scripts/migrate_config.py --auto-detect
    python scripts/migrate_config.py --rollback
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import re
from dataclasses import dataclass, asdict
from enum import Enum

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.core.config import Settings
    from app.core.config_validators import ConfigurationBusinessRuleValidator
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the backend directory with virtual environment activated")
    sys.exit(1)


class MigrationType(Enum):
    """Types of migration operations."""
    RENAME_FIELD = "rename_field"
    TRANSFORM_VALUE = "transform_value"
    ADD_FIELD = "add_field"
    REMOVE_FIELD = "remove_field"
    SPLIT_FIELD = "split_field"
    MERGE_FIELDS = "merge_fields"
    CONDITIONAL_UPDATE = "conditional_update"


@dataclass
class MigrationRule:
    """Represents a single migration rule."""
    rule_type: MigrationType
    source_field: Optional[str] = None
    target_field: Optional[str] = None
    source_fields: Optional[List[str]] = None
    target_fields: Optional[List[str]] = None
    transformation: Optional[str] = None  # Python expression or function name
    condition: Optional[str] = None  # Condition for conditional updates
    default_value: Optional[Any] = None
    description: str = ""
    environments: Optional[List[str]] = None  # Environments where this rule applies


@dataclass
class MigrationPlan:
    """Complete migration plan from one version to another."""
    from_version: str
    to_version: str
    rules: List[MigrationRule]
    description: str = ""
    breaking_changes: List[str] = None
    rollback_supported: bool = True


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    success: bool
    from_version: str
    to_version: str
    migrated_fields: List[str]
    warnings: List[str]
    errors: List[str]
    backup_path: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class ConfigMigrator:
    """Main configuration migration tool."""
    
    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        self.backup_dir = self.config_dir / "backups"
        self.migration_dir = Path(__file__).parent / "migrations"
        self.history_file = self.config_dir / ".migration_history.json"
        
        # Ensure directories exist
        self.backup_dir.mkdir(exist_ok=True)
        self.migration_dir.mkdir(exist_ok=True)
        
        # Load migration history
        self.history = self._load_migration_history()
        
        # Define migration plans
        self.migration_plans = self._initialize_migration_plans()
    
    def _load_migration_history(self) -> List[Dict[str, Any]]:
        """Load migration history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load migration history: {e}")
        return []
    
    def _save_migration_history(self, migration_result: MigrationResult):
        """Save migration result to history."""
        self.history.append(asdict(migration_result))
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save migration history: {e}")
    
    def _initialize_migration_plans(self) -> Dict[Tuple[str, str], MigrationPlan]:
        """Initialize all migration plans."""
        plans = {}
        
        # Example migration from 0.1.0 to 0.2.0
        plans[("0.1.0", "0.2.0")] = MigrationPlan(
            from_version="0.1.0",
            to_version="0.2.0",
            description="Migrate to improved security configuration",
            breaking_changes=[
                "PASSWORD_POLICY renamed to PASSWORD_MIN_LENGTH",
                "CORS_ALLOWED_ORIGINS renamed to CORS_ORIGINS",
                "JWT_EXPIRY_MINUTES renamed to ACCESS_TOKEN_EXPIRE_MINUTES"
            ],
            rules=[
                MigrationRule(
                    rule_type=MigrationType.RENAME_FIELD,
                    source_field="PASSWORD_POLICY",
                    target_field="PASSWORD_MIN_LENGTH",
                    description="Rename password policy field to be more specific"
                ),
                MigrationRule(
                    rule_type=MigrationType.RENAME_FIELD,
                    source_field="CORS_ALLOWED_ORIGINS",
                    target_field="CORS_ORIGINS",
                    description="Standardize CORS configuration naming"
                ),
                MigrationRule(
                    rule_type=MigrationType.RENAME_FIELD,
                    source_field="JWT_EXPIRY_MINUTES",
                    target_field="ACCESS_TOKEN_EXPIRE_MINUTES",
                    description="More specific JWT token naming"
                ),
                MigrationRule(
                    rule_type=MigrationType.ADD_FIELD,
                    target_field="REFRESH_TOKEN_EXPIRE_DAYS",
                    default_value="7",
                    description="Add refresh token expiry configuration"
                ),
                MigrationRule(
                    rule_type=MigrationType.ADD_FIELD,
                    target_field="CSRF_PROTECTION_ENABLED",
                    default_value="true",
                    description="Enable CSRF protection by default",
                    environments=["staging", "production"]
                ),
                MigrationRule(
                    rule_type=MigrationType.CONDITIONAL_UPDATE,
                    source_field="ENVIRONMENT",
                    condition="value == 'prod'",
                    transformation="'production'",
                    description="Standardize environment naming"
                )
            ]
        )
        
        # Migration from 0.2.0 to 0.3.0
        plans[("0.2.0", "0.3.0")] = MigrationPlan(
            from_version="0.2.0",
            to_version="0.3.0",
            description="Add rate limiting and audit logging configuration",
            breaking_changes=[
                "REDIS_URL format changed to include database number",
                "LOG_LEVEL now required for production environments"
            ],
            rules=[
                MigrationRule(
                    rule_type=MigrationType.TRANSFORM_VALUE,
                    source_field="REDIS_URL",
                    target_field="REDIS_URL",
                    transformation="add_redis_db_to_url(value)",
                    description="Add database number to Redis URL if missing"
                ),
                MigrationRule(
                    rule_type=MigrationType.ADD_FIELD,
                    target_field="RATE_LIMITING_ENABLED",
                    default_value="true",
                    description="Enable rate limiting by default"
                ),
                MigrationRule(
                    rule_type=MigrationType.ADD_FIELD,
                    target_field="LOGIN_RATE_LIMIT_ATTEMPTS",
                    default_value="5",
                    description="Set default login rate limit"
                ),
                MigrationRule(
                    rule_type=MigrationType.ADD_FIELD,
                    target_field="LOGIN_RATE_LIMIT_WINDOW_MINUTES",
                    default_value="15",
                    description="Set default login rate limit window"
                ),
                MigrationRule(
                    rule_type=MigrationType.SPLIT_FIELD,
                    source_field="DB_URL",
                    target_fields=["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"],
                    transformation="parse_database_url(value)",
                    description="Split database URL into individual components for better configuration"
                )
            ]
        )
        
        return plans
    
    def detect_current_version(self) -> Optional[str]:
        """Detect the current configuration version."""
        # Check if there's a version file
        version_file = self.config_dir / ".config_version"
        if version_file.exists():
            try:
                return version_file.read_text().strip()
            except Exception:
                pass
        
        # Check migration history for last successful migration
        if self.history:
            for entry in reversed(self.history):
                if entry.get("success"):
                    return entry.get("to_version")
        
        # Try to infer from .env file content
        env_file = self.config_dir / ".env"
        if env_file.exists():
            content = env_file.read_text()
            
            # Version 0.3.0+ has rate limiting config
            if "RATE_LIMITING_ENABLED" in content:
                return "0.3.0"
            
            # Version 0.2.0+ has CSRF protection and standardized naming
            if "CSRF_PROTECTION_ENABLED" in content and "ACCESS_TOKEN_EXPIRE_MINUTES" in content:
                return "0.2.0"
            
            # Version 0.1.0 has old field names
            if "PASSWORD_POLICY" in content or "CORS_ALLOWED_ORIGINS" in content:
                return "0.1.0"
        
        # Default to latest if we can't detect
        return None
    
    def get_migration_path(self, from_version: str, to_version: str) -> List[MigrationPlan]:
        """Get the migration path from one version to another."""
        # For simplicity, assume direct migration paths
        # In a real system, you'd implement graph traversal for multi-step migrations
        
        if (from_version, to_version) in self.migration_plans:
            return [self.migration_plans[(from_version, to_version)]]
        
        # Try to find a path through intermediate versions
        available_versions = ["0.1.0", "0.2.0", "0.3.0"]
        
        path = []
        current = from_version
        
        while current != to_version:
            next_version = None
            
            # Find next step in migration path
            for version in available_versions:
                if (current, version) in self.migration_plans:
                    if version == to_version or available_versions.index(version) < available_versions.index(to_version):
                        next_version = version
                        break
            
            if next_version is None:
                raise ValueError(f"No migration path found from {from_version} to {to_version}")
            
            path.append(self.migration_plans[(current, next_version)])
            current = next_version
        
        return path
    
    def create_backup(self, reason: str = "migration") -> str:
        """Create a backup of current configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"config_backup_{reason}_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        # Create backup directory
        backup_path.mkdir(exist_ok=True)
        
        # Copy configuration files
        files_to_backup = [".env", ".env.local", ".env.example"]
        
        for filename in files_to_backup:
            source_file = self.config_dir / filename
            if source_file.exists():
                shutil.copy2(source_file, backup_path / filename)
        
        # Save backup metadata
        metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "files": [f for f in files_to_backup if (self.config_dir / f).exists()]
        }
        
        with open(backup_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return str(backup_path)
    
    def load_env_file(self, file_path: Path) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}
        
        if not file_path.exists():
            return env_vars
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        env_vars[key] = value
        
        except Exception as e:
            print(f"Warning: Could not load {file_path}: {e}")
        
        return env_vars
    
    def save_env_file(self, file_path: Path, env_vars: Dict[str, str], preserve_comments: bool = True):
        """Save environment variables to .env file."""
        lines = []
        
        # If preserving comments, read existing file first
        if preserve_comments and file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    original_lines = f.readlines()
                
                # Process existing lines
                processed_keys = set()
                for line in original_lines:
                    stripped = line.strip()
                    
                    # Keep comments and empty lines
                    if not stripped or stripped.startswith('#'):
                        lines.append(line.rstrip() + '\n')
                        continue
                    
                    # Update existing variables
                    if '=' in stripped:
                        key = stripped.split('=', 1)[0].strip()
                        if key in env_vars:
                            lines.append(f"{key}={env_vars[key]}\n")
                            processed_keys.add(key)
                        else:
                            # Keep line as-is if not in new vars
                            lines.append(line.rstrip() + '\n')
                
                # Add new variables that weren't in the original file
                for key, value in env_vars.items():
                    if key not in processed_keys:
                        lines.append(f"{key}={value}\n")
            
            except Exception as e:
                print(f"Warning: Could not preserve comments from {file_path}: {e}")
                # Fall back to simple save
                preserve_comments = False
        
        if not preserve_comments:
            # Simple save without preserving structure
            for key, value in env_vars.items():
                lines.append(f"{key}={value}\n")
        
        # Write to file
        try:
            with open(file_path, 'w') as f:
                f.writelines(lines)
        except Exception as e:
            raise Exception(f"Could not save {file_path}: {e}")
    
    def apply_migration_rule(self, rule: MigrationRule, env_vars: Dict[str, str], environment: str) -> Tuple[Dict[str, str], List[str], List[str]]:
        """Apply a single migration rule to environment variables."""
        warnings = []
        errors = []
        result_vars = env_vars.copy()
        
        # Check if rule applies to this environment
        if rule.environments and environment not in rule.environments:
            return result_vars, warnings, errors
        
        try:
            if rule.rule_type == MigrationType.RENAME_FIELD:
                if rule.source_field in result_vars:
                    result_vars[rule.target_field] = result_vars[rule.source_field]
                    del result_vars[rule.source_field]
                else:
                    warnings.append(f"Source field {rule.source_field} not found for rename")
            
            elif rule.rule_type == MigrationType.ADD_FIELD:
                if rule.target_field not in result_vars:
                    result_vars[rule.target_field] = str(rule.default_value)
                else:
                    warnings.append(f"Field {rule.target_field} already exists, skipping add")
            
            elif rule.rule_type == MigrationType.REMOVE_FIELD:
                if rule.source_field in result_vars:
                    del result_vars[rule.source_field]
            
            elif rule.rule_type == MigrationType.TRANSFORM_VALUE:
                if rule.source_field in result_vars:
                    old_value = result_vars[rule.source_field]
                    new_value = self._apply_transformation(rule.transformation, old_value)
                    result_vars[rule.target_field or rule.source_field] = new_value
                else:
                    warnings.append(f"Source field {rule.source_field} not found for transformation")
            
            elif rule.rule_type == MigrationType.CONDITIONAL_UPDATE:
                if rule.source_field in result_vars:
                    current_value = result_vars[rule.source_field]
                    if self._evaluate_condition(rule.condition, current_value):
                        new_value = self._apply_transformation(rule.transformation, current_value)
                        result_vars[rule.source_field] = new_value
            
            elif rule.rule_type == MigrationType.SPLIT_FIELD:
                if rule.source_field in result_vars:
                    source_value = result_vars[rule.source_field]
                    split_values = self._apply_transformation(rule.transformation, source_value)
                    
                    if isinstance(split_values, dict) and rule.target_fields:
                        for target_field in rule.target_fields:
                            if target_field in split_values:
                                result_vars[target_field] = split_values[target_field]
                    
                    # Remove source field
                    del result_vars[rule.source_field]
            
            elif rule.rule_type == MigrationType.MERGE_FIELDS:
                if rule.source_fields and all(field in result_vars for field in rule.source_fields):
                    source_values = {field: result_vars[field] for field in rule.source_fields}
                    merged_value = self._apply_transformation(rule.transformation, source_values)
                    result_vars[rule.target_field] = merged_value
                    
                    # Remove source fields
                    for field in rule.source_fields:
                        del result_vars[field]
        
        except Exception as e:
            errors.append(f"Error applying rule {rule.rule_type.value}: {e}")
        
        return result_vars, warnings, errors
    
    def _apply_transformation(self, transformation: str, value: Any) -> str:
        """Apply a transformation to a value."""
        if transformation == "add_redis_db_to_url(value)":
            return self._add_redis_db_to_url(str(value))
        elif transformation == "parse_database_url(value)":
            return self._parse_database_url(str(value))
        elif transformation.startswith("'") and transformation.endswith("'"):
            return transformation[1:-1]  # String literal
        else:
            # Evaluate as Python expression (be careful in production!)
            try:
                # Create safe evaluation context
                context = {"value": value}
                return str(eval(transformation, {"__builtins__": {}}, context))
            except Exception as e:
                raise ValueError(f"Could not evaluate transformation '{transformation}': {e}")
    
    def _evaluate_condition(self, condition: str, value: Any) -> bool:
        """Evaluate a condition against a value."""
        try:
            context = {"value": value}
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False
    
    def _add_redis_db_to_url(self, redis_url: str) -> str:
        """Add database number to Redis URL if missing."""
        if "/0" not in redis_url and not redis_url.endswith("/"):
            if redis_url.count("/") >= 2:
                return redis_url
            else:
                return redis_url + "/0"
        return redis_url
    
    def _parse_database_url(self, db_url: str) -> Dict[str, str]:
        """Parse database URL into components."""
        import urllib.parse
        
        parsed = urllib.parse.urlparse(db_url)
        
        return {
            "DB_HOST": parsed.hostname or "localhost",
            "DB_PORT": str(parsed.port or 5432),
            "DB_NAME": parsed.path[1:] if parsed.path else "postgres",
            "DB_USER": parsed.username or "postgres",
            "DB_PASSWORD": parsed.password or ""
        }
    
    def migrate(self, from_version: str, to_version: str, dry_run: bool = False) -> MigrationResult:
        """Perform migration from one version to another."""
        print(f"Migrating configuration from {from_version} to {to_version}")
        
        # Get migration path
        try:
            migration_plans = self.get_migration_path(from_version, to_version)
        except ValueError as e:
            return MigrationResult(
                success=False,
                from_version=from_version,
                to_version=to_version,
                migrated_fields=[],
                warnings=[],
                errors=[str(e)]
            )
        
        # Create backup
        backup_path = None
        if not dry_run:
            backup_path = self.create_backup(f"migration_{from_version}_to_{to_version}")
            print(f"Created backup at: {backup_path}")
        
        # Load current configuration
        env_file = self.config_dir / ".env"
        env_vars = self.load_env_file(env_file)
        
        # Detect environment
        environment = env_vars.get("ENVIRONMENT", "development")
        
        all_warnings = []
        all_errors = []
        migrated_fields = []
        
        # Apply each migration plan
        for plan in migration_plans:
            print(f"Applying migration plan: {plan.description}")
            
            if plan.breaking_changes:
                print("Breaking changes in this migration:")
                for change in plan.breaking_changes:
                    print(f"  - {change}")
            
            # Apply each rule in the plan
            for rule in plan.rules:
                print(f"  Applying rule: {rule.description}")
                
                new_vars, warnings, errors = self.apply_migration_rule(rule, env_vars, environment)
                
                if warnings:
                    all_warnings.extend(warnings)
                    for warning in warnings:
                        print(f"    Warning: {warning}")
                
                if errors:
                    all_errors.extend(errors)
                    for error in errors:
                        print(f"    Error: {error}")
                else:
                    # Track successful migrations
                    if rule.rule_type in [MigrationType.RENAME_FIELD, MigrationType.ADD_FIELD, 
                                        MigrationType.TRANSFORM_VALUE, MigrationType.CONDITIONAL_UPDATE]:
                        field = rule.target_field or rule.source_field
                        if field:
                            migrated_fields.append(field)
                    
                    env_vars = new_vars
        
        # Save migrated configuration
        if not dry_run and not all_errors:
            try:
                self.save_env_file(env_file, env_vars)
                
                # Save version file
                version_file = self.config_dir / ".config_version"
                version_file.write_text(to_version)
                
                print(f"Migration completed successfully!")
                print(f"Configuration saved to: {env_file}")
                
            except Exception as e:
                all_errors.append(f"Could not save migrated configuration: {e}")
        
        # Create migration result
        result = MigrationResult(
            success=len(all_errors) == 0,
            from_version=from_version,
            to_version=to_version,
            migrated_fields=migrated_fields,
            warnings=all_warnings,
            errors=all_errors,
            backup_path=backup_path
        )
        
        # Save to history
        if not dry_run:
            self._save_migration_history(result)
        
        return result
    
    def rollback(self, backup_path: Optional[str] = None) -> bool:
        """Rollback to a previous configuration."""
        if backup_path is None:
            # Find most recent backup
            backups = list(self.backup_dir.glob("config_backup_*"))
            if not backups:
                print("No backups found to rollback to")
                return False
            
            # Sort by modification time
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            backup_path = str(backups[0])
        
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            print(f"Backup directory not found: {backup_path}")
            return False
        
        print(f"Rolling back to backup: {backup_path}")
        
        # Restore configuration files
        for backup_file in backup_dir.glob(".*env*"):
            target_file = self.config_dir / backup_file.name
            try:
                shutil.copy2(backup_file, target_file)
                print(f"Restored: {target_file}")
            except Exception as e:
                print(f"Error restoring {backup_file}: {e}")
                return False
        
        # Remove version file to force re-detection
        version_file = self.config_dir / ".config_version"
        if version_file.exists():
            version_file.unlink()
        
        print("Rollback completed successfully!")
        return True
    
    def list_migrations(self) -> None:
        """List available migration plans."""
        print("Available migration plans:")
        print()
        
        for (from_ver, to_ver), plan in self.migration_plans.items():
            print(f"Migration: {from_ver} → {to_ver}")
            print(f"  Description: {plan.description}")
            print(f"  Rules: {len(plan.rules)}")
            if plan.breaking_changes:
                print(f"  Breaking changes: {len(plan.breaking_changes)}")
            print()
    
    def validate_configuration(self) -> bool:
        """Validate current configuration."""
        try:
            settings = Settings()
            print("Configuration validation: PASSED")
            print(f"Environment: {settings.environment}")
            print(f"App version: {settings.app_version}")
            return True
        except Exception as e:
            print(f"Configuration validation: FAILED")
            print(f"Error: {e}")
            return False


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Configuration Migration Tool")
    parser.add_argument("--from-version", help="Source version to migrate from")
    parser.add_argument("--to-version", help="Target version to migrate to")
    parser.add_argument("--auto-detect", action="store_true", 
                       help="Auto-detect current version and migrate to latest")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be migrated without making changes")
    parser.add_argument("--rollback", action="store_true", 
                       help="Rollback to most recent backup")
    parser.add_argument("--backup-path", help="Specific backup path for rollback")
    parser.add_argument("--list-migrations", action="store_true", 
                       help="List available migration plans")
    parser.add_argument("--validate", action="store_true", 
                       help="Validate current configuration")
    parser.add_argument("--config-dir", default=".", 
                       help="Configuration directory (default: current directory)")
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = ConfigMigrator(args.config_dir)
    
    if args.list_migrations:
        migrator.list_migrations()
        return
    
    if args.validate:
        is_valid = migrator.validate_configuration()
        sys.exit(0 if is_valid else 1)
    
    if args.rollback:
        success = migrator.rollback(args.backup_path)
        sys.exit(0 if success else 1)
    
    if args.auto_detect:
        current_version = migrator.detect_current_version()
        if current_version is None:
            print("Could not detect current version. Please specify --from-version")
            sys.exit(1)
        
        latest_version = "0.3.0"  # Update this as new versions are added
        
        if current_version == latest_version:
            print(f"Configuration is already at latest version ({latest_version})")
            sys.exit(0)
        
        print(f"Detected current version: {current_version}")
        print(f"Migrating to latest version: {latest_version}")
        
        result = migrator.migrate(current_version, latest_version, args.dry_run)
    
    elif args.from_version and args.to_version:
        result = migrator.migrate(args.from_version, args.to_version, args.dry_run)
    
    else:
        print("Error: Must specify either --auto-detect or both --from-version and --to-version")
        parser.print_help()
        sys.exit(1)
    
    # Print results
    print("\nMigration Results:")
    print(f"Success: {result.success}")
    print(f"Migrated fields: {', '.join(result.migrated_fields) if result.migrated_fields else 'None'}")
    
    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")
    
    if result.backup_path:
        print(f"\nBackup created at: {result.backup_path}")
    
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()