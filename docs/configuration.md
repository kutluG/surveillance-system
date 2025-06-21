# Configuration Guide

This guide covers the configuration options for the AI-Powered Surveillance System.

## 🎛️ Configuration Overview

The system uses a layered configuration approach:
1. **Environment variables** (`.env` file)
2. **Configuration files** (YAML/JSON)
3. **Database settings** (runtime configuration)
4. **Service-specific configs** (per-service settings)

## 📄 Environment Configuration

### Main Environment File (`.env`)

```bash
# ======================
# CORE SYSTEM SETTINGS
# ======================

# Application
APP_NAME=AI-Powered Surveillance System
APP_VERSION=1.0.0
APP_ENV=production  # development, staging, production
DEBUG=false
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# ======================
# DATABASE CONFIGURATION
# ======================

# PostgreSQL (Primary Database)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=surveillance
POSTGRES_USER=surveillance_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_MAX_CONNECTIONS=100

# Redis (Caching & Session Storage)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0
REDIS_MAX_CONNECTIONS=50

# ======================
# SECURITY SETTINGS
# ======================

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# API Security
API_KEY=your-api-key-change-this
API_RATE_LIMIT=1000  # requests per hour
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Encryption
ENCRYPTION_KEY=your-32-byte-encryption-key-here
PASSWORD_SALT_ROUNDS=12

# ======================
# VIDEO MANAGEMENT
# ======================

# Storage Configuration
VIDEO_STORAGE_PATH=/app/data/videos
THUMBNAIL_STORAGE_PATH=/app/data/thumbnails
MAX_VIDEO_SIZE_MB=500
SUPPORTED_FORMATS=mp4,avi,mov,mkv,webm

# Processing
VIDEO_PROCESSING_WORKERS=4
THUMBNAIL_GENERATION=true
VIDEO_COMPRESSION=true
VIDEO_COMPRESSION_QUALITY=23  # CRF value (lower = better quality)

# ======================
# AI/ML CONFIGURATION
# ======================

# Model Settings
MODEL_CACHE_DIR=/app/models
AI_PROCESSING_WORKERS=2
INFERENCE_BATCH_SIZE=4
MODEL_UPDATE_INTERVAL=24  # hours

# GPU Configuration
CUDA_VISIBLE_DEVICES=0  # GPU device IDs, comma-separated
USE_GPU=true
GPU_MEMORY_FRACTION=0.8

# Object Detection
DETECTION_CONFIDENCE_THRESHOLD=0.5
DETECTION_NMS_THRESHOLD=0.4
DETECTION_MAX_OBJECTS=100

# Face Recognition
FACE_RECOGNITION_THRESHOLD=0.6
FACE_ENCODING_MODEL=large  # small, large
UNKNOWN_FACE_RETENTION_DAYS=30

# ======================
# MONITORING & LOGGING
# ======================

# Metrics
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
METRICS_RETENTION_DAYS=30

# Logging
LOG_ROTATION_SIZE=100MB
LOG_RETENTION_DAYS=30
LOG_FORMAT=json  # json, text

# Health Checks
HEALTH_CHECK_INTERVAL=30  # seconds
SERVICE_TIMEOUT=60  # seconds

# ======================
# NOTIFICATION SETTINGS
# ======================

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_TLS=true

# Webhook Notifications
WEBHOOK_URL=https://your-webhook-url.com/alerts
WEBHOOK_SECRET=your-webhook-secret

# Push Notifications
PUSH_NOTIFICATION_ENABLED=true
FCM_SERVER_KEY=your-fcm-server-key

# ======================
# EXTERNAL INTEGRATIONS
# ======================

# Cloud Storage (Optional)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=surveillance-videos

# External APIs
WEATHER_API_KEY=your-weather-api-key
GEOCODING_API_KEY=your-geocoding-api-key

# ======================
# DEVELOPMENT SETTINGS
# ======================

# Development only
ALLOW_ORIGINS=*
ENABLE_SWAGGER=true
ENABLE_REDOC=true
MOCK_AI_PROCESSING=false
```

### Service-Specific Environment Files

#### VMS Service (`.env.vms`)
```bash
VMS_PORT=8001
MAX_CONCURRENT_STREAMS=10
STREAM_BUFFER_SIZE=1048576
RTSP_TIMEOUT=30
HLS_SEGMENT_DURATION=6
```

#### AI Service (`.env.ai`)
```bash
AI_SERVICE_PORT=8004
MODEL_WARMUP=true
BATCH_PROCESSING=true
RESULT_CACHE_TTL=3600
```

## 📋 Configuration Files

### Main Configuration (`config/app.yml`)
```yaml
app:
  name: "AI-Powered Surveillance System"
  version: "1.0.0"
  debug: false

database:
  migrations:
    auto_run: true
    backup_before: true
  
  connection_pool:
    min_size: 5
    max_size: 20
    idle_timeout: 300

security:
  password_policy:
    min_length: 8
    require_uppercase: true
    require_lowercase: true
    require_numbers: true
    require_symbols: true
  
  session:
    timeout: 1800  # 30 minutes
    remember_me_days: 30

video:
  processing:
    parallel_jobs: 4
    timeout: 300
    retry_attempts: 3
  
  quality:
    default_resolution: "1920x1080"
    compression: "h264"
    bitrate: "2M"

ai:
  models:
    object_detection: "yolov8n"
    face_recognition: "facenet"
    person_tracking: "deepsort"
  
  processing:
    queue_size: 100
    worker_timeout: 60
    result_ttl: 3600
```

