"""
Comprehensive tests for input validation enhancements

Tests cover:
- Enhanced Pydantic model validation
- Security validation (injection prevention, size limits)
- Custom validators and sanitization
- Error handling and response formatting
- Edge cases and boundary conditions
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any
import json
import uuid

from pydantic import ValidationError
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Import the validation models and utilities
from validation import (
    EnhancedCreateTaskRequest,
    EnhancedCreateWorkflowRequest,
    EnhancedAgentRegistrationRequest,
    TaskQueryParams,
    AgentQueryParams,
    ValidationErrorResponse,
    ValidationErrorDetail,
    SecurityValidator,
    ValidationUtils,
    TaskType,
    TaskPriority,
    AgentType,
    WorkflowStatus
)

class TestValidationUtils:
    """Test validation utility functions"""
    
    def test_validate_dict_depth_valid(self):
        """Test dict depth validation with valid nested dict"""
        valid_dict = {"level1": {"level2": {"level3": "value"}}}
        assert ValidationUtils.validate_dict_depth(valid_dict, 5)
    
    def test_validate_dict_depth_too_deep(self):
        """Test dict depth validation with overly nested dict"""
        deep_dict = {"l1": {"l2": {"l3": {"l4": {"l5": {"l6": {"l7": "value"}}}}}}}
        assert not ValidationUtils.validate_dict_depth(deep_dict, 5)
    
    def test_validate_list_size_valid(self):
        """Test list size validation with valid list"""
        valid_list = list(range(50))
        assert ValidationUtils.validate_list_size(valid_list, 100)
    
    def test_validate_list_size_too_large(self):
        """Test list size validation with oversized list"""
        large_list = list(range(150))
        assert not ValidationUtils.validate_list_size(large_list, 100)
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization"""
        clean_string = "Hello World!"
        result = ValidationUtils.sanitize_string(clean_string)
        assert result == clean_string
    
    def test_sanitize_string_script_removal(self):
        """Test script tag removal"""
        malicious_string = "Hello <script>alert('xss')</script> World"
        result = ValidationUtils.sanitize_string(malicious_string)
        assert "<script>" not in result
        assert "alert" not in result
    
    def test_sanitize_string_sql_injection(self):
        """Test SQL injection pattern removal"""
        sql_injection = "'; DROP TABLE users; --"
        result = ValidationUtils.sanitize_string(sql_injection)
        assert "drop table" not in result.lower()
    
    def test_validate_url_valid(self):
        """Test URL validation with valid URLs"""
        valid_urls = [
            "https://api.example.com/endpoint",
            "http://localhost:8080/api",
            "https://192.168.1.100:3000/health"
        ]
        for url in valid_urls:
            assert ValidationUtils.validate_url(url)
    
    def test_validate_url_invalid(self):
        """Test URL validation with invalid URLs"""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "javascript:alert('xss')",
            ""
        ]
        for url in invalid_urls:
            assert not ValidationUtils.validate_url(url)
    
    def test_validate_uuid_valid(self):
        """Test UUID validation with valid UUIDs"""
        valid_uuid = str(uuid.uuid4())
        assert ValidationUtils.validate_uuid(valid_uuid)
    
    def test_validate_uuid_invalid(self):
        """Test UUID validation with invalid UUIDs"""
        invalid_uuids = [
            "not-a-uuid",
            "12345678-1234-1234-1234-12345678901",  # Too short
            "12345678-1234-1234-1234-123456789012g",  # Invalid character
            ""
        ]
        for invalid_uuid in invalid_uuids:
            assert not ValidationUtils.validate_uuid(invalid_uuid)

