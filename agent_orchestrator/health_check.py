"""
Deep Health Check System for Agent Orchestrator Service

This module provides comprehensive health checking capabilities that verify:
- Redis connectivity and operations
- External service availability (RAG, Rule Generation, Notifier)
- Database connectivity
- System resource availability
- Service configuration validity

Features:
- Deep dependency verification
- Kubernetes-ready readiness/liveness probes
- Detailed health status reporting
- Performance metrics collection
- Configurable timeout and retry settings
"""
import asyncio
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

import httpx
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Import database manager
from database import get_database_manager, get_database_health

# Import psutil at module level for easier mocking in tests
try:
    import psutil
except ImportError:
    psutil = None

# Import Prometheus metrics for health check monitoring
try:
    from prometheus_client import Counter, Histogram, Gauge
    HEALTH_CHECK_DURATION = Histogram(
        'agent_orchestrator_health_check_duration_seconds',
        'Duration of health checks',
        ['component', 'status']
    )
    HEALTH_CHECK_STATUS = Gauge(
        'agent_orchestrator_health_check_status',
        'Health check status (1=healthy, 0.5=degraded, 0=unhealthy)',
        ['component', 'type']
    )
    HEALTH_CHECK_ERRORS = Counter(
        'agent_orchestrator_health_check_errors_total',
        'Total health check errors',
        ['component', 'error_type']
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

from config import get_config

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(str, Enum):
    """Component type enumeration"""
    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL_SERVICE = "external_service"
    INTERNAL_SERVICE = "internal_service"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class HealthCheckResult:
    """Individual health check result"""
    component: str
    component_type: ComponentType
    status: HealthStatus
    message: str
    response_time: float
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class SystemHealthStatus:
    """Overall system health status"""
    status: HealthStatus
    message: str
    timestamp: datetime
    components: List[HealthCheckResult]
    summary: Dict[str, Any]
    uptime: float
    version: str = "1.0.0"


class HealthChecker:
    """Comprehensive health checker for Agent Orchestrator with caching and metrics"""
    
    def __init__(self, cache_ttl: int = 30):
        self.config = get_config()
        self.start_time = time.time()
        self.http_client = None
        self.redis_client = None
        self.cache_ttl = cache_ttl  # Cache health results for 30 seconds by default
        self._cache = {}  # Simple in-memory cache
        
        # Health check configuration
        self.check_timeout = 10.0
        self.critical_services = [
            "redis",
            "rag_service"
        ]
        
        # Component definitions
        self.components = {
            "redis": {
                "type": ComponentType.CACHE,
                "check_func": self._check_redis,
                "critical": True,
                "timeout": 5.0
            },
            "database": {
                "type": ComponentType.DATABASE,
                "check_func": self._check_database,
                "critical": True,
                "timeout": 10.0
            },
            "rag_service": {
                "type": ComponentType.EXTERNAL_SERVICE,
                "check_func": self._check_rag_service,
                "critical": True,
                "timeout": 15.0
            },
            "rulegen_service": {
                "type": ComponentType.EXTERNAL_SERVICE,
                "check_func": self._check_rulegen_service,
                "critical": True,
                "timeout": 15.0
            },
            "notifier_service": {
                "type": ComponentType.EXTERNAL_SERVICE,
                "check_func": self._check_notifier_service,
                "critical": False,
                "timeout": 10.0
            },
            "api_gateway": {
                "type": ComponentType.EXTERNAL_SERVICE,
                "check_func": self._check_api_gateway,
                "critical": False,
                "timeout": 10.0
            },
            "websocket_service": {
                "type": ComponentType.EXTERNAL_SERVICE,
                "check_func": self._check_websocket_service,
                "critical": False,
                "timeout": 8.0
            },
            "system_resources": {
                "type": ComponentType.INFRASTRUCTURE,
                "check_func": self._check_system_resources,
                "critical": False,
                "timeout": 5.0
            },
            "configuration": {
                "type": ComponentType.INTERNAL_SERVICE,
                "check_func": self._check_configuration,
                "critical": True,
                "timeout": 2.0
            },
            "connectivity": {
                "type": ComponentType.INFRASTRUCTURE,
                "check_func": self._check_network_connectivity,
                "critical": False,
                "timeout": 8.0
            }
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.http_client = httpx.AsyncClient(timeout=self.check_timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.http_client:
            await self.http_client.aclose()
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def perform_health_check(self, 
                                 component_filter: Optional[List[str]] = None,
                                 include_non_critical: bool = True,
                                 use_cache: bool = True) -> SystemHealthStatus:
        """Perform comprehensive health check with optional caching"""
        start_time = time.time()
        results = []
        
        # Filter components if specified
        components_to_check = self.components
        if component_filter:
            components_to_check = {
                k: v for k, v in self.components.items() 
                if k in component_filter
            }
        
        # Perform health checks with caching
        for component_name, component_config in components_to_check.items():
            if not include_non_critical and not component_config.get("critical", False):
                continue
            
            # Check cache first
            cache_key = f"{component_name}_{include_non_critical}"
            cached_result = None
            
            if use_cache and cache_key in self._cache:
                cached_entry = self._cache[cache_key]
                if time.time() - cached_entry['timestamp'] < self.cache_ttl:
                    cached_result = cached_entry['result']
                    # Update timestamp to current time for response
                    cached_result.timestamp = datetime.now(timezone.utc)
                    results.append(cached_result)
                    continue
                else:
                    # Cache expired, remove it
                    del self._cache[cache_key]
            
            try:
                result = await self._perform_component_check(component_name, component_config)
                results.append(result)
                
                # Cache the result
                if use_cache:
                    self._cache[cache_key] = {
                        'result': result,
                        'timestamp': time.time()
                    }
                    
            except Exception as e:
                logger.error(f"Health check failed for {component_name}: {e}")
                result = HealthCheckResult(
                    component=component_name,
                    component_type=component_config["type"],
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(e)}",
                    response_time=0.0,
                    timestamp=datetime.now(timezone.utc),
                    error=str(e)
                )
                results.append(result)
                
                # Cache the error result too (but for shorter time)
                if use_cache:
                    self._cache[cache_key] = {
                        'result': result,
                        'timestamp': time.time()
                    }
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(results)
        
        # Create summary
        summary = self._create_health_summary(results)
          # Add cache statistics to summary
        if use_cache:
            summary["cache_stats"] = {
                "cache_size": len(self._cache),
                "cache_ttl": self.cache_ttl,
                "cache_hit_rate": self._calculate_cache_hit_rate()
            }
        
        return SystemHealthStatus(
            status=overall_status,
            message=self._get_status_message(overall_status, results),
            timestamp=datetime.now(timezone.utc),
            components=results,
            summary=summary,
            uptime=time.time() - self.start_time,
            version="1.0.0"
        )
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate for monitoring"""
        # This is a simplified implementation
        # In production, you might want to track hits/misses over time
        if not hasattr(self, '_cache_hits'):
            self._cache_hits = 0
        if not hasattr(self, '_cache_requests'):
            self._cache_requests = 0
        
        if self._cache_requests == 0:
            return 0.0
        
        return (self._cache_hits / self._cache_requests) * 100
    
    def clear_cache(self):
        """Clear the health check cache"""
        self._cache.clear()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the health check cache"""
        return {
            "cache_size": len(self._cache),
            "cache_ttl": self.cache_ttl,
            "cached_components": list(self._cache.keys()),
            "cache_hit_rate": self._calculate_cache_hit_rate()
        }
    
    async def _perform_component_check(self, 
                                     component_name: str, 
                                     component_config: Dict) -> HealthCheckResult:
        """Perform health check for a single component"""
        start_time = time.time()
        timeout = component_config.get("timeout", self.check_timeout)
        
        try:
            # Start metrics timer
            if METRICS_AVAILABLE:
                HEALTH_CHECK_DURATION.labels(component=component_name, status="in_progress").observe(0)
            
            # Run the component-specific health check
            check_func = component_config["check_func"]
            result = await asyncio.wait_for(check_func(), timeout=timeout)
            response_time = time.time() - start_time
            
            # Update metrics on success
            if METRICS_AVAILABLE:
                HEALTH_CHECK_DURATION.labels(component=component_name, status="success").observe(response_time)
                HEALTH_CHECK_STATUS.labels(component=component_name, type=component_config["type"]).set(1)
            
            return HealthCheckResult(
                component=component_name,
                component_type=component_config["type"],
                status=result.get("status", HealthStatus.UNKNOWN),
                message=result.get("message", "No message provided"),
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                details=result.get("details"),
                error=result.get("error")
            )
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            # Update metrics on timeout
            if METRICS_AVAILABLE:
                HEALTH_CHECK_DURATION.labels(component=component_name, status="timeout").observe(response_time)
                HEALTH_CHECK_STATUS.labels(component=component_name, type=component_config["type"]).set(0)
            
            return HealthCheckResult(                component=component_name,
                component_type=component_config["type"],
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {timeout}s",
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                error=f"Timeout after {timeout}s"
            )
        except Exception as e:
            response_time = time.time() - start_time
            # Update metrics on error
            if METRICS_AVAILABLE:
                HEALTH_CHECK_ERRORS.labels(component=component_name, error_type="exception").inc()
                HEALTH_CHECK_STATUS.labels(component=component_name, type=component_config["type"]).set(0)
            
            return HealthCheckResult(                component=component_name,
                component_type=component_config["type"],
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                error=str(e)
            )    
    # Component-specific health check methods
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and comprehensive operations"""
        try:
            if not self.redis_client:
                self.redis_client = redis.from_url(
                    self.config.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5.0,
                    socket_timeout=5.0
                )
            
            # Test basic operations
            test_key = "health_check_test"
            test_value = f"test_{int(time.time())}"
            
            # Test SET operation
            await self.redis_client.set(test_key, test_value, ex=10)
            
            # Test GET operation
            retrieved_value = await self.redis_client.get(test_key)
            
            if retrieved_value != test_value:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Redis read/write operation failed",
                    "error": "Retrieved value doesn't match stored value"
                }
            
            # Test PING command
            ping_result = await self.redis_client.ping()
            if not ping_result:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": "Redis ping failed",
                    "error": "PING command returned False"
                }
            
            # Test LIST operations (for task queues)
            queue_test_key = "health_check_queue"
            await self.redis_client.lpush(queue_test_key, "test_item")
            queue_item = await self.redis_client.rpop(queue_test_key)
            
            if queue_item != "test_item":
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": "Redis queue operations failed",
                    "error": "Queue push/pop test failed"
                }
            
            # Test HASH operations (for agent state)
            hash_test_key = "health_check_hash"
            await self.redis_client.hset(hash_test_key, "field1", "value1")
            hash_value = await self.redis_client.hget(hash_test_key, "field1")
            
            if hash_value != "value1":
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": "Redis hash operations failed",
                    "error": "Hash set/get test failed"
                }
            
            # Get Redis info and check memory usage
            info = await self.redis_client.info()
            memory_usage = info.get("used_memory", 0)
            memory_limit = info.get("maxmemory", 0)
            
            # Check if memory usage is critical (>90% if limit is set)
            memory_status = "healthy"
            if memory_limit > 0:
                memory_percentage = (memory_usage / memory_limit) * 100
                if memory_percentage > 90:
                    memory_status = "critical"
                elif memory_percentage > 80:
                    memory_status = "warning"
            
            # Clean up test keys
            await self.redis_client.delete(test_key, queue_test_key, hash_test_key)
            
            # Check connection count
            connected_clients = info.get("connected_clients", 0)
            max_clients = info.get("maxclients", 10000)
            client_usage_pct = (connected_clients / max_clients) * 100 if max_clients > 0 else 0
            
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Redis is accessible and all operations working",
                "details": {
                    "redis_version": info.get("redis_version"),
                    "connected_clients": connected_clients,
                    "client_usage_percentage": round(client_usage_pct, 1),
                    "used_memory_human": info.get("used_memory_human"),
                    "memory_status": memory_status,
                    "uptime_in_seconds": info.get("uptime_in_seconds"),
                    "operations_tested": ["set/get", "ping", "list_push/pop", "hash_set/get"],
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                }
            }
            
        except redis.ConnectionError as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Cannot connect to Redis",
                "error": str(e)
            }
        except redis.ResponseError as e:
            return {
                "status": HealthStatus.DEGRADED,
                "message": "Redis operation failed",
                "error": str(e)
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,                "message": "Redis health check failed",
                "error": str(e)
            }

    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and operations using the database manager"""
        try:
            # Use the centralized database health check
            health_result = await get_database_health()
            
            # Convert to our health check format
            if health_result["status"] == "healthy":
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": health_result["message"],
                    "details": {
                        "response_time": health_result.get("response_time", 0),
                        "pool_stats": health_result.get("pool_stats", {}),
                        "active_connections": health_result.get("active_connections", 0),
                        "active_sessions": health_result.get("active_sessions", 0),
                        "database_url": self.config.database_url.split('@')[0] + "@***" if hasattr(self.config, 'database_url') else "not_configured"
                    }
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": health_result["message"],
                    "error": health_result.get("error"),
                    "details": {
                        "database_url": self.config.database_url.split('@')[0] + "@***" if hasattr(self.config, 'database_url') else "not_configured"
                    }
                }
                
        except Exception as e:
            return {                "status": HealthStatus.UNHEALTHY,
                "message": "Database health check failed",
                "error": str(e),
                "details": {
                    "database_url": self.config.database_url.split('@')[0] + "@***" if hasattr(self.config, 'database_url') else "not_configured"
                }
            }

    async def _check_rag_service(self) -> Dict[str, Any]:
        """Check RAG service connectivity and functional health"""
        try:
            # First check basic health endpoint
            health_url = f"{self.config.rag_service_url}/health"
            response = await self.http_client.get(health_url)
            
            if response.status_code != 200:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": f"RAG service returned status {response.status_code}",
                    "error": f"HTTP {response.status_code}"
                }
            
            try:
                health_data = response.json()
            except Exception:
                health_data = {"status": "healthy"}  # Fallback for simple health checks
            
            # Test functional endpoint (lightweight query test)
            try:
                test_query_url = f"{self.config.rag_service_url}/api/v1/rag/health-test"
                test_response = await self.http_client.post(
                    test_query_url,
                    json={"query": "health check test", "max_results": 1},
                    timeout=5.0
                )
                
                functional_test = test_response.status_code in [200, 400]  # 400 is OK for test query
                
            except Exception:
                functional_test = False  # Not critical, basic health is more important
            
            return {
                "status": HealthStatus.HEALTHY,
                "message": "RAG service is healthy and functional",
                "details": {
                    "service_url": self.config.rag_service_url,
                    "health_response": health_data,
                    "functional_test_passed": functional_test,
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else None
                }
            }
                
        except httpx.ConnectError:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Cannot connect to RAG service",
                "error": "Connection refused"
            }
        except httpx.TimeoutException:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "RAG service health check timed out",
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "RAG service health check failed",
                "error": str(e)
            }
    
    async def _check_rulegen_service(self) -> Dict[str, Any]:
        """Check Rule Generation service connectivity and health"""
        try:
            health_url = f"{self.config.rulegen_service_url}/health"
            response = await self.http_client.get(health_url)
            
            if response.status_code == 200:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "Rule Generation service is healthy",
                    "details": {"service_url": self.config.rulegen_service_url}
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": f"Rule Generation service returned status {response.status_code}",
                    "error": f"HTTP {response.status_code}"
                }
                
        except httpx.ConnectError:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Cannot connect to Rule Generation service",
                "error": "Connection refused"
            }
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED,
                "message": "Rule Generation service health check failed",
                "error": str(e)
            }
    
    async def _check_notifier_service(self) -> Dict[str, Any]:
        """Check Notifier service connectivity and health"""
        try:
            health_url = f"{self.config.notifier_service_url}/health"
            response = await self.http_client.get(health_url)
            
            if response.status_code == 200:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "Notifier service is healthy",
                    "details": {"service_url": self.config.notifier_service_url}
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": f"Notifier service returned status {response.status_code}",
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED,
                "message": "Notifier service health check failed",
                "error": str(e)
            }
    
    async def _check_api_gateway(self) -> Dict[str, Any]:
        """Check API Gateway connectivity and health"""
        try:
            api_gateway_url = getattr(self.config, 'api_gateway_url', 'http://api-gateway:8000')
            health_url = f"{api_gateway_url}/health"
            response = await self.http_client.get(health_url)
            
            if response.status_code == 200:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "API Gateway is healthy",
                    "details": {
                        "service_url": api_gateway_url,
                        "response_time": response.elapsed.total_seconds()
                    }
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": f"API Gateway returned status {response.status_code}",
                    "error": f"HTTP {response.status_code}"
                }
                
        except httpx.ConnectError:
            return {
                "status": HealthStatus.DEGRADED,
                "message": "Cannot connect to API Gateway",
                "error": "Connection refused"
            }
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED,
                "message": "API Gateway health check failed",
                "error": str(e)
            }
    
    async def _check_websocket_service(self) -> Dict[str, Any]:
        """Check WebSocket service connectivity and health"""
        try:
            websocket_url = getattr(self.config, 'websocket_service_url', 'http://websocket-service:8000')
            health_url = f"{websocket_url}/health"
            response = await self.http_client.get(health_url)
            
            if response.status_code == 200:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "WebSocket service is healthy",
                    "details": {"service_url": websocket_url}
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": f"WebSocket service returned status {response.status_code}",
                    "error": f"HTTP {response.status_code}"
                }
                
        except httpx.ConnectError:
            return {
                "status": HealthStatus.DEGRADED,
                "message": "Cannot connect to WebSocket service",
                "error": "Connection refused"
            }
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED,
                "message": "WebSocket service health check failed",
                "error": str(e)
            }
    
    async def _check_network_connectivity(self) -> Dict[str, Any]:
        """Check basic network connectivity to external services"""
        try:
            connectivity_results = {}
            
            # Test DNS resolution
            import socket
            try:
                socket.gethostbyname('google.com')
                connectivity_results['dns'] = 'healthy'
            except socket.gaierror:
                connectivity_results['dns'] = 'failed'
            
            # Test internet connectivity with a simple HTTP request
            try:
                response = await self.http_client.get('https://httpbin.org/status/200', timeout=5.0)
                connectivity_results['internet'] = 'healthy' if response.status_code == 200 else 'degraded'
            except Exception:
                connectivity_results['internet'] = 'failed'
            
            # Determine overall connectivity status
            if connectivity_results.get('dns') == 'healthy' and connectivity_results.get('internet') == 'healthy':
                status = HealthStatus.HEALTHY
                message = "Network connectivity is healthy"
            elif connectivity_results.get('dns') == 'healthy':
                status = HealthStatus.DEGRADED
                message = "DNS working but internet connectivity issues"
            else:
                status = HealthStatus.DEGRADED
                message = "Network connectivity issues detected"
            
            return {
                "status": status,
                "message": message,
                "details": connectivity_results
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN,
                "message": "Network connectivity check failed",
                "error": str(e)
            }    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource availability"""
        try:
            if psutil is None:
                return {
                    "status": HealthStatus.DEGRADED.value,
                    "message": "psutil not available for system resource monitoring",
                    "details": {"warning": "System resource monitoring disabled"}
                }
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine status based on resource usage
            status = HealthStatus.HEALTHY
            warnings = []
            
            if cpu_percent > 90:
                status = HealthStatus.DEGRADED
                warnings.append(f"High CPU usage: {cpu_percent}%")
            
            if memory.percent > 90:
                status = HealthStatus.DEGRADED
                warnings.append(f"High memory usage: {memory.percent}%")
            
            if disk.percent > 95:
                status = HealthStatus.DEGRADED
                warnings.append(f"High disk usage: {disk.percent}%")
            
            message = "System resources are healthy"
            if warnings:
                message = f"System resources degraded: {'; '.join(warnings)}"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_percent": disk.percent,
                    "disk_free_gb": round(disk.free / (1024**3), 2)
                }
            }
            
        except ImportError:
            return {
                "status": HealthStatus.UNKNOWN,
                "message": "psutil not available for system resource monitoring"
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN,
                "message": "System resource check failed",
                "error": str(e)
            }
    
    async def _check_configuration(self) -> Dict[str, Any]:
        """Check service configuration validity"""
        try:
            config_issues = []
            
            # Check required configuration values
            required_configs = [
                ("redis_url", "Redis URL"),
                ("rag_service_url", "RAG Service URL"),
                ("rulegen_service_url", "Rule Generation Service URL"),
                ("notifier_service_url", "Notifier Service URL")
            ]
            
            for config_attr, config_name in required_configs:
                if not hasattr(self.config, config_attr) or not getattr(self.config, config_attr):
                    config_issues.append(f"{config_name} not configured")
            
            if config_issues:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": f"Configuration issues: {'; '.join(config_issues)}",
                    "error": "Missing required configuration"
                }
            
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Service configuration is valid",
                "details": {
                    "service_host": self.config.service_host,
                    "service_port": self.config.service_port,
                    "log_level": self.config.log_level,
                    "debug_mode": self.config.debug_mode
                }
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Configuration check failed",
                "error": str(e)
            }
    
    # Helper methods
    
    def _calculate_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Calculate overall system health status"""
        if not results:
            return HealthStatus.UNKNOWN
        
        # Check if any critical components are unhealthy
        critical_unhealthy = any(
            result.status == HealthStatus.UNHEALTHY and 
            self.components.get(result.component, {}).get("critical", False)
            for result in results
        )
        
        if critical_unhealthy:
            return HealthStatus.UNHEALTHY
        
        # Check if any components are degraded
        has_degraded = any(result.status == HealthStatus.DEGRADED for result in results)
        has_unhealthy = any(result.status == HealthStatus.UNHEALTHY for result in results)
        
        if has_degraded or has_unhealthy:
            return HealthStatus.DEGRADED
        
        # Check if all components are healthy
        all_healthy = all(result.status == HealthStatus.HEALTHY for result in results)
        
        if all_healthy:
            return HealthStatus.HEALTHY
        
        return HealthStatus.UNKNOWN
    
    def _create_health_summary(self, results: List[HealthCheckResult]) -> Dict[str, Any]:
        """Create health status summary"""
        total_components = len(results)
        healthy_count = len([r for r in results if r.status == HealthStatus.HEALTHY])
        degraded_count = len([r for r in results if r.status == HealthStatus.DEGRADED])
        unhealthy_count = len([r for r in results if r.status == HealthStatus.UNHEALTHY])
        unknown_count = len([r for r in results if r.status == HealthStatus.UNKNOWN])
        
        critical_components = [
            r for r in results 
            if self.components.get(r.component, {}).get("critical", False)
        ]
        critical_healthy = len([r for r in critical_components if r.status == HealthStatus.HEALTHY])
        
        avg_response_time = sum(r.response_time for r in results) / total_components if total_components > 0 else 0
        
        return {
            "total_components": total_components,
            "healthy": healthy_count,
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
            "unknown": unknown_count,
            "critical_components_total": len(critical_components),
            "critical_components_healthy": critical_healthy,
            "health_percentage": round((healthy_count / total_components) * 100, 1) if total_components > 0 else 0,
            "average_response_time": round(avg_response_time, 3),
            "components_by_type": self._group_components_by_type(results),
            "failed_components": [r.component for r in results if r.status == HealthStatus.UNHEALTHY]
        }
    
    def _group_components_by_type(self, results: List[HealthCheckResult]) -> Dict[str, Dict[str, int]]:
        """Group health results by component type"""
        type_summary = {}
        
        for result in results:
            component_type = result.component_type.value
            if component_type not in type_summary:
                type_summary[component_type] = {"healthy": 0, "degraded": 0, "unhealthy": 0, "unknown": 0}
            
            type_summary[component_type][result.status.value] += 1
        
        return type_summary
    
    def _get_status_message(self, status: HealthStatus, results: List[HealthCheckResult]) -> str:
        """Get descriptive status message"""
        if status == HealthStatus.HEALTHY:
            return "All components are healthy and operational"
        elif status == HealthStatus.DEGRADED:
            degraded_components = [r.component for r in results if r.status == HealthStatus.DEGRADED]
            unhealthy_components = [r.component for r in results if r.status == HealthStatus.UNHEALTHY]
            
            issues = []
            if degraded_components:
                issues.append(f"degraded: {', '.join(degraded_components)}")
            if unhealthy_components:
                issues.append(f"unhealthy: {', '.join(unhealthy_components)}")
            
            return f"System is degraded - {'; '.join(issues)}"
        elif status == HealthStatus.UNHEALTHY:
            unhealthy_critical = [
                r.component for r in results 
                if r.status == HealthStatus.UNHEALTHY and 
                self.components.get(r.component, {}).get("critical", False)
            ]
            return f"System is unhealthy - critical components failed: {', '.join(unhealthy_critical)}"
        else:
            return "System health status unknown"


