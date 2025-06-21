"""
Pydantic schemas for request/response validation with XSS protection.
"""
from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
import html
from models import AnnotationStatus


class BboxSchema(BaseModel):
    """Bounding box coordinates with validation."""
    x1: float = Field(..., ge=0, description="Left x coordinate")
    y1: float = Field(..., ge=0, description="Top y coordinate") 
    x2: float = Field(..., gt=0, description="Right x coordinate")
    y2: float = Field(..., gt=0, description="Bottom y coordinate")
    
    @validator('x2')
    def x2_must_be_greater_than_x1(cls, v, values):
        if 'x1' in values and v <= values['x1']:
            raise ValueError('x2 must be greater than x1')
        return v
    
    @validator('y2')
    def y2_must_be_greater_than_y1(cls, v, values):
        if 'y1' in values and v <= values['y1']:
            raise ValueError('y2 must be greater than y1')
        return v
    
    @validator('x1', 'x2')
    def x_coordinates_within_bounds(cls, v):
        if v < 0 or v > 1920:  # Assuming max width of 1920
            raise ValueError('x coordinates must be between 0 and 1920')
        return v
    
    @validator('y1', 'y2')
    def y_coordinates_within_bounds(cls, v):
        if v < 0 or v > 1080:  # Assuming max height of 1080
            raise ValueError('y coordinates must be between 0 and 1080')
        return v


