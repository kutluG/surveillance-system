"""
FastAPI middleware for audit trail and request correlation tracking.
Automatically logs request lifecycle events with correlation IDs.
"""
import time
import uuid
from typing import Callable, Optional

import jwt
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging_config import (
    get_logger, 
    set_request_id, 
    clear_context,
    log_request_started,
    log_request_completed,
    log_request_error
)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for audit trail and request correlation tracking.
    
    Features:
    - Extracts or generates X-Request-ID for correlation
    - Logs request started/completed/error events
    - Tracks request duration
    - Extracts user_id from various auth sources
    - Handles unhandled exceptions gracefully
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        service_name: str = None,
        exclude_paths: list = None,
        extract_user_id: Callable[[Request], Optional[str]] = None
    ):
        super().__init__(app)
        self.service_name = service_name or "unknown-service"
        self.logger = get_logger(self.service_name)
        self.exclude_paths = exclude_paths or ['/health', '/metrics', '/docs', '/openapi.json']
        self.extract_user_id = extract_user_id or self._default_extract_user_id
    
    def _default_extract_user_id(self, request: Request) -> Optional[str]:
        """
        Default user ID extraction logic.
        Override this by passing a custom extract_user_id function.
        """        # Try to extract from JWT token in Authorization header
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            try:
                token = auth_header.split(' ')[1]
                # Decode without verification for user_id extraction
                # In production, you should verify the token
                payload = jwt.decode(token, options={"verify_signature": False})
                return payload.get('sub') or payload.get('user_id') or payload.get('uid')
            except Exception:
                pass
        
        # Try to extract from X-User-ID header
        user_id = request.headers.get('x-user-id')
        if user_id:
            return user_id
        
        # Try to extract from query parameter
        user_id = request.query_params.get('user_id')
        if user_id:
            return user_id
        
        return None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with audit logging."""
        
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Extract or generate request ID
        request_id = request.headers.get('x-request-id') or str(uuid.uuid4())
        
        # Set request ID in thread-local context
        set_request_id(request_id)
        
        # Store request ID in request state for access in endpoints
        request.state.request_id = request_id
        
        # Extract user ID
        user_id = self.extract_user_id(request)
        if user_id:
            request.state.user_id = user_id
        
        # Record start time
        start_time = time.time()
        
        # Log request started
        log_request_started(
            self.logger,
            method=request.method,
            path=request.url.path,
            user_id=user_id,
            query_params=dict(request.query_params) if request.query_params else None,
            user_agent=request.headers.get('user-agent'),
            client_ip=self._get_client_ip(request)
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log successful completion
            log_request_completed(
                self.logger,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                response_size=response.headers.get('content-length')
            )
            
            # Add request ID to response headers for client correlation
            response.headers['X-Request-ID'] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration for error case
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            log_request_error(
                self.logger,
                method=request.method,
                path=request.url.path,
                error=e,
                user_id=user_id,
                duration_ms=duration_ms
            )
            
            # Return structured error response
            error_response = JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "message": "An unexpected error occurred. Please contact support with the request ID."
                },
                headers={"X-Request-ID": request_id}
            )
            
            return error_response
            
        finally:
            # Clean up thread-local context
            clear_context()
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers."""
        # Check for forwarded IP first (load balancer/proxy)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # Take the first IP if multiple are present
            return forwarded_for.split(',')[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else 'unknown'


class CameraAuditMiddleware(AuditMiddleware):
    """
    Specialized audit middleware for camera-related services.
    Extracts camera_id from requests for enhanced logging.
    """
    
    def _extract_camera_context(self, request: Request) -> dict:
        """Extract camera-specific context from request."""
        context = {}
        
        # Extract camera_id from path parameters
        if hasattr(request, 'path_params'):
            camera_id = request.path_params.get('camera_id')
            if camera_id:
                context['camera_id'] = camera_id
        
        # Extract camera_id from query parameters
        camera_id = request.query_params.get('camera_id')
        if camera_id:
            context['camera_id'] = camera_id
        
        # Extract from request body for POST/PUT requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            # This would require reading the body, which is more complex
            # For now, we'll leave this for endpoint-specific logging
            pass
        
        return context
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enhanced dispatch with camera context extraction."""
        
        # Extract camera context and store in request state
        camera_context = self._extract_camera_context(request)
        for key, value in camera_context.items():
            setattr(request.state, key, value)
        
        return await super().dispatch(request, call_next)


def add_audit_middleware(
    app, 
    service_name: str = None,
    exclude_paths: list = None,
    extract_user_id: Callable[[Request], Optional[str]] = None,
    use_camera_middleware: bool = False
):
    """
    Convenience function to add audit middleware to FastAPI app.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service for logging
        exclude_paths: List of paths to exclude from audit logging
        extract_user_id: Custom function to extract user ID from request
        use_camera_middleware: Whether to use camera-specific middleware
    """
    middleware_class = CameraAuditMiddleware if use_camera_middleware else AuditMiddleware
    
    app.add_middleware(
        middleware_class,
        service_name=service_name,
        exclude_paths=exclude_paths,
        extract_user_id=extract_user_id
    )
