"""
Test fixtures and configuration for enhanced_prompt_service tests.
"""
import pytest
import fakeredis
import json
import redis
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
from typing import Dict, Any, List

# Import modules to be tested
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conversation_manager import ConversationManager


@pytest.fixture
def fake_redis():
    """Fixture providing a fake Redis server for testing."""
    return fakeredis.FakeRedis()


@pytest.fixture
def conversation_manager(fake_redis):
    """Fixture providing a ConversationManager with fake Redis."""
    return ConversationManager(fake_redis)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_completion = Mock()
    mock_choice = Mock()
    mock_message = Mock()
    
    # Setup completion response structure
    mock_message.content = "This is a test response from the AI assistant."
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]
    mock_completion.usage = Mock()
    mock_completion.usage.total_tokens = 150
    
    mock_client.chat.completions.create.return_value = mock_completion
    return mock_client


@pytest.fixture
def mock_weaviate_client():
    """Mock Weaviate client for testing."""
    client = Mock()
    
    # Mock collection query response
    mock_response = Mock()
    mock_response.objects = []
    
    # Mock collection
    mock_collection = Mock()
    mock_collection.query.hybrid.return_value.with_limit.return_value.do.return_value = mock_response
    mock_collection.query.near_text.return_value.with_limit.return_value.do.return_value = mock_response
    mock_collection.query.get.return_value.with_limit.return_value.do.return_value = mock_response
    
    client.collections.get.return_value = mock_collection
    return client


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "openai_api_key": "test-api-key",
        "openai_model": "gpt-4",
        "weaviate_url": "http://test-weaviate:8080",
        "redis_url": "redis://test-redis:6379"
    }


@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing."""
    return {
        "id": "test-conversation-id",
        "user_id": "test-user-123",
        "created_at": "2025-06-18T10:00:00",
        "last_activity": "2025-06-18T10:30:00",
        "context": {"camera_focus": "main_entrance"},
        "message_count": 2,
        "status": "active"
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {
        "id": "test-message-id",
        "conversation_id": "test-conversation-id",
        "role": "user",
        "content": "Show me recent security events",
        "timestamp": "2025-06-18T10:30:00",
        "metadata": {"client": "web"}
    }


@pytest.fixture
def sample_search_results():
    """Sample Weaviate search results for testing."""
    return [
        {
            "event_id": "event-001",
            "timestamp": "2025-06-18T09:00:00Z",
            "camera_id": "cam-001",
            "event_type": "person_detected",
            "details": "Person detected at main entrance",
            "confidence": 0.95,
            "certainty": 0.92
        },
        {
            "event_id": "event-002", 
            "timestamp": "2025-06-18T09:15:00Z",
            "camera_id": "cam-002",
            "event_type": "motion_detected",
            "details": "Motion in parking area",
            "confidence": 0.87,
            "certainty": 0.85
        }
    ]


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing."""
    return [
        {"role": "user", "content": "What happened at the main entrance today?"},
        {"role": "assistant", "content": "I found several events at the main entrance today..."},
        {"role": "user", "content": "Show me more details about the person detection"}
    ]


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = "This is a test response from the AI assistant."
    response.usage = Mock()
    response.usage.total_tokens = 150
    return response


@pytest.fixture
def mock_openai_follow_up_response():
    """Mock OpenAI API response for follow-up questions."""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = json.dumps([
        "Can you show me more details about these events?",
        "What cameras are involved in these detections?",
        "Are there any patterns in the timing?",
        "How can I set up alerts for similar events?"
    ])
    response.usage = Mock()
    response.usage.total_tokens = 100
    return response


@pytest.fixture
def mock_weaviate_client():
    """Mock Weaviate client for testing."""
    client = Mock()
    collection = Mock()
    client.collections.get.return_value = collection
    
    # Mock search response
    search_response = Mock()
    search_response.objects = []
    collection.query.near_text.return_value = search_response
    
    return client


@pytest.fixture
def mock_weaviate_search_objects(sample_search_results):
    """Mock Weaviate search result objects."""
    objects = []
    for result_data in sample_search_results:
        obj = Mock()
        obj.properties = result_data.copy()
        obj.metadata = Mock()
        obj.metadata.certainty = result_data.get("certainty", 0.8)
        obj.metadata.distance = 0.2
        objects.append(obj)
    return objects


@pytest.fixture
def mock_config():
    """Mock service configuration."""
    return {
        "openai_api_key": "test-api-key",
        "openai_model": "gpt-4",
        "weaviate_url": "http://test-weaviate:8080"
    }


@pytest.fixture
def patch_get_service_config(mock_config):
    """Patch the get_service_config function."""
    with patch('shared.config.get_service_config', return_value=mock_config):
        yield mock_config


@pytest.fixture
def patch_openai_client():
    """Patch OpenAI client."""
    with patch('openai.OpenAI') as mock_openai:
        yield mock_openai


@pytest.fixture
def patch_weaviate_client():
    """Patch Weaviate client connection."""
    with patch('weaviate.connect_to_local') as mock_connect:
        yield mock_connect


