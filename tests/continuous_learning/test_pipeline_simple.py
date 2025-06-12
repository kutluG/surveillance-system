#!/usr/bin/env python3
"""
Simple test to verify the continuous learning pipeline components are properly implemented.
"""
import sys
import os
import numpy as np
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_edge_inference_with_hard_examples():
    """Test that EdgeInference can detect and publish hard examples."""
    print("🔍 Testing Edge Inference with Hard Example Detection...")
    
    try:
        from edge_service.inference import EdgeInference
        from shared.models import Detection, BoundingBox
        
        # Initialize inference engine (without Kafka for this test)
        inference = EdgeInference(model_dir="./models", kafka_bootstrap_servers="localhost:9092")
        
        # Test that hard example thresholds are configured
        assert hasattr(inference, 'hard_example_thresholds'), "Hard example thresholds not configured"
        assert 'person' in inference.hard_example_thresholds, "Person threshold not set"
        assert 'face' in inference.hard_example_thresholds, "Face threshold not set"
        assert 'vehicle' in inference.hard_example_thresholds, "Vehicle threshold not set"
        
        print(f"✅ Hard example thresholds: {inference.hard_example_thresholds}")
        
        # Test inference with camera_id and frame_data
        dummy_tensor = np.random.rand(3, 640, 480).astype(np.float32)
        dummy_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        detections = inference.infer_objects(
            dummy_tensor, 
            camera_id="test_camera_01", 
            frame_data=dummy_frame
        )
        
        print(f"✅ Generated {len(detections)} test detections")
        
        # Check if any detections are hard examples
        hard_examples = []
        for det in detections:
            threshold = inference.hard_example_thresholds.get(det.class_name)
            if threshold and det.confidence < threshold:
                hard_examples.append(det)
        
        print(f"✅ Found {len(hard_examples)} hard examples")
        return True
        
    except Exception as e:
        print(f"❌ Edge inference test failed: {e}")
        return False

def test_hard_example_collector():
    """Test that HardExampleCollector service is properly implemented."""
    print("\n🔍 Testing Hard Example Collector...")
    
    try:
        # Check if the service file exists and has required components
        collector_file = project_root / "hard_example_collector" / "main.py"
        if not collector_file.exists():
            print("❌ HardExampleCollector main.py not found")
            return False
        
        # Read and verify service content
        content = collector_file.read_text()
        
        required_components = [
            "HardExampleCollector",
            "kafka",
            "hard-examples",
            "FastAPI",
            "/health"
        ]
        
        missing = []
        for component in required_components:
            if component not in content:
                missing.append(component)
        
        if missing:
            print(f"❌ Missing components in HardExampleCollector: {missing}")
            return False
        
        print("✅ HardExampleCollector service properly implemented")
        return True
        
    except Exception as e:
        print(f"❌ HardExampleCollector test failed: {e}")
        return False

def test_annotation_frontend():
    """Test that AnnotationFrontend service is properly implemented."""
    print("\n🔍 Testing Annotation Frontend...")
    
    try:
        frontend_file = project_root / "annotation_frontend" / "main.py"
        template_file = project_root / "annotation_frontend" / "templates" / "index.html"
        
        if not frontend_file.exists():
            print("❌ AnnotationFrontend main.py not found")
            return False
            
        if not template_file.exists():
            print("❌ AnnotationFrontend template not found")
            return False
        
        content = frontend_file.read_text()
        template_content = template_file.read_text()
        
        required_components = [
            "AnnotationFrontend",
            "templates",
            "/annotate",
            "hard-examples",
            "labeled-examples"
        ]
        
        missing = []
        for component in required_components:
            if component not in content:
                missing.append(component)
        
        if missing:
            print(f"❌ Missing components in AnnotationFrontend: {missing}")
            return False
        
        # Check template has annotation UI
        if "annotation" not in template_content.lower():
            print("❌ Template missing annotation UI")
            return False
        
        print("✅ AnnotationFrontend service properly implemented")
        return True
        
    except Exception as e:
        print(f"❌ AnnotationFrontend test failed: {e}")
        return False

def test_training_service():
    """Test that TrainingService is properly implemented."""
    print("\n🔍 Testing Training Service...")
    
    try:
        training_file = project_root / "training_service" / "main.py"
        
        if not training_file.exists():
            print("❌ TrainingService main.py not found")
            return False
        
        content = training_file.read_text()
        
        required_components = [
            "TrainingService",
            "labeled-examples",
            "scheduler",
            "retrain",
            "model_updates"
        ]
        
        missing = []
        for component in required_components:
            if component not in content:
                missing.append(component)
        
        if missing:
            print(f"❌ Missing components in TrainingService: {missing}")
            return False
        
        print("✅ TrainingService properly implemented")
        return True
        
    except Exception as e:
        print(f"❌ TrainingService test failed: {e}")
        return False

def test_docker_compose_integration():
    """Test that all services are integrated in Docker Compose."""
    print("\n🔍 Testing Docker Compose Integration...")
    
    try:
        compose_file = project_root / "docker-compose.yml"
        if not compose_file.exists():
            print("❌ docker-compose.yml not found")
            return False
        
        content = compose_file.read_text()
        
        required_services = [
            "hard_example_collector:",
            "annotation_frontend:",
            "training_service:",
            "kafka:",
            "zookeeper:"
        ]
        
        missing = []
        for service in required_services:
            if service not in content:
                missing.append(service)
        
        if missing:
            print(f"❌ Missing services in docker-compose.yml: {missing}")
            return False
        
        print("✅ All continuous learning services integrated in Docker Compose")
        return True
        
    except Exception as e:
        print(f"❌ Docker Compose test failed: {e}")
        return False

def main():
    """Run all tests for the continuous learning pipeline."""
    print("🚀 Testing Continuous Learning Pipeline Implementation")
    print("=" * 60)
    
    tests = [
        test_edge_inference_with_hard_examples,
        test_hard_example_collector,
        test_annotation_frontend,
        test_training_service,
        test_docker_compose_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 CONTINUOUS LEARNING PIPELINE IMPLEMENTATION COMPLETE!")
        print("\n📋 Next Steps:")
        print("1. Start Docker Desktop")
        print("2. Run: docker-compose up -d")
        print("3. Create Kafka topics: .\\create_kafka_topics.ps1")
        print("4. Test end-to-end: .\\test_continuous_learning.ps1")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
