"""
Comprehensive Metrics Collection for Advanced RAG Service

This module provides detailed Prometheus metrics for monitoring:
- Query latency and performance
- Vector search operations
- External service response times
- Cache hit rates and effectiveness
- Service health and availability
"""

import time
import logging
from typing import Dict, Optional, Any, Callable
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import asyncio

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
        def time(self): return MockTimer()
        def labels(self, *args, **kwargs): return self
    
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    
    class Summary:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def time(self): return MockTimer()
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
    QUERY_LATENCY = "query_latency"
    VECTOR_SEARCH = "vector_search"
    EXTERNAL_SERVICE = "external_service"
    CACHE_OPERATIONS = "cache_operations"
    SERVICE_HEALTH = "service_health"
    BUSINESS_LOGIC = "business_logic"

class ServiceType(str, Enum):
    """External services being monitored"""
    WEAVIATE = "weaviate"
    OPENAI = "openai"
    REDIS = "redis"
    EMBEDDING_MODEL = "embedding_model"
    DATABASE = "database"

@dataclass
class MetricLabels:
    """Standard labels for metrics"""
    service: str = "advanced_rag"
    version: str = "1.0"
    environment: str = "development"
    endpoint: Optional[str] = None
    operation: Optional[str] = None
    status: Optional[str] = None
    service_type: Optional[str] = None

