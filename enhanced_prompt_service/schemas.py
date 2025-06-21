"""
Response schemas for the Enhanced Prompt Service API.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class Evidence(BaseModel):
    """Evidence item model for search results."""
    event_id: str = Field(..., description="Unique identifier for the event")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")
    camera_id: str = Field(..., description="Camera identifier that captured the event")
    event_type: str = Field(..., description="Type of event (e.g., 'person_detected', 'motion')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    description: str = Field(..., description="Human-readable description of the event")


class PromptResponse(BaseModel):
    """Response model for prompt/conversation endpoints."""
    conversation_id: str = Field(..., description="Unique conversation identifier")
    response: str = Field(..., description="AI-generated response text")
    follow_up_questions: List[str] = Field(default_factory=list, description="Suggested follow-up questions")
    evidence: List[Evidence] = Field(default_factory=list, description="Evidence supporting the response")
    clip_links: List[str] = Field(default_factory=list, description="URLs to video clips")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in the response")
    response_type: str = Field(..., description="Type of response: 'answer', 'clarification', 'proactive_insight'")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional response metadata")


class ConversationMessage(BaseModel):
    """Individual conversation message."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Message metadata")


class HistoryResponse(BaseModel):
    """Response model for conversation history endpoints."""
    conversation_id: str = Field(..., description="Unique conversation identifier")
    messages: List[ConversationMessage] = Field(..., description="List of conversation messages")


class ProactiveInsightsResponse(BaseModel):
    """Response model for proactive insights endpoints."""
    insights: List[PromptResponse] = Field(..., description="List of proactive insights")


class HealthResponse(BaseModel):
    """Response model for health check endpoints."""
    status: str = Field(..., description="Service health status")


class ConversationDeleteResponse(BaseModel):
    """Response model for conversation deletion."""
    message: str = Field(..., description="Deletion confirmation message")


# Downstream Integration Payload Models
class PromptResponsePayload(BaseModel):
    """
    Payload schema for sending prompt responses to downstream services.
    Used by Ingest Service, Notifier Service, and AI Dashboard.
    """
    service_name: str = Field(default="enhanced_prompt_service", description="Source service identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Response generation timestamp")
    conversation_id: str = Field(..., description="Unique conversation identifier")
    user_id: str = Field(..., description="User identifier who made the request")
    
    # Core response data
    query: str = Field(..., description="Original user query")
    response: str = Field(..., description="AI-generated response")
    response_type: str = Field(..., description="Response type: 'answer', 'clarification', 'proactive_insight'")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Response confidence score")
    
    # Evidence and context
    evidence_count: int = Field(..., ge=0, description="Number of evidence items found")
    evidence: List[Evidence] = Field(default_factory=list, description="Supporting evidence")
    clip_links: List[str] = Field(default_factory=list, description="Video clip URLs")
    
    # Engagement metrics
    follow_up_questions: List[str] = Field(default_factory=list, description="Generated follow-up questions")
    conversation_turn: int = Field(..., ge=1, description="Turn number in conversation")
    processing_time_ms: int = Field(..., ge=0, description="Response processing time in milliseconds")
    
    # System metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional system metadata")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "service_name": "enhanced_prompt_service",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "conversation_id": "conv_12345",
                    "user_id": "user_67890",
                    "query": "What happened in camera 3 today?",
                    "response": "I found 5 motion detection events in camera 3 today, including 2 person detections between 2-3 PM.",
                    "response_type": "answer",
                    "confidence_score": 0.87,
                    "evidence_count": 5,
                    "evidence": [
                        {
                            "event_id": "evt_001",
                            "timestamp": "2024-01-15T14:30:00Z",
                            "camera_id": "camera_3",
                            "event_type": "person_detected",
                            "confidence": 0.92,
                            "description": "Person detected near entrance"
                        }
                    ],
                    "clip_links": ["https://clips.example.com/evt_001.mp4"],
                    "follow_up_questions": ["Would you like to see the video clips?", "Do you want to check other cameras?"],
                    "conversation_turn": 1,
                    "processing_time_ms": 1250,
                    "metadata": {
                        "search_duration_ms": 850,
                        "ai_model": "gpt-4",
                        "context_used": True
                    }
                }
            ]
        }


