#!/usr/bin/env python3
"""
Edge Inference Service with MLflow Integration

Production-ready edge inference service that:
1. Loads models from MLflow Model Registry
2. Provides REST and gRPC APIs for inference
3. Supports TensorRT optimization
4. Includes comprehensive monitoring and health checks
5. Handles model hot-swapping and updates

Usage:
    python main.py
    python main.py --reload  # Development mode with auto-reload
"""

import os
import sys
import json
import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

# Add app directory to Python path
sys.path.insert(0, '/app')

# FastAPI and async imports
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Monitoring and metrics
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# MLflow and inference
import mlflow
import mlflow.pytorch
from mlflow.tracking import MlflowClient

# Computer vision and ML
import numpy as np
import cv2
import torch
from PIL import Image
import onnxruntime as ort

# Application imports
try:
    from edge_service.inference import EdgeInference
    from shared.models import Detection, BoundingBox
except ImportError:
    # Fallback for standalone deployment
    sys.path.append('/app/edge_service')
    sys.path.append('/app/shared')
    from inference import EdgeInference
    from models import Detection, BoundingBox

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_format = os.getenv('LOG_FORMAT', 'text')

if log_format.lower() == 'json':
    import json
    import logging
    
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            if record.exc_info:
                log_entry['exception'] = self.formatException(record.exc_info)
            return json.dumps(log_entry)
    
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.handlers = [handler]

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('edge_inference_service')

# Prometheus metrics
inference_requests_total = Counter(
    'inference_requests_total', 
    'Total number of inference requests',
    ['endpoint', 'model_type', 'status']
)

inference_duration_seconds = Histogram(
    'inference_duration_seconds',
    'Time spent processing inference requests',
    ['endpoint', 'model_type']
)

model_load_duration_seconds = Histogram(
    'model_load_duration_seconds',
    'Time spent loading models',
    ['model_name', 'model_version']
)

active_requests = Gauge(
    'active_inference_requests',
    'Number of currently active inference requests'
)

model_info = Gauge(
    'model_info',
    'Information about loaded models',
    ['model_name', 'model_version', 'model_stage', 'architecture']
)

gpu_memory_usage = Gauge(
    'gpu_memory_usage_bytes',
    'GPU memory usage in bytes'
)

# Pydantic models for API
class InferenceRequest(BaseModel):
    image_data: str = Field(..., description="Base64 encoded image data")
    camera_id: Optional[str] = Field(None, description="Camera identifier")
    model_type: str = Field("object_detection", description="Type of model to use")
    confidence_threshold: float = Field(0.5, description="Confidence threshold for detections")

class InferenceResponse(BaseModel):
    detections: List[Dict[str, Any]]
    processing_time_ms: float
    model_info: Dict[str, str]
    camera_id: Optional[str]
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    models_loaded: bool
    gpu_available: bool
    memory_usage: Dict[str, float]
    uptime_seconds: float

class ModelInfo(BaseModel):
    name: str
    version: str
    stage: str
    architecture: str
    precision: str
    last_updated: str

# Global application state
class AppState:
    def __init__(self):
        self.inference_engine: Optional[EdgeInference] = None
        self.models_info: Dict[str, ModelInfo] = {}
        self.start_time = time.time()
        self.ready = False
        self.mlflow_client: Optional[MlflowClient] = None

app_state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting Edge Inference Service")
    
    # Startup
    try:
        await startup_sequence()
        app_state.ready = True
        logger.info("✅ Service ready for requests")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Edge Inference Service")
    await shutdown_sequence()

