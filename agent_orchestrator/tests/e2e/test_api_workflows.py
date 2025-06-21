"""
End-to-End Tests for Agent Orchestrator Service

This module contains end-to-end tests that test the complete system
including HTTP API endpoints, real service interactions, and
user workflows from start to finish.

Test Categories:
- API endpoint tests
- Complete user workflow tests
- Performance and load tests
- Real service integration tests (when available)
"""

import pytest
import asyncio
import requests
import json
import time
from unittest.mock import patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Import FastAPI test client
from fastapi.testclient import TestClient
from main import app
from orchestrator import OrchestrationRequest, OrchestrationResponse


class TestAPIEndpoints:
    """End-to-end tests for HTTP API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client for the FastAPI application"""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_system_status_endpoint(self, client):
        """Test system status endpoint"""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "agents" in data
        assert "tasks" in data
        assert "workflows" in data
        
        # Verify structure
        assert "total" in data["agents"]
        assert "active" in data["agents"]
        assert "idle" in data["agents"]
    
    def test_agent_registration_endpoint(self, client):
        """Test agent registration API endpoint"""
        agent_data = {
            "type": "rag_agent",
            "name": "Test RAG Agent",
            "endpoint": "http://test-rag:8000",
            "capabilities": ["search", "analysis"]
        }
        
        with patch('main.AgentManager.register_agent') as mock_register:
            mock_register.return_value = "test-agent-id"
            
            response = client.post("/api/v1/agents/register", json=agent_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["agent_id"] == "test-agent-id"
            assert data["status"] == "registered"
    
    def test_list_agents_endpoint(self, client):
        """Test listing agents endpoint"""
        with patch('main.state') as mock_state:
            # Mock agent data
            mock_agent = {
                "id": "agent-1",
                "type": "rag_agent",
                "name": "Test Agent",
                "endpoint": "http://test:8000",
                "capabilities": ["search"],
                "status": "idle",
                "last_seen": datetime.utcnow(),
                "current_task": None,
                "performance_metrics": {}
            }
            mock_state.agents = {"agent-1": type('Agent', (), mock_agent)()}
            
            response = client.get("/api/v1/agents")
            assert response.status_code == 200
            
            data = response.json()
            assert "agents" in data
            assert len(data["agents"]) == 1
    
    def test_task_creation_endpoint(self, client):
        """Test task creation API endpoint"""
        task_data = {
            "type": "search_query",
            "description": "Test search task",
            "input_data": {"query": "test query"},
            "priority": 1,
            "required_capabilities": ["search"]
        }
        
        with patch('main.TaskManager.create_task') as mock_create:
            mock_create.return_value = "test-task-id"
            
            response = client.post("/api/v1/tasks", json=task_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["task_id"] == "test-task-id"
            assert data["status"] == "created"
    
    def test_get_task_endpoint(self, client):
        """Test get task details endpoint"""
        with patch('main.state') as mock_state:
            from main import Task, TaskStatus
            
            # Mock task data
            task = Task(
                id="test-task",
                type="search",
                description="Test task",
                input_data={"query": "test"},
                assigned_agents=["agent-1"],
                status=TaskStatus.RUNNING,
                created_at=datetime.utcnow(),
                started_at=datetime.utcnow()
            )
            mock_state.tasks = {"test-task": task}
            
            response = client.get("/api/v1/tasks/test-task")
            assert response.status_code == 200
            
            data = response.json()
            assert data["id"] == "test-task"
            assert data["type"] == "search"
            assert data["status"] == "running"
    
    def test_workflow_creation_endpoint(self, client):
        """Test workflow creation API endpoint"""
        workflow_data = {
            "name": "Test Workflow",
            "description": "End-to-end test workflow",
            "user_id": "test-user",
            "tasks": [
                {
                    "type": "rag_query",
                    "description": "RAG analysis",
                    "input_data": {"query": "test"},
                    "priority": 1
                },
                {
                    "type": "notification",
                    "description": "Send notification",
                    "input_data": {"message": "complete"},
                    "priority": 2
                }
            ]
        }
        
        with patch('main.WorkflowManager.create_workflow') as mock_create:
            mock_create.return_value = "test-workflow-id"
            
            response = client.post("/api/v1/workflows", json=workflow_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["workflow_id"] == "test-workflow-id"
            assert data["status"] == "created"


class TestOrchestrationEndpoint:
    """End-to-end tests for the main orchestration endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client for the FastAPI application"""
        return TestClient(app)
    
    def test_successful_orchestration_endpoint(self, client):
        """Test successful orchestration via API endpoint"""
        request_data = {
            "event_data": {
                "camera_id": "cam_001",
                "timestamp": "2025-06-13T10:30:00Z",
                "label": "person_detected",
                "bbox": {"x": 100, "y": 150, "width": 50, "height": 100}
            },
            "query": "Person detected in restricted area",
            "notification_channels": ["email"],
            "recipients": ["security@company.com"]
        }
        
        with patch('main.orchestrator_service') as mock_service:
            # Mock successful orchestration
            mock_result = OrchestrationResponse(
                status="ok",
                details={
                    "rag_success": True,
                    "rule_success": True,
                    "notification_success": True,
                    "timestamp": datetime.utcnow().isoformat()
                },
                rag_result={
                    "linked_explanation": "Person detected in temporal context",
                    "retrieved_context": []
                },
                rule_result={
                    "triggered_actions": [
                        {
                            "type": "send_notification",
                            "rule_id": "person_alert",
                            "parameters": {"message": "Person detected", "severity": "high"}
                        }
                    ]
                },
                notification_result={
                    "status": "sent",
                    "message_id": "msg_123"
                }
            )
            mock_service.orchestrate = AsyncMock(return_value=mock_result)
            
            response = client.post("/api/v1/orchestrate", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["rag_result"] is not None
            assert data["rule_result"] is not None
            assert data["notification_result"] is not None
    
    def test_orchestration_with_notifier_failure(self, client):
        """Test orchestration endpoint when notifier fails (should return 202)"""
        request_data = {
            "event_data": {
                "camera_id": "cam_001",
                "timestamp": "2025-06-13T10:30:00Z",
                "label": "person_detected"
            }
        }
        
        with patch('main.orchestrator_service') as mock_service:
            # Mock partial success with notifier failure
            mock_result = OrchestrationResponse(
                status="partial_success",
                details={
                    "rag_success": True,
                    "rule_success": True,
                    "notification_success": False,
                    "notification_queued_for_retry": True,
                    "timestamp": datetime.utcnow().isoformat()
                },
                rag_result={"linked_explanation": "Test", "retrieved_context": []},
                rule_result={"triggered_actions": []},
                notification_result={"status": "notifier_unreachable"}
            )
            mock_service.orchestrate = AsyncMock(return_value=mock_result)
            
            response = client.post("/api/v1/orchestrate", json=request_data)
            
            assert response.status_code == 202  # Accepted but will retry
    
    def test_orchestration_with_rag_failure(self, client):
        """Test orchestration endpoint when RAG fails (should return 503)"""
        request_data = {
            "event_data": {
                "camera_id": "cam_001",
                "timestamp": "2025-06-13T10:30:00Z",
                "label": "person_detected"
            }
        }
        
        with patch('main.orchestrator_service') as mock_service:
            # Mock fallback due to RAG failure
            mock_result = OrchestrationResponse(
                status="fallback",
                details={
                    "rag_success": False,
                    "rag_fallback_used": True,
                    "timestamp": datetime.utcnow().isoformat()
                },
                rag_result={
                    "linked_explanation": "We could not retrieve context due to a temporary service outage. Please try again shortly.",
                    "retrieved_context": []
                },
                rule_result=None,
                notification_result=None
            )
            mock_service.orchestrate = AsyncMock(return_value=mock_result)
            
            response = client.post("/api/v1/orchestrate", json=request_data)
            
            assert response.status_code == 503  # Service Unavailable


class TestCompleteUserWorkflows:
    """End-to-end tests for complete user workflows"""
    
    @pytest.fixture
    def client(self):
        """Create test client for the FastAPI application"""
        return TestClient(app)
    
    def test_agent_registration_to_task_execution_workflow(self, client):
        """Test complete workflow from agent registration to task execution"""
        # Step 1: Register an agent
        agent_data = {
            "type": "rag_agent",
            "name": "E2E Test Agent",
            "endpoint": "http://e2e-test:8000",
            "capabilities": ["search", "analysis"]
        }
        
        with patch('main.AgentManager.register_agent') as mock_register, \
             patch('main.TaskManager.create_task') as mock_create_task, \
             patch('main.state') as mock_state:
            
            mock_register.return_value = "e2e-agent-id"
            mock_create_task.return_value = "e2e-task-id"
            
            # Register agent
            response = client.post("/api/v1/agents/register", json=agent_data)
            assert response.status_code == 200
            agent_id = response.json()["agent_id"]
            
            # Step 2: Create a task
            task_data = {
                "type": "search_analysis",
                "description": "E2E test task",
                "input_data": {"query": "end-to-end test"},
                "priority": 1,
                "required_capabilities": ["search", "analysis"]
            }
            
            response = client.post("/api/v1/tasks", json=task_data)
            assert response.status_code == 200
            task_id = response.json()["task_id"]
            
            # Step 3: Verify task was created
            from main import Task, TaskStatus
            mock_task = Task(
                id=task_id,
                type="search_analysis",
                description="E2E test task",
                input_data={"query": "end-to-end test"},
                assigned_agents=[],
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow()
            )
            mock_state.tasks = {task_id: mock_task}
            
            response = client.get(f"/api/v1/tasks/{task_id}")
            assert response.status_code == 200
            
            data = response.json()
            assert data["id"] == task_id
            assert data["type"] == "search_analysis"
            assert data["status"] == "pending"
    
    def test_workflow_creation_and_monitoring_workflow(self, client):
        """Test complete workflow creation and monitoring workflow"""
        # Step 1: Create a multi-task workflow
        workflow_data = {
            "name": "E2E Test Workflow",
            "description": "End-to-end test workflow",
            "user_id": "e2e-test-user",
            "tasks": [
                {
                    "type": "data_analysis",
                    "description": "Analyze input data",
                    "input_data": {"data": "test_data"},
                    "priority": 1
                },
                {
                    "type": "report_generation", 
                    "description": "Generate analysis report",
                    "input_data": {"format": "json"},
                    "priority": 2
                },
                {
                    "type": "notification",
                    "description": "Send completion notification",
                    "input_data": {"recipients": ["user@example.com"]},
                    "priority": 3
                }
            ]
        }
        
        with patch('main.WorkflowManager.create_workflow') as mock_create:
            mock_create.return_value = "e2e-workflow-id"
            
            # Create workflow
            response = client.post("/api/v1/workflows", json=workflow_data)
            assert response.status_code == 200
            
            workflow_id = response.json()["workflow_id"]
            
            # Step 2: Monitor workflow status
            with patch('main.state') as mock_state:
                from main import Workflow
                
                mock_workflow = Workflow(
                    id=workflow_id,
                    name="E2E Test Workflow",
                    description="End-to-end test workflow",
                    tasks=["task-1", "task-2", "task-3"],
                    status="running",
                    created_at=datetime.utcnow(),
                    user_id="e2e-test-user",
                    configuration={}
                )
                mock_state.workflows = {workflow_id: mock_workflow}
                
                response = client.get(f"/api/v1/workflows/{workflow_id}")
                assert response.status_code == 200
                
                data = response.json()
                assert data["id"] == workflow_id
                assert data["name"] == "E2E Test Workflow"
                assert data["user_id"] == "e2e-test-user"
                assert len(data["tasks"]) == 3


class TestPerformanceAndLoad:
    """End-to-end performance and load tests"""
    
    @pytest.fixture
    def client(self):
        """Create test client for the FastAPI application"""
        return TestClient(app)
    
    def test_concurrent_orchestration_requests(self, client):
        """Test handling of concurrent orchestration requests"""
        request_data = {
            "event_data": {
                "camera_id": "cam_001",
                "timestamp": "2025-06-13T10:30:00Z",
                "label": "person_detected"
            },
            "notification_channels": ["email"],
            "recipients": ["test@example.com"]
        }
        
        def make_request():
            """Make a single orchestration request"""
            with patch('main.orchestrator_service') as mock_service:
                mock_result = OrchestrationResponse(
                    status="ok",
                    details={"timestamp": datetime.utcnow().isoformat()},
                    rag_result={"linked_explanation": "Test", "retrieved_context": []},
                    rule_result={"triggered_actions": []},
                    notification_result={"status": "sent"}
                )
                mock_service.orchestrate = AsyncMock(return_value=mock_result)
                
                response = client.post("/api/v1/orchestrate", json=request_data)
                return response.status_code
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in futures]
        
        # Verify all requests succeeded
        assert all(status_code == 200 for status_code in results)
    
    def test_api_response_times(self, client):
        """Test API response times for various endpoints"""
        endpoints = [
            ("GET", "/health"),
            ("GET", "/api/v1/status"),
            ("GET", "/api/v1/agents"),
            ("GET", "/api/v1/tasks"),
            ("GET", "/api/v1/workflows")
        ]
        
        for method, endpoint in endpoints:
            start_time = time.time()
            
            if method == "GET":
                response = client.get(endpoint)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Verify response time is reasonable (under 1 second for mocked responses)
            assert response_time < 1.0, f"Endpoint {endpoint} took {response_time:.2f} seconds"
            assert response.status_code in [200, 404]  # Some endpoints might return 404 with empty state


class TestRealServiceIntegration:
    """End-to-end tests with real services (when available)"""
    
    @pytest.mark.skipif(True, reason="Requires real services to be running")
    def test_real_orchestration_with_live_services(self):
        """Test orchestration with actual running services"""
        # This test would only run when real services are available
        # It's marked to skip by default
        
        request_data = {
            "event_data": {
                "camera_id": "cam_001",
                "timestamp": "2025-06-13T10:30:00Z",
                "label": "person_detected",
                "bbox": {"x": 100, "y": 150, "width": 50, "height": 100}
            },
            "query": "Person detected in restricted area",
            "notification_channels": ["email"],
            "recipients": ["test@example.com"]
        }
        
        try:
            response = requests.post(
                "http://localhost:8006/api/v1/orchestrate",
                json=request_data,
                timeout=30
            )
            
            assert response.status_code in [200, 202, 503]
            
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "details" in data
                
        except requests.exceptions.ConnectionError:
            pytest.skip("Agent orchestrator service not available")
    
    @pytest.mark.skipif(True, reason="Requires real services to be running") 
    def test_health_check_with_dependencies(self):
        """Test health check with real service dependencies"""
        try:
            response = requests.get("http://localhost:8006/health", timeout=5)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Agent orchestrator service not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
