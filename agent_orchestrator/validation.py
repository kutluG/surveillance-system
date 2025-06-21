"""
Enhanced Input Validation for Agent Orchestrator Service

This module provides enhanced validation for request payloads, improving error handling 
and security through strict data validation, sanitization, and business rule enforcement.

Features:
- Pydantic model enhancements with detailed constraints
- Custom validators for business logic
- Input sanitization and normalization
- Security validation (injection prevention, size limits)
- Comprehensive error messages
- Request rate limiting validation
- Data format validation (URLs, UUIDs, etc.)
"""

import re
import json
from typing import Any, Dict, List, Optional, Union, Callable, Annotated
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)

# Constants for validation
MAX_STRING_LENGTH = 10000
MAX_DESCRIPTION_LENGTH = 5000
MAX_NAME_LENGTH = 255
MAX_CAPABILITIES = 50
MAX_TASKS_PER_WORKFLOW = 100
MAX_DICT_DEPTH = 10
MAX_LIST_SIZE = 1000

# Regex patterns for validation
URL_PATTERN = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\s\.\,\(\)]+$')
UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

# Enhanced Enums with detailed documentation
class TaskType(str, Enum):
    """
    Valid task types supported by the surveillance system
    
    Each task type represents a specific category of AI processing:
    - ANALYSIS: General data analysis and pattern recognition
    - DETECTION: Object, person, or event detection tasks
    - CLASSIFICATION: Content classification and categorization
    - TRACKING: Object or person tracking across frames/time
    - ALERT: Alert generation and notification tasks
    - REPORT: Report generation and data summarization
    - CUSTOM: Custom task types for specialized processing
    """
    ANALYSIS = "analysis"
    DETECTION = "detection"
    CLASSIFICATION = "classification"
    TRACKING = "tracking"
    ALERT = "alert"
    REPORT = "report"
    CUSTOM = "custom"

class TaskPriority(int, Enum):
    """
    Task priority levels for queue management and resource allocation
    
    Priority levels affect task scheduling and resource allocation:
    - LOW (1): Background tasks, non-urgent processing
    - NORMAL (2): Standard processing tasks (default)
    - HIGH (3): Important tasks requiring faster processing
    - CRITICAL (4): High-priority tasks for immediate processing
    - EMERGENCY (5): Emergency tasks with highest priority
    """
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

class AgentType(str, Enum):
    """
    Valid agent types that can be registered in the system
    
    Agent types define the capabilities and processing specialization:
    - DETECTOR: Specialized in object/event detection
    - ANALYZER: General analysis and data processing
    - CLASSIFIER: Content classification and categorization
    - TRACKER: Object/person tracking capabilities  
    - NOTIFIER: Alert and notification dispatch
    - COORDINATOR: Task coordination and workflow management
    - CUSTOM: Custom agent types for specialized functions
    """
    DETECTOR = "detector"
    ANALYZER = "analyzer"
    CLASSIFIER = "classifier"
    TRACKER = "tracker"
    NOTIFIER = "notifier"
    COORDINATOR = "coordinator"
    CUSTOM = "custom"

class WorkflowStatus(str, Enum):
    """
    Workflow execution status values
    
    Status progression through workflow lifecycle:
    - PENDING: Workflow created but not yet started
    - RUNNING: Workflow actively executing tasks
    - PAUSED: Workflow temporarily suspended
    - COMPLETED: All workflow tasks completed successfully
    - FAILED: Workflow failed due to task failures or errors
    - CANCELLED: Workflow manually cancelled by user
    """
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskStatus(str, Enum):
    """
    Individual task execution status values
    
    Status progression through task lifecycle:
    - PENDING: Task created and waiting for agent assignment
    - RUNNING: Task actively being processed by an agent
    - COMPLETED: Task completed successfully with results
    - FAILED: Task failed during processing
    - CANCELLED: Task cancelled before or during execution
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Validation utilities
class ValidationUtils:
    """Utility functions for validation"""
    
    @staticmethod
    def validate_dict_depth(data: dict, max_depth: int = MAX_DICT_DEPTH) -> bool:
        """Validate dictionary nesting depth to prevent DoS attacks"""
        def get_depth(d, depth=0):
            if not isinstance(d, dict) or depth > max_depth:
                return depth
            return max([get_depth(v, depth + 1) for v in d.values()] + [depth])
        
        return get_depth(data) <= max_depth
    
    @staticmethod
    def validate_list_size(data: list, max_size: int = MAX_LIST_SIZE) -> bool:
        """Validate list size to prevent memory exhaustion"""
        return len(data) <= max_size
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize string input to prevent injection attacks"""
        if not isinstance(value, str):
            return str(value)
        
        # Remove potential script tags and SQL injection patterns
        dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload=',
            r'onerror=',
            r'onclick=',
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into'
        ]
        
        cleaned = value
        for pattern in dangerous_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        return bool(URL_PATTERN.match(url))
    
    @staticmethod
    def validate_uuid(uuid_str: str) -> bool:
        """Validate UUID format"""
        try:
            uuid.UUID(uuid_str)
            return True
        except ValueError:
            return False

