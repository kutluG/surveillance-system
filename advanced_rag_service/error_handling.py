"""
Enhanced error handling and retry logic for Advanced RAG Service

Provides robust error handling with exponential backoff,
circuit breaker pattern, and comprehensive logging.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from functools import wraps
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorType(Enum):
    """Types of errors that can occur"""
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker implementation"""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 2
    
    def __post_init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state = CircuitBreakerState.CLOSED


class EnhancedRAGError(Exception):
    """Base exception for RAG service errors"""
    
    def __init__(self, message: str, error_type: ErrorType, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.error_type = error_type
        self.original_error = original_error
        self.timestamp = time.time()


class ConnectionError(EnhancedRAGError):
    """Connection-related errors"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorType.NETWORK_ERROR, original_error)


class ValidationError(EnhancedRAGError):
    """Validation-related errors"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorType.VALIDATION_ERROR, original_error)


class TimeoutError(EnhancedRAGError):
    """Timeout-related errors"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorType.TIMEOUT_ERROR, original_error)


# Enhanced error types for external service failures
class WeaviateConnectionError(EnhancedRAGError):
    """Weaviate connection and query errors"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorType.NETWORK_ERROR, original_error)


class OpenAIAPIError(EnhancedRAGError):
    """OpenAI API related errors"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorType.API_ERROR, original_error)


class EmbeddingGenerationError(EnhancedRAGError):
    """Embedding model errors"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorType.API_ERROR, original_error)


class TemporalProcessingError(EnhancedRAGError):
    """Errors specific to temporal processing"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorType.VALIDATION_ERROR, original_error)


class ServiceDegradationError(EnhancedRAGError):
    """Errors when service is running in degraded mode"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, ErrorType.API_ERROR, original_error)


# Fallback response classes for graceful degradation
@dataclass
class FallbackResponse:
    """Base class for fallback responses when services are unavailable"""
    service_name: str
    fallback_reason: str
    timestamp: float
    original_error: Optional[str] = None


@dataclass
class FallbackTemporalRAGResponse:
    """Fallback response for temporal RAG queries"""
    service_name: str
    fallback_reason: str
    timestamp: float
    linked_explanation: str
    retrieved_context: List[Dict[str, Any]]
    explanation_confidence: float
    original_error: Optional[str] = None
    degraded_mode: bool = True
    
    @classmethod
    def create_minimal_response(cls, query_event, reason: str, original_error: Optional[Exception] = None):
        """Create minimal fallback response when services are unavailable"""
        return cls(
            service_name="temporal_rag",
            fallback_reason=reason,
            timestamp=time.time(),
            original_error=str(original_error) if original_error else None,
            linked_explanation=f"Service temporarily degraded: {reason}. Unable to provide detailed temporal analysis for {query_event.label} detection on camera {query_event.camera_id} at {query_event.timestamp}.",
            retrieved_context=[],
            explanation_confidence=0.0,
            degraded_mode=True
        )

def with_retry(
    config: Optional[RetryConfig] = None,
    exceptions: tuple = (Exception,),
    circuit_breaker: Optional[CircuitBreaker] = None
):
    """Decorator for adding retry logic with exponential backoff"""
    
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            # Check circuit breaker
            if circuit_breaker and circuit_breaker.state == CircuitBreakerState.OPEN:
                if time.time() - circuit_breaker.last_failure_time > circuit_breaker.recovery_timeout:
                    circuit_breaker.state = CircuitBreakerState.HALF_OPEN
                    circuit_breaker.success_count = 0
                else:
                    raise EnhancedRAGError(
                        "Circuit breaker is OPEN - service temporarily unavailable",
                        ErrorType.NETWORK_ERROR
                    )
            
            for attempt in range(config.max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    
                    # Success - update circuit breaker
                    if circuit_breaker:
                        if circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
                            circuit_breaker.success_count += 1
                            if circuit_breaker.success_count >= circuit_breaker.success_threshold:
                                circuit_breaker.state = CircuitBreakerState.CLOSED
                                circuit_breaker.failure_count = 0
                        elif circuit_breaker.state == CircuitBreakerState.CLOSED:
                            circuit_breaker.failure_count = 0
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Update circuit breaker on failure
                    if circuit_breaker:
                        circuit_breaker.failure_count += 1
                        circuit_breaker.last_failure_time = time.time()
                        
                        if (circuit_breaker.state == CircuitBreakerState.CLOSED and 
                            circuit_breaker.failure_count >= circuit_breaker.failure_threshold):
                            circuit_breaker.state = CircuitBreakerState.OPEN
                        elif circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
                            circuit_breaker.state = CircuitBreakerState.OPEN
                    
                    if attempt == config.max_attempts - 1:
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter if enabled
                    if config.jitter:
                        delay *= (0.5 + 0.5 * time.time() % 1)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    await asyncio.sleep(delay)
            
            # All attempts failed
            error_msg = f"Function {func.__name__} failed after {config.max_attempts} attempts"
            if isinstance(last_exception, EnhancedRAGError):
                raise last_exception
            else:
                raise EnhancedRAGError(error_msg, ErrorType.UNKNOWN_ERROR, last_exception)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        break
                    
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    if config.jitter:
                        delay *= (0.5 + 0.5 * time.time() % 1)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    time.sleep(delay)
            
            error_msg = f"Function {func.__name__} failed after {config.max_attempts} attempts"
            if isinstance(last_exception, EnhancedRAGError):
                raise last_exception
            else:
                raise EnhancedRAGError(error_msg, ErrorType.UNKNOWN_ERROR, last_exception)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def handle_exceptions(
    default_return: Any = None,
    log_error: bool = True,
    raise_on_critical: bool = True
):
    """Decorator for comprehensive exception handling"""
    
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, Any]]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Union[T, Any]:
            try:
                return await func(*args, **kwargs)
            except EnhancedRAGError as e:
                if log_error:
                    logger.error(f"RAG Error in {func.__name__}: {e} (Type: {e.error_type.value})")
                if raise_on_critical and e.error_type in [ErrorType.VALIDATION_ERROR]:
                    raise
                return default_return
            except Exception as e:
                if log_error:
                    logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
                if raise_on_critical:
                    raise EnhancedRAGError(
                        f"Unexpected error in {func.__name__}",
                        ErrorType.UNKNOWN_ERROR,
                        e
                    )
                return default_return
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Union[T, Any]:
            try:
                return func(*args, **kwargs)
            except EnhancedRAGError as e:
                if log_error:
                    logger.error(f"RAG Error in {func.__name__}: {e} (Type: {e.error_type.value})")
                if raise_on_critical and e.error_type in [ErrorType.VALIDATION_ERROR]:
                    raise
                return default_return
            except Exception as e:
                if log_error:
                    logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
                if raise_on_critical:
                    raise EnhancedRAGError(
                        f"Unexpected error in {func.__name__}",
                        ErrorType.UNKNOWN_ERROR,
                        e
                    )
                return default_return
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
