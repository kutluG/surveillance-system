# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the AI-Powered Surveillance System.

## 🔍 General Troubleshooting Steps

### 1. Check System Status
```bash
# Check all services
docker-compose ps

# Check service health
curl http://localhost:8000/health

# View system logs
docker-compose logs --tail=100
```

### 2. Verify Configuration
```bash
# Validate environment variables
python scripts/validate_config.py

# Check configuration files
python scripts/check_config.py

# Test database connection
python scripts/test_connections.py
```

### 3. Monitor Resources
```bash
# Check system resources
docker stats

# Check disk usage
df -h

# Check memory usage
free -h
```

## 🚨 Common Issues and Solutions

### Service Startup Issues

#### Issue: Services Won't Start
**Symptoms:**
- Containers exit immediately
- "Port already in use" errors
- Connection refused errors

**Solutions:**
```bash
# Check port conflicts
netstat -tulnp | grep :8000

# Stop conflicting services
sudo systemctl stop apache2
sudo systemctl stop nginx

# Reset Docker environment
docker-compose down -v
docker system prune -a
docker-compose up -d

# Check logs for specific errors
docker-compose logs [service-name]
```

#### Issue: Database Connection Failed
**Symptoms:**
- "Connection refused" to PostgreSQL
- Authentication failures
- Database doesn't exist errors

**Solutions:**
```bash
# Check PostgreSQL container
docker-compose logs postgres

# Verify database exists
docker-compose exec postgres psql -U surveillance_user -l

# Create database if missing
docker-compose exec postgres createdb -U surveillance_user surveillance

# Run migrations
docker-compose exec api-gateway python scripts/migrate.py

# Reset database (WARNING: loses data)
docker-compose down
docker volume rm surveillance_db
docker-compose up -d postgres
```

#### Issue: Redis Connection Failed
**Symptoms:**
- Redis connection timeout
- Cache-related errors
- Session issues

**Solutions:**
```bash
# Check Redis container
docker-compose logs redis

# Test Redis connection
docker-compose exec redis redis-cli ping

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL

# Restart Redis
docker-compose restart redis
```

### Video Processing Issues

#### Issue: Video Upload Fails
**Symptoms:**
- Upload timeouts
- "File format not supported"
- Storage space errors

**Solutions:**
```bash
# Check available disk space
df -h

# Verify file permissions
ls -la data/videos/
sudo chown -R 1000:1000 data/

# Check supported formats
grep SUPPORTED_FORMATS .env

# Test with smaller file
curl -X POST "http://localhost:8000/api/v1/videos/upload" \
  -F "file=@small_test.mp4"

# Check upload limits
grep MAX_VIDEO_SIZE .env
```

#### Issue: Video Processing Stuck
**Symptoms:**
- Videos stuck in "processing" state
- No thumbnails generated
- Processing queue backed up

**Solutions:**
```bash
# Check processing workers
docker-compose logs ai-service

# Restart processing service
docker-compose restart ai-service

# Clear processing queue
curl -X POST "http://localhost:8000/api/v1/admin/clear-queue"

# Check GPU availability (if using GPU)
docker-compose exec ai-service nvidia-smi

# Increase processing timeout
# Edit .env: VIDEO_PROCESSING_TIMEOUT=600
```

### AI/ML Issues

#### Issue: Object Detection Not Working
**Symptoms:**
- No objects detected in videos
- AI processing errors
- Model loading failures

**Solutions:**
```bash
# Check model files
ls -la models/
docker-compose exec ai-service python -c "import torch; print(torch.__version__)"

# Download missing models
docker-compose exec ai-service python scripts/download_models.py

# Test model inference
docker-compose exec ai-service python scripts/test_inference.py

# Check GPU usage
docker-compose exec ai-service nvidia-smi

# Verify model configuration
grep -A5 "object_detection" config/models.yml
```

#### Issue: Face Recognition Failing
**Symptoms:**
- Faces not detected
- Recognition accuracy low
- Face encoding errors

**Solutions:**
```bash
# Check face recognition model
docker-compose exec ai-service python scripts/test_face_recognition.py

# Verify face detection threshold
grep FACE_RECOGNITION_THRESHOLD .env

# Check face database
docker-compose exec postgres psql -U surveillance_user -d surveillance \
  -c "SELECT COUNT(*) FROM face_encodings;"

# Clear face cache
curl -X POST "http://localhost:8000/api/v1/admin/clear-face-cache"

# Retrain face recognition
docker-compose exec ai-service python scripts/retrain_faces.py
```

### Performance Issues

#### Issue: Slow Video Loading
**Symptoms:**
- Videos take long to load
- Streaming interruptions
- Thumbnail generation slow

**Solutions:**
```bash
# Check video compression settings
grep VIDEO_COMPRESSION .env

# Optimize video storage
docker-compose exec vms-service python scripts/optimize_videos.py

# Check network bandwidth
speedtest-cli

# Increase buffer size
# Edit .env: STREAM_BUFFER_SIZE=2097152

# Enable CDN/caching
# Configure nginx reverse proxy
```

#### Issue: High CPU/Memory Usage
**Symptoms:**
- System slow/unresponsive
- Out of memory errors
- CPU at 100%

**Solutions:**
```bash
# Check resource usage
docker stats

# Limit resource usage
# Edit docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       memory: 1G
#       cpus: '2'

# Optimize batch processing
# Edit .env: INFERENCE_BATCH_SIZE=2

# Scale down AI workers
# Edit .env: AI_PROCESSING_WORKERS=1

# Enable GPU acceleration
# Edit .env: USE_GPU=true
```

