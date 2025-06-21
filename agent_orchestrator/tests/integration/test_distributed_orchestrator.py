"""
Comprehensive tests for the Distributed Orchestrator

Tests cover:
- State synchronization across instances
- Leader election mechanisms
- Distributed task assignment
- Event-driven coordination
- Distributed locking
- Fault tolerance and recovery
"""

import asyncio
import pytest
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from distributed_orchestrator import (
    DistributedOrchestrator,
    DistributedState,
    LeaderElection,
    EventDrivenCoordinator,
    CapabilityDomain,
    TaskPriority,
    OrchestratorRole,
    DistributedTask,
    AgentInfo,
    OrchestratorInstance
)


class TestDistributedState:
    """Test distributed state management via Redis"""
    
    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis client"""
        redis_mock = AsyncMock()
        redis_mock.keys.return_value = []
        redis_mock.hgetall.return_value = {}
        redis_mock.hset.return_value = True
        redis_mock.expire.return_value = True
        return redis_mock
    
    @pytest.fixture
    def distributed_state(self, mock_redis):
        """Create DistributedState instance with mock Redis"""
        return DistributedState(mock_redis)
    
    @pytest.mark.asyncio
    async def test_set_instance_info(self, distributed_state, mock_redis):
        """Test storing orchestrator instance information"""
        instance = OrchestratorInstance(
            instance_id="test-instance",
            hostname="test-host",
            port=8000,
            role=OrchestratorRole.FOLLOWER,
            capabilities=[CapabilityDomain.RAG_ANALYSIS],
            last_heartbeat=datetime.utcnow()
        )
        
        await distributed_state.set_instance_info(instance)
        
        # Verify Redis calls
        mock_redis.hset.assert_called_once()
        mock_redis.expire.assert_called_once()
        
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == "orchestrator:instances:test-instance"
    
    @pytest.mark.asyncio
    async def test_get_all_instances(self, distributed_state, mock_redis):
        """Test retrieving all orchestrator instances"""
        # Mock Redis response
        mock_redis.keys.return_value = ["orchestrator:instances:test-1", "orchestrator:instances:test-2"]
        mock_redis.hgetall.side_effect = [
            {
                'instance_id': 'test-1',
                'hostname': 'host-1',
                'port': '8000',
                'role': 'follower',
                'capabilities': '["rag_analysis"]',
                'last_heartbeat': '2023-01-01T12:00:00',
                'load_score': '0.5',
                'active_tasks': '2'
            },
            {}  # Empty dict to test filtering
        ]
        
        instances = await distributed_state.get_all_instances()
        
        assert len(instances) == 1
        assert instances[0].instance_id == "test-1"
        assert instances[0].hostname == "host-1"
        assert instances[0].port == 8000
    
    @pytest.mark.asyncio
    async def test_set_and_get_task(self, distributed_state, mock_redis):
        """Test storing and retrieving distributed tasks"""
        task = DistributedTask(
            task_id="test-task",
            task_type="test_type",
            capability_domain=CapabilityDomain.RAG_ANALYSIS,
            priority=TaskPriority.HIGH,
            payload={"key": "value"},
            created_at=datetime.utcnow()
        )
        
        # Test set_task
        await distributed_state.set_task(task)
        mock_redis.hset.assert_called_once()
        
        # Test get_task
        mock_redis.hgetall.return_value = {
            'task_id': 'test-task',
            'task_type': 'test_type',
            'capability_domain': 'rag_analysis',
            'priority': 'high',
            'payload': '{"key": "value"}',
            'created_at': '2023-01-01T12:00:00',
            'assigned_to': '',
            'assigned_at': '',
            'status': 'pending',
            'retry_count': '0',
            'max_retries': '3',
            'timeout_seconds': '300'
        }
        
        retrieved_task = await distributed_state.get_task("test-task")
        
        assert retrieved_task.task_id == "test-task"
        assert retrieved_task.capability_domain == CapabilityDomain.RAG_ANALYSIS
        assert retrieved_task.priority == TaskPriority.HIGH


class TestLeaderElection:
    """Test leader election mechanism"""
    
    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis client for leader election"""
        redis_mock = AsyncMock()
        redis_mock.set.return_value = True
        redis_mock.get.return_value = None
        redis_mock.expire.return_value = True
        redis_mock.delete.return_value = True
        return redis_mock
    
    @pytest.fixture
    def leader_election(self, mock_redis):
        """Create LeaderElection instance"""
        return LeaderElection(mock_redis, "test-instance")
    
    @pytest.mark.asyncio
    async def test_become_leader(self, leader_election, mock_redis):
        """Test becoming leader"""
        # Mock successful leader acquisition
        mock_redis.set.return_value = True
        
        await leader_election._attempt_leadership()
        
        assert leader_election.is_leader is True
        mock_redis.set.assert_called_once_with(
            "orchestrator:leader",
            "test-instance",
            nx=True,
            ex=30
        )
    
    @pytest.mark.asyncio
    async def test_lose_leadership(self, leader_election, mock_redis):
        """Test losing leadership"""
        # First become leader
        leader_election.is_leader = True
        
        # Mock leadership lost (another instance is leader)
        mock_redis.set.return_value = False
        mock_redis.get.return_value = "other-instance"
        
        await leader_election._attempt_leadership()
        
        assert leader_election.is_leader is False
    
    @pytest.mark.asyncio
    async def test_maintain_leadership(self, leader_election, mock_redis):
        """Test maintaining leadership"""
        # Set as current leader
        leader_election.is_leader = True
        
        # Mock maintaining leadership
        mock_redis.set.return_value = False
        mock_redis.get.return_value = "test-instance"
        
        await leader_election._attempt_leadership()
        
        assert leader_election.is_leader is True
        mock_redis.expire.assert_called_once_with("orchestrator:leader", 30)
    
    @pytest.mark.asyncio
    async def test_release_leadership(self, leader_election, mock_redis):
        """Test voluntary leadership release"""
        leader_election.is_leader = True
        mock_redis.get.return_value = "test-instance"
        
        await leader_election._release_leadership()
        
        assert leader_election.is_leader is False
        mock_redis.delete.assert_called_once_with("orchestrator:leader")


