"""
Edge AI Service: captures frames, runs inference, and publishes events via MQTT.
"""
import os
import cv2
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from shared.logging import get_logger
from shared.metrics import instrument_app
from shared.models import CameraEvent, EventType, Detection
from preprocessing import resize_letterbox, normalize_image
from inference import EdgeInference
from mqtt_client import MQTTClient
from shared.tracing import configure_tracing

LOGGER = get_logger("edge_service")

# Configure tracing before app initialization
configure_tracing("edge_service")

app = FastAPI(title="Edge AI Service")
instrument_app(app, service_name="edge_service")

# Configuration
CAMERA_ID = os.getenv("CAMERA_ID", "camera-01")
MODEL_DIR = os.getenv("MODEL_DIR", "/models")
TARGET_RESOLUTION = tuple(map(int, os.getenv("TARGET_RESOLUTION", "224,224").split(",")))
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
CAPTURE_DEVICE = int(os.getenv("CAPTURE_DEVICE", "0"))

# Initialize components
camera = None  # will be set in startup
engine: EdgeInference
mqtt_client: MQTTClient

@app.on_event("startup")
async def startup_event():
    global camera, engine, mqtt_client
    LOGGER.info("Starting Edge AI Service", camera_id=CAMERA_ID)
    
    # Try to open camera, but don't fail if it's not available (for testing)
    try:
        camera = cv2.VideoCapture(CAPTURE_DEVICE)
        if not camera.isOpened():
            LOGGER.warning("Camera not available - running in simulation mode", device=CAPTURE_DEVICE)
            camera = None
    except Exception as e:
        LOGGER.warning("Camera initialization failed - running in simulation mode", error=str(e))
        camera = None
    
    engine = EdgeInference(model_dir=MODEL_DIR)
    mqtt_client = MQTTClient(client_id=CAMERA_ID)

@app.on_event("shutdown")
async def shutdown_event():
    if camera and camera.isOpened():
        camera.release()
    mqtt_client.client.loop_stop()
    mqtt_client.client.disconnect()
    LOGGER.info("Edge AI Service shutdown complete")

async def process_frame():
    """
    Capture one frame, preprocess, infer, and publish event.
    """
    if camera is None:
        LOGGER.info("Camera not available - skipping frame processing")
        return
        
    ret, frame = camera.read()
    if not ret:
        LOGGER.warning("Failed to read frame from camera")
        return
    # Preprocess
    img = resize_letterbox(frame, TARGET_RESOLUTION)
    tensor = normalize_image(img, MEAN, STD)
    # Inference
    detections = engine.infer_objects(tensor)
    activity = engine.infer_activity(tensor)
    # Build event
    event = CameraEvent(
        camera_id=CAMERA_ID,
        event_type=EventType.DETECTION if detections else EventType.ACTIVITY,
        detections=detections or None,
        activity=activity if not detections else None,
    )
    # Publish
    topic = f"camera/events/{CAMERA_ID}"
    mqtt_client.publish_event(topic, event.dict())
    LOGGER.info("Published event", event_id=str(event.id))

@app.post("/capture")
async def capture_once(background: BackgroundTasks):
    """
    Trigger one frame capture and processing asynchronously.
    """
    background.add_task(process_frame)
    return {"status": "scheduled"}

@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    if camera and camera.isOpened():
        return {"status": "ok"}
    raise HTTPException(status_code=503, detail="Camera not available")

@app.post("/ota")
async def ota_update(model_url: str):
    """
    Over-the-air model update: download new engine files and reload.
    """
    # TODO: Download from model_url, verify, swap engine files, and reinstantiate EdgeInference.
    LOGGER.info("Received OTA update request", url=model_url)
    return {"status": "accepted", "next_steps": "update logic pending"}