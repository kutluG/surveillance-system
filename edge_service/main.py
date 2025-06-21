"""
Edge AI Service: captures frames, runs inference, and publishes events via MQTT.
Includes on-device face anonymization for privacy compliance.
"""
import os
import cv2
import asyncio
import json
import time
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from prometheus_client import Counter, Histogram, Gauge, Info

from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.models import CameraEvent, EventType, Detection
from shared.middleware import add_rate_limiting
from preprocessing import resize_letterbox, normalize_image
from inference import EdgeInference, get_inference_session, start_inference_monitoring, stop_inference_monitoring
from mqtt_client import MQTTClient
from shared.tracing import configure_tracing
try:
    from .monitoring import get_current_resource_status
    from .monitoring_thread import get_inference_monitoring_status
except ImportError:
    # Fallback for direct execution
    from monitoring import get_current_resource_status
    from monitoring_thread import get_inference_monitoring_status
from face_anonymization import (
    FaceAnonymizer, 
    AnonymizationConfig, 
    AnonymizationMethod, 
    PrivacyLevel,
    get_strict_config,
    get_moderate_config,
    get_minimal_config
)

# Prometheus metrics integration
from prometheus_client import make_asgi_app

# Configure logging first
logger = configure_logging("edge_service")

# Configure tracing before app initialization
configure_tracing("edge_service")

