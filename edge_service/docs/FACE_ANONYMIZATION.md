# Face Anonymization & Privacy Compliance

## Overview

The Edge Service now includes **mandatory on-device face anonymization** to ensure privacy compliance and meet regulatory requirements. All faces are detected and anonymized **before any data leaves the device**.

## 🔒 Privacy-First Design

### Core Principles
- **On-Device Processing**: All face detection and anonymization happens locally
- **No Raw Face Data**: Raw face images never leave the device
- **Configurable Privacy Levels**: Choose from strict, moderate, or minimal privacy protection
- **Hash-Only Embeddings**: Optional face identification using privacy-preserving hashes
- **Fail-Safe Operation**: In strict mode, frames are dropped if anonymization fails

## 🛠️ Configuration

### Environment Variables

```bash
# Enable/disable face anonymization (strongly recommended: true)
ANONYMIZATION_ENABLED=true

# Privacy protection level
PRIVACY_LEVEL=strict  # Options: strict, moderate, minimal

# Anonymization method
ANONYMIZATION_METHOD=blur  # Options: blur, pixelate, black_box, emoji
```

### Privacy Levels

#### 🔐 Strict (Recommended for Production)
- **Method**: Black boxes over faces
- **Face Data**: No face data stored or transmitted
- **Hashes**: Basic geometric hashes only
- **Fail-Safe**: Drops frames if anonymization fails

#### 🛡️ Moderate (Balanced Privacy)
- **Method**: Heavy blur over faces
- **Face Data**: Privacy-preserving hashed embeddings only
- **Hashes**: Similarity-based hashes for identification
- **Fail-Safe**: Continues with warning if anonymization fails

#### ⚖️ Minimal (Light Privacy)
- **Method**: Light blur over faces
- **Face Data**: Basic face metrics stored
- **Hashes**: More detailed hashes for better identification
- **Fail-Safe**: Minimal protection, prioritizes functionality

### Anonymization Methods

#### 🌫️ Blur
- **Effect**: Gaussian blur over detected faces
- **Privacy**: High - faces become unrecognizable
- **Performance**: Fast
- **Use Case**: General purpose anonymization

#### 🔲 Pixelate
- **Effect**: Pixelation effect over faces
- **Privacy**: High - faces become blocky and unrecognizable
- **Performance**: Fast
- **Use Case**: Modern anonymization with visual appeal

#### ⬛ Black Box
- **Effect**: Solid black rectangles over faces
- **Privacy**: Maximum - complete face obscuration
- **Performance**: Fastest
- **Use Case**: Strict compliance environments

#### 😊 Emoji
- **Effect**: Random emoji overlays on faces
- **Privacy**: High with friendly appearance
- **Performance**: Moderate
- **Use Case**: Public-facing systems, customer areas

## 📊 API Endpoints

### Privacy Status
```http
GET /privacy/status
```
Returns current privacy configuration and anonymization statistics.

**Response:**
```json
{
  "enabled": true,
  "privacy_level": "strict",
  "method": "blur",
  "stats": {
    "frames_processed": 1500,
    "faces_anonymized": 342,
    "compliance_score": 98.5
  },
  "models": {
    "haar_cascade": "loaded",
    "dnn_model": "loaded"
  }
}
```

### Configure Privacy Settings
```http
POST /privacy/configure
Content-Type: application/json

{
  "privacy_level": "strict",
  "method": "blur",
  "enabled": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Privacy settings updated",
  "current_config": {
    "privacy_level": "strict",
    "method": "blur",
    "enabled": true
  }
}
```

### Test Anonymization
```http
POST /privacy/test
Content-Type: multipart/form-data

image: [image file]
```

Tests face detection and anonymization on an uploaded image.

## 🔧 Setup & Installation

### 1. Model Download
The system requires OpenCV face detection models. Run the setup script:

```bash
cd edge_service
python setup_face_models.py
```

This downloads:
- Haar Cascade frontal face classifier
- OpenCV DNN face detection model

### 2. Docker Build
Models are automatically downloaded during Docker build:

```bash
docker-compose build edge-service
```

### 3. Environment Configuration
Ensure privacy settings are configured in `.env`:

```bash
# Privacy Compliance
ANONYMIZATION_ENABLED=true
PRIVACY_LEVEL=strict
ANONYMIZATION_METHOD=blur
FACE_HASH_ENABLED=true
COMPLIANCE_MODE=gdpr
```

## 🧪 Testing

### Automated Testing
Run the comprehensive test suite:

```bash
# Windows
.\test_face_anonymization.ps1

# Linux/Mac
python -m pytest tests/test_face_anonymization.py -v
python -m pytest tests/test_integration_anonymization.py -v
```

### Manual Testing
1. **Start the service**:
   ```bash
   docker-compose up edge-service
   ```

2. **Check privacy status**:
   ```bash
   curl http://localhost:8001/privacy/status
   ```

3. **Test with an image**:
   ```bash
   curl -X POST -F "image=@test_image.jpg" http://localhost:8001/privacy/test
   ```

