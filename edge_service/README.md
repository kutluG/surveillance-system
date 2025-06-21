# Edge AI Service

This service captures frames from a camera, runs AI inference with privacy-compliant face anonymization, and publishes JSON events to an MQTT broker for downstream processing.

## Features

🤖 **AI-Powered Detection**
- Real-time object detection and activity recognition
- TensorRT-optimized inference for edge devices
- Support for multiple model formats (TensorRT, ONNX, TensorFlow Lite)

🔒 **Privacy-First Design**
- On-device face detection and anonymization
- Multiple anonymization methods (blur, pixelate, black box, emoji)
- GDPR-compliant privacy levels
- No raw face data ever leaves the device

📡 **Event Publishing**
- MQTT-based event streaming
- Kafka integration via message bridge
- Structured JSON event schemas
- Real-time health and metrics reporting

⚙️ **Production Ready**
- Prometheus metrics integration
- Comprehensive health checks
- Over-the-air model updates
- Docker containerization

## Quick Start

### 1. Environment Setup

```bash
# Copy configuration template
cp .env.example .env

# Configure your environment
CAMERA_ID=camera-01
CAPTURE_DEVICE=0
MODEL_DIR=/models
TARGET_RESOLUTION=416,416

# Privacy configuration
ANONYMIZATION_ENABLED=true
PRIVACY_LEVEL=strict
ANONYMIZATION_METHOD=blur

# MQTT configuration
MQTT_BROKER=mqtt.surveillance.local
MQTT_PORT=8883
MQTT_TLS_CA=/certs/ca.crt
MQTT_TLS_CERT=/certs/client.crt
MQTT_TLS_KEY=/certs/client.key
```

### 2. Docker Deployment

```bash
# Build and run the service
docker-compose up --build edge_service

# Or run specific configuration
docker-compose -f docker-compose.yml up edge_service
```

### 3. Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Download face detection models
python setup_face_models.py

# Run the service
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/capture` | POST | Schedule frame capture and processing |
| `/health` | GET | Comprehensive health check |
| `/metrics` | GET | Prometheus metrics export |

### Privacy & Anonymization

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/privacy/status` | GET | Get anonymization status and statistics |
| `/api/v1/privacy/configure` | POST | Update privacy settings at runtime |
| `/api/v1/privacy/test` | POST | Test anonymization with current frame |

### Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/models/info` | GET | Get loaded model information |
| `/api/v1/ota` | POST | Over-the-air model updates |
| `/api/v1/openapi.json` | GET | Export OpenAPI specification |

### Example Usage

```bash
# Trigger frame capture
curl -X POST "http://localhost:8001/api/v1/capture"

# Check service health
curl -X GET "http://localhost:8001/health"

# Get privacy status
curl -X GET "http://localhost:8001/api/v1/privacy/status"

# Update privacy settings
curl -X POST "http://localhost:8001/api/v1/privacy/configure" \
  -H "Content-Type: application/json" \
  -d '{"privacy_level": "strict", "method": "blur", "enabled": true}'

# Test anonymization
curl -X POST "http://localhost:8001/api/v1/privacy/test"

# Export OpenAPI specification
curl -X GET "http://localhost:8001/api/v1/openapi.json" > edge_service_api.json
```

## Documentation

### 📋 API Documentation
- **[OpenAPI Specification](docs/edge_service_openapi.json)** - Complete API reference
- **Interactive API Docs**: `http://localhost:8001/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8001/redoc` (ReDoc)

### 🔗 Integration Guide
- **[Integration Guide](docs/EDGE_SERVICE_INTEGRATION.md)** - MQTT/Kafka integration patterns
- Message schemas and topic structure
- Downstream subscriber examples (Python, Node.js)
- Error handling and resilience patterns

### 🤖 Model Documentation
- **[Model Specifications](docs/EDGE_SERVICE_MODELS.md)** - Detailed AI model documentation
- Face detection models (Haar Cascade, OpenCV DNN)
- Object detection and activity recognition
- Performance metrics and optimization guides

### 🔒 Privacy Documentation
- **[Face Anonymization Guide](docs/FACE_ANONYMIZATION.md)** - Privacy compliance features
- Anonymization methods and configurations
- GDPR compliance and audit trails
- Privacy-first architecture design

## Configuration

### Privacy Settings

