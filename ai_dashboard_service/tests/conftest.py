"""
Test fixtures and configuration for AI Dashboard Service tests.

This module provides comprehensive test fixtures for unit testing the AI Dashboard
Service components. It includes mocked external dependencies, sample data generators,
and configuration helpers to ensure isolated and reliable test execution.

Key Features:
- Fake Redis instance using fakeredis for caching tests
- Mocked OpenAI client for LLM service testing
- Mocked Weaviate client for vector database testing  
- Sample data generators for realistic test scenarios
- Configuration patches for test isolation
- Async test support with pytest-asyncio

Fixtures:
    fake_redis: Fake Redis instance for caching operations
    mock_openai_client: Mocked OpenAI API client
    mock_weaviate_client: Mocked Weaviate vector database client
    sample_analytics_data: Sample surveillance analytics data
    test_database_session: Mocked async database session
"""

import json
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock, patch

# Test framework imports
try:
    import fakeredis
    FAKEREDIS_AVAILABLE = True
except ImportError:
    FAKEREDIS_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Application imports
from app.models.schemas import AnalyticsRequest, TrendAnalysis, AnomalyDetection
from app.models.enums import AnalyticsType, TimeRange, WidgetType, PredictionType
from app.services.analytics import AnalyticsService
from app.services.llm_client import LLMService
from app.services.weaviate_client import WeaviateService


@pytest.fixture
def fake_redis():
    """
    Provide a fake Redis instance for testing caching operations.
    
    Creates a fakeredis instance that mimics Redis behavior without
    requiring an actual Redis server. Perfect for unit testing
    caching logic and Redis-dependent operations.
    
    :return: FakeRedis instance with Redis-compatible API
    :raises pytest.skip: If fakeredis is not available
    
    Example:
        >>> def test_caching(fake_redis):
        ...     fake_redis.set("key", "value")
        ...     assert fake_redis.get("key") == b"value"
    """
    if not FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not available")
    
    return fakeredis.FakeRedis(decode_responses=False)


@pytest.fixture
def mock_database_session():
    """
    Provide a mocked async database session for testing database operations.
    
    Creates an AsyncMock that simulates SQLAlchemy AsyncSession behavior
    for testing database-dependent operations without requiring an actual
    database connection.
    
    :return: AsyncMock configured as database session
    
    Example:
        >>> async def test_db_operation(mock_database_session):
        ...     mock_database_session.execute.return_value = Mock()
        ...     # Test database operations
    """
    db_session = AsyncMock()
    db_session.execute = AsyncMock()
    db_session.commit = AsyncMock()
    db_session.rollback = AsyncMock()
    db_session.close = AsyncMock()
    return db_session


@pytest.fixture
def mock_openai_client():
    """
    Provide a mocked OpenAI client for testing LLM operations.
    
    Creates a comprehensive mock of the OpenAI AsyncClient with
    realistic response structures for testing AI-powered features
    without making actual API calls.
    
    :return: Mock OpenAI client with chat completions support
    
    Example:
        >>> def test_llm_generation(mock_openai_client):
        ...     mock_openai_client.chat.completions.create.return_value = mock_response
        ...     # Test LLM operations
    """
    client = AsyncMock()
    
    # Mock chat completions response structure
    mock_response = AsyncMock()
    mock_choice = Mock()
    mock_message = Mock()
    mock_message.content = "This is a test AI response with insights and recommendations."
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    # Mock usage information
    mock_usage = Mock()
    mock_usage.total_tokens = 150
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    mock_response.usage = mock_usage
    
    # Configure the mock to return our response
    client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    return client


@pytest.fixture
def mock_weaviate_client():
    """
    Provide a mocked Weaviate client for testing vector database operations.
    
    Creates a comprehensive mock of the Weaviate client with collection
    support, search capabilities, and realistic response structures for
    testing semantic search and vector operations.
    
    :return: Mock Weaviate client with collections and search support
    
    Example:
        >>> def test_semantic_search(mock_weaviate_client):
        ...     mock_weaviate_client.collections.get.return_value = mock_collection
        ...     # Test vector database operations
    """
    client = Mock()
    
    # Mock collection and search response
    mock_collection = Mock()
    mock_query = Mock()
    mock_near_text = Mock()
    
    # Mock search result objects
    mock_objects = []
    for i in range(3):
        obj = Mock()
        obj.uuid = f"event-{i:03d}"
        obj.properties = {
            "event_id": f"event-{i:03d}",
            "event_type": "motion_detected" if i % 2 == 0 else "person_detected",
            "camera_id": f"cam-{i:03d}",
            "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
            "confidence": 0.9 - (i * 0.1),
            "description": f"Test surveillance event {i}"
        }
        obj.metadata = Mock()
        obj.metadata.certainty = 0.9 - (i * 0.05)
        obj.metadata.distance = 0.1 + (i * 0.05)
        mock_objects.append(obj)
    
    # Configure mock chain
    mock_near_text.objects = mock_objects
    mock_query.near_text = Mock(return_value=mock_near_text)
    mock_query.near_object = Mock(return_value=mock_near_text)
    mock_collection.query = mock_query
    
    # Mock data insertion
    mock_collection.data.insert = Mock(return_value="new-event-uuid")
    
    # Configure client to return collection
    client.collections.get = Mock(return_value=mock_collection)
    
    return client


