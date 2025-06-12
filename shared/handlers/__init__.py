"""
Logging handlers for enterprise surveillance system.

This package provides specialized logging handlers including:
- WORMLogHandler: Immutable audit log storage with AWS S3 Object Lock
- S3WORMSetup: S3 bucket configuration utilities
"""

try:
    from .worm_log_handler import WORMLogHandler, WORMLogHandlerFactory, add_worm_logging
    WORM_HANDLER_AVAILABLE = True
except ImportError:
    # WORM handler requires boto3, which may not be available in all environments
    WORM_HANDLER_AVAILABLE = False

__all__ = []

if WORM_HANDLER_AVAILABLE:
    __all__.extend(['WORMLogHandler', 'WORMLogHandlerFactory', 'add_worm_logging'])