# Enhanced Pydantic models with comprehensive validation
class EnhancedCreateTaskRequest(BaseModel):
    """Enhanced task creation request with comprehensive validation"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    type: TaskType = Field(..., description="Type of task to create")
    name: str = Field(..., min_length=3, max_length=MAX_NAME_LENGTH, description="Human-readable task name")
    description: str = Field(..., min_length=1, max_length=MAX_DESCRIPTION_LENGTH, description="Detailed task description")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Task input data and parameters")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority level")
    required_capabilities: List[str] = Field(default_factory=list, max_length=MAX_CAPABILITIES, description="Required agent capabilities")
    workflow_id: Optional[str] = Field(None, description="Associated workflow ID")
    timeout: Optional[float] = Field(None, gt=0, le=86400, description="Task timeout in seconds")
    max_retries: Optional[int] = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    tags: List[str] = Field(default_factory=list, max_length=20, description="Task tags for categorization")
    
    @field_validator('name', 'description')
    def validate_text_fields(cls, v):
        """Validate text fields for safety"""
        if not SAFE_STRING_PATTERN.match(v):
            raise ValueError("Text contains invalid characters")
        return ValidationUtils.sanitize_string(v)
    
    @field_validator('input_data')
    def validate_input_data(cls, v):
        """Validate input data structure"""
        if not ValidationUtils.validate_dict_depth(v):
            raise ValueError(f"Input data nesting too deep. Maximum depth: {MAX_DICT_DEPTH}")
        
        try:
            serialized = json.dumps(v)
            if len(serialized) > MAX_STRING_LENGTH:
                raise ValueError(f"Input data too large. Maximum size: {MAX_STRING_LENGTH} characters")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Input data must be JSON serializable: {e}")
        
        return v
    
    @field_validator('required_capabilities')
    def validate_capabilities(cls, v):
        """Validate capabilities list"""
        if len(v) > MAX_CAPABILITIES:
            raise ValueError(f"Too many capabilities. Maximum allowed: {MAX_CAPABILITIES}")
        
        validated_caps = []
        for cap in v:
            if not isinstance(cap, str):
                raise ValueError("All capabilities must be strings")
            
            cleaned_cap = ValidationUtils.sanitize_string(cap)
            if len(cleaned_cap) < 2:
                raise ValueError(f"Capability '{cap}' is too short")
            if len(cleaned_cap) > 100:
                raise ValueError(f"Capability '{cap}' is too long")
            
            validated_caps.append(cleaned_cap)
        
        return validated_caps
    
    @field_validator('workflow_id')
    def validate_workflow_id(cls, v):
        """Validate workflow ID format"""
        if v and not ValidationUtils.validate_uuid(v):
            raise ValueError("Invalid workflow ID format")
        return v
    
    @field_validator('tags')
    def validate_tags(cls, v):
        """Validate tags"""
        validated_tags = []
        for tag in v:
            if not isinstance(tag, str):
                raise ValueError("All tags must be strings")
            
            cleaned_tag = ValidationUtils.sanitize_string(tag)
            if len(cleaned_tag) < 2:
                raise ValueError(f"Tag '{tag}' is too short")
            if len(cleaned_tag) > 50:
                raise ValueError(f"Tag '{tag}' is too long")
            
            validated_tags.append(cleaned_tag)
        
        return validated_tags

class EnhancedCreateWorkflowRequest(BaseModel):
    """Enhanced workflow creation request with comprehensive validation"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=3, max_length=MAX_NAME_LENGTH, description="Workflow name")
    description: str = Field(..., min_length=1, max_length=MAX_DESCRIPTION_LENGTH, description="Workflow description")
    tasks: List[EnhancedCreateTaskRequest] = Field(..., min_length=1, max_length=MAX_TASKS_PER_WORKFLOW, description="Tasks in the workflow")
    user_id: str = Field(..., min_length=3, description="User creating the workflow")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Workflow configuration")
    schedule: Optional[str] = Field(None, description="Cron-style schedule expression")
    dependencies: List[str] = Field(default_factory=list, max_length=10, description="Workflow dependencies")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    
    @field_validator('name', 'description')
    def validate_text_fields(cls, v):
        """Validate text fields for safety"""
        if not SAFE_STRING_PATTERN.match(v):
            raise ValueError("Text contains invalid characters")
        return ValidationUtils.sanitize_string(v)
    
    @field_validator('configuration')
    def validate_configuration(cls, v):
        """Validate workflow configuration"""
        if not ValidationUtils.validate_dict_depth(v):
            raise ValueError(f"Configuration nesting too deep. Maximum depth: {MAX_DICT_DEPTH}")
        
        # Validate specific configuration keys
        if 'timeout' in v:
            if not isinstance(v['timeout'], (int, float)) or v['timeout'] <= 0:
                raise ValueError("Timeout must be a positive number")
            if v['timeout'] > 86400:
                raise ValueError("Timeout cannot exceed 24 hours")
        
        if 'max_retries' in v:
            if not isinstance(v['max_retries'], int) or v['max_retries'] < 0:
                raise ValueError("max_retries must be a non-negative integer")
            if v['max_retries'] > 10:
                raise ValueError("max_retries cannot exceed 10")
        
        return v
    
    @field_validator('user_id')
    def validate_user_id(cls, v):
        """Validate user ID"""
        sanitized = ValidationUtils.sanitize_string(v)
        if len(sanitized) < 3:
            raise ValueError("User ID too short")
        return sanitized
    
    @field_validator('schedule')
    def validate_schedule(cls, v):
        """Validate cron schedule"""
        if v:
            parts = v.split()
            if len(parts) != 5:
                raise ValueError("Schedule must be in cron format (5 fields)")
        return v
    
    @field_validator('dependencies')
    def validate_dependencies(cls, v):
        """Validate workflow dependencies"""
        for dep in v:
            if not ValidationUtils.validate_uuid(dep):
                raise ValueError(f"Invalid dependency ID format: {dep}")
        return v
    
    @field_validator('environment')
    def validate_environment(cls, v):
        """Validate environment variables"""
        if len(v) > 50:
            raise ValueError("Too many environment variables")
        
        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Environment variables must be string key-value pairs")
            if len(key) > 100 or len(value) > 1000:
                raise ValueError("Environment variable key or value too long")
        return v