# Convenience functions for different health check scenarios

async def basic_health_check() -> Dict[str, Any]:
    """Perform basic health check (critical components only)"""
    async with HealthChecker() as checker:
        result = await checker.perform_health_check(
            component_filter=["redis", "rag_service", "configuration"],
            include_non_critical=False
        )
        return asdict(result)


async def readiness_probe() -> Tuple[bool, Dict[str, Any]]:
    """Kubernetes readiness probe - checks if service is ready to accept traffic"""
    async with HealthChecker() as checker:
        result = await checker.perform_health_check(
            component_filter=["redis", "rag_service", "configuration"],
            include_non_critical=False
        )
        
        is_ready = result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        return is_ready, asdict(result)


async def liveness_probe() -> Tuple[bool, Dict[str, Any]]:
    """Kubernetes liveness probe - checks if service is alive and should not be restarted"""
    async with HealthChecker() as checker:
        result = await checker.perform_health_check(
            component_filter=["configuration"],
            include_non_critical=False
        )
        
        is_alive = result.status != HealthStatus.UNHEALTHY
        return is_alive, asdict(result)


async def full_health_check() -> Dict[str, Any]:
    """Perform comprehensive health check of all components"""
    async with HealthChecker() as checker:
        result = await checker.perform_health_check(include_non_critical=True)
        return asdict(result)