@pytest.fixture
def sample_analytics_request():
    """
    Provide sample analytics request data for testing.
    
    Creates realistic AnalyticsRequest instances for testing various
    analytics operations and request validation scenarios.
    
    :return: Sample AnalyticsRequest instance
    """
    return AnalyticsRequest(
        analytics_type=AnalyticsType.TREND_ANALYSIS,
        time_range=TimeRange.LAST_24_HOURS,
        filters={"camera_id": "cam-001"},
        parameters={"confidence_threshold": 0.8}
    )


@pytest.fixture
def sample_time_series_data():
    """
    Provide sample time series data for analytics testing.
    
    Creates realistic surveillance metrics data for testing
    trend analysis, anomaly detection, and statistical operations.
    
    :return: Dictionary of metric names to time series values
    """
    return {
        "detection_count": [10, 12, 8, 15, 9, 11, 13, 7, 14, 10, 16, 12, 8, 9, 11],
        "alert_count": [2, 3, 1, 4, 2, 3, 5, 1, 3, 2, 4, 3, 1, 2, 3],
        "camera_uptime": [0.98, 0.97, 0.99, 0.96, 0.98, 0.97, 0.95, 0.99, 0.98, 0.97, 0.96, 0.98, 0.99, 0.97, 0.98],
        "processing_latency": [85, 92, 78, 105, 88, 95, 110, 75, 98, 89, 115, 93, 82, 87, 96]
    }


