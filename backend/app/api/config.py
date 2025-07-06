"""
Configuration Management API Endpoints

Provides controlled access to configuration with RBAC enforcement.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query, status
from pydantic import BaseModel, Field

from app.api.auth import get_current_user, get_current_admin_user
from app.models.user import User
from app.services.config_access_service import get_config_access_service
from app.core.config_rbac_compat import ConfigRole, ConfigPermission
from app.core.config import get_settings


router = APIRouter(
    prefix="/api/v1/config",
    tags=["Configuration"]
)


class ConfigFieldUpdate(BaseModel):
    """Model for updating a configuration field."""
    field_name: str = Field(..., description="Configuration field name")
    value: Any = Field(..., description="New value for the field")


class ConfigBulkUpdate(BaseModel):
    """Model for bulk configuration updates."""
    updates: Dict[str, Any] = Field(..., description="Dictionary of field updates")


class RoleAssignment(BaseModel):
    """Model for role assignment."""
    user_id: str = Field(..., description="Target user ID")
    role: str = Field(..., description="Configuration role to assign")


class CustomRoleCreate(BaseModel):
    """Model for creating custom roles."""
    name: str = Field(..., description="Role name")
    description: str = Field(..., description="Role description")
    field_permissions: List[Dict[str, Any]] = Field(..., description="Field permission definitions")
    inherits_from: Optional[List[str]] = Field(None, description="Parent roles to inherit from")


@router.get("/fields", response_model=Dict[str, Any])
async def get_configuration(
    current_user: User = Depends(get_current_user),
    fields: Optional[List[str]] = Query(None, description="Specific fields to retrieve")
) -> Dict[str, Any]:
    """
    Get configuration fields based on user permissions.
    
    Returns only fields the user has read access to.
    """
    service = get_config_access_service()
    
    try:
        # Get user's configuration proxy
        config_proxy = service.get_user_config(current_user)
        
        if fields:
            # Get specific fields
            result = {}
            for field in fields:
                try:
                    result[field] = service.read_config_field(current_user, field)
                except (PermissionError, ValueError):
                    # Skip fields user can't access or don't exist
                    pass
            return result
        else:
            # Get all accessible fields
            return config_proxy.get_safe_config()
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration: {str(e)}"
        )


@router.get("/field/{field_name}", response_model=Dict[str, Any])
async def get_config_field(
    field_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get a specific configuration field.
    
    Requires read permission for the field.
    """
    service = get_config_access_service()
    
    try:
        value = service.read_config_field(current_user, field_name)
        return {
            "field": field_name,
            "value": value,
            "environment": get_settings().environment
        }
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to field '{field_name}'"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/field", response_model=Dict[str, Any])
async def update_config_field(
    update: ConfigFieldUpdate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update a configuration field.
    
    Requires write permission for the field.
    """
    service = get_config_access_service()
    settings = get_settings()
    
    # Production safety check
    if settings.is_production and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can modify configuration in production"
        )
    
    try:
        new_value = service.write_config_field(
            current_user,
            update.field_name,
            update.value
        )
        
        return {
            "field": update.field_name,
            "value": new_value,
            "status": "updated",
            "environment": settings.environment
        }
        
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to modify field '{update.field_name}'"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update field: {str(e)}"
        )


@router.post("/validate", response_model=Dict[str, Any])
async def validate_config_updates(
    updates: ConfigBulkUpdate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Validate configuration updates without applying them.
    
    Checks permissions and validation rules.
    """
    service = get_config_access_service()
    
    try:
        validation_result = service.validate_config_for_user(
            current_user,
            updates.updates
        )
        
        return {
            "status": "valid" if validation_result["valid"] else "invalid",
            "result": validation_result,
            "environment": get_settings().environment
        }
        
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks validate permission"
        )


@router.get("/export", response_model=Dict[str, Any])
async def export_configuration(
    current_user: User = Depends(get_current_user),
    include_sensitive: bool = Query(False, description="Include sensitive values (requires admin)")
) -> Dict[str, Any]:
    """
    Export configuration based on user permissions.
    
    Sensitive values are redacted unless user is admin and requests them.
    """
    service = get_config_access_service()
    settings = get_settings()
    
    # Check sensitive export permission
    if include_sensitive and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can export sensitive configuration"
        )
    
    try:
        config = service.export_config_for_user(current_user, include_sensitive)
        
        return {
            "configuration": config,
            "environment": settings.environment,
            "exported_fields": len(config),
            "include_sensitive": include_sensitive
        }
        
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks export permission"
        )


@router.get("/permissions", response_model=Dict[str, Any])
async def get_my_permissions(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current user's configuration permissions.
    
    Shows roles and accessible fields.
    """
    service = get_config_access_service()
    
    permissions = service.get_user_permissions(current_user)
    return {
        "status": "success",
        "permissions": permissions
    }


@router.post("/rotate/{field_name}", response_model=Dict[str, Any])
async def rotate_secret(
    field_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Rotate a secret configuration field.
    
    Requires rotate permission for the field.
    """
    service = get_config_access_service()
    settings = get_settings()
    
    # Production safety check
    if settings.is_production and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can rotate secrets in production"
        )
    
    try:
        success = service.rotate_secret_for_user(current_user, field_name)
        
        return {
            "field": field_name,
            "status": "rotated" if success else "failed",
            "environment": settings.environment,
            "message": f"Secret rotation initiated for {field_name}"
        }
        
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to rotate field '{field_name}'"
        )


# Admin-only endpoints

@router.post("/roles/assign", response_model=Dict[str, Any])
async def assign_role(
    assignment: RoleAssignment,
    admin_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Assign a configuration role to a user.
    
    Admin access required.
    """
    service = get_config_access_service()
    
    try:
        # Validate role
        role = ConfigRole(assignment.role)
        
        # Assign role
        service.assign_config_role(admin_user, assignment.user_id, role)
        
        return {
            "status": "success",
            "user_id": assignment.user_id,
            "role": role.value,
            "action": "assigned"
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {assignment.role}"
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/roles/revoke", response_model=Dict[str, Any])
async def revoke_role(
    assignment: RoleAssignment,
    admin_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Revoke a configuration role from a user.
    
    Admin access required.
    """
    service = get_config_access_service()
    
    try:
        # Validate role
        role = ConfigRole(assignment.role)
        
        # Revoke role
        service.revoke_config_role(admin_user, assignment.user_id, role)
        
        return {
            "status": "success",
            "user_id": assignment.user_id,
            "role": role.value,
            "action": "revoked"
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {assignment.role}"
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/roles/custom", response_model=Dict[str, Any])
async def create_custom_role(
    role_data: CustomRoleCreate,
    admin_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Create a custom configuration role.
    
    Super admin access required.
    """
    service = get_config_access_service()
    
    try:
        service.create_custom_role(
            admin_user,
            role_data.name,
            role_data.description,
            role_data.field_permissions,
            role_data.inherits_from
        )
        
        return {
            "status": "success",
            "role": role_data.name,
            "description": role_data.description,
            "action": "created"
        }
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create role: {str(e)}"
        )


@router.get("/roles/available", response_model=Dict[str, Any])
async def get_available_roles(
    admin_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get list of available configuration roles.
    
    Admin access required.
    """
    # Get all available roles
    roles = [
        {
            "name": role.value,
            "description": f"Pre-defined {role.value} role"
        }
        for role in ConfigRole
    ]
    
    return {
        "status": "success",
        "roles": roles,
        "total": len(roles)
    }