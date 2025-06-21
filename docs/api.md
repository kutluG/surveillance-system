# API Reference

## Overview

The AI-Powered Surveillance System provides RESTful APIs for all major functions including video management, annotation, monitoring, and system administration. All APIs use JSON for data exchange and support standard HTTP methods.

## Authentication

All protected endpoints require JWT authentication. Include the token in the Authorization header:

```bash
Authorization: Bearer <jwt_token>
```

### Getting a Token

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## Base URLs

| Service | Base URL | Description |
|---------|----------|-------------|
| API Gateway | `http://localhost:8000` | Central entry point |
| VMS Service | `http://localhost:8001` | Video management |
| Agent Orchestrator | `http://localhost:8002` | AI coordination |
| Dashboard Service | `http://localhost:8003` | Analytics |
| Ingest Service | `http://localhost:8004` | Stream processing |
| Rule Builder | `http://localhost:8005` | Alert rules |
| Notifier | `http://localhost:8006` | Notifications |
| Retention Service | `http://localhost:8007` | Data lifecycle |
| RAG Service | `http://localhost:8008` | AI insights |
| Prompt Service | `http://localhost:8009` | Prompt management |
| RuleGen Service | `http://localhost:8010` | Rule generation |
| Annotation Frontend | `http://localhost:8011` | Human annotation |

## Core API Endpoints

### Health & Status

#### System Health
```bash
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "service": "api_gateway",
  "timestamp": "2025-06-16T12:00:00Z",
  "uptime": 3600,
  "version": "1.0.0"
}
```

#### Service Status
```bash
GET /api/v1/status
```
*Requires: Authentication*

**Response:**
```json
{
  "services": {
    "vms_service": "healthy",
    "agent_orchestrator": "healthy",
    "dashboard_service": "healthy",
    "kafka": "healthy",
    "postgresql": "healthy",
    "redis": "healthy"
  },
  "overall_status": "healthy",
  "last_check": "2025-06-16T12:00:00Z"
}
```

### Video Management System (VMS)

#### List Cameras
```bash
GET /api/v1/cameras
```
*Requires: Authentication*

**Response:**
```json
{
  "cameras": [
    {
      "id": "cam-001",
      "name": "Front Door",
      "location": "Main Entrance",
      "status": "online",
      "stream_url": "rtsp://192.168.1.100:554/stream",
      "resolution": "1920x1080",
      "fps": 30,
      "last_seen": "2025-06-16T11:59:30Z"
    }
  ],
  "total": 1
}
```

#### Get Camera Details
```bash
GET /api/v1/cameras/{camera_id}
```
*Requires: Authentication*

**Response:**
```json
{
  "id": "cam-001",
  "name": "Front Door",
  "location": "Main Entrance",
  "status": "online",
  "stream_url": "rtsp://192.168.1.100:554/stream",
  "settings": {
    "resolution": "1920x1080",
    "fps": 30,
    "encoding": "H.264",
    "bitrate": 2000
  },
  "statistics": {
    "uptime": 99.5,
    "total_recordings": 1250,
    "storage_used": "15.2GB",
    "last_recording": "2025-06-16T11:45:00Z"
  }
}
```

#### Start/Stop Recording
```bash
POST /api/v1/cameras/{camera_id}/recording
Content-Type: application/json
```
*Requires: Authentication with `camera:control` scope*

**Request:**
```json
{
  "action": "start",
  "duration": 3600,
  "quality": "high"
}
```

**Response:**
```json
{
  "status": "success",
  "recording_id": "rec-001",
  "started_at": "2025-06-16T12:00:00Z",
  "estimated_end": "2025-06-16T13:00:00Z"
}
```

### Annotation System

#### Get Pending Examples
```bash
GET /api/v1/examples
```
*Requires: Authentication*

