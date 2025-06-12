"""
Inference engine for object detection and activity recognition with hard example detection.
"""
import os
import time
import json
import base64
import numpy as np
from typing import List, Optional, Dict
from shared.models import Detection, BoundingBox

# Add Kafka producer import
from confluent_kafka import Producer

class EdgeInference:
    def __init__(self, model_dir: str, kafka_bootstrap_servers: str = "localhost:9092"):
        """
        Load object detection and activity recognition models.
        :param model_dir: Directory containing serialized engine files.
        :param kafka_bootstrap_servers: Kafka bootstrap servers for hard example publishing.
        """
        self.model_dir = model_dir
        # TODO: Replace with real TensorRT engine loading
        self.obj_model = self._load_engine(os.path.join(model_dir, "object_detection.trt"))
        self.act_model = self._load_engine(os.path.join(model_dir, "activity_recognition.trt"))
        
        # Initialize Kafka producer for hard examples
        try:
            self.kafka_producer = Producer({
                "bootstrap.servers": kafka_bootstrap_servers,
                "client.id": "edge-service-inference"
            })
            print(f"Connected to Kafka at {kafka_bootstrap_servers}")
        except Exception as e:
            print(f"Warning: Could not connect to Kafka: {e}")
            self.kafka_producer = None
        
        # Hard example thresholds
        self.hard_example_thresholds = {
            'person': 0.6,
            'face': 0.5,
            'vehicle': 0.4,
            'object': 0.5
        }

    def _load_engine(self, engine_path: str):
        """
        Load a TensorRT engine from file.
        :param engine_path: Path to .trt file.
        :return: Loaded inference engine context.
        """
        # TODO: implement TensorRT runtime and engine context
        if not os.path.exists(engine_path):
            print(f"Warning: Engine file not found: {engine_path} - running in simulation mode")
            return None  # Return None for simulation mode
        # Stub: return path as placeholder
        return engine_path
        
    def infer_objects(self, input_tensor: np.ndarray, camera_id: str = None, frame_data: np.ndarray = None) -> List[Detection]:
        """
        Run object detection on a preprocessed tensor.
        :param input_tensor: CHW float32 array.
        :param camera_id: Camera identifier for hard example tracking.
        :param frame_data: Original frame data for hard example storage.
        :return: List of Detection objects with confidence scores.
        """
        # TODO: Run real inference via TensorRT or Torch-TensorRT
        # For now, simulate some detections with varying confidence levels
        import random
        
        # Simulate random detections for demonstration
        detections = []
        # Ensure we get at least 3 detections
        num_detections = random.randint(3, 5)
        
        # Force at least one detection to be a hard example
        for i in range(num_detections):
            if i == 0:
                # First detection will always be a hard example (low confidence)
                class_name = random.choice(["person", "vehicle", "object"])
                # Use a confidence below the threshold
                if class_name == "person":
                    confidence = random.uniform(0.2, 0.55)  # below 0.6 threshold
                elif class_name == "vehicle":
                    confidence = random.uniform(0.2, 0.35)  # below 0.4 threshold
                else:
                    confidence = random.uniform(0.2, 0.45)  # below 0.5 threshold
            else:
                # Generate random confidence (some low, some high)
                confidence = random.uniform(0.2, 0.9)
                
                # Choose class based on confidence
                if confidence < 0.4:
                    class_name = random.choice(["person", "vehicle", "object"])
                elif confidence < 0.6:
                    class_name = random.choice(["person", "vehicle"])
                else:
                    class_name = "person"
            
            # Generate random bounding box
            x1 = random.uniform(0, 0.7)
            y1 = random.uniform(0, 0.7)
            x2 = x1 + random.uniform(0.1, 0.3)
            y2 = y1 + random.uniform(0.1, 0.3)
            
            bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
            
            detection = Detection(
                bbox=bbox,
                class_name=class_name,
                confidence=confidence
            )
            detections.append(detection)
        
        # Check for hard examples and publish to Kafka if needed
        if camera_id and frame_data is not None and self.kafka_producer is not None:
            self._check_and_publish_hard_examples(detections, camera_id, frame_data)
        
        return detections

    def _check_and_publish_hard_examples(self, detections: List[Detection], camera_id: str, frame_data: np.ndarray):
        """
        Check if any detections qualify as hard examples and publish them to Kafka.
        :param detections: List of detections from inference.
        :param camera_id: Camera identifier.
        :param frame_data: Original frame data as numpy array.
        """
        if not self.kafka_producer:
            return
        
        hard_examples = []
        
        for detection in detections:
            threshold = self.hard_example_thresholds.get(detection.class_name, 0.5)
            if detection.confidence < threshold:
                hard_examples.append({
                    'class_name': detection.class_name,
                    'confidence': detection.confidence,
                    'bbox': detection.bbox.dict()
                })
        
        if hard_examples:
            # Encode frame data as base64
            try:
                import cv2
                _, buffer = cv2.imencode('.jpg', frame_data)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                hard_example_message = {
                    'camera_id': camera_id,
                    'timestamp': int(time.time()),
                    'frame_data': frame_base64,
                    'detections': hard_examples,
                    'model_version': getattr(self, 'model_version', '1.0.0')
                }
                
                self.kafka_producer.produce(
                    'hard-examples',
                    key=camera_id,
                    value=json.dumps(hard_example_message).encode('utf-8'),
                    callback=self._delivery_report
                )
                self.kafka_producer.poll(0)
                
                print(f"Published hard example from camera {camera_id} with {len(hard_examples)} low-confidence detections")
            except Exception as e:
                print(f"Error publishing hard example: {e}")

    def _delivery_report(self, err, msg):
        """Callback for Kafka message delivery."""
        if err is not None:
            print(f"Message delivery failed: {err}")
        else:
            print(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

    def infer_activity(self, input_tensor: np.ndarray) -> str:
        """
        Run activity recognition on a preprocessed tensor.
        :param input_tensor: CHW float32 array.
        :return: Activity label.
        """
        # TODO: Run real inference
        return "unknown"
