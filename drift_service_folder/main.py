"""
Drift Service: Continuously monitors Edge Inference logs, detects distribution 
drift in model confidence, and captures "hard examples" when confidence falls 
below a threshold.
"""
import os
import json
import asyncio
import statistics
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Deque
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("drift_service")

app = FastAPI(
    title="Model Drift Detection Service",
    openapi_prefix="/api/v1"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
DRIFT_WINDOW_SIZE = int(os.getenv("DRIFT_WINDOW_SIZE", "1000"))
DRIFT_THRESHOLD_SIGMA = float(os.getenv("DRIFT_THRESHOLD_SIGMA", "2.0"))
CONSUMER_GROUP_ID = os.getenv("CONSUMER_GROUP_ID", "drift-service-group")
INPUT_TOPIC = os.getenv("INPUT_TOPIC", "camera.detections")
OUTPUT_TOPIC = os.getenv("OUTPUT_TOPIC", "hard_examples")

# =============================================================================
# MODELS
# =============================================================================

class InferenceEvent(BaseModel):
    """Model for incoming inference events from Kafka."""
    camera_id: str = Field(..., description="Camera identifier")
    timestamp: str = Field(..., description="Event timestamp in ISO format")
    label: str = Field(..., description="Detected object label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")

class HardExample(BaseModel):
    """Model for hard examples to be published."""
    camera_id: str
    timestamp: str
    label: str
    confidence: float
    drift_detected: bool = True
    mean_confidence: float
    std_confidence: float
    deviation_sigma: float
    frame_url: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)

class DriftAlert(BaseModel):
    """Model for structured drift logging."""
    action: str = "drift_detected"
    label: str
    timestamp: str
    confidence: float
    mean: float
    std: float
    deviation_sigma: float
    camera_id: str

# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

# Counters
drift_events_total = Counter(
    'drift_events_total',
    'Total number of drift events detected',
    ['label', 'camera_id']
)

hard_examples_emitted_total = Counter(
    'hard_examples_emitted_total',
    'Total number of hard examples emitted to Kafka',
    ['label', 'camera_id']
)

processed_events_total = Counter(
    'processed_events_total',
    'Total number of inference events processed',
    ['label', 'camera_id']
)