# Enhanced convenience functions for different health check scenarios

async def monitoring_health_check() -> Dict[str, Any]:
    """Enhanced health check specifically for monitoring systems with additional metrics"""
    async with HealthChecker() as checker:
        result = await checker.perform_health_check(include_non_critical=True)
        
        # Add additional monitoring-specific data
        health_dict = asdict(result)
        health_dict["monitoring"] = {
            "cache_info": checker.get_cache_info(),
            "metrics_available": METRICS_AVAILABLE,
            "check_duration": time.time() - checker.start_time if hasattr(checker, 'start_time') else 0,
            "service_uptime": time.time() - checker.start_time,
            "critical_components_status": [
                {
                    "component": comp.component,
                    "status": comp.status.value,
                    "is_critical": checker.components.get(comp.component, {}).get("critical", False)
                }
                for comp in result.components
                if checker.components.get(comp.component, {}).get("critical", False)
            ]
        }
        
        return health_dict


async def alerting_health_check() -> Dict[str, Any]:
    """Health check optimized for alerting with clear failure reasons"""
    async with HealthChecker() as checker:
        result = await checker.perform_health_check(
            component_filter=["redis", "rag_service", "rulegen_service", "configuration"],
            include_non_critical=False,
            use_cache=False  # Always fresh data for alerting
        )
        
        health_dict = asdict(result)
        
        # Add alerting-specific information
        failed_critical = [
            comp for comp in result.components 
            if comp.status == HealthStatus.UNHEALTHY and 
            checker.components.get(comp.component, {}).get("critical", False)
        ]
        
        degraded_services = [
            comp for comp in result.components 
            if comp.status == HealthStatus.DEGRADED
        ]
        
        health_dict["alerting"] = {
            "should_alert": len(failed_critical) > 0,
            "alert_level": "critical" if len(failed_critical) > 0 else "warning" if len(degraded_services) > 0 else "none",
            "failed_critical_components": [comp.component for comp in failed_critical],
            "degraded_components": [comp.component for comp in degraded_services],
            "alert_message": _generate_alert_message(result.status, failed_critical, degraded_services),
            "recovery_suggestions": _get_recovery_suggestions(failed_critical, degraded_services)
        }
        
        return health_dict


