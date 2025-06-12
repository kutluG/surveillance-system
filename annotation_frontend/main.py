"""
Annotation Frontend Service: Web UI for human labeling of hard examples
from the continuous learning pipeline.
"""
import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import base64

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from confluent_kafka import Consumer, Producer, KafkaError
from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.middleware import add_rate_limiting

# Configure logging first
logger = configure_logging("annotation_frontend")

app = FastAPI(
    title="Annotation Frontend Service",
    openapi_prefix="/api/v1"
)

# Add audit middleware
add_audit_middleware(app, service_name="annotation_frontend")
instrument_app(app, service_name="annotation_frontend")

# Add rate limiting middleware
add_rate_limiting(app, service_name="annotation_frontend")

# Configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
HARD_EXAMPLES_TOPIC = os.getenv("HARD_EXAMPLES_TOPIC", "hard.examples")
LABELED_EXAMPLES_TOPIC = os.getenv("LABELED_EXAMPLES_TOPIC", "labeled.examples")
GROUP_ID = os.getenv("GROUP_ID", "annotation-frontend-group")

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
        "bootstrap.servers": KAFKA_BROKER,
        "client.id": "annotation-frontend"
    })
    
    # Initialize Kafka consumer for hard examples
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": GROUP_ID,
        "auto.offset.reset": "latest",  # Only get new examples
        "enable.auto.commit": True
    })
    consumer.subscribe([HARD_EXAMPLES_TOPIC])
    
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
    return templates.TemplateResponse("index.html", {
        "request": request,
        "pending_count": len(pending_examples)
    })

@app.get("/api/v1/examples", response_class=JSONResponse)
async def get_pending_examples():
    """Get list of pending hard examples for annotation."""
    return {
        "examples": pending_examples[-20:],  # Return last 20 examples
        "total": len(pending_examples)
    }

@app.get("/api/v1/examples/{event_id}", response_class=JSONResponse)
async def get_example(event_id: str):
    """Get specific hard example by event ID."""
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
    notes: Optional[str] = Form(None)
):
    """Submit corrected labels for a hard example."""
    
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
            LABELED_EXAMPLES_TOPIC,
            key=original_example["camera_id"],
            value=labeled_example.json(),
            callback=delivery_report
        )
        producer.poll(0)
        
        logger.info("Published labeled example", 
                   event_id=event_id,
                   annotator_id=annotator_id,
                   corrections_count=len(corrected_detections))
        
        return {"status": "success", "event_id": event_id}
        
    except Exception as e:
        logger.error("Failed to publish labeled example", 
                    event_id=event_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to save annotation")

@app.delete("/api/v1/examples/{event_id}")
async def skip_example(event_id: str):
    """Skip/reject a hard example without annotation."""
    
    for i, example in enumerate(pending_examples):
        if example.get("event_id") == event_id:
            pending_examples.pop(i)
            logger.info("Skipped hard example", event_id=event_id)
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
async def get_stats():
    """Get annotation statistics."""
    return {
        "pending_examples": len(pending_examples),
        "topics": {
            "input": HARD_EXAMPLES_TOPIC,
            "output": LABELED_EXAMPLES_TOPIC
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
