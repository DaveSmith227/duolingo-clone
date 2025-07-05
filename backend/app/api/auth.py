"""
Main authentication router that imports the modular auth system.
This file exists for backward compatibility.
"""
from app.api.auth import auth_router

# Export the router for backward compatibility
router = auth_router

__all__ = ["router"]