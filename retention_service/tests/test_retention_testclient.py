#!/usr/bin/env python3
"""
Test retention service HTTP endpoints using FastAPI TestClient.
"""

import os
import tempfile
from fastapi.testclient import TestClient

# Set test environment
test_storage = tempfile.mkdtemp()
os.environ["DB_URL"] = "sqlite:///./test_endpoints.db"
os.environ["STORAGE_PATH"] = test_storage
os.environ["RETENTION_DAYS"] = "7"

print("🧪 HTTP Endpoint Tests")
print("=" * 30)

try:
    # Import after setting environment
    from retention_service.main import app
    
    # Create test client
    client = TestClient(app)
    
    # Test health endpoint
    print("🔍 Testing /health endpoint...")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    print("✓ Health endpoint working")
    
    # Test status endpoint
    print("🔍 Testing /purge/status endpoint...")
    response = client.get("/purge/status")
    assert response.status_code == 200
    data = response.json()
    assert "retention_days" in data
    assert "storage_path" in data
    assert "storage_type" in data
    assert data["retention_days"] == 7
    print("✓ Status endpoint working")
    print(f"  - Retention period: {data['retention_days']} days")
    print(f"  - Storage type: {data['storage_type']}")
    
    # Test run endpoint (dry run)
    print("🔍 Testing /purge/run endpoint (dry run)...")
    response = client.post("/purge/run?dry_run=true")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "summary" in data
    assert data["status"] == "completed"
    print("✓ Run endpoint working (dry run)")
    print(f"  - Files would be deleted: {data['summary']['files_deleted']}")
    print(f"  - Records would be deleted: {data['summary']['records_deleted']}")
    
    # Test OpenAPI docs
    print("🔍 Testing /docs endpoint...")
    response = client.get("/docs")
    assert response.status_code == 200
    print("✓ OpenAPI docs endpoint working")
    
    # Test OpenAPI schema
    print("🔍 Testing /openapi.json endpoint...")
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "/health" in schema["paths"]
    assert "/purge/status" in schema["paths"]
    assert "/purge/run" in schema["paths"]
    print("✓ OpenAPI schema endpoint working")
    
    print()
    print("🎉 ALL HTTP ENDPOINT TESTS PASSED!")
    print("The retention service REST API is fully functional.")
    
except Exception as e:
    print(f"❌ HTTP endpoint test failed: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    # Cleanup
    import shutil
    if os.path.exists("test_endpoints.db"):
        os.remove("test_endpoints.db")
    if os.path.exists(test_storage):
        shutil.rmtree(test_storage)
    print("🧹 Cleanup completed")
