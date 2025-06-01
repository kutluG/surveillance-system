"""
Structured logging setup using structlog for all services.
"""
import logging
import sys
from typing import Any

import structlog

def _configure_stdlib_logger() -> None:
    """
    Configure the standard library logging to write to stdout and
    let structlog wrap it for structured JSON output.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    # Reduce verbosity of libraries
    for noisy in ("uvicorn.access", "uvicorn.error", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

def _configure_structlog() -> None:
    """
    Configure structlog to emit JSON-formatted logs with timestamps,
    log levels, exception info, and service context.
    """
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,             # add "level"
            structlog.processors.TimeStamper(fmt="iso"),    # add "timestamp"
            structlog.processors.StackInfoRenderer(),       # add "stack_info" if requested
            structlog.processors.format_exc_info,           # format exception info
            structlog.processors.UnicodeDecoder(),          # ensure unicode
            structlog.processors.JSONRenderer(),            # output JSON
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )

# Perform one-time configuration on import
_configure_stdlib_logger()
_configure_structlog()

def get_logger(service: str) -> structlog.BoundLogger:
    """
    Get a structlog logger pre-bound with a service name.
    :param service: Name of the service (e.g., "edge_service").
    :return: A BoundLogger instance.
    """
    return structlog.get_logger().bind(service=service)