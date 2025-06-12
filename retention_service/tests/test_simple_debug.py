#!/usr/bin/env python3
"""
Simple diagnostic test to verify the issue.
"""

print("Starting diagnostic test...")

try:
    print("Testing basic imports...")
    import os
    import tempfile
    print("Basic imports work")
    
    # Set environment
    test_storage = tempfile.mkdtemp()
    os.environ["DB_URL"] = "sqlite:///./test_simple.db"
    os.environ["STORAGE_PATH"] = test_storage
    os.environ["RETENTION_DAYS"] = "7"
    print("Environment set")
      # Test FastAPI import  
    print("Testing FastAPI import...")
    from starlette.testclient import TestClient
    print("TestClient import works")
    
    # Test retention service import
    print("Testing retention service import...")
    from retention_service.main import app
    print("Retention service import works")    # Create test client
    print("Creating test client...")
    with TestClient(app) as client:
        print("Test client created")
        
        # Simple health check
        print("Testing health endpoint...")
        response = client.get("/health")
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.json()}")
    
    print("Test completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
