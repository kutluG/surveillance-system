"""
Hard Example Collector Service: Identifies and publishes low-confidence frames 
for continuous learning pipeline.
"""
import os
import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import base64

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from confluent_kafka import Producer, Consumer, KafkaError
from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.models import CameraEvent, Detection
from shared.middleware import add_rate_limiting

# Configure logging first
logger = configure_logging("hard_example_collector")

app = FastAPI(
    title="Hard Example Collector Service",
    openapi_prefix="/api/v1"
)

# Add audit middleware
add_audit_middleware(app, service_name="hard_example_collector")
instrument_app(app, service_name="hard_example_collector")

# Add rate limiting middleware
add_rate_limiting(app, service_name="hard_example_collector")

# Configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
INPUT_TOPIC = os.getenv("INPUT_TOPIC", "camera.events")
HARD_EXAMPLES_TOPIC = os.getenv("HARD_EXAMPLES_TOPIC", "hard.examples")
GROUP_ID = os.getenv("GROUP_ID", "hard-example-collector-group")

# Confidence thresholds for different detection types
CONFIDENCE_THRESHOLDS = {
    "face": float(os.getenv("FACE_CONFIDENCE_THRESHOLD", "0.5")),
    "person": float(os.getenv("PERSON_CONFIDENCE_THRESHOLD", "0.6")),
    "vehicle": float(os.getenv("VEHICLE_CONFIDENCE_THRESHOLD", "0.4")),
    "default": float(os.getenv("DEFAULT_CONFIDENCE_THRESHOLD", "0.5"))
}

# Model for hard example metadata
class HardExample(BaseModel):
    event_id: str
    camera_id: str
    timestamp: datetime
    frame_data: str  # base64 encoded frame
    detections: list  # Low confidence detections
    confidence_scores: Dict[str, float]
    reason: str  # Why this is a hard example
    anonymized: bool = True

producer: Optional[Producer] = None
consumer: Optional[Consumer] = None

def is_hard_example(event: CameraEvent) -> tuple[bool, str, Dict[str, float]]:
    """
    Determine if an event contains hard examples based on confidence thresholds.
    
    Args:
        event: CameraEvent to analyze
        
    Returns:
        (is_hard, reason, confidence_scores)
    """
    if not event.detections:
        return False, "", {}
    
    confidence_scores = {}
    hard_detections = []
    
    for detection in event.detections:
        # Get appropriate threshold for detection class
        threshold = CONFIDENCE_THRESHOLDS.get(
            detection.class_name.lower(), 
            CONFIDENCE_THRESHOLDS["default"]
        )
        
        confidence_scores[detection.class_name] = detection.confidence
        
        # Check if confidence is below threshold
        if detection.confidence < threshold:
            hard_detections.append(detection)
    
    if hard_detections:
        reason = f"Low confidence detections: {[d.class_name for d in hard_detections]}"
        return True, reason, confidence_scores
    
    return False, "", confidence_scores

def create_hard_example(event: CameraEvent, reason: str, confidence_scores: Dict[str, float]) -> HardExample:
    """
    Create a HardExample from a CameraEvent.
    """
    # For now, we'll use placeholder frame data since we don't have actual frame in event
    # In a real implementation, you'd get the frame from the camera or a frame buffer
    frame_data = "placeholder_frame_data"  # This should be base64 encoded frame
    
    return HardExample(
        event_id=str(event.id),
        camera_id=event.camera_id,
        timestamp=event.timestamp,
        frame_data=frame_data,
        detections=[det.dict() for det in event.detections or []],
        confidence_scores=confidence_scores,
        reason=reason,
        anonymized=True  # Assume frames are already anonymized from edge service
    )

async def process_event(event: CameraEvent):
    """
    Process a camera event and publish to hard examples topic if needed.
    """
    is_hard, reason, confidence_scores = is_hard_example(event)
    
    if is_hard:
        hard_example = create_hard_example(event, reason, confidence_scores)
        
        # Publish to Kafka hard examples topic
        try:
            producer.produce(
                HARD_EXAMPLES_TOPIC,
                key=event.camera_id,
                value=hard_example.json(),
                callback=delivery_report
            )
            producer.poll(0)
            
            logger.info("Published hard example", 
                       event_id=str(event.id),
                       camera_id=event.camera_id,
                       reason=reason,
                       confidence_scores=confidence_scores)
        except Exception as e:
            logger.error("Failed to publish hard example", 
                        event_id=str(event.id), 
                        error=str(e))

def delivery_report(err, msg):
    """Callback for Kafka message delivery."""
    if err:
        logger.error("Hard example delivery failed", error=str(err))
    else:
        logger.debug("Hard example delivered", 
                    topic=msg.topic(), 
                    partition=msg.partition())

def consume_loop():
    """
    Main consumer loop to process camera events.
    """
    global consumer
    while True:
        try:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    logger.error("Kafka consumer error", error=str(msg.error()))
                continue
            
            # Parse camera event
            try:
                raw_data = msg.value().decode("utf-8")
                event_data = json.loads(raw_data)
                event = CameraEvent.parse_obj(event_data)
                
                # Process event asynchronously
                asyncio.create_task(process_event(event))
                
            except Exception as e:
                logger.error("Failed to parse camera event", 
                           error=str(e), 
                           raw_data=raw_data[:200])
                
        except Exception as e:
            logger.error("Error in consume loop", error=str(e))
            import time
            time.sleep(1)

@app.on_event("startup")
async def startup_event():
    global producer, consumer
    logger.info("Starting Hard Example Collector Service")
    
    # Initialize Kafka producer
    producer = Producer({
        "bootstrap.servers": KAFKA_BROKER,
        "client.id": "hard-example-collector"
    })
    
    # Initialize Kafka consumer
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True
    })
    consumer.subscribe([INPUT_TOPIC])
    
    # Start consumer loop in background task
    asyncio.create_task(asyncio.to_thread(consume_loop))
    
    logger.info("Hard Example Collector Service started")

@app.on_event("shutdown")
async def shutdown_event():
    if consumer:
        consumer.close()
    if producer:
        producer.flush()
    logger.info("Hard Example Collector Service shutdown complete")

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "hard_example_collector",
        "thresholds": CONFIDENCE_THRESHOLDS
    }

@app.get("/api/v1/stats")
async def get_stats():
    """Get statistics about hard example collection."""
    # In a real implementation, you'd track metrics
    return {
        "thresholds": CONFIDENCE_THRESHOLDS,
        "topics": {
            "input": INPUT_TOPIC,
            "output": HARD_EXAMPLES_TOPIC
        }
    }

@app.post("/api/v1/thresholds")
async def update_thresholds(thresholds: Dict[str, float]):
    """Update confidence thresholds at runtime."""
    global CONFIDENCE_THRESHOLDS
    
    for key, value in thresholds.items():
        if key in CONFIDENCE_THRESHOLDS:
            CONFIDENCE_THRESHOLDS[key] = value
    
    logger.info("Updated confidence thresholds", thresholds=CONFIDENCE_THRESHOLDS)
    return {"status": "updated", "thresholds": CONFIDENCE_THRESHOLDS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