class AdvancedMetricsCollector:
    """
    Comprehensive metrics collector for Advanced RAG Service
    
    Provides detailed monitoring across all service operations with
    Prometheus-compatible metrics collection.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.enabled = PROMETHEUS_AVAILABLE
        
        if not self.enabled:
            logger.warning("Prometheus client not available - metrics collection disabled")
            return
        
        self._initialize_metrics()
        logger.info("Advanced metrics collector initialized")
    
    def _initialize_metrics(self):
        """Initialize all Prometheus metrics"""
        
        # =============================================================================
        # QUERY LATENCY METRICS
        # =============================================================================
        
        # Overall query processing time
        self.query_duration = Histogram(
            'rag_query_duration_seconds',
            'Time spent processing RAG queries',
            ['endpoint', 'query_type', 'status'],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0),
            registry=self.registry
        )
        
        # Query complexity metrics
        self.query_complexity = Histogram(
            'rag_query_complexity_score',
            'Complexity score of processed queries',
            ['endpoint', 'query_type'],
            buckets=(0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry
        )
        
        # Query result quality
        self.query_confidence = Histogram(
            'rag_query_confidence_score',
            'Confidence score of query results',
            ['endpoint', 'query_type'],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry
        )
        
        # =============================================================================
        # VECTOR SEARCH PERFORMANCE METRICS
        # =============================================================================
        
        # Vector embedding generation time
        self.embedding_generation_time = Histogram(
            'rag_embedding_generation_seconds',
            'Time to generate embeddings',
            ['model_type', 'content_type'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
            registry=self.registry
        )
        
        # Vector search operation time
        self.vector_search_time = Histogram(
            'rag_vector_search_seconds',
            'Time for vector similarity search',
            ['index_type', 'search_type', 'k_value'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
            registry=self.registry
        )
        
        # Vector search result metrics
        self.vector_search_results = Histogram(
            'rag_vector_search_results_count',
            'Number of results returned from vector search',
            ['index_type', 'search_type'],
            buckets=(1, 5, 10, 20, 50, 100, 200, 500),
            registry=self.registry
        )
        
        # Vector similarity scores
        self.vector_similarity_scores = Histogram(
            'rag_vector_similarity_scores',
            'Distribution of vector similarity scores',
            ['index_type', 'search_type'],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry
        )
        
        # =============================================================================
        # EXTERNAL SERVICE RESPONSE TIMES
        # =============================================================================
        
        # External service call durations
        self.external_service_duration = Histogram(
            'rag_external_service_duration_seconds',
            'Time spent calling external services',
            ['service_type', 'operation', 'status'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self.registry
        )
        
        # External service success/failure rates
        self.external_service_requests = Counter(
            'rag_external_service_requests_total',
            'Total external service requests',
            ['service_type', 'operation', 'status'],
            registry=self.registry
        )
        
        # External service availability
        self.external_service_availability = Gauge(
            'rag_external_service_availability',
            'External service availability (1=up, 0=down)',
            ['service_type'],
            registry=self.registry
        )
        
        # Service health check response times
        self.health_check_duration = Histogram(
            'rag_health_check_duration_seconds',
            'Time for service health checks',
            ['service_type'],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry
        )
        
        # =============================================================================
        # CACHE HIT RATES AND PERFORMANCE
        # =============================================================================
        
        # Cache operations
        self.cache_operations = Counter(
            'rag_cache_operations_total',
            'Total cache operations',
            ['cache_type', 'operation', 'result'],
            registry=self.registry
        )
        
        # Cache hit rate
        self.cache_hit_rate = Gauge(
            'rag_cache_hit_rate',
            'Cache hit rate percentage',
            ['cache_type'],
            registry=self.registry
        )
        
        # Cache operation duration
        self.cache_operation_duration = Histogram(
            'rag_cache_operation_duration_seconds',
            'Duration of cache operations',
            ['cache_type', 'operation'],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5),
            registry=self.registry
        )
        
        # Cache size metrics
        self.cache_size = Gauge(
            'rag_cache_size_bytes',
            'Current cache size in bytes',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_entries = Gauge(
            'rag_cache_entries_count',
            'Number of entries in cache',
            ['cache_type'],
            registry=self.registry
        )
        
        # =============================================================================
        # BUSINESS LOGIC METRICS
        # =============================================================================
        
        # Evidence processing metrics
        self.evidence_processed = Counter(
            'rag_evidence_processed_total',
            'Total evidence items processed',
            ['evidence_type', 'status'],
            registry=self.registry
        )
        
        # Correlation analysis metrics
        self.correlation_analysis_time = Histogram(
            'rag_correlation_analysis_seconds',
            'Time for evidence correlation analysis',
            ['analysis_type'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self.registry
        )
        
        # Temporal analysis metrics
        self.temporal_analysis_time = Histogram(
            'rag_temporal_analysis_seconds',
            'Time for temporal analysis',
            ['time_window'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
            registry=self.registry
        )
        
        # =============================================================================
        # SYSTEM RESOURCE METRICS
        # =============================================================================
        
        # Active queries gauge
        self.active_queries = Gauge(
            'rag_active_queries_count',
            'Number of currently active queries',
            registry=self.registry
        )
        
        # Memory usage for specific operations
        self.operation_memory_usage = Gauge(
            'rag_operation_memory_bytes',
            'Memory usage during operations',
            ['operation_type'],
            registry=self.registry
        )
        
        # Service info
        self.service_info = Info(
            'rag_service_info',
            'Advanced RAG Service information',
            registry=self.registry
        )
    
    # =============================================================================
    # CONTEXT MANAGERS AND DECORATORS
    # =============================================================================
    
    @contextmanager
    def time_operation(self, metric_name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations"""
        if not self.enabled:
            yield
            return
        
        labels = labels or {}
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            metric = getattr(self, metric_name, None)
            if metric and hasattr(metric, 'labels'):
                metric.labels(**labels).observe(duration)
    
    def time_query(self, endpoint: str = "unknown", query_type: str = "unknown"):
        """Time query operations"""
        return self.time_operation('query_duration', {
            'endpoint': endpoint,
            'query_type': query_type,
            'status': 'success'
        })
    
    def time_vector_search(self, index_type: str = "weaviate", search_type: str = "similarity", k_value: str = "10"):
        """Time vector search operations"""
        return self.time_operation('vector_search_time', {
            'index_type': index_type,
            'search_type': search_type,
            'k_value': k_value
        })
    
    def time_external_service(self, service_type: str, operation: str = "unknown"):
        """Time external service calls"""
        return self.time_operation('external_service_duration', {
            'service_type': service_type,
            'operation': operation,
            'status': 'success'
        })
    
    def time_cache_operation(self, cache_type: str = "redis", operation: str = "get"):
        """Time cache operations"""
        return self.time_operation('cache_operation_duration', {
            'cache_type': cache_type,
            'operation': operation
        })
    
    # =============================================================================
    # METRIC RECORDING METHODS
    # =============================================================================
    
    def record_query_metrics(self, endpoint: str, query_type: str, duration: float, 
                           confidence: float = None, complexity: float = None, status: str = "success"):
        """Record comprehensive query metrics"""
        if not self.enabled:
            return
        
        self.query_duration.labels(
            endpoint=endpoint,
            query_type=query_type,
            status=status
        ).observe(duration)
        
        if confidence is not None:
            self.query_confidence.labels(
                endpoint=endpoint,
                query_type=query_type
            ).observe(confidence)
        
        if complexity is not None:
            self.query_complexity.labels(
                endpoint=endpoint,
                query_type=query_type
            ).observe(complexity)
    
    def record_vector_search_metrics(self, index_type: str, search_type: str, 
                                   duration: float, result_count: int, 
                                   similarity_scores: list = None, k_value: int = 10):
        """Record vector search performance metrics"""
        if not self.enabled:
            return
        
        self.vector_search_time.labels(
            index_type=index_type,
            search_type=search_type,
            k_value=str(k_value)
        ).observe(duration)
        
        self.vector_search_results.labels(
            index_type=index_type,
            search_type=search_type
        ).observe(result_count)
        
        if similarity_scores:
            for score in similarity_scores:
                self.vector_similarity_scores.labels(
                    index_type=index_type,
                    search_type=search_type
                ).observe(score)
    
    def record_embedding_metrics(self, model_type: str, content_type: str, duration: float):
        """Record embedding generation metrics"""
        if not self.enabled:
            return
        
        self.embedding_generation_time.labels(
            model_type=model_type,
            content_type=content_type
        ).observe(duration)
    
    def record_external_service_metrics(self, service_type: str, operation: str, 
                                      duration: float, status: str = "success"):
        """Record external service call metrics"""
        if not self.enabled:
            return
        
        self.external_service_duration.labels(
            service_type=service_type,
            operation=operation,
            status=status
        ).observe(duration)
        
        self.external_service_requests.labels(
            service_type=service_type,
            operation=operation,
            status=status
        ).inc()
    
    def record_cache_metrics(self, cache_type: str, operation: str, result: str, duration: float = None):
        """Record cache operation metrics"""
        if not self.enabled:
            return
        
        self.cache_operations.labels(
            cache_type=cache_type,
            operation=operation,
            result=result
        ).inc()
        
        if duration is not None:
            self.cache_operation_duration.labels(
                cache_type=cache_type,
                operation=operation
            ).observe(duration)
    
    def update_cache_hit_rate(self, cache_type: str, hit_rate: float):
        """Update cache hit rate gauge"""
        if not self.enabled:
            return
        
        self.cache_hit_rate.labels(cache_type=cache_type).set(hit_rate)
    
    def update_service_availability(self, service_type: str, is_available: bool):
        """Update service availability gauge"""
        if not self.enabled:
            return
        
        self.external_service_availability.labels(service_type=service_type).set(1 if is_available else 0)
    
    def update_active_queries(self, count: int):
        """Update active queries gauge"""
        if not self.enabled:
            return
        
        self.active_queries.set(count)
    
    def increment_active_queries(self):
        """Increment active queries count"""
        if not self.enabled:
            return
        
        self.active_queries.inc()
    
    def decrement_active_queries(self):
        """Decrement active queries count"""
        if not self.enabled:
            return
        
        self.active_queries.dec()
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_metrics_data(self) -> str:
        """Get Prometheus metrics data in text format"""
        if not self.enabled:
            return "# Prometheus metrics not available\n"
        
        return generate_latest(self.registry).decode('utf-8')
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        if not self.enabled:
            return
        
        # Clear registry and reinitialize
        self.registry = CollectorRegistry()
        self._initialize_metrics()
        logger.info("All metrics reset")