## 📈 Monitoring & Compliance

### Prometheus Metrics
The service exposes privacy compliance metrics:

- `anonymization_frames_processed_total`: Total frames processed
- `anonymization_faces_detected_total`: Total faces detected
- `anonymization_faces_anonymized_total`: Total faces anonymized
- `anonymization_processing_duration_seconds`: Processing time distribution
- `anonymization_failure_total`: Anonymization failures
- `privacy_compliance_score`: Current compliance score (0-100)
- `face_detection_model_load_duration_seconds`: Model loading time
- `anonymization_method_usage_total`: Usage by method

### Grafana Dashboard
A comprehensive privacy compliance dashboard is available:
- Real-time anonymization statistics
- Compliance score tracking
- Performance metrics
- Failure rate monitoring

Import from: `monitoring/grafana/dashboards/privacy-compliance.json`

### GDPR Compliance
The system is designed for GDPR compliance:
- ✅ **Data Minimization**: Only necessary face metadata retained
- ✅ **Purpose Limitation**: Anonymization serves security purposes only
- ✅ **Storage Limitation**: No raw face data stored
- ✅ **Accuracy**: High-quality face detection models
- ✅ **Security**: On-device processing prevents data breaches
- ✅ **Accountability**: Comprehensive audit logging

## 🔍 Technical Implementation

### Face Detection Models
1. **Primary**: OpenCV Haar Cascade (fast, reliable)
2. **Fallback**: DNN-based face detection (higher accuracy)
3. **Automatic Switching**: Falls back to DNN if Haar fails

### Processing Pipeline
```
Camera Frame → Face Detection → Anonymization → AI Processing → Transmission
     ↓              ↓              ↓
Raw Image → Face Boxes → Anonymized → Safe for AI
```

### Privacy-Preserving Hashes
Face identification uses one-way hashes:
- **Geometric Features**: Distance ratios, angles
- **Privacy-Safe**: Cannot reconstruct original face
- **Consistent**: Same person generates same hash
- **Configurable**: Hash complexity based on privacy level

## 🚨 Troubleshooting

### Common Issues

#### Face Detection Models Not Found
```bash
# Download models manually
python setup_face_models.py

# Check model files exist
ls -la models/
```

#### Low Detection Accuracy
- Switch to DNN model in configuration
- Adjust detection confidence threshold
- Ensure good lighting conditions

#### Performance Issues
- Use Haar Cascade for speed
- Reduce frame resolution
- Optimize detection parameters

#### Privacy Compliance Failures
- Enable strict mode
- Verify all faces are detected
- Check anonymization coverage

### Log Analysis
Monitor logs for privacy compliance:

```bash
# Check anonymization status
docker logs edge-service | grep "anonymization"

# Monitor failures
docker logs edge-service | grep "PRIVACY_VIOLATION"

# Check compliance scores
docker logs edge-service | grep "compliance_score"
```

### Performance Tuning
Optimize for your use case:

```python
# High Performance (lower privacy)
ANONYMIZATION_METHOD=black_box
PRIVACY_LEVEL=minimal
DETECTION_MODEL=haar

# High Privacy (lower performance)
ANONYMIZATION_METHOD=blur
PRIVACY_LEVEL=strict
DETECTION_MODEL=dnn
```

## 🔐 Security Considerations

### Threat Model
- **Data Breach**: Raw face data never leaves device
- **Model Attacks**: Models run locally, not exposed
- **Hash Analysis**: Hashes use one-way functions
- **Compliance Audit**: Full audit trail maintained

### Best Practices
1. **Always Enable**: Keep anonymization enabled in production
2. **Regular Updates**: Update face detection models periodically
3. **Monitor Compliance**: Track compliance scores and failures
4. **Test Regularly**: Run automated tests to ensure functionality
5. **Audit Logs**: Review privacy compliance logs regularly

## 🚀 Deployment Checklist

- [ ] Face detection models downloaded and verified
- [ ] Privacy configuration set in environment variables
- [ ] Anonymization enabled and tested
- [ ] Compliance monitoring configured
- [ ] Grafana dashboard imported and configured
- [ ] Automated tests passing
- [ ] Performance metrics within acceptable ranges
- [ ] Security audit completed
- [ ] Documentation reviewed and updated

---

**Remember**: Privacy compliance is not optional. This system ensures that surveillance capabilities do not compromise individual privacy rights while maintaining operational effectiveness.

#### Blur (Default)
- Gaussian blur applied to face regions
- Configurable blur intensity
- Preserves general face area for context

#### Pixelate
- Reduces face resolution with pixelation effect
- Configurable pixelation factor
- Retains basic face shape

#### Black Box
- Solid black rectangle over face
- Maximum privacy protection
- Complete face obscuration

#### Emoji
- Friendly emoji-style anonymization
- Yellow circle with simple features
- Good for public-facing applications

## 📡 API Endpoints

### Get Anonymization Status
```http
GET /privacy/status
```

