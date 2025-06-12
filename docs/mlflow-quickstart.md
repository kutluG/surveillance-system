# MLflow Model Registry & Edge Deployment Quick Start Guide

## 🎯 Overview

This guide helps you get started with the comprehensive MLflow model registry and versioned deployment system for edge inference models in the surveillance system.

## 📋 Prerequisites

### Required Dependencies
```bash
pip install mlflow>=2.10.0
pip install torch torchvision
pip install onnx onnxruntime
pip install ultralytics  # For YOLO models
pip install albumentations opencv-python
pip install scikit-learn numpy pandas
```

### Optional (for TensorRT optimization)
```bash
# TensorRT requires manual installation - see NVIDIA documentation
pip install tensorrt pycuda
pip install nvidia-ml-py
```

## 🚀 Quick Start

### 1. Start MLflow Tracking Server

```bash
# Option A: Simple local server
python infra/mlflow_server.py

# Option B: Production server with custom config
python infra/mlflow_server.py --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///mlflow.db
```

The MLflow UI will be available at: http://localhost:5000

### 2. Train Your First Model

```bash
# Train MobileNetV3 for surveillance classification
python train/train.py --model mobilenet_v3 --epochs 10 --batch-size 16

# Train YOLOv8 for object detection
python train/train.py --model yolov8n --epochs 20 --img-size 640

# Train EfficientNet with custom parameters
python train/train.py --model efficientnet_b0 --epochs 50 --lr 0.0001
```

### 3. Optimize Model for Edge Deployment

```bash
# Convert latest trained model to TensorRT
python train/convert_to_trt.py --model-name surveillance_mobilenet_v3_edge --precision fp16

# Convert specific model version
python train/convert_to_trt.py --model-name surveillance_mobilenet_v3_edge --version 2 --precision int8

# Convert from specific run
python train/convert_to_trt.py --run-id <your-mlflow-run-id> --precision fp16
```

## 📊 Monitoring and Management

### View Training Experiments
1. Open MLflow UI: http://localhost:5000
2. Navigate to "Experiments" → "surveillance-edge-models"
3. Compare metrics, parameters, and artifacts across runs

### Model Registry Management
1. Go to "Models" tab in MLflow UI
2. View registered models and versions
3. Transition models between stages:
   - **None** → **Staging** → **Production**

### Performance Monitoring
- Training metrics: accuracy, loss, F1-score
- TensorRT optimization: latency improvement, throughput gains
- Edge deployment: inference speed, memory usage

## 🔧 Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# MLflow Configuration
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=surveillance-edge-models
MODEL_REGISTRY_STAGE=Staging

# Dataset Configuration
DATASET_PATH=data/surveillance_dataset

# TensorRT Configuration
TRT_CACHE_DIR=cache/tensorrt
CUDA_VISIBLE_DEVICES=0

# Edge Deployment
DEVICE_TYPE=nvidia-gpu
GPU_MEMORY_FRACTION=0.8
ENABLE_TENSORRT=true
```

### Dataset Structure

For classification:
```
data/surveillance_dataset/
├── train/
│   ├── person/
│   ├── vehicle/
│   ├── bike/
│   └── animal/
└── val/
    ├── person/
    ├── vehicle/
    ├── bike/
    └── animal/
```

For YOLO detection:
```
data/surveillance_dataset/
├── data.yaml
├── train/
│   ├── images/
│   └── labels/
└── val/
    ├── images/
    └── labels/
```

## 🧪 Testing

### Run Integration Tests
```bash
# Full test suite
pytest tests/test_mlflow_integration.py -v

# Specific test categories
pytest tests/test_mlflow_integration.py::TestMLflowServer -v
pytest tests/test_mlflow_integration.py::TestModelTraining -v
pytest tests/test_mlflow_integration.py::TestModelRegistry -v
```

### Manual Testing
```bash
# Test MLflow server health
curl http://localhost:5000/health

# Test model registry API
python -c "
import mlflow
mlflow.set_tracking_uri('http://localhost:5000')
client = mlflow.tracking.MlflowClient()
experiments = client.search_experiments()
print(f'Found {len(experiments)} experiments')
"
```

## 🐳 Docker Deployment

### Build Edge Inference Container
```bash
# Build Docker image
docker build -f docker/edge-inference.Dockerfile -t surveillance-edge:latest .

# Run container locally
docker run -d \
  --name surveillance-edge \
  --gpus all \
  -p 8000:8000 \
  -e MLFLOW_TRACKING_URI=http://host.docker.internal:5000 \
  surveillance-edge:latest
