# Enhanced Prompt Service - API Documentation

## Overview

The Enhanced Prompt Service provides a REST API for intelligent conversational interactions with surveillance system data. All endpoints require JWT authentication and support JSON request/response formats.

**Base URL**: `http://localhost:8000/api/v1`  
**Authentication**: Bearer Token (JWT)  
**Content-Type**: `application/json`

## Authentication

All API endpoints require a valid JWT token in the Authorization header:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/v1/conversation
```

## Endpoints

### 1. Health Check

**GET** `/health`

Check service health status.

**Response:**
```json
{
  "status": "ok"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### 2. Enhanced Conversation

**POST** `/api/v1/conversation`

Submit a query and receive an AI-powered conversational response with context and follow-up suggestions.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | User's question or query |
| `conversation_id` | string | No | Existing conversation ID (creates new if omitted) |
| `user_context` | object | No | Additional context metadata |
| `limit` | integer | No | Maximum search results (default: 5) |

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `conversation_id` | string | Unique conversation identifier |
| `response` | string | AI-generated response text |
| `follow_up_questions` | array[string] | Suggested follow-up questions |
| `evidence` | array[object] | Supporting evidence from search |
| `clip_links` | array[string] | Related video clip URLs |
| `confidence_score` | float | Response confidence (0.0-1.0) |
| `response_type` | string | Type: "answer", "clarification", "proactive_insight" |
| `metadata` | object | Additional response metadata |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/conversation \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me any security incidents from camera 5 today",
    "limit": 10
  }'
```

**Example Response:**
```json
{
  "conversation_id": "conv_123e4567-e89b-12d3-a456-426614174000",
  "response": "I found 3 security incidents from camera 5 today. The most significant was a person detected in a restricted area at 14:32 with high confidence. There were also two motion alerts during off-hours.",
  "follow_up_questions": [
    "Can you show me the video clip from the 14:32 incident?",
    "What was the confidence level for each detection?",
    "Are there any patterns in the timing of these incidents?",
    "Have there been similar incidents on other cameras?"
  ],
  "evidence": [
    {
      "event_id": "evt_789",
      "timestamp": "2025-06-18T14:32:15Z",
      "camera_id": "camera_5",
      "event_type": "person_detected",
      "confidence": 0.94,
      "details": "Person detected in restricted area Zone-A"
    }
  ],
  "clip_links": [
    {
      "url": "http://localhost:8001/clips/evt_789.mp4",
      "event_id": "evt_789",
      "timestamp": "2025-06-18T14:32:15Z",
      "camera_id": "camera_5",
      "confidence": 0.94,
      "description": "Person detected in restricted area"
    }
  ],
  "confidence_score": 0.89,
  "response_type": "answer",
  "metadata": {
    "search_time_ms": 45,
    "llm_time_ms": 1200,
    "total_events_found": 3,
    "conversation_length": 1
  }
}
```

---

### 3. Proactive Insights

**GET** `/api/v1/proactive-insights`

Get AI-generated insights about system patterns and anomalies.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `time_range` | string | "24h" | Time window: "1h", "24h", "7d", "30d" |
| `severity_threshold` | string | "medium" | Minimum severity: "low", "medium", "high" |
| `include_predictions` | boolean | true | Include predictive insights |

**Response:**
Array of `ConversationResponse` objects with `response_type: "proactive_insight"`

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/proactive-insights?time_range=24h&severity_threshold=medium" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Example Response:**
```json
[
  {
    "conversation_id": "insight_123",
    "response": "Unusual activity spike detected: 40% increase in motion alerts between 2-4 AM compared to normal patterns. Camera 3 and 7 showing highest activity.",
    "follow_up_questions": [
      "Show me the specific events from cameras 3 and 7",
      "What's the normal activity pattern for this time period?",
      "Are there any environmental factors that might explain this?"
    ],
    "evidence": [],
    "clip_links": [],
    "confidence_score": 0.76,
    "response_type": "proactive_insight",
    "metadata": {
      "insight_type": "activity_spike",
      "affected_cameras": ["camera_3", "camera_7"],
      "time_period": "02:00-04:00",
      "severity": "medium"
    }
  }
]
```

---

### 4. Conversation History

**GET** `/api/v1/conversation/{conversation_id}/history`

Get the message history for a specific conversation.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | Yes | Conversation identifier |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Maximum messages to return |

**Response:**
```json
{
  "conversation_id": "conv_123e4567-e89b-12d3-a456-426614174000",
  "messages": [
    {
      "id": "msg_456",
      "role": "user",
      "content": "Show me security incidents from today",
      "timestamp": "2025-06-18T10:30:00Z",
      "metadata": {}
    },
    {
      "id": "msg_789",
      "role": "assistant",
      "content": "I found 5 security incidents today across 3 cameras...",
      "timestamp": "2025-06-18T10:30:02Z",
      "metadata": {
        "confidence_score": 0.92,
        "evidence_count": 5
      }
    }
  ],
  "total_messages": 12,
  "created_at": "2025-06-18T09:15:00Z",
  "last_activity": "2025-06-18T10:30:02Z"
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/conversation/conv_123/history?limit=20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 5. Delete Conversation

**DELETE** `/api/v1/conversation/{conversation_id}`

Delete a conversation and all its message history.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | Yes | Conversation identifier |

**Response:**
```json
{
  "message": "Conversation deleted successfully",
  "conversation_id": "conv_123e4567-e89b-12d3-a456-426614174000"
}
```

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/api/v1/conversation/conv_123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "detail": "Error description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2025-06-18T10:30:00Z",
  "path": "/api/v1/conversation",
  "correlation_id": "req_123456"
}
```

### Common HTTP Status Codes

- **200 OK** - Successful request
- **400 Bad Request** - Invalid request parameters
- **401 Unauthorized** - Missing or invalid JWT token
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error
- **503 Service Unavailable** - Service temporarily unavailable

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Default Limit**: 100 requests per minute per user
- **Burst Limit**: 20 requests per 10 seconds per user
- **Headers**: Rate limit information in response headers:
  - `X-RateLimit-Limit`: Requests allowed per window
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Time when the limit resets

## Request/Response Examples

### Complex Conversation Example

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/conversation \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What security patterns have you noticed this week?",
    "conversation_id": "conv_existing_123",
    "user_context": {
      "user_role": "security_manager",
      "timezone": "America/New_York",
      "dashboard_context": "weekly_review"
    },
    "limit": 15
  }'
```

