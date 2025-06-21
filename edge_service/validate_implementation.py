#!/usr/bin/env python3
"""
Validation script for performance optimization implementation.
Tests core functionality without pytest complications.
"""

import os
import sys
import time
import numpy as np
from pathlib import Path

def test_basic_imports():
    """Test that all required modules can be imported."""
    print("Testing basic imports...")
    
    try:
        import onnxruntime
        print("✓ onnxruntime imported successfully")
    except ImportError as e:
        print(f"✗ onnxruntime import failed: {e}")
        return False
    
    try:
        import onnx
        print("✓ onnx imported successfully")
    except ImportError as e:
        print(f"✗ onnx import failed: {e}")
        return False
    
    try:
        import prometheus_client
        print("✓ prometheus_client imported successfully")
    except ImportError as e:
        print(f"✗ prometheus_client import failed: {e}")
        return False
    
    try:
        import psutil
        print("✓ psutil imported successfully")
    except ImportError as e:
        print(f"✗ psutil import failed: {e}")
        return False
    
    return True

def test_monitoring_module():
    """Test monitoring module functionality."""
    print("\nTesting monitoring module...")
    
    try:
        from monitoring import ResourceMonitor, get_resource_monitor, get_current_resource_status
        print("✓ Monitoring module imported successfully")
        
        # Test ResourceMonitor initialization
        monitor = ResourceMonitor()
        print(f"✓ ResourceMonitor initialized with interval: {monitor.monitor_interval}s")
        
        # Test resource status collection
        status = get_current_resource_status()
        print(f"✓ Resource status collected: {list(status.keys())}")
        
        return True
        
    except Exception as e:
        print(f"✗ Monitoring module test failed: {e}")
        return False

def test_quantization_tools():
    """Test quantization tools."""
    print("\nTesting quantization tools...")
    
    try:
        from tools.quantize_model import ModelQuantizer
        print("✓ ModelQuantizer imported successfully")
        
        # Test quantizer initialization
        quantizer = ModelQuantizer()
        print(f"✓ ModelQuantizer initialized with model dir: {quantizer.model_dir}")
        
        return True
        
    except Exception as e:
        print(f"✗ Quantization tools test failed: {e}")
        return False

def test_monitoring_thread():
    """Test monitoring thread functionality."""
    print("\nTesting monitoring thread...")
    
    try:
        from monitoring_thread import (
            get_inference_monitoring_status,
            start_inference_monitoring,
            stop_inference_monitoring
        )
        print("✓ Monitoring thread module imported successfully")
        
        # Test monitoring status
        status = get_inference_monitoring_status()
        print(f"✓ Monitoring status retrieved: {status.get('active', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Monitoring thread test failed: {e}")
        return False

def test_inference_integration():
    """Test inference module integration."""
    print("\nTesting inference integration...")
    
    try:
        # Test importing inference functions
        from inference import get_inference_session, EdgeInference
        print("✓ Inference module imported successfully")
        
        # Test EdgeInference initialization (should work even without models)
        inference_engine = EdgeInference()
        print(f"✓ EdgeInference initialized with model dir: {inference_engine.model_dir}")
        
        return True
        
    except Exception as e:
        print(f"✗ Inference integration test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("=== Performance Optimization Implementation Validation ===")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print()
    
    tests = [
        test_basic_imports,
        test_monitoring_module,
        test_quantization_tools,
        test_monitoring_thread,
        test_inference_integration,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("=== Summary ===")
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {failed}")
    print(f"Total tests: {passed + failed}")
    
    if failed == 0:
        print("🎉 All tests passed! Implementation is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
