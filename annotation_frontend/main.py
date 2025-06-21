"""
Annotation Frontend Service: Web UI for human labeling of hard examples
from the continuous learning pipeline.

Scalable backend with Redis retry queue, Kafka pooling, and static asset caching.
"""
import asyncio
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends, status, Form, Query, WebSocket, WebSocketDisconnect, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.exceptions import RequestValidationError
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import get_db, create_tables
from models import AnnotationExample, AnnotationStatus
from schemas import (
    AnnotationRequest, 
    AnnotationResponse, 
    ExampleResponse,
    ExampleListResponse,
    HealthResponse,
    StatsResponse,
    LoginResponse,
    CSRFTokenResponse,
    ErrorResponse,
    ValidationErrorResponse
)
from services import AnnotationService
from auth import get_current_user, require_scopes, require_role, TokenData, authenticate_user, create_access_token, oauth2_password_bearer
from data_subject import router as data_subject_router
from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.middleware import add_rate_limiting
from kafka_pool import kafka_pool
from redis_service import redis_retry_service
from background_tasks import background_retry_task

# Rate limiting imports
from rate_limiting import (
    setup_rate_limiting,
    limiter,
    rate_limit_annotation_submission,
    rate_limit_data_deletion,
    rate_limit_authentication,
    rate_limit_health_check,
    MAX_JSON_FIELD_SIZE
)

# Import routers
from routers.examples import router as examples_router
from routers.health import router as health_router

# Configure logging first
logger = configure_logging("annotation_frontend")

# CSRF Protection Configuration
class CsrfSettings(BaseModel):
    secret_key: str = settings.CSRF_SECRET_KEY
    token_expires: int = settings.CSRF_TOKEN_EXPIRES
    max_age: int = settings.CSRF_TOKEN_EXPIRES

# Initialize CSRF Protection
csrf_protect = CsrfProtect()

# Configure CSRF protection
@csrf_protect.load_config
def load_csrf_config():
    return CsrfSettings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    
    # Startup
    logger.info("Starting Annotation Frontend Service")
    
    # Initialize database
    create_tables()
    
    # Initialize Kafka connection pool
    await kafka_pool.initialize()
    app.state.kafka_pool = kafka_pool
    
    # Initialize Redis retry service
    await redis_retry_service.initialize()
    app.state.redis_retry_service = redis_retry_service
    
    # Start background tasks
    asyncio.create_task(consume_hard_examples())
    await background_retry_task.start()
    
    logger.info("Annotation Frontend Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Annotation Frontend Service")
    
    # Stop background tasks
    await background_retry_task.stop()
    
    # Close connections
    await kafka_pool.close()
    await redis_retry_service.close()
    
    logger.info("Annotation Frontend Service shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Annotation Frontend Service",
    description="Scalable backend for annotation with Redis retry queue and Kafka pooling",
    version="2.1.0",
    openapi_prefix="/api/v1",
    lifespan=lifespan
)