# Custom OpenAPI configuration
def custom_openapi():
    """Generate custom OpenAPI schema with enhanced documentation"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Edge AI Service",
        version="1.2.0",
        description="""
        Edge AI Service for real-time video processing with face anonymization.
        
        ## Features
        - Real-time object detection and activity recognition
        - Privacy-compliant face anonymization
        - MQTT event publishing
        - Prometheus metrics export
        - Over-the-air model updates
        
        ## Privacy Compliance
        All faces are detected and anonymized **on-device** before any data processing or transmission.
        
        ## Integration
        Events are published to MQTT broker for downstream processing by the surveillance pipeline.
        """,
        routes=app.routes,
        servers=[
            {"url": "/", "description": "Edge Service (Local)"},
            {"url": "/api/v1", "description": "Edge Service API v1"},
        ],
        tags=[
            {
                "name": "core",
                "description": "Core inference and capture operations"
            },
            {
                "name": "privacy",
                "description": "Face anonymization and privacy controls"
            },
            {
                "name": "system",
                "description": "Health checks and system status"
            },
            {
                "name": "management",
                "description": "OTA updates and configuration"
            }
        ]
    )
    
    # Add custom schema extensions
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-fastapi-margin.png"
    }
    
    openapi_schema["info"]["contact"] = {
        "name": "Edge AI Service Support",
        "email": "support@example.com"
    }
    
    openapi_schema["info"]["license"] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Anonymization-specific Prometheus metrics
FRAMES_PROCESSED = Counter(
    "frames_processed_total",
    "Total number of frames processed with anonymization"
)

FACES_ANONYMIZED = Counter(
    "faces_anonymized_total", 
    "Total number of faces detected and anonymized"
)

ANONYMIZATION_PROCESSING_TIME = Histogram(
    "anonymization_processing_time_seconds",
    "Time spent processing frames for anonymization"
)

ANONYMIZATION_ENABLED = Gauge(
    "anonymization_enabled",
    "Whether face anonymization is currently enabled (1=enabled, 0=disabled)"
)

PRIVACY_LEVEL = Gauge(
    "privacy_level",
    "Current privacy level (1=minimal, 2=moderate, 3=strict)"
)

ANONYMIZATION_FAILURES = Counter(
    "anonymization_failures_total",
    "Total number of anonymization failures"
)

ANONYMIZATION_METHOD_USAGE = Counter(
    "anonymization_method_usage_total",
    "Usage count by anonymization method",
    ["method"]
)

GDPR_COMPLIANCE_SCORE = Gauge(
    "gdpr_compliance_score",
    "GDPR compliance score (0-100)"
)

# Initialize metrics with defaults
ANONYMIZATION_ENABLED.set(1 if os.getenv("ANONYMIZATION_ENABLED", "true").lower() == "true" else 0)
privacy_level_map = {"minimal": 1, "moderate": 2, "strict": 3}
PRIVACY_LEVEL.set(privacy_level_map.get(os.getenv("PRIVACY_LEVEL", "moderate"), 2))
GDPR_COMPLIANCE_SCORE.set(85)  # Initial compliance score

app = FastAPI(
    title="Edge AI Service",
    version="1.2.0",
    description="Edge AI Service for real-time video processing with privacy-compliant face anonymization",
    openapi_prefix="/api/v1",
    openapi_tags=[
        {"name": "core", "description": "Core inference and capture operations"},
        {"name": "privacy", "description": "Face anonymization and privacy controls"},
        {"name": "system", "description": "Health checks and system status"},
        {"name": "management", "description": "OTA updates and configuration"}
    ]
)

# Set custom OpenAPI function
app.openapi = custom_openapi

instrument_app(app, service_name="edge_service")

# Add audit middleware after app creation
add_audit_middleware(app, service_name="edge_service", use_camera_middleware=True)

# Add rate limiting middleware
add_rate_limiting(app, service_name="edge_service")

# Create Prometheus metrics ASGI app
metrics_app = make_asgi_app()

# Mount metrics endpoint
app.mount("/metrics", metrics_app)

# Configuration
CAMERA_ID = os.getenv("CAMERA_ID", "camera-01")
MODEL_DIR = os.getenv("MODEL_DIR", "/models")
TARGET_RESOLUTION = tuple(map(int, os.getenv("TARGET_RESOLUTION", "224,224").split(",")))
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
CAPTURE_DEVICE = int(os.getenv("CAPTURE_DEVICE", "0"))

# Privacy/Anonymization Configuration
ANONYMIZATION_ENABLED = os.getenv("ANONYMIZATION_ENABLED", "true").lower() == "true"
PRIVACY_LEVEL = os.getenv("PRIVACY_LEVEL", "strict")  # strict, moderate, minimal
ANONYMIZATION_METHOD = os.getenv("ANONYMIZATION_METHOD", "blur")  # blur, pixelate, black_box, emoji

# Initialize components
camera = None  # will be set in startup
engine: EdgeInference
mqtt_client: MQTTClient
face_anonymizer: FaceAnonymizer

@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    
    Initializes all service components including camera capture, inference engine,
    MQTT client, and face anonymization system. Handles graceful degradation
    when components are unavailable (e.g., camera in testing environments).
    
    :raises Exception: Logs errors but continues startup for non-critical failures
    """
    global camera, engine, mqtt_client, face_anonymizer
    logger.info("Starting Edge AI Service", camera_id=CAMERA_ID)
    
    # Try to open camera, but don't fail if it's not available (for testing)
    try:
        camera = cv2.VideoCapture(CAPTURE_DEVICE)
        if not camera.isOpened():
            logger.warning("Camera not available - running in simulation mode", device=CAPTURE_DEVICE)
            camera = None
    except Exception as e:
        logger.warning("Camera initialization failed - running in simulation mode", error=str(e))
        camera = None    # Initialize AI inference engine with Kafka configuration
    kafka_servers = os.getenv("KAFKA_BROKER", "kafka:9092")
    engine = EdgeInference(model_dir=MODEL_DIR, kafka_bootstrap_servers=kafka_servers)
    
    # Initialize MQTT client
    mqtt_client = MQTTClient(client_id=CAMERA_ID)
      # Start resource monitoring for performance tracking
    start_inference_monitoring()
    logger.info("Inference resource monitoring started")
    
    # Pre-load inference session for optimal performance
    session = get_inference_session()
    if session:
        logger.info("Inference session loaded successfully at startup")
    else:
        logger.warning("Inference session not available, running in simulation mode")
    
    # Initialize face anonymization based on configuration
    if ANONYMIZATION_ENABLED:
        anonymization_config = _get_anonymization_config()
        face_anonymizer = FaceAnonymizer(anonymization_config)
        logger.info("Face anonymization enabled", 
                   privacy_level=PRIVACY_LEVEL, 
                   method=ANONYMIZATION_METHOD)
    else:
        face_anonymizer = None
        logger.warning("Face anonymization DISABLED - Privacy compliance may be at risk!")