Response:
```json
{
  "enabled": true,
  "method": "blur",
  "privacy_level": "strict",
  "faces_detected_today": 42,
  "total_frames_processed": 1250
}
```

### Configure Anonymization
```http
POST /privacy/configure
Content-Type: application/json

{
  "enabled": true,
  "method": "blur",
  "privacy_level": "strict",
  "blur_factor": 20,
  "pixelate_factor": 10
}
```

### Test Anonymization
```http
POST /privacy/test
```

Tests anonymization with current camera frame and returns statistics.

## 🔧 Technical Implementation

### Detection Methods

1. **OpenCV Haar Cascade** (Primary)
   - Lightweight, fast detection
   - Good for edge devices
   - Lower accuracy but reliable

2. **DNN Face Detection** (Backup)
   - Higher accuracy detection
   - More computational overhead
   - Requires additional model files

### Face Hash Generation

Face hashes are generated based on privacy level:

- **Strict**: Only geometric features (position, size)
- **Moderate**: Blurred and resized face features
- **Minimal**: Basic face region characteristics

### Processing Pipeline

```
1. Capture Frame
2. ↓
3. Face Detection (OpenCV/DNN)
4. ↓
5. Face Anonymization (Blur/Pixelate/Block)
6. ↓
7. Generate Privacy-Safe Hashes
8. ↓
9. AI Inference on Anonymized Frame
10. ↓
11. Publish Event with Privacy Metadata
```

## 🚨 Compliance Features

### Regulatory Compliance
- **GDPR Article 25**: Privacy by design and by default
- **CCPA**: Consumer privacy protection
- **PIPEDA**: Personal information protection
- **Local Privacy Laws**: Configurable to meet local requirements

### Audit Trail
- All anonymization events are logged
- Privacy metadata included in event streams
- Configuration changes tracked
- Test results recorded

### Fail-Safe Mechanisms
- Strict mode drops frames if anonymization fails
- Health checks include anonymization status
- Real-time monitoring of privacy protection
- Automatic fallback to higher privacy levels

## 📊 Monitoring & Metrics

### Key Metrics
- `faces_detected_total`: Total faces detected
- `faces_anonymized_total`: Total faces anonymized
- `anonymization_failures_total`: Failed anonymization attempts
- `privacy_level_changes_total`: Configuration changes
- `frames_dropped_privacy_total`: Frames dropped for privacy

### Grafana Dashboard

A pre-configured Grafana dashboard is available at:
`monitoring/grafana/dashboards/privacy-compliance.json`

## 🧪 Testing

### Unit Tests
```bash
cd edge_service
python -m pytest tests/test_face_anonymization.py -v
```

### Integration Tests
```bash
# Test with live camera
curl -X POST http://localhost:8001/privacy/test

# Test configuration changes
curl -X POST http://localhost:8001/privacy/configure \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "method": "blur", "privacy_level": "strict"}'
```

## 🔍 Troubleshooting

### Common Issues

#### No Faces Detected
- Check camera positioning and lighting
- Verify minimum face size settings
- Test with different detection confidence thresholds

#### Anonymization Failures
- Check available memory and CPU resources
- Verify OpenCV installation
- Review error logs for specific failure reasons

#### Performance Issues
- Consider using Haar cascade only (disable DNN)
- Reduce frame processing rate
- Optimize blur/pixelation parameters

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Test with specific privacy settings
export PRIVACY_LEVEL=minimal
export ANONYMIZATION_METHOD=blur
```

## 📝 Best Practices

### Production Deployment
1. **Always Enable**: Never deploy without anonymization
2. **Use Strict Mode**: Maximum privacy protection by default
3. **Monitor Continuously**: Set up alerts for anonymization failures
4. **Regular Testing**: Verify anonymization effectiveness
5. **Document Settings**: Maintain configuration documentation

### Performance Optimization
1. **Tune Detection**: Balance accuracy vs. speed
2. **Batch Processing**: Process multiple frames efficiently
3. **Resource Monitoring**: Monitor CPU/memory usage
4. **Network Optimization**: Minimize data transmission

### Security Considerations
1. **Secure Configuration**: Protect anonymization settings
2. **Access Control**: Limit who can modify privacy settings
3. **Audit Logs**: Maintain detailed privacy audit trails
4. **Regular Updates**: Keep face detection models current

## 🔮 Future Enhancements

### Planned Features
- **Advanced Detection**: MTCNN and RetinaFace support
- **Edge AI Models**: Custom face detection for edge devices
- **Biometric Anonymization**: Voice and gait anonymization
- **Real-time Analytics**: Live privacy compliance dashboards
- **Automated Testing**: Continuous privacy validation

### Research Areas
- **Differential Privacy**: Mathematical privacy guarantees
- **Federated Learning**: Privacy-preserving model training
- **Homomorphic Encryption**: Computation on encrypted face data
- **Zero-Knowledge Proofs**: Prove face detection without revealing faces

---

**⚠️ IMPORTANT**: Face anonymization is critical for privacy compliance. Never disable in production environments without proper legal review and user consent.
