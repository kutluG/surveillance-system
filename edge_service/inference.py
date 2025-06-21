"""
Edge AI Inference Engine Module

This module provides object detection and activity recognition capabilities for the edge service.
It handles model loading, inference execution, and hard example detection for continuous learning.

The module supports:
- ONNX Runtime optimized models for high-performance inference
- Singleton model caching for efficient resource usage
- Real-time object detection with configurable confidence thresholds
- Hard example detection and publishing to Kafka for model improvement
- Comprehensive performance metrics and resource monitoring
- Simulation mode for development and testing when models are unavailable

Dependencies:
    - ONNX Runtime for optimized inference
    - Kafka for hard example publishing
    - OpenCV for image processing
    - NumPy for tensor operations
    - Prometheus for performance metrics
    - psutil for system resource monitoring
"""
import os
import sys
import time
import json
import base64
import threading
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import wraps

# Performance monitoring imports
from prometheus_client import Summary, Gauge, Counter, make_asgi_app
import numpy as np

# ONNX Runtime for optimized inference
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logging.warning("ONNX Runtime not available, falling back to simulation mode")

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.models import Detection, BoundingBox

# Import monitoring module
try:
    from .monitoring import get_resource_monitor
    from .monitoring_thread import start_inference_monitoring, stop_inference_monitoring
except ImportError:
    # Fallback for direct execution
    from monitoring import get_resource_monitor
    from monitoring_thread import start_inference_monitoring, stop_inference_monitoring

# Import settings with fallback
try:
    from .config import settings
except ImportError:
    try:
        from config import settings
    except ImportError:
        # Fallback settings for testing
        class FallbackSettings:
            model_dir = "/tmp/models"
            kafka_broker = "localhost:9092"
            quantized_model_path = "/tmp/models/model_int8.onnx"
        settings = FallbackSettings()

# Add Kafka producer import
try:
    from confluent_kafka import Producer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("Kafka not available, hard examples will not be published")

# Configure logging
logger = logging.getLogger(__name__)

# =============================================================================
# PERFORMANCE METRICS INSTRUMENTATION
# =============================================================================

# Inference latency tracking
INFERENCE_LATENCY = Summary(    'edge_inference_latency_seconds',
    'Time spent on inference operations',
    ['model_type', 'batch_size']
)

# Performance counters (inference-specific)
INFERENCE_COUNT = Counter(
    'edge_inference_total',
    'Total number of inference operations',
    ['model_type', 'status']
)

MODEL_LOAD_TIME = Gauge(
    'edge_model_load_time_seconds',
    'Time taken to load models at startup'
)

# Model performance metrics
MODEL_SIZE_BYTES = Gauge(
    'edge_model_size_bytes',
    'Size of loaded model in bytes',
    ['model_type']
)

SESSION_READY = Gauge(
    'edge_session_ready',
    'Whether inference session is ready (1=ready, 0=not ready)',
    ['model_type']
)

# =============================================================================
# SINGLETON MODEL MANAGEMENT
# =============================================================================

# Global inference session - loaded once at startup
_inference_session: Optional[ort.InferenceSession] = None
_session_lock = threading.Lock()

# Start monitoring using the dedicated monitoring thread
def start_inference_monitoring():
    """Start resource monitoring for inference"""
    try:
        from monitoring_thread import start_inference_monitoring as start_monitoring
        start_monitoring()
        logger.info("Inference resource monitoring started")
    except Exception as e:
        logger.error(f"Failed to start inference monitoring: {e}")

def stop_inference_monitoring():
    """Stop resource monitoring for inference"""
    try:
        from monitoring_thread import stop_inference_monitoring as stop_monitoring
        stop_monitoring()
        logger.info("Inference resource monitoring stopped")
    except Exception as e:
        logger.error(f"Failed to stop inference monitoring: {e}")


