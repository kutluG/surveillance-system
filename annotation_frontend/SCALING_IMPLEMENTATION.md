# Stateless Annotation Service - Scaling Implementation

This document describes the implementation of horizontal scaling for the Annotation Frontend Service, making it fully stateless and capable of running multiple instances behind a load balancer.

## Overview

The annotation service has been refactored to:
- Remove all in-memory global state
- Use Kafka consumer groups for proper load balancing
- Externalize state to Redis and PostgreSQL
- Provide health and readiness endpoints for orchestration
- Support horizontal scaling with Docker Compose

## Key Changes

### 1. Stateless Architecture

**Before**: The service maintained global in-memory state including:
- WebSocket connection counts
- Example queues
- Processing state

**After**: All state is externalized to:
- **Redis**: WebSocket connection tracking, retry queues, pub/sub notifications
- **PostgreSQL**: Persistent annotation data, examples, user sessions
- **Kafka**: Message streaming and consumer group coordination

### 2. Kafka Consumer Groups

The service now uses proper Kafka consumer group configuration:

```python
consumer = AIOKafkaConsumer(
    settings.HARD_EXAMPLES_TOPIC,
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    group_id=settings.KAFKA_GROUP_ID,  # "annotation-frontend-group"
    client_id=f'{settings.SERVICE_NAME}-consumer-{id(self)}',  # Unique per instance
    auto_offset_reset='latest',
    enable_auto_commit=True,
)
```

**Key Configuration:**
- `group_id`: All instances share the same group ID for load balancing
- `client_id`: Each instance has a unique client ID for identification
- Kafka automatically distributes partitions among group members

### 3. Health & Readiness Endpoints

#### `/healthz` - Liveness Probe
- Always returns 200 if the application is running
- Used by load balancers to check if the service is alive
- Does not check external dependencies

#### `/readyz` - Readiness Probe  
- Returns 200 only when the service is ready to serve traffic
- Checks Redis connectivity
- Verifies Kafka consumer partition assignment
- Returns 503 if any dependency is unhealthy

### 4. Redis State Management

New Redis operations for stateless coordination:

```python
# WebSocket connection tracking across instances
await redis_service.increment_websocket_count()
await redis_service.get_websocket_count()

# Cross-instance notifications
await redis_service.publish_new_example_notification(example_data)

# Health checks
is_connected = await redis_service.check_connectivity()
```

## Configuration

### Environment Variables

```env
# Kafka Consumer Group Configuration
KAFKA_GROUP_ID=annotation-frontend-group
SERVICE_NAME=annotation-frontend
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Redis Configuration for Shared State
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=
REDIS_DB=0

# Service Configuration
HOST=0.0.0.0
PORT=8000
```

## Deployment

### Docker Compose Scaling

Use the provided `docker-compose-scaling.yml`:

```bash
# Scale to 3 instances
docker-compose -f docker-compose-scaling.yml up --scale annotation_frontend=3 -d

# Scale to 5 instances
docker-compose -f docker-compose-scaling.yml up --scale annotation_frontend=5 -d

# View running instances
docker-compose -f docker-compose-scaling.yml ps

# Monitor logs from all instances
docker-compose -f docker-compose-scaling.yml logs -f annotation_frontend
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annotation-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: annotation-frontend
  template:
    metadata:
      labels:
        app: annotation-frontend
    spec:
      containers:
      - name: annotation-frontend
        image: myorg/annotation_frontend:latest
        ports:
        - containerPort: 8000
        env:
        - name: KAFKA_GROUP_ID
          value: "annotation-frontend-group"
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

## Load Balancing

### Nginx Configuration

```nginx
upstream annotation_backend {
    server annotation_frontend_1:8000;
    server annotation_frontend_2:8000;
    server annotation_frontend_3:8000;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://annotation_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /healthz {
        proxy_pass http://annotation_backend;
        access_log off;
    }
}
```

## Monitoring

### Health Check Endpoints

```bash
# Check if service is alive
curl -f http://localhost:8000/healthz

# Check if service is ready
curl -f http://localhost:8000/readyz
```

### Kafka Consumer Monitoring

Check consumer group status:

```bash
# View consumer group details
kafka-consumer-groups.sh \
  --bootstrap-server kafka:9092 \
  --describe \
  --group annotation-frontend-group

# Monitor partition assignment
kubectl exec -it kafka-pod -- kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --group annotation-frontend-group
```

### Redis Monitoring

```bash
# Check WebSocket connections across all instances
redis-cli GET websocket:connection_count

# Monitor pub/sub activity
redis-cli MONITOR
```

## Testing

Run the scalability tests:

```bash
# Run all scalability tests
pytest tests/test_scalability.py -v

# Test specific scenarios
pytest tests/test_scalability.py::TestScalability::test_kafka_consumer_group_coordination -v
pytest tests/test_scalability.py::TestScalability::test_readiness_endpoint_with_healthy_dependencies -v
```

## Troubleshooting

### Consumer Group Issues

**Problem**: Consumers not receiving messages
```bash
# Check consumer group lag
kafka-consumer-groups.sh --bootstrap-server kafka:9092 --describe --group annotation-frontend-group

# Reset consumer group offsets
kafka-consumer-groups.sh --bootstrap-server kafka:9092 --group annotation-frontend-group --reset-offsets --to-latest --all-topics --execute
```

**Problem**: Readiness probe failing
```bash
# Check Redis connectivity
redis-cli ping

# Check Kafka consumer assignment
curl -s http://localhost:8000/readyz | jq '.checks.kafka_consumer'
```

### Performance Tuning

1. **Kafka Consumer Configuration**:
   - Adjust `max_poll_records` for batch processing
   - Tune `session_timeout_ms` for faster rebalancing
   - Configure `heartbeat_interval_ms` for health monitoring

2. **Redis Configuration**:
   - Set appropriate `maxmemory` and `maxmemory-policy`
   - Enable persistence if state durability is required
   - Configure connection pooling

3. **Application Scaling**:
   - Monitor CPU and memory usage per instance
   - Scale based on Kafka consumer lag
   - Consider partition count when determining max replicas

## Security Considerations

- Redis should be configured with authentication in production
- Use TLS for Kafka connections
- Implement proper network segmentation
- Secure health check endpoints if they expose sensitive information

## Migration Guide

To migrate from the previous stateful version:

1. **Deploy Redis** and configure connection settings
2. **Update configuration** with new environment variables
3. **Deploy new version** with rolling update strategy
4. **Verify consumer group** assignment and partition distribution
5. **Test health endpoints** and monitoring setup
6. **Scale horizontally** and verify load distribution

This implementation ensures the annotation service can scale horizontally while maintaining consistency and reliability across multiple instances.
