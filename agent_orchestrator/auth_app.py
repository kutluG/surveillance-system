"""
Integration script for authenticated endpoints.

This script integrates the authenticated endpoints with the main FastAPI application
and provides configuration for API key authentication.

Author: Agent Orchestrator Team
Version: 1.0.0
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
import logging

from .auth_endpoints import auth_router
from .auth import AuthenticationError, AuthorizationError
from .config import get_config

logger = logging.getLogger(__name__)


def setup_authentication(app: FastAPI):
    """
    Set up authentication middleware and error handlers for the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    config = get_config()
    
    # Add authentication router
    app.include_router(auth_router, prefix="", tags=["Authentication"])
    
    # Add authentication error handlers
    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        """Handle authentication errors."""
        logger.warning(f"Authentication failed for {request.url.path}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "authentication_failed",
                "message": exc.detail,
                "timestamp": "2024-01-15T10:30:00Z"
            },
            headers=exc.headers
        )
    
    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(request: Request, exc: AuthorizationError):
        """Handle authorization errors."""
        logger.warning(f"Authorization failed for {request.url.path}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "authorization_failed",
                "message": exc.detail,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    # Add security middleware
    if config.enable_rate_limiting:
        # Rate limiting is handled per-API-key in the auth module
        logger.info("API key-based rate limiting enabled")
    
    # Add CORS middleware for authenticated endpoints
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    logger.info("Authentication system initialized")


def create_authenticated_app() -> FastAPI:
    """
    Create a FastAPI application with authentication enabled.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Agent Orchestrator Service (Authenticated)",
        description="""
        **Authenticated Agent Orchestrator Service**
        
        This service provides secure, API key-based access to agent orchestration
        capabilities. All endpoints require valid API key authentication.
        
        ## Authentication
        
        All endpoints require a valid API key in the Authorization header:
        ```
        Authorization: Bearer <your-api-key>
        ```
        
        ## Permissions
        
        Different endpoints require different permissions:
        - `agent:read` - Read agent information
        - `agent:write` - Update agent information
        - `agent:register` - Register new agents
        - `agent:delete` - Delete agents
        - `task:read` - Read task information
        - `task:create` - Create new tasks
        - `admin` - Administrative operations
        
        ## Rate Limiting
        
        API keys have individual rate limits. Exceeding the limit will result in
        HTTP 401 responses.
        
        ## Getting Started
        
        1. Obtain an API key from your administrator
        2. Include the key in the Authorization header
        3. Use the endpoints according to your permissions
        
        For API key management, use the CLI tool:
        ```bash
        python -m agent_orchestrator.api_key_manager create --name "My Key"
        ```
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Set up authentication
    setup_authentication(app)
    
    return app


# Example usage for testing
if __name__ == "__main__":
    import uvicorn
    
    app = create_authenticated_app()
    
    # Run the authenticated service
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # Different port from main service
        log_level="info"
    )
