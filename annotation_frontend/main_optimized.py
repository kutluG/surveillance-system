"""
Annotation Frontend Service: Web UI for human labeling of hard examples
from the continuous learning pipeline.

Scalable backend with Redis retry queue, Kafka pooling, and static asset caching.
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends, status, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import get_db, create_tables
from models import AnnotationExample, AnnotationStatus
from schemas import (
    AnnotationRequest, 
    AnnotationResponse, 
    ExampleResponse,
    ExampleListResponse,
    HealthResponse,
    StatsResponse
)
from services import AnnotationService
from auth import get_current_user, require_scopes, TokenData
from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.middleware import add_rate_limiting
from kafka_pool import kafka_pool
from redis_service import redis_retry_service
from background_tasks import background_retry_task

# Configure logging first
logger = configure_logging("annotation_frontend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    
    # Startup
    logger.info("Starting Annotation Frontend Service")
    
    # Initialize database
    create_tables()
    
    # Initialize Kafka connection pool
    await kafka_pool.initialize()
    app.state.kafka_pool = kafka_pool
    
    # Initialize Redis retry service
    await redis_retry_service.initialize()
    app.state.redis_retry_service = redis_retry_service
    
    # Start background tasks
    asyncio.create_task(consume_hard_examples())
    await background_retry_task.start()
    
    logger.info("Annotation Frontend Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Annotation Frontend Service")
    
    # Stop background tasks
    await background_retry_task.stop()
    
    # Close connections
    await kafka_pool.close()
    await redis_retry_service.close()
    
    logger.info("Annotation Frontend Service shutdown complete")

app = FastAPI(
    title="Annotation Frontend Service",
    description="Scalable backend for annotation with Redis retry queue and Kafka pooling",
    version="2.1.0",
    openapi_prefix="/api/v1",
    lifespan=lifespan
)

# Add audit middleware
add_audit_middleware(app, service_name="annotation_frontend")
instrument_app(app, service_name="annotation_frontend")

# Add rate limiting middleware
add_rate_limiting(app, service_name="annotation_frontend")

# Setup templates and static files with caching
templates = Jinja2Templates(directory="templates")

# Configure static files with caching headers
class CachedStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        # Add cache control headers for static assets
        response.headers["Cache-Control"] = f"public, max-age={settings.STATIC_CACHE_MAX_AGE}"
        response.headers["ETag"] = f'"{hash(response.body)}"'
        return response

app.mount("/static", CachedStaticFiles(
    directory="static",
    html=True,
    check_dir=True
), name="static")

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

async def consume_hard_examples():
    """
    Background task to consume hard examples from Kafka using connection pool.
    """
    logger.info("Starting hard examples consumer")
    
    async def process_message(topic: str, message: str, key: Optional[str]):
        """Process individual Kafka message."""
        try:
            data = json.loads(message)
            logger.debug(f"Received hard example: {data.get('event_id')}")
            
            # Store in database using annotation service
            db_gen = get_db()
            db = next(db_gen)
            try:
                example = AnnotationService.create_example_from_kafka(data, db)
                logger.info(f"Stored hard example: {example.example_id}")
            finally:
                db.close()
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Kafka message: {e}")
        except Exception as e:
            logger.error(f"Error processing hard example: {e}")
    
    # Consume messages continuously
    while True:
        try:
            await kafka_pool.consume_messages(process_message, timeout_ms=5000)
            await asyncio.sleep(1)  # Brief pause between polling
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
            await asyncio.sleep(5)  # Wait before retrying

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    """Main annotation interface."""
    pending_count = db.query(AnnotationExample).filter(
        AnnotationExample.status == AnnotationStatus.PENDING
    ).count()
    
    return templates.TemplateResponse("annotation.html", {
        "request": request,
        "pending_count": pending_count,
        "config": settings
    })

@app.get("/api/v1/examples", response_model=ExampleListResponse)
async def get_pending_examples(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(settings.ANNOTATION_PAGE_SIZE, ge=1, le=100, description="Page size"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of pending hard examples for annotation with pagination. Requires authentication."""
    logger.info(f"Fetching pending examples (page={page}, size={size})", user_id=current_user.sub)
    
    try:
        result = AnnotationService.get_pending_examples(db, page=page, page_size=size)
        return result
    except Exception as e:
        logger.error(f"Failed to get pending examples: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve examples"
        )