class AnnotationRequest(BaseModel):
    """Request schema for annotation submission with XSS protection."""
    example_id: str = Field(..., min_length=1, max_length=255)
    bbox: BboxSchema
    label: str = Field(..., min_length=1, max_length=100)
    annotator_id: str = Field(..., min_length=1, max_length=255)
    quality_score: float = Field(1.0, ge=0.0, le=1.0)
    notes: Optional[str] = Field(None, max_length=1000)

    @validator('label')
    def validate_label(cls, v):
        """Validate label against allowed pattern to prevent XSS."""
        if not isinstance(v, str):
            raise ValueError('Label must be a string')
        
        # Only allow alphanumeric characters, spaces, underscores, and hyphens
        pattern = re.compile(r'^[A-Za-z0-9 _-]{1,50}$')
        if not pattern.match(v):
            raise ValueError(
                'Invalid label format. Only alphanumeric characters, spaces, '
                'underscores, and hyphens are allowed (1-50 characters).'
            )
        
        # Additional XSS protection - escape HTML entities
        sanitized = html.escape(v.strip())
        
        # Check for script tags or suspicious patterns (defense in depth)
        dangerous_patterns = [
            r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
            r'javascript:',
            r'vbscript:',
            r'on\w+\s*=',
            r'<.*?>',
            r'&\w+;',  # HTML entities that might have bypassed previous checks
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise ValueError('Label contains invalid characters or patterns')
        
        return sanitized

    @validator('annotator_id')
    def validate_annotator_id(cls, v):
        """Validate annotator ID to prevent injection attacks."""
        if not isinstance(v, str):
            raise ValueError('Annotator ID must be a string')
        
        # Only allow alphanumeric characters, underscores, and hyphens
        pattern = re.compile(r'^[A-Za-z0-9_-]{1,100}$')
        if not pattern.match(v):
            raise ValueError(
                'Invalid annotator ID format. Only alphanumeric characters, '
                'underscores, and hyphens are allowed (1-100 characters).'
            )
        
        # Escape HTML entities for safety
        sanitized = html.escape(v.strip())
        return sanitized

    @validator('example_id')
    def validate_example_id(cls, v):
        """Validate example ID to prevent injection attacks."""
        if not isinstance(v, str):
            raise ValueError('Example ID must be a string')
        
        # Allow alphanumeric characters, underscores, hyphens, and periods
        pattern = re.compile(r'^[A-Za-z0-9._-]{1,255}$')
        if not pattern.match(v):
            raise ValueError(
                'Invalid example ID format. Only alphanumeric characters, '
                'periods, underscores, and hyphens are allowed (1-255 characters).'
            )
        
        return html.escape(v.strip())

    @validator('notes')
    def validate_notes(cls, v):
        """Validate notes field to prevent XSS attacks."""
        if v is None:
            return v
        
        if not isinstance(v, str):
            raise ValueError('Notes must be a string')
        
        if len(v) > 1000:
            raise ValueError('Notes must be 1000 characters or less')
        
        # Check for script tags
        if re.search(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', v, re.IGNORECASE):
            raise ValueError('Notes contain invalid script tags')
        
        # Check for dangerous event handlers
        if re.search(r'on\w+\s*=', v, re.IGNORECASE):
            raise ValueError('Notes contain invalid event handlers')
        
        # Check for other dangerous patterns
        dangerous_patterns = [
            r'<iframe\b[^>]*>',  # iframes
            r'<object\b[^>]*>',  # objects
            r'<embed\b[^>]*>',   # embeds
            r'<link\b[^>]*>',    # links (CSS/external resources)
            r'<style\b[^>]*>',   # style tags
            r'javascript:',       # javascript protocol
            r'vbscript:',        # vbscript protocol
            r'data:.*script',     # data URLs with scripts
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Notes contain invalid or potentially dangerous content')
        
        # Escape HTML entities
        sanitized = html.escape(v.strip())
        return sanitized

    @validator('quality_score')
    def validate_quality_score(cls, v):
        """Validate quality score is within bounds."""
        if not isinstance(v, (int, float)):
            raise ValueError('Quality score must be a number')
        
        if v < 0.0 or v > 1.0:
            raise ValueError('Quality score must be between 0.0 and 1.0')
        
        return float(v)


class AnnotationResponse(BaseModel):
    """Response schema for annotation operations."""
    status: str
    example_id: str
    message: Optional[str] = None


class ExampleResponse(BaseModel):
    """Response schema for example data."""
    id: int
    example_id: str
    camera_id: str
    timestamp: datetime
    original_detections: Optional[Dict[str, Any]] = None
    confidence_scores: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    bbox: Optional[Dict[str, float]] = None
    label: Optional[str] = None
    status: AnnotationStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExampleListResponse(BaseModel):
    """Response schema for example lists."""
    examples: List[ExampleResponse]
    total: int
    page: int = 1
    page_size: int = 50


class HealthResponse(BaseModel):
    """Response schema for health check."""
    status: str
    service: str
    database_connected: bool
    kafka_connected: bool
    pending_examples: int
    details: Optional[Dict[str, Any]] = None


class StatsResponse(BaseModel):
    """Response schema for statistics."""
    pending_examples: int
    completed_examples: int
    retry_queue_size: int
    topics: Dict[str, str]


# Error Response Models for consistent error handling
class ErrorDetail(BaseModel):
    """Detailed error information."""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: str
    detail: str
    errors: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Response for validation errors (422)."""
    error: str = "Validation Error"
    detail: str
    errors: List[ErrorDetail]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


# Additional response models for specific endpoints
class LoginResponse(BaseModel):
    """Response schema for authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 28800  # 8 hours in seconds


class CSRFTokenResponse(BaseModel):
    """Response schema for CSRF token."""
    csrf_token: str


class KafkaMetricsResponse(BaseModel):
    """Response schema for Kafka metrics."""
    consumer_group: str
    consumer_group_members: int
    partition_assignments: Dict[str, List[int]]
    consumer_lag: Dict[str, int]
    topics: List[str]
    connection_status: str
    last_heartbeat: Optional[datetime] = None


class ScalingInfoResponse(BaseModel):
    """Response schema for scaling information."""
    instance_id: str
    instance_index: int
    total_instances: int
    websocket_connections: int
    consumer_assignments: Dict[str, List[int]]
    redis_connected: bool
    kafka_connected: bool
    uptime_seconds: float


# Success response models for specific operations
class DeleteResponse(BaseModel):
    """Response schema for delete operations."""
    status: str = "success"
    message: str
    deleted_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GenericSuccessResponse(BaseModel):
    """Generic success response."""
    status: str = "success"
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[Dict[str, Any]] = None


class ExamplesResponse(BaseModel):
    """Response schema for multiple examples with pagination."""
    total: int
    items: List[ExampleResponse]
    page: int = 1
    page_size: int = 50
    has_next: bool = False
    has_prev: bool = False