class EnhancedAgentRegistrationRequest(BaseModel):
    """Enhanced agent registration request with comprehensive validation"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    type: AgentType = Field(..., description="Type of agent")
    name: str = Field(..., min_length=3, max_length=MAX_NAME_LENGTH, description="Agent name")
    endpoint: str = Field(..., description="Agent endpoint URL")
    capabilities: List[str] = Field(default_factory=list, max_length=MAX_CAPABILITIES, description="Agent capabilities")
    version: Optional[str] = Field(None, description="Agent version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional agent metadata")
    health_check_interval: Optional[int] = Field(default=60, ge=10, le=3600, description="Health check interval in seconds")
    max_concurrent_tasks: Optional[int] = Field(default=5, ge=1, le=100, description="Maximum concurrent tasks")
    
    @field_validator('name')
    def validate_name(cls, v):
        """Validate agent name"""
        if not SAFE_STRING_PATTERN.match(v):
            raise ValueError("Name contains invalid characters")
        return ValidationUtils.sanitize_string(v)
    
    @field_validator('endpoint')
    def validate_endpoint(cls, v):
        """Validate endpoint URL"""
        if not ValidationUtils.validate_url(v):
            raise ValueError("Invalid URL format")
        
        # Security warning for localhost/internal IPs
        if any(suspicious in v.lower() for suspicious in ['localhost', '127.0.0.1', '0.0.0.0']):
            logger.warning(f"Potentially unsafe endpoint URL: {v}")
        
        return v
    
    @field_validator('capabilities')
    def validate_capabilities(cls, v):
        """Validate agent capabilities"""
        if len(v) > MAX_CAPABILITIES:
            raise ValueError(f"Too many capabilities. Maximum allowed: {MAX_CAPABILITIES}")
        
        validated_caps = []
        for cap in v:
            if not isinstance(cap, str):
                raise ValueError("All capabilities must be strings")
            
            cleaned_cap = ValidationUtils.sanitize_string(cap)
            if len(cleaned_cap) < 2:
                raise ValueError(f"Capability '{cap}' is too short")
            if len(cleaned_cap) > 100:
                raise ValueError(f"Capability '{cap}' is too long")
            
            validated_caps.append(cleaned_cap)
        
        return validated_caps
    
    @field_validator('version')
    def validate_version(cls, v):
        """Validate version format"""
        if v and not re.match(r'^\d+\.\d+\.\d+.*$', v):
            raise ValueError("Version must follow semantic versioning (x.y.z)")
        return v
    
    @field_validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata"""
        if not ValidationUtils.validate_dict_depth(v):
            raise ValueError("Metadata nesting too deep")
        
        try:
            serialized = json.dumps(v)
            if len(serialized) > 5000:
                raise ValueError("Metadata too large")
        except (TypeError, ValueError):
            raise ValueError("Metadata must be JSON serializable")
        
        return v