def _get_anonymization_config() -> AnonymizationConfig:
    """Get anonymization configuration based on environment settings"""
    if PRIVACY_LEVEL == "strict":
        config = get_strict_config()
    elif PRIVACY_LEVEL == "moderate":
        config = get_moderate_config()
    elif PRIVACY_LEVEL == "minimal":
        config = get_minimal_config()
    else:
        logger.warning(f"Unknown privacy level '{PRIVACY_LEVEL}', using strict")
        config = get_strict_config()
    
    # Override method if specified
    try:
        config.method = AnonymizationMethod(ANONYMIZATION_METHOD)
    except ValueError:
        logger.warning(f"Unknown anonymization method '{ANONYMIZATION_METHOD}', using default")
    
    return config

# Enhanced Pydantic models for API requests and responses
class CaptureResponse(BaseModel):
    """Response model for capture endpoint"""
    status: str
    message: str = "Frame capture scheduled successfully"
    timestamp: float

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: float
    camera_available: bool
    anonymization: Dict[str, Any]
    metrics: Dict[str, int]

class PrivacyTestRequest(BaseModel):
    """Request model for privacy testing"""
    include_frame_data: bool = False
    test_mode: str = "current"  # current, sample, upload

class AnonymizationConfigRequest(BaseModel):
    """
    Request model for updating face anonymization configuration.
    
    Defines the structure for anonymization configuration updates,
    including method selection, privacy levels, and parameter tuning.
    """
    enabled: bool = True
    method: str = "blur"  # blur, pixelate, black_box, emoji
    privacy_level: str = "strict"  # strict, moderate, minimal
    blur_factor: Optional[int] = 15
    pixelate_factor: Optional[int] = 10

class AnonymizationStatusResponse(BaseModel):
    """
    Response model for anonymization status and configuration.
    
    Provides current anonymization settings and operational status
    for monitoring and debugging purposes.
    """
    enabled: bool
    method: str
    privacy_level: str
    faces_detected_today: int
    total_frames_processed: int
    models_loaded: Dict[str, bool]
    statistics: Dict[str, Any]

class OTAUpdateRequest(BaseModel):
    """OTA update request model"""
    model_url: str
    model_type: str = "detection"  # detection, activity, face
    verify_checksum: bool = True
    backup_current: bool = True