class TestEventDrivenCoordinator:
    """Test Kafka-based event coordination"""
    
    @pytest.fixture
    def mock_producer(self):
        """Mock Kafka producer"""
        producer = MagicMock()
        producer.produce = MagicMock()
        producer.flush = MagicMock()
        return producer
    
    @pytest.fixture
    def mock_consumer(self):
        """Mock Kafka consumer"""
        consumer = MagicMock()
        consumer.subscribe = MagicMock()
        consumer.poll = MagicMock()
        consumer.close = MagicMock()
        return consumer
    
    @pytest.fixture
    def event_coordinator(self):
        """Create EventDrivenCoordinator instance"""
        kafka_config = {'bootstrap.servers': 'localhost:9092'}
        return EventDrivenCoordinator(kafka_config, "test-instance")
    
    @pytest.mark.asyncio
    async def test_publish_coordination_event(self, event_coordinator, mock_producer):
        """Test publishing coordination events"""
        event_coordinator.producer = mock_producer
        
        await event_coordinator.publish_coordination_event(
            "instance_started", 
            {"capabilities": ["rag_analysis"]}
        )
        
        mock_producer.produce.assert_called_once()
        mock_producer.flush.assert_called_once()
        
        # Verify event structure
        call_args = mock_producer.produce.call_args
        assert call_args[1]['topic'] == 'orchestrator.coordination'
        assert call_args[1]['key'] == 'test-instance'
        
        event_data = json.loads(call_args[1]['value'])
        assert event_data['event_type'] == 'instance_started'
        assert event_data['instance_id'] == 'test-instance'
    
    @pytest.mark.asyncio
    async def test_publish_task_event(self, event_coordinator, mock_producer):
        """Test publishing task-related events"""
        event_coordinator.producer = mock_producer
        
        await event_coordinator.publish_task_event(
            "task-123", 
            "task_assigned", 
            {"agent_id": "agent-456"}
        )
        
        mock_producer.produce.assert_called_once()
        
        call_args = mock_producer.produce.call_args
        assert call_args[1]['topic'] == 'orchestrator.task_events'
        assert call_args[1]['key'] == 'task-123'


