"""
Event Ingest Service: consumes CameraEvent JSON from Kafka, validates,
persists to PostgreSQL, and upserts vector embeddings into Weaviate.
"""
import os
import json
import threading
from typing import Optional

from confluent_kafka import Consumer, KafkaError
from fastapi import FastAPI, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.models import CameraEvent
from shared.middleware import add_rate_limiting

from database import SessionLocal, engine
from models import Base, Event as DbEvent
from weaviate_client import client as weaviate_client, init_schema

# Configure logging first
logger = configure_logging("ingest_service")
app = FastAPI(
    title="Event Ingest Service",
    openapi_prefix="/api/v1"
)

# Add audit middleware
add_audit_middleware(app, service_name="ingest_service", use_camera_middleware=True)
instrument_app(app, service_name="ingest_service")

# Add rate limiting middleware
add_rate_limiting(app, service_name="ingest_service")

# Kafka configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "camera.events")
GROUP_ID = os.getenv("GROUP_ID", "ingest-service-group")

consumer: Optional[Consumer] = None

def save_to_db(event: CameraEvent):
    db = SessionLocal()
    try:
        db_event = DbEvent.from_camera_event(event)
        db.add(db_event)
        db.commit()
        logger.info("Event saved to database", extra={
            'action': 'save_to_db',
            'event_id': str(event.id),
            'camera_id': event.camera_id
        })
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("DB error inserting event", extra={
            'action': 'save_to_db_error',
            'event_id': str(event.id),
            'camera_id': event.camera_id,
            'error': str(e)
        })
    finally:
        db.close()

def compute_embedding(event: CameraEvent) -> list[float]:
    """
    Compute or retrieve vector embedding for the event.
    Placeholder returns zero-vector; replace with real embedding logic.
    """
    # TODO: call shared ML embedding function
    return [0.0] * 128

def upsert_to_weaviate(event: CameraEvent):
    # Ensure schema is initialized once
    init_schema()
    embedding = None
    if event.metadata and isinstance(event.metadata.get("embedding"), list):
        embedding = event.metadata["embedding"]
    else:
        embedding = compute_embedding(event)
    properties = {
        "event_id": str(event.id),
        "timestamp": event.timestamp.isoformat(),
        "camera_id": event.camera_id,
        "event_type": event.event_type.value,
    }
    # Upsert via batch for efficiency
    with weaviate_client.batch as batch:
        batch.add_data_object(properties, "CameraEvent", vector=embedding)

def consume_loop():
    """
    Poll Kafka for messages and process each event.
    """
    global consumer
    while True:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() != KafkaError._PARTITION_EOF:
                logger.error("Kafka error", extra={
                    'action': 'kafka_error',
                    'error': str(msg.error())
                })
            continue
        raw = msg.value().decode("utf-8")
        try:
            data = json.loads(raw)
            event = CameraEvent.parse_obj(data)
            
            with log_context(action="ingest_event", camera_id=event.camera_id, event_id=str(event.id)):
                save_to_db(event)
                upsert_to_weaviate(event)
                logger.info("Processed event successfully", extra={
                    'action': 'ingest_event',
                    'event_id': str(event.id),
                    'camera_id': event.camera_id,
                    'event_type': event.event_type.value
                })
        except Exception as e:
            logger.error("Failed to process message", extra={
                'action': 'ingest_event_error',
                'error': str(e),
                'payload': raw[:500]  # Truncate payload for logging
            })

@app.on_event("startup")
def startup_event():
    global consumer
    logger.info("Starting Event Ingest Service", extra={'action': 'service_startup'})
    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)
    # Initialize Kafka consumer
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([KAFKA_TOPIC])
    # Start background thread
    thread = threading.Thread(target=consume_loop, daemon=True)
    thread.start()
    logger.info("Kafka consumer initialized", extra={
        'action': 'kafka_consumer_init',
        'broker': KAFKA_BROKER,
        'topic': KAFKA_TOPIC,
        'group_id': GROUP_ID
    })

@app.on_event("shutdown")
def shutdown_event():
    if consumer:
        consumer.close()
    logger.info("Event Ingest Service shutdown complete", extra={'action': 'service_shutdown'})

@app.get("/health")
def health():
    """
    Health check endpoint.
    """
    if consumer is None:
        raise HTTPException(status_code=503, detail="consumer not initialized")
    logger.info("Health check performed", extra={'action': 'health_check'})
    return {"status": "ok"}

@app.post("/api/v1/ingest")
async def ingest_event(request: Request, event: CameraEvent):
    """
    Manual event ingestion endpoint for testing.
    """
    user_id = getattr(request.state, 'user_id', None)
    
    with log_context(action="manual_ingest", camera_id=event.camera_id, event_id=str(event.id), user_id=user_id):
        try:
            save_to_db(event)
            upsert_to_weaviate(event)
            
            logger.info("Manual event ingestion successful", extra={
                'action': 'manual_ingest',
                'event_id': str(event.id),
                'camera_id': event.camera_id,
                'user_id': user_id
            })
            
            return {"status": "success", "event_id": str(event.id)}
            
        except Exception as e:
            logger.error("Manual event ingestion failed", extra={
                'action': 'manual_ingest_error',
                'event_id': str(event.id),
                'camera_id': event.camera_id,
                'user_id': user_id,
                'error': str(e)
            })
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")