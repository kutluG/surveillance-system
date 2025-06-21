# AI Dashboard Service Deployment Guide

This guide provides comprehensive instructions for deploying the AI Dashboard Service in various environments, from development to production.

## Environment Variables

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for AI features | `sk-...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/8` |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_HOST` | Host to bind the service | `0.0.0.0` |
| `SERVICE_PORT` | Port to run the service | `8004` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CORS_ORIGINS` | Allowed CORS origins | `["*"]` |
| `ANOMALY_THRESHOLD` | Anomaly detection threshold | `2.0` |
| `PREDICTION_CACHE_TTL` | Prediction cache TTL (seconds) | `3600` |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |
| `RATE_LIMIT_REQUESTS` | Requests per minute | `100` |
| `WEAVIATE_URL` | Weaviate vector database URL | `http://localhost:8080` |

## Docker Deployment

### Single Container

```bash
# Build the image
docker build -t ai_dashboard_service .

# Run with environment file
docker run -d \
  --name ai_dashboard \
  --env-file .env \
  -p 8004:8004 \
  --restart unless-stopped \
  ai_dashboard_service
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ai_dashboard:
    image: ai_dashboard_service:latest
    build: .
    ports:
      - "8004:8004"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD}@postgres:5432/surveillance
      - REDIS_URL=redis://redis:6379/8
      - SERVICE_HOST=0.0.0.0
      - SERVICE_PORT=8004
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=surveillance
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes

volumes:
  postgres_data:
  redis_data:
```

Create `.env` file:
```env
OPENAI_API_KEY=your-openai-api-key
DB_PASSWORD=secure_password_here
```

Deploy:
```bash
docker-compose up -d
```

## Kubernetes Deployment

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: surveillance-system
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-dashboard-config
  namespace: surveillance-system
data:
  SERVICE_HOST: "0.0.0.0"
  SERVICE_PORT: "8004"
  LOG_LEVEL: "INFO"
  ANOMALY_THRESHOLD: "2.0"
  PREDICTION_CACHE_TTL: "3600"
  RATE_LIMIT_ENABLED: "true"
  RATE_LIMIT_REQUESTS: "100"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ai-dashboard-secrets
  namespace: surveillance-system
type: Opaque
stringData:
  OPENAI_API_KEY: "your-openai-api-key"
  DATABASE_URL: "postgresql+asyncpg://user:password@postgres:5432/surveillance"
  REDIS_URL: "redis://redis:6379/8"
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-dashboard-service
  namespace: surveillance-system
  labels:
    app: ai-dashboard-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-dashboard-service
  template:
    metadata:
      labels:
        app: ai-dashboard-service
    spec:
      containers:
      - name: ai-dashboard
        image: ai_dashboard_service:latest
        ports:
        - containerPort: 8004
        envFrom:
        - configMapRef:
            name: ai-dashboard-config
        - secretRef:
            name: ai-dashboard-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8004
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8004
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
      imagePullSecrets:
      - name: registry-secret
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-dashboard-service
  namespace: surveillance-system
spec:
  selector:
    app: ai-dashboard-service
  ports:
  - name: http
    port: 8004
    targetPort: 8004
  type: ClusterIP
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-dashboard-ingress
  namespace: surveillance-system
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - ai-dashboard.yourdomain.com
    secretName: ai-dashboard-tls
  rules:
  - host: ai-dashboard.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ai-dashboard-service
            port:
              number: 8004
```

Deploy to Kubernetes:
```bash
kubectl apply -f k8s/
```

## Health Checks and Monitoring

### Health Check Endpoints

The service provides health check endpoints:

- `GET /health` - Basic health status
- Response: `{"status": "healthy", "timestamp": "..."}`

### Monitoring Configuration

#### Prometheus Metrics

Add to deployment:
```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8004"
  prometheus.io/path: "/metrics"
