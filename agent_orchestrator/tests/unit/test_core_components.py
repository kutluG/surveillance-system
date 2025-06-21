"""
Unit Tests for Agent Orchestrator Service

This module contains unit tests that test individual components and classes
in isolation without external dependencies like Redis, HTTP clients, or databases.

Test Categories:
- Configuration tests
- Data model tests  
- Service component tests
- Utility function tests
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

# Import the components to test
from config import OrchestratorConfig, get_config, validate_config
from main import AgentManager, TaskManager, WorkflowManager, OrchestrationState
from main import Agent, Task, Workflow, TaskStatus, AgentType
from orchestrator import OrchestratorService, OrchestrationRequest, OrchestrationResponse


class TestConfiguration:
    """Unit tests for configuration management"""
    
    def test_default_configuration_values(self):
        """Test that default configuration values are set correctly"""
        config = OrchestratorConfig()
        
        assert config.service_host == "0.0.0.0"
        assert config.service_port == 8006
        assert config.redis_url == "redis://redis:6379/0"
        assert config.rag_service_url == "http://advanced_rag_service:8000"
        assert config.log_level == "INFO"
        assert config.enable_rate_limiting is True
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults"""
        with patch.dict('os.environ', {
            'HOST': '127.0.0.1',
            'PORT': '9000',
            'LOG_LEVEL': 'DEBUG'
        }):
            config = OrchestratorConfig()
            assert config.service_host == "127.0.0.1"
            assert config.service_port == 9000
            assert config.log_level == "DEBUG"
    
    def test_port_validation(self):
        """Test port number validation"""
        with patch.dict('os.environ', {'PORT': '99999'}):
            with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
                OrchestratorConfig()
    
    def test_log_level_validation(self):
        """Test log level validation"""
        with patch.dict('os.environ', {'LOG_LEVEL': 'INVALID'}):
            with pytest.raises(ValueError, match="Log level must be one of"):
                OrchestratorConfig()
    
    def test_cors_origins_parsing(self):
        """Test CORS origins parsing from comma-separated string"""
        with patch.dict('os.environ', {
            'CORS_ORIGINS': 'http://localhost:3000,https://example.com'
        }):
            config = OrchestratorConfig()
            expected = ['http://localhost:3000', 'https://example.com']
            assert config.cors_origins == expected


class TestDataModels:
    """Unit tests for data models and enums"""
    
    def test_agent_creation(self):
        """Test Agent data model creation"""
        agent = Agent(
            id="test-agent-1",
            type=AgentType.RAG_AGENT,
            name="Test RAG Agent",
            endpoint="http://localhost:8000",
            capabilities=["search", "analysis"],
            status="idle"
        )
        
        assert agent.id == "test-agent-1"
        assert agent.type == AgentType.RAG_AGENT
        assert agent.name == "Test RAG Agent"
        assert agent.capabilities == ["search", "analysis"]
        assert agent.status == "idle"
    
    def test_task_creation(self):
        """Test Task data model creation"""
        now = datetime.utcnow()
        task = Task(
            id="test-task-1",
            type="search_query",
            description="Test search task",
            input_data={"query": "test"},
            assigned_agents=[],
            status=TaskStatus.PENDING,
            created_at=now,
            priority=1
        )
        
        assert task.id == "test-task-1"
        assert task.type == "search_query"
        assert task.status == TaskStatus.PENDING
        assert task.priority == 1
        assert task.created_at == now
    
    def test_workflow_creation(self):
        """Test Workflow data model creation"""
        now = datetime.utcnow()
        workflow = Workflow(
            id="test-workflow-1",
            name="Test Workflow",
            description="Test workflow description",
            tasks=["task-1", "task-2"],
            status="running",
            created_at=now,
            user_id="user-123",
            configuration={"param": "value"}
        )
        
        assert workflow.id == "test-workflow-1"
        assert workflow.name == "Test Workflow"
        assert workflow.tasks == ["task-1", "task-2"]
        assert workflow.user_id == "user-123"
    
    def test_orchestration_request_validation(self):
        """Test OrchestrationRequest model validation"""
        request = OrchestrationRequest(
            event_data={"camera_id": "cam_001", "label": "person_detected"},
            query="test query",
            notification_channels=["email"],
            recipients=["user@example.com"]
        )
        
        assert request.event_data["camera_id"] == "cam_001"
        assert request.query == "test query"
        assert request.notification_channels == ["email"]
        assert request.recipients == ["user@example.com"]


