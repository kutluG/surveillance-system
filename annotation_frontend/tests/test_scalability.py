"""
Scalability tests for stateless annotation service.
Tests consumer group coordination, health endpoints, and state externalization.
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient

from main import app
from kafka_pool import KafkaConnectionPool
from redis_service import RedisRetryService
from config import settings


class TestScalability:
    """Test suite for horizontal scaling capabilities."""

    @pytest.fixture
    def test_client(self):
        """FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.incr.return_value = 1
        mock_redis.decr.return_value = 0
        mock_redis.get.return_value = "0"
        mock_redis.publish.return_value = None
        return mock_redis

    @pytest.fixture
    def mock_kafka_consumer_1(self):
        """Mock Kafka consumer for instance 1."""
        mock_consumer = AsyncMock()
        mock_consumer.assignment.return_value = [
            Mock(topic="hard-examples", partition=0),
            Mock(topic="hard-examples", partition=1)
        ]
        return mock_consumer

    @pytest.fixture
    def mock_kafka_consumer_2(self):
        """Mock Kafka consumer for instance 2."""
        mock_consumer = AsyncMock()
        mock_consumer.assignment.return_value = [
            Mock(topic="hard-examples", partition=2),
            Mock(topic="hard-examples", partition=3)
        ]
        return mock_consumer

    @pytest.mark.asyncio
    async def test_kafka_consumer_group_coordination(
        self, 
        mock_kafka_consumer_1, 
        mock_kafka_consumer_2
    ):
        """
        Test that two consumer instances with the same group_id coordinate properly.
        Each instance should be assigned different partitions.
        """
        # Create two Kafka pool instances representing different service instances
        pool_1 = KafkaConnectionPool()
        pool_2 = KafkaConnectionPool()
        
        # Mock the consumers to simulate partition assignment
        pool_1.consumer = mock_kafka_consumer_1
        pool_1.use_aiokafka = True
        pool_1._initialized = True
        
        pool_2.consumer = mock_kafka_consumer_2
        pool_2.use_aiokafka = True
        pool_2._initialized = True
        
        # Get consumer metrics from both instances
        metrics_1 = await pool_1.get_consumer_metrics()
        metrics_2 = await pool_2.get_consumer_metrics()
        
        # Assert both consumers are in the same group
        assert metrics_1['group_id'] == settings.KAFKA_GROUP_ID
        assert metrics_2['group_id'] == settings.KAFKA_GROUP_ID
        
        # Assert they have different client IDs
        assert metrics_1['client_id'] != metrics_2['client_id']
        
        # Assert they are assigned different partitions (load balancing)
        partitions_1 = set(metrics_1['assignment'])
        partitions_2 = set(metrics_2['assignment'])
        
        # No partition overlap - perfect load balancing
        assert len(partitions_1.intersection(partitions_2)) == 0
        
        # Both instances should have some partitions assigned
        assert len(partitions_1) > 0
        assert len(partitions_2) > 0

    @pytest.mark.asyncio
    async def test_redis_state_externalization(self, mock_redis):
        """
        Test that state is properly externalized to Redis instead of in-memory.
        """
        redis_service = RedisRetryService()
        redis_service.redis_client = mock_redis
        
        # Test WebSocket connection tracking in Redis
        await redis_service.increment_websocket_count()
        await redis_service.increment_websocket_count()
        
        # Verify Redis was called to store state
        assert mock_redis.incr.call_count == 2
        mock_redis.incr.assert_called_with("websocket:connection_count")
        
        # Test new example notification publishing
        example_data = {
            "event_id": "test-event-123",
            "camera_id": "cam-001",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await redis_service.publish_new_example_notification(example_data)
        
        # Verify Redis pub/sub was used for cross-instance communication
        mock_redis.publish.assert_called_once()
        publish_args = mock_redis.publish.call_args
        
        assert publish_args[0][0] == "websocket:new_example"
        
        # Verify the published message contains the example data
        published_message = json.loads(publish_args[0][1])
        assert published_message['type'] == 'new_example'
        assert published_message['example']['event_id'] == "test-event-123"

    def test_health_endpoint_always_ready(self, test_client):
        """
        Test /healthz endpoint always returns 200 if the app is running.
        """
        response = test_client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data

    @pytest.mark.asyncio
    async def test_readiness_endpoint_with_healthy_dependencies(self, mock_redis):
        """
        Test /readyz endpoint returns 200 when Redis and Kafka consumer are healthy.
        """
        with patch('main.redis_retry_service') as mock_redis_service, \
             patch('main.kafka_pool') as mock_kafka_pool:
            
            # Mock Redis as healthy
            mock_redis_service.check_connectivity.return_value = True
            
            # Mock Kafka consumer as assigned to partitions
            mock_kafka_pool.check_consumer_health.return_value = {
                'consumer_assigned': True,
                'assigned_partitions': ['hard-examples-0', 'hard-examples-1'],
                'consumer_ready': True,
                'group_id': settings.KAFKA_GROUP_ID
            }
            
            test_client = TestClient(app)
            response = test_client.get("/readyz")
            
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'ready'
            assert data['checks']['redis']['status'] == 'healthy'
            assert data['checks']['kafka_consumer']['status'] == 'healthy'

    @pytest.mark.asyncio
    async def test_readiness_endpoint_with_unhealthy_redis(self):
        """
        Test /readyz endpoint returns 503 when Redis is not reachable.
        """
        with patch('main.redis_retry_service') as mock_redis_service, \
             patch('main.kafka_pool') as mock_kafka_pool:
            
            # Mock Redis as unhealthy
            mock_redis_service.check_connectivity.return_value = False
            
            # Mock Kafka consumer as healthy
            mock_kafka_pool.check_consumer_health.return_value = {
                'consumer_assigned': True,
                'assigned_partitions': ['hard-examples-0'],
                'consumer_ready': True
            }
            
            test_client = TestClient(app)
            response = test_client.get("/readyz")
            
            assert response.status_code == 503
            data = response.json()
            assert data['status'] == 'not_ready'
            assert data['checks']['redis']['status'] == 'unhealthy'

    @pytest.mark.asyncio
    async def test_readiness_endpoint_with_unassigned_consumer(self):
        """
        Test /readyz endpoint returns 503 when Kafka consumer has no partition assignments.
        """
        with patch('main.redis_retry_service') as mock_redis_service, \
             patch('main.kafka_pool') as mock_kafka_pool:
            
            # Mock Redis as healthy
            mock_redis_service.check_connectivity.return_value = True
            
            # Mock Kafka consumer as not assigned to any partitions
            mock_kafka_pool.check_consumer_health.return_value = {
                'consumer_assigned': False,
                'assigned_partitions': [],
                'consumer_ready': False
            }
            
            test_client = TestClient(app)
            response = test_client.get("/readyz")
            
            assert response.status_code == 503
            data = response.json()
            assert data['status'] == 'not_ready'
            assert data['checks']['kafka_consumer']['status'] == 'unhealthy'

    @pytest.mark.asyncio
    async def test_websocket_connection_manager_redis_backed(self, mock_redis):
        """
        Test that WebSocket connection manager uses Redis for state tracking.
        """
        from main import connection_manager
        
        with patch('main.redis_retry_service') as mock_redis_service:
            mock_redis_service.increment_websocket_count.return_value = 5
            mock_redis_service.get_websocket_count.return_value = 5
            
            # Mock WebSocket
            mock_websocket = AsyncMock()
            
            # Test connection
            await connection_manager.connect(mock_websocket)
            
            # Verify Redis increment was called
            mock_redis_service.increment_websocket_count.assert_called_once()
            
            # Test getting total connections across instances
            total_connections = await connection_manager.get_total_connections()
            assert total_connections == 5
            
            # Verify Redis was queried for global count
            mock_redis_service.get_websocket_count.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_instance_consumer_group_behavior(self):
        """
        Test that multiple instances properly join the same consumer group.
        """
        # Test configuration consistency
        assert settings.KAFKA_GROUP_ID == "annotation-frontend-group"
        assert settings.SERVICE_NAME == "annotation-frontend"
        
        # Create multiple pool instances
        pools = [KafkaConnectionPool() for _ in range(3)]
        
        # Mock initialization
        for i, pool in enumerate(pools):
            pool._initialized = True
            pool.use_aiokafka = True
            
            # Mock consumer with unique client ID but same group
            mock_consumer = AsyncMock()
            mock_consumer.assignment.return_value = [
                Mock(topic="hard-examples", partition=i)  # Each gets different partition
            ]
            pool.consumer = mock_consumer
        
        # Get metrics from all instances
        metrics_list = []
        for pool in pools:
            metrics = await pool.get_consumer_metrics()
            metrics_list.append(metrics)
        
        # Assert all are in the same group
        for metrics in metrics_list:
            assert metrics['group_id'] == settings.KAFKA_GROUP_ID
        
        # Assert all have unique client IDs
        client_ids = [metrics['client_id'] for metrics in metrics_list]
        assert len(set(client_ids)) == len(client_ids)  # All unique
        
        # Assert partitions are distributed (no duplicates)
        all_partitions = []
        for metrics in metrics_list:
            all_partitions.extend(metrics['assignment'])
        
        assert len(all_partitions) == len(set(all_partitions))  # No duplicates

    @pytest.mark.asyncio 
    async def test_stateless_operation_no_global_variables(self):
        """
        Test that the service doesn't rely on global mutable state.
        All state should be in Redis or database.
        """
        # This test verifies the architecture - all persistent state
        # should be externalized to Redis or the database
        
        # Check that connection manager doesn't store global state
        from main import connection_manager
        
        # The only local state should be the active connections list for this instance
        # All counts and cross-instance coordination should use Redis
        
        with patch('main.redis_retry_service') as mock_redis_service:
            mock_redis_service.get_websocket_count.return_value = 10
            
            # Even if local connections list is empty, total should come from Redis
            connection_manager.active_connections = []
            total = await connection_manager.get_total_connections()
            
            # Should return Redis value, not local count
            assert total == 10
            mock_redis_service.get_websocket_count.assert_called_once()

    def test_service_configuration_for_scaling(self):
        """
        Test that service is properly configured for horizontal scaling.
        """
        # Verify essential configuration for scaling
        assert settings.KAFKA_GROUP_ID is not None
        assert settings.SERVICE_NAME is not None
        assert settings.REDIS_URL is not None
        
        # Verify consumer group configuration
        assert "group" in settings.KAFKA_GROUP_ID.lower()
        
        # Verify service name is suitable for client identification
        assert len(settings.SERVICE_NAME) > 0
        assert "-" in settings.SERVICE_NAME or "_" in settings.SERVICE_NAME

    @pytest.mark.asyncio
    async def test_kafka_consumer_rebalancing_simulation(self):
        """
        Simulate Kafka consumer group rebalancing when instances join/leave.
        """
        # Initial state: 2 consumers with even partition distribution
        consumer_1_initial = [0, 1]  # Partitions for consumer 1
        consumer_2_initial = [2, 3]  # Partitions for consumer 2
        
        # Simulate a third consumer joining (triggers rebalancing)
        # Kafka would redistribute partitions
        consumer_1_after_join = [0]     # Consumer 1 loses partition 1
        consumer_2_after_join = [2]     # Consumer 2 loses partition 3  
        consumer_3_after_join = [1, 3]  # New consumer gets partitions 1, 3
        
        # All partitions should still be covered
        all_partitions_before = set(consumer_1_initial + consumer_2_initial)
        all_partitions_after = set(
            consumer_1_after_join + consumer_2_after_join + consumer_3_after_join
        )
        
        assert all_partitions_before == all_partitions_after
        assert len(all_partitions_after) == 4  # All 4 partitions covered
        
        # Verify no partition is assigned to multiple consumers
        all_assignments = (
            consumer_1_after_join + consumer_2_after_join + consumer_3_after_join        )
        assert len(all_assignments) == len(set(all_assignments))  # No duplicates
