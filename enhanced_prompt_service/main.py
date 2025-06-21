"""
Enhanced Prompt Service: Advanced conversational AI with context and follow-ups.
"""
from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from typing import List, Optional, Dict, Any
import json
import uuid
import re
import os
import redis
import redis.asyncio
import weaviate
from openai import OpenAI
from urllib.parse import urlparse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from tenacity import retry, stop_after_attempt, wait_exponential

from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.models import QueryResult
from shared.auth import get_current_user, TokenData
from shared.middleware import add_rate_limiting
from shared.config import get_service_config, Settings

from enhanced_prompt_service.conversation_manager import ConversationManager
from enhanced_prompt_service.schemas import HealthResponse, ErrorResponse
from enhanced_prompt_service.routers import prompt, history

# Get service configuration
config = get_service_config("enhanced_prompt_service")
settings = Settings()

# Configure logging first
logger = configure_logging("enhanced_prompt_service")

# Dependency injection functions
async def get_redis(request: Request) -> redis.Redis:
    """Get Redis client from app state."""
    return request.app.state.redis_client

async def get_weaviate(request: Request):
    """Get Weaviate client from app state."""
    return request.app.state.weaviate_client

async def get_openai(request: Request) -> OpenAI:
    """Get OpenAI client from app state."""
    return request.app.state.openai_client

async def get_conversation_manager(request: Request) -> ConversationManager:
    """Get ConversationManager from app state."""
    return request.app.state.conversation_manager

