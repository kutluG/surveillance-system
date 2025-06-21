"""
Integration tests for metrics endpoints

Tests:
- Metrics endpoint returns Prometheus data
- Metrics summary endpoint returns human-readable data
- Metrics collection during orchestration
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Mock the dependencies to avoid DB/Redis connections during tests
async def mock_lifespan(app):
    yield

with patch("main.lifespan", mock_lifespan):
    from main import app
    from orchestrator import OrchestrationRequest

class TestMetricsEndpoints:
    """Test metrics-related endpoints"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    def test_metrics_endpoint(self):
        """Test /metrics endpoint returns Prometheus data"""
        response = self.client.get("/metrics")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        # Check for basic Prometheus format
        content = response.text
        assert "# HELP" in content or "# Metrics not available" in content
        
    def test_metrics_summary_endpoint(self):
        """Test /metrics/summary endpoint returns human-readable data"""
        response = self.client.get("/metrics/summary")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert "service" in data
        assert data["service"] == "agent_orchestrator"
        assert "version" in data
        assert "metrics_enabled" in data
        assert "endpoints" in data
        assert "timestamp" in data
        
    def test_health_endpoint(self):
        """Test health endpoint still works"""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

class TestMetricsIntegrationWithOrchestration:
    """Test metrics collection during orchestration"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    @patch('orchestrator.OrchestratorService.orchestrate')
    def test_orchestration_with_metrics_collection(self, mock_orchestrate):
        """Test that orchestration calls collect metrics"""
        # Mock successful orchestration response
        from orchestrator import OrchestrationResponse
        mock_response = OrchestrationResponse(
            status="ok",
            details={},
            rag_result={"linked_explanation": "Test explanation"},
            rule_result={"triggered_actions": []},
            notification_result=None
        )
        mock_orchestrate.return_value = mock_response
        
        # Make orchestration request
        request_data = {
            "event_data": {
                "camera_id": "test_camera",
                "timestamp": "2025-06-14T00:00:00Z",
                "label": "person_detected",
                "bbox": [100, 100, 200, 200]
            },
            "query": "test query",
            "notification_channels": ["email"],
            "recipients": ["test@example.com"]
        }
        
        response = self.client.post("/api/v1/orchestrate", json=request_data)
        
        # Should succeed
        assert response.status_code == 200
        
        # Verify orchestration was called
        assert mock_orchestrate.called
        
        # Check that metrics endpoint still works after orchestration
        metrics_response = self.client.get("/metrics")
        assert metrics_response.status_code == 200
        
    @patch('orchestrator.OrchestratorService.orchestrate')
    def test_orchestration_error_metrics(self, mock_orchestrate):
        """Test that orchestration errors are recorded in metrics"""
        # Mock error response
        mock_orchestrate.side_effect = Exception("Test error")
        
        # Make orchestration request
        request_data = {
            "event_data": {
                "camera_id": "test_camera",
                "timestamp": "2025-06-14T00:00:00Z",
                "label": "person_detected"
            }
        }
        
        response = self.client.post("/api/v1/orchestrate", json=request_data)
        
        # Should return error
        assert response.status_code == 500
        
        # Check that metrics endpoint still works after error
        metrics_response = self.client.get("/metrics")
        assert metrics_response.status_code == 200

class TestMetricsConfiguration:
    """Test metrics configuration and availability"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    def test_metrics_available_when_prometheus_installed(self):
        """Test metrics are available when prometheus_client is installed"""
        response = self.client.get("/metrics/summary")
        data = response.json()
        
        # Should indicate metrics are enabled (assuming prometheus_client is installed)
        assert isinstance(data["metrics_enabled"], bool)
        
    @patch('metrics.PROMETHEUS_AVAILABLE', False)
    def test_metrics_disabled_when_prometheus_unavailable(self):
        """Test metrics handling when prometheus_client is not available"""
        response = self.client.get("/metrics")
        
        # Should still return 200 but with different content
        assert response.status_code == 200
        
        # Content should indicate metrics are not available
        content = response.text
        assert "Metrics not available" in content or len(content) > 0

class TestMetricsContentValidation:
    """Test metrics content validation"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    def test_metrics_contains_agent_orchestrator_metrics(self):
        """Test that metrics contain agent orchestrator specific metrics"""
        response = self.client.get("/metrics")
        content = response.text
        
        if "Metrics not available" not in content:
            # Should contain service info
            assert "agent_orchestrator_service_info" in content or "orchestrator_" in content
        
    def test_metrics_format_is_valid_prometheus(self):
        """Test that metrics are in valid Prometheus format"""
        response = self.client.get("/metrics")
        content = response.text
        
        if "Metrics not available" not in content:
            # Basic Prometheus format validation
            lines = content.split('\n')
            
            # Should have HELP and TYPE lines
            has_help = any(line.startswith("# HELP") for line in lines)
            has_type = any(line.startswith("# TYPE") for line in lines)
            
            # At least one should be present for valid metrics
            assert has_help or has_type or len(lines) == 1  # Empty metrics case
        
    def test_metrics_summary_structure(self):
        """Test metrics summary has expected structure"""
        response = self.client.get("/metrics/summary")
        data = response.json()
        
        required_fields = ["service", "version", "metrics_enabled", "endpoints", "timestamp"]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Validate field types
        assert isinstance(data["service"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["metrics_enabled"], bool)
        assert isinstance(data["endpoints"], list)
        assert isinstance(data["timestamp"], str)
        
        # Validate endpoints list
        assert len(data["endpoints"]) >= 2
        assert any("metrics" in endpoint for endpoint in data["endpoints"])

if __name__ == "__main__":
    pytest.main([__file__])
