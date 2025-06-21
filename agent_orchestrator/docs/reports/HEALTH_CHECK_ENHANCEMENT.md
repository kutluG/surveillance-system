# Enhanced Health Check System - Agent Orchestrator

## Overview

The Agent Orchestrator service now includes a comprehensive health check system that provides deep dependency verification and Kubernetes-ready probes. This enhancement ensures reliable health reporting and better production readiness.

## Features

### 🔍 Deep Health Checks
- **Redis Connectivity**: Verifies connection and performs read/write operations
- **External Service Health**: Checks RAG, Rule Generation, and Notifier services
- **Database Connectivity**: Validates database connection and query execution
- **System Resources**: Monitors CPU, memory, and disk usage
- **Configuration Validation**: Ensures all required settings are present

### 🚀 Kubernetes Integration
- **Liveness Probes**: Basic service availability checks
- **Readiness Probes**: Comprehensive dependency verification
- **Startup Probes**: Handles slow initialization scenarios
- **Graceful Degradation**: Distinguishes between critical and non-critical failures

### 📊 Health Status Levels
- **Healthy**: All components operational
- **Degraded**: Some non-critical issues but service functional
- **Unhealthy**: Critical components failed, service not operational
- **Unknown**: Unable to determine status

## API Endpoints

### Basic Health Check
```
GET /health
```
- **Purpose**: Quick health status for basic monitoring
- **Response Time**: < 5 seconds
- **Checks**: Redis, RAG service, configuration

**Example Response:**
```json
{
  "status": "healthy",
  "message": "All components are healthy and operational",
  "timestamp": "2025-06-14T10:30:00.000Z",
  "components": [
    {
      "component": "redis",
      "status": "healthy",
      "message": "Redis is accessible and operational",
      "response_time": 0.123
    }
  ],
  "summary": {
    "total_components": 3,
    "healthy": 3,
    "health_percentage": 100.0
  },
  "uptime": 1800.5
}
```

### Readiness Probe
```
GET /health/ready
```
- **Purpose**: Kubernetes readiness probe
- **Response Time**: < 10 seconds
- **Checks**: Critical dependencies for accepting traffic

**Use Case:**
```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8006
  initialDelaySeconds: 15
  periodSeconds: 10
  timeoutSeconds: 10
  failureThreshold: 3
```

### Liveness Probe
```
GET /health/live
```
- **Purpose**: Kubernetes liveness probe
- **Response Time**: < 5 seconds
- **Checks**: Basic service availability

**Use Case:**
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8006
  initialDelaySeconds: 30
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3
```

### Full Health Status
```
GET /health/full
```
- **Purpose**: Comprehensive health report
- **Response Time**: < 15 seconds
- **Checks**: All components including non-critical ones

## Component Health Checks

### 1. Redis Cache
**Verification:**
- Connection establishment
- Set/Get operations
- Key deletion
- Redis server info

**Failure Modes:**
- Connection refused
- Authentication failure
- Operation timeout
- Memory issues

### 2. External Services
**RAG Service:**
- Health endpoint availability
- Response time measurement
- Service-specific status validation

**Rule Generation Service:**
- Connection verification
- Health endpoint check
- Fallback capability assessment

**Notifier Service:**
- Health endpoint availability
- Non-critical failure handling

### 3. Database
**Verification:**
- Connection establishment
- Simple query execution
- Connection pooling status

**Configuration:**
- Supports PostgreSQL with async drivers
- Configurable timeout and retry settings

### 4. System Resources
**Monitoring:**
- CPU usage percentage
- Memory utilization
- Disk space availability
- Process health

**Thresholds:**
- CPU > 90% → Degraded
- Memory > 90% → Degraded  
- Disk > 95% → Degraded

### 5. Configuration
**Validation:**
- Required environment variables
- Service URL formats
- Port availability
- Security settings

## Configuration

### Environment Variables
```bash
# Health Check Configuration
HEALTH_CHECK_TIMEOUT=10.0
HEALTH_CHECK_REDIS_TIMEOUT=5.0
HEALTH_CHECK_DB_TIMEOUT=10.0
HEALTH_CHECK_SERVICE_TIMEOUT=15.0

# Component URLs (inherited from main config)
REDIS_URL=redis://redis:6379/0
RAG_SERVICE_URL=http://advanced_rag_service:8000
RULEGEN_SERVICE_URL=http://rulegen_service:8000
NOTIFIER_SERVICE_URL=http://notifier:8000
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
```

### Critical vs Non-Critical Components
**Critical Components:**
- Redis (caching and queuing)
- RAG Service (core functionality)
- Configuration (service startup)

**Non-Critical Components:**
- Notifier Service (degraded notifications)
- System Resources (performance monitoring)
- Database (if not essential for core operations)

## Health Check Implementation

### Python Code Example
```python
from health_check import basic_health_check, readiness_probe, liveness_probe

# Basic health check
health_result = await basic_health_check()
if health_result["status"] == "healthy":
    print("Service is healthy")

