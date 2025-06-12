# Multi-stage Dockerfile for MLflow Edge Inference Deployment
# This Dockerfile creates optimized containers for edge inference with MLflow model loading
# and TensorRT optimization capabilities

# =====================================
# Stage 1: Base Image with CUDA/TensorRT
# =====================================
FROM nvcr.io/nvidia/tensorrt:23.08-py3 as tensorrt-base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgoogle-glog-dev \
    && rm -rf /var/lib/apt/lists/*

# =====================================
# Stage 2: Python Dependencies
# =====================================
FROM tensorrt-base as python-deps

# Upgrade pip and install build tools
RUN pip3 install --upgrade pip setuptools wheel

# Install PyTorch with CUDA support
RUN pip3 install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 \
    --index-url https://download.pytorch.org/whl/cu118

# Install MLflow and core dependencies
RUN pip3 install \
    mlflow>=2.10.0 \
    onnx>=1.15.0 \
    onnxruntime-gpu>=1.16.0 \
    numpy>=1.24.0 \
    pydantic>=2.0.0 \
    fastapi>=0.100.0 \
    uvicorn[standard]>=0.20.0

# Install computer vision libraries
RUN pip3 install \
    opencv-python>=4.8.0 \
    pillow>=10.0.0 \
    albumentations>=1.3.0 \
    scikit-image>=0.21.0

# Install monitoring and utilities
RUN pip3 install \
    prometheus-client>=0.17.0 \
    psutil>=5.9.0 \
    GPUtil>=1.4.0 \
    requests>=2.28.0 \
    aiofiles>=23.0.0 \
    python-multipart>=0.0.6

# Install Kafka client
RUN pip3 install confluent-kafka>=2.3.0

# =====================================
# Stage 3: Application Build
# =====================================
FROM python-deps as app-build

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Copy shared libraries and models
COPY shared/ /app/shared/
COPY models/ /app/models/

# Copy edge service application
COPY edge_service/ /app/edge_service/

# Copy training and optimization scripts
COPY train/ /app/train/
COPY infra/ /app/infra/

# Install application dependencies
COPY requirements.txt /app/
RUN pip3 install -r requirements.txt

# =====================================
# Stage 4: Final Production Image
# =====================================
FROM app-build as production

# Build arguments for model information
ARG MODEL_ARCHITECTURE=mobilenet_v3
ARG MODEL_VERSION=latest
ARG TENSORRT_PRECISION=fp16
ARG MLFLOW_RUN_ID=""

# Set build info as environment variables
ENV MODEL_ARCHITECTURE=${MODEL_ARCHITECTURE}
ENV MODEL_VERSION=${MODEL_VERSION}
ENV TENSORRT_PRECISION=${TENSORRT_PRECISION}
ENV MLFLOW_RUN_ID=${MLFLOW_RUN_ID}

# Set application environment variables
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV LOG_FORMAT=json
ENV METRICS_PORT=8080
ENV HEALTH_CHECK_PORT=8000
ENV GRPC_PORT=50051

# MLflow configuration
ENV MLFLOW_TRACKING_URI=http://mlflow-server:5000
ENV MLFLOW_EXPERIMENT_NAME=edge-inference-production

# Inference configuration
ENV INFERENCE_TIMEOUT=30
ENV MAX_CONCURRENT_REQUESTS=100
ENV ENABLE_TENSORRT=true
ENV ENABLE_PERFORMANCE_MONITORING=true
ENV BATCH_SIZE=8
ENV GPU_MEMORY_FRACTION=0.8

# Create application directories
RUN mkdir -p /app/cache/tensorrt \
    /app/logs \
    /app/data \
    /app/models \
    /model-cache \
    /tmp/inference \
    && chown -R appuser:appuser /app /model-cache /tmp/inference

# Create edge inference application
COPY docker/edge-inference-app.py /app/main.py

# Create health check script
RUN cat > /app/health_check.py << 'EOF'
#!/usr/bin/env python3
import sys
import requests
import time

def check_health():
    try:
        # Check main application
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print(f"Health check failed: {response.status_code}")
            return False
        
        # Check metrics endpoint
        response = requests.get("http://localhost:8080/metrics", timeout=5)
        if response.status_code != 200:
            print(f"Metrics check failed: {response.status_code}")
            return False
        
        print("Health check passed")
        return True
    except Exception as e:
        print(f"Health check error: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
EOF

# Create model loader script
RUN cat > /app/load_models.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import mlflow
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_models_from_mlflow():
    """Download models from MLflow registry"""
    try:
        # Setup MLflow client
        tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
        mlflow.set_tracking_uri(tracking_uri)
        
        model_arch = os.getenv('MODEL_ARCHITECTURE', 'mobilenet_v3')
        stage = os.getenv('MODEL_REGISTRY_STAGE', 'Production')
        
        logger.info(f"Loading model: surveillance_{model_arch}_edge from {stage}")
        
        # Get model from registry
        model_name = f"surveillance_{model_arch}_edge"
        client = mlflow.tracking.MlflowClient()
        
        try:
            # Try to get production model first
            models = client.get_latest_versions(model_name, stages=[stage])
            if not models and stage == 'Production':
                # Fall back to staging if no production model
                logger.warning("No production model found, trying staging...")
                models = client.get_latest_versions(model_name, stages=['Staging'])
                
            if not models:
                logger.error(f"No model found for {model_name}")
                return False
                
            model_version = models[0]
            model_uri = f"models:/{model_name}/{model_version.version}"
            
            logger.info(f"Downloading model version {model_version.version}")
            
            # Download to cache
            cache_dir = Path('/model-cache')
            cache_dir.mkdir(exist_ok=True)
            
            downloaded_path = mlflow.artifacts.download_artifacts(
                artifact_uri=model_uri,
                dst_path=str(cache_dir)
            )
            
            logger.info(f"Model downloaded to: {downloaded_path}")
            
            # Create symlink for inference engine
            models_dir = Path('/app/models')
            models_dir.mkdir(exist_ok=True)
            
            # Link ONNX and TensorRT files
            for ext in ['*.onnx', '*.engine', '*.pt']:
                for model_file in Path(downloaded_path).rglob(ext):
                    target = models_dir / model_file.name
                    if target.exists():
                        target.unlink()
                    target.symlink_to(model_file)
                    logger.info(f"Linked {model_file.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
            
    except Exception as e:
        logger.error(f"MLflow setup error: {e}")
        return False

if __name__ == "__main__":
    success = load_models_from_mlflow()
    sys.exit(0 if success else 1)
EOF

# Create startup script
RUN cat > /app/start.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Starting Edge Inference Service"
echo "Model: ${MODEL_ARCHITECTURE}"
echo "Version: ${MODEL_VERSION}"
echo "Precision: ${TENSORRT_PRECISION}"
echo "MLflow URI: ${MLFLOW_TRACKING_URI}"

# Load models from MLflow
echo "📥 Loading models from MLflow..."
python /app/load_models.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to load models from MLflow"
    exit 1
fi

# Start metrics server in background
echo "📊 Starting metrics server..."
python -c "
import time
from prometheus_client import start_http_server, Counter, Histogram, Gauge
import threading

# Metrics
inference_requests = Counter('inference_requests_total', 'Total inference requests')
inference_latency = Histogram('inference_latency_seconds', 'Inference latency')
gpu_utilization = Gauge('gpu_utilization_percent', 'GPU utilization')
model_loads = Counter('model_loads_total', 'Total model loads')

def update_gpu_metrics():
    try:
        import GPUtil
        while True:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_utilization.set(gpus[0].load * 100)
            time.sleep(10)
    except:
        pass

start_http_server(${METRICS_PORT})
threading.Thread(target=update_gpu_metrics, daemon=True).start()

print('Metrics server started on port ${METRICS_PORT}')
while True:
    time.sleep(60)
" &

# Start main application
echo "🎯 Starting inference server..."
exec python /app/main.py
EOF

# Make scripts executable
RUN chmod +x /app/start.sh /app/health_check.py /app/load_models.py

# Set proper ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 8000 8080 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python /app/health_check.py

# Set entrypoint
ENTRYPOINT ["/app/start.sh"]

# =====================================
# Development Stage (Optional)
# =====================================
FROM production as development

USER root

# Install development tools
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    curl \
    netcat \
    telnet \
    && rm -rf /var/lib/apt/lists/*

# Install Python development dependencies
RUN pip3 install \
    pytest>=7.4.0 \
    pytest-asyncio>=0.21.0 \
    pytest-mock>=3.11.0 \
    ipython>=8.0.0 \
    jupyter>=1.0.0 \
    black>=23.0.0 \
    isort>=5.12.0

# Development environment variables
ENV DEVELOPMENT_MODE=true
ENV LOG_LEVEL=DEBUG
ENV RELOAD=true

USER appuser

# Default command for development
CMD ["python", "/app/main.py", "--reload"]