**Query Parameters:**
- `limit` (optional): Number of examples to return (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "examples": [
    {
      "event_id": "evt-12345",
      "camera_id": "cam-001",
      "timestamp": "2025-06-16T11:30:00Z",
      "reason": "Low confidence detection",
      "confidence_scores": {
        "person": 0.45,
        "vehicle": 0.12
      },
      "detections": [
        {
          "bbox": {"x1": 100, "y1": 50, "x2": 200, "y2": 150},
          "class_name": "person",
          "confidence": 0.45
        }
      ],
      "frame_data": "base64_encoded_image_data"
    }
  ],
  "total": 23,
  "has_more": true
}
```

#### Get Specific Example
```bash
GET /api/v1/examples/{event_id}
```
*Requires: Authentication*

**Response:**
```json
{
  "event_id": "evt-12345",
  "camera_id": "cam-001",
  "timestamp": "2025-06-16T11:30:00Z",
  "reason": "Low confidence detection",
  "confidence_scores": {
    "person": 0.45,
    "vehicle": 0.12
  },
  "detections": [
    {
      "bbox": {"x1": 100, "y1": 50, "x2": 200, "y2": 150},
      "class_name": "person",
      "confidence": 0.45
    }
  ],
  "frame_data": "base64_encoded_image_data",
  "metadata": {
    "original_size": {"width": 1920, "height": 1080},
    "processing_time": 0.25,
    "model_version": "v2.1.0"
  }
}
```

#### Submit Annotation
```bash
POST /api/v1/examples/{event_id}/label
Content-Type: application/json
```
*Requires: Authentication with `annotation:write` scope*

**Request:**
```json
{
  "corrected_detections": [
    {
      "bbox": {"x1": 100, "y1": 50, "x2": 200, "y2": 150},
      "class_name": "person",
      "confidence": 0.45,
      "corrected_class": "person",
      "is_correct": true
    }
  ],
  "annotator_id": "annotator-123",
  "quality_score": 0.95,
  "notes": "Clear person detection, correct classification"
}
```

**Response:**
```json
{
  "status": "success",
  "event_id": "evt-12345",
  "annotation_id": "ann-789",
  "processed_at": "2025-06-16T12:00:00Z"
}
```

#### Skip Example
```bash
DELETE /api/v1/examples/{event_id}
```
*Requires: Authentication with `annotation:write` scope*

**Response:**
```json
{
  "status": "skipped",
  "event_id": "evt-12345",
  "skipped_at": "2025-06-16T12:00:00Z"
}
```

### Alert Management

#### List Alerts
```bash
GET /api/v1/alerts
```
*Requires: Authentication*

**Query Parameters:**
- `status` (optional): Filter by status (`active`, `resolved`, `acknowledged`)
- `severity` (optional): Filter by severity (`low`, `medium`, `high`, `critical`)
- `camera_id` (optional): Filter by camera
- `limit` (optional): Number of alerts to return (default: 50)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "alerts": [
    {
      "id": "alert-001",
      "title": "Person detected in restricted area",
      "description": "Person detected in Building A restricted zone",
      "severity": "high",
      "status": "active",
      "camera_id": "cam-001",
      "location": "Building A - Zone 1",
      "created_at": "2025-06-16T11:45:00Z",
      "updated_at": "2025-06-16T11:45:00Z",
      "metadata": {
        "detection_confidence": 0.89,
        "person_count": 1,
        "duration": 45
      }
    }
  ],
  "total": 5,
  "has_more": false
}
```

#### Create Alert
```bash
POST /api/v1/alerts
Content-Type: application/json
```
*Requires: Authentication with `alert:create` scope*

**Request:**
```json
{
  "title": "Security breach detected",
  "description": "Unauthorized access attempt",
  "severity": "critical",
  "camera_id": "cam-002",
  "location": "Main Entrance",
  "metadata": {
    "detection_type": "person",
    "confidence": 0.95
  }
}
```

**Response:**
```json
{
  "id": "alert-002",
  "status": "created",
  "created_at": "2025-06-16T12:00:00Z"
}
```

#### Update Alert Status
```bash
PATCH /api/v1/alerts/{alert_id}
Content-Type: application/json
```
*Requires: Authentication with `alert:update` scope*

**Request:**
```json
{
  "status": "acknowledged",
  "notes": "Security team notified and investigating"
}
```

**Response:**
```json
{
  "id": "alert-001",
  "status": "acknowledged",
  "updated_at": "2025-06-16T12:00:00Z",
  "updated_by": "user@example.com"
}
```

### Dashboard & Analytics

#### Get System Overview
```bash
GET /api/v1/dashboard/overview
```
*Requires: Authentication*

**Response:**
```json
{
  "summary": {
    "active_cameras": 12,
    "active_alerts": 3,
    "recordings_today": 45,
    "storage_used": "2.3TB",
    "system_health": "healthy"
  },
  "metrics": {
    "detections_last_hour": 127,
    "false_positive_rate": 0.02,
    "average_response_time": 245,
    "uptime_percentage": 99.8
  },
  "recent_activities": [
    {
      "type": "alert",
      "description": "Person detected in restricted area",
      "timestamp": "2025-06-16T11:45:00Z",
      "camera_id": "cam-001"
    }
  ]
}
```

#### Get Analytics Data
```bash
GET /api/v1/dashboard/analytics
```
*Requires: Authentication*

**Query Parameters:**
- `timerange` (optional): Time range (`1h`, `24h`, `7d`, `30d`) (default: `24h`)
- `metric` (optional): Specific metric to retrieve
- `camera_id` (optional): Filter by camera

**Response:**
```json
{
  "timerange": "24h",
  "data": {
    "detections": {
      "total": 1250,
      "by_type": {
        "person": 856,
        "vehicle": 394
      },
      "by_hour": [
        {"hour": "00:00", "count": 45},
        {"hour": "01:00", "count": 23}
      ]
    },
    "alerts": {
      "total": 12,
      "by_severity": {
        "low": 5,
        "medium": 4,
        "high": 2,
        "critical": 1
      }
    }
  }
}
```

### Notification Management

#### Send Notification
```bash
POST /api/v1/notifications
Content-Type: application/json
```
*Requires: Authentication with `notification:send` scope*

