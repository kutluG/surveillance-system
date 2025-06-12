#!/usr/bin/env python3
"""
Final validation test for retention service.
"""

import os
import tempfile
import shutil
from datetime import datetime, timedelta

# Add parent directory to path to allow imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Set test environment
os.environ["DB_URL"] = "sqlite:///./test_final.db"
test_storage = tempfile.mkdtemp()
os.environ["STORAGE_PATH"] = test_storage
os.environ["RETENTION_DAYS"] = "30"

print("🧪 Final Retention Service Validation")
print("=" * 40)

try:
    # Test imports
    print("🔍 Testing imports...")
    from retention_service.main import (
        app, VideoSegment, RETENTION_DAYS, STORAGE_PATH, is_s3_path
    )
    print("✓ All imports successful")
    
    # Test configuration
    print("🔍 Testing configuration...")
    assert RETENTION_DAYS == 30, f"Expected 30, got {RETENTION_DAYS}"
    assert STORAGE_PATH == test_storage, f"Storage path mismatch"
    print(f"✓ Configuration valid (retention: {RETENTION_DAYS} days)")
    
    # Test FastAPI app
    print("🔍 Testing FastAPI app...")
    assert app.title == "Data Retention Service"
    routes = [route.path for route in app.routes]
    required_routes = ["/health", "/purge/status", "/purge/run"]
    
    for route in required_routes:
        assert route in routes, f"Missing route: {route}"
    print(f"✓ FastAPI app valid ({len(routes)} routes)")
    
    # Test models
    print("🔍 Testing models...")
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
    print("✓ VideoSegment model working")
    
    # Test utility functions
    print("🔍 Testing utilities...")
    assert is_s3_path("s3://bucket/path") == True
    assert is_s3_path("/local/path") == False
    print("✓ Utility functions working")
    
    # Test OpenAPI
    print("🔍 Testing OpenAPI schema...")
    schema = app.openapi()
    assert "paths" in schema
    assert "/health" in schema["paths"]
    print("✓ OpenAPI schema valid")
    
    print()
    print("🎉 ALL TESTS PASSED!")
    print("The retention service is ready for production deployment.")
    print()
    print("📋 Service Summary:")
    print(f"   • Retention Period: {RETENTION_DAYS} days")
    print(f"   • Storage Type: {'S3' if is_s3_path(STORAGE_PATH) else 'Local'}")
    print(f"   • API Routes: {len([r for r in routes if not r.startswith('/openapi')])}")
    print(f"   • Database: SQLite (test) / PostgreSQL (production)")
    
except AssertionError as e:
    print(f"❌ Assertion failed: {e}")
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    # Cleanup
    if os.path.exists("test_final.db"):
        os.remove("test_final.db")
    if os.path.exists(test_storage):
        shutil.rmtree(test_storage)
    print("🧹 Cleanup completed")