# Readiness probe
is_ready, health_data = await readiness_probe()
if is_ready:
    print("Service ready to accept traffic")

# Liveness probe  
is_alive, health_data = await liveness_probe()
if not is_alive:
    print("Service should be restarted")
```

### Custom Health Checks
```python
from health_check import HealthChecker

async def custom_health_check():
    async with HealthChecker() as checker:
        # Check specific components
        result = await checker.perform_health_check(
            component_filter=["redis", "rag_service"],
            include_non_critical=False
        )
        return result
```

## Monitoring Integration

### Prometheus Metrics
The health check system integrates with the existing metrics collection:

```
# Health check duration
agent_orchestrator_health_check_duration_seconds

# Component health status
agent_orchestrator_component_health_status

# Health check failures
agent_orchestrator_health_check_failures_total
```

### Alerting Rules
```yaml
# Prometheus alerting rules
groups:
- name: agent_orchestrator_health
  rules:
  - alert: AgentOrchestratorUnhealthy
    expr: agent_orchestrator_component_health_status{status="unhealthy"} > 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Agent Orchestrator service unhealthy"
      
  - alert: AgentOrchestratorDegraded
    expr: agent_orchestrator_component_health_status{status="degraded"} > 0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Agent Orchestrator service degraded"
```

## Deployment Configuration

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-orchestrator
spec:
  template:
    spec:
      containers:
      - name: agent-orchestrator
        # Enhanced health checks
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8006
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8006
          initialDelaySeconds: 15
          periodSeconds: 10
          timeoutSeconds: 10
          failureThreshold: 3
        
        startupProbe:
          httpGet:
            path: /health/live
            port: 8006
          initialDelaySeconds: 10
          periodSeconds: 10
          failureThreshold: 10
```

### Docker Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1
```

## Testing

### Unit Tests
```bash
# Run health check tests
pytest test_health_check.py -v

# Run specific test categories
pytest test_health_check.py::TestHealthChecker -v
pytest test_health_check.py::TestHealthCheckEndpoints -v
```

### Integration Tests
```bash
# Test with real dependencies (Redis required)
pytest test_health_check.py::TestHealthCheckIntegration -v
```

### Load Testing
```bash
# Test health endpoints under load
wrk -t12 -c400 -d30s http://localhost:8006/health
wrk -t12 -c400 -d30s http://localhost:8006/health/ready
```

## Troubleshooting

### Common Issues

**Redis Connection Failures:**
```bash
# Check Redis connectivity
redis-cli -h redis -p 6379 ping

# Check Redis configuration
kubectl logs agent-orchestrator -c agent-orchestrator | grep redis
```

**Service Discovery Issues:**
```bash
# Check service DNS resolution
nslookup advanced-rag-service
nslookup rulegen-service

# Check service endpoints
kubectl get endpoints
```

**Resource Constraints:**
```bash
# Check pod resources
kubectl top pods agent-orchestrator

# Check resource limits
kubectl describe pod agent-orchestrator
```

### Health Check Failures

**Critical Component Failures:**
- Service marked as unhealthy
- Kubernetes will not route traffic
- Requires immediate attention

**Non-Critical Component Failures:**
- Service marked as degraded
- Traffic still routed (with warnings)
- Monitor for degraded performance

### Performance Optimization

**Health Check Timing:**
- Liveness: 30s intervals (stability)
- Readiness: 10s intervals (responsiveness)
- Startup: 10s intervals × 10 attempts (initialization)

**Timeout Configuration:**
- Redis: 5s (fast cache operations)
- Database: 10s (query execution)
- External Services: 15s (network latency)

## Benefits

### 🔧 Operational Benefits
- **Early Problem Detection**: Identify issues before they impact users
- **Automated Recovery**: Kubernetes restarts unhealthy pods automatically
- **Reduced MTTR**: Faster problem diagnosis and resolution
- **Better Monitoring**: Detailed health status for operational teams

### 🏗️ Development Benefits
- **Local Development**: Test dependency health during development
- **CI/CD Integration**: Verify deployment health automatically
- **Testing Support**: Mock health checks for unit tests
- **Debugging Aid**: Detailed component status for troubleshooting

### 📈 Production Benefits
- **High Availability**: Prevents routing to unhealthy instances
- **Graceful Degradation**: Continues operation when possible
- **Performance Monitoring**: Track component response times
- **Compliance**: Meet health check requirements for production systems

## Migration Guide

### From Basic Health Checks
1. **Update Dependencies**: Add `psutil==5.9.6` to requirements.txt
2. **Import New Module**: Replace health check implementation
3. **Update Kubernetes**: Use new probe endpoints
4. **Test Deployment**: Verify health checks work correctly

### Configuration Changes
```diff
# Kubernetes deployment.yaml
- path: /health
+ path: /health/ready

# Docker health check
- CMD curl -f http://localhost:8006/health
+ CMD curl -f http://localhost:8006/health || exit 1
```

This enhanced health check system provides robust monitoring capabilities essential for production deployments while maintaining simplicity for development and testing scenarios.
