"""
Enterprise-grade structured logging configuration for FastAPI microservices.
Uses Python's logging library with JSON formatter for consistent, searchable logs.
"""
import logging
import logging.config
import os
import sys
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager

from pythonjsonlogger import jsonlogger


class CorrelationIDFilter(logging.Filter):
    """Filter to inject correlation ID into log records."""
    
    def filter(self, record):
        # Get correlation ID from context (set by middleware)
        correlation_id = getattr(logging._current_context, 'request_id', None)
        if correlation_id:
            record.request_id = correlation_id
        else:
            # Generate a default correlation ID if none exists
            record.request_id = str(uuid.uuid4())
        return True


class ServiceContextFilter(logging.Filter):
    """Filter to inject service context into log records."""
    
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
    
    def filter(self, record):
        record.service_name = self.service_name
        # Add other context if available
        context = getattr(logging._current_context, 'context', {})
        for key, value in context.items():
            setattr(record, key, value)
        return True


class EnhancedJSONFormatter(jsonlogger.JsonFormatter):
    """Enhanced JSON formatter with additional enterprise fields."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        super().add_fields(log_record, record, message_dict)
          # Ensure timestamp is ISO 8601 format
        if 'timestamp' not in log_record:
            from datetime import datetime, timezone
            log_record['timestamp'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # Ensure required fields exist
        log_record.setdefault('service_name', getattr(record, 'service_name', 'unknown'))
        log_record.setdefault('level', record.levelname)
        log_record.setdefault('request_id', getattr(record, 'request_id', str(uuid.uuid4())))
        
        # Add optional context fields if they exist
        for field in ['user_id', 'camera_id', 'action']:
            value = getattr(record, field, None)
            if value is not None:
                log_record[field] = value


# Thread-local storage for request context
logging._current_context = threading.local()


def configure_logging(service_name: str, log_level: str = None, enable_worm: bool = None) -> logging.Logger:
    """
    Configure enterprise-grade structured logging for a service.
    
    Args:
        service_name: Name of the service (from SERVICE_NAME env var)
        log_level: Log level (from LOG_LEVEL env var, defaults to INFO)
        enable_worm: Whether to enable WORM audit logging (from ENABLE_WORM_LOGGING env var)
    
    Returns:
        Configured logger instance
    """
    import threading
    
    # Get configuration from environment
    service_name = service_name or os.getenv('SERVICE_NAME', 'unknown-service')
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO').upper()
    enable_worm = enable_worm if enable_worm is not None else os.getenv('ENABLE_WORM_LOGGING', 'false').lower() == 'true'
    
    # Validate log level
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Create custom JSON formatter - compatible with python-json-logger 3.x
    json_formatter = EnhancedJSONFormatter(
        reserved_attrs=[
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
            'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 
            'relativeCreated', 'thread', 'threadName', 'processName', 'process'
        ]
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(json_formatter)
    
    # Add filters
    correlation_filter = CorrelationIDFilter()
    service_filter = ServiceContextFilter(service_name)
    
    console_handler.addFilter(correlation_filter)
    console_handler.addFilter(service_filter)
    
    root_logger.addHandler(console_handler)
      # Add WORM handler if enabled
    if enable_worm:
        try:
            from .handlers.worm_log_handler import WORMLogHandlerFactory
            
            # Create WORM handler with INFO level or above
            worm_handler = WORMLogHandlerFactory.create_compliance_handler(
                service_name=service_name,
                s3_bucket=os.getenv('AWS_S3_BUCKET')
            )
            
            # Ensure WORM handler log level is INFO or above
            worm_handler.setLevel(max(logging.INFO, numeric_level))
            
            # Use the same JSON formatter as console handler
            worm_handler.setFormatter(json_formatter)
            
            # Add same filters to WORM handler for consistent context
            worm_handler.addFilter(correlation_filter)
            worm_handler.addFilter(service_filter)
            
            # Add WORM handler to root logger
            root_logger.addHandler(worm_handler)
            
            # Log WORM activation to console only (to avoid recursion)
            print(f"WORM audit logging enabled for {service_name} -> S3 bucket: {os.getenv('AWS_S3_BUCKET')}")
            
        except Exception as e:
            # Log error but don't fail startup
            print(f"Warning: Failed to initialize WORM logging for {service_name}: {e}")
    
    # Reduce verbosity of noisy libraries
    for noisy_logger in ['uvicorn.access', 'uvicorn.error', 'asyncio', 'httpx', 'httpcore']:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    
    # Create service-specific logger
    logger = logging.getLogger(service_name)
    
    # Log successful configuration
    logger.info("Logging configured successfully", extra={
        'action': 'logging_configured',
        'log_level': log_level,
        'service_name': service_name,
        'worm_enabled': enable_worm
    })
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance for the current service.
    
    Args:
        name: Logger name (defaults to service name from env)
    
    Returns:
        Logger instance
    """
    if name is None:
        name = os.getenv('SERVICE_NAME', 'unknown-service')
    return logging.getLogger(name)


