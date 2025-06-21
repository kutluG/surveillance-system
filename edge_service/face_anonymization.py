"""
Face Anonymization Module for Edge Service

This module provides on-device face anonymization capabilities to ensure privacy compliance.
It detects faces in video frames and applies anonymization before any data leaves the device.

Features:
- Real-time face detection using OpenCV/MTCNN
- Multiple anonymization methods (blur, pixelate, black boxes)
- Configurable privacy levels
- Hash-based face embeddings for identification without storing raw faces
- Performance optimization for edge devices
"""

import cv2
import numpy as np
import hashlib
import os
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
import logging
from dataclasses import dataclass
from .config import settings

logger = logging.getLogger(__name__)

class AnonymizationMethod(Enum):
    """Supported face anonymization methods"""
    BLUR = "blur"
    PIXELATE = "pixelate"
    BLACK_BOX = "black_box"
    EMOJI = "emoji"

class PrivacyLevel(Enum):
    """Privacy protection levels"""
    STRICT = "strict"      # Maximum anonymization, no face data stored
    MODERATE = "moderate"  # Anonymize faces, store hashed embeddings
    MINIMAL = "minimal"    # Light blur, keep basic metrics

@dataclass
class FaceDetection:
    """Face detection result with anonymization info"""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    face_hash: Optional[str] = None
    anonymized: bool = False

@dataclass
class AnonymizationConfig:
    """Configuration for face anonymization"""
    enabled: bool = True
    method: AnonymizationMethod = AnonymizationMethod.BLUR
    privacy_level: PrivacyLevel = PrivacyLevel.STRICT
    blur_factor: int = 15
    pixelate_factor: int = 10
    min_face_size: int = 30
    detection_confidence: float = 0.7
    store_face_hashes: bool = False
    hash_embeddings_only: bool = True