# =============================================================================
# DECORATOR FUNCTIONS
# =============================================================================

def monitor_query_performance(endpoint: str = None, query_type: str = "unknown"):
    """Decorator to monitor query performance"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            endpoint_name = endpoint or func.__name__
            
            metrics_collector.increment_active_queries()
            start_time = time.time()
            
            try:
                with metrics_collector.time_query(endpoint_name, query_type):
                    result = await func(*args, **kwargs)
                
                duration = time.time() - start_time
                
                # Extract confidence if available in result
                confidence = None
                if hasattr(result, 'explanation_confidence'):
                    confidence = result.explanation_confidence
                elif isinstance(result, dict) and 'confidence_score' in result:
                    confidence = result['confidence_score']
                
                metrics_collector.record_query_metrics(
                    endpoint=endpoint_name,
                    query_type=query_type,
                    duration=duration,
                    confidence=confidence,
                    status="success"
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_query_metrics(
                    endpoint=endpoint_name,
                    query_type=query_type,
                    duration=duration,
                    status="error"
                )
                raise
            finally:
                metrics_collector.decrement_active_queries()
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            endpoint_name = endpoint or func.__name__
            
            metrics_collector.increment_active_queries()
            start_time = time.time()
            
            try:
                with metrics_collector.time_query(endpoint_name, query_type):
                    result = func(*args, **kwargs)
                
                duration = time.time() - start_time
                metrics_collector.record_query_metrics(
                    endpoint=endpoint_name,
                    query_type=query_type,
                    duration=duration,
                    status="success"
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_query_metrics(
                    endpoint=endpoint_name,
                    query_type=query_type,
                    duration=duration,
                    status="error"
                )
                raise
            finally:
                metrics_collector.decrement_active_queries()
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def monitor_external_service(service_type: str, operation: str = "unknown"):
    """Decorator to monitor external service calls"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                with metrics_collector.time_external_service(service_type, operation):
                    result = await func(*args, **kwargs)
                
                duration = time.time() - start_time
                metrics_collector.record_external_service_metrics(
                    service_type=service_type,
                    operation=operation,
                    duration=duration,
                    status="success"
                )
                
                # Update service availability
                metrics_collector.update_service_availability(service_type, True)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_external_service_metrics(
                    service_type=service_type,
                    operation=operation,
                    duration=duration,
                    status="error"
                )
                
                # Update service availability
                metrics_collector.update_service_availability(service_type, False)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                with metrics_collector.time_external_service(service_type, operation):
                    result = func(*args, **kwargs)
                
                duration = time.time() - start_time
                metrics_collector.record_external_service_metrics(
                    service_type=service_type,
                    operation=operation,
                    duration=duration,
                    status="success"
                )
                
                metrics_collector.update_service_availability(service_type, True)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_external_service_metrics(
                    service_type=service_type,
                    operation=operation,
                    duration=duration,
                    status="error"
                )
                
                metrics_collector.update_service_availability(service_type, False)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# =============================================================================
# GLOBAL METRICS COLLECTOR INSTANCE
# =============================================================================

# Global metrics collector instance
metrics_collector = AdvancedMetricsCollector()

# Initialize service info
if metrics_collector.enabled:
    metrics_collector.service_info.info({
        'service': 'advanced_rag_service',
        'version': '1.0.0',
        'description': 'Advanced RAG Service with comprehensive monitoring'
    })
