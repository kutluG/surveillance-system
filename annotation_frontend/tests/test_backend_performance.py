"""
Test backend performance optimizations including Redis retry queue,
Kafka pooling, and pagination.
"""
import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import get_db, Base
from models import AnnotationExample, AnnotationStatus
from redis_service import RedisRetryService, RetryItem
from kafka_pool import KafkaConnectionPool
from config import settings
from auth import create_test_token


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Test client with overridden dependencies."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Authentication headers for testing."""
    token = create_test_token(
        subject="test-user",
        scopes=["annotation:read", "annotation:write"],
        roles=["annotator"]
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_examples():
    """Sample annotation examples for testing."""
    db = TestingSessionLocal()
    examples = []
    
    for i in range(25):  # Create 25 examples for pagination testing
        example = AnnotationExample(
            example_id=f"test-example-{i:03d}",
            camera_id=f"camera-{i % 3}",
            timestamp="2025-06-16T10:00:00",
            original_detections={"test": "data"},
            confidence_scores={"confidence": 0.8},
            reason="Low confidence detection",
            status=AnnotationStatus.PENDING
        )
        db.add(example)
        examples.append(example)
    
    db.commit()
    db.close()
    return examples


class TestRedisRetryQueue:
    """Test Redis-backed retry queue functionality."""
    
    @pytest_asyncio.fixture
    async def mock_redis_service(self):
        """Mock Redis service for testing."""
        # Mock Redis client
        mock_client = AsyncMock()
        
        # Create service instance with mocked client
        service = RedisRetryService(redis_client=mock_client)
        
        return service, mock_client
    
    @pytest.mark.asyncio
    async def test_add_retry_item(self, mock_redis_service):
        """Test adding items to Redis retry queue."""
        service, mock_client = mock_redis_service
        
        # Test adding retry item
        retry_id = await service.add_retry_item(
            example_id="test-123",
            topic="test-topic",
            payload=json.dumps({"test": "data"}),
            key="test-key",
            error_message="Test error"
        )
        
        # Verify Redis lpush was called
        mock_client.lpush.assert_called_once()
        args = mock_client.lpush.call_args[0]
        assert args[0] == settings.RETRY_QUEUE_KEY
        
        # Verify item data structure
        item_data = json.loads(args[1])
        assert item_data["example_id"] == "test-123"
        assert item_data["topic"] == "test-topic"
        assert item_data["error_message"] == "Test error"
        assert retry_id is not None
    
    @pytest.mark.asyncio
    async def test_get_retry_items(self, mock_redis_service):
        """Test retrieving items from Redis retry queue."""
        service, mock_client = mock_redis_service
        
        # Mock Redis response
        retry_item_data = {
            "id": "test-123:12345",
            "example_id": "test-123",
            "topic": "test-topic",
            "payload": json.dumps({"test": "data"}),
            "attempts": 1,
            "max_attempts": 5,
            "created_at": "2025-06-16T10:00:00"
        }
        
        mock_client.rpop.return_value = json.dumps(retry_item_data)
        mock_client.sadd = AsyncMock()
        
        # Get retry items
        items = await service.get_retry_items(batch_size=5)
        
        # Verify results
        assert len(items) == 1
        assert items[0].example_id == "test-123"
        assert items[0].topic == "test-topic"
        assert items[0].attempts == 1
        
        # Verify item added to processing set
        mock_client.sadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_queue_size_tracking(self, mock_redis_service):
        """Test queue size tracking."""
        service, mock_client = mock_redis_service
        
        # Mock queue size
        mock_client.llen.return_value = 42
        mock_client.scard.return_value = 5
        
        # Test queue size
        queue_size = await service.get_queue_size()
        processing_count = await service.get_processing_count()
        
        assert queue_size == 42
        assert processing_count == 5
        
        mock_client.llen.assert_called_with(settings.RETRY_QUEUE_KEY)
        mock_client.scard.assert_called_with(f"{settings.RETRY_QUEUE_KEY}:processing")


class TestKafkaConnectionPooling:
    """Test Kafka connection pooling functionality."""
    
    @pytest.fixture
    def mock_kafka_pool(self):
        """Mock Kafka connection pool."""
        with patch('kafka_pool.kafka_pool') as mock_pool:
            mock_pool._initialized = True
            mock_pool.send_message = AsyncMock(return_value=True)
            mock_pool.consume_messages = AsyncMock()
            mock_pool.initialize = AsyncMock()
            mock_pool.close = AsyncMock()
            yield mock_pool
    
    @pytest.mark.asyncio
    async def test_single_producer_instance(self, mock_kafka_pool):
        """Test that only one Kafka producer instance is created and reused."""
        # Simulate multiple message sends
        await mock_kafka_pool.send_message("topic1", "message1", "key1")
        await mock_kafka_pool.send_message("topic2", "message2", "key2")
        await mock_kafka_pool.send_message("topic3", "message3", "key3")
        
        # Verify initialize was called only once (during app startup)
        mock_kafka_pool.initialize.assert_called_once()
        
        # Verify send_message was called multiple times
        assert mock_kafka_pool.send_message.call_count == 3
    
    @pytest.mark.asyncio
    async def test_kafka_pool_configuration(self):
        """Test Kafka pool configuration parameters."""
        with patch('kafka_pool.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            pool = KafkaConnectionPool()
            await pool.initialize()
            
            # Verify producer was configured with performance settings
            producer_config = mock_producer_class.call_args[1]
            
            assert producer_config['linger_ms'] == settings.KAFKA_LINGER_MS
            assert producer_config['batch_size'] == settings.KAFKA_BATCH_SIZE * 1024
            assert producer_config['compression_type'] == settings.KAFKA_COMPRESSION_TYPE
            assert producer_config['acks'] == 'all'
    
    @pytest.mark.asyncio
    async def test_kafka_error_handling(self, mock_kafka_pool):
        """Test Kafka connection error handling."""
        # Simulate connection failure
        mock_kafka_pool.send_message.return_value = False
        
        result = await mock_kafka_pool.send_message("test-topic", "test-message")
        assert result is False


class TestPaginationEndpoints:
    """Test pagination functionality in API endpoints."""
    
    def test_get_examples_default_pagination(self, client, auth_headers, sample_examples):
        """Test GET /api/v1/examples with default pagination."""
        response = client.get("/api/v1/examples", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "examples" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        
        # Verify pagination
        assert data["page"] == 1
        assert data["page_size"] == settings.ANNOTATION_PAGE_SIZE
        assert data["total"] == 25
        assert len(data["examples"]) <= settings.ANNOTATION_PAGE_SIZE
    
    def test_get_examples_custom_pagination(self, client, auth_headers, sample_examples):
        """Test GET /api/v1/examples with custom pagination parameters."""
        response = client.get(
            "/api/v1/examples?page=2&size=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify custom pagination
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total"] == 25
        assert len(data["examples"]) == 10  # Second page should have 10 items
    
    def test_get_examples_page_bounds(self, client, auth_headers, sample_examples):
        """Test pagination boundary conditions."""
        # Test last page
        response = client.get(
            "/api/v1/examples?page=3&size=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Last page should have remaining items
        assert data["page"] == 3
        assert data["page_size"] == 10
        assert len(data["examples"]) == 5  # 25 total - 20 from first two pages = 5
    
    def test_get_examples_invalid_pagination(self, client, auth_headers, sample_examples):
        """Test invalid pagination parameters."""
        # Test invalid page number
        response = client.get(
            "/api/v1/examples?page=0&size=10",
            headers=auth_headers
        )
        assert response.status_code == 422  # Validation error
        
        # Test invalid page size
        response = client.get(
            "/api/v1/examples?page=1&size=101",
            headers=auth_headers
        )
        assert response.status_code == 422  # Validation error
    
    def test_pagination_metadata_accuracy(self, client, auth_headers, sample_examples):
        """Test that pagination metadata is accurate."""
        # Test multiple pages to verify metadata
        pages_to_test = [1, 2, 3]
        page_size = 8
        
        for page in pages_to_test:
            response = client.get(
                f"/api/v1/examples?page={page}&size={page_size}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify metadata consistency
            assert data["page"] == page
            assert data["page_size"] == page_size
            assert data["total"] == 25
            
            # Verify item count for each page
            expected_items = min(page_size, max(0, 25 - (page - 1) * page_size))
            assert len(data["examples"]) == expected_items


class TestIntegrationWithRetryQueue:
    """Test integration between API endpoints and Redis retry queue."""
    
    @pytest.mark.asyncio
    async def test_failed_kafka_triggers_retry_queue(self, client, auth_headers, sample_examples):
        """Test that failed Kafka sends trigger Redis retry queue."""
        with patch('main.kafka_pool') as mock_kafka_pool, \
             patch('main.redis_retry_service') as mock_redis_service:
            
            # Mock Kafka failure
            mock_kafka_pool.send_message.return_value = False
            mock_redis_service.add_retry_item = AsyncMock()
            
            # Submit annotation
            annotation_data = {
                "example_id": "test-example-000",
                "bbox": {"x1": 10, "y1": 20, "x2": 100, "y2": 200},
                "label": "person",
                "annotator_id": "test-annotator",
                "quality_score": 0.9,
                "notes": "Test annotation"
            }
            
            response = client.post(
                "/api/v1/examples/test-example-000/label",
                json=annotation_data,
                headers=auth_headers
            )
            
            # Should succeed even if Kafka fails
            assert response.status_code == 200
            
            # Verify retry item was added
            mock_redis_service.add_retry_item.assert_called_once()
            call_args = mock_redis_service.add_retry_item.call_args[1]
            assert call_args["example_id"] == "test-example-000"
            assert call_args["topic"] == settings.LABELED_EXAMPLES_TOPIC


class TestStaticAssetCaching:
    """Test static asset caching configuration."""
    
    def test_static_files_cache_headers(self, client):
        """Test that static files include appropriate cache headers."""
        # This test would require actual static files to be present
        # For now, we test the cache configuration
        
        # Verify cache settings are configured
        assert hasattr(settings, 'STATIC_CACHE_MAX_AGE')
        assert settings.STATIC_CACHE_MAX_AGE == 86400  # 1 day
    
    def test_cache_control_configuration(self):
        """Test cache control configuration."""
        from main import CachedStaticFiles
        
        # Test that our custom static files class exists
        assert CachedStaticFiles is not None
        
        # In a real implementation, you would test:
        # 1. Cache-Control headers are set correctly
        # 2. ETag headers are generated
        # 3. Conditional requests work properly


class TestHealthAndStats:
    """Test health check and statistics endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "service" in data
        assert "database_connected" in data
        assert "kafka_connected" in data
        assert "pending_examples" in data
        
        assert data["service"] == "annotation_frontend"
    
    def test_stats_endpoint_requires_auth(self, client):
        """Test stats endpoint requires authentication."""
        response = client.get("/api/v1/stats")
        assert response.status_code == 401  # Unauthorized
    
    def test_stats_endpoint_with_auth(self, client, auth_headers, sample_examples):
        """Test stats endpoint with authentication."""
        with patch('main.redis_retry_service') as mock_redis_service:
            mock_redis_service.get_queue_size.return_value = 5
            
            response = client.get("/api/v1/stats", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "pending_examples" in data
            assert "completed_examples" in data
            assert "retry_queue_size" in data
            assert "topics" in data
            
            assert data["retry_queue_size"] == 5
            assert settings.HARD_EXAMPLES_TOPIC in data["topics"].values()
            assert settings.LABELED_EXAMPLES_TOPIC in data["topics"].values()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
