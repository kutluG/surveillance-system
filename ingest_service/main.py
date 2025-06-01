"""
Event Ingest Service: consumes CameraEvent JSON from Kafka, validates,
persists to PostgreSQL, and upserts vector embeddings into Weaviate.
"""
import os
import json
import threading
from typing import Optional

from confluent_kafka import Consumer, KafkaError
from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from shared.logging import get_logger
from shared.metrics import instrument_app
from shared.models import CameraEvent

from ingest_service.database import SessionLocal, engine
from ingest_service.models import Base, Event as DbEvent
from ingest_service.weaviate_client import client as weaviate_client, init_schema

LOGGER = get_logger("ingest_service")
app = FastAPI(title="Event Ingest Service")
instrument_app(app, service_name="ingest_service")

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
    except SQLAlchemyError as e:
        db.rollback()
        LOGGER.error("DB error inserting event", error=str(e))
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
                LOGGER.error("Kafka error", error=str(msg.error()))
            continue
        raw = msg.value().decode("utf-8")
        try:
            data = json.loads(raw)
            event = CameraEvent.parse_obj(data)
            save_to_db(event)
            upsert_to_weaviate(event)
            LOGGER.info("Processed event", event_id=str(event.id))
        except Exception as e:
            LOGGER.error("Failed to process message", error=str(e), payload=raw)

@app.on_event("startup")
def startup_event():
    global consumer
    LOGGER.info("Starting Event Ingest Service")
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

@app.on_event("shutdown")
def shutdown_event():
    if consumer:
        consumer.close()
    LOGGER.info("Event Ingest Service shutdown complete")

@app.get("/health")
def health():
    """
    Health check endpoint.
    """
    if consumer is None:
        raise HTTPException(status_code=503, detail="consumer not initialized")
    return {"status": "ok"}