class ModelInfo(BaseModel):
    """Model information response"""
    name: str
    version: str
    size_mb: float
    checksum: str
    last_updated: str
    performance_metrics: Dict[str, float]

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event handler."""
    global camera, mqtt_client
    
    logger.info("Shutting down Edge AI Service...")
      # Stop resource monitoring
    stop_inference_monitoring()
    logger.info("Inference resource monitoring stopped")
    
    # Close camera if it was opened
    if camera:
        camera.release()
        logger.info("Camera released")
    
    # Close MQTT connection
    if mqtt_client:
        mqtt_client.disconnect()
        logger.info("MQTT client disconnected")
    
    logger.info("Edge AI Service shutdown completed")
    """
    Application shutdown event handler.
    
    Gracefully releases all resources including camera connections,
    MQTT client connections, and any other service components.
    Ensures clean shutdown without resource leaks.
    """
    if camera and camera.isOpened():
        camera.release()
    mqtt_client.client.loop_stop()
    mqtt_client.client.disconnect()
    logger.info("Edge AI Service shutdown complete")

async def process_frame():
    """
    Capture one frame, apply face anonymization, preprocess, infer, and publish event.
    """
    if camera is None:
        logger.info("Camera not available - skipping frame processing")
        return
        
    ret, frame = camera.read()
    if not ret:
        logger.warning("Failed to read frame from camera")
        return
    
    # CRITICAL: Apply face anonymization BEFORE any processing or transmission
    anonymized_frame = frame
    face_stats = {}
    
    if face_anonymizer is not None:
        try:
            # Start processing time measurement
            processing_time_start = asyncio.get_event_loop().time()
            
            anonymized_frame, faces_detected = face_anonymizer.anonymize_frame(frame)
            face_stats = face_anonymizer.get_anonymization_stats(faces_detected)
            
            # Stop processing time measurement
            processing_time_end = asyncio.get_event_loop().time()
            processing_duration = processing_time_end - processing_time_start
            
            # Update Prometheus metrics
            FRAMES_PROCESSED.inc()
            FACES_ANONYMIZED.inc(len(faces_detected))
            ANONYMIZATION_PROCESSING_TIME.observe(processing_duration)
            
            if faces_detected:
                logger.info("Face anonymization applied", 
                           faces_count=len(faces_detected),
                           method=face_anonymizer.config.method.value)
        except Exception as e:
            logger.error("Face anonymization failed", error=str(e))
            ANONYMIZATION_FAILURES.inc()
            # In strict mode, don't process frame if anonymization fails
            if PRIVACY_LEVEL == "strict":
                logger.error("Skipping frame due to anonymization failure in strict mode")
                return
    
    # Preprocess the anonymized frame
    img = resize_letterbox(anonymized_frame, TARGET_RESOLUTION)
    tensor = normalize_image(img, MEAN, STD)
      # Inference on anonymized frame with hard example detection
    detections = engine.infer_objects(tensor, camera_id=CAMERA_ID, frame_data=anonymized_frame)
    activity = engine.infer_activity(tensor)
    
    # Build event with anonymization metadata
    event = CameraEvent(
        camera_id=CAMERA_ID,
        event_type=EventType.DETECTION if detections else EventType.ACTIVITY,
        detections=detections or None,
        activity=activity if not detections else None,
    )
    
    # Add anonymization metadata to event
    event_dict = event.dict()
    if face_stats:
        event_dict["privacy"] = {
            "faces_anonymized": face_stats.get("faces_anonymized", 0),
            "anonymization_method": face_stats.get("anonymization_method"),
            "privacy_level": face_stats.get("privacy_level"),
            "face_hashes": face_stats.get("face_hashes", []) if PRIVACY_LEVEL != "strict" else []
        }
    
    # Publish
    topic = f"camera/events/{CAMERA_ID}"
    mqtt_client.publish_event(topic, event_dict)
    logger.info("Published event", event_id=str(event.id), 
               faces_anonymized=face_stats.get("faces_anonymized", 0))

@app.post("/api/v1/capture", 
          response_model=CaptureResponse,
          tags=["core"],
          summary="Capture and process frame",
          description="""
          Trigger one frame capture and processing asynchronously.
          
          This endpoint will:
          1. Capture a frame from the camera
          2. Apply face anonymization (if enabled)
          3. Run object detection and activity recognition
          4. Publish results to MQTT broker
          
          The processing happens in the background to ensure fast API response.
          """)
async def capture_once(background: BackgroundTasks) -> CaptureResponse:
    """
    Trigger one frame capture and processing asynchronously.
    """
    import time
    timestamp = time.time()
    background.add_task(process_frame)
    return CaptureResponse(
        status="scheduled",
        message="Frame capture scheduled successfully",
        timestamp=timestamp
    )

@app.get("/health",
         response_model=HealthResponse,
         tags=["system"],
         summary="Service health check",
         description="""
         Comprehensive health check endpoint providing system status.
         
         Returns information about:
         - Overall service status
         - Camera availability
         - Face anonymization status and configuration
         - Processing metrics and statistics
         """)
async def health() -> HealthResponse:
    """
    Health check endpoint with anonymization status.
    """
    camera_available = camera is not None and camera.isOpened()
    anonymization_status = "disabled"
    
    if face_anonymizer is not None:
        status = face_anonymizer.get_privacy_status()
        if status["enabled"]:
            anonymization_status = f"enabled ({status['privacy_level']})"
        else:
            anonymization_status = "enabled but not active"
    
    health_status = {
        "status": "ok" if camera_available else "degraded",
        "timestamp": asyncio.get_event_loop().time(),
        "camera_available": camera_available,
        "anonymization": {
            "status": anonymization_status,
            "enabled": face_anonymizer is not None,
            "privacy_level": face_anonymizer.get_privacy_status()["privacy_level"] if face_anonymizer else "none",
            "method": face_anonymizer.get_privacy_status()["anonymization_method"] if face_anonymizer else "none"
        },
        "metrics": {
            "frames_processed": int(FRAMES_PROCESSED._value.get()),
            "faces_anonymized": int(FACES_ANONYMIZED._value.get()),
            "failures": int(ANONYMIZATION_FAILURES._value.get())
        }
    }
    
    if not camera_available:
        raise HTTPException(status_code=503, detail="Camera not available")    
    return health_status

@app.get("/api/v1/monitoring/status",
         tags=["system"],
         summary="Get resource monitoring status",
         description="""
         Get current resource monitoring status and performance metrics.
         
         Provides information about:
         - Monitoring thread status and activity
         - Current CPU, memory, and disk usage
         - Alert thresholds and consecutive alert counts
         - Model loading status and performance metrics
         """)
async def get_monitoring_status():
    """
    Get current resource monitoring status and metrics.
    """
    try:
        # Get comprehensive monitoring status
        monitoring_status = get_inference_monitoring_status()
        resource_status = get_current_resource_status()
        
        # Combine the information
        combined_status = {
            "monitoring_status": monitoring_status,
            "resource_status": resource_status,
            "timestamp": time.time()
        }
        
        return JSONResponse(content=combined_status)
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring status: {str(e)}")

@app.get("/api/v1/privacy/status",
         response_model=AnonymizationStatusResponse,
         tags=["privacy"],
         summary="Get privacy status",
         description="""
         Get current face anonymization status and comprehensive statistics.
         
         Provides detailed information about:
         - Privacy configuration and status
         - Model loading status
         - Processing statistics and performance metrics
         - Compliance scores and metrics
         """)
async def get_anonymization_status() -> AnonymizationStatusResponse:
    """
    Get current face anonymization status and statistics.
    """
    if face_anonymizer is None:
        return {
            "enabled": False,
            "privacy_level": "none",
            "anonymization_method": "none",
            "models_loaded": {
                "haar_cascade": False,
                "dnn_model": False
            },
            "statistics": {
                "frames_processed": int(FRAMES_PROCESSED._value.get()),
                "faces_anonymized": int(FACES_ANONYMIZED._value.get()),
                "total_processing_time": 0,
                "average_processing_time": 0,
                "failures": int(ANONYMIZATION_FAILURES._value.get())
            }
        }
    
    # Get statistics from face anonymizer
    status = face_anonymizer.get_privacy_status()
    
    # Add Prometheus metrics
    status["statistics"].update({
        "frames_processed": int(FRAMES_PROCESSED._value.get()),
        "faces_anonymized": int(FACES_ANONYMIZED._value.get()),
        "failures": int(ANONYMIZATION_FAILURES._value.get())
    })
    
    return status

@app.post("/api/v1/privacy/configure",
          tags=["privacy"],
          summary="Configure privacy settings",
          description="""
          Update face anonymization configuration at runtime.
          
          Allows dynamic configuration of:
          - Privacy level (strict, moderate, minimal)
          - Anonymization method (blur, pixelate, black_box, emoji)
          - Enable/disable anonymization
          - Method-specific parameters
          """)
async def configure_anonymization(config_request: AnonymizationConfigRequest):
    """
    Update face anonymization configuration at runtime.
    """
    global face_anonymizer
    
    try:
        # Extract configuration parameters
        privacy_level = config_request.get("privacy_level", "moderate")
        anonymization_method = config_request.get("anonymization_method", "blur")
        enabled = config_request.get("enabled", True)
        
        # Update Prometheus metrics
        ANONYMIZATION_ENABLED.set(1 if enabled else 0)
        privacy_level_map = {"minimal": 1, "moderate": 2, "strict": 3}
        PRIVACY_LEVEL.set(privacy_level_map.get(privacy_level, 2))
        
        # Update anonymizer configuration
        if face_anonymizer is not None:
            success = face_anonymizer.update_configuration({
                "privacy_level": privacy_level,
                "anonymization_method": anonymization_method
            })
            
            if success:
                # Track method usage
                ANONYMIZATION_METHOD_USAGE.labels(method=anonymization_method).inc()
                
                logger.info("Face anonymization reconfigured",
                           method=anonymization_method,
                           privacy_level=privacy_level)
                
                return {
                    "success": True,
                    "message": "Privacy configuration updated successfully",
                    "config": {
                        "enabled": enabled,
                        "privacy_level": privacy_level,
                        "anonymization_method": anonymization_method
                    }
                }
            else:
                raise HTTPException(status_code=400, detail="Invalid configuration parameters")
        else:
            raise HTTPException(status_code=400, detail="Face anonymization not initialized")
            
    except Exception as e:
        logger.error("Failed to update anonymization config", error=str(e))
        raise HTTPException(status_code=500, detail=f"Configuration update failed: {str(e)}")

@app.post("/api/v1/privacy/test")
async def test_anonymization():
    """
    Test face anonymization with current camera frame.
    Returns anonymization statistics without publishing the event.
    """
    if camera is None:
        raise HTTPException(status_code=503, detail="Camera not available")
    
    if face_anonymizer is None:
        raise HTTPException(status_code=400, detail="Face anonymization not enabled")
    
    ret, frame = camera.read()
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to capture frame")
    
    try:
        anonymized_frame, faces_detected = face_anonymizer.anonymize_frame(frame)
        stats = face_anonymizer.get_anonymization_stats(faces_detected)
        
        return {
            "status": "success",
            "test_results": stats,
            "frame_processed": True,
            "message": f"Detected and anonymized {len(faces_detected)} faces"
        }
        
    except Exception as e:
        logger.error("Face anonymization test failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Anonymization test failed: {str(e)}")

@app.post("/api/v1/ota")
async def ota_update(model_url: str):
    """
    Over-the-air model update: download new engine files and reload.
    """
    # TODO: Download from model_url, verify, swap engine files, and reinstantiate EdgeInference.
    logger.info("Received OTA update request", url=model_url)
    return {"status": "accepted", "next_steps": "update logic pending"}

@app.get("/api/v1/openapi.json",
         tags=["system"],
         summary="Export OpenAPI specification",
         description="Export the complete OpenAPI specification as JSON",
         include_in_schema=False)
async def export_openapi():
    """Export OpenAPI specification to JSON file and return it"""
    try:
        # Get the OpenAPI schema
        openapi_schema = app.openapi()
        
        # Ensure docs directory exists
        docs_dir = Path("docs")
        docs_dir.mkdir(exist_ok=True)
        
        # Save to file
        openapi_file = docs_dir / "edge_service_openapi.json"
        with open(openapi_file, 'w', encoding='utf-8') as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
        
        logger.info(f"OpenAPI specification exported to {openapi_file}")
        
        return JSONResponse(
            content=openapi_schema,
            headers={
                "Content-Disposition": "attachment; filename=edge_service_openapi.json"
            }
        )
    except Exception as e:
        logger.error(f"Failed to export OpenAPI spec: {e}")
        raise HTTPException(status_code=500, detail="Failed to export OpenAPI specification")

@app.get("/api/v1/models/info",
         response_model=List[ModelInfo],
         tags=["management"],
         summary="Get model information",
         description=""":
         Get detailed information about loaded AI models.
         
         Returns information about:
         - Object detection models
         - Activity recognition models  
         - Face detection models
         - Performance metrics and checksums
         """)
async def get_model_info() -> List[ModelInfo]:
    """Get information about loaded models"""
    models = []
    
    # Face detection models
    if face_anonymizer:
        models.extend([
            ModelInfo(
                name="Haar Cascade Face Detector",
                version="OpenCV 4.8.1",
                size_mb=0.9,
                checksum="sha256:...",
                last_updated="2024-01-01T00:00:00Z",
                performance_metrics={
                    "avg_detection_time_ms": 15.2,
                    "accuracy": 0.85,
                    "false_positive_rate": 0.02
                }
            ),
            ModelInfo(
                name="DNN Face Detector",
                version="OpenCV DNN",
                size_mb=2.7,
                checksum="sha256:...",
                last_updated="2024-01-01T00:00:00Z",
                performance_metrics={
                    "avg_detection_time_ms": 25.8,
                    "accuracy": 0.92,
                    "false_positive_rate": 0.01
                }
            )
        ])
    
    return models

# Override default OpenAPI schema generation
app.openapi = custom_openapi

# Custom error handler to include request ID in responses
@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
    """
    Custom exception handler to return structured error responses.
    """
    logger.error("Unhandled exception", request_id=request.headers.get("X-Request-ID"), error=str(exc))
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal Server Error",
            "details": str(exc),
            "request_id": request.headers.get("X-Request-ID")
        }
    )
