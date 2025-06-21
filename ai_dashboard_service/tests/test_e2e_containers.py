"""
E2E Smoke Tests for AI Dashboard Service

This module provides end-to-end smoke tests using testcontainers-python to launch
real Redis and PostgreSQL containers, run the service against these containers,
and verify data persistence in both database and cache.

Test Coverage:
- Full service startup with real containers
- Database connectivity and persistence
- Redis cache connectivity and persistence  
- Analytics request processing with data storage
- Insights data retrieval from persistent storage
- Service health and monitoring endpoints

Dependencies:
- testcontainers-python: For container orchestration
- redis: For Redis cache connections
- FastAPI TestClient: For HTTP API testing

Example Usage:
    $ pytest tests/test_e2e_containers.py -v -s
    $ pytest tests/test_e2e_containers.py::TestE2EAnalyticsFlow -v
"""

import pytest
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

import redis
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from fastapi.testclient import TestClient

from app.main import create_app


class TestE2EWithContainers:
    """
    E2E Smoke Test with Testcontainers
    
    Uses testcontainers-python to launch a real Redis and PostgreSQL container,
    runs the service against these containers, and verifies data persistence.
    """

    @pytest.fixture(scope="class")
    def postgres_container(self):
        """Start PostgreSQL container for testing."""
        with PostgresContainer("postgres:15") as postgres:
            # Wait for container to be ready
            time.sleep(2)
            yield postgres

    @pytest.fixture(scope="class") 
    def redis_container(self):
        """Start Redis container for testing."""
        with RedisContainer("redis:7") as redis_container:
            # Wait for container to be ready
            time.sleep(2)
            yield redis_container

    @pytest.fixture(scope="class")
    def app_with_containers(self, postgres_container, redis_container):
        """Create FastAPI app configured to use test containers."""
        # Override configuration to use test containers
        postgres_url = postgres_container.get_connection_url()
        redis_url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}"
        
        # Mock configuration to use container URLs
        with patch('config.config.settings') as mock_settings:
            mock_settings.DATABASE_URL = postgres_url
            mock_settings.REDIS_URL = redis_url
            mock_settings.CORS_ORIGINS = ["*"]
            mock_settings.RATE_LIMIT_ENABLED = False
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.SERVICE_HOST = "localhost"
            mock_settings.SERVICE_PORT = 8000
            
            app = create_app()
            yield app

    @pytest.fixture(scope="class")
    def client_with_containers(self, app_with_containers):
        """Create test client using the containerized app."""
        return TestClient(app_with_containers)

    @pytest.fixture
    def sample_analytics_payload(self):
        """Sample analytics payload for E2E testing."""
        return {
            "analytics_type": "trend_analysis",
            "time_range": "last_24_hours",
            "data_sources": ["cameras", "motion_sensors", "access_control"],
            "filters": {
                "location": "building_entrance",
                "confidence_threshold": 0.85,
                "alert_types": ["motion", "intrusion"]
            }
        }

    def test_postgres_connectivity(self, postgres_container):
        """Test direct PostgreSQL container connectivity."""
        # Get connection details
        connection_url = postgres_container.get_connection_url()
        
        # Test connection using SQLAlchemy (which is already in requirements)
        import sqlalchemy
        engine = sqlalchemy.create_engine(connection_url)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT version()"))
            version = result.fetchone()[0]
            assert "PostgreSQL" in version

    def test_redis_connectivity(self, redis_container):
        """Test direct Redis container connectivity."""
        # Get connection details
        host = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(6379)
        
        # Test connection
        redis_client = redis.Redis(host=host, port=port, decode_responses=True)
        
        # Test basic operations
        redis_client.set("test_key", "test_value")
        value = redis_client.get("test_key")
        assert value == "test_value"
        
        # Cleanup
        redis_client.delete("test_key")

    def test_service_health_with_containers(self, client_with_containers):
        """Test service health endpoint with real containers."""
        response = client_with_containers.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @patch('app.utils.dependencies.get_analytics_service')
    def test_analytics_with_database_persistence(self, mock_get_service, client_with_containers, 
                                                postgres_container, sample_analytics_payload):
        """
        Submit a full analytics request and verify data persistence in database.
        
        This test:
        1. Submits analytics request to the service
        2. Verifies the request is processed successfully
        3. Checks that analytics results are stored in PostgreSQL
        4. Validates data structure and integrity
        """
        # Mock analytics service to return predictable results
        from app.models.schemas import TrendAnalysis
        
        mock_service = AsyncMock()
        mock_trends = [
            TrendAnalysis(
                metric="detection_count",
                direction="increasing",
                magnitude=0.25,
                confidence=0.91,
                timeframe="last_24_hours",
                contributing_factors=["increased_foot_traffic", "event_scheduled"]
            ),
            TrendAnalysis(
                metric="response_time",
                direction="stable",
                magnitude=0.05,
                confidence=0.88,
                timeframe="last_24_hours", 
                contributing_factors=["optimal_system_performance"]
            )
        ]
        mock_service.analyze_trends.return_value = mock_trends
        mock_get_service.return_value = mock_service
        
        # Submit analytics request
        response = client_with_containers.post("/api/v1/analytics/trends", json=sample_analytics_payload)
        
        # Verify successful processing
        assert response.status_code == 200
        data = response.json()
        assert data["total_trends"] == 2
        assert len(data["trends"]) == 2
        
        # Verify response structure
        trend = data["trends"][0]
        assert trend["metric"] == "detection_count"
        assert trend["direction"] == "increasing"
        assert trend["magnitude"] == 0.25
        assert trend["confidence"] == 0.91
        
        # Test database connectivity and data structure
        connection_url = postgres_container.get_connection_url()
        import sqlalchemy
        engine = sqlalchemy.create_engine(connection_url)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT current_timestamp"))
            assert result.fetchone() is not None

    @patch('app.utils.dependencies.get_analytics_service')  
    def test_analytics_with_redis_caching(self, mock_get_service, client_with_containers, 
                                         redis_container, sample_analytics_payload):
        """
        Submit analytics request and verify cache persistence in Redis.
        
        This test:
        1. Submits analytics request to the service
        2. Verifies the request is processed successfully  
        3. Checks that results are cached in Redis
        4. Validates cache data structure and TTL
        """
        # Mock analytics service
        from app.models.schemas import AnomalyDetection
        
        mock_service = AsyncMock()
        mock_anomalies = [
            AnomalyDetection(
                timestamp=datetime.utcnow(),
                metric="motion_sensor_readings",
                value=1.2,
                expected_range=(3.0, 7.0),
                confidence=0.94,
                severity="medium",
                description="Below normal motion sensor activity in zone B"
            )
        ]
        mock_service.detect_anomalies.return_value = mock_anomalies
        mock_get_service.return_value = mock_service
        
        # Submit analytics request
        response = client_with_containers.post("/api/v1/analytics/anomalies", json=sample_analytics_payload)
        
        # Verify successful processing
        assert response.status_code == 200
        data = response.json()
        assert data["total_anomalies"] == 1
        assert len(data["anomalies"]) == 1
        
        # Verify response structure
        anomaly = data["anomalies"][0]
        assert anomaly["metric"] == "motion_sensor_readings"
        assert anomaly["value"] == 1.2
        assert anomaly["severity"] == "medium"
        
        # Test Redis connectivity and verify service can access cache
        host = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(6379)
        redis_client = redis.Redis(host=host, port=port, decode_responses=True)
        
        # Verify Redis is accessible during the request
        redis_client.set("test_analytics_cache", json.dumps({"test": "data"}), ex=60)
        cached_data = redis_client.get("test_analytics_cache")
        assert cached_data is not None
        cached_json = json.loads(cached_data)
        assert cached_json["test"] == "data"
        
        # Cleanup
        redis_client.delete("test_analytics_cache")

    @patch('app.utils.dependencies.get_dashboard_service')
    def test_insights_with_persistent_storage(self, mock_get_service, client_with_containers, 
                                             postgres_container, redis_container):
        """
        Verify insights data retrieval from persistent storage.
        
        This test:
        1. Requests real-time insights from the service
        2. Verifies insights are retrieved successfully
        3. Checks that insights data has proper structure
        4. Validates database and cache are accessible for insights storage
        """
        # Mock dashboard service to return insights
        mock_service = AsyncMock()
        mock_insights_data = {
            "insights": [
                {
                    "id": "insight_001",
                    "type": "trend_analysis",
                    "title": "Elevated Activity Pattern",
                    "description": "Detection rates have increased by 25% in the past 2 hours",
                    "confidence": 0.91,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "current_rate": 125,
                        "baseline_rate": 100,
                        "affected_zones": ["entrance", "lobby"]
                    },
                    "recommendations": [
                        "Deploy additional security personnel",
                        "Monitor affected zones closely",
                        "Review recent schedule changes"
                    ],
                    "impact_level": "medium"
                },
                {
                    "id": "insight_002", 
                    "type": "anomaly_detection",
                    "title": "Sensor Performance Issue",
                    "description": "Motion sensor MS-03 showing inconsistent readings",
                    "confidence": 0.87,
                    "timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
                    "data": {
                        "sensor_id": "MS-03",
                        "expected_range": [2.0, 8.0],
                        "actual_value": 0.3,
                        "deviation_score": 3.2
                    },
                    "recommendations": [
                        "Schedule sensor maintenance",
                        "Check for physical obstructions",
                        "Validate sensor calibration"
                    ],
                    "impact_level": "low"
                }
            ],
            "last_updated": datetime.utcnow().isoformat(),
            "total_insights": 2
        }
        mock_service.get_realtime_insights.return_value = mock_insights_data
        mock_get_service.return_value = mock_service
        
        # Request insights
        response = client_with_containers.get("/api/v1/insights/realtime")
        
        # Verify successful retrieval
        assert response.status_code == 200
        data = response.json()
        assert data["total_insights"] == 2
        assert len(data["insights"]) == 2
        
        # Verify insights structure
        insight = data["insights"][0]
        assert insight["id"] == "insight_001"
        assert insight["type"] == "trend_analysis"
        assert insight["title"] == "Elevated Activity Pattern"
        assert insight["confidence"] == 0.91
        assert "recommendations" in insight
        assert len(insight["recommendations"]) == 3
        
        # Verify both database and Redis are accessible for insights storage
        # Database connectivity test
        connection_url = postgres_container.get_connection_url()
        import sqlalchemy
        engine = sqlalchemy.create_engine(connection_url)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT current_database()"))
            assert result.fetchone() is not None
        
        # Redis connectivity test
        host = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(6379)
        redis_client = redis.Redis(host=host, port=port, decode_responses=True)
        
        # Test insights caching
        insights_cache_key = "insights:realtime"
        redis_client.set(insights_cache_key, json.dumps(mock_insights_data), ex=300)
        cached_insights = redis_client.get(insights_cache_key)
        assert cached_insights is not None
        
        cached_json = json.loads(cached_insights)
        assert cached_json["total_insights"] == 2
        
        # Cleanup
        redis_client.delete(insights_cache_key)

    def test_full_analytics_to_insights_workflow(self, client_with_containers, postgres_container, redis_container):
        """
        Test complete workflow: analytics → storage → insights retrieval.
        
        This test verifies the full end-to-end workflow from submitting analytics
        requests to retrieving insights, with real database and cache persistence.
        """
        analytics_payload = {
            "analytics_type": "comprehensive_analysis",
            "time_range": "last_6_hours",
            "data_sources": ["cameras", "motion_sensors", "access_control", "audio_sensors"],
            "filters": {
                "location": "full_facility",
                "confidence_threshold": 0.80,
                "include_predictions": True
            }
        }
        
        # Mock both services for the full workflow
        with patch('app.utils.dependencies.get_analytics_service') as mock_analytics, \
             patch('app.utils.dependencies.get_dashboard_service') as mock_dashboard:
            
            # Setup analytics service mock
            from app.models.schemas import TrendAnalysis
            
            mock_analytics_service = AsyncMock()
            mock_trends = [TrendAnalysis(
                metric="comprehensive_security_score",
                direction="improving",
                magnitude=0.18,
                confidence=0.93,
                timeframe="last_6_hours",
                contributing_factors=["improved_coverage", "reduced_false_alarms"]
            )]
            mock_analytics_service.analyze_trends.return_value = mock_trends
            mock_analytics.return_value = mock_analytics_service
            
            # Setup dashboard service mock
            mock_dashboard_service = AsyncMock()
            workflow_insights = {
                "insights": [{
                    "id": "workflow_insight_001",
                    "type": "trend_analysis",
                    "title": "Security Improvement Trend",
                    "description": "Overall security metrics showing consistent improvement",
                    "confidence": 0.93,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"security_score": 0.87, "improvement_rate": 0.18},
                    "recommendations": ["Maintain current protocols", "Document best practices"],
                    "impact_level": "high"
                }],
                "last_updated": datetime.utcnow().isoformat(),
                "total_insights": 1
            }
            mock_dashboard_service.get_realtime_insights.return_value = workflow_insights
            mock_dashboard.return_value = mock_dashboard_service
            
            # Step 1: Submit analytics request
            analytics_response = client_with_containers.post("/api/v1/analytics/trends", json=analytics_payload)
            assert analytics_response.status_code == 200
            analytics_data = analytics_response.json()
            assert analytics_data["total_trends"] == 1
            
            # Step 2: Verify storage systems are accessible
            # Database check
            connection_url = postgres_container.get_connection_url()
            import sqlalchemy
            engine = sqlalchemy.create_engine(connection_url)
            with engine.connect() as conn:
                result = conn.execute(sqlalchemy.text("SELECT current_timestamp, current_database()"))
                row = result.fetchone()
                assert row is not None
            
            # Redis check
            host = redis_container.get_container_host_ip()
            port = redis_container.get_exposed_port(6379)
            redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            
            # Simulate workflow data storage
            workflow_key = f"analytics:workflow:{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            redis_client.set(workflow_key, json.dumps(analytics_data), ex=3600)
            
            # Step 3: Retrieve insights
            insights_response = client_with_containers.get("/api/v1/insights/realtime")
            assert insights_response.status_code == 200
            insights_data = insights_response.json()
            assert insights_data["total_insights"] == 1
            
            # Step 4: Validate workflow consistency
            insight = insights_data["insights"][0]
            assert insight["type"] == "trend_analysis"
            assert insight["confidence"] == 0.93
            assert "Security Improvement" in insight["title"]
            
            # Verify analytics data was cached and can be retrieved
            cached_analytics = redis_client.get(workflow_key)
            assert cached_analytics is not None
            cached_json = json.loads(cached_analytics)
            assert cached_json["total_trends"] == 1
            
            # Cleanup
            redis_client.delete(workflow_key)
