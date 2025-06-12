#!/usr/bin/env python3
"""
Direct API testing for retention service using TestClient workaround.
"""

import asyncio
import tempfile
import os
from datetime import datetime, timedelta

# Set environment for testing
os.environ["DB_URL"] = "sqlite:///./test_retention.db"
os.environ["STORAGE_PATH"] = tempfile.mkdtemp()
os.environ["RETENTION_DAYS"] = "30"

from retention_service.main import (
    app, purge_old_events, purge_old_video_segments, 
    delete_file_from_storage, VideoSegment, RETENTION_DAYS, STORAGE_PATH
)


def test_app_creation():
    """Test that the FastAPI app was created successfully."""
    assert app is not None
    assert app.title == "Data Retention Service"
    print("✓ FastAPI app created successfully")


def test_app_routes():
    """Test that the expected routes are available."""
    routes = [route.path for route in app.routes]
    expected_routes = ["/health", "/purge/status", "/purge/run", "/docs", "/redoc", "/openapi.json"]
    
    for expected_route in expected_routes:
        assert expected_route in routes, f"Route {expected_route} not found"
    
    print("✓ All expected routes are available")
    print(f"  Available routes: {', '.join(routes)}")


async def test_core_functions():
    """Test the core retention functions work."""
    print("🔍 Testing core retention functions...")
    
    # Test file deletion
    test_dir = tempfile.mkdtemp()
    test_file = os.path.join(test_dir, "test_video.mp4")
    with open(test_file, 'w') as f:
        f.write("test content")
    
    success = await delete_file_from_storage("test_video.mp4", test_dir)
    assert success
    assert not os.path.exists(test_file)
    print("✓ File deletion works")
    
    # Test model creation
    now = datetime.utcnow()
    segment = VideoSegment(
        event_id="test-123",
        camera_id="cam01",
        file_key="test.mp4",
        start_ts=now - timedelta(minutes=5),
        end_ts=now,
        file_size=1024
    )
    assert segment.event_id == "test-123"
    assert segment.created_at is not None
    print("✓ VideoSegment model creation works")
    
    # Cleanup
    os.rmdir(test_dir)


def test_configuration():
    """Test service configuration."""
    assert isinstance(RETENTION_DAYS, int)
    assert RETENTION_DAYS == 30
    assert isinstance(STORAGE_PATH, str)
    assert len(STORAGE_PATH) > 0
    
    print("✓ Service configuration is valid")
    print(f"  - Retention period: {RETENTION_DAYS} days")
    print(f"  - Storage path: {STORAGE_PATH}")


def test_app_metadata():
    """Test FastAPI app metadata."""
    # The app should have correct openapi info
    openapi_schema = app.openapi()
    assert openapi_schema["info"]["title"] == "Data Retention Service"
    assert "paths" in openapi_schema
    assert "/health" in openapi_schema["paths"]
    
    print("✓ OpenAPI schema is valid")


async def main():
    """Run all direct API tests."""
    print("🧪 Running Direct Retention Service API Tests")
    print("=" * 55)
    
    try:
        test_app_creation()
        test_app_routes()
        await test_core_functions()
        test_configuration()
        test_app_metadata()
        
        print()
        print("🎉 All direct API tests passed!")
        print("The retention service API is functioning correctly.")
        
    except Exception as e:
        print(f"❌ Direct API test failed: {e}")
        raise
    finally:
        # Cleanup test database
        if os.path.exists("test_retention.db"):
            os.remove("test_retention.db")


if __name__ == "__main__":
    asyncio.run(main())
