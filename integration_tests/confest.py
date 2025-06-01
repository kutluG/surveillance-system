"""
Pytest configuration and fixtures for integration tests.
"""
import pytest
import requests
import time
import json
from typing import Dict, Any

@pytest.fixture(scope="session")
def service_urls():
    """Service URLs for testing."""
    return {
        "edge": "http://localhost:8001",
        "bridge": "http://localhost:8002",
        "ingest": "http://localhost:8003", 
        "rag": "http://localhost:8004",
        "prompt": "http://localhost:8005",
        "rulegen": "http://localhost:8006",
        "notifier": "http://localhost:8007",
        "vms": "http://localhost:8008",
    }

@pytest.fixture(scope="session")
def wait_for_services(service_urls):
    """Wait for all services to be healthy before running tests."""
    max_retries = 30
    retry_delay = 2
    
    for service_name, url in service_urls.items():
        for attempt in range(max_retries):
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    print(f"✓ {service_name} service ready")
                    break
            except requests.exceptions.RequestException:
                pass
            
            if attempt == max_retries - 1:
                pytest.fail(f"Service {service_name} not ready after {max_retries} attempts")
            
            time.sleep(retry_delay)

@pytest.fixture
def mock_camera_event():
    """Sample camera event for testing."""
    return {
        "id": "test-event-123",
        "camera_id": "test-cam-01", 
        "event_type": "detection",
        "timestamp": "2025-05-31T10:39:22Z",
        "detections": [
            {
                "label": "person",
                "confidence": 0.95,
                "bounding_box": {
                    "x_min": 0.1,
                    "y_min": 0.2,
                    "x_max": 0.5,
                    "y_max": 0.8
                }
            }
        ],
        "metadata": {
            "test": True,
            "integration_test": True
        }
    }

@pytest.fixture
def auth_headers():
    """Mock authentication headers for testing."""
    return {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json"
    }

@pytest.fixture
def sample_rule():
    """Sample security rule for testing."""
    return {
        "name": "Test Integration Rule",
        "description": "Rule created during integration testing",
        "rule_text": "Alert security when person detected during business hours"
    }

@pytest.fixture
def sample_notification():
    """Sample notification request for testing.""" 
    return {
        "channel": "email",
        "recipients": ["integration-test@example.com"],
        "subject": "Integration Test Notification",
        "message": "This notification was sent during integration testing",
        "metadata": {
            "test": True,
            "timestamp": "2025-05-31T10:39:22Z"
        }
    }

class ApiClient:
    """Helper class for making API requests during tests."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Make GET request."""
        return self.session.get(f"{self.base_url}{endpoint}", **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Make POST request."""
        return self.session.post(f"{self.base_url}{endpoint}", **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """Make PUT request."""
        return self.session.put(f"{self.base_url}{endpoint}", **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make DELETE request."""
        return self.session.delete(f"{self.base_url}{endpoint}", **kwargs)

@pytest.fixture
def api_clients(service_urls):
    """API clients for each service."""
    return {
        name: ApiClient(url) 
        for name, url in service_urls.items()
    }

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "load: marks tests as load tests"
    )

def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their location."""
    for item in items:
        # Mark all tests in this directory as integration tests
        item.add_marker(pytest.mark.integration)
        
        # Mark load tests
        if "load" in item.nodeid:
            item.add_marker(pytest.mark.load)
            item.add_marker(pytest.mark.slow)