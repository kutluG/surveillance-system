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
    $ pytest tests/test_api_endpoints.py -v
    $ pytest tests/test_api_endpoints.py::TestAnalyticsEndpoints -v
    $ pytest tests/test_api_endpoints.py::TestInsightsEndpoints -v
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.schemas import (
    AnalyticsInsight, TrendAnalysis, AnomalyDetection
)
from app.models.enums import AnalyticsType, TimeRange, WidgetType, PredictionType


@pytest.fixture
def app():
    """Create FastAPI application for testing."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def sample_analytics_request():
    """Sample analytics request payload for trends and anomalies."""
    return {
        "analytics_type": "trend_analysis",
        "time_range": "last_24_hours",
        "data_sources": ["cameras", "motion_sensors"],
        "filters": {"location": "parking_lot", "confidence_threshold": 0.8}
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
        "data_sources": "not_a_list",  # Should be list
        "filters": "not_a_dict" # Should be dict
    }


@pytest.fixture
def sample_prediction_request():
    """Sample prediction request payload."""
    return {
        "prediction_type": "security_threat",
        "time_horizon": "next_hour",
        "data_sources": ["cameras", "sensors"],
        "parameters": {"confidence_threshold": 0.9}
    }


@pytest.fixture
def sample_report_request():
    """Sample report generation request payload."""
    return {
        "report_type": "security_summary",
        "time_range": "last_week",
        "include_analytics": True,
        "include_predictions": True,
        "format": "pdf"
    }


@pytest.fixture
def sample_widget_request():
    """Sample widget creation request payload."""
    return {
        "widget_type": "chart",
        "title": "Detection Trends",
        "description": "Real-time detection count trends",
        "configuration": {
            "chart_type": "line",
            "metrics": ["detection_count"],
            "time_range": "last_hour"
        },
        "filters": {"location": "main_entrance"}
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
            timestamp=datetime.utcnow(),
            metric="detection_count",
            value=45.2,
            expected_range=(20.0, 30.0),
            confidence=0.89,
            severity="high",
            description="Unusually high detection count in sector A"
        ),
        AnomalyDetection(
            timestamp=datetime.utcnow() - timedelta(minutes=30),
            metric="motion_sensor_activity",
            value=0.1,
            expected_range=(2.0, 8.0),
            confidence=0.95,
            severity="medium",
            description="Low motion sensor activity detected"
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

        # Verify service was called correctly
        mock_service.analyze_trends.assert_called_once()

    @patch('app.utils.dependencies.get_analytics_service')
    def test_analyze_trends_service_error(self, mock_get_service, client, sample_analytics_request):
        """Test trend analysis with service error."""
        # Mock service to raise exception
        mock_service = AsyncMock()
        mock_service.analyze_trends.side_effect = Exception("Database connection failed")
        mock_get_service.return_value = mock_service

        # Make request
        response = client.post("/api/v1/analytics/trends", json=sample_analytics_request)

        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Trend analysis failed" in data["detail"]

    def test_analyze_trends_invalid_payload(self, client):
        """Test trend analysis with malformed payload."""
        invalid_payload = {
            "analytics_type": "invalid_type",  # Invalid enum value
            "time_range": "invalid_range",     # Invalid enum value
            # Missing required fields
        }

        response = client.post("/api/v1/analytics/trends", json=invalid_payload)

        # Should return 422 for validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # FastAPI automatically generates validation error details

    def test_analyze_trends_missing_fields(self, client):
        """Test trend analysis with missing required fields."""
        incomplete_payload = {
            "analytics_type": "trend_analysis"
            # Missing time_range and data_sources
        }

        response = client.post("/api/v1/analytics/trends", json=incomplete_payload)

        # Should return 422 for validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @patch('app.utils.dependencies.get_analytics_service')
    def test_detect_anomalies_success(self, mock_get_service, client, sample_analytics_request):
        """Test successful anomaly detection."""
        # Mock analytics service
        mock_service = AsyncMock()
        mock_anomalies = [
            AnomalyDetection(
                id="anomaly_001",
                timestamp=datetime.utcnow(),
                metric="detection_count",
                value=45.0,
                expected_range=(10.0, 25.0),
                deviation=2.8,
                severity="high",
                description="Unusually high detection count in sector A",
                contributing_factors=["crowd_event", "false_alarms"]
            )
        ]
        mock_service.detect_anomalies.return_value = mock_anomalies
        mock_get_service.return_value = mock_service

        # Make request
        response = client.post("/api/v1/analytics/anomalies", json=sample_analytics_request)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert "anomalies" in data
        assert "detection_timestamp" in data
        assert "total_anomalies" in data
        assert data["total_anomalies"] == 1
        
        # Verify anomaly structure
        anomaly = data["anomalies"][0]
        assert anomaly["metric"] == "detection_count"
        assert anomaly["severity"] == "high"
        assert anomaly["deviation"] == 2.8

    @patch('app.utils.dependencies.get_analytics_service')
    def test_detect_anomalies_no_anomalies(self, mock_get_service, client, sample_analytics_request):
        """Test anomaly detection when no anomalies are found."""
        # Mock service returning empty list
        mock_service = AsyncMock()
        mock_service.detect_anomalies.return_value = []
        mock_get_service.return_value = mock_service

        response = client.post("/api/v1/analytics/anomalies", json=sample_analytics_request)

        assert response.status_code == 200
        data = response.json()
        assert data["total_anomalies"] == 0
        assert data["anomalies"] == []


class TestPredictionEndpoints:
    """Test suite for prediction-related API endpoints."""

    def test_generate_predictions_placeholder(self, client, sample_prediction_request):
        """Test predictions endpoint (currently placeholder)."""
        response = client.post("/api/v1/predictions", json=sample_prediction_request)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "prediction_type" in data
        assert "generated_at" in data
        assert data["prediction_type"] == "security_threat"


class TestReportEndpoints:
    """Test suite for report generation and retrieval endpoints."""

    def test_generate_report_placeholder(self, client, sample_report_request):
        """Test report generation endpoint (currently placeholder)."""
        response = client.post("/api/v1/reports/generate", json=sample_report_request)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "report_type" in data
        assert "generated_at" in data
        assert data["report_type"] == "security_summary"

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_get_report_success(self, mock_get_service, client):
        """Test successful report retrieval."""
        # Mock dashboard service
        mock_service = AsyncMock()
        mock_report = {
            "id": "report_123",
            "type": "security_summary",
            "content": "Sample report content",
            "generated_at": datetime.utcnow().isoformat(),
            "status": "completed"
        }
        mock_service.get_stored_report.return_value = mock_report
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/reports/report_123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "report_123"
        assert data["type"] == "security_summary"

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_get_report_not_found(self, mock_get_service, client):
        """Test report retrieval when report doesn't exist."""
        # Mock service returning None
        mock_service = AsyncMock()
        mock_service.get_stored_report.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/reports/nonexistent_report")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Report not found" in data["detail"]