class TestSecurityValidator:
    """Test security validation functions"""
    
    def test_validate_input_size_valid(self):
        """Test input size validation with valid data"""
        small_data = {"key": "value"}
        assert SecurityValidator.validate_input_size(small_data, 1000)
    
    def test_validate_input_size_too_large(self):
        """Test input size validation with oversized data"""
        large_data = {"key": "x" * 1000}
        assert not SecurityValidator.validate_input_size(large_data, 500)
    
    def test_validate_no_suspicious_patterns_clean(self):
        """Test suspicious pattern detection with clean text"""
        clean_text = "This is a normal description of a task"
        assert SecurityValidator.validate_no_suspicious_patterns(clean_text)
    
    def test_validate_no_suspicious_patterns_script(self):
        """Test suspicious pattern detection with script tags"""
        malicious_text = "Task <script>alert('xss')</script> description"
        assert not SecurityValidator.validate_no_suspicious_patterns(malicious_text)
    
    def test_validate_no_suspicious_patterns_javascript(self):
        """Test suspicious pattern detection with javascript protocol"""
        malicious_text = "javascript:alert('xss')"
        assert not SecurityValidator.validate_no_suspicious_patterns(malicious_text)
    
    def test_validate_no_suspicious_patterns_sql_injection(self):
        """Test suspicious pattern detection with SQL injection"""
        malicious_text = "'; UNION SELECT * FROM users; --"
        assert not SecurityValidator.validate_no_suspicious_patterns(malicious_text)
    
    def test_validate_rate_limit_compliance_within_limit(self):
        """Test rate limit validation within allowed limits"""
        assert SecurityValidator.validate_rate_limit_compliance(50, 60, 100)
    
    def test_validate_rate_limit_compliance_exceeded(self):
        """Test rate limit validation when limit exceeded"""
        assert not SecurityValidator.validate_rate_limit_compliance(150, 60, 100)