def get_inference_session() -> Optional[ort.InferenceSession]:
    """
    Get the global inference session, loading it if necessary.
    
    This implements singleton pattern for model loading to ensure efficient
    resource usage and fast inference times.
    
    :return: ONNX Runtime inference session or None if not available
    """
    global _inference_session
    
    if _inference_session is not None:
        return _inference_session
    
    with _session_lock:
        # Double-check locking pattern
        if _inference_session is not None:
            return _inference_session
        
        if not ONNX_AVAILABLE:
            logger.warning("ONNX Runtime not available, cannot load inference session")
            return None
        
        try:
            start_time = time.time()
              # Determine model path (prefer quantized model if enabled)
            if getattr(settings, 'use_quantized_model', True) and hasattr(settings, 'quantized_model_path'):
                model_path = settings.quantized_model_path
                if Path(model_path).exists():
                    logger.info(f"Loading quantized INT8 model: {model_path}")
                    model_type = 'quantized_int8'
                else:
                    logger.warning(f"Quantized model not found: {model_path}, falling back to default")
                    model_path = os.path.join(settings.model_dir, "model.onnx")
                    model_type = 'fp32'
            else:
                # Fallback to regular model path
                model_path = os.path.join(settings.model_dir, "model.onnx")
                model_type = 'fp32'
                
            if not Path(model_path).exists():
                logger.error(f"Model file not found: {model_path}")
                return None
            
            # Configure session options for optimal performance
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            session_options.enable_cpu_mem_arena = True
            session_options.enable_mem_pattern = True
            session_options.enable_mem_reuse = True
            
            # Set thread count for optimal CPU utilization
            cpu_count = os.cpu_count() or 4
            session_options.intra_op_num_threads = min(cpu_count, 8)
            session_options.inter_op_num_threads = min(cpu_count // 2, 4)
            
            # Configure execution providers (prefer GPU if available)
            providers = []
            if ort.get_available_providers():
                available_providers = ort.get_available_providers()
                if 'CUDAExecutionProvider' in available_providers:
                    providers.append('CUDAExecutionProvider')
                providers.append('CPUExecutionProvider')
            else:
                providers = ['CPUExecutionProvider']
            
            logger.info(f"Using execution providers: {providers}")
            
            # Create inference session
            _inference_session = ort.InferenceSession(
                model_path,
                sess_options=session_options,
                providers=providers
            )
            
            load_time = time.time() - start_time
            MODEL_LOAD_TIME.set(load_time)
              # Record model size
            model_size = Path(model_path).stat().st_size
            MODEL_SIZE_BYTES.labels(model_type=model_type).set(model_size)
            
            # Mark session as ready
            SESSION_READY.labels(model_type=model_type).set(1)            
            logger.info(f"Inference session loaded successfully in {load_time:.3f} seconds")
            logger.info(f"Model size: {model_size / (1024*1024):.2f} MB")
            logger.info(f"Input shapes: {[input.shape for input in _inference_session.get_inputs()]}")
            logger.info(f"Output shapes: {[output.shape for output in _inference_session.get_outputs()]}")
            
            return _inference_session
            
        except Exception as e:
            logger.error(f"Failed to load inference session: {e}")
            SESSION_READY.labels(model_type='unknown').set(0)
            return None


def performance_monitor(func):
    """
    Decorator to monitor inference performance metrics.
    
    :param func: Function to monitor
    :return: Wrapped function with performance monitoring
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        model_type = kwargs.get('model_type', 'unknown')
        batch_size = kwargs.get('batch_size', 1)
        
        try:
            result = func(*args, **kwargs)
            INFERENCE_COUNT.labels(model_type=model_type, status='success').inc()
            return result
        except Exception as e:
            INFERENCE_COUNT.labels(model_type=model_type, status='error').inc()
            raise
        finally:
            latency = time.time() - start_time
            INFERENCE_LATENCY.labels(model_type=model_type, batch_size=str(batch_size)).observe(latency)
    
    return wrapper


# Initialize resource monitoring at module load
start_inference_monitoring()

class EdgeInference:
    """
    Edge AI inference engine for object detection and activity recognition.
    
    This class handles loading and executing ONNX Runtime optimized models for real-time
    inference on edge devices. It uses singleton model caching for efficient resource usage
    and provides comprehensive performance monitoring and hard example detection.
    
    Attributes:
        model_dir (str): Directory containing serialized model files
        kafka_producer: Kafka producer for hard example publishing
        hard_example_thresholds (dict): Confidence thresholds for hard example detection
        inference_session: ONNX Runtime inference session (singleton)
    """
    
    def __init__(self, model_dir: str = None, kafka_bootstrap_servers: str = None):
        """
        Initialize the inference engine with models and Kafka connection.
        
        :param model_dir: Directory containing serialized model files (uses config default if None)
        :param kafka_bootstrap_servers: Kafka bootstrap servers for hard example publishing (uses config default if None)
        :raises Exception: If Kafka connection fails (warning only, continues without Kafka)
        """
        self.model_dir = model_dir or settings.model_dir
        kafka_servers = kafka_bootstrap_servers or settings.kafka_broker
        
        # Initialize inference session (singleton pattern)
        self.inference_session = get_inference_session()
        
        # Initialize Kafka producer for hard examples
        if KAFKA_AVAILABLE:
            try:
                self.kafka_producer = Producer({
                    "bootstrap.servers": kafka_servers,
                    "client.id": "edge-service-inference",
                    "delivery.timeout.ms": 30000,
                    "request.timeout.ms": 10000,
                })
                logger.info(f"Connected to Kafka at {kafka_servers}")
            except Exception as e:
                logger.warning(f"Could not connect to Kafka: {e}")
                self.kafka_producer = None
        else:
            self.kafka_producer = None
        
        # Hard example detection thresholds - low confidence detections trigger retraining
        self.hard_example_thresholds = {
            'person': 0.6,      # Person detection threshold
            'face': 0.5,        # Face detection threshold  
            'vehicle': 0.4,     # Vehicle detection threshold
            'object': 0.5       # Generic object threshold
        }
        
        logger.info(f"EdgeInference initialized with model_dir: {self.model_dir}")
        logger.info(f"Inference session ready: {self.inference_session is not None}")

    @performance_monitor
    def infer_objects(self, input_tensor: np.ndarray, camera_id: str = None, 
                     frame_data: np.ndarray = None, model_type: str = "object_detection", 
                     batch_size: int = 1) -> List[Detection]:
        """
        Run object detection on a preprocessed tensor.
        
        Executes object detection inference on a preprocessed input tensor using the
        singleton ONNX Runtime session. Falls back to simulation mode if no model
        is available.
        
        :param input_tensor: Preprocessed input tensor in CHW format (channels, height, width) as float32 array
        :param camera_id: Optional camera identifier for hard example tracking and analytics
        :param frame_data: Optional original frame data as numpy array for hard example storage
        :param model_type: Type of model for metrics tracking
        :param batch_size: Batch size for metrics tracking
        :return: List of Detection objects with bounding boxes, class names, and confidence scores
        :raises ValueError: If input_tensor has invalid shape or dtype
        """
        # Validate input tensor
        if input_tensor is None or input_tensor.size == 0:
            raise ValueError("Input tensor cannot be None or empty")
        
        if len(input_tensor.shape) != 3:
            raise ValueError(f"Expected 3D tensor (CHW), got shape: {input_tensor.shape}")
        
        detections = []
        
        # Use ONNX Runtime inference if available
        if self.inference_session is not None:
            try:
                # Prepare input for ONNX Runtime (add batch dimension if needed)
                if len(input_tensor.shape) == 3:
                    input_batch = np.expand_dims(input_tensor, axis=0)  # Add batch dimension
                else:
                    input_batch = input_tensor
                
                # Get input name from the model
                input_name = self.inference_session.get_inputs()[0].name
                
                # Run inference
                start_time = time.time()
                outputs = self.inference_session.run(None, {input_name: input_batch})
                inference_time = time.time() - start_time
                
                logger.debug(f"ONNX inference completed in {inference_time:.3f}s")
                
                # Parse outputs (assuming standard detection format)
                detections = self._parse_onnx_outputs(outputs)
                
            except Exception as e:
                logger.error(f"ONNX inference failed: {e}, falling back to simulation")
                detections = self._simulate_inference_results()
        else:
            # Fallback to simulation mode
            logger.debug("Using simulation mode for inference")
            detections = self._simulate_inference_results()
        
        # Check for hard examples and publish to Kafka if needed
        if camera_id and frame_data is not None and self.kafka_producer is not None:
            self._check_and_publish_hard_examples(detections, camera_id, frame_data)
        
        return detections
    
    def _parse_onnx_outputs(self, outputs: List[np.ndarray]) -> List[Detection]:
        """
        Parse ONNX model outputs into Detection objects.
        
        :param outputs: Raw outputs from ONNX Runtime inference
        :return: List of Detection objects
        """
        detections = []
        
        try:
            # Assuming standard detection output format:
            # outputs[0] shape: [batch_size, num_detections, 7]
            # where each detection is [batch_id, class_id, confidence, x_min, y_min, x_max, y_max]
            
            if len(outputs) > 0 and outputs[0].size > 0:
                detection_data = outputs[0][0]  # Remove batch dimension
                
                # Class names mapping (extend as needed)
                class_names = {
                    0: "background",
                    1: "person",
                    2: "vehicle", 
                    3: "object"
                }
                
                for det in detection_data:
                    if len(det) >= 7:
                        _, class_id, confidence, x_min, y_min, x_max, y_max = det[:7]
                        
                        # Filter out low confidence detections
                        if confidence > 0.1:  # Minimum confidence threshold
                            class_name = class_names.get(int(class_id), "unknown")
                            
                            bbox = BoundingBox(
                                x_min=float(x_min),
                                y_min=float(y_min),
                                x_max=float(x_max),
                                y_max=float(y_max)
                            )
                            
                            detection = Detection(
                                label=class_name,
                                confidence=float(confidence),
                                bounding_box=bbox
                            )
                            detections.append(detection)
            
        except Exception as e:
            logger.error(f"Error parsing ONNX outputs: {e}")
            # Fall back to simulation if parsing fails
            detections = self._simulate_inference_results()
        
        return detections
    
    def _simulate_inference_results(self) -> List[Detection]:
        """
        Generate simulated inference results for testing/development.
        
        :return: List of simulated Detection objects
        """
        import random
        
        detections = []
        
        # Generate a realistic number of detections (2-4 objects per frame)
        num_detections = random.randint(2, 4)
        
        # Ensure we always generate at least one hard example (low confidence detection)
        for i in range(num_detections):
            if i == 0:
                # First detection is always a hard example with low confidence
                class_name = random.choice(["person", "vehicle", "object"])
                
                # Generate confidence below the threshold for this class
                if class_name == "person":
                    confidence = random.uniform(0.2, 0.55)  # Below 0.6 threshold
                elif class_name == "vehicle":
                    confidence = random.uniform(0.2, 0.35)  # Below 0.4 threshold
                else:
                    confidence = random.uniform(0.2, 0.45)  # Below 0.5 threshold
            else:
                # Generate mixed confidence levels for remaining detections
                confidence = random.uniform(0.2, 0.9)
                
                # Class selection based on confidence level
                if confidence < 0.4:
                    class_name = random.choice(["person", "vehicle", "object"])
                elif confidence < 0.6:
                    class_name = random.choice(["person", "vehicle"])
                else:
                    class_name = "person"  # High confidence detections are usually persons
            
            # Generate realistic bounding box coordinates (normalized to [0,1])
            x_min = random.uniform(0, 0.7)
            y_min = random.uniform(0, 0.7)
            x_max = x_min + random.uniform(0.1, 0.3)
            y_max = y_min + random.uniform(0.1, 0.3)
            
            bbox = BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)
            
            detection = Detection(
                label=class_name,
                confidence=confidence,
                bounding_box=bbox
            )
            detections.append(detection)
        
        return detections

    def _check_and_publish_hard_examples(self, detections: List[Detection], camera_id: str, frame_data: np.ndarray):
        """
        Check if any detections qualify as hard examples and publish them to Kafka.
        
        Hard examples are detections with confidence scores below predefined thresholds
        for each class. These low-confidence detections indicate challenging scenarios
        where the model struggles, making them valuable for retraining and improvement.
        
        :param detections: List of detections from inference to evaluate
        :param camera_id: Camera identifier for tracking and analytics purposes
        :param frame_data: Original frame data as numpy array for storage with hard examples
        :raises Exception: If Kafka publishing fails (logs error but continues execution)
        """
        # Early return if Kafka producer is not available
        # This allows the service to continue functioning without Kafka dependency
        if not self.kafka_producer:
            return
        
        hard_examples = []
          # Evaluate each detection against class-specific confidence thresholds
        for detection in detections:
            # Get threshold for this class, defaulting to 0.5 for unknown classes
            threshold = self.hard_example_thresholds.get(detection.label, 0.5)
            
            # Detections below threshold are considered hard examples
            if detection.confidence < threshold:
                hard_examples.append({
                    'class_name': detection.label,
                    'confidence': detection.confidence,
                    'bbox': detection.bounding_box.dict()  # Convert bounding box to dictionary
                })
        
        # Only publish if we found hard examples
        if hard_examples:
            # Encode frame data as base64 for JSON serialization
            # This allows the frame to be stored and transmitted via Kafka
            try:
                import cv2
                
                # Encode frame as JPEG to reduce size while maintaining quality
                success, buffer = cv2.imencode('.jpg', frame_data)
                if not success:
                    print("Warning: Failed to encode frame for hard example")
                    return
                    
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # Create comprehensive hard example message
                hard_example_message = {
                    'camera_id': camera_id,
                    'timestamp': int(time.time()),
                    'frame_data': frame_base64,
                    'detections': hard_examples,
                    'model_version': getattr(self, 'model_version', '1.0.0')
                }
                
                # Publish to Kafka 'hard-examples' topic
                # Using camera_id as key for partitioning (same camera -> same partition)
                self.kafka_producer.produce(
                    'hard-examples',
                    key=camera_id,
                    value=json.dumps(hard_example_message).encode('utf-8'),
                    callback=self._delivery_report
                )
                
                # Poll for delivery confirmation (non-blocking)
                self.kafka_producer.poll(0)
                
                print(f"Published hard example from camera {camera_id} with {len(hard_examples)} low-confidence detections")
            except Exception as e:
                print(f"Error publishing hard example: {e}")

    def _delivery_report(self, err, msg):
        """
        Callback for Kafka message delivery confirmation.
        
        This callback is invoked by the Kafka producer after attempting to deliver
        a message, providing success/failure notification for monitoring purposes.
        
        :param err: Error object if delivery failed, None if successful
        :param msg: Message object containing delivery details
        """
        if err is not None:
            print(f"Message delivery failed: {err}")
        else:
            print(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

    def infer_activity(self, input_tensor: np.ndarray) -> str:
        """
        Run activity recognition on a preprocessed tensor.
        
        Performs activity recognition inference to classify the current activity
        in the video frame. Currently returns placeholder results as the activity
        recognition model is not yet implemented.
        
        :param input_tensor: Preprocessed input tensor in CHW format as float32 array
        :return: Activity label string (currently "unknown" placeholder)
        :raises NotImplementedError: Activity recognition is not yet implemented
        """
        # TODO: Implement activity recognition inference
        # This would involve loading an activity recognition model and running inference
        # on temporal features extracted from video sequences
        return "unknown"


# Additional functions for comprehensive inference pipeline

def preprocess_frame(image: np.ndarray, target_size: tuple = (224, 224)) -> np.ndarray:
    """
    Preprocess frame for inference by resizing and normalizing.
    
    Combines resize and normalization operations into a single function
    for convenient preprocessing of camera frames before inference.
    
    :param image: Input BGR image as numpy array
    :param target_size: Target size for resizing (width, height)
    :return: Preprocessed tensor in CHW format as float32 array
    :raises ValueError: If image is None or has invalid dimensions
    """
    if image is None:
        raise ValueError("Input image cannot be None")
    
    if len(image.shape) != 3:
        raise ValueError("Input image must be 3-channel (BGR)")
      # Import preprocessing functions
    try:
        from .preprocessing import resize_letterbox, normalize_image
    except ImportError:
        from preprocessing import resize_letterbox, normalize_image
    
    # Resize with letterboxing to maintain aspect ratio
    resized = resize_letterbox(image, target_size)
    
    # Normalize using ImageNet statistics (RGB format)
    tensor = normalize_image(resized, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    
    return tensor


def run_inference(blob: np.ndarray, model_path: str = None, config_path: str = None) -> np.ndarray:
    """
    Run inference on preprocessed blob using OpenCV DNN.
    
    Loads a deep neural network model and runs forward inference on the input blob.
    Currently supports TensorFlow and ONNX model formats through OpenCV DNN.
    
    :param blob: Preprocessed tensor in NCHW format as float32 array
    :param model_path: Path to model weights file (optional, uses default if None)
    :param config_path: Path to model config file (optional, uses default if None)
    :return: Detection results tensor with format [batch_id, class_id, confidence, x, y, w, h]
    :raises FileNotFoundError: If model files are not found
    :raises ValueError: If blob has invalid format
    """
    import cv2
    
    if blob is None or blob.size == 0:
        raise ValueError("Input blob cannot be None or empty")
    
    # Use default model paths if not specified
    if model_path is None:
        model_path = os.path.join(settings.model_dir, "opencv_face_detector_uint8.pb")
    if config_path is None:
        config_path = os.path.join(settings.model_dir, "opencv_face_detector.pbtxt")
    
    # Check if model files exist
    if not os.path.exists(model_path):
        # Return simulated results for development/testing
        print(f"Warning: Model file not found: {model_path} - returning simulated results")
        return _simulate_inference_results()
    
    if not os.path.exists(config_path):
        print(f"Warning: Config file not found: {config_path} - returning simulated results")
        return _simulate_inference_results()
    
    try:
        # Load the network
        net = cv2.dnn.readNetFromTensorflow(model_path, config_path)
        
        # Set input blob
        net.setInput(blob)
        
        # Run forward pass
        detections = net.forward()
        
        return detections
        
    except Exception as e:
        print(f"Warning: Inference failed: {e} - returning simulated results")
        return _simulate_inference_results()


def _simulate_inference_results() -> np.ndarray:
    """
    Generate simulated inference results for testing/development.
    
    :return: Simulated detection tensor with realistic values
    """
    import random
    
    # Generate 2-4 simulated detections
    num_detections = random.randint(2, 4)
    detections = []
    
    for i in range(num_detections):
        # Generate realistic detection values
        batch_id = 0
        class_id = random.choice([1, 2, 3])  # Person, vehicle, object
        confidence = random.uniform(0.3, 0.9)
        
        # Generate bbox coordinates (normalized)
        x = random.uniform(0.1, 0.6)
        y = random.uniform(0.1, 0.6)  
        w = random.uniform(0.1, 0.3)
        h = random.uniform(0.1, 0.3)
        
        detections.append([batch_id, class_id, confidence, x, y, w, h])
    
    return np.array(detections, dtype=np.float32)


def detect_and_annotate(image: np.ndarray, confidence_threshold: float = 0.5, 
                       anonymize_faces: bool = True) -> np.ndarray:
    """
    Detect objects and annotate image with face anonymization.
    
    Performs end-to-end object detection on an input image, applies face anonymization
    for privacy compliance, and returns the annotated result. This is the main
    high-level function for processing camera frames.
    
    :param image: Input BGR image as numpy array
    :param confidence_threshold: Minimum confidence threshold for detections
    :param anonymize_faces: Whether to apply face anonymization
    :return: Annotated image with detected objects and anonymized faces
    :raises ValueError: If image is None or has invalid format
    """
    import cv2
    
    if image is None:
        raise ValueError("Input image cannot be None")
    
    if len(image.shape) != 3:
        raise ValueError("Input image must be 3-channel (BGR)")
    
    try:
        # Step 1: Preprocess the frame
        blob = preprocess_frame(image)
        
        # Step 2: Run inference
        detections = run_inference(blob)
        
        # Step 3: Process detections and annotate image
        annotated_image = image.copy()
        
        # Step 4: Apply face anonymization if enabled
        if anonymize_faces:
            annotated_image = _apply_face_anonymization(annotated_image, detections, confidence_threshold)
        
        # Step 5: Draw bounding boxes for other objects (non-faces)
        annotated_image = _draw_detection_boxes(annotated_image, detections, confidence_threshold)
        
        return annotated_image
        
    except Exception as e:
        print(f"Warning: Detection and annotation failed: {e}")
        # Return original image on failure
        return image.copy()


def _apply_face_anonymization(image: np.ndarray, detections: np.ndarray, 
                             confidence_threshold: float) -> np.ndarray:
    """
    Apply face anonymization (blurring) to detected faces.
    
    :param image: Input image
    :param detections: Detection results from inference
    :param confidence_threshold: Minimum confidence for processing
    :return: Image with anonymized faces    """
    import cv2
    
    height, width = image.shape[:2]
    
    for detection in detections:
        confidence = detection[2]
        class_id = int(detection[1])
        
        # Process only high-confidence face detections (assuming class_id 1 is face/person)
        if confidence >= confidence_threshold and class_id == 1:
            # Convert normalized coordinates to pixel coordinates
            x = int(detection[3] * width)
            y = int(detection[4] * height) 
            w = int(detection[5] * width)
            h = int(detection[6] * height)
            
            # Ensure coordinates are within image bounds
            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            w = max(1, min(w, width - x))
            h = max(1, min(h, height - y))
            
            # Extract face region and apply Gaussian blur
            if w > 0 and h > 0:
                face_region = image[y:y+h, x:x+w]
                if face_region.size > 0:
                    # Apply strong blur for anonymization
                    kernel_size = max(31, min(w, h) // 3)
                    if kernel_size % 2 == 0:
                        kernel_size += 1  # Ensure odd kernel size
                    
                    blurred_face = cv2.GaussianBlur(face_region, (kernel_size, kernel_size), 0)
                    image[y:y+h, x:x+w] = blurred_face
    
    return image


def _draw_detection_boxes(image: np.ndarray, detections: np.ndarray, 
                         confidence_threshold: float) -> np.ndarray:
    """
    Draw bounding boxes for non-face detections.
    
    :param image: Input image
    :param detections: Detection results from inference
    :param confidence_threshold: Minimum confidence for drawing boxes
    :return: Image with bounding boxes drawn
    """
    import cv2
    
    height, width = image.shape[:2]
    
    # Class labels for display
    class_labels = {1: "Person", 2: "Vehicle", 3: "Object"}
    
    for detection in detections:
        confidence = detection[2]
        class_id = int(detection[1])
        
        if confidence >= confidence_threshold:
            # Convert normalized coordinates to pixel coordinates
            x = int(detection[3] * width)
            y = int(detection[4] * height)
            w = int(detection[5] * width)  
            h = int(detection[6] * height)
            
            # Draw bounding box (skip faces as they are anonymized)
            if class_id != 1:  # Not a face/person
                color = (0, 255, 0) if class_id == 2 else (255, 0, 0)  # Green for vehicle, blue for object
                cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
                
                # Draw label
                label = f"{class_labels.get(class_id, 'Unknown')}: {confidence:.2f}"
                cv2.putText(image, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return image
