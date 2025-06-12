"""
Rate Limiting Middleware for FastAPI Services

This module provides request-level rate limiting and throttling for all
FastAPI microservices in the surveillance system.

Features:
- Global rate limiting based on client IP
- Custom rate limits for sensitive endpoints
- Configurable via environment variables
- WebSocket connection rate limiting
- JSON error responses with retry-after headers
- Redis-based distributed rate limiting
"""
import os
import time
import redis
from typing import Dict, Optional, Callable, Any
from fastapi import FastAPI, Request, WebSocket, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import asyncio
import logging

logger = logging.getLogger(__name__)

# Redis connection for distributed rate limiting
redis_client = None

def get_redis_client():
    """Get Redis client for distributed rate limiting"""
    global redis_client
    if redis_client is None:
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "1"))  # Use DB 1 for rate limiting
        
        try:
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            redis_client.ping()
            logger.info(f"Connected to Redis for rate limiting: {redis_host}:{redis_port}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for rate limiting: {e}")
            logger.warning("Falling back to in-memory rate limiting")
            redis_client = None
    
    return redis_client

def get_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    Uses X-Forwarded-For header if available, otherwise remote address.
    """
    # Check for reverse proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to remote address
    return get_remote_address(request)

# Initialize limiter with Redis or in-memory storage
def create_limiter() -> Limiter:
    """Create limiter instance with appropriate storage backend"""
    redis_conn = get_redis_client()
    if redis_conn:
        from slowapi.util import get_remote_address
        limiter = Limiter(
            key_func=get_identifier,
            storage_uri=f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/1"
        )
    else:
        limiter = Limiter(
            key_func=get_identifier
        )
    
    return limiter

# Create global limiter instance
limiter = create_limiter()

# Rate limit configurations from environment variables
DEFAULT_RATE_LIMIT = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")  # 100 requests per minute per client IP
CONTACT_RATE_LIMIT = os.getenv("RATE_LIMIT_CONTACT", "10/minute")    # 10 requests per minute for contact endpoints
ALERTS_RATE_LIMIT = os.getenv("RATE_LIMIT_ALERTS", "50/minute")      # 50 requests per minute for alerts endpoints
WEBSOCKET_RATE_LIMIT = os.getenv("RATE_LIMIT_WEBSOCKET", "30/minute")

# Custom rate limit configurations for specific endpoints
ENDPOINT_RATE_LIMITS = {
    "/api/v1/contact": CONTACT_RATE_LIMIT,
    "/api/v1/alerts": ALERTS_RATE_LIMIT,
    "/contact": CONTACT_RATE_LIMIT,
    "/alerts": ALERTS_RATE_LIMIT,
    "/notify": CONTACT_RATE_LIMIT,  # Notifier service
    "/notification": CONTACT_RATE_LIMIT,
}

def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded exceptions.
    Returns HTTP 429 with JSON: { "detail": "Rate limit exceeded. Try again in <retry_after>s." }
    """
    retry_after = int(exc.retry_after) if exc.retry_after else 60
    
    logger.warning(
        f"Rate limit exceeded for {get_identifier(request)} on {request.url.path}",
        extra={
            "client_ip": get_identifier(request),
            "endpoint": request.url.path,
            "method": request.method,
            "retry_after": retry_after
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": f"Rate limit exceeded. Try again in {retry_after}s."
        },
        headers={"Retry-After": str(retry_after)}
    )

def get_endpoint_rate_limit(path: str) -> str:
    """Get rate limit for specific endpoint or return default"""
    # Check for exact match first
    if path in ENDPOINT_RATE_LIMITS:
        return ENDPOINT_RATE_LIMITS[path]
    
    # Check for partial matches (for versioned APIs)
    for endpoint_pattern, rate_limit in ENDPOINT_RATE_LIMITS.items():
        if path.endswith(endpoint_pattern.lstrip("/")):
            return rate_limit
    
    return DEFAULT_RATE_LIMIT

def add_rate_limiting(app: FastAPI, service_name: str = "service") -> None:
    """
    Add rate limiting to FastAPI application.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service for logging
    """
    # Add the rate limiting middleware
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    
    # Add custom exception handler
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)
    
    # Add middleware to apply dynamic rate limits
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get appropriate rate limit for this endpoint
        endpoint_limit = get_endpoint_rate_limit(request.url.path)
        
        # Apply rate limit using limiter
        try:
            # Create a temporary rate-limited function
            @limiter.limit(endpoint_limit)
            async def rate_limited_endpoint(request: Request):
                return await call_next(request)
            
            return await rate_limited_endpoint(request)
        except RateLimitExceeded as e:
            return custom_rate_limit_exceeded_handler(request, e)
    
    logger.info(f"Rate limiting enabled for {service_name}")
    logger.info(f"Default rate limit: {DEFAULT_RATE_LIMIT}")
    logger.info(f"Custom limits: {ENDPOINT_RATE_LIMITS}")

