"""
AI Dashboard Service Main Module

This is the main entry point for the AI Dashboard Service application, providing
advanced analytics, predictive insights, and intelligent reporting capabilities
for surveillance systems. The service uses a modular architecture with clean
separation of concerns across multiple packages.

The application provides comprehensive dashboard functionality including:
- Real-time analytics and trend analysis
- Anomaly detection with ML algorithms
- Predictive analytics for threat assessment
- AI-powered report generation
- Interactive dashboard widgets and visualizations

Architecture:
- Modular design with separate packages for models, services, routers, and utils
- Dependency injection for clean service management
- FastAPI framework for high-performance async API operations
- Comprehensive middleware stack for security and performance
- Integration with external services (OpenAI, Redis, Weaviate)

Key Features:
- RESTful API with OpenAPI documentation
- CORS support for web integration
- Rate limiting and security middleware
- Comprehensive error handling and logging
- Health checks and monitoring endpoints
- Async operations for optimal performance

Modules:
    routers: API endpoint definitions and request handling
    services: Business logic and service layer implementations
    models: Data models, schemas, and validation
    utils: Utility functions and dependency injection
    config: Configuration management and settings
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import dashboard_router
from .utils.dependencies import cleanup_dependencies
from config.config import settings

# Import shared middleware for rate limiting (optional)
try:
    from shared.middleware import add_rate_limiting
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False
    add_rate_limiting = None

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application with comprehensive middleware.
    
    Initializes the FastAPI application with all necessary middleware, routing,
    and configuration for the AI Dashboard Service. Sets up CORS, rate limiting,
    dependency injection, and error handling for production-ready deployment.
    
    :return: Configured FastAPI application instance ready for deployment
    :raises ImportError: If required dependencies are not available
    
    Example:
        >>> app = create_app()
        >>> # Application ready for uvicorn server
    """      # Initialize FastAPI application with comprehensive metadata
    # Provides OpenAPI documentation and service information
    app = FastAPI(
        title="AI Dashboard Features",
        description="Advanced analytics, predictions, and intelligent reporting for surveillance systems",
        version="1.0.0"
    )

    # Configure CORS middleware for cross-origin requests
    # Essential for web dashboard integration and API access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,  # Configurable origins from settings
        allow_credentials=True,               # Allow cookies and authentication
        allow_methods=["*"],                  # Allow all HTTP methods
        allow_headers=["*"],                  # Allow all headers
    )
    
    # Add rate limiting middleware if enabled and available
    # Protects against API abuse and ensures fair resource usage
    if settings.RATE_LIMIT_ENABLED and RATE_LIMITING_AVAILABLE:
        add_rate_limiting(app, service_name="ai_dashboard_service")
        logger.info("Rate limiting middleware enabled")
    else:
        logger.warning("Rate limiting not available or disabled")

    # Include routers
    app.include_router(dashboard_router)

    # Event handlers
    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup"""
        logger.info("Starting AI Dashboard Service")
        # Initialize any necessary resources here    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on application shutdown"""
        logger.info("Shutting down AI Dashboard Service")
        await cleanup_dependencies()

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=True
    )
