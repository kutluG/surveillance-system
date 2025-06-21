"""
Annotation Frontend Service: Web UI for human labeling of hard examples
from the continuous learning pipeline.

Hardened backend with thread safety, persistence, validation, and resilience.
"""
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends, status, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from confluent_kafka import Consumer, Producer, KafkaError

from config import settings
from database import get_db, create_tables
from models import AnnotationExample, AnnotationStatus
from schemas import (
    AnnotationRequest, 
    AnnotationResponse, 
    ExampleResponse,
    ExampleListResponse
)
from services import AnnotationService
from kafka_retry import KafkaRetryService
from auth import get_current_user, require_scopes, TokenData
from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.middleware import add_rate_limiting

# Configure logging first
logger = configure_logging("annotation_frontend")

# Global services
annotation_service: Optional[AnnotationService] = None
kafka_retry_service: Optional[KafkaRetryService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global annotation_service, kafka_retry_service
    
    # Startup
    logger.info("Starting Annotation Frontend Service")
      # Initialize database
    create_tables()
    
    # Initialize services
    annotation_service = AnnotationService()
    kafka_retry_service = KafkaRetryService()
    
    # Start background tasks
    asyncio.create_task(consume_hard_examples())
    asyncio.create_task(kafka_retry_service.retry_failed_messages())
    
    logger.info("Annotation Frontend Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Annotation Frontend Service")
    if annotation_service:
        await annotation_service.cleanup()
    if kafka_retry_service:
        await kafka_retry_service.cleanup()
    logger.info("Annotation Frontend Service shutdown complete")

app = FastAPI(
    title="Annotation Frontend Service",
    description="Hardened backend for annotation with persistence and resilience",
    version="2.0.0",
    openapi_prefix="/api/v1",
    lifespan=lifespan
)

# Add audit middleware
add_audit_middleware(app, service_name="annotation_frontend")
instrument_app(app, service_name="annotation_frontend")

# Add rate limiting middleware
add_rate_limiting(app, service_name="annotation_frontend")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Models
class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class LabeledDetection(BaseModel):
    bbox: BoundingBox
    class_name: str
    confidence: float
    corrected_class: Optional[str] = None
    is_correct: bool = True

class LabeledExample(BaseModel):
    event_id: str
    camera_id: str
    timestamp: datetime
    frame_data: str
    original_detections: List[Dict]
    corrected_detections: List[LabeledDetection]
    annotator_id: str
    annotation_timestamp: datetime
    quality_score: float = 1.0
    notes: Optional[str] = None

# Global state for pending annotations
pending_examples: List[Dict] = []
producer: Optional[Producer] = None
consumer: Optional[Consumer] = None

def delivery_report(err, msg):
    """Callback for Kafka message delivery."""
    if err:
        logger.error("Labeled example delivery failed", error=str(err))
    else:
        logger.debug("Labeled example delivered", 
                    topic=msg.topic(), 
                    partition=msg.partition())

async def consume_hard_examples():
    """
    Background task to consume hard examples from Kafka.
    """
    global consumer, pending_examples
    
    while True:
        try:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    logger.error("Kafka consumer error", error=str(msg.error()))
                continue
            
            # Parse hard example
            try:
                raw_data = msg.value().decode("utf-8")
                hard_example = json.loads(raw_data)
                
                # Add to pending examples queue (keep last 100)
                pending_examples.append(hard_example)
                if len(pending_examples) > 100:
                    pending_examples.pop(0)
                
                logger.info("Received hard example for annotation", 
                           event_id=hard_example.get("event_id"))
                
            except Exception as e:
                logger.error("Failed to parse hard example", 
                           error=str(e), 
                           raw_data=raw_data[:200])
                
        except Exception as e:
            logger.error("Error in consume loop", error=str(e))
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    global producer, consumer
    logger.info("Starting Annotation Frontend Service")
    
    # Initialize Kafka producer for labeled examples
    producer = Producer({
        "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        "client.id": "annotation-frontend"
    })
    
    # Initialize Kafka consumer for hard examples
    consumer = Consumer({
        "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        "group.id": settings.KAFKA_GROUP_ID,
        "auto.offset.reset": "latest",  # Only get new examples
        "enable.auto.commit": True
    })
    consumer.subscribe([settings.HARD_EXAMPLES_TOPIC])
    
    # Start consumer task
    asyncio.create_task(consume_hard_examples())
    
    logger.info("Annotation Frontend Service started")

@app.on_event("shutdown")
async def shutdown_event():
    if consumer:
        consumer.close()
    if producer:
        producer.flush()
    logger.info("Annotation Frontend Service shutdown complete")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main annotation interface."""
    return templates.TemplateResponse("annotation.html", {
        "request": request,
        "pending_count": len(pending_examples),
        "config": settings
    })

@app.get("/api/v1/examples", response_class=JSONResponse)
async def get_pending_examples(current_user: TokenData = Depends(get_current_user)):
    """Get list of pending hard examples for annotation. Requires authentication."""
    logger.info("Fetching pending examples", user_id=current_user.sub)
    return {
        "examples": pending_examples[-settings.ANNOTATION_PAGE_SIZE:],  # Return configured page size
        "total": len(pending_examples)
    }

@app.get("/api/v1/examples/{event_id}", response_class=JSONResponse)
async def get_example(event_id: str, current_user: TokenData = Depends(get_current_user)):
    """Get specific hard example by event ID. Requires authentication."""
    logger.info("Fetching specific example", event_id=event_id, user_id=current_user.sub)
    for example in pending_examples:
        if example.get("event_id") == event_id:
            return example
    
    raise HTTPException(status_code=404, detail="Example not found")

@app.post("/api/v1/examples/{event_id}/label")
async def label_example(
    event_id: str,
    corrected_detections: List[LabeledDetection],
    annotator_id: str = Form(...),
    quality_score: float = Form(1.0),
    notes: Optional[str] = Form(None),
    current_user: TokenData = Depends(require_scopes("annotation:write"))
):
    """Submit corrected labels for a hard example. Requires 'annotation:write' scope."""    
    # Find the original example
    original_example = None
    for i, example in enumerate(pending_examples):
        if example.get("event_id") == event_id:
            original_example = example
            # Remove from pending queue
            pending_examples.pop(i)
            break
    
    if not original_example:
        raise HTTPException(status_code=404, detail="Example not found")
    
    # Create labeled example
    labeled_example = LabeledExample(
        event_id=event_id,
        camera_id=original_example["camera_id"],
        timestamp=datetime.fromisoformat(original_example["timestamp"].replace("Z", "+00:00")),
        frame_data=original_example["frame_data"],
        original_detections=original_example["detections"],
        corrected_detections=corrected_detections,
        annotator_id=annotator_id,
        annotation_timestamp=datetime.utcnow(),
        quality_score=quality_score,
        notes=notes
    )
      # Publish to labeled examples topic
    try:
        producer.produce(
            settings.LABELED_EXAMPLES_TOPIC,
            key=original_example["camera_id"],
            value=labeled_example.json(),
            callback=delivery_report
        )
        producer.poll(0)
        
        logger.info("Published labeled example", 
                   event_id=event_id,
                   annotator_id=annotator_id,
                   authenticated_user=current_user.sub,
                   corrections_count=len(corrected_detections))
        
        return {"status": "success", "event_id": event_id}
        
    except Exception as e:
        logger.error("Failed to publish labeled example", 
                    event_id=event_id, 
                    authenticated_user=current_user.sub,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to save annotation")

@app.delete("/api/v1/examples/{event_id}")
async def skip_example(event_id: str, current_user: TokenData = Depends(require_scopes("annotation:write"))):
    """Skip/reject a hard example without annotation. Requires 'annotation:write' scope."""
    
    for i, example in enumerate(pending_examples):
        if example.get("event_id") == event_id:
            pending_examples.pop(i)
            logger.info("Skipped hard example", event_id=event_id, user_id=current_user.sub)
            return {"status": "skipped", "event_id": event_id}
    
    raise HTTPException(status_code=404, detail="Example not found")

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "annotation_frontend",
        "pending_examples": len(pending_examples)
    }

@app.get("/api/v1/stats")
async def get_stats(current_user: TokenData = Depends(get_current_user)):
    """Get annotation statistics. Requires authentication."""
    logger.info("Fetching annotation stats", user_id=current_user.sub)
    return {
        "pending_examples": len(pending_examples),
        "topics": {
            "input": settings.HARD_EXAMPLES_TOPIC,
            "output": settings.LABELED_EXAMPLES_TOPIC
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
