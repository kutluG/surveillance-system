"""
Comprehensive Metrics Collection for Agent Orchestrator Service

This module provides detailed Prometheus metrics for monitoring:
- Orchestration request latency and performance
- Agent performance and availability
- Task management and workflow execution
- Service communication health (RAG, Rule Generation, Notifier)
- Resource utilization and efficiency
- Error rates and retry patterns
- Workflow success rates and bottlenecks
"""

import time
import asyncio
import logging
from typing import Dict, Optional, Any, Callable
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mock classes for when prometheus_client is not available
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    
    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def time(self): return MockTimer()
    
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    
    class Summary:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    
    class Info:
        def __init__(self, *args, **kwargs): pass
        def info(self, *args, **kwargs): pass
    
    class MockTimer:
        def __enter__(self): return self
        def __exit__(self, *args): pass

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics collected"""
    ORCHESTRATION_LATENCY = "orchestration_latency"
    AGENT_PERFORMANCE = "agent_performance"
    TASK_MANAGEMENT = "task_management"
    SERVICE_COMMUNICATION = "service_communication"
    WORKFLOW_EXECUTION = "workflow_execution"
    RETRY_PATTERNS = "retry_patterns"


class ServiceType(str, Enum):
    """External services being monitored"""
    RAG_SERVICE = "rag_service"
    RULEGEN_SERVICE = "rulegen_service"
    NOTIFIER_SERVICE = "notifier_service"
    DATABASE = "database"
    REDIS = "redis"


class OrchestrationStatus(str, Enum):
    """Orchestration outcome statuses"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FALLBACK = "fallback"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class MetricLabels:
    """Standard labels for metrics"""
    service: str = "agent_orchestrator"
    version: str = "1.0"
    environment: str = "development"
    endpoint: Optional[str] = None
    operation: Optional[str] = None
    status: Optional[str] = None
    service_type: Optional[str] = None
    agent_type: Optional[str] = None