### Network and Connectivity Issues

#### Issue: Cannot Access Web Interface
**Symptoms:**
- Browser shows "connection refused"
- Timeouts when accessing UI
- 502 Bad Gateway errors

**Solutions:**
```bash
# Check service ports
docker-compose ps

# Test direct service access
curl http://localhost:8000/health
curl http://localhost:8080

# Check firewall rules
sudo ufw status

# Verify Docker networking
docker network ls
docker network inspect surveillance-system_default

# Check reverse proxy configuration
nginx -t  # if using nginx
```

#### Issue: IP Camera Connection Failed
**Symptoms:**
- Camera stream unavailable
- RTSP connection errors
- Authentication failures

**Solutions:**
```bash
# Test camera connection
ffmpeg -i "rtsp://admin:password@192.168.1.100:554/stream1" -t 5 test.mp4

# Check camera configuration
grep -A10 "cameras:" config/cameras.yml

# Verify network connectivity
ping 192.168.1.100
telnet 192.168.1.100 554

# Update camera credentials
# Edit config/cameras.yml

# Restart camera service
docker-compose restart camera-service
```

### Authentication and Security Issues

#### Issue: Login Failures
**Symptoms:**
- Cannot log in with correct credentials
- JWT token errors
- Session expires immediately

**Solutions:**
```bash
# Check user database
docker-compose exec postgres psql -U surveillance_user -d surveillance \
  -c "SELECT username, is_active FROM users;"

# Reset admin password
docker-compose exec api-gateway python scripts/reset_admin_password.py

# Verify JWT configuration
grep JWT_SECRET_KEY .env

# Clear session cache
docker-compose exec redis redis-cli FLUSHALL

# Check authentication logs
docker-compose logs api-gateway | grep -i auth
```

#### Issue: API Authentication Errors
**Symptoms:**
- "Invalid API key" errors
- Authorization failures
- 401/403 HTTP errors

**Solutions:**
```bash
# Check API key configuration
grep API_KEY .env

# Generate new API key
python scripts/generate_api_key.py

# Test API authentication
curl -H "Authorization: Bearer $API_TOKEN" \
  http://localhost:8000/api/v1/videos

# Verify user permissions
docker-compose exec postgres psql -U surveillance_user -d surveillance \
  -c "SELECT username, role FROM users WHERE username='testuser';"
```

## 📊 Monitoring and Diagnostics

### Health Check Endpoints
```bash
# Overall system health
curl http://localhost:8000/health

# Individual service health
curl http://localhost:8001/health  # VMS Service
curl http://localhost:8002/health  # Annotation Service
curl http://localhost:8003/health  # AI Dashboard
```

### Log Analysis
```bash
# Search for errors
docker-compose logs | grep -i error

# Filter by service
docker-compose logs api-gateway | grep -i error

# Follow logs in real-time
docker-compose logs -f --tail=50

# Export logs for analysis
docker-compose logs > system_logs.txt
```

### Performance Metrics
```bash
# Prometheus metrics
curl http://localhost:9090/metrics

# Custom metrics endpoint
curl http://localhost:8000/metrics

# Database performance
docker-compose exec postgres psql -U surveillance_user -d surveillance \
  -c "SELECT * FROM pg_stat_activity;"
```

## 🔧 Advanced Troubleshooting

### Database Debugging
```sql
-- Check database connections
SELECT count(*) FROM pg_stat_activity;

-- Find slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Check table sizes
SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Container Debugging
```bash
# Enter container for debugging
docker-compose exec api-gateway bash

# Check container resources
docker stats --no-stream

# Inspect container configuration
docker inspect surveillance-system_api-gateway_1

# Debug network issues
docker network inspect surveillance-system_default

# Check volume mounts
docker volume inspect surveillance_data
```

### System Resource Debugging
```bash
# Check disk I/O
iostat -x 1

# Monitor memory usage
watch -n 1 free -h

# Check network usage
iftop

# Monitor GPU usage (if available)
watch -n 1 nvidia-smi
```

## 🚑 Emergency Procedures

### System Recovery
```bash
# Emergency shutdown
docker-compose down

# Backup critical data
cp -r data/ backup/$(date +%Y%m%d_%H%M%S)/

# Complete system reset (WARNING: Data loss)
docker-compose down -v
docker system prune -a
docker volume prune
rm -rf data/
```

### Data Recovery
```bash
# Restore from backup
cp -r backup/latest/ data/

# Restore database
docker-compose exec postgres pg_restore -U surveillance_user -d surveillance backup.sql

# Rebuild search indices
docker-compose exec api-gateway python scripts/rebuild_indices.py
```

## 📞 Getting Help

### Log Collection for Support
```bash
# Collect system information
./scripts/collect_debug_info.sh

# Generate support bundle
python scripts/generate_support_bundle.py
```

### Before Contacting Support
1. **Check this troubleshooting guide**
2. **Collect logs** from the last 24 hours
3. **Document steps to reproduce** the issue
4. **Note system specifications** and environment
5. **Include configuration files** (without secrets)

### Support Channels
- **GitHub Issues**: For bugs and feature requests
- **Documentation**: Check [docs/](index.md) for guides
- **Community Forum**: Ask questions and share solutions
- **Commercial Support**: For enterprise customers

---

**Related**: [Installation Guide](installation.md) | [Configuration Guide](configuration.md) | [Monitoring Guide](monitoring.md)
