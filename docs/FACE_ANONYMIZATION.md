# Face Anonymization Documentation

## Overview

The edge service provides on-device face anonymization capabilities to ensure privacy compliance before any video data leaves the device. This document describes the configuration, model installation, and usage of the face anonymization system.

## Features

- **Real-time face detection** using OpenCV Haar Cascade and DNN models
- **Multiple anonymization methods**: blur, pixelate, black box, emoji
- **Configurable privacy levels**: strict, moderate, minimal
- **Automated model installation** during Docker build
- **Performance optimization** for edge devices
- **Hash-based face embeddings** for identification without storing raw faces

## Model Installation

### Automated Installation (Recommended)

The face detection models are automatically downloaded during the Docker build process. The following models are installed:

1. **Haar Cascade Classifier**: `haarcascade_frontalface_default.xml`
2. **DNN Prototxt**: `opencv_face_detector.pbtxt`
3. **DNN Model**: `opencv_face_detector_uint8.pb`

### Configuration

The model installation can be configured using the following build arguments:

```bash
# Default URLs (automatically used)
MODEL_BASE_URL=https://raw.githubusercontent.com/opencv/opencv/master
DNN_MODEL_URL=https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb
```

### Custom Model URLs

To use custom model URLs, you can override the build arguments:

```bash
# Build with custom model URLs
docker build \
  --build-arg MODEL_BASE_URL=https://your-custom-server.com/opencv \
  --build-arg DNN_MODEL_URL=https://your-custom-server.com/models/face_detector.pb \
  -t edge-service .
```

### Environment Variables

The following environment variables can be used to configure the face anonymization system:

```bash
# Model configuration
EDGE_SERVICE_MODEL_BASE_URL=https://raw.githubusercontent.com/opencv/opencv/master
EDGE_SERVICE_MODEL_DIR=/app/models
EDGE_SERVICE_HAAR_CASCADE_PATH=/app/models/haarcascade_frontalface_default.xml
EDGE_SERVICE_DNN_PROTOTXT_PATH=/app/models/opencv_face_detector.pbtxt
EDGE_SERVICE_DNN_MODEL_PATH=/app/models/opencv_face_detector_uint8.pb

# Anonymization settings
EDGE_SERVICE_ANONYMIZATION_ENABLED=true
EDGE_SERVICE_PRIVACY_LEVEL=moderate
EDGE_SERVICE_ANONYMIZATION_METHOD=blur
```

## Privacy Levels

### Strict
- Maximum anonymization applied
- No face data stored
- Highest privacy protection
- Performance impact: High

### Moderate (Default)
- Balanced anonymization
- Hashed face embeddings stored
- Good privacy protection
- Performance impact: Medium

### Minimal
- Light blur applied
- Basic metrics retained
- Minimal privacy protection
- Performance impact: Low

## Anonymization Methods

### Blur (Default)
- Applies Gaussian blur to detected faces
- Configurable blur intensity
- Good balance of privacy and performance

### Pixelate
- Applies pixelation effect to faces
- Configurable pixelation factor
- Retro aesthetic while maintaining privacy

### Black Box
- Covers faces with solid black rectangles
- Maximum anonymization
- Minimal processing overhead

### Emoji
- Replaces faces with emoji symbols
- Fun approach to anonymization
- Requires additional processing

## Docker Configuration

### Docker Compose

The `docker-compose.yml` file includes the necessary build arguments and environment variables:

```yaml
edge_service:
  build:
    context: .
    dockerfile: edge_service/Dockerfile
    args:
      - MODEL_BASE_URL=${MODEL_BASE_URL:-https://raw.githubusercontent.com/opencv/opencv/master}
      - DNN_MODEL_URL=${DNN_MODEL_URL:-https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb}
  environment:
    - EDGE_SERVICE_MODEL_BASE_URL=${MODEL_BASE_URL:-https://raw.githubusercontent.com/opencv/opencv/master}
    - EDGE_SERVICE_ANONYMIZATION_ENABLED=true
    - EDGE_SERVICE_PRIVACY_LEVEL=moderate
    - EDGE_SERVICE_ANONYMIZATION_METHOD=blur
```

### Rebuilding with Custom Configuration

To rebuild the Docker image with custom model URLs:

