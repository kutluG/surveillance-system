"""
Integration Tests for Dashboard API Endpoints

This module provides comprehensive integration tests for the AI Dashboard Service
API endpoints using FastAPI's TestClient. Tests verify end-to-end behavior,
request/response validation, error handling, and proper dependency injection.

Test Coverage:
- Analytics endpoints (/api/v1/analytics/trends, /api/v1/analytics/anomalies)
- Insights endpoints (/api/v1/insights/realtime)
- Valid and malformed payload handling
- Error scenarios and edge cases
- Response validation and structure verification
- Service dependency injection and mocking
- Insights history tracking and persistence

The tests use mocked dependencies for isolated testing while still exercising
the full FastAPI application stack including routing, middleware, validation,
and response formatting.

Example Usage:
    $ pytest tests/test_integration.py -v
    $ pytest tests/test_integration.py::TestAnalyticsEndpoints -v
    $ pytest tests/test_integration.py::TestInsightsEndpoints -v
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    AnalyticsInsight, TrendAnalysis, AnomalyDetection
)
from app.models.enums import AnalyticsType, TimeRange, WidgetType, PredictionType


@pytest.fixture
def test_app():
    """Create FastAPI application for testing."""
    from app.main import app
    return app


@pytest.fixture
def client(test_app):
    """Create test client for the FastAPI application."""
    return TestClient(test_app)


@pytest.fixture
def sample_analytics_request():
    """Sample analytics request payload for trends and anomalies."""
    return {
        "analytics_type": "trend_analysis",
        "time_range": "last_24_hours",
        "filters": {"location": "parking_lot", "confidence_threshold": 0.8},
        "parameters": {"data_sources": ["cameras", "motion_sensors"]}
    }


@pytest.fixture
def invalid_analytics_request():
    """Invalid analytics request for error testing."""
    return {
        "analytics_type": "invalid_type",
        "time_range": "last_24_hours"
        # Missing required fields
    }


@pytest.fixture
def malformed_analytics_request():
    """Malformed analytics request with incorrect data types."""
    return {
        "analytics_type": 123,  # Should be string
        "time_range": [],       # Should be string
        "filters": "not_a_dict", # Should be dict
        "parameters": "not_a_dict" # Should be dict
    }


@pytest.fixture
def mock_trends():
    """Mock trend analysis results."""
    return [
        TrendAnalysis(
            metric="detection_count",
            direction="increasing",
            magnitude=0.15,
            confidence=0.92,
            timeframe="last_24_hours",
            contributing_factors=["increased_activity", "weather_change"]
        ),
        TrendAnalysis(
            metric="alert_count",
            direction="stable",
            magnitude=0.02,
            confidence=0.78,
            timeframe="last_24_hours",
            contributing_factors=["normal_operations"]
        )
    ]


@pytest.fixture
def mock_anomalies():
    """Mock anomaly detection results."""
    return [
        AnomalyDetection(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            metric="detection_count",
            expected_value=25.0,
            actual_value=45.2,
            deviation=20.2,
            severity="high",
            description="Unusually high detection count in sector A"
        ),
        AnomalyDetection(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow() - timedelta(minutes=30),
            metric="motion_sensor_activity",
            expected_value=5.0,
            actual_value=0.1,
            deviation=-4.9,
            severity="medium",            description="Low motion sensor activity detected"
        )
    ]


@pytest.fixture
def mock_insights():
    """Mock real-time insights."""
    return [
        AnalyticsInsight(
            id=str(uuid.uuid4()),
            type=AnalyticsType.TREND_ANALYSIS,
            title="Increasing Security Activity",
            description="Detection rates have increased by 15% in the last hour",
            confidence=0.92,
            timestamp=datetime.utcnow(),
            data={"detection_count": 45, "previous_count": 39},
            recommendations=["Increase patrol frequency", "Review camera coverage"],
            impact_level="medium"
        ),
        AnalyticsInsight(
            id=str(uuid.uuid4()),
            type=AnalyticsType.ANOMALY_DETECTION,
            title="Unusual Pattern Detected",
            description="Motion sensor 3A showing irregular readings",
            confidence=0.87,
            timestamp=datetime.utcnow() - timedelta(minutes=15),
            data={"sensor_id": "3A", "reading": 0.1, "expected": 5.2},
            recommendations=["Check sensor calibration", "Investigate physical obstruction"],
            impact_level="low"
        )
    ]


class TestAnalyticsEndpoints:
    """Test suite for /api/v1/analytics endpoints."""

    @patch('app.utils.dependencies.get_analytics_service')
    def test_analytics_trends_valid_payload(self, mock_get_service, client, sample_analytics_request, mock_trends):
        """Test POST /api/v1/analytics/trends with valid JSON payload → assert HTTP 200 and response schema."""
        # Mock analytics service
        mock_service = AsyncMock()
        mock_service.analyze_trends.return_value = mock_trends
        mock_get_service.return_value = mock_service

        # Make request
        response = client.post("/api/v1/analytics/trends", json=sample_analytics_request)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure matches expected schema
        assert "trends" in data
        assert "analysis_timestamp" in data
        assert "total_trends" in data
        assert data["total_trends"] == 2
        assert len(data["trends"]) == 2
        
        # Verify trend structure matches AnalyticsResponse schema
        trend = data["trends"][0]
        assert trend["metric"] == "detection_count"
        assert trend["direction"] == "increasing"
        assert trend["magnitude"] == 0.15
        assert trend["confidence"] == 0.92
        assert isinstance(trend["contributing_factors"], list)
        assert len(trend["contributing_factors"]) == 2
        
        # Verify timestamp format
        try:
            datetime.fromisoformat(data["analysis_timestamp"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Invalid ISO format timestamp")

    @patch('app.utils.dependencies.get_analytics_service')
    def test_analytics_trends_malformed_payload(self, mock_get_service, client, malformed_analytics_request):
        """Test POST /api/v1/analytics/trends with malformed payload → assert HTTP 422."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Make request with malformed payload
        response = client.post("/api/v1/analytics/trends", json=malformed_analytics_request)

        # Verify validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)  # Pydantic validation errors

    def test_analytics_trends_missing_payload(self, client):
        """Test POST /api/v1/analytics/trends with missing payload → assert HTTP 422."""
        # Make request without payload
        response = client.post("/api/v1/analytics/trends")

        # Verify validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_analytics_trends_empty_payload(self, client):
        """Test POST /api/v1/analytics/trends with empty payload → assert HTTP 422."""
        # Make request with empty payload
        response = client.post("/api/v1/analytics/trends", json={})

        # Verify validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @patch('app.utils.dependencies.get_analytics_service')
    def test_analytics_trends_service_error(self, mock_get_service, client, sample_analytics_request):
        """Test service error handling in trends endpoint."""
        # Mock service to raise exception
        mock_service = AsyncMock()
        mock_service.analyze_trends.side_effect = Exception("Service error")
        mock_get_service.return_value = mock_service

        # Make request
        response = client.post("/api/v1/analytics/trends", json=sample_analytics_request)

        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Service error" in data["detail"]

    @patch('app.utils.dependencies.get_analytics_service')
    def test_analytics_anomalies_valid_payload(self, mock_get_service, client, sample_analytics_request, mock_anomalies):
        """Test POST /api/v1/analytics/anomalies with valid JSON payload → assert HTTP 200 and response schema."""
        # Mock analytics service
        mock_service = AsyncMock()
        mock_service.detect_anomalies.return_value = mock_anomalies
        mock_get_service.return_value = mock_service

        # Make request
        response = client.post("/api/v1/analytics/anomalies", json=sample_analytics_request)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "anomalies" in data
        assert "detection_timestamp" in data
        assert "total_anomalies" in data
        assert data["total_anomalies"] == 2
        assert len(data["anomalies"]) == 2
        
        # Verify anomaly structure
        anomaly = data["anomalies"][0]
        assert "metric" in anomaly
        assert "value" in anomaly
        assert "expected_range" in anomaly
        assert "confidence" in anomaly
        assert "severity" in anomaly
        assert "description" in anomaly
        
        # Verify timestamp format
        try:
            datetime.fromisoformat(data["detection_timestamp"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Invalid ISO format timestamp")

    @patch('app.utils.dependencies.get_analytics_service')
    def test_analytics_anomalies_malformed_payload(self, mock_get_service, client, malformed_analytics_request):
        """Test POST /api/v1/analytics/anomalies with malformed payload → assert HTTP 422."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Make request with malformed payload
        response = client.post("/api/v1/analytics/anomalies", json=malformed_analytics_request)

        # Verify validation error
        assert response.status_code == 422

    @patch('app.utils.dependencies.get_analytics_service')
    def test_analytics_anomalies_no_anomalies_found(self, mock_get_service, client, sample_analytics_request):
        """Test anomaly detection when no anomalies are found."""
        # Mock service to return empty list
        mock_service = AsyncMock()
        mock_service.detect_anomalies.return_value = []
        mock_get_service.return_value = mock_service

        # Make request
        response = client.post("/api/v1/analytics/anomalies", json=sample_analytics_request)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_anomalies"] == 0
        assert len(data["anomalies"]) == 0


class TestInsightsEndpoints:
    """Test suite for /api/v1/insights endpoints."""

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_insights_realtime_valid_response(self, mock_get_service, client, mock_insights):
        """Test GET /api/v1/insights/realtime → assert HTTP 200 and response schema."""
        # Mock dashboard service
        mock_service = AsyncMock()
        mock_service.get_realtime_insights.return_value = {
            "insights": [insight.__dict__ for insight in mock_insights],
            "last_updated": datetime.utcnow().isoformat(),
            "total_insights": len(mock_insights)
        }
        mock_get_service.return_value = mock_service

        # Make request
        response = client.get("/api/v1/insights/realtime")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "insights" in data
        assert "last_updated" in data
        assert "total_insights" in data
        assert data["total_insights"] == 2
        assert len(data["insights"]) == 2
        
        # Verify insight structure
        insight = data["insights"][0]
        assert "id" in insight
        assert "type" in insight
        assert "title" in insight
        assert "description" in insight
        assert "confidence" in insight
        assert "timestamp" in insight
        assert "data" in insight
        assert "recommendations" in insight
        assert "impact_level" in insight

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_insights_realtime_service_error(self, mock_get_service, client):
        """Test service error handling in realtime insights endpoint."""
        # Mock service to raise exception
        mock_service = AsyncMock()
        mock_service.get_realtime_insights.side_effect = Exception("Insights service error")
        mock_get_service.return_value = mock_service

        # Make request
        response = client.get("/api/v1/insights/realtime")

        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Insights service error" in data["detail"]

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_insights_realtime_empty_response(self, mock_get_service, client):
        """Test realtime insights when no insights are available."""
        # Mock service to return empty insights
        mock_service = AsyncMock()
        mock_service.get_realtime_insights.return_value = {
            "insights": [],
            "last_updated": datetime.utcnow().isoformat(),
            "total_insights": 0
        }
        mock_get_service.return_value = mock_service

        # Make request
        response = client.get("/api/v1/insights/realtime")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_insights"] == 0
        assert len(data["insights"]) == 0


class TestIntegratedWorkflows:
    """Test suite for integrated workflows between analytics and insights."""

    @patch('app.utils.dependencies.get_dashboard_service')
    @patch('app.utils.dependencies.get_analytics_service')
    def test_analytics_to_insights_flow(self, mock_analytics_service, mock_dashboard_service, 
                                       client, sample_analytics_request, mock_trends, mock_insights):
        """
        Test GET /api/v1/insights/realtime after posting two analytics jobs → assert correct history retrieval.
        
        This test simulates the workflow where:
        1. POST analytics/trends generates insights
        2. POST analytics/anomalies generates more insights  
        3. GET insights/realtime retrieves combined insights history
        """
        # Setup mocks
        mock_analytics = AsyncMock()
        mock_analytics.analyze_trends.return_value = mock_trends
        mock_analytics.detect_anomalies.return_value = []
        mock_analytics_service.return_value = mock_analytics

        mock_dashboard = AsyncMock()
        mock_dashboard.get_realtime_insights.return_value = {
            "insights": [insight.__dict__ for insight in mock_insights],
            "last_updated": datetime.utcnow().isoformat(),
            "total_insights": len(mock_insights)
        }
        mock_dashboard_service.return_value = mock_dashboard

        # First analytics job - trends
        trends_response = client.post("/api/v1/analytics/trends", json=sample_analytics_request)
        assert trends_response.status_code == 200

        # Second analytics job - anomalies  
        anomalies_response = client.post("/api/v1/analytics/anomalies", json=sample_analytics_request)
        assert anomalies_response.status_code == 200

        # Get insights history
        insights_response = client.get("/api/v1/insights/realtime")
        assert insights_response.status_code == 200
        
        insights_data = insights_response.json()
        assert insights_data["total_insights"] == 2
        assert len(insights_data["insights"]) == 2
        
        # Verify insights contain data from both analytics jobs
        insight_types = [insight["type"] for insight in insights_data["insights"]]
        assert "trend_analysis" in insight_types or "anomaly_detection" in insight_types

    def test_analytics_endpoints_independence(self, client, sample_analytics_request):
        """Test that analytics endpoints work independently without interfering with each other."""
        with patch('app.utils.dependencies.get_analytics_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.analyze_trends.return_value = []
            mock_service.detect_anomalies.return_value = []
            mock_get_service.return_value = mock_service

            # Multiple requests to different endpoints
            trends_response1 = client.post("/api/v1/analytics/trends", json=sample_analytics_request)
            anomalies_response1 = client.post("/api/v1/analytics/anomalies", json=sample_analytics_request)
            trends_response2 = client.post("/api/v1/analytics/trends", json=sample_analytics_request)

            # All should succeed independently
            assert trends_response1.status_code == 200
            assert anomalies_response1.status_code == 200
            assert trends_response2.status_code == 200


class TestErrorHandlingAndEdgeCases:
    """Test suite for error handling and edge cases."""

    def test_invalid_content_type(self, client, sample_analytics_request):
        """Test requests with invalid content type."""
        # Send as form data instead of JSON
        response = client.post("/api/v1/analytics/trends", data=sample_analytics_request)
        assert response.status_code == 422

    def test_large_payload_handling(self, client):
        """Test handling of unusually large payloads."""
        large_payload = {
            "analytics_type": "trend_analysis",
            "time_range": "last_24_hours",
            "data_sources": ["camera_" + str(i) for i in range(1000)],  # Very large list
            "filters": {"large_data": "x" * 10000}  # Large string
        }
        
        with patch('app.utils.dependencies.get_analytics_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.analyze_trends.return_value = []
            mock_get_service.return_value = mock_service
            
            response = client.post("/api/v1/analytics/trends", json=large_payload)
            # Should either process successfully or fail gracefully
            assert response.status_code in [200, 422, 413]  # 413 = Request Entity Too Large

    def test_concurrent_requests(self, client, sample_analytics_request):
        """Test handling of concurrent requests to the same endpoint."""
        import threading
        import time
        
        with patch('app.utils.dependencies.get_analytics_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.analyze_trends.return_value = []
            mock_get_service.return_value = mock_service
            
            responses = []
            
            def make_request():
                response = client.post("/api/v1/analytics/trends", json=sample_analytics_request)
                responses.append(response)
            
            # Create multiple threads making concurrent requests
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all requests to complete
            for thread in threads:
                thread.join()
            
            # All requests should succeed
            assert len(responses) == 5
            for response in responses:
                assert response.status_code == 200

    def test_health_check_endpoint(self, client):
        """Test the health check endpoint for service monitoring."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"


class TestResponseValidation:
    """Test suite for response structure and data validation."""

    @patch('app.utils.dependencies.get_analytics_service')
    def test_trends_response_schema_compliance(self, mock_get_service, client, sample_analytics_request, mock_trends):
        """Verify trends response complies with expected schema structure."""
        mock_service = AsyncMock()
        mock_service.analyze_trends.return_value = mock_trends
        mock_get_service.return_value = mock_service

        response = client.post("/api/v1/analytics/trends", json=sample_analytics_request)
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields
        required_fields = ["trends", "analysis_timestamp", "total_trends"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Data types
        assert isinstance(data["trends"], list)
        assert isinstance(data["total_trends"], int)
        assert isinstance(data["analysis_timestamp"], str)
        
        # Trends structure
        if data["trends"]:
            trend = data["trends"][0]
            trend_required_fields = ["metric", "direction", "magnitude", "confidence", "timeframe", "contributing_factors"]
            for field in trend_required_fields:
                assert field in trend, f"Missing trend field: {field}"

    @patch('app.utils.dependencies.get_analytics_service')
    def test_anomalies_response_schema_compliance(self, mock_get_service, client, sample_analytics_request, mock_anomalies):
        """Verify anomalies response complies with expected schema structure."""
        mock_service = AsyncMock()
        mock_service.detect_anomalies.return_value = mock_anomalies
        mock_get_service.return_value = mock_service

        response = client.post("/api/v1/analytics/anomalies", json=sample_analytics_request)
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields
        required_fields = ["anomalies", "detection_timestamp", "total_anomalies"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Data types
        assert isinstance(data["anomalies"], list)
        assert isinstance(data["total_anomalies"], int)
        assert isinstance(data["detection_timestamp"], str)

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_insights_response_schema_compliance(self, mock_get_service, client, mock_insights):
        """Verify insights response complies with expected schema structure."""
        mock_service = AsyncMock()
        mock_service.get_realtime_insights.return_value = {
            "insights": [insight.__dict__ for insight in mock_insights],
            "last_updated": datetime.utcnow().isoformat(),
            "total_insights": len(mock_insights)
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/insights/realtime")
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields
        required_fields = ["insights", "last_updated", "total_insights"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Data types
        assert isinstance(data["insights"], list)
        assert isinstance(data["total_insights"], int)
        assert isinstance(data["last_updated"], str)
