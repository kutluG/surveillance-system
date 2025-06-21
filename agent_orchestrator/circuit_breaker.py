"""
Circuit Breaker Pattern Implementation for Agent Orchestrator Service

This module implements circuit breakers for downstream service calls to prevent
cascading failures and improve system resilience during partial outages.

Features:
- Service-specific circuit breakers
- Configurable failure thresholds and timeouts
- Health check integration
- Metrics collection for circuit breaker states
- Graceful degradation with fallback responses
- Automatic circuit recovery
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from functools import wraps
import httpx

# Import Prometheus metrics if available
try:
    from prometheus_client import Counter, Histogram, Gauge, Enum as PrometheusEnum
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

logger = logging.getLogger(__name__)

class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back up

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    name: str
    fail_max: int = 5                    # Max failures before opening
    reset_timeout: int = 60              # Seconds before trying half-open
    success_threshold: int = 3           # Successes needed to close from half-open
    timeout: float = 30.0                # Request timeout
    exclude_exceptions: List[Exception] = field(default_factory=list)
    expected_exception: Exception = httpx.RequestError

@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    failure_count: int = 0
    success_count: int = 0
    request_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_change_time: datetime = field(default_factory=datetime.utcnow)

class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    def __init__(self, circuit_name: str, message: str = None):
        self.circuit_name = circuit_name
        self.message = message or f"Circuit breaker '{circuit_name}' is open"
        super().__init__(self.message)

class CircuitBreaker:
    """
    Circuit breaker implementation for service calls
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests fail immediately  
    - HALF_OPEN: Testing if service is back, limited requests allowed
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        
        # Initialize metrics if available
        if METRICS_AVAILABLE:
            self._init_metrics()
    
    def _init_metrics(self):
        """Initialize Prometheus metrics for circuit breaker"""
        self.circuit_breaker_state = PrometheusEnum(
            f'circuit_breaker_state',
            f'Current state of circuit breaker',
            ['service'],
            states=['closed', 'open', 'half_open']
        )
        
        self.circuit_breaker_requests = Counter(
            f'circuit_breaker_requests_total',
            f'Total requests through circuit breaker',
            ['service', 'status']
        )
        
        self.circuit_breaker_failures = Counter(
            f'circuit_breaker_failures_total',
            f'Total failures in circuit breaker',
            ['service', 'error_type']
        )
        
        self.circuit_breaker_state_changes = Counter(
            f'circuit_breaker_state_changes_total',
            f'Total state changes of circuit breaker',
            ['service', 'from_state', 'to_state']
        )
        
        # Set initial state
        self.circuit_breaker_state.labels(service=self.config.name).state('closed')
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: When circuit is open
            Original exception: When function fails and circuit allows it
        """
        async with self._lock:
            # Check if we should allow the request
            if not await self._should_allow_request():
                self._record_metrics('blocked')
                raise CircuitBreakerError(
                    self.config.name, 
                    f"Circuit breaker '{self.config.name}' is {self.state.value}"
                )
        
        try:
            # Call the function with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs), 
                timeout=self.config.timeout
            )
            
            # Record success
            await self._record_success()
            self._record_metrics('success')
            
            return result
            
        except Exception as e:
            # Check if this exception should be excluded from circuit breaking
            if any(isinstance(e, exc_type) for exc_type in self.config.exclude_exceptions):
                logger.debug(f"Circuit breaker {self.config.name}: Excluded exception {type(e).__name__}")
                self._record_metrics('excluded')
                raise
            
            # Record failure and potentially open circuit
            await self._record_failure(e)
            self._record_metrics('failure', error_type=type(e).__name__)
            
            raise
    
    async def _should_allow_request(self) -> bool:
        """Determine if request should be allowed based on current state"""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if reset timeout has passed
            if self._should_attempt_reset():
                await self._transition_to_half_open()
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            return True
        
        return False
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset (transition to half-open)"""
        if not self.stats.last_failure_time:
            return False
        
        time_since_failure = datetime.utcnow() - self.stats.last_failure_time
        return time_since_failure.total_seconds() >= self.config.reset_timeout
    
    async def _record_success(self):
        """Record successful request"""
        async with self._lock:
            self.stats.success_count += 1
            self.stats.request_count += 1
            self.stats.last_success_time = datetime.utcnow()
            
            if self.state == CircuitState.HALF_OPEN:
                # Check if we have enough successes to close the circuit
                if self.stats.success_count >= self.config.success_threshold:
                    await self._transition_to_closed()
    
    async def _record_failure(self, exception: Exception):
        """Record failed request"""
        async with self._lock:
            self.stats.failure_count += 1
            self.stats.request_count += 1
            self.stats.last_failure_time = datetime.utcnow()
            
            logger.warning(
                f"Circuit breaker {self.config.name}: Failure recorded. "
                f"Count: {self.stats.failure_count}/{self.config.fail_max}. "
                f"Error: {type(exception).__name__}: {str(exception)}"
            )
            
            # Check if we should open the circuit
            if (self.state == CircuitState.CLOSED and 
                self.stats.failure_count >= self.config.fail_max):
                await self._transition_to_open()
            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open should go back to open
                await self._transition_to_open()
    
    async def _transition_to_open(self):
        """Transition circuit to OPEN state"""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.stats.state_change_time = datetime.utcnow()
        
        logger.warning(
            f"Circuit breaker {self.config.name}: Transitioning to OPEN state. "
            f"Service will be unavailable for {self.config.reset_timeout} seconds."
        )
        
        self._record_state_change(old_state, self.state)
    
    async def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state"""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.stats.state_change_time = datetime.utcnow()
        self.stats.success_count = 0  # Reset success count for half-open period
        
        logger.info(
            f"Circuit breaker {self.config.name}: Transitioning to HALF_OPEN state. "
            f"Testing service availability."
        )
        
        self._record_state_change(old_state, self.state)
    
    async def _transition_to_closed(self):
        """Transition circuit to CLOSED state"""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.stats.state_change_time = datetime.utcnow()
        self.stats.failure_count = 0  # Reset failure count
        
        logger.info(
            f"Circuit breaker {self.config.name}: Transitioning to CLOSED state. "
            f"Service is healthy again."
        )
        
        self._record_state_change(old_state, self.state)
    
    def _record_state_change(self, from_state: CircuitState, to_state: CircuitState):
        """Record state change in metrics"""
        if METRICS_AVAILABLE:
            self.circuit_breaker_state.labels(service=self.config.name).state(to_state.value)
            self.circuit_breaker_state_changes.labels(
                service=self.config.name,
                from_state=from_state.value,
                to_state=to_state.value
            ).inc()
    
    def _record_metrics(self, status: str, error_type: str = None):
        """Record request metrics"""
        if METRICS_AVAILABLE:
            self.circuit_breaker_requests.labels(
                service=self.config.name,
                status=status
            ).inc()
            
            if error_type:
                self.circuit_breaker_failures.labels(
                    service=self.config.name,
                    error_type=error_type
                ).inc()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current circuit breaker statistics"""
        return {
            "name": self.config.name,
            "state": self.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "request_count": self.stats.request_count,
            "last_failure_time": self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None,
            "last_success_time": self.stats.last_success_time.isoformat() if self.stats.last_success_time else None,
            "state_change_time": self.stats.state_change_time.isoformat(),
            "config": {
                "fail_max": self.config.fail_max,
                "reset_timeout": self.config.reset_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }
    
    async def force_open(self):
        """Manually force circuit to open (for testing/maintenance)"""
        async with self._lock:
            await self._transition_to_open()
    
    async def force_close(self):
        """Manually force circuit to close (for testing/maintenance)"""
        async with self._lock:
            await self._transition_to_closed()

class CircuitBreakerManager:
    """Manager for multiple circuit breakers"""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
    
    def register_breaker(self, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Register a new circuit breaker"""
        breaker = CircuitBreaker(config)
        self.breakers[config.name] = breaker
        
        logger.info(f"Registered circuit breaker: {config.name}")
        return breaker
    
    def get_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self.breakers.get(name)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {name: breaker.get_stats() for name, breaker in self.breakers.items()}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all circuit breakers"""
        stats = {}
        overall_health = "healthy"
        
        for name, breaker in self.breakers.items():
            breaker_stats = breaker.get_stats()
            stats[name] = breaker_stats
            
            # Determine overall health based on circuit states
            if breaker.state == CircuitState.OPEN:
                overall_health = "degraded"
            elif breaker.state == CircuitState.HALF_OPEN and overall_health == "healthy":
                overall_health = "warning"
        
        return {
            "overall_health": overall_health,
            "circuit_breakers": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

# Decorator for easy circuit breaker usage
def circuit_breaker(name: str, **config_kwargs):
    """
    Decorator to apply circuit breaker to async functions
    
    Args:
        name: Circuit breaker name
        **config_kwargs: Circuit breaker configuration options
    """
    def decorator(func):
        # Create circuit breaker config
        config = CircuitBreakerConfig(name=name, **config_kwargs)
        breaker = CircuitBreaker(config)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        # Attach breaker to function for access to stats/control
        wrapper.circuit_breaker = breaker
        return wrapper
    
    return decorator

# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()

# Export main components
__all__ = [
    'CircuitBreaker',
    'CircuitBreakerConfig', 
    'CircuitBreakerError',
    'CircuitBreakerManager',
    'CircuitState',
    'circuit_breaker',
    'circuit_breaker_manager'
]