class TestAgentManager:
    """Unit tests for AgentManager class"""
    
    @pytest.fixture
    def mock_state(self):
        """Create a mock orchestration state"""
        state = OrchestrationState()
        state.agents = {
            "agent-1": Agent(
                id="agent-1",
                type=AgentType.RAG_AGENT,
                name="RAG Agent",
                endpoint="http://rag:8000",
                capabilities=["search", "analysis"],
                status="idle"
            ),
            "agent-2": Agent(
                id="agent-2", 
                type=AgentType.PROMPT_AGENT,
                name="Prompt Agent",
                endpoint="http://prompt:8000",
                capabilities=["prompt_generation"],
                status="busy"
            )
        }
        return state
    
    @pytest.mark.asyncio
    async def test_find_suitable_agents(self, mock_state):
        """Test finding suitable agents for a task"""
        with patch('main.state', mock_state):
            agents = await AgentManager.find_suitable_agents(
                required_capabilities=["search"],
                task_type="search_query"
            )
            
            assert len(agents) == 1
            assert agents[0].id == "agent-1"
            assert agents[0].type == AgentType.RAG_AGENT
    
    @pytest.mark.asyncio
    async def test_find_no_suitable_agents(self, mock_state):
        """Test when no suitable agents are available"""
        with patch('main.state', mock_state):
            agents = await AgentManager.find_suitable_agents(
                required_capabilities=["nonexistent_capability"],
                task_type="unknown_task"
            )
            
            assert len(agents) == 0
    
    @pytest.mark.asyncio
    async def test_agent_registration(self):
        """Test agent registration"""
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
            
            assert agent_id is not None
            assert len(agent_id) > 0
            mock_redis_client.hset.assert_called_once()


class TestTaskManager:
    """Unit tests for TaskManager class"""
    
    @pytest.fixture
    def mock_state(self):
        """Create a mock orchestration state with tasks"""
        state = OrchestrationState()
        state.tasks = {}
        state.task_queue = AsyncMock()
        return state
    
    @pytest.mark.asyncio
    async def test_create_task(self, mock_state):
        """Test task creation"""
        from main import CreateTaskRequest
        
        with patch('main.state', mock_state), \
             patch('main.get_redis_client') as mock_redis:
            
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            request = CreateTaskRequest(
                type="test_task",
                description="Test task description",
                input_data={"key": "value"},
                priority=1
            )
            
            task_id = await TaskManager.create_task(request)
            
            assert task_id is not None
            assert task_id in mock_state.tasks
            
            created_task = mock_state.tasks[task_id]
            assert created_task.type == "test_task"
            assert created_task.status == TaskStatus.PENDING
            assert created_task.priority == 1
    
    @pytest.mark.asyncio
    async def test_assign_task_to_agent(self, mock_state):
        """Test assigning a task to an agent"""
        with patch('main.state', mock_state):
            # Create a test task
            task = Task(
                id="test-task",
                type="test",
                description="Test task",
                input_data={},
                assigned_agents=[],
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow()
            )
            mock_state.tasks["test-task"] = task
            mock_state.agents = {
                "test-agent": Agent(
                    id="test-agent",
                    type=AgentType.RAG_AGENT,
                    name="Test Agent",
                    endpoint="http://test:8000",
                    capabilities=[],
                    status="idle"
                )
            }
            
            await TaskManager.assign_task("test-task", "test-agent")
            
            assigned_task = mock_state.tasks["test-task"]
            assert "test-agent" in assigned_task.assigned_agents
            assert assigned_task.status == TaskStatus.RUNNING
            assert assigned_task.started_at is not None


class TestOrchestratorService:
    """Unit tests for OrchestratorService class"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator service with mocked dependencies"""
        service = OrchestratorService()
        service.redis_client = AsyncMock()
        service.http_client = AsyncMock()
        return service
    
    def test_orchestrator_initialization(self):
        """Test orchestrator service initialization"""
        service = OrchestratorService()
        assert service.redis_client is None
        assert service.http_client is None
        assert service._background_task is None
    
    @pytest.mark.asyncio
    async def test_request_response_models(self):
        """Test request and response model creation"""
        request = OrchestrationRequest(
            event_data={"camera_id": "cam_001"},
            query="test query"
        )
        
        response = OrchestrationResponse(
            status="ok",
            details={"test": "data"},
            rag_result={"result": "test"},
            rule_result={"rules": []},
            notification_result={"sent": True}
        )
        
        assert request.event_data["camera_id"] == "cam_001"
        assert response.status == "ok"
        assert response.details["test"] == "data"
    
    def test_retryable_error_detection(self, orchestrator):
        """Test retryable error detection logic"""
        from unittest.mock import Mock
        
        # Test retryable status codes
        response_503 = Mock()
        response_503.status_code = 503
        assert orchestrator._is_retryable_error(response_503) is True
        
        response_408 = Mock()
        response_408.status_code = 408
        assert orchestrator._is_retryable_error(response_408) is True
        
        # Test non-retryable status codes
        response_404 = Mock()
        response_404.status_code = 404
        assert orchestrator._is_retryable_error(response_404) is False
        
        response_200 = Mock()
        response_200.status_code = 200
        assert orchestrator._is_retryable_error(response_200) is False


class TestUtilityFunctions:
    """Unit tests for utility functions"""
    
    def test_config_validation(self):
        """Test configuration validation function"""
        # This should not raise any exceptions
        result = validate_config()
        assert result is True
    
    def test_get_config_function(self):
        """Test get_config function returns configuration"""
        config = get_config()
        assert isinstance(config, OrchestratorConfig)
        assert hasattr(config, 'service_host')
        assert hasattr(config, 'service_port')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