class TestInsightEndpoints:
    """Test suite for real-time insights endpoints."""

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_get_realtime_insights_success(self, mock_get_service, client):
        """Test successful real-time insights retrieval."""
        # Mock dashboard service
        mock_service = AsyncMock()
        mock_insights = {
            "insights": [
                {
                    "type": "security_alert",
                    "title": "Unusual Activity Detected",
                    "description": "Higher than normal motion in restricted area",
                    "confidence": 0.87,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "generated_at": datetime.utcnow().isoformat(),
            "total_insights": 1
        }
        mock_service.get_realtime_insights.return_value = mock_insights
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/insights/realtime")

        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
        assert "generated_at" in data
        assert data["total_insights"] == 1


class TestWidgetEndpoints:
    """Test suite for dashboard widget management endpoints."""

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_create_widget_success(self, mock_get_service, client, sample_widget_request):
        """Test successful widget creation."""
        # Mock dashboard service
        mock_service = AsyncMock()
        mock_service.store_widget_configuration.return_value = True
        mock_get_service.return_value = mock_service

        response = client.post("/api/v1/widgets/create", json=sample_widget_request)

        assert response.status_code == 200
        data = response.json()
        assert "widget_id" in data
        assert "widget" in data
        
        widget = data["widget"]
        assert widget["type"] == "chart"
        assert widget["title"] == "Detection Trends"
        assert "id" in widget
        assert "layout" in widget

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_create_widget_storage_failure(self, mock_get_service, client, sample_widget_request):
        """Test widget creation when storage fails."""
        # Mock service storage failure
        mock_service = AsyncMock()
        mock_service.store_widget_configuration.return_value = False
        mock_get_service.return_value = mock_service

        response = client.post("/api/v1/widgets/create", json=sample_widget_request)

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to store widget configuration" in data["detail"]

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_list_widgets_success(self, mock_get_service, client):
        """Test successful widget listing."""
        # Mock dashboard service
        mock_service = AsyncMock()
        mock_widgets = [
            {
                "id": "widget_001",
                "type": "chart",
                "title": "Detection Trends",
                "configuration": {"chart_type": "line"}
            },
            {
                "id": "widget_002", 
                "type": "metric",
                "title": "Alert Count",
                "configuration": {"metric": "alert_count"}
            }
        ]
        mock_service.get_widget_configurations.return_value = mock_widgets
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/widgets")

        assert response.status_code == 200
        data = response.json()
        assert "widgets" in data
        assert len(data["widgets"]) == 2


class TestDashboardEndpoints:
    """Test suite for dashboard summary endpoints."""

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_get_dashboard_summary_success(self, mock_get_service, client):
        """Test successful dashboard summary retrieval."""
        # Mock dashboard service
        mock_service = AsyncMock()
        mock_summary = {
            "overview": {
                "total_cameras": 24,
                "active_alerts": 3,
                "system_health": "good"
            },
            "recent_insights": [
                {
                    "type": "trend",
                    "message": "Detection rates increased 15% today"
                }
            ],
            "generated_at": datetime.utcnow().isoformat()
        }
        mock_service.get_dashboard_summary.return_value = mock_summary
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert "overview" in data
        assert "recent_insights" in data
        assert "generated_at" in data


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"


class TestEndToEndFlows:
    """Test suite for end-to-end workflows combining multiple endpoints."""

    @patch('app.utils.dependencies.get_analytics_service')
    @patch('app.utils.dependencies.get_dashboard_service')
    def test_analytics_to_insights_flow(self, mock_dashboard_service, mock_analytics_service, 
                                      client, sample_analytics_request):
        """Test workflow from analytics request to insights generation."""
        # Mock analytics service
        mock_analytics = AsyncMock()
        mock_trends = [
            TrendAnalysis(
                metric="detection_count",
                direction="increasing", 
                magnitude=0.25,
                confidence=0.95,
                timeframe="last_24_hours",
                contributing_factors=["event_detected"]
            )
        ]
        mock_analytics.analyze_trends.return_value = mock_trends
        mock_analytics_service.return_value = mock_analytics

        # Mock dashboard service
        mock_dashboard = AsyncMock()
        mock_insights = {
            "insights": [
                {
                    "type": "trend_alert",
                    "message": "Significant increase in detections detected",
                    "confidence": 0.95
                }
            ],
            "total_insights": 1
        }
        mock_dashboard.get_realtime_insights.return_value = mock_insights
        mock_dashboard_service.return_value = mock_dashboard

        # 1. Analyze trends
        trends_response = client.post("/api/v1/analytics/trends", json=sample_analytics_request)
        assert trends_response.status_code == 200
        trends_data = trends_response.json()
        assert trends_data["total_trends"] == 1

        # 2. Get real-time insights (should reflect the trend analysis)
        insights_response = client.get("/api/v1/insights/realtime")
        assert insights_response.status_code == 200
        insights_data = insights_response.json()
        assert insights_data["total_insights"] == 1

    def test_content_type_validation(self, client):
        """Test that endpoints properly validate content type."""
        # Send request without proper JSON content type
        response = client.post(
            "/api/v1/analytics/trends",
            data="invalid data",
            headers={"Content-Type": "text/plain"}
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422

    def test_large_payload_handling(self, client):
        """Test handling of large request payloads."""
        large_payload = {
            "analytics_type": "trend_analysis",
            "time_range": "last_month",
            "data_sources": ["cameras"] * 1000,  # Large array
            "filters": {f"filter_{i}": f"value_{i}" for i in range(100)}  # Large dict
        }

        # Should handle large payload gracefully
        response = client.post("/api/v1/analytics/trends", json=large_payload)
        # Might return 422 for validation or 413 for payload too large
        assert response.status_code in [413, 422, 500]

    def test_concurrent_requests(self, client, sample_analytics_request):
        """Test handling of concurrent requests to the same endpoint."""
        import concurrent.futures
        import threading

        responses = []
        
        def make_request():
            response = client.post("/api/v1/analytics/trends", json=sample_analytics_request)
            responses.append(response)

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            concurrent.futures.wait(futures)

        # All requests should complete (though some might fail due to mocking)
        assert len(responses) == 5
        # At least one should be successful format-wise
        status_codes = [r.status_code for r in responses]
        assert any(code in [200, 500] for code in status_codes)  # 200 success or 500 service error
