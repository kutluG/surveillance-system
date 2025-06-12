# Rate Limiting Middleware

This module provides comprehensive request-level rate limiting and throttling for all FastAPI microservices in the surveillance system.

## Features

- **Global Rate Limiting**: Default limit of 100 requests per minute per client IP
- **Endpoint-Specific Limits**: Custom rate limits for sensitive endpoints
- **Distributed Rate Limiting**: Redis-based storage for multi-instance deployments
- **WebSocket Support**: Rate limiting for WebSocket connections
- **Configurable**: Environment variable configuration
- **Comprehensive Logging**: Detailed rate limit violation logging
- **Health Check Exemption**: Health endpoints exempt from rate limiting

## Default Configuration

- **Default Limit**: 100 requests per minute per client IP
- **Contact Endpoints** (`/api/v1/contact`): 10 requests per minute
- **Alerts Endpoints** (`/api/v1/alerts`): 50 requests per minute
- **WebSocket Connections**: 30 requests per minute

## Quick Start

### 1. Basic Integration

```python
from fastapi import FastAPI
from shared.middleware import add_rate_limiting

app = FastAPI()

# Add rate limiting to your FastAPI app
add_rate_limiting(app, service_name="my-service")
```

### 2. Custom Endpoint Limits

```python
from fastapi import FastAPI, Request
from shared.middleware import add_rate_limiting, limiter

app = FastAPI()
add_rate_limiting(app, service_name="my-service")

@app.get("/api/v1/sensitive")
@limiter.limit("5/minute")  # Custom limit: 5 requests per minute
async def sensitive_endpoint(request: Request):
    return {"message": "Sensitive endpoint"}
```

### 3. WebSocket Rate Limiting

```python
from fastapi import WebSocket
from shared.middleware import rate_limit_websocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            
            # Check rate limit
            if not rate_limit_websocket(websocket):
                await websocket.send_json({
                    "error": "Rate limit exceeded. Try again later.",
                    "type": "rate_limit_error"
                })
                continue
                
            # Process message...
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
```

## Specialized WebSocket Endpoints

The system provides specialized WebSocket endpoints with dedicated rate limiting:

### Events WebSocket (/ws/events/{session_id})

```python
# Connect to events endpoint
ws_url = "ws://localhost:8010/ws/events/my_session_123"

# Example event subscription
subscription_message = {
    "message_type": "event_subscription",
    "event_types": ["motion_detected", "alarm_triggered", "camera_offline"]
}

# Example event query
query_message = {
    "message_type": "event_query",
    "parameters": {
        "time_range": "last_hour",
        "event_types": ["motion_detected"],
        "camera_ids": ["cam_001", "cam_002"]
    }
}
```

### Alerts WebSocket (/ws/alerts/{session_id})

```python
# Connect to alerts endpoint
ws_url = "ws://localhost:8010/ws/alerts/my_session_456"

# Example alert subscription
subscription_message = {
    "message_type": "alert_subscription",
    "alert_levels": ["high", "critical"]
}

# Example alert acknowledgment
ack_message = {
    "message_type": "alert_acknowledge",
    "alert_id": "alert_123"
}

# Example alert query
query_message = {
    "message_type": "alert_query",
    "parameters": {
        "status": "active",
        "levels": ["high", "critical"],
        "limit": 10
    }
}
```

### WebSocket Rate Limiting Behavior

- **Rate Limit**: 30 messages per minute per connection
- **Enforcement**: Per-connection tracking using client IP and port
- **Response**: JSON error message when limit exceeded
- **Cleanup**: Automatic cleanup of old connection data

```json
{
    "error": "Rate limit exceeded. Maximum 30 messages per minute allowed.",
    "type": "rate_limit_error",
    "endpoint": "events",
    "retry_after": 60
}
```

## Environment Configuration

Configure rate limits using environment variables:

