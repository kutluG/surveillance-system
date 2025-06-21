"""
Legacy Database Utilities - DEPRECATED

This module is deprecated. Use app.utils.dependencies instead.
All database connection and session management has been moved to the dependency injection system.
"""

import warnings

warnings.warn(
    "This module is deprecated. Use app.utils.dependencies for database connections.",
    DeprecationWarning,
    stacklevel=2
)

# Keep imports for backward compatibility but redirect to new system
from .dependencies import get_redis, get_db_session, cleanup_dependencies

# Legacy aliases - these should not be used in new code
async def get_redis_client():
    """DEPRECATED: Use dependencies.get_redis() instead"""
    warnings.warn("get_redis_client is deprecated. Use dependencies.get_redis()", DeprecationWarning)
    return get_redis()

async def get_database_session():
    """DEPRECATED: Use dependencies.get_db_session() instead"""
    warnings.warn("get_database_session is deprecated. Use dependencies.get_db_session()", DeprecationWarning)
    async for session in get_db_session():
        return session

async def close_connections():
    """DEPRECATED: Use dependencies.cleanup_dependencies() instead"""
    warnings.warn("close_connections is deprecated. Use dependencies.cleanup_dependencies()", DeprecationWarning)
    await cleanup_dependencies()