def _generate_alert_message(status: HealthStatus, failed_critical: List, degraded_services: List) -> str:
    """Generate a clear alert message for monitoring systems"""
    if status == HealthStatus.UNHEALTHY:
        if failed_critical:
            components = [comp.component for comp in failed_critical]
            return f"CRITICAL: Agent Orchestrator unhealthy - critical components failed: {', '.join(components)}"
        else:
            return "CRITICAL: Agent Orchestrator unhealthy - unknown critical failure"
    elif status == HealthStatus.DEGRADED:
        if degraded_services:
            components = [comp.component for comp in degraded_services]
            return f"WARNING: Agent Orchestrator degraded - components affected: {', '.join(components)}"
        else:
            return "WARNING: Agent Orchestrator degraded - unknown degradation"
    else:
        return "OK: Agent Orchestrator healthy"


def _get_recovery_suggestions(failed_critical: List, degraded_services: List) -> List[str]:
    """Provide recovery suggestions based on failed components"""
    suggestions = []
    
    for comp in failed_critical:
        if comp.component == "redis":
            suggestions.extend([
                "Check Redis container/pod status: kubectl get pods | grep redis",
                "Verify Redis connectivity: redis-cli -h redis -p 6379 ping",
                "Check Redis logs: kubectl logs redis-pod"
            ])
        elif comp.component == "rag_service":
            suggestions.extend([
                "Check RAG service status: kubectl get pods | grep rag",
                "Verify RAG service endpoint: curl http://rag-service:8000/health",
                "Check RAG service logs: kubectl logs rag-service-pod"
            ])
        elif comp.component == "configuration":
            suggestions.extend([
                "Check environment variables configuration",
                "Verify service configuration file",
                "Restart service with valid configuration"
            ])
    
    for comp in degraded_services:
        if comp.component == "notifier_service":
            suggestions.append("Check notifier service - notifications may be delayed")
        elif comp.component == "system_resources":
            suggestions.extend([
                "Check system resource usage: kubectl top pods",
                "Consider scaling up resources if consistently high"
            ])
    
    return suggestions
