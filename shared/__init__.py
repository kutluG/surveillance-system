# Shared utilities package
"""
Shared utilities and components for the surveillance system microservices.

This package provides common functionality including:
- Authentication and authorization (auth.py)
- Configuration management (config.py)
- Logging setup (logging_config.py)
- Metrics collection (metrics.py)
- Middleware components (middleware/)
- Data models (models.py)
- Distributed tracing (tracing.py)
"""

# Import middleware components for easy access
from . import middleware

__version__ = "1.0.0"
__all__ = ["middleware"]
