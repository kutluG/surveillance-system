"""
Utils Package

Contains shared utility functions and helper modules.
"""

from .database import get_redis_client, get_database_session, close_connections
from .helpers import (
    generate_uuid, current_timestamp, format_timestamp,
    safe_dict_get, validate_time_range, calculate_percentage,
    flatten_dict, chunks
)

__all__ = [
    "get_redis_client", "get_database_session", "close_connections",
    "generate_uuid", "current_timestamp", "format_timestamp",
    "safe_dict_get", "validate_time_range", "calculate_percentage",
    "flatten_dict", "chunks"
]
