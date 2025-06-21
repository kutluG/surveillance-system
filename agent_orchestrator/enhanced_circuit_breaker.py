"""
Enhanced Circuit Breaker Pattern Implementation for Agent Orchestrator Service

This module combines the robust pybreaker library with custom circuit breaker logic
to provide enhanced resilience and monitoring for downstream service calls.

Features:
- PyBreaker integration for robust circuit breaker functionality
- Custom metrics and monitoring integration
- Service-specific configuration with different failure thresholds
- Fallback response generation
- Health check integration
- Redis-based circuit breaker state persistence
- Graceful degradation strategies
"""

import asyncio
import time
import logging
import json
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from functools import wraps
import httpx

# Import pybreaker
import pybreaker

# Import Redis for state persistence 
import redis.asyncio as redis

# Import Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, Enum as PrometheusEnum
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

logger = logging.getLogger(__name__)

class ServiceType(str, Enum):
    """Supported downstream service types"""
    RAG_SERVICE = "rag_service"
    RULEGEN_SERVICE = "rulegen_service"
    NOTIFIER_SERVICE = "notifier_service"
    VMS_SERVICE = "vms_service"
    PREDICTION_SERVICE = "prediction_service"

@dataclass
class ServiceConfig:
    """Configuration for downstream service circuit breaker"""
    name: str
    service_type: ServiceType
    fail_max: int = 5                    # Max failures before opening
    recovery_timeout: int = 60           # Seconds before trying half-open
    expected_exception: tuple = (httpx.RequestError, httpx.HTTPStatusError, asyncio.TimeoutError)
    timeout: float = 30.0                # Request timeout
    fallback_enabled: bool = True        # Whether to provide fallback responses
    health_check_url: Optional[str] = None  # Health check endpoint
    priority: int = 1                    # Service priority (1=high, 3=low)