# Global Exception Handlers for consistent error responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for all unhandled exceptions.
    Returns consistent error format for any uncaught exception.
    """
    # Generate unique request ID for tracking
    request_id = str(uuid.uuid4())
    
    # Log the error with context
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}: {str(exc)}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    # Handle HTTPException (from FastAPI/Starlette)
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "detail": exc.detail,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id
            }
        )
    
    # Handle validation errors separately for better error messages
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "detail": "Request validation failed",
                "errors": [
                    {
                        "field": ".".join(str(loc) for loc in error["loc"]) if error.get("loc") else None,
                        "message": error.get("msg", "Validation error"),
                        "code": error.get("type")
                    }
                    for error in exc.errors()
                ],
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id
            }
        )
    
    # Handle all other exceptions as internal server error
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred while processing your request",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }
    )

# CSRF Middleware for state-changing requests
@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    """CSRF protection middleware for state-changing requests"""
    # Only apply CSRF protection to state-changing HTTP methods
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        # Skip CSRF for login endpoint and health checks
        if request.url.path not in ["/api/v1/login", "/health", "/api/v1/csrf-token"]:            # Check for CSRF token in header
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token:                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF protection failed: Missing X-CSRF-Token header"}
                )
            
            try:
                # Validate CSRF token using fastapi-csrf-protect
                await csrf_protect.validate_csrf(request)
            except CsrfProtectError as e:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": f"CSRF protection failed: {str(e)}"}
                )
    
    response = await call_next(request)
    return response

# Add audit middleware
add_audit_middleware(app, service_name="annotation_frontend")
instrument_app(app, service_name="annotation_frontend")

# Add rate limiting middleware and request size constraints
setup_rate_limiting(app)

# Add backwards compatibility redirect router for unversioned API calls
# Enhanced backwards compatibility redirect router for comprehensive API versioning
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def redirect_unversioned_api(request: Request, path: str):
    """
    Enhanced backwards compatibility redirect router.
    Issues HTTP 301 permanent redirect from unversioned /api/{path} to /api/v1/{path}
    
    This ensures all unversioned API calls are properly redirected to the current API version.
    """
    # Construct the versioned URL using settings configuration
    versioned_path = f"{settings.API_BASE_PATH}/{path}"
    
    # Preserve query parameters if any
    query_string = str(request.url.query)
    if query_string:
        versioned_path += f"?{query_string}"
    
    logger.info(f"API Version Redirect: {request.url.path} -> {versioned_path}")
    
    # Return HTTP 301 Moved Permanently redirect with custom header
    from fastapi.responses import RedirectResponse
    return RedirectResponse(
        url=versioned_path,
        status_code=301,
        headers={
            "X-API-Version-Redirect": settings.API_VERSION,
            "X-Deprecated-Endpoint": "true"
        }
    )

# Include data subject router for GDPR/CCPA compliance with proper versioning
app.include_router(data_subject_router, prefix=f"{settings.API_BASE_PATH}/data-subject", tags=["data-subject"])

# Include modular routers
app.include_router(examples_router, prefix=f"{settings.API_BASE_PATH}/examples", tags=["examples"])
app.include_router(health_router, prefix="/", tags=["health"])

# Setup templates and static files with caching
templates = Jinja2Templates(directory="templates")

# Configure static files with caching headers
class CachedStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        # Add cache control headers for static assets
        response.headers["Cache-Control"] = f"public, max-age={settings.STATIC_CACHE_MAX_AGE}"
        response.headers["ETag"] = f'"{hash(response.body)}"'
        return response

app.mount("/static", CachedStaticFiles(
    directory="static",
    html=True,
    check_dir=True
), name="static")

# CSRF Error Handler
@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": "CSRF protection failed", "error": str(exc)}
    )

# Models
class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class LabeledDetection(BaseModel):
    bbox: BoundingBox
    class_name: str
    confidence: float
    corrected_class: Optional[str] = None
    is_correct: bool = True

class LabeledExample(BaseModel):
    event_id: str
    camera_id: str
    timestamp: datetime
    frame_data: str
    original_detections: List[Dict]
    corrected_detections: List[LabeledDetection]
    annotator_id: str
    annotation_timestamp: datetime
    quality_score: float = 1.0
    notes: Optional[str] = None

# WebSocket Connection Manager for real-time updates (Redis-backed for stateless operation)
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Store connection count in Redis for monitoring across instances
        try:
            await redis_retry_service.increment_websocket_count()
            logger.info(f"WebSocket connected. Local connections: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"Failed to update Redis connection count: {e}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            asyncio.create_task(self._handle_disconnect_async())
            logger.info(f"WebSocket disconnected. Local connections: {len(self.active_connections)}")

    async def _handle_disconnect_async(self):
        """Handle disconnect operations that require async calls."""
        try:
            await redis_retry_service.decrement_websocket_count()
        except Exception as e:
            logger.error(f"Failed to update Redis connection count on disconnect: {e}")

    async def broadcast_new_example(self, example_data: dict):
        """Broadcast new example to all connected clients on this instance."""
        if not self.active_connections:
            return
            
        message = json.dumps({
            "type": "new_example",
            "example": example_data
        })
        
        # Send to all connected clients on this instance
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket client: {e}")
                disconnected_clients.append(connection)
          # Remove disconnected clients
        for client in disconnected_clients:
            self.disconnect(client)

    async def get_total_connections(self) -> int:
        """Get total connections across all instances from Redis."""
        try:
            return await redis_retry_service.get_websocket_count()
        except Exception as e:
            logger.error(f"Failed to get total connection count: {e}")
            return len(self.active_connections)  # fallback to local count

# Global connection manager for WebSocket connections across the instance
connection_manager = ConnectionManager()

@app.websocket("/ws/examples")
async def websocket_backwards_compatibility(websocket: WebSocket):
    """
    Backwards compatibility WebSocket endpoint.
    Redirects old /ws/examples connections to /ws/v1/examples with deprecation notice.
    """
    await websocket.accept()
    
    # Send deprecation notice
    deprecation_message = {
        "type": "deprecation_notice",
        "message": "This WebSocket endpoint is deprecated. Please use /ws/v1/examples",
        "old_endpoint": "/ws/examples",
        "new_endpoint": "/ws/v1/examples",
        "timestamp": datetime.utcnow().isoformat(),
        "action": "please_reconnect_to_new_endpoint"
    }
    
    try:
        await websocket.send_json(deprecation_message)
        await asyncio.sleep(0.5)  # Give client time to process the message
        
        # Close with custom redirect code
        await websocket.close(
            code=3000,  # Custom code for endpoint migration
            reason="Please use /ws/v1/examples"
        )
        logger.info("WebSocket redirect: /ws/examples -> /ws/v1/examples")
    except Exception as e:
        logger.error(f"WebSocket redirect error: {e}")

@app.websocket("/ws/v1/examples")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time example updates.
    Clients connect to receive notifications when new examples are available.
    """
    await connection_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle client messages if needed
            data = await websocket.receive_text()
            # For now, we just echo back or ignore client messages
            # The main purpose is to broadcast new examples to clients
            
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)

