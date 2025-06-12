"""
Training Service: Scheduled retraining pipeline for continuous learning.
Consumes labeled examples, retrains models, and deploys updated TensorRT engines.
"""
import os
import json
import asyncio
import shutil
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import zipfile
import requests

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from confluent_kafka import Consumer, KafkaError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.middleware import add_rate_limiting

# Configure logging first
logger = configure_logging("training_service")

app = FastAPI(
    title="Training Service",
    openapi_prefix="/api/v1"
)

# Add audit middleware
add_audit_middleware(app, service_name="training_service")
instrument_app(app, service_name="training_service")

# Add rate limiting middleware
add_rate_limiting(app, service_name="training_service")

# Configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
LABELED_EXAMPLES_TOPIC = os.getenv("LABELED_EXAMPLES_TOPIC", "labeled.examples")
GROUP_ID = os.getenv("GROUP_ID", "training-service-group")

# Training configuration
MIN_EXAMPLES_FOR_TRAINING = int(os.getenv("MIN_EXAMPLES_FOR_TRAINING", "50"))
TRAINING_SCHEDULE = os.getenv("TRAINING_SCHEDULE", "0 2 * * *")  # Daily at 2 AM
MODEL_OUTPUT_DIR = os.getenv("MODEL_OUTPUT_DIR", "/models/output")
EDGE_SERVICE_URL = os.getenv("EDGE_SERVICE_URL", "http://edge_service:8000")
TRAINING_DATA_DIR = os.getenv("TRAINING_DATA_DIR", "/training_data")

# Global state
labeled_examples: List[dict] = []
consumer: Optional[Consumer] = None
scheduler: Optional[AsyncIOScheduler] = None
training_in_progress = False

# Models
class TrainingJob(BaseModel):
    job_id: str
    started_at: datetime
    status: str  # pending, running, completed, failed
    examples_count: int
    model_version: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None

training_jobs: Dict[str, TrainingJob] = {}

async def consume_labeled_examples():
    """Background task to consume labeled examples from Kafka."""
    global consumer, labeled_examples
    
    while True:
        try:
            if consumer is None:
                await asyncio.sleep(1)
                continue
                
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    logger.error("Kafka consumer error", error=str(msg.error()))
                continue
            
            # Parse labeled example
            try:
                raw_data = msg.value().decode("utf-8")
                example_data = json.loads(raw_data)
                
                labeled_examples.append(example_data)
                logger.info("Received labeled example", 
                           event_id=example_data.get("event_id"),
                           annotator_id=example_data.get("annotator_id"),
                           quality_score=example_data.get("quality_score"))
                
                # Save to persistent storage for training
                await save_labeled_example(example_data)
                
            except Exception as e:
                logger.error("Failed to parse labeled example", 
                           error=str(e), 
                           raw_data=raw_data[:200])
                
        except Exception as e:
            logger.error("Error in labeled examples consumer", error=str(e))
            await asyncio.sleep(1)

async def scheduled_training():
    """Scheduled training job triggered by cron."""
    global training_in_progress
    
    if training_in_progress:
        logger.warning("Training already in progress, skipping scheduled run")
        return
    
    available_examples = count_available_examples()
    
    if available_examples < MIN_EXAMPLES_FOR_TRAINING:
        logger.info("Insufficient examples for training", 
                   available=available_examples, 
                   required=MIN_EXAMPLES_FOR_TRAINING)
        return
    
    await start_training_job()

def count_available_examples() -> int:
    """Count available labeled examples for training."""
    try:
        if not os.path.exists(TRAINING_DATA_DIR):
            return 0
        
        json_files = list(Path(TRAINING_DATA_DIR).glob("*.json"))
        return len(json_files)
    except Exception as e:
        logger.error("Failed to count examples", error=str(e))
        return 0

async def start_training_job() -> str:
    """Start a new training job."""
    global training_in_progress
    
    if training_in_progress:
        raise HTTPException(status_code=409, detail="Training already in progress")
    
    job_id = f"train_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    examples_count = count_available_examples()
    
    job = TrainingJob(
        job_id=job_id,
        started_at=datetime.utcnow(),
        status="pending",
        examples_count=examples_count
    )
    training_jobs[job_id] = job
    
    # Start training in background
    asyncio.create_task(run_training_pipeline(job_id))
    
    logger.info("Started training job", 
               job_id=job_id, 
               examples_count=examples_count)
    
    return job_id

# ... rest of implementation
async def run_training_pipeline(job_id: str):
    """Run the complete training pipeline."""
    global training_in_progress
    
    training_in_progress = True
    job = training_jobs[job_id]
    
    try:
        job.status = "running"
        logger.info("Running training pipeline", job_id=job_id)
        
        # Simulate training steps
        await asyncio.sleep(10)  # Placeholder for actual training
        
        # Update job status
        job.status = "completed"
        job.model_version = f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        job.metrics = {"accuracy": 0.89, "f1_score": 0.87}
        
        logger.info("Training pipeline completed", job_id=job_id)
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        logger.error("Training pipeline failed", job_id=job_id, error=str(e))
    finally:
        training_in_progress = False

async def save_labeled_example(example: dict):
    """Save labeled example to persistent storage."""
    try:
        os.makedirs(TRAINING_DATA_DIR, exist_ok=True)
        
        event_id = example.get("event_id")
        file_path = os.path.join(TRAINING_DATA_DIR, f"{event_id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(example, f, indent=2, default=str)
            
        logger.debug("Saved labeled example", event_id=event_id)
        
    except Exception as e:
        logger.error("Failed to save labeled example", error=str(e))

@app.on_event("startup")
async def startup_event():
    global consumer, scheduler
    logger.info("Starting Training Service")
    
    # Initialize Kafka consumer
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True
    })
    consumer.subscribe([LABELED_EXAMPLES_TOPIC])
    
    # Start consumer task
    asyncio.create_task(consume_labeled_examples())
    
    # Initialize scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_training,
        CronTrigger.from_crontab(TRAINING_SCHEDULE),
        id="scheduled_training"
    )
    scheduler.start()
    
    logger.info("Training Service started")

@app.on_event("shutdown")
async def shutdown_event():
    if consumer:
        consumer.close()
    if scheduler:
        scheduler.shutdown()
    logger.info("Training Service shutdown complete")

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "training_service",
        "training_in_progress": training_in_progress,
        "available_examples": count_available_examples()    }

@app.get("/api/v1/jobs")
async def get_jobs():
    """Get list of training jobs."""
    jobs = list(training_jobs.values())
    jobs.sort(key=lambda x: x.started_at, reverse=True)
    return {"jobs": jobs[:20]}

@app.post("/api/v1/jobs/start")
async def start_training():
    """Manually start a training job."""
    try:
        job_id = await start_training_job()
        return {"job_id": job_id, "status": "started"}
    except Exception as e:        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/stats")
async def get_stats():
    """Get training statistics."""
    return {
        "available_examples": count_available_examples(),
        "min_examples_for_training": MIN_EXAMPLES_FOR_TRAINING,
        "training_in_progress": training_in_progress,
        "total_jobs": len(training_jobs),
        "training_schedule": TRAINING_SCHEDULE
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