```bash
# Enable face anonymization (strongly recommended)
ANONYMIZATION_ENABLED=true

# Privacy protection levels
PRIVACY_LEVEL=strict    # strict | moderate | minimal

# Anonymization methods
ANONYMIZATION_METHOD=blur    # blur | pixelate | black_box | emoji

# Model configuration
FACE_HASH_ENABLED=true
COMPLIANCE_MODE=gdpr
```

### Performance Tuning

```bash
# Camera configuration
CAPTURE_DEVICE=0
TARGET_RESOLUTION=416,416    # Balance speed vs accuracy

# Processing optimization
BATCH_SIZE=1
INFERENCE_THREADS=2
MEMORY_POOL_SIZE=512MB

# Quality settings
DETECTION_CONFIDENCE=0.7
NMS_THRESHOLD=0.4
```

## Testing

### Unit Tests
```bash
# Run all tests
pytest -v

# Test face anonymization
pytest tests/test_face_anonymization.py -v

# Test API endpoints
pytest tests/test_api.py -v

# Integration tests
pytest tests/test_integration.py -v
```

### Load Testing
```bash
# Install load testing tools
pip install locust

# Run load tests
locust -f tests/load_test.py --host=http://localhost:8001
```

### Privacy Compliance Tests
```bash
# Test anonymization effectiveness
python tests/test_privacy_compliance.py

# GDPR compliance validation
python tests/test_gdpr_compliance.py
```

## Monitoring

### Prometheus Metrics

Access metrics at `http://localhost:8001/metrics`

Key metrics include:
- `frames_processed_total` - Total frames processed
- `faces_anonymized_total` - Total faces anonymized
- `anonymization_processing_time_seconds` - Processing time histogram
- `gdpr_compliance_score` - Privacy compliance score (0-100)

### Health Monitoring

```bash
# Basic health check
curl http://localhost:8001/health

# Detailed status with anonymization info
curl http://localhost:8001/api/v1/privacy/status

# Export all metrics
curl http://localhost:8001/metrics
```

### Grafana Dashboard

Import the pre-configured dashboard:
```bash
# Dashboard configuration
monitoring/grafana/dashboards/edge-service-dashboard.json
```

## Troubleshooting

### Common Issues

1. **Camera not accessible**
   ```bash
   # Check device permissions
   ls -la /dev/video*
   
   # Test camera directly
   v4l2-ctl --list-devices
   ```

2. **Face detection models not found**
   ```bash
   # Download models
   python setup_face_models.py
   
   # Verify model files
   ls -la /models/
   ```

3. **MQTT connection issues**
   ```bash
   # Test MQTT connectivity
   mosquitto_pub -h mqtt.broker.com -p 8883 -t test/topic -m "test"
   
   # Check TLS certificates
   openssl x509 -in /certs/client.crt -text -noout
   ```

4. **Privacy compliance failures**
   ```bash
   # Check anonymization status
   curl http://localhost:8001/api/v1/privacy/status
   
   # Test anonymization
   curl -X POST http://localhost:8001/api/v1/privacy/test
   ```

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
export LOG_FORMAT=json
python main.py
```

### Performance Issues

```bash
# Monitor resource usage
htop
nvidia-smi  # For GPU-enabled devices

# Profile inference performance
python -m cProfile -o profile.prof main.py
```

## Requirements

### System Requirements
- **Python**: 3.9+
- **Memory**: 2GB+ RAM
- **Storage**: 1GB+ free space for models
- **Camera**: USB/CSI camera or IP camera
- **Network**: MQTT broker access

### Hardware Recommendations

**Minimum Configuration:**
- Raspberry Pi 4B (4GB RAM)
- USB Camera
- 32GB SD Card

**Recommended Configuration:**
- NVIDIA Jetson Nano/Xavier NX
- CSI Camera
- 64GB+ Storage
- Ethernet connection

**Production Configuration:**
- NVIDIA Jetson AGX Xavier
- Industrial camera
- SSD storage
- Redundant networking

### Docker & Dependencies

```bash
# Base requirements
docker >= 20.10
docker-compose >= 1.29

# Optional for development
nvidia-docker2  # For GPU acceleration
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Ensure privacy compliance
5. Submit a pull request

### Development Guidelines

- All face data must remain on-device
- Include comprehensive tests
- Update documentation
- Follow privacy-first principles
- Maintain backward compatibility

## License

MIT License - see [LICENSE](../LICENSE) file for details.

## Support

- **Documentation**: Available in `docs/` directory
- **Issues**: GitHub issue tracker
- **Security**: Report security issues privately
- **Privacy**: GDPR compliance questions welcome