class FaceAnonymizer:
    """
    Main face anonymization class for privacy-preserving video processing.
    
    This class provides comprehensive face anonymization capabilities for edge devices,
    supporting multiple anonymization methods and privacy levels. It implements a
    robust face detection pipeline with fallback mechanisms and configurable
    privacy settings to ensure compliance with data protection regulations.
    
    Key Features:
        - Multiple detection algorithms (Haar Cascade, DNN) with automatic fallback
        - Configurable anonymization methods (blur, pixelate, black box, emoji)
        - Privacy-preserving face hashing for identification without raw face storage
        - Comprehensive statistics and monitoring capabilities
        - Edge-optimized performance with minimal resource usage
    
    Attributes:
        config (AnonymizationConfig): Configuration object controlling behavior
        face_cascade: Haar cascade classifier for lightweight face detection
        dnn_net: DNN-based face detection model for higher accuracy
    """
    
    def __init__(self, config: AnonymizationConfig = None):
        """
        Initialize the face anonymizer with configuration.
        
        Sets up the face anonymization system with the specified configuration,
        initializing detection models and logging the configuration for monitoring.
        
        :param config: Anonymization configuration object, uses default if None
        """
        self.config = config or AnonymizationConfig()
        self.face_cascade = None
        self.dnn_net = None
        self._initialize_detectors()
        
        logger.info(f"Face anonymizer initialized with method: {self.config.method.value}, "
                   f"privacy level: {self.config.privacy_level.value}")
    
    def _initialize_detectors(self):
        """
        Initialize face detection models with fallback strategy.
        
        Sets up both primary and backup face detection methods:
        1. Primary: OpenCV Haar Cascade (lightweight, good for edge devices)
        2. Backup: DNN-based face detection (more accurate but computationally heavier)
        
        The initialization follows a defensive programming approach, gracefully handling
        missing model files and configuration issues while ensuring at least one detector
        is available for face detection operations.
        
        :raises Exception: Logs errors but continues execution if detectors fail to load
        """
        try:
            # Initialize primary detector: OpenCV Haar Cascade
            # Haar cascades are lightweight and fast, ideal for edge devices
            haar_path = settings.haar_cascade_path
            if os.path.exists(haar_path):
                self.face_cascade = cv2.CascadeClassifier(haar_path)
                logger.info(f"Loaded Haar cascade from: {haar_path}")
            else:
                # Fallback to OpenCV built-in cascade if configured path not found
                # This ensures the service remains functional even with configuration issues
                self.face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                logger.warning(f"Using built-in Haar cascade, configured path not found: {haar_path}")
              # Initialize backup detector: DNN-based face detection
            # DNN models provide higher accuracy but require more computational resources
            try:
                prototxt_path = settings.dnn_prototxt_path
                weights_path = settings.dnn_model_path
                
                if os.path.exists(prototxt_path) and os.path.exists(weights_path):
                    self.dnn_net = cv2.dnn.readNetFromTensorflow(weights_path, prototxt_path)
                    logger.info(f"DNN face detector loaded from: {prototxt_path}, {weights_path}")
                else:
                    logger.warning(f"DNN model files not found: {prototxt_path}, {weights_path}")
                    self.dnn_net = None
                    
            except Exception as e:
                logger.warning(f"DNN face detector not available: {e}")
                self.dnn_net = None
                
        except Exception as e:
            logger.error(f"Failed to initialize face detectors: {e}")
            self.face_cascade = None
    
    def detect_faces(self, frame: np.ndarray) -> List[FaceDetection]:
        """
        Detect faces in the frame using available detectors.
        
        Implements a hierarchical detection strategy, attempting DNN-based detection
        first for higher accuracy, then falling back to Haar cascade if needed.
        This approach balances accuracy with performance based on available resources.
        
        :param frame: Input video frame as numpy array in BGR color space
        :return: List of FaceDetection objects with bounding boxes and confidence scores
        :raises ValueError: If frame is empty or has invalid format
        """
        # Return empty list if anonymization is disabled
        if not self.config.enabled:
            return []
        
        # Validate input frame
        if frame is None or frame.size == 0:
            raise ValueError("Input frame is empty or invalid")
        
        faces = []
        
        # Primary detection: Try DNN detector first (more accurate)
        if self.dnn_net is not None:
            faces = self._detect_faces_dnn(frame)
        
        # Fallback detection: Use Haar cascade if DNN fails or unavailable
        if not faces and self.face_cascade is not None:
            faces = self._detect_faces_haar(frame)
        
        return faces
    
    def _detect_faces_haar(self, frame: np.ndarray) -> List[FaceDetection]:
        """
        Detect faces using Haar Cascade classifier.
        
        Haar cascades are lightweight and fast, making them ideal for edge devices
        with limited computational resources. They work well for frontal faces
        under good lighting conditions.
        
        :param frame: Input BGR frame for face detection
        :return: List of detected faces with estimated confidence
        """
        # Convert to grayscale as Haar cascades work on single-channel images
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Run cascade detection with optimized parameters
        # scaleFactor: How much the image size is reduced at each scale
        # minNeighbors: How many neighbors each face candidate should retain
        # minSize: Minimum possible face size, smaller faces are ignored
        face_rects = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,        # 10% size reduction per scale level
            minNeighbors=5,         # Good balance between false positives and missed detections
            minSize=(self.config.min_face_size, self.config.min_face_size)
        )
        
        faces = []
        for (x, y, w, h) in face_rects:
            faces.append(FaceDetection(
                x=x, y=y, width=w, height=h,
                confidence=0.8  # Haar cascades don't provide confidence, use reasonable default
            ))
        
        return faces
    
    def _detect_faces_dnn(self, frame: np.ndarray) -> List[FaceDetection]:
        """
        Detect faces using DNN (Deep Neural Network) model.
        
        DNN-based detection provides higher accuracy and better handling of
        challenging conditions (lighting, angles, occlusions) compared to
        traditional methods, at the cost of increased computational requirements.
        
        :param frame: Input BGR frame for face detection
        :return: List of detected faces with confidence scores
        """
        # Get frame dimensions for coordinate normalization
        (h, w) = frame.shape[:2]
        
        # Create blob from image for DNN input
        # Resize to 300x300 (model's expected input size)
        # Subtract mean values to normalize pixel values
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 1.0,
            (300, 300), (104.0, 177.0, 123.0)
        )
        
        # Run forward pass through the network
        self.dnn_net.setInput(blob)
        detections = self.dnn_net.forward()
        
        faces = []
        
        # Process each detection
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            # Filter detections by confidence threshold
            if confidence > self.config.detection_confidence:
                # Extract bounding box coordinates (normalized [0,1])
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x, y, x1, y1) = box.astype("int")
                
                # Convert to width/height format
                width = x1 - x
                height = y1 - y
                
                # Validate face size meets minimum requirements
                if width >= self.config.min_face_size and height >= self.config.min_face_size:
                    faces.append(FaceDetection(
                        x=x, y=y, width=width, height=height,
                        confidence=float(confidence)
                    ))
        
        return faces
    
    def anonymize_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[FaceDetection]]:
        """
        Anonymize all faces in the frame
        
        Returns:
            Tuple of (anonymized_frame, face_detections)
        """
        if not self.config.enabled:
            return frame, []
        
        # Detect faces
        faces = self.detect_faces(frame)
        
        if not faces:
            return frame, []
        
        # Create anonymized frame
        anonymized_frame = frame.copy()
        
        for face in faces:
            # Apply anonymization
            anonymized_frame = self._apply_anonymization(anonymized_frame, face)
            
            # Generate face hash if needed
            if self.config.store_face_hashes or self.config.hash_embeddings_only:
                face.face_hash = self._generate_face_hash(frame, face)
            
            face.anonymized = True
        
        return anonymized_frame, faces
    
    def _apply_anonymization(self, frame: np.ndarray, face: FaceDetection) -> np.ndarray:
        """Apply the configured anonymization method to a face region"""
        x, y, w, h = face.x, face.y, face.width, face.height
        
        # Ensure coordinates are within frame bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, frame.shape[1] - x)
        h = min(h, frame.shape[0] - y)
        
        face_region = frame[y:y+h, x:x+w]
        
        if self.config.method == AnonymizationMethod.BLUR:
            # Apply Gaussian blur
            kernel_size = max(self.config.blur_factor, 3)
            if kernel_size % 2 == 0:
                kernel_size += 1
            blurred = cv2.GaussianBlur(face_region, (kernel_size, kernel_size), 0)
            frame[y:y+h, x:x+w] = blurred
            
        elif self.config.method == AnonymizationMethod.PIXELATE:
            # Pixelate the face
            factor = self.config.pixelate_factor
            temp = cv2.resize(face_region, (w//factor, h//factor), interpolation=cv2.INTER_LINEAR)
            pixelated = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
            frame[y:y+h, x:x+w] = pixelated
            
        elif self.config.method == AnonymizationMethod.BLACK_BOX:
            # Draw black rectangle
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 0), -1)
            
        elif self.config.method == AnonymizationMethod.EMOJI:
            # Draw emoji-style circle (simplified)
            center = (x + w//2, y + h//2)
            radius = min(w, h) // 2
            cv2.circle(frame, center, radius, (0, 255, 255), -1)  # Yellow circle
            # Add simple eyes and mouth
            eye_y = y + h//3
            cv2.circle(frame, (x + w//3, eye_y), 3, (0, 0, 0), -1)
            cv2.circle(frame, (x + 2*w//3, eye_y), 3, (0, 0, 0), -1)
            mouth_y = y + 2*h//3
            cv2.ellipse(frame, (x + w//2, mouth_y), (w//6, h//8), 0, 0, 180, (0, 0, 0), 2)
        
        return frame
    
    def _generate_face_hash(self, frame: np.ndarray, face: FaceDetection) -> str:
        """Generate a privacy-preserving hash of the face region"""
        x, y, w, h = face.x, face.y, face.width, face.height
        
        # Extract face region
        face_region = frame[y:y+h, x:x+w]
        
        if self.config.privacy_level == PrivacyLevel.STRICT:
            # Hash only basic geometric features (size, position)
            face_data = f"{w}_{h}_{x%100}_{y%100}".encode()
        elif self.config.privacy_level == PrivacyLevel.MODERATE:
            # Hash resized and blurred face for basic similarity
            small_face = cv2.resize(face_region, (32, 32))
            blurred_face = cv2.GaussianBlur(small_face, (5, 5), 0)
            face_data = blurred_face.tobytes()
        else:  # MINIMAL
            # Hash basic face region (less privacy but more accuracy)
            small_face = cv2.resize(face_region, (48, 48))
            face_data = small_face.tobytes()
        
        return hashlib.sha256(face_data).hexdigest()[:16]
    
    def get_anonymization_stats(self, faces: List[FaceDetection]) -> Dict[str, Any]:
        """Get statistics about anonymization process"""
        return {
            "faces_detected": len(faces),
            "faces_anonymized": sum(1 for f in faces if f.anonymized),
            "anonymization_method": self.config.method.value,
            "privacy_level": self.config.privacy_level.value,
            "average_confidence": np.mean([f.confidence for f in faces]) if faces else 0.0,
            "face_hashes": [f.face_hash for f in faces if f.face_hash] if self.config.store_face_hashes else []
        }

# Configuration factory functions
def get_strict_config() -> AnonymizationConfig:
    """Get strict privacy configuration"""
    return AnonymizationConfig(
        enabled=True,
        method=AnonymizationMethod.BLACK_BOX,
        privacy_level=PrivacyLevel.STRICT,
        store_face_hashes=False,
        hash_embeddings_only=False
    )

def get_moderate_config() -> AnonymizationConfig:
    """Get moderate privacy configuration"""
    return AnonymizationConfig(
        enabled=True,
        method=AnonymizationMethod.BLUR,
        privacy_level=PrivacyLevel.MODERATE,
        blur_factor=20,
        store_face_hashes=True,
        hash_embeddings_only=True
    )

def get_minimal_config() -> AnonymizationConfig:
    """Get minimal privacy configuration"""
    return AnonymizationConfig(
        enabled=True,
        method=AnonymizationMethod.BLUR,
        privacy_level=PrivacyLevel.MINIMAL,
        blur_factor=10,
        store_face_hashes=True,
        hash_embeddings_only=False
    )