### Camera Configuration (`config/cameras.yml`)
```yaml
cameras:
  - id: "cam_001"
    name: "Front Entrance"
    type: "ip_camera"
    url: "rtsp://admin:password@192.168.1.100:554/stream1"
    location: "entrance"
    active: true
    settings:
      resolution: "1920x1080"
      fps: 30
      night_vision: true
  
  - id: "cam_002"
    name: "Parking Lot"
    type: "ip_camera"
    url: "rtsp://admin:password@192.168.1.101:554/stream1"
    location: "parking"
    active: true
    settings:
      resolution: "1280x720"
      fps: 15
      motion_detection: true
```

### Alert Rules (`config/alerts.yml`)
```yaml
alert_rules:
  - name: "Person Detection"
    type: "object_detection"
    conditions:
      object_type: "person"
      confidence: 0.7
      duration: 5  # seconds
    actions:
      - type: "email"
        recipients: ["admin@example.com"]
      - type: "webhook"
        url: "https://your-webhook.com/alerts"
  
  - name: "Unauthorized Access"
    type: "face_recognition"
    conditions:
      unknown_face: true
      location: "restricted_area"
    actions:
      - type: "push_notification"
        priority: "high"
      - type: "record_video"
        duration: 30
```

## 🔧 Runtime Configuration

### Database Configuration

```sql
-- System settings table
INSERT INTO system_settings (key, value) VALUES
('max_retention_days', '90'),
('auto_cleanup_enabled', 'true'),
('face_recognition_enabled', 'true'),
('object_detection_enabled', 'true'),
('motion_detection_sensitivity', '0.5');
```

### User Roles and Permissions
```sql
-- Default roles
INSERT INTO roles (name, permissions) VALUES
('admin', '["all"]'),
('operator', '["view_videos", "manage_annotations", "view_alerts"]'),
('viewer', '["view_videos", "view_alerts"]');
```

## 🎯 Performance Tuning

### Database Optimization
```bash
# PostgreSQL configuration (postgresql.conf)
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

### Redis Configuration
```bash
# Redis configuration (redis.conf)
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### AI Model Configuration
```yaml
# Model configuration (config/models.yml)
models:
  object_detection:
    batch_size: 4
    input_size: [640, 640]
    confidence_threshold: 0.5
    nms_threshold: 0.4
  
  face_recognition:
    batch_size: 2
    input_size: [160, 160]
    threshold: 0.6
    max_faces_per_image: 10
```

## 🔐 Security Configuration

### SSL/TLS Setup
```yaml
# SSL configuration (config/ssl.yml)
ssl:
  enabled: true
  cert_file: "/app/certs/server.crt"
  key_file: "/app/certs/server.key"
  protocols: ["TLSv1.2", "TLSv1.3"]
  ciphers: "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
```

### Firewall Rules
```bash
# UFW firewall rules
sudo ufw allow 8000/tcp  # API Gateway
sudo ufw allow 8080/tcp  # Web Interface
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 5432/tcp   # PostgreSQL (internal only)
sudo ufw deny 6379/tcp   # Redis (internal only)
```

## 📊 Monitoring Configuration

### Prometheus Configuration (`monitoring/prometheus/prometheus.yml`)
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'surveillance-system'
    static_configs:
      - targets: ['api-gateway:8000', 'vms-service:8001']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### Grafana Configuration
```yaml
# Grafana provisioning (monitoring/grafana/dashboards.yml)
apiVersion: 1

providers:
  - name: 'default'
    folder: 'Surveillance System'
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

## 🚀 Production Deployment

### Docker Compose Override
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  api-gateway:
    environment:
      - APP_ENV=production
      - DEBUG=false
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

### Load Balancer Configuration
```nginx
# nginx.conf
upstream surveillance_api {
    server api-gateway-1:8000;
    server api-gateway-2:8000;
    server api-gateway-3:8000;
}

server {
    listen 80;
    server_name surveillance.example.com;
    
    location / {
        proxy_pass http://surveillance_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🔄 Configuration Management

### Environment-Specific Configs
```bash
# Development
cp .env.development .env

# Staging
cp .env.staging .env

# Production
cp .env.production .env
```

### Configuration Validation
```bash
# Validate configuration
python scripts/validate_config.py

# Test database connection
python scripts/test_db_connection.py

# Verify AI models
python scripts/verify_models.py
```

## 📝 Configuration Best Practices

1. **Never commit secrets** - Use `.env.example` for templates
2. **Use strong passwords** - Generate random, complex passwords
3. **Rotate keys regularly** - Implement key rotation schedules
4. **Monitor configuration drift** - Track changes and validate
5. **Document all changes** - Maintain configuration change logs
6. **Test configurations** - Validate in staging before production
7. **Backup configurations** - Keep secure backups of config files

## 🆘 Troubleshooting Configuration

### Common Configuration Issues

#### Database Connection
```bash
# Test database connection
docker-compose exec postgres psql -U surveillance_user -d surveillance -c "SELECT 1;"
```

#### Redis Connection
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping
```

#### AI Model Loading
```bash
# Check model files
ls -la models/
docker-compose logs ai-service | grep -i model
```

#### Permission Issues
```bash
# Fix file permissions
sudo chown -R 1000:1000 data/
sudo chmod -R 755 data/
```

---

**Next**: [Architecture Overview](architecture.md) | [Quick Start](quickstart.md)