# Query parameter validation models
class TaskQueryParams(BaseModel):
    """Validation for task query parameters"""
    status: Optional[WorkflowStatus] = None
    workflow_id: Optional[str] = None
    agent_id: Optional[str] = None
    limit: Optional[int] = Field(default=100, ge=1, le=1000)
    offset: Optional[int] = Field(default=0, ge=0)
    sort_by: Optional[str] = Field(default="created_at")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")
    
    @field_validator('workflow_id', 'agent_id')
    def validate_ids(cls, v):
        """Validate ID formats"""
        if v and not ValidationUtils.validate_uuid(v):
            raise ValueError("Invalid ID format")
        return v
    
    @field_validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort field"""
        valid_fields = ["created_at", "priority", "status", "name", "type"]
        if v not in valid_fields:
            raise ValueError(f"Invalid sort field. Must be one of: {valid_fields}")
        return v

class AgentQueryParams(BaseModel):
    """Validation for agent query parameters"""
    type: Optional[AgentType] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive|all)$")
    capability: Optional[str] = None
    limit: Optional[int] = Field(default=100, ge=1, le=1000)
    offset: Optional[int] = Field(default=0, ge=0)

# Error response models
class ValidationErrorDetail(BaseModel):
    """Detailed validation error information"""
    field: str
    message: str
    invalid_value: Any
    constraint: Optional[str] = None

class ValidationErrorResponse(BaseModel):
    """Comprehensive validation error response"""
    error: str = "Validation Error"
    message: str
    details: List[ValidationErrorDetail]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: Optional[str] = None

# Security validation functions
class SecurityValidator:
    """Security-focused validation utilities"""
    
    @staticmethod
    def validate_input_size(data: Any, max_size: int = MAX_STRING_LENGTH) -> bool:
        """Validate total input size to prevent DoS"""
        try:
            size = len(json.dumps(data, default=str)) if not isinstance(data, str) else len(data)
            return size <= max_size
        except (TypeError, ValueError):
            return False
    
    @staticmethod
    def validate_no_suspicious_patterns(text: str) -> bool:
        """Check for suspicious patterns that might indicate attacks"""
        suspicious_patterns = [
            r'<script.*?>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'eval\s*\(',
            r'expression\s*\(',
            r'union.*select',
            r'drop.*table',
            r'\$\{.*\}',  # Template injection
            r'#\{.*\}',   # Template injection
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Suspicious pattern detected: {pattern}")
                return False
        
        return True
    
    @staticmethod
    def validate_rate_limit_compliance(request_count: int, time_window: int, limit: int) -> bool:
        """Validate request count against rate limits"""
        return request_count <= limit

# Export enhanced models for use in main application
__all__ = [
    'EnhancedCreateTaskRequest',
    'EnhancedCreateWorkflowRequest', 
    'EnhancedAgentRegistrationRequest',
    'TaskQueryParams',
    'AgentQueryParams',
    'ValidationErrorResponse',
    'ValidationErrorDetail',
    'SecurityValidator',
    'ValidationUtils',
    'TaskType',
    'TaskPriority',
    'AgentType',
    'WorkflowStatus',
    'TaskStatus'
]