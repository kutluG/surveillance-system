"""
Integration Tests for Agent Orchestrator Service

This module contains integration tests that test the interaction between
multiple components and external services in a controlled environment.

Test Categories:
- Service-to-service communication tests
- Database integration tests  
- Redis integration tests
- Workflow orchestration tests
- Error handling and recovery tests
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import httpx

# Import components for integration testing
from orchestrator import OrchestratorService, OrchestrationRequest, OrchestrationResponse
from main import OrchestrationState, AgentManager, TaskManager, WorkflowManager
from main import Agent, Task, Workflow, AgentType, TaskStatus
from config import get_config


class TestServiceCommunication:
    """Integration tests for service-to-service communication"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator service with partially mocked dependencies"""
        service = OrchestratorService()
        service.redis_client = AsyncMock()
        service.http_client = AsyncMock()
        return service
    
    @pytest.fixture
    def sample_request(self):
        """Sample orchestration request for testing"""
        return OrchestrationRequest(
            event_data={
                "camera_id": "cam_001",
                "timestamp": "2025-06-13T10:30:00Z",
                "label": "person_detected",
                "bbox": {"x": 100, "y": 150, "width": 50, "height": 100}
            },
            query="Person detected in restricted area",
            notification_channels=["email", "sms"],
            recipients=["security@company.com"]
        )
    
    @pytest.mark.asyncio
    async def test_successful_full_orchestration(self, orchestrator, sample_request):
        """Test successful orchestration with all services responding correctly"""
        # Mock successful RAG service response
        rag_response = AsyncMock()
        rag_response.status_code = 200
        rag_response.json.return_value = {
            "linked_explanation": "Person detected in temporal context",
            "retrieved_context": [{"event": "previous_detection"}]
        }
        
        # Mock successful rule generation response  
        rule_response = AsyncMock()
        rule_response.status_code = 200
        rule_response.json.return_value = {
            "triggered_actions": [
                {
                    "type": "send_notification",
                    "rule_id": "person_alert",
                    "parameters": {"message": "Person detected", "severity": "high"}
                }
            ]
        }
        
        # Mock successful notifier response
        notifier_response = AsyncMock()
        notifier_response.status_code = 200
        notifier_response.json.return_value = {
            "status": "sent",
            "message_id": "msg_123"
        }
        
        # Configure mock HTTP client to return responses in order
        orchestrator.http_client.post.side_effect = [
            rag_response,
            rule_response, 
            notifier_response
        ]
        
        # Execute orchestration
        result = await orchestrator.orchestrate(sample_request)
        
        # Verify successful orchestration
        assert result.status == "ok"
        assert result.rag_result is not None
        assert result.rule_result is not None
        assert result.notification_result is not None
        assert result.details["rag_success"] is True
        assert result.details["rule_success"] is True
        assert result.details["notification_success"] is True
        
        # Verify correct number of HTTP calls
        assert orchestrator.http_client.post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_rag_service_failure_fallback(self, orchestrator, sample_request):
        """Test orchestration when RAG service is unavailable"""
        # Mock RAG service failure
        rag_response = AsyncMock()
        rag_response.status_code = 503
        rag_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=AsyncMock(), response=rag_response
        )
        
        orchestrator.http_client.post.return_value = rag_response
        
        # Execute orchestration
        result = await orchestrator.orchestrate(sample_request)
        
        # Verify fallback behavior
        assert result.status == "fallback"
        assert result.rag_result is not None
        assert "temporary service outage" in result.rag_result["linked_explanation"]
        assert result.rule_result is None  # Should skip rule generation
        assert result.details["rag_fallback_used"] is True
    
    @pytest.mark.asyncio
    async def test_notifier_failure_retry_mechanism(self, orchestrator, sample_request):
        """Test notification retry mechanism when notifier service fails"""
        # Mock successful RAG and rule responses
        rag_response = AsyncMock()
        rag_response.status_code = 200
        rag_response.json.return_value = {
            "linked_explanation": "Person detected",
            "retrieved_context": []
        }
        
        rule_response = AsyncMock()
        rule_response.status_code = 200
        rule_response.json.return_value = {
            "triggered_actions": [
                {
                    "type": "send_notification",
                    "rule_id": "alert",
                    "parameters": {"message": "Alert", "severity": "medium"}
                }
            ]
        }
        
        # Mock notifier service failure
        notifier_response = AsyncMock()
        notifier_response.status_code = 503
        notifier_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=AsyncMock(), response=notifier_response
        )
        
        orchestrator.http_client.post.side_effect = [
            rag_response,
            rule_response,
            notifier_response
        ]
        
        # Execute orchestration
        result = await orchestrator.orchestrate(sample_request)
        
        # Verify partial success with retry queuing
        assert result.status == "partial_success"
        assert result.details["notification_queued_for_retry"] is True
        assert result.notification_result["status"] == "notifier_unreachable"
        
        # Verify retry was queued
        orchestrator.redis_client.lpush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rule_generation_failure_with_defaults(self, orchestrator, sample_request):
        """Test default rule application when rule generation service fails"""
        # Mock successful RAG response
        rag_response = AsyncMock()
        rag_response.status_code = 200
        rag_response.json.return_value = {
            "linked_explanation": "Person detected",
            "retrieved_context": []
        }
        
        # Mock rule generation failure
        rule_response = AsyncMock()
        rule_response.status_code = 500
        rule_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=AsyncMock(), response=rule_response
        )
        
        # Mock successful notifier response
        notifier_response = AsyncMock()
        notifier_response.status_code = 200
        notifier_response.json.return_value = {"status": "sent"}
        
        orchestrator.http_client.post.side_effect = [
            rag_response,
            rule_response,
            notifier_response
        ]
        
        # Execute orchestration
        result = await orchestrator.orchestrate(sample_request)
        
        # Verify partial success with default rules
        assert result.status == "partial_success"
        assert result.details["default_rules_used"] is True
        assert result.rule_result is not None
        assert len(result.rule_result["triggered_actions"]) == 1
        assert result.rule_result["triggered_actions"][0]["rule_id"] == "default_alert"