```

### Test Edge Inference API
```bash
# Health check
curl http://localhost:8000/health

# Inference test
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"image": "base64_encoded_image_data"}'
```

## ☸️ Kubernetes Deployment

### Deploy to Kubernetes
```bash
# Apply all manifests
kubectl apply -f k8s/edge-deployment.yaml

# Check deployment status
kubectl get pods -n surveillance-edge
kubectl get services -n surveillance-edge

# View logs
kubectl logs -f deployment/surveillance-edge-inference -n surveillance-edge
```

### Scale Deployment
```bash
# Manual scaling
kubectl scale deployment surveillance-edge-inference --replicas=5 -n surveillance-edge

# Auto-scaling is configured via HorizontalPodAutoscaler
kubectl get hpa -n surveillance-edge
```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

The CI/CD pipeline automatically:
1. **Triggers** on code changes to `train/`, `models/`, or `data/` directories
2. **Trains** models with MLflow tracking
3. **Optimizes** with TensorRT for edge deployment
4. **Tests** integration and performance
5. **Builds** Docker containers
6. **Deploys** to staging environment
7. **Promotes** to production (with approval)

### Manual Workflow Trigger
```bash
# Trigger via GitHub CLI
gh workflow run train_and_deploy.yml \
  -f model_architecture=mobilenet_v3 \
  -f epochs=50 \
  -f precision=fp16 \
  -f deploy_to_staging=true
```

## 📈 Best Practices

### Model Training
- **Reproducibility**: Always set random seeds
- **Versioning**: Use meaningful experiment and run names
- **Monitoring**: Track comprehensive metrics (accuracy, loss, F1, precision, recall)
- **Validation**: Implement proper train/validation splits
- **Artifacts**: Log model files, configurations, and conversion outputs

### Model Registry
- **Staging**: Test all models in staging before production
- **Versioning**: Use semantic versioning for model releases
- **Documentation**: Add descriptive tags and documentation
- **Rollback**: Keep previous versions for quick rollback

### Edge Deployment
- **Optimization**: Always use TensorRT for NVIDIA hardware
- **Monitoring**: Track inference latency and throughput
- **Auto-scaling**: Configure based on request load
- **Health Checks**: Implement comprehensive health endpoints

### Security
- **Secrets**: Use Kubernetes secrets for credentials
- **Network Policies**: Restrict network access between services
- **Images**: Scan container images for vulnerabilities
- **RBAC**: Use proper role-based access control

## 🔧 Troubleshooting

### Common Issues

**MLflow Server Won't Start**
```bash
# Check port availability
netstat -an | findstr 5000

# Check database permissions
ls -la mlflow.db

# Reset database
rm mlflow.db && python infra/mlflow_server.py
```

**Training Fails**
```bash
# Check dataset structure
python -c "
from train.train import SurveillanceDataset
dataset = SurveillanceDataset('data/surveillance_dataset/train')
print(f'Found {len(dataset)} samples')
"

# Test MLflow connection
python -c "
import mlflow
mlflow.set_tracking_uri('http://localhost:5000')
try:
    mlflow.create_experiment('test')
    print('MLflow connection successful')
except:
    print('MLflow connection failed')
"
```

**TensorRT Conversion Fails**
```bash
# Check GPU availability
python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'GPU count: {torch.cuda.device_count()}')
"

# Check TensorRT installation
python -c "
try:
    import tensorrt as trt
    print(f'TensorRT version: {trt.__version__}')
except ImportError:
    print('TensorRT not installed')
"
```

**Kubernetes Deployment Issues**
```bash
# Check pod status
kubectl describe pod <pod-name> -n surveillance-edge

# Check logs
kubectl logs <pod-name> -n surveillance-edge

# Check resource limits
kubectl top pods -n surveillance-edge
```

## 📚 Additional Resources

- **MLflow Documentation**: https://mlflow.org/docs/latest/
- **TensorRT Documentation**: https://docs.nvidia.com/deeplearning/tensorrt/
- **Kubernetes Documentation**: https://kubernetes.io/docs/
- **PyTorch Documentation**: https://pytorch.org/docs/
- **Ultralytics YOLO**: https://docs.ultralytics.com/

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs in MLflow UI and Kubernetes
3. Run the integration test suite
4. Open an issue in the project repository

---

🎉 **You're now ready to use the complete MLflow model registry and edge deployment system!**