@pytest.fixture
def sample_insights_data():
    """
    Provide sample insights data for LLM testing.
    
    Creates realistic surveillance insights data structure for testing
    AI-powered analysis, summarization, and recommendation generation.
    
    :return: Dictionary containing insights, trends, and metrics
    """
    return {
        "trends": [
            {
                "metric": "detection_count",
                "direction": "increasing",
                "magnitude": 0.15,
                "confidence": 0.85,
                "timeframe": "last_24_hours"
            }
        ],
        "anomalies": [
            {
                "id": "anomaly_001",
                "metric": "processing_latency",
                "severity": "medium",
                "description": "Processing latency spike detected",
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "performance_metrics": {
            "cpu_usage": 75.2,
            "memory_usage": 68.5,
            "active_cameras": 10,
            "detection_rate": 0.92
        },
        "recommendations": [
            "Monitor processing latency trends",
            "Consider scaling resources during peak hours"
        ]
    }


@pytest.fixture
def sample_weaviate_events():
    """
    Provide sample surveillance events for Weaviate testing.
    
    Creates realistic surveillance event data for testing vector
    database operations, semantic search, and pattern analysis.
    
    :return: List of surveillance event dictionaries
    """
    events = []
    event_types = ["motion_detected", "person_detected", "vehicle_detected", "alert_triggered"]
    
    for i in range(5):
        event = {
            "event_id": f"event-{i:03d}",
            "event_type": event_types[i % len(event_types)],
            "camera_id": f"cam-{i:03d}",
            "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
            "confidence": 0.9 - (i * 0.05),
            "location": f"Zone-{i % 3 + 1}",
            "description": f"Surveillance event {i} detected by camera {i:03d}",
            "metadata": {
                "duration": 30 + (i * 5),
                "object_count": i + 1,
                "weather": "clear" if i % 2 == 0 else "cloudy"
            }
        }
        events.append(event)
    
    return events


@pytest.fixture
def mock_settings():
    """
    Provide mocked application settings for testing.
    
    Creates a mock settings object with test-appropriate values
    for configuration-dependent testing scenarios.
    
    :return: Mock settings object with test values
    """
    settings = Mock()
    settings.OPENAI_API_KEY = "test-openai-key"
    settings.WEAVIATE_URL = "http://test-weaviate:8080"
    settings.REDIS_URL = "redis://test-redis:6379/0"
    settings.ANOMALY_THRESHOLD = 2.0
    settings.PREDICTION_CACHE_TTL = 3600
    settings.DATABASE_URL = "postgresql://test:test@localhost/test_db"
    return settings


@pytest.fixture
def analytics_service(mock_database_session, fake_redis):
    """
    Provide an AnalyticsService instance with mocked dependencies.
    
    Creates a fully configured AnalyticsService for testing with
    mocked database and Redis connections to ensure test isolation.
    
    :param mock_database_session: Mocked database session
    :param fake_redis: Fake Redis instance
    :return: AnalyticsService instance ready for testing
    """
    return AnalyticsService(db=mock_database_session, redis_client=fake_redis)


@pytest.fixture
def llm_service(mock_openai_client):
    """
    Provide an LLMService instance with mocked OpenAI client.
    
    Creates a fully configured LLMService for testing with a
    mocked OpenAI client to avoid actual API calls during testing.
    
    :param mock_openai_client: Mocked OpenAI client
    :return: LLMService instance ready for testing
    """
    return LLMService(openai_client=mock_openai_client)


@pytest.fixture
def weaviate_service(mock_weaviate_client):
    """
    Provide a WeaviateService instance with mocked Weaviate client.
    
    Creates a fully configured WeaviateService for testing with a
    mocked Weaviate client to avoid actual vector database operations.
    
    :param mock_weaviate_client: Mocked Weaviate client
    :return: WeaviateService instance ready for testing
    """
    return WeaviateService(weaviate_client=mock_weaviate_client)


# Test data generators
def create_test_trend_analysis(**overrides) -> TrendAnalysis:
    """
    Create a test TrendAnalysis instance with optional overrides.
    
    :param overrides: Fields to override in the default trend analysis
    :return: TrendAnalysis instance for testing
    """
    defaults = {
        "metric": "detection_count",
        "direction": "increasing",
        "magnitude": 0.25,
        "confidence": 0.85,
        "timeframe": "last_24_hours",
        "contributing_factors": ["Higher activity levels", "Improved detection sensitivity"]
    }
    defaults.update(overrides)
    return TrendAnalysis(**defaults)


def create_test_anomaly_detection(**overrides) -> AnomalyDetection:
    """
    Create a test AnomalyDetection instance with optional overrides.
    
    :param overrides: Fields to override in the default anomaly detection
    :return: AnomalyDetection instance for testing
    """
    defaults = {
        "id": "test-anomaly-001",
        "timestamp": datetime.utcnow(),
        "metric": "processing_latency",
        "expected_value": 100.0,
        "actual_value": 250.0,
        "deviation": 2.5,
        "severity": "high",
        "description": "Test anomaly detected in processing latency"
    }
    defaults.update(overrides)
    return AnomalyDetection(**defaults)


# Async test utilities
@pytest.fixture(scope="session")
def event_loop():
    """
    Provide an event loop for async testing.
    
    Creates a new event loop for the test session to ensure
    proper async test execution and cleanup.
    
    :return: asyncio event loop
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Configuration patches
@pytest.fixture
def patch_settings(mock_settings):
    """
    Patch application settings for testing.
    
    Temporarily replaces the global settings with mock values
    for the duration of the test to ensure test isolation.
    
    :param mock_settings: Mock settings object
    :return: Patched settings context
    """
    with patch('config.config.settings', mock_settings):
        yield mock_settings


# Error simulation fixtures
@pytest.fixture
def simulate_redis_error(fake_redis):
    """
    Configure Redis to simulate connection errors.
    
    Modifies the fake Redis instance to raise connection errors
    for testing error handling and fallback mechanisms.
    
    :param fake_redis: Fake Redis instance
    :return: Modified fake Redis that raises errors
    """
    fake_redis.ping = Mock(side_effect=ConnectionError("Redis connection failed"))
    return fake_redis


@pytest.fixture
def simulate_openai_error(mock_openai_client):
    """
    Configure OpenAI client to simulate API errors.
    
    Modifies the mock OpenAI client to raise API errors for
    testing error handling and retry logic.
    
    :param mock_openai_client: Mock OpenAI client
    :return: Modified mock client that raises errors
    """
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=Exception("OpenAI API error")
    )
    return mock_openai_client


@pytest.fixture
def simulate_weaviate_error(mock_weaviate_client):
    """
    Configure Weaviate client to simulate database errors.
    
    Modifies the mock Weaviate client to raise database errors
    for testing error handling and fallback mechanisms.
    
    :param mock_weaviate_client: Mock Weaviate client
    :return: Modified mock client that raises errors
    """
    mock_weaviate_client.collections.get = Mock(
        side_effect=Exception("Weaviate connection failed")
    )
    return mock_weaviate_client
