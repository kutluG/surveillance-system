"""
Rate Limiting and Security Middleware for Annotation Frontend

Implements per-route rate limiting using SlowAPI and request size constraints.
"""
import time
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Configure the limiter with default rate limits
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],  # Default: 60 requests per minute per IP as required
    storage_uri="memory://",  # Use in-memory storage for development
    # For production, use Redis: storage_uri="redis://localhost:6379"
)

# Custom rate limit exceeded handler with detailed error information
async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    Provides detailed information about the rate limit.
    """
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "detail": f"Too many requests. Limit: {exc.detail}",
            "retry_after": exc.retry_after,
            "endpoint": str(request.url.path),
            "timestamp": int(time.time())
        }
    )
    
    # Add standard rate limiting headers
    response.headers["Retry-After"] = str(exc.retry_after)
    response.headers["X-RateLimit-Limit"] = str(exc.detail)
    response.headers["X-RateLimit-Remaining"] = "0"
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + exc.retry_after)
    
    return response

# Request size validation constants
MAX_REQUEST_BODY_SIZE = 1024 * 1024  # 1MB in bytes
MAX_JSON_FIELD_SIZE = 4096  # 4KB for individual JSON fields

class RequestSizeMiddleware:
    """
    Middleware to enforce request body size limits.
    """
    
    def __init__(self, app, max_size: int = MAX_REQUEST_BODY_SIZE):
        self.app = app
        self.max_size = max_size
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Check Content-Length header if present
            headers = dict(scope.get("headers", []))
            content_length = headers.get(b"content-length")
            
            if content_length:
                try:
                    content_length = int(content_length.decode())
                    if content_length > self.max_size:
                        # Send 413 Payload Too Large response
                        response = JSONResponse(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            content={
                                "error": "Request body too large",
                                "detail": f"Request body size {content_length} exceeds maximum {self.max_size} bytes",
                                "max_size": self.max_size
                            }
                        )
                        await response(scope, receive, send)
                        return
                except (ValueError, UnicodeDecodeError):
                    pass
            
            # Track actual bytes received for requests without Content-Length
            received_bytes = 0
            
            async def receive_wrapper():
                nonlocal received_bytes
                message = await receive()
                
                if message["type"] == "http.request":
                    body = message.get("body", b"")
                    received_bytes += len(body)
                    
                    if received_bytes > self.max_size:
                        # Raise exception to stop processing
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Request body size exceeds maximum {self.max_size} bytes"
                        )
                
                return message
            
            try:
                await self.app(scope, receive_wrapper, send)
            except HTTPException as e:
                if e.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
                    response = JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": "Request body too large",
                            "detail": str(e.detail),
                            "max_size": self.max_size
                        }
                    )
                    await response(scope, receive, send)
                else:
                    raise
        else:
            await self.app(scope, receive, send)

def setup_rate_limiting(app):
    """
    Set up rate limiting middleware and exception handlers for the FastAPI app.
    """
    # Attach limiter to app state
    app.state.limiter = limiter
    
    # Add exception handler for rate limit exceeded
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)
    
    # Add SlowAPI middleware
    app.add_middleware(SlowAPIMiddleware)
    
    # Add request size limiting middleware
    app.add_middleware(RequestSizeMiddleware, max_size=MAX_REQUEST_BODY_SIZE)

def get_client_ip(request: Request) -> str:
    """
    Get the client IP address from the request.
    Handles X-Forwarded-For header for proxied requests.
    """
    # Check for X-Forwarded-For header (common in load-balanced environments)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    return get_remote_address(request)

# Alternative limiter with IP detection for proxied environments
limiter_with_proxy_support = Limiter(
    key_func=get_client_ip,
    default_limits=["60/minute"],
    storage_uri="memory://"
)

# Rate limiting decorators for specific use cases
def rate_limit_annotation_submission():
    """Rate limit decorator for annotation submission endpoints."""
    return limiter.limit("10/minute")  # Exactly 10 requests/minute as required

def rate_limit_data_deletion():
    """Rate limit decorator for data deletion endpoints.""" 
    return limiter.limit("5/hour")  # Exactly 5 requests/hour as required

def rate_limit_authentication():
    """Rate limit decorator for authentication endpoints."""
    return limiter.limit("20/minute")

def rate_limit_health_check():
    """Rate limit decorator for health check endpoints."""
    return limiter.limit("120/minute")  # More lenient for monitoring

# Utility function to check if request is from trusted sources
def is_trusted_ip(request: Request) -> bool:
    """
    Check if the request is from a trusted IP address.
    Used to bypass rate limiting for internal services.
    """
    trusted_ips = [
        "127.0.0.1",
        "::1",
        "10.0.0.0/8",    # Private networks
        "172.16.0.0/12",
        "192.168.0.0/16"
    ]
    
    client_ip = get_client_ip(request)
    
    # Simple IP checking (in production, use proper IP network checking)
    for trusted_ip in trusted_ips:
        if client_ip.startswith(trusted_ip.split("/")[0]):
            return True
    
    return False

# Custom limiter that exempts trusted IPs
def create_limiter_with_exemptions():
    """
    Create a limiter that exempts trusted IP addresses.
    """
    def key_func_with_exemptions(request: Request) -> Optional[str]:
        if is_trusted_ip(request):
            return None  # No rate limiting for trusted IPs
        return get_client_ip(request)
    
    return Limiter(
        key_func=key_func_with_exemptions,
        default_limits=["60/minute"],
        storage_uri="memory://"
    )