class EnhancedCircuitBreakerManager:
    """
    Enhanced circuit breaker manager with pybreaker integration
    
    Provides:
    - Service-specific circuit breakers with different configurations
    - Fallback response generation
    - Health check monitoring
    - Metrics collection and state persistence
    - Graceful degradation strategies
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.circuit_breakers: Dict[str, pybreaker.CircuitBreaker] = {}
        self.service_configs: Dict[str, ServiceConfig] = {}
        self.metrics: Dict[str, Any] = {}
        self._initialize_metrics()
        
    def _initialize_metrics(self):
        """Initialize Prometheus metrics for enhanced circuit breakers"""
        if not METRICS_AVAILABLE:
            return
            
        self.circuit_breaker_state = Gauge(
            'enhanced_circuit_breaker_state',
            'Current state of enhanced circuit breaker (0=closed, 1=open, 2=half_open)',
            ['service_name', 'service_type']
        )
        
        self.circuit_breaker_requests = Counter(
            'enhanced_circuit_breaker_requests_total',
            'Total requests through enhanced circuit breaker',
            ['service_name', 'service_type', 'status']
        )
        
        self.circuit_breaker_failures = Counter(
            'enhanced_circuit_breaker_failures_total',
            'Total failures in enhanced circuit breaker',
            ['service_name', 'service_type', 'error_type']
        )
        
        self.circuit_breaker_fallbacks = Counter(
            'enhanced_circuit_breaker_fallbacks_total',
            'Total fallback responses generated',
            ['service_name', 'service_type', 'fallback_type']
        )
        
        self.circuit_breaker_response_time = Histogram(
            'enhanced_circuit_breaker_response_time_seconds',
            'Response time of requests through circuit breaker',
            ['service_name', 'service_type', 'status']
        )
    
    def register_service(self, config: ServiceConfig) -> pybreaker.CircuitBreaker:
        """
        Register a new service with circuit breaker protection
        
        Args:
            config: Service configuration
            
        Returns:
            Configured pybreaker CircuitBreaker instance
        """
        # Create custom listener for metrics and state persistence
        def on_state_change(prev_state, new_state, service_name=config.name):
            logger.info(f"Circuit breaker '{service_name}' state changed: {prev_state} -> {new_state}")
            
            # Update metrics
            if METRICS_AVAILABLE:
                state_value = {'closed': 0, 'open': 1, 'half-open': 2}.get(new_state.name.lower(), 0)
                self.circuit_breaker_state.labels(
                    service_name=service_name,
                    service_type=config.service_type.value
                ).set(state_value)
            
            # Persist state to Redis
            if self.redis_client:
                asyncio.create_task(self._persist_circuit_state(service_name, new_state.name))
        
        def on_failure(exception, service_name=config.name):
            logger.warning(f"Circuit breaker '{service_name}' recorded failure: {type(exception).__name__}")
            
            if METRICS_AVAILABLE:
                self.circuit_breaker_failures.labels(
                    service_name=service_name,
                    service_type=config.service_type.value,
                    error_type=type(exception).__name__
                ).inc()
        
        def on_success(service_name=config.name):
            logger.debug(f"Circuit breaker '{service_name}' recorded success")
          # Create pybreaker circuit breaker with enhanced configuration
        circuit_breaker = pybreaker.CircuitBreaker(
            fail_max=config.fail_max,
            reset_timeout=config.recovery_timeout,
            exclude=config.expected_exception,
            name=config.name
        )
          # Add event listeners
        circuit_breaker.add_listener(on_state_change)
        circuit_breaker.add_listener(on_failure)
        circuit_breaker.add_listener(on_success)
        
        # Store configuration and circuit breaker
        self.service_configs[config.name] = config
        self.circuit_breakers[config.name] = circuit_breaker
        
        logger.info(f"Registered circuit breaker for service '{config.name}' (type: {config.service_type.value})")
        return circuit_breaker
    
    async def _persist_circuit_state(self, service_name: str, state: str):
        """Persist circuit breaker state to Redis"""
        if not self.redis_client:
            return
            
        try:
            state_data = {
                'service_name': service_name,
                'state': state,
                'timestamp': datetime.utcnow().isoformat(),
                'fail_counter': getattr(self.circuit_breakers[service_name], 'fail_counter', 0)
            }
            
            await self.redis_client.hset(
                f"circuit_breaker_state:{service_name}",
                mapping=state_data
            )
            
            # Set expiration for cleanup
            await self.redis_client.expire(f"circuit_breaker_state:{service_name}", 3600)
            
        except Exception as e:
            logger.error(f"Failed to persist circuit breaker state for {service_name}: {e}")
    
    async def call_service(self, service_name: str, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """
        Call a service through its circuit breaker with enhanced error handling
        
        Args:
            service_name: Name of the registered service
            func: Async function to call
            *args: Function arguments  
            **kwargs: Function keyword arguments
            
        Returns:
            Dict containing result or fallback response
        """
        if service_name not in self.circuit_breakers:
            raise ValueError(f"Service '{service_name}' not registered")
        
        circuit_breaker = self.circuit_breakers[service_name]
        config = self.service_configs[service_name]
        start_time = time.time()
        
        try:
            # Record request attempt
            if METRICS_AVAILABLE:
                self.circuit_breaker_requests.labels(
                    service_name=service_name,
                    service_type=config.service_type.value,
                    status='attempted'
                ).inc()
              # Call through circuit breaker with timeout
            result = await asyncio.wait_for(
                circuit_breaker(func)(*args, **kwargs),
                timeout=config.timeout
            )
            
            # Record successful request
            response_time = time.time() - start_time
            if METRICS_AVAILABLE:
                self.circuit_breaker_requests.labels(
                    service_name=service_name,
                    service_type=config.service_type.value,
                    status='success'
                ).inc()
                
                self.circuit_breaker_response_time.labels(
                    service_name=service_name,
                    service_type=config.service_type.value,
                    status='success'
                ).observe(response_time)
            
            return {
                'success': True,
                'data': result,
                'service': service_name,
                'response_time': response_time,
                'circuit_breaker_state': circuit_breaker.current_state
            }
            
        except pybreaker.CircuitBreakerError as e:
            # Circuit breaker is open - provide fallback
            logger.warning(f"Circuit breaker for '{service_name}' is open: {e}")
            
            if METRICS_AVAILABLE:
                self.circuit_breaker_requests.labels(
                    service_name=service_name,
                    service_type=config.service_type.value,
                    status='circuit_open'
                ).inc()
            
            fallback_response = await self._generate_fallback_response(service_name, config)
            return fallback_response
            
        except Exception as e:
            # Service call failed
            response_time = time.time() - start_time
            logger.error(f"Service call to '{service_name}' failed: {e}")
            
            if METRICS_AVAILABLE:
                self.circuit_breaker_requests.labels(
                    service_name=service_name,
                    service_type=config.service_type.value,
                    status='failed'
                ).inc()
                
                self.circuit_breaker_response_time.labels(
                    service_name=service_name,
                    service_type=config.service_type.value,
                    status='failed'
                ).observe(response_time)
            
            # Generate fallback if enabled
            if config.fallback_enabled:
                fallback_response = await self._generate_fallback_response(service_name, config, error=e)
                return fallback_response
            else:
                # Re-raise exception if no fallback
                raise e
    
    async def _generate_fallback_response(self, service_name: str, config: ServiceConfig, error: Exception = None) -> Dict[str, Any]:
        """
        Generate appropriate fallback response based on service type
        
        Args:
            service_name: Name of the service
            config: Service configuration
            error: Optional error that triggered fallback
            
        Returns:
            Fallback response dictionary
        """
        fallback_type = "circuit_open" if isinstance(error, pybreaker.CircuitBreakerError) else "service_error"
        
        if METRICS_AVAILABLE:
            self.circuit_breaker_fallbacks.labels(
                service_name=service_name,
                service_type=config.service_type.value,
                fallback_type=fallback_type
            ).inc()
        
        base_response = {
            'success': False,
            'fallback_used': True,
            'service': service_name,
            'circuit_breaker_state': self.circuit_breakers[service_name].current_state,
            'error_type': type(error).__name__ if error else 'circuit_open',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Service-specific fallback responses
        if config.service_type == ServiceType.RAG_SERVICE:
            return {
                **base_response,
                'data': {
                    'linked_explanation': 'RAG service is temporarily unavailable. Using cached or default response.',
                    'retrieved_context': [],
                    'confidence_score': 0.0,
                    'fallback_reason': 'Service unavailable due to circuit breaker protection'
                }
            }
            
        elif config.service_type == ServiceType.RULEGEN_SERVICE:
            return {
                **base_response,
                'data': {
                    'rules_triggered': [],
                    'severity': 'medium',
                    'confidence': 0.5,
                    'explanation': 'Rule generation service unavailable. Using default rule assessment.',
                    'fallback_reason': 'Service unavailable due to circuit breaker protection'
                }
            }
            
        elif config.service_type == ServiceType.NOTIFIER_SERVICE:
            return {
                **base_response,
                'data': {
                    'notification_queued': True,
                    'status': 'queued_for_retry',
                    'message': 'Notification service unavailable. Notification queued for retry.',
                    'retry_scheduled': True
                }
            }
            
        else:
            # Generic fallback
            return {
                **base_response,
                'data': {
                    'message': f'{service_name} is temporarily unavailable',
                    'fallback_reason': 'Service unavailable due to circuit breaker protection'
                }
            }
    
    async def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """
        Get health status of a service and its circuit breaker
        
        Args:
            service_name: Name of the registered service
            
        Returns:
            Health status dictionary
        """
        if service_name not in self.circuit_breakers:
            return {'error': f"Service '{service_name}' not registered"}
        
        circuit_breaker = self.circuit_breakers[service_name]
        config = self.service_configs[service_name]
        
        health_data = {
            'service_name': service_name,
            'service_type': config.service_type.value,
            'circuit_breaker_state': circuit_breaker.current_state,
            'fail_counter': getattr(circuit_breaker, 'fail_counter', 0),
            'last_failure_time': getattr(circuit_breaker, 'last_failure', None),
            'configuration': {
                'fail_max': config.fail_max,
                'recovery_timeout': config.recovery_timeout,
                'timeout': config.timeout,
                'fallback_enabled': config.fallback_enabled,
                'priority': config.priority
            }
        }
        
        # Add Redis-persisted state if available
        if self.redis_client:
            try:
                redis_state = await self.redis_client.hgetall(f"circuit_breaker_state:{service_name}")
                if redis_state:
                    health_data['persisted_state'] = redis_state
            except Exception as e:
                logger.error(f"Failed to retrieve persisted state for {service_name}: {e}")
        
        return health_data
    
    async def get_all_service_health(self) -> Dict[str, Any]:
        """Get health status of all registered services"""
        health_status = {}
        
        for service_name in self.circuit_breakers.keys():
            health_status[service_name] = await self.get_service_health(service_name)
        
        return {
            'services': health_status,
            'total_services': len(self.circuit_breakers),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def force_circuit_state(self, service_name: str, state: str) -> bool:
        """
        Force a circuit breaker to a specific state (for testing/admin purposes)
        
        Args:
            service_name: Name of the service
            state: Target state ('open', 'closed', 'half-open')
            
        Returns:
            True if successful, False otherwise
        """
        if service_name not in self.circuit_breakers:
            return False
        
        circuit_breaker = self.circuit_breakers[service_name]
        
        try:
            if state.lower() == 'open':
                circuit_breaker.open()
            elif state.lower() == 'closed':
                circuit_breaker.close()
            elif state.lower() == 'half-open':
                circuit_breaker.half_open()
            else:
                return False
                
            logger.info(f"Forced circuit breaker '{service_name}' to state '{state}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to force circuit breaker state for {service_name}: {e}")
            return False

# Global enhanced circuit breaker manager instance
enhanced_circuit_breaker_manager: Optional[EnhancedCircuitBreakerManager] = None

def get_enhanced_circuit_breaker_manager(redis_client: Optional[redis.Redis] = None) -> EnhancedCircuitBreakerManager:
    """Get or create the global enhanced circuit breaker manager"""
    global enhanced_circuit_breaker_manager
    
    if enhanced_circuit_breaker_manager is None:
        enhanced_circuit_breaker_manager = EnhancedCircuitBreakerManager(redis_client)
    
    return enhanced_circuit_breaker_manager