# WebSocket rate limiting functionality
class WebSocketRateLimiter:
    """Rate limiter for WebSocket connections"""
    
    def __init__(self, rate_limit: str = WEBSOCKET_RATE_LIMIT):
        self.rate_limit = rate_limit
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.parse_rate_limit(rate_limit)
    
    def parse_rate_limit(self, rate_limit: str):
        """Parse rate limit string like '30/minute' into number and period"""
        parts = rate_limit.split("/")
        self.limit_count = int(parts[0])
        
        period_str = parts[1].lower()
        if period_str in ["second", "sec", "s"]:
            self.period_seconds = 1
        elif period_str in ["minute", "min", "m"]:
            self.period_seconds = 60
        elif period_str in ["hour", "hr", "h"]:
            self.period_seconds = 3600
        elif period_str in ["day", "d"]:
            self.period_seconds = 86400
        else:
            self.period_seconds = 60  # Default to minute
    
    def get_connection_id(self, websocket: WebSocket) -> str:
        """Get unique identifier for WebSocket connection"""
        client_ip = websocket.client.host if websocket.client else "unknown"
        return f"{client_ip}:{websocket.client.port if websocket.client else 'unknown'}"
    
    def is_allowed(self, websocket: WebSocket) -> bool:
        """Check if WebSocket connection is allowed to send message"""
        conn_id = self.get_connection_id(websocket)
        current_time = time.time()
        
        if conn_id not in self.connections:
            self.connections[conn_id] = {
                "messages": [],
                "first_message_time": current_time
            }
        
        conn_data = self.connections[conn_id]
        
        # Remove old messages outside the time window
        cutoff_time = current_time - self.period_seconds
        conn_data["messages"] = [msg_time for msg_time in conn_data["messages"] if msg_time > cutoff_time]
        
        # Check if under limit
        if len(conn_data["messages"]) < self.limit_count:
            conn_data["messages"].append(current_time)
            return True
        
        return False
    
    def cleanup_old_connections(self):
        """Clean up old connection data"""
        current_time = time.time()
        cutoff_time = current_time - (self.period_seconds * 2)  # Keep data for 2x the period
        
        to_remove = []
        for conn_id, conn_data in self.connections.items():
            if not conn_data["messages"] or max(conn_data["messages"]) < cutoff_time:
                to_remove.append(conn_id)
        
        for conn_id in to_remove:
            del self.connections[conn_id]

# Global WebSocket rate limiter
websocket_limiter = WebSocketRateLimiter()

def rate_limit_websocket(websocket: WebSocket) -> bool:
    """
    Check if WebSocket connection is rate limited.
    Returns True if allowed, False if rate limited.
    """
    return websocket_limiter.is_allowed(websocket)

async def websocket_rate_limit_middleware(websocket: WebSocket, call_next: Callable) -> Any:
    """
    Middleware for WebSocket rate limiting.
    Usage in WebSocket endpoint:
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                if not rate_limit_websocket(websocket):
                    await websocket.send_json({
                        "error": "Rate limit exceeded. Try again later.",
                        "type": "rate_limit_error"
                    })
                    continue
                # Process message...
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
    """
    return await call_next(websocket)

# Utility functions for testing and monitoring
def get_rate_limit_stats() -> Dict[str, Any]:
    """Get current rate limiting statistics"""
    stats = {
        "default_limit": DEFAULT_RATE_LIMIT,
        "endpoint_limits": ENDPOINT_RATE_LIMITS,
        "redis_connected": get_redis_client() is not None,
        "websocket_connections": len(websocket_limiter.connections),
        "websocket_limit": WEBSOCKET_RATE_LIMIT
    }
    
    return stats

def reset_rate_limits(identifier: Optional[str] = None) -> bool:
    """
    Reset rate limits for testing purposes.
    If identifier is None, resets all limits.
    """
    try:
        redis_conn = get_redis_client()
        if redis_conn:
            if identifier:
                # Reset specific identifier
                keys = redis_conn.keys(f"*{identifier}*")
                if keys:
                    redis_conn.delete(*keys)
            else:
                # Reset all rate limit keys
                keys = redis_conn.keys("LIMITER*")
                if keys:
                    redis_conn.delete(*keys)
            return True
    except Exception as e:
        logger.error(f"Failed to reset rate limits: {e}")
    
    return False