class TestDatabaseIntegration:
    """Integration tests for database operations"""
    
    @pytest.mark.asyncio
    async def test_database_session_creation(self):
        """Test database session creation with configuration"""
        from main import get_database_session
        
        with patch('main.create_async_engine') as mock_engine, \
             patch('main.sessionmaker') as mock_sessionmaker:
            
            mock_session = AsyncMock()
            mock_sessionmaker.return_value = lambda: mock_session
            
            session = await get_database_session()
            
            # Verify engine was created with config URL
            mock_engine.assert_called_once()
            config = get_config()
            mock_engine.assert_called_with(config.database_url)
    
    @pytest.mark.asyncio 
    async def test_agent_persistence(self):
        """Test agent data persistence to Redis"""
        from main import AgentRegistrationRequest
        
        with patch('main.state') as mock_state, \
             patch('main.get_redis_client') as mock_redis:
            
            mock_state.agents = {}
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            request = AgentRegistrationRequest(
                type=AgentType.RAG_AGENT,
                name="Test Agent",
                endpoint="http://test:8000",
                capabilities=["test"]
            )
            
            agent_id = await AgentManager.register_agent(request)
            
            # Verify agent was stored in Redis
            mock_redis_client.hset.assert_called_once()
            call_args = mock_redis_client.hset.call_args
            assert call_args[0][0] == "agents"  # Redis key
            assert call_args[0][1] == agent_id  # Agent ID
            
            # Verify agent data was serialized
            stored_data = json.loads(call_args[0][2])
            assert stored_data["name"] == "Test Agent"
            assert stored_data["type"] == "rag_agent"