async def startup_event():
    """Initialize all external service connections on startup."""
    logger.info("Starting Enhanced Prompt Service...")
    
    try:
        # Initialize Redis client with async support
        redis_url = settings.redis_url
        parsed_url = urlparse(redis_url)
        redis_client = redis.asyncio.Redis(
            host=parsed_url.hostname or 'redis',
            port=parsed_url.port or 6379,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        # Test Redis connection
        await redis_client.ping()
        logger.info("Redis connection established")
        
        # Initialize Weaviate client
        weaviate_client = weaviate.connect_to_local(
            host=parsed_url.hostname or 'localhost',
            port=8080,
            grpc_port=50051
        ) if settings.weaviate_url.startswith('http://localhost') else weaviate.connect_to_custom(
            http_host=urlparse(settings.weaviate_url).hostname,
            http_port=urlparse(settings.weaviate_url).port or 8080,
            http_secure=settings.weaviate_url.startswith('https'),
            grpc_host=urlparse(settings.weaviate_url).hostname,
            grpc_port=50051,
            grpc_secure=settings.weaviate_url.startswith('https')
        )
        
        # Test Weaviate connection
        if not weaviate_client.is_ready():
            raise Exception("Weaviate is not ready")
        logger.info("Weaviate connection established")
        
        # Initialize OpenAI client
        openai_client = OpenAI(api_key=settings.openai_api_key)
        logger.info("OpenAI client initialized")
        
        # Initialize ConversationManager with async Redis client
        conversation_manager = ConversationManager(redis_client)
        logger.info("ConversationManager initialized")
        
        # Store clients in app state
        app.state.redis_client = redis_client
        app.state.weaviate_client = weaviate_client
        app.state.openai_client = openai_client
        app.state.conversation_manager = conversation_manager
        
        logger.info("Enhanced Prompt Service startup complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

async def shutdown_event():
    """Clean up connections on shutdown."""
    logger.info("Shutting down Enhanced Prompt Service...")
    
    try:
        # Close Weaviate connection
        if hasattr(app.state, 'weaviate_client'):
            app.state.weaviate_client.close()
            logger.info("Weaviate connection closed")
        
        # Redis connections are automatically managed
        logger.info("Enhanced Prompt Service shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(
    title="Enhanced Prompt Service",
    description="Advanced conversational AI with context and follow-ups for surveillance systems",
    version="1.3.0",
    contact={
        "name": "Surveillance System Team",
        "email": "support@surveillance-system.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler that returns uniform JSON error responses."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Handle different types of exceptions
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,            content=ErrorResponse(
                error=exc.detail,
                detail=str(exc.detail),
                code=str(exc.status_code)
            ).model_dump()
        )
    elif isinstance(exc, ValueError):
        return JSONResponse(
            status_code=500,            content=ErrorResponse(
                error="Internal server error",
                detail="A validation error occurred",
                code="500"
            ).model_dump()
        )
    else:
        return JSONResponse(
            status_code=500,            content=ErrorResponse(
                error="Internal server error",
                detail="An unexpected error occurred",
                code="500"
            ).model_dump()
        )

# Handle 404 errors
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 Not Found errors."""
    return JSONResponse(
        status_code=404,        content=ErrorResponse(
            error="Not Found",
            detail="The requested resource was not found",
            code="404"
        ).model_dump()
    )

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS with strict policy
allowed_origins = [
    "https://surveillance-dashboard.local",
    "https://localhost:3000",  # For development
    "https://127.0.0.1:3000",  # For development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Custom OpenAPI schema generation
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Enhanced Prompt Service API",
        version="1.3.0",
        description="""
        ## Enhanced Prompt Service

        A sophisticated conversational AI service that provides intelligent, context-aware responses 
        for surveillance system queries. This service combines semantic search, large language models, 
        and conversation memory to deliver enhanced user experiences.

        ### Key Features:
        - **Semantic Search**: Vector-based search through surveillance events
        - **Conversational AI**: Context-aware responses with conversation memory
        - **Clip Integration**: Automatic video clip URL generation
        - **Follow-up Questions**: Intelligent suggestion of relevant next questions
        - **Proactive Insights**: Pattern detection and anomaly identification

        ### Authentication:
        All endpoints require a valid JWT token in the Authorization header:
        ```
        Authorization: Bearer YOUR_JWT_TOKEN
        ```

        ### Rate Limiting:
        - 100 requests per minute per user
        - 20 requests per 10 seconds burst limit
        """,
        routes=app.routes,
        contact={
            "name": "Surveillance System Team",
            "email": "support@surveillance-system.com",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    )
    
    # Add additional schema customizations
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Export OpenAPI schema on startup (for CI/CD and documentation)
@app.on_event("startup")
async def export_openapi_schema():
    """Export OpenAPI schema to JSON file for documentation and tooling."""
    try:
        docs_dir = os.path.join(os.path.dirname(__file__), "docs")
        os.makedirs(docs_dir, exist_ok=True)
        
        schema_path = os.path.join(docs_dir, "enhanced_prompt_openapi.json")
        
        # Generate and save OpenAPI schema
        openapi_schema = custom_openapi()
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
        
        logger.info(f"OpenAPI schema exported to {schema_path}")
    except Exception as e:
        logger.warning(f"Failed to export OpenAPI schema: {e}")

# Add audit middleware
add_audit_middleware(app, service_name="enhanced_prompt_service")
instrument_app(app, service_name="enhanced_prompt_service")

# Add rate limiting middleware
add_rate_limiting(app, service_name="enhanced_prompt_service")

# Include routers with versioned paths
app.include_router(
    prompt.router,
    prefix=settings.api_base_path,
    tags=["prompt"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    history.router,
    prefix=f"{settings.api_base_path}/history",
    tags=["history"],
    dependencies=[Depends(get_current_user)]
)

# Legacy redirect handlers for unversioned API paths
@app.get("/api/{path:path}")
async def redirect_unversioned_api(path: str):
    """Redirect legacy unversioned API paths to versioned ones."""
    target = f"{settings.api_base_path}/{path}"
    logger.info(f"Redirecting legacy API path /api/{path} to {target}")
    return RedirectResponse(url=target, status_code=301)

# WebSocket redirect handler for future WebSocket endpoints
@app.websocket("/ws/{path:path}")
async def redirect_unversioned_websocket(websocket: WebSocket, path: str):
    """Redirect legacy unversioned WebSocket paths to versioned ones."""
    try:
        await websocket.accept()
        target = f"/ws/v1/{path}"
        logger.info(f"WebSocket redirect requested from /ws/{path} to {target}")
        await websocket.close(
            code=3000,  # Custom code for redirect
            reason=f"Redirecting to {target}"
        )
    except Exception as e:
        logger.error(f"Error during WebSocket redirect: {e}")
        try:
            await websocket.close(code=1011, reason="Redirect failed")
        except:
            pass

# Basic health endpoints
@app.get("/health", response_model=HealthResponse)
async def health():
    """Basic health check endpoint - always returns OK if service is running."""
    return HealthResponse(status="ok")

@app.get("/healthz", response_model=HealthResponse)
async def healthz():
    """Kubernetes liveness probe endpoint - checks if service is alive."""
    return HealthResponse(status="ok")

@app.get("/readyz", response_model=HealthResponse)
async def readyz(request: Request):
    """
    Kubernetes readiness probe endpoint.
    Checks if service is ready to serve traffic by testing dependencies.
    Returns 503 if any dependency is unhealthy.
    """
    try:
        # Check Redis connection
        redis_client = request.app.state.redis_client
        if not redis_client:
            logger.error("Redis client is not initialized")
            raise Exception("Redis client is not initialized")
        
        await redis_client.ping()
        logger.debug("Redis ping successful")
        
        # Check Weaviate health  
        weaviate_client = request.app.state.weaviate_client
        if not weaviate_client:
            logger.error("Weaviate client is not initialized")
            raise Exception("Weaviate client is not initialized")
            
        if not weaviate_client.is_ready():
            logger.error("Weaviate is not ready")
            raise Exception("Weaviate is not ready")
        logger.debug("Weaviate is ready")
        
        # Test OpenAI client (lightweight check - just verify client exists)
        # We don't make actual API calls in readiness check to avoid cost/rate limits
        openai_client = request.app.state.openai_client
        if not openai_client:
            logger.error("OpenAI client is not initialized")
            raise Exception("OpenAI client is not initialized")
            
        if not hasattr(openai_client, 'api_key') or not openai_client.api_key:
            logger.error("OpenAI client is not properly configured")
            raise Exception("OpenAI client is not properly configured")
        logger.debug("OpenAI client is configured")
        
        # Test ConversationManager
        conversation_manager = request.app.state.conversation_manager
        if not conversation_manager:
            logger.error("ConversationManager is not initialized")
            raise Exception("ConversationManager is not initialized")
        logger.debug("ConversationManager is initialized")
        
        return HealthResponse(status="ready")
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        # Return 503 Service Unavailable for readiness failures
        raise HTTPException(status_code=503, detail="Service not ready")

# Startup and shutdown events
@app.on_event("startup")
async def startup():
    await startup_event()

@app.on_event("shutdown")
async def shutdown():
    await shutdown_event()
