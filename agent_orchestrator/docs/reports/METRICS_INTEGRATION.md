# Agent Orchestrator Metrics Integration

## Overview

The Agent Orchestrator service now includes comprehensive Prometheus metrics collection for monitoring orchestration performance, service health, and operational metrics.

## Metrics Endpoints

### `/metrics`
- **Format**: Prometheus text format
- **Purpose**: Machine-readable metrics for Prometheus scraping
- **Content-Type**: `text/plain`

### `/metrics/summary`
- **Format**: JSON
- **Purpose**: Human-readable metrics summary
- **Content-Type**: `application/json`

## Metrics Categories

### 1. Orchestration Metrics
- `orchestrator_request_duration_seconds` - Request processing time
- `orchestrator_requests_total` - Total number of requests
- `orchestrator_active_requests_count` - Currently active requests
- `orchestrator_component_latency_seconds` - Component-level latency

### 2. Service Communication Metrics
- `orchestrator_service_call_duration_seconds` - External service call latency
- `orchestrator_service_requests_total` - External service request count
- `orchestrator_service_availability` - Service availability status
- `orchestrator_service_retries_total` - Service retry attempts

### 3. Task and Agent Management
- `orchestrator_agent_task_duration_seconds` - Agent task execution time
- `orchestrator_agent_availability_count` - Available agents by type
- `orchestrator_task_queue_size` - Task queue depth
- `orchestrator_task_processing_seconds` - Task processing time

### 4. Workflow Execution
- `orchestrator_workflow_outcomes_total` - Workflow execution results
- `orchestrator_workflow_step_duration_seconds` - Individual step timing

### 5. Error and Reliability
- `orchestrator_errors_total` - Error counts by type and component
- `orchestrator_fallback_usage_total` - Fallback mechanism usage
- `orchestrator_notification_delivery_total` - Notification delivery status

### 6. Resource Utilization
- `orchestrator_memory_usage_bytes` - Memory usage by operation
- `orchestrator_db_connections_count` - Database connection pool status
- `orchestrator_redis_connection_status` - Redis connection health

## Configuration

Metrics collection is automatically enabled when `prometheus_client` is installed:

```bash
pip install prometheus_client==0.19.0
```

If the prometheus client is not available, metrics collection is disabled gracefully with no impact on service functionality.

## Usage in Code

### Decorators

```python
from metrics import monitor_orchestration_performance, monitor_service_call

@monitor_orchestration_performance("success")
async def orchestrate(request):
    # Automatically tracks latency and request counts
    pass

@monitor_service_call("rag_service", "query")
async def call_rag_service():
    # Automatically tracks service call metrics
    pass
```

### Context Managers

```python
from metrics import metrics_collector

# Track concurrent requests
with metrics_collector.concurrent_request_tracker():
    # Process request
    pass

# Track orchestration stage timing
with metrics_collector.time_orchestration_stage("success", "rag_query"):
    # Call RAG service
    pass
```

### Manual Metrics Recording

```python
from metrics import metrics_collector

# Record request
metrics_collector.record_orchestration_request("success", "person_detection")

# Record latency
metrics_collector.record_orchestration_latency(0.5, "success", "total")

# Record service call
metrics_collector.record_service_request("rag_service", "query", 200, 0.3)

# Record error
metrics_collector.record_error("HTTPError", "orchestrator", "error")

# Record fallback usage
metrics_collector.record_fallback_activation("rag_service", "temporary_outage")
```

## Prometheus Configuration

Add the agent orchestrator service to your Prometheus configuration:

```yaml
scrape_configs:
  - job_name: 'agent-orchestrator'
    static_configs:
      - targets: ['agent-orchestrator:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Grafana Dashboard

Key metrics to monitor:

1. **Request Rate**: `rate(orchestrator_requests_total[5m])`
2. **Average Latency**: `avg(orchestrator_request_duration_seconds)`
3. **Error Rate**: `rate(orchestrator_errors_total[5m])`
4. **Service Availability**: `orchestrator_service_availability`
5. **Queue Depth**: `orchestrator_task_queue_size`

## Testing

Run the metrics tests:

```bash
# Unit tests
python -m pytest tests/unit/test_metrics.py -v

# Test metrics endpoints
curl http://localhost:8000/metrics
curl http://localhost:8000/metrics/summary
```

## Integration with Docker

The metrics are automatically available when running in Docker. Ensure port 8000 is exposed for Prometheus scraping:

```yaml
services:
  agent-orchestrator:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PROMETHEUS_METRICS_ENABLED=true
```

## Performance Impact

- Metrics collection has minimal overhead (< 1% CPU)
- Memory usage increases by ~10MB for metric storage
- No blocking operations - all metrics are recorded asynchronously
- Graceful degradation when Prometheus client is unavailable

## Troubleshooting

### Metrics Not Available
- Check if `prometheus_client` is installed
- Verify `/metrics/summary` shows `metrics_enabled: true`
- Check logs for metrics initialization messages

### Missing Metrics
- Ensure decorators are applied to functions
- Verify context managers are used correctly
- Check for any import errors in the metrics module

### High Memory Usage
- Metrics use bounded memory with automatic cleanup
- Consider reducing metric cardinality if needed
- Monitor Prometheus scraping frequency
