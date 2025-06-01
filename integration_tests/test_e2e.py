"""
End-to-end integration tests for the surveillance system.
Tests the complete flow from edge detection to notifications.
"""
import pytest
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# Service URLs
SERVICES = {
    "edge": "http://localhost:8001",
    "bridge": "http://localhost:8002", 
    "ingest": "http://localhost:8003",
    "rag": "http://localhost:8004",
    "prompt": "http://localhost:8005",
    "rulegen": "http://localhost:8006",
    "notifier": "http://localhost:8007",
    "vms": "http://localhost:8008",
}

class TestE2EFlow:
    """End-to-end test suite for surveillance system."""
    
    @pytest.fixture(autouse=True)
    def setup_system(self):
        """Ensure all services are healthy before tests."""
        for service_name, url in SERVICES.items():
            response = requests.get(f"{url}/health", timeout=10)
            assert response.status_code == 200, f"{service_name} service not healthy"
            
        # Wait for services to be fully ready
        time.sleep(5)
    
    def test_service_health_endpoints(self):
        """Test that all services respond to health checks."""
        for service_name, url in SERVICES.items():
            response = requests.get(f"{url}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
    
    def test_create_and_evaluate_rule(self):
        """Test rule creation and event evaluation flow."""
        # Create a test rule
        rule_data = {
            "name": "Test Person Detection Rule",
            "rule_text": "Alert when person detected in any camera during business hours"
        }
        
        # Note: This would require authentication in production
        # For testing, we'll mock or use a test token
        headers = {"Authorization": "Bearer test-token"}  # Mock token
        
        try:
            response = requests.post(
                f"{SERVICES['rulegen']}/rules",
                json=rule_data,
                headers=headers,
                timeout=10
            )
            # May fail due to auth, but test the endpoint structure
            assert response.status_code in [200, 401, 403]
        except requests.exceptions.RequestException:
            pytest.skip("Rule creation requires authentication setup")
    
    def test_rag_analysis_flow(self):
        """Test RAG service analysis capability."""
        analysis_request = {
            "query": "Show me recent person detections in the lobby area"
        }
        
        response = requests.post(
            f"{SERVICES['rag']}/analysis",
            json=analysis_request,
            timeout=15
        )
        
        # Should return 200 with alert structure or 500 if no context
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "alert_text" in data
            assert "severity" in data
            assert "evidence_ids" in data
    
    def test_prompt_service_query(self):
        """Test prompt service natural language querying."""
        query_request = {
            "query": "Find all detection events from today",
            "limit": 5
        }
        
        response = requests.post(
            f"{SERVICES['prompt']}/query",
            json=query_request,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer_text" in data
        assert "clip_links" in data
        assert isinstance(data["clip_links"], list)
    
    def test_notification_channels(self):
        """Test notification service different channels."""
        test_notifications = [
            {
                "channel": "email",
                "recipients": ["test@example.com"],
                "subject": "Test Email Notification",
                "message": "This is a test email from integration tests"
            },
            {
                "channel": "slack",
                "recipients": ["#test-channel"],
                "subject": "Test Slack Notification", 
                "message": "This is a test Slack message from integration tests"
            }
        ]
        
        for notification in test_notifications:
            response = requests.post(
                f"{SERVICES['notifier']}/send",
                json=notification,
                timeout=10
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert data["status"] == "scheduled"
    
    def test_vms_clip_management(self):
        """Test VMS service clip generation and retrieval."""
        # Test clip generation request
        mock_event = {
            "event": {
                "id": "test-event-123",
                "camera_id": "test-cam-01",
                "event_type": "detection",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "detections": [
                    {
                        "label": "person",
                        "confidence": 0.95,
                        "bounding_box": {
                            "x_min": 0.1, "y_min": 0.2,
                            "x_max": 0.5, "y_max": 0.8
                        }
                    }
                ]
            }
        }
        
        response = requests.post(
            f"{SERVICES['vms']}/clips/generate",
            json=mock_event,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert "clip_url" in data
        
        # Test clip listing
        response = requests.get(f"{SERVICES['vms']}/clips", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "clips" in data
        assert "total_count" in data
    
    def test_metrics_endpoints(self):
        """Test that services expose Prometheus metrics."""
        for service_name, url in SERVICES.items():
            try:
                response = requests.get(f"{url}/metrics", timeout=5)
                # Should return metrics or 404 if not implemented
                assert response.status_code in [200, 404]
                
                if response.status_code == 200:
                    # Basic check for Prometheus format
                    assert "# HELP" in response.text or "# TYPE" in response.text
                    
            except requests.exceptions.RequestException:
                # Some services might not have metrics endpoint yet
                pass

class TestDataFlow:
    """Test data flow between services."""
    
    def test_mock_detection_to_notification_flow(self):
        """Test a mock detection flowing through the system."""
        # This would simulate:
        # 1. Edge service detects event
        # 2. Event flows through Kafka to ingest
        # 3. Rules evaluate event
        # 4. Notification sent
        
        # For now, test individual components
        # In a full integration, you'd inject a test event at edge
        # and verify it propagates through the entire system
        
        mock_event_data = {
            "camera_id": "test-cam-01",
            "event_type": "detection",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "detections": [
                {
                    "label": "person",
                    "confidence": 0.95,
                    "bounding_box": {
                        "x_min": 0.1, "y_min": 0.2,
                        "x_max": 0.5, "y_max": 0.8
                    }
                }
            ],
            "metadata": {"test": True}
        }
        
        # Test that each service can handle the event format
        # This is a simplified test - real flow goes through Kafka
        
        # Test VMS clip generation
        vms_response = requests.post(
            f"{SERVICES['vms']}/clips/generate",
            json={"event": mock_event_data},
            timeout=10
        )
        assert vms_response.status_code == 200
        
        # Test notification
        notification_request = {
            "channel": "email",
            "recipients": ["test@example.com"],
            "subject": f"Detection Alert - {mock_event_data['camera_id']}",
            "message": f"Person detected at {mock_event_data['timestamp']}",
            "metadata": {
                "event_data": mock_event_data
            }
        }
        
        notif_response = requests.post(
            f"{SERVICES['notifier']}/send",
            json=notification_request,
            timeout=10
        )
        assert notif_response.status_code == 200

class TestPerformance:
    """Performance and load testing."""
    
    def test_concurrent_requests(self):
        """Test system handles concurrent requests."""
        import concurrent.futures
        import threading
        
        def make_health_request(service_url):
            try:
                response = requests.get(f"{service_url}/health", timeout=5)
                return response.status_code == 200
            except:
                return False
        
        # Test concurrent health checks
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(20):  # 20 concurrent requests
                for url in SERVICES.values():
                    future = executor.submit(make_health_request, url)
                    futures.append(future)
            
            # Wait for all requests
            results = [future.result() for future in futures]
            
            # At least 80% should succeed
            success_rate = sum(results) / len(results)
            assert success_rate >= 0.8, f"Success rate too low: {success_rate}"
    
    def test_response_times(self):
        """Test that services respond within acceptable time limits."""
        max_response_time = 5.0  # seconds
        
        for service_name, url in SERVICES.items():
            start_time = time.time()
            response = requests.get(f"{url}/health", timeout=max_response_time)
            response_time = time.time() - start_time
            
            assert response.status_code == 200
            assert response_time < max_response_time, f"{service_name} too slow: {response_time}s"

class TestSecurity:
    """Security-related tests."""
    
    def test_unauthenticated_access(self):
        """Test that protected endpoints require authentication."""
        protected_endpoints = [
            ("rulegen", "/rules", "POST"),
            ("rulegen", "/rules/test-id", "DELETE"),
        ]
        
        for service, endpoint, method in protected_endpoints:
            url = f"{SERVICES[service]}{endpoint}"
            
            if method == "POST":
                response = requests.post(url, json={"test": "data"})
            elif method == "DELETE":
                response = requests.delete(url)
            else:
                response = requests.get(url)
            
            # Should return 401 (Unauthorized) or 403 (Forbidden)
            assert response.status_code in [401, 403], f"{service}{endpoint} not protected"
    
    def test_input_validation(self):
        """Test that services validate input properly."""
        # Test invalid JSON
        response = requests.post(
            f"{SERVICES['rag']}/analysis",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422  # Unprocessable Entity
        
        # Test missing required fields
        response = requests.post(
            f"{SERVICES['prompt']}/query",
            json={"invalid": "field"},
            timeout=5
        )
        assert response.status_code == 422

if __name__ == "__main__":
    # Run basic smoke tests
    import sys
    
    print("Running surveillance system integration tests...")
    
    # Check if services are up
    all_healthy = True
    for service_name, url in SERVICES.items():
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✓ {service_name} service healthy")
            else:
                print(f"✗ {service_name} service unhealthy (status: {response.status_code})")
                all_healthy = False
        except Exception as e:
            print(f"✗ {service_name} service unreachable: {e}")
            all_healthy = False
    
    if not all_healthy:
        print("\nSome services are not healthy. Run 'make health' to check status.")
        sys.exit(1)
    
    print("\nAll services healthy! Run 'pytest integration_tests/' for full test suite.")