class TestRedisIntegration:
    """Integration tests for Redis operations"""
    
    @pytest.mark.asyncio
    async def test_redis_client_creation(self):
        """Test Redis client creation with configuration"""
        from main import get_redis_client
        
        with patch('main.redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.from_url.return_value = mock_client
            
            client = await get_redis_client()
            
            # Verify Redis client was created with config URL
            config = get_config()
            mock_redis.from_url.assert_called_with(config.redis_url)
    
    @pytest.mark.asyncio
    async def test_notification_retry_queue(self):
        """Test notification retry queue functionality"""
        orchestrator = OrchestratorService()
        orchestrator.redis_client = AsyncMock()
        
        notification_payload = {
            "alert": {"id": "test", "message": "test"},
            "channels": ["email"],
            "recipients": ["test@example.com"]
        }
        
        # Test enqueueing retry
        await orchestrator._enqueue_notification_retry(notification_payload)
        
        # Verify item was added to queue
        orchestrator.redis_client.lpush.assert_called_once()
        call_args = orchestrator.redis_client.lpush.call_args
        assert call_args[0][0] == "notification_retry_queue"
        
        # Verify payload structure
        queued_data = json.loads(call_args[0][1])
        assert "id" in queued_data
        assert "payload" in queued_data
        assert "timestamp" in queued_data
        assert queued_data["retry_count"] == 0


class TestWorkflowOrchestration:
    """Integration tests for workflow orchestration"""
    
    @pytest.fixture
    def mock_state_with_workflows(self):
        """Create mock state with workflow data"""
        state = OrchestrationState()
        state.workflows = {}
        state.tasks = {}
        state.task_queue = AsyncMock()
        return state
    
    @pytest.mark.asyncio
    async def test_workflow_creation_and_execution(self, mock_state_with_workflows):
        """Test complete workflow creation and execution"""
        from main import CreateWorkflowRequest, CreateTaskRequest
        
        with patch('main.state', mock_state_with_workflows), \
             patch('main.get_redis_client') as mock_redis:
            
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            # Create workflow request with multiple tasks
            workflow_request = CreateWorkflowRequest(
                name="Test Workflow",
                description="Test workflow with multiple tasks",
                user_id="user_123",
                tasks=[
                    CreateTaskRequest(
                        type="rag_query",
                        description="RAG analysis task",
                        input_data={"query": "test"}
                    ),
                    CreateTaskRequest(
                        type="notification",
                        description="Send notification",
                        input_data={"message": "workflow complete"}
                    )
                ]
            )
            
            # Create workflow
            workflow_id = await WorkflowManager.create_workflow(workflow_request)
            
            # Verify workflow was created
            assert workflow_id in mock_state_with_workflows.workflows
            workflow = mock_state_with_workflows.workflows[workflow_id]
            assert workflow.name == "Test Workflow"
            assert workflow.user_id == "user_123"
            assert len(workflow.tasks) == 2
            
            # Verify tasks were created
            assert len(mock_state_with_workflows.tasks) == 2
            for task_id in workflow.tasks:
                assert task_id in mock_state_with_workflows.tasks
                task = mock_state_with_workflows.tasks[task_id]
                assert task.workflow_id == workflow_id


class TestErrorHandlingAndRecovery:
    """Integration tests for error handling and recovery mechanisms"""
    
    @pytest.mark.asyncio
    async def test_service_timeout_handling(self):
        """Test handling of service timeouts"""
        orchestrator = OrchestratorService()
        orchestrator.redis_client = AsyncMock()
        orchestrator.http_client = AsyncMock()
        
        # Mock timeout exception
        orchestrator.http_client.post.side_effect = httpx.TimeoutException("Request timeout")
        
        request = OrchestrationRequest(
            event_data={"camera_id": "cam_001"},
            query="test"
        )
        
        # Execute orchestration - should handle timeout gracefully
        result = await orchestrator.orchestrate(request)
        
        # Verify fallback behavior
        assert result.status == "fallback"
        assert "temporary service outage" in result.rag_result["linked_explanation"]
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure_handling(self):
        """Test handling of Redis connection failures"""
        orchestrator = OrchestratorService()
        
        # Mock Redis connection failure
        with patch('orchestrator.redis.from_url') as mock_redis:
            mock_redis.side_effect = ConnectionError("Redis connection failed")
            
            # Initialization should handle the error gracefully
            with pytest.raises(Exception):  # Should propagate connection error
                await orchestrator.initialize()
    
    @pytest.mark.asyncio
    async def test_agent_failure_task_reassignment(self):
        """Test task reassignment when agent fails"""
        with patch('main.state') as mock_state:
            # Setup agents and tasks
            mock_state.agents = {
                "agent-1": Agent(
                    id="agent-1",
                    type=AgentType.RAG_AGENT,
                    name="Primary Agent",
                    endpoint="http://primary:8000",
                    capabilities=["search"],
                    status="idle"
                ),
                "agent-2": Agent(
                    id="agent-2",
                    type=AgentType.RAG_AGENT,
                    name="Backup Agent", 
                    endpoint="http://backup:8000",
                    capabilities=["search"],
                    status="idle"
                )
            }
            
            mock_state.tasks = {
                "task-1": Task(
                    id="task-1",
                    type="search",
                    description="Search task",
                    input_data={"query": "test"},
                    assigned_agents=[],
                    status=TaskStatus.PENDING,
                    created_at=datetime.utcnow()
                )
            }
            
            # Find suitable agents
            suitable_agents = await AgentManager.find_suitable_agents(
                required_capabilities=["search"],
                task_type="search"
            )
            
            # Verify multiple agents are available for failover
            assert len(suitable_agents) == 2
            assert suitable_agents[0].name in ["Primary Agent", "Backup Agent"]
            assert suitable_agents[1].name in ["Primary Agent", "Backup Agent"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