**Request:**
```json
{
  "title": "Security Alert",
  "message": "Unauthorized access detected at main entrance",
  "severity": "high",
  "channels": ["email", "sms"],
  "recipients": ["admin@company.com", "+1234567890"],
  "metadata": {
    "alert_id": "alert-001",
    "camera_id": "cam-001"
  }
}
```

**Response:**
```json
{
  "notification_id": "notif-001",
  "status": "sent",
  "channels_sent": ["email", "sms"],
  "sent_at": "2025-06-16T12:00:00Z",
  "delivery_status": {
    "email": "delivered",
    "sms": "pending"
  }
}
```

#### Get Notification History
```bash
GET /api/v1/notifications
```
*Requires: Authentication*

**Query Parameters:**
- `limit` (optional): Number of notifications to return
- `status` (optional): Filter by status (`sent`, `pending`, `failed`)

**Response:**
```json
{
  "notifications": [
    {
      "id": "notif-001",
      "title": "Security Alert",
      "message": "Unauthorized access detected",
      "severity": "high",
      "status": "sent",
      "channels": ["email", "sms"],
      "sent_at": "2025-06-16T12:00:00Z",
      "delivery_status": {
        "email": "delivered",
        "sms": "delivered"
      }
    }
  ],
  "total": 1
}
```

## Data Schemas

### Common Data Types

#### BoundingBox
```json
{
  "x1": "number (top-left x coordinate)",
  "y1": "number (top-left y coordinate)", 
  "x2": "number (bottom-right x coordinate)",
  "y2": "number (bottom-right y coordinate)"
}
```

#### Detection
```json
{
  "bbox": "BoundingBox object",
  "class_name": "string (detected object class)",
  "confidence": "number (0.0-1.0 confidence score)",
  "corrected_class": "string (optional, human-corrected class)",
  "is_correct": "boolean (whether detection is correct)"
}
```

#### Camera
```json
{
  "id": "string (unique camera identifier)",
  "name": "string (human-readable name)",
  "location": "string (physical location)",
  "status": "string (online|offline|error)",
  "stream_url": "string (RTSP/HTTP stream URL)",
  "settings": "object (camera configuration)",
  "statistics": "object (usage statistics)"
}
```

## Error Handling

All API endpoints return consistent error responses:

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "camera_id",
        "message": "Camera ID is required"
      }
    ],
    "request_id": "req-12345-abcde"
  }
}
```

### Common Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `VALIDATION_ERROR` | Invalid request parameters |
| 401 | `AUTHENTICATION_REQUIRED` | Missing or invalid authentication |
| 403 | `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| 404 | `RESOURCE_NOT_FOUND` | Requested resource does not exist |
| 409 | `RESOURCE_CONFLICT` | Resource already exists or conflict |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected server error |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily unavailable |

## Rate Limiting

API rate limits are enforced per user and per endpoint:

| Endpoint Pattern | Rate Limit | Window |
|------------------|------------|---------|
| `/health` | 100 requests | 1 minute |
| `/api/v1/auth/*` | 10 requests | 1 minute |
| `/api/v1/examples` | 50 requests | 1 minute |
| `/api/v1/alerts` | 100 requests | 1 minute |
| `/api/v1/notifications` | 20 requests | 1 minute |
| Default | 100 requests | 1 minute |

Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## WebSocket API

Real-time events are available via WebSocket connections:

### Connect to Events Stream
```javascript
const ws = new WebSocket('ws://localhost:8003/ws/v1/events/client-123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received event:', data);
};
```

### Event Types
- `detection`: New object detection
- `alert`: New alert created
- `camera_status`: Camera status change
- `system_status`: System health update

### Example Event Message
```json
{
  "type": "detection",
  "timestamp": "2025-06-16T12:00:00Z",
  "camera_id": "cam-001",
  "data": {
    "detections": [
      {
        "bbox": {"x1": 100, "y1": 50, "x2": 200, "y2": 150},
        "class_name": "person",
        "confidence": 0.89
      }
    ],
    "frame_id": "frame-12345"
  }
}
```

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Spec**: `http://localhost:8000/openapi.json`

Each service also exposes its own documentation:
- VMS Service: `http://localhost:8001/docs`
- Dashboard Service: `http://localhost:8003/docs`
- Annotation Frontend: `http://localhost:8011/docs`

## SDK and Client Libraries

Official SDKs are available for:
- **Python**: `pip install surveillance-system-sdk`
- **JavaScript/Node.js**: `npm install surveillance-system-sdk`
- **React Native**: Available as part of the mobile app

### Python SDK Example
```python
from surveillance_sdk import SurveillanceClient

client = SurveillanceClient(
    base_url="http://localhost:8000",
    token="your_jwt_token"
)

# List cameras
cameras = client.cameras.list()

# Get pending annotations
examples = client.annotations.get_pending(limit=10)

# Submit annotation
result = client.annotations.submit(
    event_id="evt-12345",
    corrected_detections=[...],
    annotator_id="user-123"
)
```

This API reference provides comprehensive documentation for integrating with the AI-Powered Surveillance System. For additional examples and advanced use cases, refer to the SDK documentation and example applications.
