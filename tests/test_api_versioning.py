#!/usr/bin/env python3
"""
API Versioning Tests for FastAPI Services - Fixed Version

This test suite validates that API versioning is properly implemented with:
1. Backwards compatibility redirects (HTTP 301) 
2. Direct versioned endpoint access (HTTP 200)

Uses requests library to avoid TestClient compatibility issues.
"""

import pytest
import requests
import sys
import os
import time
import threading
import uvicorn
import socket

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the API Gateway application
from api_gateway.main import app


def find_free_port():
    """Find a free port to run the test server on"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope="module")
def test_server():
    """Start a test server for the duration of the test module"""
    port = find_free_port()
    server_thread = threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={
            "host": "127.0.0.1",
            "port": port,
            "log_level": "error"
        },
        daemon=True
    )
    server_thread.start()
    
    # Wait for server to start
    base_url = f"http://127.0.0.1:{port}"
    timeout = 10
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/health", timeout=1.0)
            if response.status_code in [200, 404]:  # 404 is fine, server is running
                break
        except:
            pass
        time.sleep(0.1)
    else:
        raise RuntimeError(f"Test server failed to start on {base_url}")
    
    yield base_url


def test_unversioned_alerts_endpoint_redirects(test_server):
    """
    Test: Call an old unversioned endpoint `/api/alerts` and assert it returns a 301 
    with `Location: /api/v1/alerts`.
    """
    response = requests.get(f"{test_server}/api/alerts", allow_redirects=False)
    
    # Assert HTTP 301 (Moved Permanently)
    assert response.status_code == 301, f"Expected 301 redirect but got {response.status_code}"
    
    # Assert Location header points to versioned endpoint
    location = response.headers.get("location")
    assert location == "/api/v1/alerts", f"Expected Location: /api/v1/alerts but got {location}"
    
    # Assert custom version redirect header is present
    version_header = response.headers.get("X-API-Version-Redirect")
    assert version_header == "v1", f"Expected X-API-Version-Redirect: v1 but got {version_header}"
    
    print("✅ Unversioned alerts endpoint correctly redirects to v1")
    print(f"   - Status: {response.status_code}")
    print(f"   - Location: {location}")
    print(f"   - Redirect Header: {version_header}")


def test_versioned_alerts_endpoint_direct_access(test_server):
    """
    Test: Call `/api/v1/alerts` directly and assert HTTP 200 and correct schema.
    """
    response = requests.get(f"{test_server}/api/v1/alerts")
    
    # Assert HTTP 200 (Success)
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}"
    
    # Assert response is JSON
    content_type = response.headers.get("content-type", "")
    assert content_type.startswith("application/json"), \
        f"Expected JSON response but got {content_type}"
    
    # Parse JSON response
    data = response.json()
    
    # Assert basic structure (alerts endpoint should return a list or dict with alerts)
    assert isinstance(data, (list, dict)), f"Expected list or dict but got {type(data)}"
    
    if isinstance(data, dict):
        # If it's a dict, it should have some standard fields
        assert "alerts" in data or "data" in data or "items" in data, \
            f"Expected alerts/data/items key in response: {list(data.keys())}"
    
    print("✅ Versioned alerts endpoint returns HTTP 200 with correct schema")
    print(f"   - Status: {response.status_code}")
    print(f"   - Content-Type: {content_type}")
    print(f"   - Response type: {type(data)}")


if __name__ == "__main__":
    # Run tests directly if executed as a script
    pytest.main([__file__, "-v"])