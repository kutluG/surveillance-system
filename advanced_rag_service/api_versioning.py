"""
API Versioning Strategy for Advanced RAG Service

This module provides a comprehensive API versioning system with:
- Consistent versioning across all endpoints
- Support for multiple API versions simultaneously
- Version deprecation and sunset handling
- API documentation per version
- Backward compatibility management
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
import re

logger = logging.getLogger(__name__)

class APIVersion(str, Enum):
    """Supported API versions"""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"
    
    @classmethod
    def get_latest(cls) -> 'APIVersion':
        """Get the latest API version"""
        return cls.V1_1  # Update this as new versions are released
    
    @classmethod
    def get_all_versions(cls) -> List['APIVersion']:
        """Get all supported API versions"""
        return list(cls)
    
    @classmethod
    def from_string(cls, version_str: str) -> Optional['APIVersion']:
        """Parse version string to APIVersion"""
        # Handle common formats: "v1", "1.0", "v1.0", etc.
        cleaned = version_str.lower().strip('v').strip()
        for version in cls:
            if version.value == cleaned or f"v{version.value}" == version_str.lower():
                return version
        return None

@dataclass
class APIVersionInfo:
    """Information about an API version"""
    version: APIVersion
    status: str  # "active", "deprecated", "sunset"
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    changelog: List[str] = None
    breaking_changes: List[str] = None
    
    def __post_init__(self):
        if self.changelog is None:
            self.changelog = []
        if self.breaking_changes is None:
            self.breaking_changes = []
    
    @property
    def is_active(self) -> bool:
        """Check if version is active"""
        return self.status == "active"
    
    @property
    def is_deprecated(self) -> bool:
        """Check if version is deprecated"""
        return self.status == "deprecated"
    
    @property
    def is_sunset(self) -> bool:
        """Check if version is sunset (no longer supported)"""
        return self.status == "sunset"
    
    @property
    def days_until_sunset(self) -> Optional[int]:
        """Days until version sunset"""
        if self.sunset_date:
            delta = self.sunset_date - datetime.utcnow()
            return max(0, delta.days)
        return None

class APIVersionManager:
    """Manages API versions, deprecation, and routing"""
    
    def __init__(self):
        self.versions: Dict[APIVersion, APIVersionInfo] = {}
        self._initialize_versions()
    
    def _initialize_versions(self):
        """Initialize version information"""
        # Version 1.0 - Original API
        self.versions[APIVersion.V1_0] = APIVersionInfo(
            version=APIVersion.V1_0,
            status="deprecated",
            release_date=datetime(2025, 1, 1),
            deprecation_date=datetime(2025, 6, 1),
            sunset_date=datetime(2025, 12, 31),
            changelog=[
                "Initial release",
                "Basic RAG functionality",
                "Evidence analysis endpoints"
            ]
        )
        
        # Version 1.1 - Current stable
        self.versions[APIVersion.V1_1] = APIVersionInfo(
            version=APIVersion.V1_1,
            status="active",
            release_date=datetime(2025, 6, 1),
            changelog=[
                "Enhanced error handling",
                "Dependency injection support",
                "Configuration management",
                "Improved temporal analysis",
                "Health check endpoints",
                "Performance optimizations"
            ]
        )
        
        # Version 2.0 - Future version (planned)
        self.versions[APIVersion.V2_0] = APIVersionInfo(
            version=APIVersion.V2_0,
            status="planned",
            release_date=datetime(2025, 12, 1),
            changelog=[
                "New streaming endpoints",                "GraphQL support",
                "Advanced multi-modal analysis",
                "Real-time event processing"
            ],
            breaking_changes=[
                "Response format changes for /rag/query",
                "Authentication requirements",
                "Pagination for list endpoints"
            ]
        )
    
    def get_version_info(self, version: APIVersion) -> Optional[APIVersionInfo]:
        """Get information about a specific version"""
        return self.versions.get(version)
    
    def get_all_versions(self) -> Dict[APIVersion, APIVersionInfo]:
        """Get all version information"""
        return self.versions.copy()
    
    def get_active_versions(self) -> List[APIVersion]:
        """Get all active (non-sunset) versions"""
        return [v.version for v in self.versions.values() if v.status in ["active", "deprecated"]]
    
    def is_version_supported(self, version: APIVersion) -> bool:
        """Check if a version is still supported"""
        info = self.get_version_info(version)
        return info is not None and not info.is_sunset
    
    def get_deprecation_warnings(self, version: APIVersion) -> List[str]:
        """Get deprecation warnings for a version"""
        info = self.get_version_info(version)
        if not info:
            return ["Unknown API version"]
        
        warnings = []
        if info.is_deprecated:
            warnings.append(f"API version {version.value} is deprecated")
            if info.sunset_date:
                days_left = info.days_until_sunset
                if days_left is not None:
                    warnings.append(f"Support ends in {days_left} days ({info.sunset_date.strftime('%Y-%m-%d')})")
        
        return warnings

# Global version manager
version_manager = APIVersionManager()

def get_api_version_from_request(request: Request) -> APIVersion:
    """Extract API version from request"""
    # 1. Check URL path for version
    path = request.url.path
    version_match = re.search(r'/api/v?(\d+(?:\.\d+)?)', path)
    if version_match:
        version_str = version_match.group(1)
        version = APIVersion.from_string(version_str)
        if version:
            return version
    
    # 2. Check Accept header for version
    accept_header = request.headers.get('Accept', '')
    if 'application/vnd.rag.v' in accept_header:
        version_match = re.search(r'application/vnd\.rag\.v(\d+(?:\.\d+)?)', accept_header)
        if version_match:
            version_str = version_match.group(1)
            version = APIVersion.from_string(version_str)
            if version:
                return version
    
    # 3. Check custom header
    version_header = request.headers.get('X-API-Version', request.headers.get('API-Version'))
    if version_header:
        version = APIVersion.from_string(version_header)
        if version:
            return version
    
    # 4. Default to latest stable version
    return APIVersion.get_latest()

def validate_api_version(version: APIVersion) -> None:
    """Validate that API version is supported"""
    if not version_manager.is_version_supported(version):
        info = version_manager.get_version_info(version)
        if info and info.is_sunset:
            raise HTTPException(
                status_code=410,
                detail=f"API version {version.value} is no longer supported. Sunset date: {info.sunset_date}"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported API version: {version.value}. Supported versions: {[v.value for v in version_manager.get_active_versions()]}"
            )

def add_version_headers(response: JSONResponse, version: APIVersion) -> JSONResponse:
    """Add version-related headers to response"""
    info = version_manager.get_version_info(version)
    
    # Standard version headers
    response.headers["X-API-Version"] = version.value
    response.headers["X-API-Version-Status"] = info.status if info else "unknown"
    
    # Deprecation warnings
    if info and info.is_deprecated:
        warnings = version_manager.get_deprecation_warnings(version)
        if warnings:
            response.headers["Warning"] = "; ".join(warnings)
            if info.sunset_date:
                response.headers["Sunset"] = info.sunset_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    # Link to latest version
    latest = APIVersion.get_latest()
    if version != latest:
        response.headers["Link"] = f'</api/v{latest.value}>; rel="latest-version"'
    
    return response

class VersionedAPIRoute(APIRoute):
    """Custom route class that handles API versioning"""
    
    def __init__(self, *args, min_version: Optional[APIVersion] = None, 
                 max_version: Optional[APIVersion] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_version = min_version or APIVersion.V1_0
        self.max_version = max_version or APIVersion.get_latest()
    
    def matches(self, scope: dict) -> tuple:
        """Override to check version compatibility"""
        match, child_scope = super().matches(scope)
        if not match:
            return match, child_scope
        
        # Extract version from request path or headers
        request = Request(scope)
        try:
            version = get_api_version_from_request(request)
            
            # Check if version is within supported range for this endpoint
            if version.value < self.min_version.value or version.value > self.max_version.value:
                return False, {}
            
            # Store version in scope for use in endpoint
            child_scope["api_version"] = version
            
        except Exception:
            # If version parsing fails, allow the request to proceed
            # The endpoint can handle version validation
            pass
        
        return match, child_scope

def create_versioned_app(title: str = "Advanced RAG Service") -> FastAPI:
    """Create FastAPI app with versioning support"""
    
    app = FastAPI(
        title=title,
        description="Enhanced evidence processing with multi-modal analysis and correlation",
        version=APIVersion.get_latest().value,
        openapi_prefix="/api"
    )
    
    # Add versioning middleware
    @app.middleware("http")
    async def version_middleware(request: Request, call_next):
        """Middleware to handle API versioning"""
        try:
            # Get API version from request
            version = get_api_version_from_request(request)
            
            # Validate version
            validate_api_version(version)
            
            # Store version in request state
            request.state.api_version = version
            
            # Process request
            response = await call_next(request)
            
            # Add version headers to response
            if isinstance(response, JSONResponse):
                response = add_version_headers(response, version)
            else:
                # Convert to JSONResponse if needed to add headers
                if hasattr(response, 'headers'):
                    info = version_manager.get_version_info(version)
                    response.headers["X-API-Version"] = version.value
                    response.headers["X-API-Version-Status"] = info.status if info else "unknown"
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Version middleware error: {e}")
            # Continue without version processing
            return await call_next(request)
    
    return app

def get_current_api_version(request: Request) -> APIVersion:
    """Dependency to get current API version in endpoints"""
    return getattr(request.state, 'api_version', APIVersion.get_latest())

def require_min_version(min_version: APIVersion):
    """Decorator to require minimum API version for endpoint"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This would be implemented as a FastAPI dependency
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Version-specific endpoint helpers
def v1_endpoint(path: str, **kwargs):
    """Helper for v1 endpoints"""
    return {"path": f"/api/v1{path}", "tags": ["v1.0", "v1.1"], **kwargs}

def v2_endpoint(path: str, **kwargs):
    """Helper for v2 endpoints"""  
    return {"path": f"/api/v2{path}", "tags": ["v2.0"], **kwargs}

def legacy_endpoint(path: str, **kwargs):
    """Helper for legacy endpoints (no version prefix)"""
    return {"path": path, "tags": ["legacy"], **kwargs}

# API Documentation helpers
def get_api_versions_info() -> Dict[str, Any]:
    """Get API versions information for documentation"""
    versions_info = {}
    
    for version, info in version_manager.get_all_versions().items():
        versions_info[version.value] = {
            "status": info.status,
            "release_date": info.release_date.isoformat(),
            "deprecation_date": info.deprecation_date.isoformat() if info.deprecation_date else None,
            "sunset_date": info.sunset_date.isoformat() if info.sunset_date else None,
            "changelog": info.changelog,
            "breaking_changes": info.breaking_changes,
            "days_until_sunset": info.days_until_sunset
        }
    
    return {
        "current_version": APIVersion.get_latest().value,
        "supported_versions": [v.value for v in version_manager.get_active_versions()],
        "versions": versions_info
    }
