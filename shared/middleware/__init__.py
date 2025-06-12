# Shared middleware modules
"""
Shared middleware modules for FastAPI microservices.

This package provides common middleware functionality including:
- Rate limiting and throttling
- Request/response logging
- Authentication and authorization
- Metrics collection
"""

from .rate_limit import (
    limiter,
    add_rate_limiting,
    custom_rate_limit_exceeded_handler,
    get_rate_limit_stats,
    reset_rate_limits,
    rate_limit_websocket,
    websocket_rate_limit_middleware,
    WebSocketRateLimiter,
    DEFAULT_RATE_LIMIT,
    CONTACT_RATE_LIMIT,
    ALERTS_RATE_LIMIT,
    WEBSOCKET_RATE_LIMIT,
    ENDPOINT_RATE_LIMITS
)

__all__ = [
    "limiter",
    "add_rate_limiting", 
    "custom_rate_limit_exceeded_handler",
    "get_rate_limit_stats",
    "reset_rate_limits",
    "rate_limit_websocket",
    "websocket_rate_limit_middleware",
    "WebSocketRateLimiter",
    "DEFAULT_RATE_LIMIT",
    "CONTACT_RATE_LIMIT", 
    "ALERTS_RATE_LIMIT",
    "WEBSOCKET_RATE_LIMIT",
    "ENDPOINT_RATE_LIMITS"
]
