"""
Dependency Injection Utilities

This module provides comprehensive dependency injection functions for FastAPI
endpoints, managing external service clients, database sessions, and connection
pooling. It implements the singleton pattern for resource management and provides
clean interfaces for service dependencies.

The module handles initialization and lifecycle management of external services
including Redis, OpenAI, Weaviate, and database connections. It ensures proper
resource cleanup and provides fallback mechanisms for service unavailability.

Key Features:
- Singleton pattern for external service clients
- Lazy initialization with connection pooling
- Error handling and fallback mechanisms
- Proper resource lifecycle management
- Database session management with async support
- Redis connection management for caching
- OpenAI client initialization for AI services
- Weaviate client setup for vector operations

Functions:
    get_redis: Provides Redis client with connection pooling
    get_openai_client: Manages OpenAI API client initialization
    get_weaviate_client: Handles Weaviate vector database connections
    get_database: Provides async database session management
    cleanup_connections: Manages resource cleanup on shutdown
    
Dependencies:
    - FastAPI: For dependency injection framework
    - Redis: For caching and session management
    - OpenAI: For AI service integration
    - SQLAlchemy: For database ORM operations
    - Weaviate: For vector search capabilities (optional)
"""

import logging
from typing import AsyncGenerator

from fastapi import Depends
from redis.asyncio import Redis
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config.config import settings

logger = logging.getLogger(__name__)

# Global instances
_redis_client: Redis = None
_openai_client: AsyncOpenAI = None
_async_engine = None
_session_maker = None


def get_redis() -> Redis:
    """
    Get Redis client instance with connection pooling.
    
    Implements singleton pattern to ensure single Redis connection throughout
    the application lifecycle. Provides connection pooling for performance
    optimization and handles connection errors gracefully.
    
    :return: Redis client instance configured with application settings
    :raises ConnectionError: If Redis connection cannot be established
    
    Example:
        >>> redis_client = get_redis()
        >>> await redis_client.set("key", "value")
        >>> value = await redis_client.get("key")
    """
    global _redis_client
    if _redis_client is None:
        try:
            # Initialize Redis client with connection pooling
            _redis_client = Redis.from_url(settings.REDIS_URL)
            logger.info("Redis client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise ConnectionError(f"Redis connection failed: {e}")
    return _redis_client


def get_openai_client() -> AsyncOpenAI:
    """
    Get OpenAI async client instance for AI services.
    
    Manages OpenAI API client initialization with proper error handling and
    singleton pattern implementation. Configures client with API key from
    application settings and provides async support for non-blocking operations.
    
    :return: AsyncOpenAI client configured for surveillance system AI operations
    :raises ValueError: If OpenAI API key is not configured
    :raises ConnectionError: If OpenAI API cannot be reached
    
    Example:
        >>> openai_client = get_openai_client()
        >>> response = await openai_client.chat.completions.create(
        ...     model="gpt-3.5-turbo",
        ...     messages=[{"role": "user", "content": "Hello"}]
        ... )
    """
    global _openai_client
    if _openai_client is None:
        try:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key not configured")
            
            # Initialize async OpenAI client for non-blocking operations
            _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    return _openai_client


def get_weaviate_client():
    """Get Weaviate client instance"""
    try:
        import weaviate
        client = weaviate.Client(url=settings.WEAVIATE_URL)
        logger.info("Weaviate client initialized")
        return client
    except ImportError:
        logger.warning("Weaviate not installed, returning None")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Weaviate client: {e}")
        return None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    global _async_engine, _session_maker
    
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True
        )
        _session_maker = sessionmaker(
            _async_engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        logger.info("Database engine initialized")
    
    async with _session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


# Service Dependencies
from ..services.analytics import AnalyticsService
from ..services.llm_client import LLMService
from ..services.dashboard import DashboardService


def get_analytics_service(
    db: AsyncSession = Depends(get_db_session),
    redis_client: Redis = Depends(get_redis)
) -> AnalyticsService:
    """Get analytics service instance"""
    return AnalyticsService(db, redis_client)


def get_llm_service(
    openai_client: AsyncOpenAI = Depends(get_openai_client)
) -> LLMService:
    """Get LLM service instance"""
    return LLMService(openai_client)


def get_dashboard_service(
    db: AsyncSession = Depends(get_db_session),
    redis_client: Redis = Depends(get_redis),
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    weaviate_client = Depends(get_weaviate_client)
) -> DashboardService:
    """Get dashboard service instance"""
    return DashboardService(db, redis_client, openai_client, weaviate_client)


async def cleanup_dependencies():
    """Cleanup all dependency resources"""
    global _redis_client, _openai_client, _async_engine
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")
    
    # OpenAI client doesn't need explicit cleanup
    if _openai_client:
        _openai_client = None
        logger.info("OpenAI client cleaned up")
    
    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        logger.info("Database engine disposed")
