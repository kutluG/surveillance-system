"""
Helper Utilities

This module contains shared utility functions used throughout the application.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List


def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())


def current_timestamp() -> str:
    """Get current timestamp as ISO string"""
    return datetime.utcnow().isoformat()


def format_timestamp(dt: datetime) -> str:
    """Format datetime as ISO string"""
    return dt.isoformat()


def safe_dict_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary"""
    return data.get(key, default)


def validate_time_range(start_time: datetime, end_time: datetime) -> bool:
    """Validate that start time is before end time"""
    return start_time < end_time


def calculate_percentage(part: float, total: float) -> float:
    """Calculate percentage with division by zero protection"""
    if total == 0:
        return 0.0
    return (part / total) * 100


def flatten_dict(data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """Flatten nested dictionary"""
    result = {}
    for key, value in data.items():
        new_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_dict(value, new_key))
        else:
            result[new_key] = value
    return result


def chunks(lst: List[Any], n: int) -> List[List[Any]]:
    """Split list into chunks of size n"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
