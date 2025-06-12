#!/usr/bin/env python3
"""
Simple integration test for the retention service.
"""

import asyncio
import os
import tempfile
import shutil
from datetime import datetime, timedelta

def test_service_import():
    """Test that the retention service can be imported."""
    try:
        from retention_service.main import app, VideoSegment, delete_file_from_storage
        print("✓ Retention service imports successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_fastapi_app():
    """Test FastAPI app creation."""
    try:
        from fastapi.testclient import TestClient
        from retention_service.main import app
        
        client = TestClient(app)
        response = client.get("/health")
        
        if response.status_code == 200:
            print("✓ FastAPI health endpoint working")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ FastAPI test failed: {e}")
        return False

async def test_file_operations():
    """Test file deletion operations."""
    try:
        from retention_service.main import delete_file_from_storage
        
        # Create temporary directory and file
        temp_dir = tempfile.mkdtemp()
        test_file = os.path.join(temp_dir, "test.mp4")
        
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Test deletion
        success = await delete_file_from_storage("test.mp4", temp_dir)
        
        if success and not os.path.exists(test_file):
            print("✓ File deletion working")
            shutil.rmtree(temp_dir)
            return True
        else:
            print("❌ File deletion failed")
            shutil.rmtree(temp_dir)
            return False
            
    except Exception as e:
        print(f"❌ File operations test failed: {e}")
        return False

def test_model_creation():
    """Test VideoSegment model."""
    try:
        from retention_service.main import VideoSegment
        
        now = datetime.utcnow()
        segment = VideoSegment(
            event_id="test-123",
            camera_id="cam01", 
            file_key="test.mp4",
            start_ts=now - timedelta(minutes=5),
            end_ts=now,
            file_size=1024
        )
        
        if segment.event_id == "test-123" and segment.created_at is not None:
            print("✓ VideoSegment model working")
            return True
        else:
            print("❌ VideoSegment model failed")
            return False
            
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

async def main():
    """Run simple integration tests."""
    print("🧪 Running Simple Retention Service Tests")
    print("=" * 45)
    
    results = []
    
    # Run tests
    results.append(test_service_import())
    results.append(test_fastapi_app())
    results.append(await test_file_operations())
    results.append(test_model_creation())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print()
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Retention service is ready.")
    else:
        print("❌ Some tests failed. Check the output above.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())
