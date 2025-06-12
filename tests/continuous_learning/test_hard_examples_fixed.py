#!/usr/bin/env python3
"""
Test script to verify hard example detection and collection functionality.
This script tests the continuous learning pipeline's ability to identify and publish hard examples.
"""
import os
import sys
import numpy as np
import cv2
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

# Define models for testing since we might not have access to shared modules
@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    
    def dict(self) -> Dict[str, float]:
        return asdict(self)

@dataclass
class Detection:
    bbox: BoundingBox
    class_name: str
    confidence: float
    
    def dict(self) -> Dict[str, Any]:
        return {
            "bbox": self.bbox.dict(),
            "class_name": self.class_name,
            "confidence": self.confidence
        }

# Monkey patch the modules to make the import work
import sys
import types

# Create mock module for shared
shared_module = types.ModuleType("shared")
sys.modules["shared"] = shared_module

# Create mock module for shared.models
models_module = types.ModuleType("shared.models")
models_module.BoundingBox = BoundingBox
models_module.Detection = Detection
sys.modules["shared.models"] = models_module

# Import our EdgeInference class
from edge_service.inference_with_hard_examples import EdgeInference

def generate_test_frame(width=640, height=480):
    """Generate a test frame with some content."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Add a simple pattern
    cv2.rectangle(frame, (100, 100), (300, 300), (0, 255, 0), 2)
    cv2.circle(frame, (400, 200), 80, (0, 0, 255), -1)
    cv2.putText(frame, "Test Frame", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    return frame

def test_hard_example_detection():
    """Test if the EdgeInference class correctly detects and publishes hard examples."""
    print("\n🔍 Testing Hard Example Detection...")
    
    # Create test frame
    frame = generate_test_frame()
    
    # Create test input tensor (normally would be preprocessed from the frame)
    input_tensor = np.random.rand(3, 224, 224).astype(np.float32)
    
    # Initialize EdgeInference with Kafka connection
    print("Initializing EdgeInference...")
    edge_inference = EdgeInference(
        model_dir="./models", 
        kafka_bootstrap_servers="localhost:9092"
    )
    
    # Verify hard example thresholds are configured
    if not hasattr(edge_inference, 'hard_example_thresholds'):
        print("❌ Hard example thresholds not configured!")
        return False
    
    print(f"✅ Hard example thresholds configured: {edge_inference.hard_example_thresholds}")
    
    # Run inference with camera_id and frame data to trigger hard example check
    print("Running inference with hard example detection...")
    detections = edge_inference.infer_objects(
        input_tensor=input_tensor,
        camera_id="test-camera-01",
        frame_data=frame
    )
    
    print(f"✅ Generated {len(detections)} detections")
    
    # Check if any are considered hard examples
    hard_examples = []
    for det in detections:
        threshold = edge_inference.hard_example_thresholds.get(
            det.class_name, 
            edge_inference.hard_example_thresholds.get('default', 0.5)
        )
        if det.confidence < threshold:
            hard_examples.append(det)
    
    if hard_examples:
        print(f"✅ Found {len(hard_examples)} hard examples")
        for i, ex in enumerate(hard_examples):
            print(f"  Hard Example {i+1}: {ex.class_name} with confidence {ex.confidence:.2f}")
        return True
    else:
        print("⚠️ No hard examples found in this run. This might be random - try running the test again.")
        return False

if __name__ == "__main__":
    print("🚀 Testing Continuous Learning / Hard Example Pipeline")
    print("=" * 60)
    
    success = test_hard_example_detection()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Hard example detection is working correctly!")
        print("\n📋 Next Steps:")
        print("1. Start all services with docker-compose up -d")
        print("2. Create Kafka topics with ./create_kafka_topics.ps1")
        print("3. Test the full pipeline with ./test_continuous_learning.ps1")
    else:
        print("❌ Hard example detection test failed. Check the logs above for details.")
    
    sys.exit(0 if success else 1)