class TestEnhancedCreateTaskRequest:
    """Test enhanced task creation request validation"""
    
    def test_valid_task_request(self):
        """Test valid task request creation"""
        request_data = {
            "type": "analysis",
            "name": "Test Analysis Task",
            "description": "This is a test analysis task",
            "input_data": {"param1": "value1", "param2": 42},
            "priority": 2,
            "required_capabilities": ["analysis", "detection"],
            "timeout": 300.0,
            "max_retries": 3,
            "tags": ["test", "analysis"]
        }
        
        request = EnhancedCreateTaskRequest(**request_data)
        assert request.type == TaskType.ANALYSIS
        assert request.name == "Test Analysis Task"
        assert request.priority == TaskPriority.NORMAL
        assert len(request.required_capabilities) == 2
        assert len(request.tags) == 2
    
    def test_invalid_task_type(self):
        """Test task request with invalid type"""
        request_data = {
            "type": "invalid_type",
            "name": "Test Task",
            "description": "Test description"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EnhancedCreateTaskRequest(**request_data)
        
        assert "type" in str(exc_info.value)
    
    def test_name_too_short(self):
        """Test task request with name too short"""
        request_data = {
            "type": "analysis",
            "name": "AB",  # Too short
            "description": "Test description"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EnhancedCreateTaskRequest(**request_data)
        
        assert "name" in str(exc_info.value)
    
    def test_description_too_long(self):
        """Test task request with description too long"""
        request_data = {
            "type": "analysis",
            "name": "Test Task",
            "description": "x" * 6000  # Too long
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EnhancedCreateTaskRequest(**request_data)
        
        assert "description" in str(exc_info.value)
    
    def test_too_many_capabilities(self):
        """Test task request with too many capabilities"""
        request_data = {
            "type": "analysis",
            "name": "Test Task",
            "description": "Test description",
            "required_capabilities": [f"capability_{i}" for i in range(60)]  # Too many
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EnhancedCreateTaskRequest(**request_data)
        
        assert "capabilities" in str(exc_info.value)
    
    def test_invalid_workflow_id(self):
        """Test task request with invalid workflow ID format"""
        request_data = {            "type": "analysis",
            "name": "Test Task",
            "description": "Test description",
            "workflow_id": "not-a-uuid"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EnhancedCreateTaskRequest(**request_data)
        
        assert "workflow_id" in str(exc_info.value)
    
    def test_timeout_validation(self):
        """Test timeout parameter validation"""
        # Valid timeout
        request_data = {
            "type": "analysis",
            "name": "Test Task",
            "description": "Test description",
            "timeout": 600.0
        }
        request = EnhancedCreateTaskRequest(**request_data)
        assert request.timeout == 600.0
        
        # Invalid timeout (too large)
        request_data["timeout"] = 90000.0  # More than 24 hours
        with pytest.raises(ValidationError):
            EnhancedCreateTaskRequest(**request_data)
    
    def test_input_data_validation(self):
        """Test input data validation"""
        # Valid input data
        request_data = {
            "type": "analysis",
            "name": "Test Task",
            "description": "Test description",
            "input_data": {"key": "value", "number": 42}
        }
        request = EnhancedCreateTaskRequest(**request_data)
        assert request.input_data == {"key": "value", "number": 42}
        
        # Overly nested input data (reduce depth to trigger validation)
        deep_data = {"l1": {"l2": {"l3": {"l4": {"l5": {"l6": {"l7": {"l8": {"l9": {"l10": {"l11": "deep"}}}}}}}}}}}
        request_data["input_data"] = deep_data
        with pytest.raises(ValidationError):
            EnhancedCreateTaskRequest(**request_data)

class TestEnhancedAgentRegistrationRequest:
    """Test enhanced agent registration request validation"""
    
    def test_valid_agent_registration(self):
        """Test valid agent registration request"""
        request_data = {
            "type": "detector",
            "name": "Test Agent",
            "endpoint": "https://api.example.com/agent",
            "capabilities": ["detection", "analysis"],
            "version": "1.0.0",
            "metadata": {"model": "yolo", "accuracy": 0.95},
            "health_check_interval": 60,
            "max_concurrent_tasks": 5
        }
        
        request = EnhancedAgentRegistrationRequest(**request_data)
        assert request.type == AgentType.DETECTOR
        assert request.name == "Test Agent"
        assert request.endpoint == "https://api.example.com/agent"
        assert request.version == "1.0.0"
    
    def test_invalid_endpoint_url(self):
        """Test agent registration with invalid endpoint URL"""
        request_data = {
            "type": "detector",
            "name": "Test Agent",
            "endpoint": "not-a-url",
            "capabilities": ["detection"]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EnhancedAgentRegistrationRequest(**request_data)
        
        assert "endpoint" in str(exc_info.value)
    
    def test_invalid_version_format(self):
        """Test agent registration with invalid version format"""
        request_data = {
            "type": "detector",
            "name": "Test Agent",
            "endpoint": "https://api.example.com/agent",
            "capabilities": ["detection"],
            "version": "not-semantic-version"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EnhancedAgentRegistrationRequest(**request_data)
        
        assert "version" in str(exc_info.value)
    
    def test_health_check_interval_bounds(self):
        """Test health check interval validation bounds"""
        base_data = {
            "type": "detector",
            "name": "Test Agent",
            "endpoint": "https://api.example.com/agent",
            "capabilities": ["detection"]
        }
        
        # Valid interval
        request_data = {**base_data, "health_check_interval": 60}
        request = EnhancedAgentRegistrationRequest(**request_data)
        assert request.health_check_interval == 60
        
        # Too low
        request_data = {**base_data, "health_check_interval": 5}
        with pytest.raises(ValidationError):
            EnhancedAgentRegistrationRequest(**request_data)
        
        # Too high
        request_data = {**base_data, "health_check_interval": 4000}
        with pytest.raises(ValidationError):
            EnhancedAgentRegistrationRequest(**request_data)

class TestQueryParams:
    """Test query parameter validation models"""
    
    def test_task_query_params_valid(self):
        """Test valid task query parameters"""
        params = TaskQueryParams(
            status=WorkflowStatus.RUNNING,
            workflow_id=str(uuid.uuid4()),
            agent_id=str(uuid.uuid4()),
            limit=50,
            offset=10,
            sort_by="created_at",
            sort_order="desc"
        )
        
        assert params.status == WorkflowStatus.RUNNING
        assert params.limit == 50
        assert params.offset == 10
        assert params.sort_by == "created_at"
        assert params.sort_order == "desc"
    
    def test_task_query_params_invalid_sort_by(self):
        """Test task query parameters with invalid sort field"""
        with pytest.raises(ValidationError) as exc_info:
            TaskQueryParams(sort_by="invalid_field")
        
        assert "sort_by" in str(exc_info.value)
    
    def test_task_query_params_invalid_sort_order(self):
        """Test task query parameters with invalid sort order"""
        with pytest.raises(ValidationError) as exc_info:
            TaskQueryParams(sort_order="invalid_order")
        
        assert "sort_order" in str(exc_info.value)
    
    def test_task_query_params_limit_bounds(self):
        """Test task query parameters limit validation"""
        # Valid limit
        params = TaskQueryParams(limit=500)
        assert params.limit == 500
        
        # Too high
        with pytest.raises(ValidationError):
            TaskQueryParams(limit=2000)
        
        # Too low
        with pytest.raises(ValidationError):
            TaskQueryParams(limit=0)
    
    def test_agent_query_params_valid(self):
        """Test valid agent query parameters"""
        params = AgentQueryParams(
            type=AgentType.DETECTOR,
            status="active",
            capability="detection",
            limit=25,
            offset=5
        )
        
        assert params.type == AgentType.DETECTOR
        assert params.status == "active"
        assert params.capability == "detection"
        assert params.limit == 25
        assert params.offset == 5

class TestValidationErrorResponse:
    """Test validation error response models"""
    
    def test_validation_error_detail(self):
        """Test validation error detail model"""
        detail = ValidationErrorDetail(
            field="name",
            message="Field is required",
            invalid_value="",
            constraint="required"
        )
        
        assert detail.field == "name"
        assert detail.message == "Field is required"
        assert detail.invalid_value == ""
        assert detail.constraint == "required"
    
    def test_validation_error_response(self):
        """Test validation error response model"""
        details = [
            ValidationErrorDetail(
                field="name",
                message="Field is required",
                invalid_value="",
                constraint="required"
            ),
            ValidationErrorDetail(
                field="type",
                message="Invalid type",
                invalid_value="invalid",
                constraint="enum"
            )
        ]
        
        response = ValidationErrorResponse(
            message="Validation failed",
            details=details,
            request_id="test-request-id"
        )
        
        assert response.error == "Validation Error"
        assert response.message == "Validation failed"
        assert len(response.details) == 2
        assert response.request_id == "test-request-id"
        assert response.timestamp is not None

class TestEnhancedWorkflowRequest:
    """Test enhanced workflow request validation"""
    
    def test_valid_workflow_request(self):
        """Test valid workflow creation request"""
        task_request = {
            "type": "analysis",
            "name": "Test Task",
            "description": "Test task description",
            "input_data": {"param": "value"}
        }
        
        request_data = {
            "name": "Test Workflow",
            "description": "Test workflow description",
            "tasks": [task_request],
            "user_id": "test-user-123",
            "configuration": {"timeout": 600, "max_retries": 3},
            "schedule": "0 0 * * *",  # Daily at midnight
            "dependencies": [],
            "environment": {"ENV_VAR": "value"}
        }
        
        request = EnhancedCreateWorkflowRequest(**request_data)
        assert request.name == "Test Workflow"
        assert len(request.tasks) == 1
        assert request.user_id == "test-user-123"
        assert request.configuration["timeout"] == 600
    
    def test_invalid_schedule_format(self):
        """Test workflow request with invalid schedule format"""
        task_request = {
            "type": "analysis",
            "name": "Test Task",
            "description": "Test task description"
        }
        
        request_data = {
            "name": "Test Workflow",
            "description": "Test workflow description",
            "tasks": [task_request],
            "user_id": "test-user",
            "schedule": "invalid cron"  # Invalid cron format
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EnhancedCreateWorkflowRequest(**request_data)
        
        assert "schedule" in str(exc_info.value)
    
    def test_too_many_tasks(self):
        """Test workflow request with too many tasks"""
        tasks = []
        for i in range(110):  # More than MAX_TASKS_PER_WORKFLOW (100)
            tasks.append({
                "type": "analysis",
                "name": f"Task {i}",
                "description": f"Task {i} description"
            })
        
        request_data = {
            "name": "Test Workflow",
            "description": "Test workflow description",
            "tasks": tasks,
            "user_id": "test-user"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EnhancedCreateWorkflowRequest(**request_data)
        
        assert "tasks" in str(exc_info.value)

# Integration tests would go here to test the actual FastAPI endpoints
# These would require setting up the test client and mocking dependencies

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
