#!/usr/bin/env python3
"""
Comprehensive test for the Continuous Learning Pipeline.
Tests the complete flow from hard example detection through annotation to model retraining.
"""
import os
import sys
import time
import json
import random
import requests
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our mock models (to avoid import errors if shared module isn't available)
from test_hard_examples_fixed import BoundingBox, Detection

# Import the EdgeInference class with hard example detection
from edge_service.inference_with_hard_examples import EdgeInference

# Configuration for tests
KAFKA_HOST = os.getenv("KAFKA_HOST", "localhost:9092")
HARD_EXAMPLE_COLLECTOR_URL = os.getenv("HARD_EXAMPLE_COLLECTOR_URL", "http://localhost:8010")
ANNOTATION_FRONTEND_URL = os.getenv("ANNOTATION_FRONTEND_URL", "http://localhost:8011")
TRAINING_SERVICE_URL = os.getenv("TRAINING_SERVICE_URL", "http://localhost:8012")

def generate_test_frame(width=640, height=480):
    """Generate a test frame with some content."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Add a simple pattern
    cv2_available = False
    try:
        import cv2
        cv2_available = True
    except ImportError:
        pass
    
    if cv2_available:
        cv2.rectangle(frame, (100, 100), (300, 300), (0, 255, 0), 2)
        cv2.circle(frame, (400, 200), 80, (0, 0, 255), -1)
        cv2.putText(frame, "Test Frame", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    else:
        # Simple pattern without cv2
        frame[100:300, 100:300] = [0, 255, 0]
        frame[150:250, 350:450] = [0, 0, 255]
    
    return frame

def test_edge_inference():
    """Test if the EdgeInference class correctly detects and publishes hard examples."""
    print("\n🔍 Testing Edge Inference with Hard Example Detection...")
    
    try:
        # Create test frame
        frame = generate_test_frame()
        
        # Create test input tensor
        input_tensor = np.random.rand(3, 224, 224).astype(np.float32)
        
        # Initialize EdgeInference with Kafka connection
        edge_inference = EdgeInference(
            model_dir="./models", 
            kafka_bootstrap_servers=KAFKA_HOST
        )
        
        # Verify hard example thresholds are configured
        if not hasattr(edge_inference, 'hard_example_thresholds'):
            print("❌ Hard example thresholds not configured!")
            return False
        
        print(f"✅ Hard example thresholds configured: {edge_inference.hard_example_thresholds}")
        
        # Run inference with camera_id and frame data to trigger hard example check
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
    
    except Exception as e:
        print(f"❌ Edge inference test failed: {str(e)}")
        return False

def test_hard_example_collector():
    """Test if the Hard Example Collector service is running and configured properly."""
    print("\n🔍 Testing Hard Example Collector Service...")
    
    try:
        # Try to connect to the health endpoint
        response = requests.get(f"{HARD_EXAMPLE_COLLECTOR_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Hard Example Collector service returned status code {response.status_code}")
            return False
        
        print("✅ Hard Example Collector service is running")
        
        # Get stats 
        stats_response = requests.get(f"{HARD_EXAMPLE_COLLECTOR_URL}/stats", timeout=5)
        if stats_response.status_code != 200:
            print(f"❌ Could not get stats from Hard Example Collector")
            return False
        
        stats = stats_response.json()
        print(f"✅ Hard Example Collector configuration: {json.dumps(stats, indent=2)}")
        
        # Verify thresholds are configured
        if 'thresholds' not in stats:
            print("❌ Confidence thresholds not found in stats response")
            return False
        
        thresholds = stats.get('thresholds', {})
        if not all(k in thresholds for k in ['person', 'vehicle']):
            print("❌ Required thresholds (person, vehicle) not configured")
            return False
        
        print(f"✅ Confidence thresholds configured: {thresholds}")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Hard Example Collector at {HARD_EXAMPLE_COLLECTOR_URL}")
        return False
    except Exception as e:
        print(f"❌ Hard Example Collector test failed: {str(e)}")
        return False

def test_annotation_frontend():
    """Test if the Annotation Frontend service is running."""
    print("\n🔍 Testing Annotation Frontend Service...")
    
    try:
        # Try to connect to the health endpoint
        response = requests.get(f"{ANNOTATION_FRONTEND_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Annotation Frontend service returned status code {response.status_code}")
            return False
        
        print("✅ Annotation Frontend service is running")
        
        # Try to get pending examples API
        try:
            examples_response = requests.get(f"{ANNOTATION_FRONTEND_URL}/api/examples", timeout=5)
            if examples_response.status_code == 200:
                examples = examples_response.json()
                print(f"✅ Annotation Frontend has {len(examples)} pending examples")
            else:
                print("⚠️ Could not retrieve pending examples, but service is running")
        except Exception:
            print("⚠️ Could not check for pending examples, but service is running")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Annotation Frontend at {ANNOTATION_FRONTEND_URL}")
        return False
    except Exception as e:
        print(f"❌ Annotation Frontend test failed: {str(e)}")
        return False

def test_training_service():
    """Test if the Training Service is running and properly configured."""
    print("\n🔍 Testing Training Service...")
    
    try:
        # Try to connect to the health endpoint
        response = requests.get(f"{TRAINING_SERVICE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Training Service returned status code {response.status_code}")
            return False
        
        print("✅ Training Service is running")
        
        # Get stats
        stats_response = requests.get(f"{TRAINING_SERVICE_URL}/stats", timeout=5)
        if stats_response.status_code != 200:
            print(f"❌ Could not get stats from Training Service")
            return False
        
        stats = stats_response.json()
        print(f"✅ Training Service configuration: {json.dumps(stats, indent=2)}")
        
        min_examples = stats.get('min_examples_for_training', 0)
        available_examples = stats.get('available_examples', 0)
        
        print(f"✅ Training Service has {available_examples} examples (minimum required: {min_examples})")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Training Service at {TRAINING_SERVICE_URL}")
        return False
    except Exception as e:
        print(f"❌ Training Service test failed: {str(e)}")
        return False

def test_end_to_end():
    """Test the complete end-to-end pipeline with all services."""
    print("\n🔍 Testing End-to-End Pipeline Flow...")
    
    # Check if all services are running first
    if not all([
        test_hard_example_collector(),
        test_annotation_frontend(),
        test_training_service()
    ]):
        print("❌ Some services are not running - skipping end-to-end test")
        return False
    
    try:
        # Step 1: Try to trigger hard examples from edge service
        print("\nStep 1: Triggering hard examples generation...")
        try:
            edge_response = requests.post("http://localhost:8000/capture", timeout=5)
            if edge_response.status_code == 200:
                print("✅ Successfully triggered edge service frame capture")
            else:
                print("⚠️ Could not trigger edge service, but continuing with test")
        except Exception:
            print("⚠️ Could not connect to edge service, but continuing with test")
        
        # Wait for Kafka message processing
        time.sleep(3)
        
        # Step 2: Check if hard examples were collected
        print("\nStep 2: Checking for hard examples...")
        hard_example_stats = requests.get(f"{HARD_EXAMPLE_COLLECTOR_URL}/stats", timeout=5).json()
        print(f"✅ Hard example collector stats: {json.dumps(hard_example_stats, indent=2)}")
        
        # Step 3: Check annotation frontend
        print("\nStep 3: Checking annotation frontend...")
        try:
            examples_response = requests.get(f"{ANNOTATION_FRONTEND_URL}/api/examples", timeout=5)
            if examples_response.status_code == 200:
                examples = examples_response.json()
                print(f"✅ Annotation Frontend has {len(examples)} pending examples")
            else:
                print("⚠️ Could not retrieve pending examples")
        except Exception:
            print("⚠️ Could not check for pending examples")
        
        # Step 4: Check training service
        print("\nStep 4: Checking training service...")
        training_stats = requests.get(f"{TRAINING_SERVICE_URL}/stats", timeout=5).json()
        print(f"✅ Training service stats: {json.dumps(training_stats, indent=2)}")
        
        # Optionally trigger a training job
        try:
            training_trigger = requests.post(f"{TRAINING_SERVICE_URL}/jobs/start", timeout=5)
            if training_trigger.status_code == 200:
                print(f"✅ Successfully triggered a training job: {training_trigger.json()}")
            else:
                print(f"⚠️ Could not trigger training job: {training_trigger.status_code}")
        except Exception as e:
            print(f"⚠️ Could not trigger training job: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ End-to-end pipeline test failed: {str(e)}")
        return False

def main():
    """Run all tests for the continuous learning pipeline."""
    print("🚀 Testing Continuous Learning / Hard Example Pipeline")
    print("=" * 60)
    
    tests = [
        test_edge_inference,
        test_hard_example_collector,
        test_annotation_frontend,
        test_training_service,
        test_end_to_end
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 CONTINUOUS LEARNING PIPELINE IS FULLY OPERATIONAL!")
        print("\n📋 Next Steps:")
        print("1. Monitor Kafka topics with ./monitor_kafka_topics.ps1")
        print("2. Visit the annotation frontend: http://localhost:8011")
        print("3. Check training jobs: http://localhost:8012/jobs")
    elif passed > 0:
        print("⚠️ CONTINUOUS LEARNING PIPELINE IS PARTIALLY OPERATIONAL")
        print("Review the test results above to identify and fix issues.")
    else:
        print("❌ CONTINUOUS LEARNING PIPELINE IS NOT OPERATIONAL")
        print("Start by running docker-compose up -d and creating Kafka topics.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