```bash
# Set environment variables
export MODEL_BASE_URL=https://your-custom-server.com/opencv
export DNN_MODEL_URL=https://your-custom-server.com/models/face_detector.pb

# Rebuild the service
docker-compose build edge_service
```

## Usage

### Basic Usage

```python
from edge_service.face_anonymization import FaceAnonymizer, AnonymizationConfig
from edge_service.config import settings

# Use default configuration
anonymizer = FaceAnonymizer()

# Process a frame
anonymized_frame = anonymizer.anonymize_frame(input_frame)
```

### Custom Configuration

```python
# Custom anonymization configuration
config = AnonymizationConfig(
    enabled=True,
    method=AnonymizationMethod.BLUR,
    privacy_level=PrivacyLevel.STRICT,
    blur_factor=20
)

anonymizer = FaceAnonymizer(config)
anonymized_frame = anonymizer.anonymize_frame(input_frame)
```

### Configuration via Environment Variables

```python
# Configuration is automatically loaded from environment variables
# via the settings module
from edge_service.config import settings

print(f"Model directory: {settings.model_dir}")
print(f"Anonymization enabled: {settings.anonymization_enabled}")
print(f"Privacy level: {settings.privacy_level}")
```

## Performance Considerations

### Model Selection
- **Haar Cascade**: Lightweight, good for edge devices
- **DNN Model**: More accurate but requires more processing power

### Optimization Tips
1. Use appropriate privacy level for your use case
2. Consider frame rate requirements
3. Monitor system resources
4. Adjust blur/pixelation factors based on performance needs

## Troubleshooting

### Model Files Not Found
If you encounter model file errors:

1. Check that the Docker build completed successfully
2. Verify the model files exist in `/app/models/`
3. Check the environment variables are set correctly
4. Ensure the model URLs are accessible

### Performance Issues
If face anonymization is too slow:

1. Reduce the privacy level to `minimal`
2. Use `blur` method instead of `pixelate` or `emoji`
3. Reduce the blur factor
4. Consider using only Haar Cascade detection

### Memory Issues
If the service runs out of memory:

1. Reduce the batch size for processing
2. Use smaller model files if available
3. Increase container memory limits
4. Monitor memory usage with metrics

## Security Considerations

### Data Privacy
- Face detection models are stored locally
- No face data is transmitted outside the device
- Hash-based embeddings provide privacy protection
- Raw face images are never stored

### Model Integrity
- Models are downloaded from trusted sources
- File integrity is verified during Docker build
- Consider using checksums for additional verification

### Network Security
- Model downloads occur only during build time
- Runtime operation is fully offline
- No external dependencies for face processing

## Development

### Testing
Run the edge setup tests to verify configuration:

```bash
# Run all edge setup tests
python -m pytest tests/test_edge_setup.py -v

# Run specific test categories
python -m pytest tests/test_edge_setup.py::TestModelConfiguration -v
python -m pytest tests/test_edge_setup.py::TestRequirementsConsolidation -v
```

### Adding New Models
To add support for new face detection models:

1. Update the `config.py` file with new model paths
2. Modify the Dockerfile to download additional models
3. Update the `face_anonymization.py` module to use new models
4. Add tests for the new models

### Configuration Changes
When modifying configuration:

1. Update the `EdgeServiceSettings` class in `config.py`
2. Update the Dockerfile environment variables
3. Update the docker-compose.yml file
4. Update this documentation

## API Reference

### Configuration Classes

#### `EdgeServiceSettings`
Main configuration class for the edge service.

#### `AnonymizationConfig`
Configuration for face anonymization behavior.

### Anonymization Classes

#### `FaceAnonymizer`
Main class for face detection and anonymization.

#### `AnonymizationMethod`
Enum defining available anonymization methods.

#### `PrivacyLevel`
Enum defining privacy protection levels.

### Utility Functions

#### `get_model_paths()`
Returns dictionary of all model file paths.

#### `validate_model_files()`
Validates that all required model files exist and are not empty.

#### `get_settings()`
Returns the global settings instance.

## Changelog

### Version 2.0.0
- Automated model installation during Docker build
- Consolidated requirements files
- Removed manual setup script
- Added comprehensive configuration system
- Improved error handling and validation

### Version 1.0.0
- Initial face anonymization implementation
- Manual model setup required
- Basic configuration support
