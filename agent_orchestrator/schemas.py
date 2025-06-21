"""
Schema models for Agent Orchestrator Service.

This module defines Pydantic models for request/response schemas used
in the authenticated endpoints. These models provide data validation,
serialization, and API documentation.

Author: Agent Orchestrator Team
Version: 1.0.0
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Generic, TypeVar
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# Enums
class AgentStatus(str, Enum):
    """Agent status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Task priority enumeration."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


# Request Models
class AgentRegistrationRequest(BaseModel):
    """Request model for agent registration."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Security Agent 1",
                "agent_type": "security_monitor",
                "capabilities": ["motion_detection", "face_recognition", "alert_generation"],
                "config": {
                    "camera_ids": ["cam_001", "cam_002"],
                    "sensitivity": 0.8,
                    "notification_enabled": True
                },
                "metadata": {
                    "location": "main_entrance",
                    "installation_date": "2024-01-15"
                }
            }
        }
    )
    
    name: str = Field(..., description="Human-readable name for the agent")
    agent_type: str = Field(..., description="Type of agent (e.g., security_monitor, object_detector)")
    capabilities: List[str] = Field(default_factory=list, description="List of agent capabilities")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AgentUpdateRequest(BaseModel):
    """Request model for agent updates."""
    name: Optional[str] = Field(None, description="Updated name")
    status: Optional[AgentStatus] = Field(None, description="Updated status")
    capabilities: Optional[List[str]] = Field(None, description="Updated capabilities")
    config: Optional[Dict[str, Any]] = Field(None, description="Updated configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class TaskCreateRequest(BaseModel):
    """Request model for task creation."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_type": "security_analysis",
                "priority": 3,
                "config": {
                    "camera_id": "cam_001",
                    "time_range": {
                        "start": "2024-01-15T10:00:00Z",
                        "end": "2024-01-15T11:00:00Z"
                    },
                    "analysis_type": "motion_detection"
                },
                "assigned_agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "metadata": {
                    "priority_reason": "security_alert",
                    "alert_id": "alert_001"
                }
            }
        }
    )
    
    task_type: str = Field(..., description="Type of task to execute")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Task priority level")
    config: Dict[str, Any] = Field(default_factory=dict, description="Task configuration")
    assigned_agent_id: Optional[UUID] = Field(None, description="ID of agent to assign task to")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional task metadata")


class WorkflowCreateRequest(BaseModel):
    """Request model for workflow creation."""
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    steps: List[Dict[str, Any]] = Field(..., description="Workflow steps configuration")
    config: Dict[str, Any] = Field(default_factory=dict, description="Workflow configuration")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional workflow metadata")


# Response Models
class AgentResponse(BaseModel):
    """Response model for agent information."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent name")
    agent_type: str = Field(..., description="Agent type")
    capabilities: List[str] = Field(..., description="Agent capabilities")
    status: AgentStatus = Field(..., description="Current agent status")
    config: Dict[str, Any] = Field(..., description="Agent configuration")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat timestamp")


class TaskResponse(BaseModel):
    """Response model for task information."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="Unique task identifier")
    task_type: str = Field(..., description="Task type")
    status: TaskStatus = Field(..., description="Current task status")
    priority: TaskPriority = Field(..., description="Task priority")
    config: Dict[str, Any] = Field(..., description="Task configuration")
    assigned_agent_id: Optional[UUID] = Field(None, description="Assigned agent ID")
    result: Optional[Dict[str, Any]] = Field(None, description="Task execution result")
    error_message: Optional[str] = Field(None, description="Error message if task failed")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class WorkflowResponse(BaseModel):
    """Response model for workflow information."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    status: str = Field(..., description="Current workflow status")
    steps: List[Dict[str, Any]] = Field(..., description="Workflow steps")
    config: Dict[str, Any] = Field(..., description="Workflow configuration")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    authenticated: bool = Field(False, description="Whether request was authenticated")
    api_key_name: Optional[str] = Field(None, description="Name of the API key used")
    permissions: Optional[List[str]] = Field(None, description="Permissions of the API key")
    error: Optional[str] = Field(None, description="Error message if unhealthy")


# Generic pagination model
T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model."""
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum number of items returned")
    has_next: bool = Field(..., description="Whether there are more items")
    has_previous: bool = Field(..., description="Whether there are previous items")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Calculate pagination flags
        self.has_next = (self.skip + self.limit) < self.total
        self.has_previous = self.skip > 0


# Error response models
class ErrorDetail(BaseModel):
    """Error detail model."""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")


# API Key management models
class APIKeyCreateRequest(BaseModel):
    """Request model for API key creation."""
    name: str = Field(..., description="Human-readable name for the API key")
    permissions: List[str] = Field(default_factory=lambda: ["agent:read"], description="List of permissions")
    expires_in_days: Optional[int] = Field(30, description="Days until expiration (None for no expiration)")
    rate_limit: int = Field(100, description="Requests per minute allowed")
    allowed_endpoints: List[str] = Field(
        default_factory=lambda: ["/api/v1/agents", "/api/v1/tasks", "/api/v1/health"],
        description="Allowed endpoint patterns"
    )


class APIKeyResponse(BaseModel):
    """Response model for API key information."""
    key_id: str = Field(..., description="Unique key identifier")
    name: str = Field(..., description="Key name")
    permissions: List[str] = Field(..., description="Key permissions")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    is_active: bool = Field(..., description="Whether the key is active")
    rate_limit: int = Field(..., description="Requests per minute allowed")
    allowed_endpoints: List[str] = Field(..., description="Allowed endpoint patterns")


class APIKeyCreatedResponse(BaseModel):
    """Response model for newly created API key."""
    api_key: str = Field(..., description="The generated API key (only shown once)")
    key_info: APIKeyResponse = Field(..., description="API key information")
    warning: str = Field(
        default="Store this API key securely. It will not be shown again.",
        description="Security warning"
    )