# Create FastAPI app
app = FastAPI(
    title="Edge Inference Service",
    description="MLflow-integrated edge inference service for surveillance models",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def startup_sequence():
    """Initialize the inference service"""
    logger.info("Initializing MLflow client...")
    
    # Setup MLflow
    mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    mlflow.set_tracking_uri(mlflow_uri)
    app_state.mlflow_client = MlflowClient()
    
    logger.info(f"MLflow tracking URI: {mlflow_uri}")
    
    # Initialize inference engine
    logger.info("Initializing inference engine...")
    model_dir = os.getenv('MODEL_DIR', '/app/models')
    kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    
    app_state.inference_engine = EdgeInference(
        model_dir=model_dir,
        kafka_bootstrap_servers=kafka_servers
    )
    
    # Load model information
    await load_model_info()
    
    logger.info("Startup sequence completed")

async def shutdown_sequence():
    """Cleanup on shutdown"""
    if app_state.inference_engine and hasattr(app_state.inference_engine, 'kafka_producer'):
        if app_state.inference_engine.kafka_producer:
            app_state.inference_engine.kafka_producer.flush()

async def load_model_info():
    """Load model information from MLflow registry"""
    try:
        model_arch = os.getenv('MODEL_ARCHITECTURE', 'mobilenet_v3')
        model_name = f"surveillance_{model_arch}_edge"
        
        # Get model versions
        production_models = app_state.mlflow_client.get_latest_versions(
            model_name, stages=['Production']
        )
        staging_models = app_state.mlflow_client.get_latest_versions(
            model_name, stages=['Staging']
        )
        
        # Store model info
        for model_version in production_models + staging_models:
            app_state.models_info[f"{model_version.name}_{model_version.current_stage}"] = ModelInfo(
                name=model_version.name,
                version=model_version.version,
                stage=model_version.current_stage,
                architecture=model_arch,
                precision=os.getenv('TENSORRT_PRECISION', 'fp16'),
                last_updated=model_version.last_updated_timestamp
            )
            
            # Update Prometheus metrics
            model_info.labels(
                model_name=model_version.name,
                model_version=model_version.version,
                model_stage=model_version.current_stage,
                architecture=model_arch
            ).set(1)
        
        logger.info(f"Loaded info for {len(app_state.models_info)} models")
        
    except Exception as e:
        logger.warning(f"Could not load model info from MLflow: {e}")

def update_gpu_metrics():
    """Update GPU metrics"""
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            gpu_memory_usage.set(gpu.memoryUsed * 1024 * 1024)  # Convert to bytes
    except Exception as e:
        logger.debug(f"Could not update GPU metrics: {e}")

def decode_image(image_data: str) -> np.ndarray:
    """Decode base64 image data to numpy array"""
    import base64
    
    try:
        # Remove data URL prefix if present
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Decode base64
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        
        # Decode image
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Could not decode image")
        
        return image
    
    except Exception as e:
        raise ValueError(f"Image decoding failed: {e}")

def preprocess_image(image: np.ndarray, target_size: tuple = (224, 224)) -> np.ndarray:
    """Preprocess image for inference"""
    try:
        # Resize image
        resized = cv2.resize(image, target_size)
        
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize
        normalized = rgb_image.astype(np.float32) / 255.0
        
        # Convert to CHW format
        chw_image = np.transpose(normalized, (2, 0, 1))
        
        return chw_image
    
    except Exception as e:
        raise ValueError(f"Image preprocessing failed: {e}")

# API Endpoints

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check GPU availability
        gpu_available = False
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            gpu_available = len(gpus) > 0
        except:
            pass
        
        # Check memory usage
        import psutil
        memory = psutil.virtual_memory()
        
        update_gpu_metrics()
        
        return HealthResponse(
            status="healthy" if app_state.ready else "starting",
            timestamp=datetime.utcnow().isoformat(),
            version="1.0.0",
            models_loaded=app_state.inference_engine is not None,
            gpu_available=gpu_available,
            memory_usage={
                "used_percent": memory.percent,
                "available_gb": memory.available / (1024**3)
            },
            uptime_seconds=time.time() - app_state.start_time
        )
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    if not app_state.ready or not app_state.inference_engine:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {"status": "ready"}

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    update_gpu_metrics()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    """List available models"""
    return list(app_state.models_info.values())

@app.post("/reload-model")
async def reload_model(background_tasks: BackgroundTasks):
    """Reload model from MLflow registry"""
    background_tasks.add_task(load_model_info)
    return {"status": "reload_initiated"}

@app.post("/inference", response_model=InferenceResponse)
async def inference(request: InferenceRequest):
    """Run inference on uploaded image"""
    start_time = time.time()
    
    if not app_state.ready or not app_state.inference_engine:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    active_requests.inc()
    
    try:
        # Decode and preprocess image
        image = decode_image(request.image_data)
        preprocessed = preprocess_image(image)
        
        # Run inference
        with inference_duration_seconds.labels(
            endpoint="inference",
            model_type=request.model_type
        ).time():
            
            detections = app_state.inference_engine.infer_objects(
                input_tensor=preprocessed,
                camera_id=request.camera_id,
                frame_data=image
            )
        
        # Filter by confidence threshold
        filtered_detections = [
            {
                "class_name": det.class_name,
                "confidence": det.confidence,
                "bbox": {
                    "x": det.bbox.x,
                    "y": det.bbox.y,
                    "width": det.bbox.width,
                    "height": det.bbox.height
                }
            }
            for det in detections
            if det.confidence >= request.confidence_threshold
        ]
        
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Update metrics
        inference_requests_total.labels(
            endpoint="inference",
            model_type=request.model_type,
            status="success"
        ).inc()
        
        return InferenceResponse(
            detections=filtered_detections,
            processing_time_ms=processing_time,
            model_info={
                "architecture": os.getenv('MODEL_ARCHITECTURE', 'unknown'),
                "version": os.getenv('MODEL_VERSION', 'unknown'),
                "precision": os.getenv('TENSORRT_PRECISION', 'unknown')
            },
            camera_id=request.camera_id,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        inference_requests_total.labels(
            endpoint="inference",
            model_type=request.model_type,
            status="error"
        ).inc()
        
        logger.error(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        active_requests.dec()

@app.post("/inference/file")
async def inference_file(
    file: UploadFile = File(...),
    camera_id: Optional[str] = None,
    confidence_threshold: float = 0.5
):
    """Run inference on uploaded file"""
    try:
        # Read file
        contents = await file.read()
        
        # Convert to base64
        import base64
        image_data = base64.b64encode(contents).decode('utf-8')
        
        # Create request
        request = InferenceRequest(
            image_data=image_data,
            camera_id=camera_id,
            confidence_threshold=confidence_threshold
        )
        
        return await inference(request)
    
    except Exception as e:
        logger.error(f"File inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    try:
        import psutil
        
        # System stats
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # GPU stats
        gpu_stats = {}
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                gpu_stats = {
                    "name": gpu.name,
                    "load": gpu.load * 100,
                    "memory_used": gpu.memoryUsed,
                    "memory_total": gpu.memoryTotal,
                    "temperature": gpu.temperature
                }
        except:
            pass
        
        return {
            "uptime_seconds": time.time() - app_state.start_time,
            "models_loaded": len(app_state.models_info),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3)
            },
            "gpu": gpu_stats,
            "service": {
                "ready": app_state.ready,
                "model_architecture": os.getenv('MODEL_ARCHITECTURE', 'unknown'),
                "tensorrt_enabled": os.getenv('ENABLE_TENSORRT', 'false').lower() == 'true'
            }
        }
    
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Development endpoints
if os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true':
    
    @app.get("/debug/models")
    async def debug_models():
        """Debug endpoint to show model files"""
        model_dir = Path('/app/models')
        files = []
        
        if model_dir.exists():
            for file in model_dir.iterdir():
                if file.is_file():
                    files.append({
                        "name": file.name,
                        "size": file.stat().st_size,
                        "modified": file.stat().st_mtime
                    })
        
        return {
            "model_directory": str(model_dir),
            "files": files,
            "cache_directory": "/model-cache",
            "environment": {
                "MODEL_ARCHITECTURE": os.getenv('MODEL_ARCHITECTURE'),
                "MODEL_VERSION": os.getenv('MODEL_VERSION'),
                "MLFLOW_TRACKING_URI": os.getenv('MLFLOW_TRACKING_URI')
            }
        }

def main():
    """Main entry point"""
    # Configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8000'))
    workers = int(os.getenv('WORKERS', '1'))
    reload = os.getenv('RELOAD', 'false').lower() == 'true'
    
    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Workers: {workers}, Reload: {reload}")
    logger.info(f"Model: {os.getenv('MODEL_ARCHITECTURE', 'unknown')}")
    logger.info(f"MLflow URI: {os.getenv('MLFLOW_TRACKING_URI', 'unknown')}")
    
    # Run server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        workers=workers if not reload else 1,
        reload=reload,
        log_level=log_level.lower(),
        access_log=True
    )

if __name__ == "__main__":
    main()