class HistoryRetrievalPayload(BaseModel):
    """
    Payload schema for sending conversation history to downstream services.
    Used for analytics, audit logs, and AI Dashboard conversation views.
    """
    service_name: str = Field(default="enhanced_prompt_service", description="Source service identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Retrieval timestamp")
    conversation_id: str = Field(..., description="Unique conversation identifier")
    user_id: str = Field(..., description="User identifier")
    
    # Conversation metadata
    conversation_created: str = Field(..., description="Conversation creation timestamp")
    total_messages: int = Field(..., ge=0, description="Total number of messages in conversation")
    conversation_duration_minutes: Optional[int] = Field(None, ge=0, description="Conversation duration in minutes")
    
    # Message history
    messages: List[ConversationMessage] = Field(..., description="Chronological list of messages")
    
    # Conversation analytics
    user_queries: int = Field(..., ge=0, description="Number of user queries")
    ai_responses: int = Field(..., ge=0, description="Number of AI responses")
    average_confidence: float = Field(..., ge=0.0, le=1.0, description="Average AI response confidence")
    evidence_items_total: int = Field(..., ge=0, description="Total evidence items referenced")
    
    # Context and classification
    conversation_topics: List[str] = Field(default_factory=list, description="Identified conversation topics")
    cameras_discussed: List[str] = Field(default_factory=list, description="Camera IDs mentioned in conversation")
    last_activity: str = Field(..., description="Timestamp of last conversation activity")
    
    # System metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional conversation metadata")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "service_name": "enhanced_prompt_service",
                    "timestamp": "2024-01-15T16:45:00Z",
                    "conversation_id": "conv_12345",
                    "user_id": "user_67890",
                    "conversation_created": "2024-01-15T10:30:00Z",
                    "total_messages": 6,
                    "conversation_duration_minutes": 375,
                    "messages": [
                        {
                            "role": "user",
                            "content": "What happened in camera 3 today?",
                            "timestamp": "2024-01-15T10:30:00Z",
                            "metadata": {}
                        },
                        {
                            "role": "assistant",
                            "content": "I found 5 motion detection events in camera 3 today...",
                            "timestamp": "2024-01-15T10:30:15Z",
                            "metadata": {"confidence": 0.87, "evidence_count": 5}
                        }
                    ],
                    "user_queries": 3,
                    "ai_responses": 3,
                    "average_confidence": 0.85,
                    "evidence_items_total": 12,
                    "conversation_topics": ["motion_detection", "camera_3", "security_review"],
                    "cameras_discussed": ["camera_3", "camera_1"],
                    "last_activity": "2024-01-15T16:45:00Z",
                    "metadata": {
                        "user_session": "session_789",
                        "client_type": "web",
                        "conversation_rating": "helpful"
                    }
                }
            ]
        }


class ProactiveInsightPayload(BaseModel):
    """
    Payload schema for sending proactive insights to downstream services.
    Used for system monitoring, alerting, and dashboard notifications.
    """
    service_name: str = Field(default="enhanced_prompt_service", description="Source service identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Insight generation timestamp")
    
    # Insight identification
    insight_id: str = Field(..., description="Unique insight identifier")
    insight_type: str = Field(..., description="Type of insight: 'activity_spike', 'camera_performance', 'security_anomaly', 'prediction'")
    severity: str = Field(..., description="Insight severity: 'low', 'medium', 'high', 'critical'")
    
    # Core insight data
    title: str = Field(..., description="Brief insight title")
    message: str = Field(..., description="Detailed insight description")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Insight confidence score")
    
    # Time and scope
    analysis_period: str = Field(..., description="Time period analyzed (e.g., '24h', '7d')")
    affected_cameras: List[str] = Field(default_factory=list, description="Camera IDs affected by this insight")
    event_count: int = Field(..., ge=0, description="Number of events analyzed")
    
    # Recommendations
    suggested_actions: List[str] = Field(default_factory=list, description="Recommended actions")
    priority_level: int = Field(..., ge=1, le=5, description="Action priority level (1=low, 5=critical)")
    
    # Supporting data
    evidence: List[Evidence] = Field(default_factory=list, description="Supporting evidence")
    clip_links: List[str] = Field(default_factory=list, description="Relevant video clips")
    
    # System context
    related_insights: List[str] = Field(default_factory=list, description="Related insight IDs")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional insight metadata")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "service_name": "enhanced_prompt_service",
                    "timestamp": "2024-01-15T09:00:00Z",
                    "insight_id": "insight_activity_spike_001",
                    "insight_type": "activity_spike",
                    "severity": "medium",
                    "title": "Unusual Activity Detected",
                    "message": "Unusual activity detected: 67 events in the last hour, significantly above normal baseline of 20-25 events.",
                    "confidence_score": 0.82,
                    "analysis_period": "1h",
                    "affected_cameras": ["camera_1", "camera_3", "camera_5"],
                    "event_count": 67,
                    "suggested_actions": [
                        "Review camera feeds for the affected areas",
                        "Check for environmental factors causing false triggers",
                        "Consider adjusting detection sensitivity"
                    ],
                    "priority_level": 3,
                    "evidence": [
                        {
                            "event_id": "evt_spike_001",
                            "timestamp": "2024-01-15T08:30:00Z",
                            "camera_id": "camera_1",
                            "event_type": "motion_detected",
                            "confidence": 0.78,
                            "description": "Motion detected in main entrance"
                        }
                    ],
                    "clip_links": ["https://clips.example.com/evt_spike_001.mp4"],
                    "related_insights": [],
                    "metadata": {
                        "baseline_events_per_hour": 23,
                        "spike_threshold": 45,
                        "weather_condition": "windy",
                        "detection_algorithm": "yolo_v8"
                    }
                }
            ]
        }