@pytest.fixture
def patch_logger():
    """Patch logger to avoid import issues during testing."""
    with patch('shared.logging_config.get_logger') as mock_logger:
        mock_logger.return_value = Mock()
        yield mock_logger


# Test data generators

def create_test_conversation(**overrides) -> Dict[str, Any]:
    """Create test conversation data with optional overrides."""
    base_data = {
        "id": "test-conv-123",
        "user_id": "user-456",
        "created_at": datetime.utcnow().isoformat(),
        "last_activity": datetime.utcnow().isoformat(),
        "context": {},
        "message_count": 0,
        "status": "active"
    }
    base_data.update(overrides)
    return base_data


def create_test_message(**overrides) -> Dict[str, Any]:
    """Create test message data with optional overrides."""
    base_data = {
        "id": "test-msg-789",
        "conversation_id": "test-conv-123",
        "role": "user",
        "content": "Test message content",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {}
    }
    base_data.update(overrides)
    return base_data


def create_test_search_result(**overrides) -> Dict[str, Any]:
    """Create test search result with optional overrides."""
    base_data = {
        "event_id": "event-123",
        "timestamp": "2025-06-18T10:00:00Z",
        "camera_id": "cam-001",
        "event_type": "person_detected",
        "details": "Test event details",
        "confidence": 0.85,
        "certainty": 0.80
    }
    base_data.update(overrides)
    return base_data


# Additional test fixtures for comprehensive testing

@pytest.fixture
def sample_weaviate_search_results():
    """Sample Weaviate search results with realistic structure."""
    return [
        {
            "event_id": "evt_001",
            "timestamp": "2025-06-18T08:30:00Z",
            "camera_id": "main_entrance_cam",
            "event_type": "person_detected",
            "details": "Person with backpack entering building",
            "confidence": 0.94,
            "certainty": 0.92,
            "location": {"x": 100, "y": 200}
        },
        {
            "event_id": "evt_002",
            "timestamp": "2025-06-18T08:45:00Z", 
            "camera_id": "parking_lot_cam",
            "event_type": "vehicle_detected",
            "details": "Blue sedan entering parking area",
            "confidence": 0.87,
            "certainty": 0.85,
            "location": {"x": 300, "y": 150}
        }
    ]


@pytest.fixture
def mock_redis_connection_error():
    """Mock Redis connection that raises connection errors."""
    mock_redis = Mock(spec=redis.Redis)
    mock_redis.get.side_effect = redis.ConnectionError("Connection refused")
    mock_redis.set.side_effect = redis.ConnectionError("Connection refused")
    mock_redis.setex.side_effect = redis.ConnectionError("Connection refused")
    mock_redis.zadd.side_effect = redis.ConnectionError("Connection refused")
    return mock_redis


@pytest.fixture  
def mock_openai_rate_limit_error():
    """Mock OpenAI client that raises rate limit errors."""
    from openai import RateLimitError
    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = RateLimitError(
        message="Rate limit exceeded",
        response=Mock(),
        body=None
    )
    return mock_client


@pytest.fixture
def mock_openai_api_error():
    """Mock OpenAI client that raises API connection errors.""" 
    from openai import APIConnectionError
    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = APIConnectionError(
        message="Connection error"
    )
    return mock_client


@pytest.fixture
def mock_weaviate_empty_response():
    """Mock Weaviate client that returns empty results."""
    client = Mock()
    collection = Mock()
    client.collections.get.return_value = collection
    
    # Mock empty response
    search_response = Mock()
    search_response.objects = []
    
    # Chain the methods properly
    query_mock = Mock()
    query_mock.near_text.return_value = query_mock
    query_mock.hybrid.return_value = query_mock  
    query_mock.with_limit.return_value = query_mock
    query_mock.with_where.return_value = query_mock
    query_mock.do.return_value = search_response
    
    collection.query = query_mock
    return client


@pytest.fixture
def mock_weaviate_connection_error():
    """Mock Weaviate client that raises connection errors."""
    client = Mock()
    client.collections.get.side_effect = Exception("Weaviate connection failed")
    return client


@pytest.fixture
def sample_system_context():
    """Sample system context data for LLM testing."""
    return {
        "proactive_insights": [
            "Increased activity detected at main entrance",
            "Unusual pattern in parking lot traffic"
        ],
        "patterns": "Peak activity between 8-9 AM and 5-6 PM",
        "anomalies": "Motion detected in restricted area at 2 AM"
    }


@pytest.fixture
def invalid_json_response():
    """Mock OpenAI response with invalid JSON for follow-up questions."""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = "This is not valid JSON for follow-up questions"
    response.usage = Mock()
    response.usage.total_tokens = 75
    return response


@pytest.fixture
def empty_conversation_history():
    """Empty conversation history for testing."""
    return []


@pytest.fixture
def long_conversation_history():
    """Long conversation history for testing pagination/limits."""
    history = []
    for i in range(10):
        history.extend([
            {"role": "user", "content": f"User message {i+1}"},
            {"role": "assistant", "content": f"Assistant response {i+1}"}
        ])
    return history
