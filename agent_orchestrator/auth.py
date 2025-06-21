"""
Authentication module for Agent Orchestrator Service.

This module provides API key-based authentication for securing agent registration
and management endpoints. It includes:
- API key validation and management
- Authentication middleware
- Security utilities for key generation and hashing
- Dependency injection for authentication

Author: Agent Orchestrator Team
Version: 1.0.0
"""

import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import HTTPException, Security, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import logging

from .config import Config

logger = logging.getLogger(__name__)

# Security scheme for API key authentication
security = HTTPBearer(scheme_name="API Key Authentication")


class APIKeyInfo(BaseModel):
    """Information about an API key."""
    key_id: str = Field(..., description="Unique identifier for the API key")
    name: str = Field(..., description="Human-readable name for the API key")
    permissions: List[str] = Field(default_factory=list, description="List of permissions")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Expiration time (None for no expiration)")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    is_active: bool = Field(True, description="Whether the key is active")
    rate_limit: int = Field(100, description="Requests per minute allowed")
    allowed_endpoints: List[str] = Field(default_factory=list, description="Allowed endpoint patterns")


class AuthenticationError(HTTPException):
    """Custom authentication error."""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(HTTPException):
    """Custom authorization error."""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class APIKeyManager:
    """Manages API keys for authentication."""
    
    def __init__(self, config: Config):
        self.config = config
        self._keys: Dict[str, APIKeyInfo] = {}
        self._key_hashes: Dict[str, str] = {}  # hashed_key -> key_id
        self._usage_tracker: Dict[str, List[datetime]] = {}
        
        # Initialize with master API key if configured
        if config.api_key:
            self._init_master_key()
    
    def _init_master_key(self):
        """Initialize the master API key from configuration."""
        master_key = self.config.api_key
        key_id = "master_key"
        
        # Hash the master key for secure storage
        key_hash = self._hash_key(master_key)
        
        # Create master key info
        master_key_info = APIKeyInfo(
            key_id=key_id,
            name="Master API Key",
            permissions=["*"],  # Full permissions
            created_at=datetime.utcnow(),
            expires_at=None,  # Never expires
            is_active=True,
            rate_limit=1000,  # Higher rate limit for master key
            allowed_endpoints=["*"]  # All endpoints
        )
        
        self._keys[key_id] = master_key_info
        self._key_hashes[key_hash] = key_id
        self._usage_tracker[key_id] = []
        
        logger.info("Master API key initialized from configuration")
    
    def generate_api_key(self) -> str:
        """Generate a new secure API key."""
        # Generate a 32-byte random key and encode as hex
        return secrets.token_hex(32)
    
    def _hash_key(self, key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def create_key(
        self,
        name: str,
        permissions: List[str] = None,
        expires_in_days: Optional[int] = None,
        rate_limit: int = 100,
        allowed_endpoints: List[str] = None
    ) -> tuple[str, APIKeyInfo]:
        """
        Create a new API key.
        
        Args:
            name: Human-readable name for the key
            permissions: List of permissions (default: ["agent:register"])
            expires_in_days: Days until expiration (None for no expiration)
            rate_limit: Requests per minute allowed
            allowed_endpoints: Allowed endpoint patterns
            
        Returns:
            Tuple of (api_key, key_info)
        """
        api_key = self.generate_api_key()
        key_id = f"key_{secrets.token_hex(8)}"
        key_hash = self._hash_key(api_key)
        
        # Set default permissions if not provided
        if permissions is None:
            permissions = ["agent:register", "agent:read"]
        
        # Set default allowed endpoints if not provided
        if allowed_endpoints is None:
            allowed_endpoints = ["/api/v1/agents/*", "/api/v1/health"]
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        key_info = APIKeyInfo(
            key_id=key_id,
            name=name,
            permissions=permissions,
            expires_at=expires_at,
            is_active=True,
            rate_limit=rate_limit,
            allowed_endpoints=allowed_endpoints
        )
        
        self._keys[key_id] = key_info
        self._key_hashes[key_hash] = key_id
        self._usage_tracker[key_id] = []
        
        logger.info(f"Created new API key: {name} (ID: {key_id})")
        return api_key, key_info
    
    def validate_key(self, api_key: str) -> Optional[APIKeyInfo]:
        """
        Validate an API key and return key info if valid.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            APIKeyInfo if valid, None otherwise
        """
        try:
            key_hash = self._hash_key(api_key)
            key_id = self._key_hashes.get(key_hash)
            
            if not key_id:
                return None
            
            key_info = self._keys.get(key_id)
            if not key_info:
                return None
            
            # Check if key is active
            if not key_info.is_active:
                logger.warning(f"Attempt to use inactive API key: {key_id}")
                return None
            
            # Check expiration
            if key_info.expires_at and datetime.utcnow() > key_info.expires_at:
                logger.warning(f"Attempt to use expired API key: {key_id}")
                return None
            
            # Update last used timestamp
            key_info.last_used = datetime.utcnow()
            
            # Track usage for rate limiting
            now = datetime.utcnow()
            usage_history = self._usage_tracker[key_id]
            
            # Remove entries older than 1 minute
            cutoff = now - timedelta(minutes=1)
            usage_history[:] = [timestamp for timestamp in usage_history if timestamp > cutoff]
            
            # Check rate limit
            if len(usage_history) >= key_info.rate_limit:
                logger.warning(f"Rate limit exceeded for API key: {key_id}")
                return None
            
            # Record this usage
            usage_history.append(now)
            
            return key_info
            
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None
    
    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: The key ID to revoke
            
        Returns:
            True if successfully revoked, False otherwise
        """
        if key_id in self._keys:
            self._keys[key_id].is_active = False
            logger.info(f"Revoked API key: {key_id}")
            return True
        return False
    
    def list_keys(self) -> List[APIKeyInfo]:
        """List all API keys (without sensitive data)."""
        return list(self._keys.values())
    
    def get_key_info(self, key_id: str) -> Optional[APIKeyInfo]:
        """Get information about a specific API key."""
        return self._keys.get(key_id)


# Global API key manager instance
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """Get the global API key manager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        from .config import get_config
        config = get_config()
        _api_key_manager = APIKeyManager(config)
    return _api_key_manager


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> APIKeyInfo:
    """
    Verify API key from Authorization header.
    
    This dependency can be used to protect endpoints that require authentication.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        APIKeyInfo for the validated key
        
    Raises:
        AuthenticationError: If authentication fails
    """
    if not credentials or not credentials.credentials:
        raise AuthenticationError("API key required")
    
    api_key_manager = get_api_key_manager()
    key_info = api_key_manager.validate_key(credentials.credentials)
    
    if not key_info:
        raise AuthenticationError("Invalid or expired API key")
    
    return key_info


async def verify_permission(
    required_permission: str,
    key_info: APIKeyInfo = Depends(verify_api_key)
) -> APIKeyInfo:
    """
    Verify that the API key has a specific permission.
    
    Args:
        required_permission: The permission to check for
        key_info: The validated API key info
        
    Returns:
        APIKeyInfo if permission is granted
        
    Raises:
        AuthorizationError: If permission is denied
    """
    # Check for wildcard permission
    if "*" in key_info.permissions:
        return key_info
    
    # Check for specific permission
    if required_permission in key_info.permissions:
        return key_info
    
    # Check for pattern matching (e.g., "agent:*" matches "agent:register")
    for permission in key_info.permissions:
        if permission.endswith("*") and required_permission.startswith(permission[:-1]):
            return key_info
    
    raise AuthorizationError(f"Permission '{required_permission}' required")


def require_permission(permission: str):
    """
    Decorator to require a specific permission for an endpoint.
    
    Args:
        permission: The required permission
        
    Returns:
        Dependency function
    """
    async def permission_dependency(
        key_info: APIKeyInfo = Depends(verify_api_key)
    ) -> APIKeyInfo:
        return await verify_permission(permission, key_info)
    
    return Depends(permission_dependency)


async def verify_endpoint_access(
    request: Request,
    key_info: APIKeyInfo = Depends(verify_api_key)
) -> APIKeyInfo:
    """
    Verify that the API key can access the requested endpoint.
    
    Args:
        request: The HTTP request
        key_info: The validated API key info
        
    Returns:
        APIKeyInfo if access is granted
        
    Raises:
        AuthorizationError: If access is denied
    """
    endpoint_path = request.url.path
    
    # Check for wildcard access
    if "*" in key_info.allowed_endpoints:
        return key_info
    
    # Check for specific endpoint access
    for allowed_pattern in key_info.allowed_endpoints:
        if allowed_pattern.endswith("*"):
            # Pattern matching (e.g., "/api/v1/agents/*")
            if endpoint_path.startswith(allowed_pattern[:-1]):
                return key_info
        else:
            # Exact match
            if endpoint_path == allowed_pattern:
                return key_info
    
    raise AuthorizationError(f"Access to endpoint '{endpoint_path}' denied")


# Common permission dependencies
require_agent_register = require_permission("agent:register")
require_agent_read = require_permission("agent:read")
require_agent_write = require_permission("agent:write")
require_agent_delete = require_permission("agent:delete")
require_task_create = require_permission("task:create")
require_task_read = require_permission("task:read")
require_task_write = require_permission("task:write")
require_admin = require_permission("admin")


class AuthenticationService:
    """Service class for authentication operations."""
    
    def __init__(self, api_key_manager: APIKeyManager):
        self.api_key_manager = api_key_manager
    
    async def create_service_key(
        self,
        service_name: str,
        permissions: List[str] = None,
        expires_in_days: Optional[int] = 90
    ) -> tuple[str, APIKeyInfo]:
        """
        Create an API key for a service.
        
        Args:
            service_name: Name of the service
            permissions: List of permissions
            expires_in_days: Days until expiration
            
        Returns:
            Tuple of (api_key, key_info)
        """
        if permissions is None:
            permissions = ["agent:register", "agent:read", "task:create", "task:read"]
        
        return self.api_key_manager.create_key(
            name=f"Service: {service_name}",
            permissions=permissions,
            expires_in_days=expires_in_days,
            rate_limit=500,
            allowed_endpoints=["*"]
        )
    
    async def create_user_key(
        self,
        user_name: str,
        permissions: List[str] = None,
        expires_in_days: Optional[int] = 30
    ) -> tuple[str, APIKeyInfo]:
        """
        Create an API key for a user.
        
        Args:
            user_name: Name of the user
            permissions: List of permissions
            expires_in_days: Days until expiration
            
        Returns:
            Tuple of (api_key, key_info)
        """
        if permissions is None:
            permissions = ["agent:read", "task:read"]
        
        return self.api_key_manager.create_key(
            name=f"User: {user_name}",
            permissions=permissions,
            expires_in_days=expires_in_days,
            rate_limit=100,
            allowed_endpoints=["/api/v1/agents", "/api/v1/tasks", "/api/v1/health"]
        )


def get_auth_service() -> AuthenticationService:
    """Get the authentication service instance."""
    api_key_manager = get_api_key_manager()
    return AuthenticationService(api_key_manager)


# Dependency for getting authentication service
def get_auth_service_dependency() -> AuthenticationService:
    """Dependency function for getting authentication service."""
    return get_auth_service()
