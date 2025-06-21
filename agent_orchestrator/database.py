"""
Database Connection Management with Dependency Injection

This module provides robust database session management with proper dependency injection,
connection pooling, transaction handling, and monitoring.

Features:
- Proper database session lifecycle management
- Connection pool monitoring and health checks
- Transaction context managers
- Dependency injection for FastAPI endpoints
- Connection leak prevention
- Graceful shutdown handling
- Metrics collection for connection usage
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import weakref

from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    AsyncEngine,
    async_scoped_session
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError

# Import metrics if available
try:
    from prometheus_client import Counter, Histogram, Gauge
    DB_CONNECTIONS_ACTIVE = Gauge(
        'agent_orchestrator_db_connections_active',
        'Number of active database connections'
    )
    DB_CONNECTIONS_CREATED = Counter(
        'agent_orchestrator_db_connections_created_total',
        'Total database connections created'
    )
    DB_CONNECTIONS_CLOSED = Counter(
        'agent_orchestrator_db_connections_closed_total',
        'Total database connections closed'
    )
    DB_TRANSACTION_DURATION = Histogram(
        'agent_orchestrator_db_transaction_duration_seconds',
        'Database transaction duration',
        ['operation_type']
    )
    DB_QUERY_DURATION = Histogram(
        'agent_orchestrator_db_query_duration_seconds',
        'Database query duration'
    )
    DB_CONNECTION_ERRORS = Counter(
        'agent_orchestrator_db_connection_errors_total',
        'Database connection errors',
        ['error_type']
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

from config import get_config

logger = logging.getLogger(__name__)


@dataclass
class DatabasePoolStats:
    """Database connection pool statistics"""
    pool_size: int
    checked_in: int
    checked_out: int
    overflow: int
    invalid: int


@dataclass
class DatabaseConnectionInfo:
    """Database connection information for monitoring"""
    connection_id: str
    created_at: datetime
    last_used: datetime
    transaction_count: int
    query_count: int
    is_active: bool


class DatabaseManager:
    """
    Database manager with dependency injection and robust connection handling
    """
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._scoped_session: Optional[async_scoped_session] = None
        self._config = get_config()
        self._active_sessions: weakref.WeakSet = weakref.WeakSet()
        self._connection_info: Dict[str, DatabaseConnectionInfo] = {}
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self) -> None:
        """Initialize database engine and session factory"""
        if self._engine is not None:
            logger.warning("Database manager already initialized")
            return
            
        try:
            # Create engine with optimized settings
            self._engine = create_async_engine(
                self._config.database_url,
                
                # Connection pool settings
                poolclass=QueuePool,
                pool_size=self._config.db_pool_size if hasattr(self._config, 'db_pool_size') else 10,
                max_overflow=self._config.db_max_overflow if hasattr(self._config, 'db_max_overflow') else 20,
                pool_timeout=self._config.db_pool_timeout if hasattr(self._config, 'db_pool_timeout') else 30,
                pool_recycle=self._config.db_pool_recycle if hasattr(self._config, 'db_pool_recycle') else 3600,
                pool_pre_ping=True,  # Validate connections before use
                
                # Connection settings
                connect_args={
                    "server_settings": {
                        "application_name": "agent_orchestrator",
                    }
                } if "postgresql" in self._config.database_url else {},
                
                # Logging and debugging
                echo=self._config.log_level == "DEBUG",
                echo_pool=self._config.log_level == "DEBUG",
                
                # Performance settings
                future=True,
            )
            
            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            # Create scoped session for thread-safe access
            self._scoped_session = async_scoped_session(
                self._session_factory,
                scopefunc=asyncio.current_task
            )
            
            # Set up connection event listeners for monitoring
            self._setup_connection_listeners()
            
            # Test connection
            await self._test_connection()
            
            logger.info("Database manager initialized successfully")
            
            if METRICS_AVAILABLE:
                DB_CONNECTIONS_CREATED.inc()
                
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            if METRICS_AVAILABLE:
                DB_CONNECTION_ERRORS.labels(error_type="initialization").inc()
            raise
    
    def _setup_connection_listeners(self) -> None:
        """Set up SQLAlchemy event listeners for connection monitoring"""
        
        @event.listens_for(self._engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Handle new database connections"""
            connection_id = str(id(dbapi_connection))
            self._connection_info[connection_id] = DatabaseConnectionInfo(
                connection_id=connection_id,
                created_at=datetime.utcnow(),
                last_used=datetime.utcnow(),
                transaction_count=0,
                query_count=0,
                is_active=True
            )
            
            if METRICS_AVAILABLE:
                DB_CONNECTIONS_ACTIVE.inc()
                DB_CONNECTIONS_CREATED.inc()
            
            logger.debug(f"Database connection created: {connection_id}")
        
        @event.listens_for(self._engine.sync_engine, "close")
        def on_close(dbapi_connection, connection_record):
            """Handle database connection closure"""
            connection_id = str(id(dbapi_connection))
            
            if connection_id in self._connection_info:
                self._connection_info[connection_id].is_active = False
                del self._connection_info[connection_id]
            
            if METRICS_AVAILABLE:
                DB_CONNECTIONS_ACTIVE.dec()
                DB_CONNECTIONS_CLOSED.inc()
            
            logger.debug(f"Database connection closed: {connection_id}")
    
    async def _test_connection(self) -> None:
        """Test database connection during initialization"""
        async with self.get_session() as session:
            result = await session.execute(text("SELECT 1"))
            if result.scalar() != 1:
                raise RuntimeError("Database connection test failed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with proper lifecycle management
        
        This is the main method for getting database sessions with dependency injection.
        It ensures proper cleanup and error handling.
        """
        if self._scoped_session is None:
            raise RuntimeError("Database manager not initialized")
        
        session = self._scoped_session()
        self._active_sessions.add(session)
        
        try:
            if METRICS_AVAILABLE:
                start_time = asyncio.get_event_loop().time()
            
            yield session
            
            # Commit if no exceptions occurred
            await session.commit()
            
            if METRICS_AVAILABLE:
                duration = asyncio.get_event_loop().time() - start_time
                DB_TRANSACTION_DURATION.labels(operation_type="commit").observe(duration)
                
        except Exception as e:
            # Rollback on any exception
            await session.rollback()
            
            if METRICS_AVAILABLE:
                duration = asyncio.get_event_loop().time() - start_time
                DB_TRANSACTION_DURATION.labels(operation_type="rollback").observe(duration)
                DB_CONNECTION_ERRORS.labels(error_type="transaction").inc()
            
            logger.error(f"Database transaction error: {e}")
            raise
            
        finally:
            await session.close()
            await self._scoped_session.remove()
    
    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with explicit transaction control
        
        Use this when you need explicit transaction boundaries.
        """
        async with self.get_session() as session:
            async with session.begin():
                yield session
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a query with proper session management
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Query result
        """
        async with self.get_session() as session:
            if METRICS_AVAILABLE:
                start_time = asyncio.get_event_loop().time()
            
            try:
                result = await session.execute(text(query), params or {})
                
                if METRICS_AVAILABLE:
                    duration = asyncio.get_event_loop().time() - start_time
                    DB_QUERY_DURATION.observe(duration)
                
                return result
                
            except Exception as e:
                if METRICS_AVAILABLE:
                    DB_CONNECTION_ERRORS.labels(error_type="query").inc()
                raise
    
    async def get_pool_stats(self) -> DatabasePoolStats:
        """Get connection pool statistics"""
        if self._engine is None:
            raise RuntimeError("Database manager not initialized")
        
        pool = self._engine.pool
        return DatabasePoolStats(
            pool_size=pool.size(),
            checked_in=pool.checkedin(),
            checked_out=pool.checkedout(),
            overflow=pool.overflow(),
            invalid=pool.invalid()
        )
    
    async def get_connection_info(self) -> Dict[str, DatabaseConnectionInfo]:
        """Get information about active connections"""
        return self._connection_info.copy()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive database health check
        
        Returns:
            Health check results with detailed statistics
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Test basic connectivity
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1 as health_check"))
                health_result = result.scalar()
                
                if health_result != 1:
                    return {
                        "status": "unhealthy",
                        "message": "Database query returned unexpected result"
                    }
            
            # Get pool statistics
            pool_stats = await self.get_pool_stats()
            connection_info = await self.get_connection_info()
            
            query_time = asyncio.get_event_loop().time() - start_time
            
            return {
                "status": "healthy",
                "message": "Database connection successful",
                "response_time": round(query_time, 3),
                "pool_stats": {
                    "pool_size": pool_stats.pool_size,
                    "checked_in": pool_stats.checked_in,
                    "checked_out": pool_stats.checked_out,
                    "overflow": pool_stats.overflow,
                    "invalid": pool_stats.invalid
                },
                "active_connections": len(connection_info),
                "active_sessions": len(self._active_sessions)
            }
            
        except Exception as e:
            if METRICS_AVAILABLE:
                DB_CONNECTION_ERRORS.labels(error_type="health_check").inc()
            
            return {
                "status": "unhealthy",
                "message": "Database health check failed",
                "error": str(e)
            }
    
    async def close(self) -> None:
        """
        Gracefully close database connections and clean up resources
        """
        logger.info("Shutting down database manager...")
        
        self._shutdown_event.set()
        
        # Close all active sessions
        active_sessions = list(self._active_sessions)
        for session in active_sessions:
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
        
        # Close scoped session
        if self._scoped_session:
            await self._scoped_session.remove()
        
        # Dispose engine
        if self._engine:
            await self._engine.dispose()
            self._engine = None
        
        self._session_factory = None
        self._scoped_session = None
        self._connection_info.clear()
        
        logger.info("Database manager shutdown complete")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


async def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()
    
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions
    
    This is the main dependency to use in FastAPI endpoints:
    
    @app.get("/example")
    async def example_endpoint(db: AsyncSession = Depends(get_db_session)):
        # Use db session here
        pass
    """
    db_manager = await get_database_manager()
    async with db_manager.get_session() as session:
        yield session


async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database transactions
    
    Use when you need explicit transaction control:
    
    @app.post("/example")
    async def example_endpoint(db: AsyncSession = Depends(get_db_transaction)):
        # All operations will be in a single transaction
        pass
    """
    db_manager = await get_database_manager()
    async with db_manager.get_transaction() as session:
        yield session


@asynccontextmanager
async def database_lifespan():
    """
    Application lifespan context manager for database
    
    Use this with FastAPI's lifespan parameter:
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with database_lifespan():
            yield
    
    app = FastAPI(lifespan=lifespan)
    """
    global _db_manager
    
    try:
        # Initialize database manager
        if _db_manager is None:
            _db_manager = DatabaseManager()
            await _db_manager.initialize()
        
        yield
        
    finally:
        # Clean up database manager
        if _db_manager is not None:
            await _db_manager.close()
            _db_manager = None


# Utility functions for common database operations
async def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Execute a query using the global database manager"""
    db_manager = await get_database_manager()
    return await db_manager.execute_query(query, params)


async def get_database_health() -> Dict[str, Any]:
    """Get database health status"""
    try:
        db_manager = await get_database_manager()
        return await db_manager.health_check()
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": "Database manager not available",
            "error": str(e)
        }