async def consume_hard_examples():
    """
    Background task to consume hard examples from Kafka using connection pool.
    """
    logger.info("Starting hard examples consumer")
    
    async def process_message(topic: str, message: str, key: Optional[str]):
        """Process individual Kafka message."""
        try:
            data = json.loads(message)
            logger.debug(f"Received hard example: {data.get('event_id')}")
            
            # Store in database using annotation service
            db_gen = get_db()
            db = next(db_gen)
            try:
                example = AnnotationService.create_example_from_kafka(data, db)
                logger.info(f"Stored hard example: {example.example_id}")
                
                # Store notification in Redis for WebSocket broadcasting
                # This allows any instance to pick up and broadcast to its clients
                await redis_retry_service.publish_new_example_notification(data)
                
            finally:
                db.close()
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Kafka message: {e}")
        except Exception as e:
            logger.error(f"Error processing hard example: {e}")
    
    # Consume messages continuously
    while True:
        try:
            await kafka_pool.consume_messages(process_message, timeout_ms=5000)
            await asyncio.sleep(1)  # Brief pause between polling
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
            await asyncio.sleep(5)  # Wait before retrying

# Authentication endpoints
@app.post(
    "/api/v1/login", 
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        422: {"model": ValidationErrorResponse, "description": "Invalid credentials format"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    },
    summary="Authenticate user",
    description="Authenticate user with username and password, returns JWT access token"
)
@rate_limit_authentication()
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticate user and return JWT token.
    Rate limited to 20 requests per minute per IP.
    """
    logger.info(f"Login attempt for user: {form_data.username}")
    
    # Authenticate user
    user_data = authenticate_user(form_data.username, form_data.password)
    if not user_data:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(user_data)
    logger.info(f"Successful login for user: {form_data.username}", user_id=user_data.sub)
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=28800  # 8 hours
    )

@app.get(
    "/api/v1/csrf-token",
    response_model=CSRFTokenResponse,
    summary="Get CSRF token",
    description="Get CSRF token for form submissions to prevent CSRF attacks"
)
async def get_csrf_token(request: Request):
    """
    Get CSRF token for form submissions.
    """
    csrf_token = csrf_protect.generate_csrf()
    response = JSONResponse(
        content={"csrf_token": csrf_token}
    )
    csrf_protect.set_csrf_cookie(csrf_token, response)
    return response

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page for authentication."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    """Main annotation interface."""
    pending_count = db.query(AnnotationExample).filter(
        AnnotationExample.status == AnnotationStatus.PENDING
    ).count()
    
    return templates.TemplateResponse("annotation.html", {
        "request": request,
        "pending_count": pending_count,
        "config": settings
    })

# Health and readiness endpoints
@app.get("/healthz")
async def health_check():
    """
    Health check endpoint - returns 200 if the application is running.
    This is used by load balancers and orchestrators to check if the service is alive.
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/readyz")
async def readiness_check():
    """
    Readiness check endpoint - returns 200 only if the service is ready to serve traffic.
    Checks Redis connectivity and Kafka consumer assignment.
    """
    checks = {
        "redis": {"status": "unknown", "details": {}},
        "kafka_consumer": {"status": "unknown", "details": {}},
        "overall": {"status": "not_ready"}
    }
    
    ready = True
    
    # Check Redis connectivity
    try:
        redis_connected = await redis_retry_service.check_connectivity()
        if redis_connected:
            checks["redis"]["status"] = "healthy"
            checks["redis"]["details"] = {"connected": True}
        else:
            checks["redis"]["status"] = "unhealthy"
            checks["redis"]["details"] = {"connected": False}
            ready = False
    except Exception as e:
        checks["redis"]["status"] = "error"
        checks["redis"]["details"] = {"error": str(e)}
        ready = False
    
    # Check Kafka consumer health
    try:
        consumer_health = await kafka_pool.check_consumer_health()
        if consumer_health.get("consumer_assigned", False):
            checks["kafka_consumer"]["status"] = "healthy"
            checks["kafka_consumer"]["details"] = consumer_health
        else:
            checks["kafka_consumer"]["status"] = "unhealthy"
            checks["kafka_consumer"]["details"] = consumer_health
            ready = False
    except Exception as e:
        checks["kafka_consumer"]["status"] = "error"
        checks["kafka_consumer"]["details"] = {"error": str(e)}
        ready = False
    
    # Overall status
    if ready:
        checks["overall"]["status"] = "ready"
        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": checks
            }
        )
    else:
        checks["overall"]["status"] = "not_ready"
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": checks
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