# Histograms
confidence_distribution = Histogram(
    'confidence_distribution',
    'Distribution of confidence scores',
    ['label', 'camera_id'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

drift_deviation_histogram = Histogram(
    'drift_deviation_sigma',
    'Distribution of drift deviations in sigma units',
    ['label', 'camera_id'],
    buckets=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
)

# =============================================================================
# DRIFT DETECTION LOGIC
# =============================================================================

class DriftDetector:
    """
    Maintains rolling windows of confidence scores per label and detects
    statistical drift when new confidence scores deviate significantly.
    """
    
    def __init__(self, window_size: int = 1000, threshold_sigma: float = 2.0):
        self.window_size = window_size
        self.threshold_sigma = threshold_sigma
        # Rolling windows per label: label -> deque of confidence scores
        self.confidence_windows: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        # Statistics cache to avoid recalculation
        self._stats_cache: Dict[str, tuple] = {}
        self._cache_dirty: Dict[str, bool] = defaultdict(bool)
    
    def add_confidence(self, label: str, confidence: float) -> None:
        """Add a new confidence score to the rolling window for a label."""
        self.confidence_windows[label].append(confidence)
        self._cache_dirty[label] = True
    
    def get_statistics(self, label: str) -> tuple:
        """Get mean and standard deviation for a label's confidence window."""
        if label not in self.confidence_windows:
            return 0.0, 0.0
        
        window = self.confidence_windows[label]
        if len(window) < 2:
            return 0.0, 0.0
        
        # Use cache if available and not dirty
        if not self._cache_dirty.get(label, True) and label in self._stats_cache:
            return self._stats_cache[label]
        
        # Calculate statistics
        try:
            mean = statistics.mean(window)
            std = statistics.stdev(window) if len(window) > 1 else 0.0
            self._stats_cache[label] = (mean, std)
            self._cache_dirty[label] = False
            return mean, std
        except statistics.StatisticsError:
            return 0.0, 0.0
    
    def is_drift_detected(self, label: str, confidence: float) -> tuple:
        """
        Check if the given confidence represents drift for the label.
        Returns (is_drift, mean, std, deviation_sigma).
        """
        mean, std = self.get_statistics(label)
        
        # Need sufficient data and non-zero standard deviation
        if len(self.confidence_windows[label]) < 10 or std == 0:
            return False, mean, std, 0.0
        
        # Calculate how many standard deviations below the mean
        deviation = (mean - confidence) / std
        is_drift = deviation > self.threshold_sigma
        
        return is_drift, mean, std, deviation
    
    def get_window_info(self) -> Dict[str, Dict]:
        """Get information about all windows for monitoring."""
        info = {}
        for label, window in self.confidence_windows.items():
            mean, std = self.get_statistics(label)
            info[label] = {
                "count": len(window),
                "mean": round(mean, 4),
                "std": round(std, 4),
                "latest": window[-1] if window else None
            }
        return info

# =============================================================================
# GLOBAL STATE
# =============================================================================

drift_detector = DriftDetector(DRIFT_WINDOW_SIZE, DRIFT_THRESHOLD_SIGMA)
kafka_consumer: Optional[AIOKafkaConsumer] = None
kafka_producer: Optional[AIOKafkaProducer] = None

# =============================================================================
# KAFKA PROCESSING
# =============================================================================

async def process_inference_event(event_data: dict) -> None:
    """Process a single inference event and check for drift."""
    try:
        # Parse and validate the event
        event = InferenceEvent(**event_data)
        
        # Update metrics
        processed_events_total.labels(
            label=event.label,
            camera_id=event.camera_id
        ).inc()
        
        confidence_distribution.labels(
            label=event.label,
            camera_id=event.camera_id
        ).observe(event.confidence)
        
        # Check for drift before adding to window
        is_drift, mean, std, deviation_sigma = drift_detector.is_drift_detected(
            event.label, event.confidence
        )
        
        # Add confidence to rolling window for future calculations
        drift_detector.add_confidence(event.label, event.confidence)
        
        if is_drift:
            logger.info(f"Drift detected for {event.label}: confidence={event.confidence:.3f}, "
                       f"mean={mean:.3f}, std={std:.3f}, deviation={deviation_sigma:.2f}σ")
            
            # Update metrics
            drift_events_total.labels(
                label=event.label,
                camera_id=event.camera_id
            ).inc()
            
            drift_deviation_histogram.labels(
                label=event.label,
                camera_id=event.camera_id
            ).observe(deviation_sigma)
            
            # Create hard example
            hard_example = HardExample(
                camera_id=event.camera_id,
                timestamp=event.timestamp,
                label=event.label,
                confidence=event.confidence,
                mean_confidence=mean,
                std_confidence=std,
                deviation_sigma=deviation_sigma,
                metadata={
                    "drift_threshold_sigma": DRIFT_THRESHOLD_SIGMA,
                    "window_size": len(drift_detector.confidence_windows[event.label])
                }
            )
            
            # Publish to hard examples topic
            await publish_hard_example(hard_example)
            
            # Log structured drift alert
            drift_alert = DriftAlert(
                label=event.label,
                timestamp=event.timestamp,
                confidence=event.confidence,
                mean=mean,
                std=std,
                deviation_sigma=deviation_sigma,
                camera_id=event.camera_id
            )
            
            logger.warning(f"DRIFT_ALERT: {drift_alert.model_dump_json()}")
            
    except Exception as e:
        logger.error(f"Error processing inference event: {e}, data: {event_data}")

async def publish_hard_example(hard_example: HardExample) -> None:
    """Publish a hard example to the Kafka output topic."""
    try:
        if kafka_producer is None:
            logger.error("Kafka producer not initialized")
            return
        
        message = hard_example.model_dump_json().encode('utf-8')
        await kafka_producer.send_and_wait(OUTPUT_TOPIC, message)
        
        # Update metrics
        hard_examples_emitted_total.labels(
            label=hard_example.label,
            camera_id=hard_example.camera_id
        ).inc()
        
        logger.debug(f"Published hard example for {hard_example.label} to {OUTPUT_TOPIC}")
        
    except Exception as e:
        logger.error(f"Error publishing hard example: {e}")

async def kafka_consumer_loop() -> None:
    """Main Kafka consumer loop."""
    global kafka_consumer
    
    try:
        kafka_consumer = AIOKafkaConsumer(
            INPUT_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP_ID,
            auto_offset_reset='latest',  # Start from latest messages
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        await kafka_consumer.start()
        logger.info(f"Started Kafka consumer for topic '{INPUT_TOPIC}'")
        
        async for message in kafka_consumer:
            await process_inference_event(message.value)
            
    except Exception as e:
        logger.error(f"Error in Kafka consumer loop: {e}")
    finally:
        if kafka_consumer:
            await kafka_consumer.stop()

# =============================================================================
# FASTAPI ENDPOINTS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize Kafka producer and start consumer task."""
    global kafka_producer
    
    logger.info("Starting Drift Detection Service")
    
    # Initialize Kafka producer
    kafka_producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: v
    )
    await kafka_producer.start()
    
    # Start consumer task
    asyncio.create_task(kafka_consumer_loop())
    
    logger.info(f"Drift service started - monitoring topic '{INPUT_TOPIC}', "
               f"publishing to '{OUTPUT_TOPIC}', window_size={DRIFT_WINDOW_SIZE}, "
               f"threshold={DRIFT_THRESHOLD_SIGMA}σ")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up Kafka connections."""
    global kafka_consumer, kafka_producer
    
    if kafka_consumer:
        await kafka_consumer.stop()
    if kafka_producer:
        await kafka_producer.stop()
    
    logger.info("Drift Detection Service shutdown complete")

@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "drift_detection",
        "window_size": DRIFT_WINDOW_SIZE,
        "threshold_sigma": DRIFT_THRESHOLD_SIGMA,
        "kafka_config": {
            "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
            "input_topic": INPUT_TOPIC,
            "output_topic": OUTPUT_TOPIC
        }
    }

@app.get("/api/v1/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/v1/drift-stats")
async def get_drift_stats():
    """Get current drift detection statistics."""
    window_info = drift_detector.get_window_info()
    return {
        "window_size": DRIFT_WINDOW_SIZE,
        "threshold_sigma": DRIFT_THRESHOLD_SIGMA,
        "labels": window_info,
        "total_labels_tracked": len(window_info)
    }

@app.post("/api/v1/drift-config")
async def update_drift_config(threshold_sigma: float = None):
    """Update drift detection configuration at runtime."""
    global drift_detector
    
    if threshold_sigma is not None:
        if threshold_sigma <= 0:
            raise HTTPException(status_code=400, detail="threshold_sigma must be positive")
        drift_detector.threshold_sigma = threshold_sigma
        logger.info(f"Updated drift threshold to {threshold_sigma}σ")
    
    return {
        "window_size": drift_detector.window_size,
        "threshold_sigma": drift_detector.threshold_sigma
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