```

#### Grafana Dashboard

Import the provided Grafana dashboard configuration from `monitoring/grafana-dashboard.json`.

### Logging

The service uses structured JSON logging. Configure log aggregation:

```yaml
# Fluentd/Fluent Bit configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  fluent-bit.conf: |
    [INPUT]
        Name tail
        Path /var/log/containers/*ai-dashboard*.log
        Parser docker
        Tag ai.dashboard.*
    
    [OUTPUT]
        Name es
        Match ai.dashboard.*
        Host elasticsearch
        Port 9200
        Index ai-dashboard-logs
```

## Production Considerations

### Security

1. **API Security**:
   ```yaml
   # Add authentication middleware
   - name: AUTH_ENABLED
     value: "true"
   - name: JWT_SECRET_KEY
     valueFrom:
       secretKeyRef:
         name: ai-dashboard-secrets
         key: JWT_SECRET_KEY
   ```

2. **Network Security**:
   ```yaml
   # Network policies
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: ai-dashboard-netpol
   spec:
     podSelector:
       matchLabels:
         app: ai-dashboard-service
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: api-gateway
       ports:
       - protocol: TCP
         port: 8004
   ```

### Performance

1. **Resource Limits**:
   ```yaml
   resources:
     requests:
       memory: "512Mi"
       cpu: "500m"
     limits:
       memory: "1Gi"
       cpu: "1000m"
   ```

2. **Horizontal Pod Autoscaling**:
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: ai-dashboard-hpa
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: ai-dashboard-service
     minReplicas: 3
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
   ```

### High Availability

1. **Pod Disruption Budget**:
   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: ai-dashboard-pdb
   spec:
     minAvailable: 2
     selector:
       matchLabels:
         app: ai-dashboard-service
   ```

2. **Anti-Affinity Rules**:
   ```yaml
   affinity:
     podAntiAffinity:
       preferredDuringSchedulingIgnoredDuringExecution:
       - weight: 100
         podAffinityTerm:
           labelSelector:
             matchExpressions:
             - key: app
               operator: In
               values:
               - ai-dashboard-service
           topologyKey: kubernetes.io/hostname
   ```

## Backup and Recovery

### Database Backup

```bash
# Automated PostgreSQL backup
kubectl create cronjob postgres-backup \
  --image=postgres:15-alpine \
  --schedule="0 2 * * *" \
  -- pg_dump -h postgres -U postgres surveillance > backup.sql
```

### Configuration Backup

```bash
# Backup Kubernetes configurations
kubectl get configmap,secret,deployment,service,ingress \
  -n surveillance-system -o yaml > backup-config.yaml
```

## Troubleshooting

### Common Issues

1. **Service Won't Start**:
   ```bash
   # Check logs
   kubectl logs -f deployment/ai-dashboard-service -n surveillance-system
   
   # Check configuration
   kubectl describe pod -l app=ai-dashboard-service -n surveillance-system
   ```

2. **Database Connection Issues**:
   ```bash
   # Test database connectivity
   kubectl exec -it deployment/ai-dashboard-service -n surveillance-system \
     -- python -c "import asyncpg; print('DB connection test')"
   ```

3. **Health Check Failures**:
   ```bash
   # Manual health check
   kubectl port-forward service/ai-dashboard-service 8004:8004 -n surveillance-system
   curl http://localhost:8004/health
   ```

### Performance Issues

1. **High Memory Usage**:
   - Check for memory leaks in analytics processing
   - Adjust cache TTL settings
   - Increase memory limits

2. **Slow Response Times**:
   - Check Redis connectivity
   - Monitor OpenAI API latency
   - Review database query performance

### Monitoring Commands

```bash
# Check resource usage
kubectl top pods -n surveillance-system

# View recent events
kubectl get events --sort-by=.metadata.creationTimestamp -n surveillance-system

# Check service endpoints
kubectl get endpoints -n surveillance-system
```

## Rollback Procedures

### Kubernetes Rollback

```bash
# Check rollout history
kubectl rollout history deployment/ai-dashboard-service -n surveillance-system

# Rollback to previous version
kubectl rollout undo deployment/ai-dashboard-service -n surveillance-system

# Rollback to specific revision
kubectl rollout undo deployment/ai-dashboard-service --to-revision=2 -n surveillance-system
```

### Docker Rollback

```bash
# Tag and push previous version
docker tag ai_dashboard_service:previous ai_dashboard_service:latest
docker-compose down
docker-compose up -d
```

This deployment guide provides comprehensive instructions for various deployment scenarios. Choose the appropriate method based on your infrastructure requirements and operational constraints.