**Response:**
```json
{
  "conversation_id": "conv_existing_123",
  "response": "Based on this week's data, I've identified several notable security patterns:\n\n1. **Peak Activity Hours**: Unusual activity spikes between 2-4 AM on weekdays, primarily from cameras 5 and 8\n2. **Detection Confidence**: Average confidence scores have improved 12% this week, indicating better lighting conditions\n3. **False Positive Reduction**: Motion alerts decreased 25% after the recent calibration updates\n\nThe most significant pattern is the recurring late-night activity in the east wing, which warrants investigation.",
  "follow_up_questions": [
    "Can you show me specific incidents from the east wing this week?",
    "What caused the confidence score improvements?",
    "Are there any seasonal patterns in the security data?",
    "How do this week's metrics compare to last month?",
    "Should we adjust detection thresholds based on these patterns?"
  ],
  "evidence": [
    {
      "event_id": "evt_week_summary",
      "pattern_type": "activity_spike",
      "affected_cameras": ["camera_5", "camera_8"],
      "time_pattern": "02:00-04:00 weekdays",
      "confidence": 0.87
    }
  ],
  "clip_links": [],
  "confidence_score": 0.91,
  "response_type": "answer",
  "metadata": {
    "analysis_period": "7_days",
    "total_events_analyzed": 1247,
    "patterns_detected": 3,
    "conversation_turn": 4,
    "user_context": {
      "role": "security_manager",
      "dashboard_context": "weekly_review"
    }
  }
}
```

## SDK and Client Libraries

Coming soon:
- Python SDK
- JavaScript/TypeScript SDK
- CLI tool for testing and automation

## Webhook Support

Future versions will support webhook notifications for:
- Proactive insight generation
- Conversation state changes
- System alerts and anomalies