```bash
# Default rate limit (requests per minute per IP)
RATE_LIMIT_DEFAULT=100/minute

# Contact endpoints
RATE_LIMIT_CONTACT=10/minute

# Alerts endpoints  
RATE_LIMIT_ALERTS=50/minute

# WebSocket connections
RATE_LIMIT_WEBSOCKET=30/minute

# Redis configuration for distributed rate limiting
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1
```

## Rate Limit Formats

Rate limits can be specified in various formats:

- `100/minute` - 100 requests per minute
- `10/second` - 10 requests per second
- `1000/hour` - 1000 requests per hour
- `5000/day` - 5000 requests per day

## Error Response Format

When rate limits are exceeded, the middleware returns HTTP 429 with:

```json
{
  "detail": "Rate limit exceeded. Try again in 60s."
}
```

Headers include:
- `Retry-After`: Number of seconds until retry is allowed

## Exempt Endpoints

The following endpoints are exempt from rate limiting:
- `/health` - Health check endpoint
- `/metrics` - Prometheus metrics
- `/docs` - OpenAPI documentation
- `/redoc` - ReDoc documentation
- `/openapi.json` - OpenAPI schema

## Client IP Detection

The middleware intelligently detects client IPs using:

1. `X-Forwarded-For` header (for reverse proxies)
2. `X-Real-IP` header (for load balancers)
3. Direct connection IP (fallback)

## Redis Backend

For production deployments with multiple service instances, Redis is used for distributed rate limiting:

- **Connection**: Automatic Redis connection with fallback to in-memory
- **Database**: Uses Redis DB 1 for rate limiting data
- **Timeout**: 5-second connection timeout
- **Error Handling**: Graceful fallback to in-memory storage

## Monitoring and Stats

Get rate limiting statistics:

```python
from shared.middleware import get_rate_limit_stats

stats = get_rate_limit_stats()
# Returns:
# {
#   "default_limit": "100/minute",
#   "endpoint_limits": {...},
#   "redis_connected": true,
#   "websocket_connections": 5,
#   "websocket_limit": "30/minute"
# }
```

## Testing Utilities

Reset rate limits for testing:

```python
from shared.middleware import reset_rate_limits

# Reset all rate limits
reset_rate_limits()

# Reset specific IP
reset_rate_limits("192.168.1.1")
```

## Integration Examples

### API Gateway
```python
from shared.middleware import add_rate_limiting
add_rate_limiting(app, service_name="api-gateway")
```

### Edge Service
```python  
from shared.middleware import add_rate_limiting
add_rate_limiting(app, service_name="edge-service")
```

### Contact/Notifier Service
```python
from shared.middleware import add_rate_limiting
add_rate_limiting(app, service_name="notifier")
# /api/v1/contact automatically gets 10/minute limit
```

## Logging

Rate limit violations are logged with structured data:

```json
{
  "level": "warning",
  "message": "Rate limit exceeded for 192.168.1.1 on /api/v1/contact",
  "client_ip": "192.168.1.1",
  "endpoint": "/api/v1/contact", 
  "method": "POST",
  "retry_after": 60
}
```

## Performance Considerations

- **Redis**: Recommended for production multi-instance deployments
- **Memory**: In-memory fallback for single-instance or development
- **Cleanup**: Automatic cleanup of old WebSocket connection data
- **Overhead**: Minimal performance impact (~0.1ms per request)

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Check Redis host/port configuration
   - Verify Redis service is running
   - Fallback to in-memory storage is automatic

2. **Rate Limits Not Applied**
   - Ensure `add_rate_limiting()` is called after app creation
   - Check endpoint path matches configured patterns
   - Verify middleware order

3. **WebSocket Rate Limiting Not Working**
   - Use `rate_limit_websocket()` function in WebSocket handlers
   - Check WebSocket connection IP detection

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("shared.middleware.rate_limit").setLevel(logging.DEBUG)
```

## Security Considerations

- **IP Spoofing**: Middleware validates proxy headers
- **DDoS Protection**: Automatic rate limiting prevents abuse
- **Resource Limits**: WebSocket connection cleanup prevents memory leaks
- **Configuration**: Rate limits configurable per environment