class TestDistributedOrchestrator:
    """Test the main distributed orchestrator functionality"""
    
    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis client"""
        redis_mock = AsyncMock()
        redis_mock.ping.return_value = True
        redis_mock.from_url = AsyncMock(return_value=redis_mock)
        return redis_mock
    
    @pytest.fixture
    def orchestrator(self):
        """Create DistributedOrchestrator instance"""
        return DistributedOrchestrator("test-orchestrator")
    
    @pytest.mark.asyncio
    async def test_initialization(self, orchestrator, mock_redis):
        """Test orchestrator initialization"""
        with patch('distributed_orchestrator.redis.from_url', return_value=mock_redis):
            with patch('distributed_orchestrator.httpx.AsyncClient'):
                with patch.object(orchestrator, '_initialize_circuit_breakers'):
                    with patch.object(orchestrator, 'event_coordinator') as mock_coordinator:
                        mock_coordinator.initialize = AsyncMock()
                        
                        await orchestrator.initialize()
                        
                        assert orchestrator.redis_client is not None
                        assert orchestrator.distributed_state is not None
                        assert orchestrator.leader_election is not None
    
    @pytest.mark.asyncio
    async def test_agent_registration(self, orchestrator, mock_redis):
        """Test agent registration in distributed system"""
        # Setup mocks
        orchestrator.distributed_state = AsyncMock()
        orchestrator.event_coordinator = AsyncMock()
        orchestrator.event_coordinator.publish_coordination_event = AsyncMock()
        
        agent_spec = {
            'agent_id': 'test-agent',
            'capability_domain': CapabilityDomain.RAG_ANALYSIS.value,
            'endpoint': 'http://test:8000',
            'load_score': 0.5,
            'status': 'active'
        }
        
        result = await orchestrator.register_agent(agent_spec)
        
        assert result is True
        assert 'test-agent' in orchestrator.registered_agents
        orchestrator.distributed_state.set_agent_info.assert_called_once()
        orchestrator.event_coordinator.publish_coordination_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_task_assignment(self, orchestrator, mock_redis):
        """Test distributed task assignment"""
        # Setup mocks
        orchestrator.distributed_state = AsyncMock()
        orchestrator.event_coordinator = AsyncMock()
        orchestrator.event_coordinator.publish_task_event = AsyncMock()
        orchestrator.redis_client = mock_redis
        
        # Mock finding best agent
        orchestrator._find_best_agent = AsyncMock(return_value="test-agent")
        orchestrator._record_assignment = AsyncMock()
        
        task_spec = {
            'task_type': 'analyze_event',
            'capability_domain': CapabilityDomain.RAG_ANALYSIS.value,
            'priority': TaskPriority.HIGH.value,
            'payload': {'test': 'data'}
        }
        
        # Mock distributed lock
        with patch('distributed_orchestrator.redis_lock.Lock') as mock_lock:
            mock_lock.return_value.__aenter__ = AsyncMock()
            mock_lock.return_value.__aexit__ = AsyncMock()
            
            task_id = await orchestrator.assign_task(task_spec)
            
            assert task_id is not None
            assert task_id in orchestrator.active_tasks
            
            # Verify task was assigned
            task = orchestrator.active_tasks[task_id]
            assert task.assigned_to == "test-agent"
            assert task.status == "assigned"
    
    @pytest.mark.asyncio
    async def test_find_best_agent(self, orchestrator):
        """Test finding best agent for capability domain"""
        # Setup mock agents
        agents = [
            AgentInfo(
                agent_id="agent-1",
                capability_domain=CapabilityDomain.RAG_ANALYSIS,
                instance_id="instance-1",
                endpoint="http://agent1:8000",
                load_score=0.8,
                last_seen=datetime.utcnow()
            ),
            AgentInfo(
                agent_id="agent-2",
                capability_domain=CapabilityDomain.RAG_ANALYSIS,
                instance_id="instance-2",
                endpoint="http://agent2:8000",
                load_score=0.3,
                last_seen=datetime.utcnow()
            )
        ]
        
        orchestrator.distributed_state = AsyncMock()
        orchestrator.distributed_state.get_agents_by_capability.return_value = agents
        
        best_agent = await orchestrator._find_best_agent(CapabilityDomain.RAG_ANALYSIS)
        
        # Should select agent with lowest load score
        assert best_agent == "agent-2"
    
    @pytest.mark.asyncio
    async def test_cluster_status(self, orchestrator):
        """Test getting cluster status"""
        # Setup mocks
        orchestrator.distributed_state = AsyncMock()
        orchestrator.leader_election = AsyncMock()
        
        # Mock instances
        instances = [
            OrchestratorInstance(
                instance_id="instance-1",
                hostname="host-1",
                port=8000,
                role=OrchestratorRole.LEADER,
                capabilities=[CapabilityDomain.RAG_ANALYSIS],
                last_heartbeat=datetime.utcnow(),
                active_tasks=2
            )
        ]
        orchestrator.distributed_state.get_all_instances.return_value = instances
        orchestrator.leader_election.get_current_leader.return_value = "instance-1"
        
        # Mock agents by capability
        orchestrator.distributed_state.get_agents_by_capability.return_value = []
        
        status = await orchestrator.get_cluster_status()
        
        assert status['total_instances'] == 1
        assert status['current_leader'] == 'instance-1'
        assert 'instances' in status
        assert 'agent_capabilities' in status
    
    @pytest.mark.asyncio
    async def test_distributed_lock_success(self, orchestrator, mock_redis):
        """Test successful distributed lock acquisition"""
        orchestrator.redis_client = mock_redis
        
        # Mock successful lock
        with patch('distributed_orchestrator.redis_lock.Lock') as mock_lock:
            lock_instance = MagicMock()
            lock_instance.acquire.return_value = True
            lock_instance.release.return_value = None
            mock_lock.return_value = lock_instance
            
            async with orchestrator.distributed_lock("test-resource"):
                # Lock acquired successfully
                pass
            
            lock_instance.acquire.assert_called_once()
            lock_instance.release.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_distributed_lock_failure(self, orchestrator, mock_redis):
        """Test distributed lock acquisition failure"""
        orchestrator.redis_client = mock_redis
        
        # Mock failed lock acquisition
        with patch('distributed_orchestrator.redis_lock.Lock') as mock_lock:
            lock_instance = MagicMock()
            lock_instance.acquire.return_value = False
            mock_lock.return_value = lock_instance
            
            with pytest.raises(Exception):  # Should raise HTTPException
                async with orchestrator.distributed_lock("test-resource", timeout=1):
                    pass


class TestIntegration:
    """Integration tests for distributed orchestrator"""
    
    @pytest.mark.asyncio
    async def test_multi_instance_coordination(self):
        """Test coordination between multiple orchestrator instances"""
        # This would be a more complex integration test
        # involving multiple orchestrator instances and real Redis/Kafka
        # For now, we'll test the coordination logic with mocks
        
        orchestrator1 = DistributedOrchestrator("instance-1")
        orchestrator2 = DistributedOrchestrator("instance-2")
        
        # Mock shared components
        shared_redis = AsyncMock()
        shared_redis.ping.return_value = True
        
        with patch('distributed_orchestrator.redis.from_url', return_value=shared_redis):
            with patch('distributed_orchestrator.httpx.AsyncClient'):
                with patch.object(orchestrator1, '_initialize_circuit_breakers'):
                    with patch.object(orchestrator2, '_initialize_circuit_breakers'):
                        # Initialize both orchestrators
                        orchestrator1.event_coordinator = AsyncMock()
                        orchestrator1.event_coordinator.initialize = AsyncMock()
                        orchestrator2.event_coordinator = AsyncMock()
                        orchestrator2.event_coordinator.initialize = AsyncMock()
                        
                        await orchestrator1.initialize()
                        await orchestrator2.initialize()
                        
                        # Verify both instances are initialized
                        assert orchestrator1.distributed_state is not None
                        assert orchestrator2.distributed_state is not None
                        
                        # Test agent registration coordination
                        agent_spec = {
                            'agent_id': 'shared-agent',
                            'capability_domain': CapabilityDomain.RAG_ANALYSIS.value,
                            'endpoint': 'http://agent:8000',
                            'load_score': 0.5
                        }
                        
                        # Register agent on first instance
                        result = await orchestrator1.register_agent(agent_spec)
                        assert result is True
                        
                        # Verify coordination event was published
                        orchestrator1.event_coordinator.publish_coordination_event.assert_called()


# Test fixtures and utilities
@pytest.fixture
def sample_orchestrator_instance():
    """Sample orchestrator instance for testing"""
    return OrchestratorInstance(
        instance_id="test-instance",
        hostname="test-host",
        port=8000,
        role=OrchestratorRole.FOLLOWER,
        capabilities=[CapabilityDomain.RAG_ANALYSIS, CapabilityDomain.NOTIFICATION],
        last_heartbeat=datetime.utcnow(),
        load_score=0.5,
        active_tasks=3
    )

@pytest.fixture
def sample_distributed_task():
    """Sample distributed task for testing"""
    return DistributedTask(
        task_id=str(uuid.uuid4()),
        task_type="analyze_event",
        capability_domain=CapabilityDomain.RAG_ANALYSIS,
        priority=TaskPriority.HIGH,
        payload={
            "camera_id": "cam_001",
            "event_type": "person_detected",
            "confidence": 0.95
        },
        created_at=datetime.utcnow()
    )

@pytest.fixture
def sample_agent_info():
    """Sample agent info for testing"""
    return AgentInfo(
        agent_id="test-agent",
        capability_domain=CapabilityDomain.RAG_ANALYSIS,
        instance_id="test-instance",
        endpoint="http://agent:8000",
        load_score=0.3,
        last_seen=datetime.utcnow(),
        status="active"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
