"""
Supabase Client Configuration

Handles Supabase client initialization and OAuth provider management
for the Duolingo clone authentication system.
"""

import logging
from typing import Optional, Dict, Any
from supabase import create_client, Client
from supabase.client import ClientOptions
from gotrue.errors import AuthError
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Supabase client wrapper for authentication and user management.
    
    Provides a singleton pattern for Supabase client access and includes
    helper methods for OAuth provider management and user operations.
    """
    
    _instance: Optional['SupabaseClient'] = None
    _client: Optional[Client] = None
    
    def __new__(cls) -> 'SupabaseClient':
        """Ensure singleton pattern for Supabase client."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Supabase client if not already initialized."""
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the Supabase client with configuration."""
        settings = get_settings()
        
        if not settings.has_supabase_config:
            logger.warning("Supabase configuration incomplete. Client will not be initialized.")
            return
        
        try:
            # Configure client options for enhanced security
            options = ClientOptions(
                auto_refresh_token=True,
                persist_session=True,
                detect_session_in_url=False,  # We handle OAuth callbacks manually
                flow_type="pkce"  # Use PKCE for enhanced security
            )
            
            self._client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_anon_key,
                options=options
            )
            
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise
    
    @property
    def client(self) -> Optional[Client]:
        """Get the Supabase client instance."""
        return self._client
    
    @property
    def auth(self):
        """Get the Supabase auth client."""
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        return self._client.auth
    
    @property
    def db(self):
        """Get the Supabase database client."""
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        return self._client.table
    
    def is_configured(self) -> bool:
        """Check if Supabase client is properly configured."""
        return self._client is not None
    
    async def sign_in_with_oauth(self, provider: str, redirect_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Initiate OAuth sign-in flow with specified provider.
        
        Args:
            provider: OAuth provider name (google, apple, facebook, tiktok)
            redirect_url: Custom redirect URL (defaults to configured OAuth callback)
            
        Returns:
            Dictionary containing OAuth URL and session information
            
        Raises:
            AuthError: If OAuth initiation fails
            RuntimeError: If client not configured
        """
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        
        settings = get_settings()
        callback_url = redirect_url or settings.oauth_callback_url
        
        try:
            response = await self.auth.sign_in_with_oauth({
                "provider": provider,
                "options": {
                    "redirect_to": callback_url,
                    "scopes": self._get_provider_scopes(provider)
                }
            })
            
            logger.info(f"OAuth sign-in initiated for provider: {provider}")
            return response
            
        except AuthError as e:
            logger.error(f"OAuth sign-in failed for provider {provider}: {str(e)}")
            raise
    
    async def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Handle OAuth callback and exchange code for session.
        
        Args:
            code: Authorization code from OAuth provider
            state: State parameter for CSRF protection
            
        Returns:
            Dictionary containing user session and profile information
            
        Raises:
            AuthError: If callback handling fails
        """
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        
        try:
            response = await self.auth.exchange_code_for_session({
                "auth_code": code,
                "code_verifier": state  # PKCE code verifier
            })
            
            logger.info("OAuth callback handled successfully")
            return response
            
        except AuthError as e:
            logger.error(f"OAuth callback handling failed: {str(e)}")
            raise
    
    async def sign_out(self) -> None:
        """Sign out current user and invalidate session."""
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        
        try:
            await self.auth.sign_out()
            logger.info("User signed out successfully")
            
        except AuthError as e:
            logger.error(f"Sign out failed: {str(e)}")
            raise
    
    async def get_user(self) -> Optional[Dict[str, Any]]:
        """
        Get current authenticated user information.
        
        Returns:
            User dictionary if authenticated, None otherwise
        """
        if not self._client:
            return None
        
        try:
            user = await self.auth.get_user()
            return user.user if user else None
            
        except AuthError:
            return None
    
    async def refresh_session(self) -> Optional[Dict[str, Any]]:
        """
        Refresh current user session.
        
        Returns:
            Refreshed session information or None if refresh fails
        """
        if not self._client:
            return None
        
        try:
            response = await self.auth.refresh_session()
            return response
            
        except AuthError as e:
            logger.error(f"Session refresh failed: {str(e)}")
            return None
    
    def _get_provider_scopes(self, provider: str) -> str:
        """
        Get appropriate scopes for OAuth provider.
        
        Args:
            provider: OAuth provider name
            
        Returns:
            Space-separated string of scopes
        """
        scopes_map = {
            "google": "openid email profile",
            "facebook": "email public_profile",
            "apple": "email name",
            "tiktok": "user.info.basic user.info.profile"
        }
        
        return scopes_map.get(provider, "openid email profile")
    
    async def create_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create user profile in application database.
        
        Args:
            user_id: Supabase user ID
            profile_data: User profile information
            
        Returns:
            Created profile data
        """
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        
        try:
            response = await self.db("profiles").insert({
                "user_id": user_id,
                **profile_data
            }).execute()
            
            logger.info(f"User profile created for user: {user_id}")
            return response.data[0] if response.data else {}
            
        except Exception as e:
            logger.error(f"Failed to create user profile: {str(e)}")
            raise
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile from application database.
        
        Args:
            user_id: Supabase user ID
            
        Returns:
            User profile data or None if not found
        """
        if not self._client:
            return None
        
        try:
            response = await self.db("profiles").select("*").eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Failed to get user profile: {str(e)}")
            return None


# Global Supabase client instance
_supabase_client = None


def get_supabase_client() -> SupabaseClient:
    """
    Get global Supabase client instance.
    
    Returns:
        Singleton SupabaseClient instance
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client


def init_supabase() -> None:
    """
    Initialize Supabase client on application startup.
    
    This function should be called during FastAPI application startup
    to ensure Supabase client is properly configured.
    """
    client = get_supabase_client()
    if client.is_configured():
        logger.info("Supabase client configuration verified")
    else:
        logger.warning("Supabase client configuration incomplete")