class OrchestrationMetricsCollector:
    """
    Comprehensive metrics collector for Agent Orchestrator Service
    
    Provides detailed monitoring across all orchestration operations with
    Prometheus-compatible metrics collection.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.enabled = PROMETHEUS_AVAILABLE
        
        if not self.enabled:
            logger.warning("Prometheus client not available - metrics collection disabled")
            return
        
        self._initialize_metrics()
        logger.info("Agent Orchestrator metrics collector initialized")
    
    def _initialize_metrics(self):
        """Initialize all Prometheus metrics"""
        
        # =============================================================================
        # ORCHESTRATION REQUEST METRICS
        # =============================================================================
        
        # Overall orchestration processing time
        self.orchestration_duration = Histogram(
            'orchestrator_request_duration_seconds',
            'Time spent processing orchestration requests',
            ['endpoint', 'status', 'workflow_type'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
            registry=self.registry
        )
        
        # Orchestration request count
        self.orchestration_requests = Counter(
            'orchestrator_requests_total',
            'Total number of orchestration requests',
            ['endpoint', 'status', 'workflow_type'],
            registry=self.registry
        )
        
        # Active orchestrations
        self.active_orchestrations = Gauge(
            'orchestrator_active_requests_count',
            'Number of currently active orchestration requests',
            registry=self.registry
        )
        
        # Orchestration latency by component
        self.component_latency = Histogram(
            'orchestrator_component_latency_seconds',
            'Latency for individual orchestration components',
            ['component', 'operation', 'status'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        
        # =============================================================================
        # SERVICE COMMUNICATION METRICS
        # =============================================================================
        
        # External service call durations
        self.service_call_duration = Histogram(
            'orchestrator_service_call_duration_seconds',
            'Time spent calling external services',
            ['service_type', 'operation', 'status'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self.registry
        )
        
        # External service request count
        self.service_requests = Counter(
            'orchestrator_service_requests_total',
            'Total external service requests',
            ['service_type', 'operation', 'status'],
            registry=self.registry
        )
        
        # Service availability
        self.service_availability = Gauge(
            'orchestrator_service_availability',
            'External service availability (1=up, 0=down)',
            ['service_type'],
            registry=self.registry
        )
        
        # Service retry attempts
        self.service_retries = Counter(
            'orchestrator_service_retries_total',
            'Total service retry attempts',
            ['service_type', 'operation', 'retry_reason'],
            registry=self.registry
        )
        
        # =============================================================================
        # AGENT AND TASK MANAGEMENT METRICS
        # =============================================================================
        
        # Agent performance metrics
        self.agent_task_duration = Histogram(
            'orchestrator_agent_task_duration_seconds',
            'Time agents spend on tasks',
            ['agent_type', 'task_type', 'status'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
            registry=self.registry
        )
        
        # Agent availability
        self.agent_availability = Gauge(
            'orchestrator_agent_availability_count',
            'Number of available agents by type',
            ['agent_type', 'status'],
            registry=self.registry
        )
        
        # Task queue metrics
        self.task_queue_size = Gauge(
            'orchestrator_task_queue_size',
            'Number of tasks in queue',
            ['queue_type', 'priority'],
            registry=self.registry
        )
        
        # Task processing metrics
        self.task_processing_time = Histogram(
            'orchestrator_task_processing_seconds',
            'Time to process tasks',
            ['task_type', 'status'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self.registry
        )
        
        # =============================================================================
        # WORKFLOW EXECUTION METRICS
        # =============================================================================
        
        # Workflow success rates
        self.workflow_outcomes = Counter(
            'orchestrator_workflow_outcomes_total',
            'Workflow execution outcomes',
            ['workflow_type', 'outcome', 'failure_point'],
            registry=self.registry
        )
        
        # Workflow step duration
        self.workflow_step_duration = Histogram(
            'orchestrator_workflow_step_duration_seconds',
            'Duration of individual workflow steps',
            ['workflow_type', 'step_name', 'status'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
            registry=self.registry
        )
        
        # =============================================================================
        # NOTIFICATION AND ALERTING METRICS
        # =============================================================================
        
        # Notification delivery metrics
        self.notification_delivery = Counter(
            'orchestrator_notification_delivery_total',
            'Notification delivery attempts',
            ['channel', 'status', 'priority'],
            registry=self.registry
        )
        
        # Notification latency
        self.notification_latency = Histogram(
            'orchestrator_notification_latency_seconds',
            'Time from event to notification delivery',
            ['channel', 'priority'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
            registry=self.registry
        )
        
        # Notification retry queue
        self.notification_retry_queue_size = Gauge(
            'orchestrator_notification_retry_queue_size',
            'Number of notifications in retry queue',
            ['channel'],
            registry=self.registry
        )
        
        # =============================================================================
        # ERROR AND RELIABILITY METRICS
        # =============================================================================
        
        # Error rates by component
        self.error_rates = Counter(
            'orchestrator_errors_total',
            'Total errors by component and type',
            ['component', 'error_type', 'severity'],
            registry=self.registry
        )
        
        # Fallback usage
        self.fallback_usage = Counter(
            'orchestrator_fallback_usage_total',
            'Times fallback mechanisms were used',
            ['component', 'fallback_type', 'reason'],
            registry=self.registry
        )
        
        # =============================================================================
        # RESOURCE UTILIZATION METRICS
        # =============================================================================
        
        # Memory usage by operation
        self.memory_usage = Gauge(
            'orchestrator_memory_usage_bytes',
            'Memory usage during operations',
            ['operation_type'],
            registry=self.registry
        )
        
        # Database connection pool
        self.db_connection_pool = Gauge(
            'orchestrator_db_connections_count',
            'Database connection pool status',
            ['pool_type', 'status'],
            registry=self.registry
        )
        
        # Redis connection metrics
        self.redis_connection_status = Gauge(
            'orchestrator_redis_connection_status',
            'Redis connection status',
            ['operation_type'],
            registry=self.registry
        )
        
        # =============================================================================
        # BUSINESS LOGIC METRICS
        # =============================================================================
        
        # Event processing metrics
        self.event_processing = Counter(
            'orchestrator_events_processed_total',
            'Total events processed',
            ['event_type', 'source', 'status'],
            registry=self.registry
        )
        
        # Rule evaluation metrics
        self.rule_evaluations = Counter(
            'orchestrator_rule_evaluations_total',
            'Rule evaluation attempts',
            ['rule_type', 'outcome'],
            registry=self.registry
        )
        
        # Context enrichment metrics
        self.context_enrichment_time = Histogram(
            'orchestrator_context_enrichment_seconds',
            'Time spent enriching context',
            ['enrichment_type'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
            registry=self.registry
        )
          # Service info
        self.service_info = Info(
            'orchestrator_service_info',
            'Agent Orchestrator Service information',
            registry=self.registry
        )
    
    def record_orchestration_request(self, status: str, query_type: str = "unknown", 
                                   notification_channels: str = "none"):
        """Record an orchestration request"""
        if not self.enabled:
            return
        self.orchestration_requests.labels(
            endpoint="orchestrate",
            status=status,
            workflow_type=query_type
        ).inc()
    
    def record_orchestration_latency(self, duration: float, status: str, stage: str):
        """Record orchestration latency"""
        if not self.enabled:
            return
        self.orchestration_duration.labels(
            endpoint="orchestrate",
            status=status,
            workflow_type=stage
        ).observe(duration)
    
    def record_service_request(self, service: str, endpoint: str, status_code: int, duration: float):
        """Record external service request"""
        if not self.enabled:
            return
        status = "success" if 200 <= status_code < 300 else "error"
        self.service_requests.labels(
            service_type=service,
            operation=endpoint,
            status=status
        ).inc()
        self.service_call_duration.labels(
            service_type=service,
            operation=endpoint,
            status=status
        ).observe(duration)
    
    def set_service_availability(self, service: str, available: bool):
        """Set service availability status"""
        if not self.enabled:
            return
        self.service_availability.labels(service_type=service).set(1 if available else 0)
    
    def update_agent_count(self, agent_type: str, status: str, count: int):
        """Update agent count"""
        if not self.enabled:
            return
        self.agent_availability.labels(agent_type=agent_type, status=status).set(count)
    
    def set_agent_performance(self, agent_id: str, agent_type: str, score: float):
        """Set agent performance score (not implemented in current metrics)"""
        if not self.enabled:
            return
        # This would require adding a new metric - for now, log it
        logger.info(f"Agent {agent_id} ({agent_type}) performance score: {score}")
    
    def record_task_assignment(self, agent_id: str, agent_type: str, task_type: str):
        """Record task assignment to agent"""
        if not self.enabled:
            return
        # Using workflow outcomes for now
        self.workflow_outcomes.labels(
            workflow_type=task_type,
            outcome="assigned",
            failure_point="none"
        ).inc()
    
    def record_error(self, error_type: str, component: str, severity: str = "error"):
        """Record an error occurrence"""
        if not self.enabled:
            return
        self.error_rates.labels(
            component=component,
            error_type=error_type,
            severity=severity
        ).inc()
    
    def record_retry_attempt(self, service: str, operation: str, attempt_number: int):
        """Record a retry attempt"""
        if not self.enabled:
            return
        self.service_retries.labels(
            service_type=service,
            operation=operation,
            retry_reason=f"attempt_{attempt_number}"
        ).inc()
    
    def record_fallback_activation(self, service: str, fallback_type: str):
        """Record fallback mechanism activation"""
        if not self.enabled:
            return
        self.fallback_usage.labels(
            component=service,
            fallback_type=fallback_type,
            reason="service_unavailable"
        ).inc()
    
    @contextmanager
    def time_orchestration_stage(self, status: str, stage: str):
        """Context manager to time orchestration stages"""
        if not self.enabled:
            yield
            return
        
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.component_latency.labels(
                component="orchestrator",
                operation=stage,
                status=status
            ).observe(duration)
    
    @contextmanager
    def concurrent_request_tracker(self):
        """Context manager to track concurrent requests"""
        if not self.enabled:
            yield
            return
        
        self.active_orchestrations.inc()
        try:
            yield
        finally:
            self.active_orchestrations.dec()
    
    def get_metrics_data(self) -> str:
        """Get current metrics data in Prometheus format"""
        if not self.enabled:
            return "# Metrics not available\n"
        data = generate_latest(self.registry)
        return data.decode('utf-8') if isinstance(data, bytes) else data

# =============================================================================
# DECORATOR FUNCTIONS
# =============================================================================

def monitor_orchestration_performance(status_label: str = "success"):
    """Decorator to monitor orchestration performance"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with metrics_collector.concurrent_request_tracker():
                start_time = time.time()
                status = status_label
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    metrics_collector.record_error(
                        error_type=type(e).__name__,
                        component="orchestration",
                        severity="error"
                    )
                    raise
                finally:
                    duration = time.time() - start_time
                    metrics_collector.record_orchestration_latency(duration, status, "total")
                    metrics_collector.record_orchestration_request(status, "unknown", "none")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with metrics_collector.concurrent_request_tracker():
                start_time = time.time()
                status = status_label
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    metrics_collector.record_error(
                        error_type=type(e).__name__,
                        component="orchestration",
                        severity="error"
                    )
                    raise
                finally:
                    duration = time.time() - start_time
                    metrics_collector.record_orchestration_latency(duration, status, "total")
                    metrics_collector.record_orchestration_request(status, "unknown", "none")
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def monitor_service_call(service_name: str, endpoint: str = "unknown"):
    """Decorator to monitor external service calls"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            try:
                result = await func(*args, **kwargs)
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                return result
            except Exception as e:
                status_code = getattr(e, 'status_code', 500)
                metrics_collector.record_error(
                    error_type=type(e).__name__,
                    component=service_name,
                    severity="error"
                )
                raise
            finally:
                duration = time.time() - start_time
                metrics_collector.record_service_request(service_name, endpoint, status_code, duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            try:
                result = func(*args, **kwargs)
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                return result
            except Exception as e:
                status_code = getattr(e, 'status_code', 500)
                metrics_collector.record_error(
                    error_type=type(e).__name__,
                    component=service_name,
                    severity="error"
                )
                raise
            finally:
                duration = time.time() - start_time
                metrics_collector.record_service_request(service_name, endpoint, status_code, duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# =============================================================================
# GLOBAL METRICS COLLECTOR INSTANCE
# =============================================================================

# Global metrics collector instance
metrics_collector = OrchestrationMetricsCollector()

# Initialize service info
if metrics_collector.enabled:
    service_info = Info(
        'agent_orchestrator_service_info',
        'Agent Orchestrator Service Information'
    )
    service_info.info({
        'version': '1.0.0',
        'service': 'agent_orchestrator',
        'description': 'Orchestrates multi-agent workflows for surveillance system'
    })
    
    logger.info("Agent Orchestrator metrics system initialized")
else:
    logger.warning("Metrics collection disabled - prometheus_client not available")