@contextmanager
def log_context(**kwargs):
    """
    Context manager to add structured context to all logs within the block.
    
    Usage:
        with log_context(user_id="user123", camera_id="cam001", action="process_frame"):
            logger.info("Processing started")
            # ... processing logic ...
            logger.info("Processing completed")
    """
    # Store previous context
    previous_context = getattr(logging._current_context, 'context', {})
    
    # Set new context
    new_context = previous_context.copy()
    new_context.update(kwargs)
    logging._current_context.context = new_context
    
    try:
        yield
    finally:
        # Restore previous context
        logging._current_context.context = previous_context


def set_request_id(request_id: str):
    """Set the request ID for the current thread context."""
    logging._current_context.request_id = request_id


def get_request_id() -> Optional[str]:
    """Get the current request ID from thread context."""
    return getattr(logging._current_context, 'request_id', None)


def clear_context():
    """Clear all context from the current thread."""
    if hasattr(logging._current_context, 'context'):
        del logging._current_context.context
    if hasattr(logging._current_context, 'request_id'):
        del logging._current_context.request_id


# Convenience functions for common logging patterns
def log_request_started(logger: logging.Logger, method: str, path: str, user_id: str = None, **kwargs):
    """Log request started event."""
    extra = {
        'action': 'request_started',
        'method': method,
        'path': path,
        **kwargs
    }
    if user_id:
        extra['user_id'] = user_id
    
    logger.info(f"Request started: {method} {path}", extra=extra)


def log_request_completed(logger: logging.Logger, method: str, path: str, status_code: int, 
                         duration_ms: float, user_id: str = None, **kwargs):
    """Log request completed event."""
    extra = {
        'action': 'request_completed',
        'method': method,
        'path': path,
        'status_code': status_code,
        'duration_ms': duration_ms,
        **kwargs
    }
    if user_id:
        extra['user_id'] = user_id
    
    logger.info(f"Request completed: {method} {path} - {status_code} ({duration_ms:.2f}ms)", extra=extra)


def log_request_error(logger: logging.Logger, method: str, path: str, error: Exception, 
                      user_id: str = None, **kwargs):
    """Log request error event."""
    extra = {
        'action': 'request_error',
        'method': method,
        'path': path,
        'error_type': type(error).__name__,
        'error_message': str(error),
        **kwargs
    }
    if user_id:
        extra['user_id'] = user_id
    
    logger.error(f"Request error: {method} {path} - {type(error).__name__}: {error}", 
                 extra=extra, exc_info=True)


def configure_worm_logging(
    logger: logging.Logger,
    service_name: str,
    s3_bucket: str = None,
    compliance_mode: bool = True
) -> Optional[logging.Handler]:
    """
    Add WORM audit logging to an existing logger.
    
    Args:
        logger: Logger to add WORM handler to
        service_name: Name of the service
        s3_bucket: S3 bucket for audit logs (from AWS_S3_BUCKET env var if not provided)
        compliance_mode: Whether to use compliance-optimized settings
        
    Returns:
        The created WORM handler or None if failed
    """
    try:
        from .handlers.worm_log_handler import add_worm_logging
        
        s3_bucket = s3_bucket or os.getenv('AWS_S3_BUCKET')
        if not s3_bucket:
            raise ValueError("S3 bucket must be specified via parameter or AWS_S3_BUCKET env var")
        
        worm_handler = add_worm_logging(
            logger=logger,
            service_name=service_name,
            s3_bucket=s3_bucket,
            compliance_mode=compliance_mode
        )
        
        # Ensure WORM handler log level is INFO or above
        current_level = logger.getEffectiveLevel()
        worm_handler.setLevel(max(logging.INFO, current_level))
        
        logger.info("WORM audit logging enabled", extra={
            'action': 'worm_logging_enabled',
            's3_bucket': s3_bucket,
            'compliance_mode': compliance_mode
        })
        
        return worm_handler
        
    except Exception as e:
        logger.error("Failed to configure WORM logging", extra={
            'action': 'worm_logging_failed',
            'error': str(e)
        })
        return None
