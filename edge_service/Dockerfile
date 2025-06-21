# ==============================================================================
# Edge AI Service Dockerfile
# ==============================================================================
# This Dockerfile builds a containerized edge AI service for real-time video
# processing, object detection, and face anonymization. The service is optimized
# for edge deployment with automated model downloading and minimal resource usage.
#
# Build Arguments:
#   MODEL_BASE_URL: Base URL for downloading OpenCV models
#   DNN_MODEL_URL: Specific URL for DNN face detection model
#
# Key Features:
#   - Automated face detection model downloading
#   - Privacy-preserving face anonymization
#   - TensorRT-ready inference pipeline
#   - Comprehensive system dependencies
#   - Production-ready environment configuration
# ==============================================================================

# Stage 1: Base Python Environment
# Use Python 3.9 slim for optimal balance of features and size
FROM python:3.9-slim

# Build arguments for flexible model configuration
# These allow customization of model sources during build time
ARG MODEL_BASE_URL=https://raw.githubusercontent.com/opencv/opencv/master
ARG DNN_MODEL_URL=https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb

# Stage 2: System Dependencies Installation
# Install essential system packages for OpenCV, SSL, and GUI support
RUN apt-get update && apt-get install -y \
    # Build tools for compiling Python packages
    build-essential \
    # OpenGL support for computer vision operations
    libgl1 \
    # SSL/TLS support for secure communications
    libssl-dev \
    # GLib support for system integration
    libglib2.0-0 \
    # X11 support for image processing
    libsm6 \
    libxext6 \
    libxrender-dev \
    # OpenMP support for parallel processing
    libgomp1 \
    # GTK support for GUI applications (if needed)
    libgtk-3-0 \
    # Network utilities for model downloading
    wget \
    curl \
    # Clean up package cache to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Stage 3: Application Directory Setup
# Set working directory for application code
WORKDIR /app

# Stage 4: Python Dependencies Installation
# Copy requirements file and install Python packages
# This is done early to leverage Docker layer caching
COPY edge_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 5: Model Directory Creation
# Create directory for face detection models
RUN mkdir -p /app/models

# Stage 6: Automated Model Download
# Download face detection models automatically during build
# This ensures models are always available without manual intervention
RUN echo "Downloading face detection models..." && \
    # Download Haar cascade for lightweight face detection
    wget -q -O /app/models/haarcascade_frontalface_default.xml \
        "${MODEL_BASE_URL}/data/haarcascades/haarcascade_frontalface_default.xml" && \
    # Download DNN prototxt configuration file
    wget -q -O /app/models/opencv_face_detector.pbtxt \
        "${MODEL_BASE_URL}/samples/dnn/face_detector/opencv_face_detector.pbtxt" && \
    # Download DNN model weights file
    wget -q -O /app/models/opencv_face_detector_uint8.pb \
        "${DNN_MODEL_URL}" && \
    echo "Face detection models downloaded successfully!" && \
    # List downloaded files for verification
    ls -la /app/models/

# Stage 7: Model Verification
# Verify that all downloaded models are valid and non-empty
# This prevents runtime errors due to corrupted or missing models
RUN python3 -c "\
import os; \
# Define required model files
models = ['/app/models/haarcascade_frontalface_default.xml', \
          '/app/models/opencv_face_detector.pbtxt', \
          '/app/models/opencv_face_detector_uint8.pb']; \
# Check for missing or empty files
missing = [m for m in models if not os.path.exists(m) or os.path.getsize(m) == 0]; \
# Fail build if any models are missing
assert not missing, f'Missing or empty model files: {missing}'; \
print('All face detection models verified successfully!')"

# Stage 8: Application Code Copy
# Copy shared libraries and edge service code
# Order matters for optimal layer caching
COPY shared/ /app/shared/
COPY edge_service/ .

# Stage 8.5: Model Quantization
# Run model quantization to create optimized INT8 models
# This step happens after copying code but before final configuration
RUN echo "Starting model quantization pipeline..." && \
    # Create dummy model for quantization if no existing model
    python3 tools/quantize_model.py --create-dummy --model-dir /app/models --verbose && \
    # Run quantization to create INT8 optimized model
    python3 tools/quantize_model.py --model-dir /app/models --verbose && \
    echo "Model quantization completed successfully!" && \
    # List all model files for verification
    ls -la /app/models/ && \
    # Show quantization statistics if available
    if [ -f /app/models/quantization_stats.json ]; then \
        echo "Quantization Statistics:" && \
        cat /app/models/quantization_stats.json; \
    fi

# Stage 9: Environment Configuration
# Set environment variables for service configuration
# These control face anonymization behavior and model paths

# Python runtime configuration
ENV PYTHONUNBUFFERED=1

# Face anonymization configuration
# Enable face anonymization by default for privacy compliance
ENV EDGE_SERVICE_ANONYMIZATION_ENABLED=true
# Set moderate privacy level (balance between privacy and functionality)
ENV EDGE_SERVICE_PRIVACY_LEVEL=moderate
# Use blur method for face anonymization (less intrusive than black boxes)
ENV EDGE_SERVICE_ANONYMIZATION_METHOD=blur

# Model file paths configuration
# Point to the downloaded models in the container and use quantized INT8 model
ENV EDGE_SERVICE_MODEL_DIR=/app/models
ENV EDGE_SERVICE_QUANTIZED_MODEL_PATH=/app/models/model_int8.onnx
ENV EDGE_SERVICE_USE_QUANTIZED_MODEL=true
ENV EDGE_SERVICE_HAAR_CASCADE_PATH=/app/models/haarcascade_frontalface_default.xml
ENV EDGE_SERVICE_DNN_PROTOTXT_PATH=/app/models/opencv_face_detector.pbtxt
ENV EDGE_SERVICE_DNN_MODEL_PATH=/app/models/opencv_face_detector_uint8.pb

# Stage 10: Network Configuration
# Expose port 8000 for the FastAPI service
EXPOSE 8000

# Stage 11: Service Startup
# Start the edge service using Uvicorn ASGI server
# Configuration optimized for edge deployment
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]