@app.get("/api/v1/examples/{event_id}", response_model=ExampleResponse)
async def get_example(
    event_id: str, 
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific hard example by event ID. Requires authentication."""
    logger.info(f"Fetching specific example: {event_id}", user_id=current_user.sub)
    
    try:
        example = AnnotationService.get_example_by_id(db, event_id)
        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Example not found"
            )
        return ExampleResponse.from_orm(example)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get example {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve example"
        )

@app.post("/api/v1/examples/{event_id}/label", response_model=AnnotationResponse)
async def label_example(
    event_id: str,
    request: AnnotationRequest,
    current_user: TokenData = Depends(require_scopes("annotation:write")),
    db: Session = Depends(get_db)
):
    """Submit corrected labels for a hard example. Requires 'annotation:write' scope."""
    logger.info(f"Submitting annotation for example: {event_id}", user_id=current_user.sub)
    
    try:
        # Submit annotation
        example = AnnotationService.submit_annotation(db, request)
        
        # Create labeled example for Kafka
        labeled_example = LabeledExample(
            event_id=event_id,
            camera_id=example.camera_id,
            timestamp=example.timestamp,
            frame_data=example.frame_data or "",
            original_detections=example.original_detections or [],
            corrected_detections=[],  # Would be populated from request
            annotator_id=request.annotator_id,
            annotation_timestamp=datetime.utcnow(),
            quality_score=request.quality_score,
            notes=request.notes
        )
        
        # Publish to labeled examples topic using Kafka pool
        message = json.dumps({
            "event_id": labeled_example.event_id,
            "camera_id": labeled_example.camera_id,
            "timestamp": labeled_example.timestamp.isoformat(),
            "frame_data": labeled_example.frame_data,
            "original_detections": labeled_example.original_detections,
            "corrected_detections": [d.dict() for d in labeled_example.corrected_detections],
            "annotator_id": labeled_example.annotator_id,
            "annotation_timestamp": labeled_example.annotation_timestamp.isoformat(),
            "quality_score": labeled_example.quality_score,
            "notes": labeled_example.notes
        })
        
        success = await kafka_pool.send_message(
            topic=settings.LABELED_EXAMPLES_TOPIC,
            message=message,
            key=event_id
        )
        
        if not success:
            # Add to Redis retry queue
            await redis_retry_service.add_retry_item(
                example_id=event_id,
                topic=settings.LABELED_EXAMPLES_TOPIC,
                payload=message,
                key=event_id,
                error_message="Initial send failed"
            )
            logger.warning(f"Failed to send labeled example, added to retry queue: {event_id}")
        
        return AnnotationResponse(
            status="success",
            example_id=event_id,
            message="Annotation submitted successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to submit annotation for {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit annotation"
        )

@app.delete("/api/v1/examples/{event_id}", response_model=AnnotationResponse)
async def skip_example(
    event_id: str,
    current_user: TokenData = Depends(require_scopes("annotation:write")),
    db: Session = Depends(get_db)
):
    """Skip an annotation example. Requires 'annotation:write' scope."""
    logger.info(f"Skipping example: {event_id}", user_id=current_user.sub)
    
    try:
        example = AnnotationService.skip_example(db, event_id)
        
        return AnnotationResponse(
            status="success",
            example_id=event_id,
            message="Example skipped successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to skip example {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to skip example"
        )

@app.get("/health", response_model=HealthResponse)
async def health(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Check database connection
        db_connected = True
        try:
            db.execute("SELECT 1")
        except Exception:
            db_connected = False
        
        # Check Kafka connection
        kafka_connected = kafka_pool._initialized
        
        # Get pending examples count
        pending_count = 0
        if db_connected:
            pending_count = db.query(AnnotationExample).filter(
                AnnotationExample.status == AnnotationStatus.PENDING
            ).count()
        
        return HealthResponse(
            status="healthy" if db_connected and kafka_connected else "unhealthy",
            service="annotation_frontend",
            database_connected=db_connected,
            kafka_connected=kafka_connected,
            pending_examples=pending_count
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            service="annotation_frontend",
            database_connected=False,
            kafka_connected=False,
            pending_examples=0
        )

@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get service statistics. Requires authentication."""
    logger.info("Fetching service statistics", user_id=current_user.sub)
    
    try:
        stats = AnnotationService.get_statistics(db)
        
        # Add Redis retry queue size
        retry_queue_size = await redis_retry_service.get_queue_size()
        
        return StatsResponse(
            pending_examples=stats.get("pending_examples", 0),
            completed_examples=stats.get("completed_examples", 0),
            retry_queue_size=retry_queue_size,
            topics={
                "hard_examples": settings.HARD_EXAMPLES_TOPIC,
                "labeled_examples": settings.LABELED_EXAMPLES_TOPIC
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
