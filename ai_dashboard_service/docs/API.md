# AI Dashboard Service API Documentation

This document provides comprehensive API documentation for the AI Dashboard Service, including endpoints, request/response schemas, and usage examples.

## Base URL

```
http://localhost:8004/api/v1
```

## Authentication

Currently, the service does not require authentication for API access. In production environments, consider implementing API key authentication or OAuth 2.0.

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error description",
  "status_code": 400
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `404`: Not Found  
- `422`: Validation Error
- `500`: Internal Server Error

## Endpoints

### Health Check

#### GET /health

Check service health and availability.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-19T10:30:00.000Z"
}
```

**Example:**
```bash
curl -X GET http://localhost:8004/health
```

---

### Analytics

#### POST /api/v1/analytics/trends

Analyze trends in surveillance data using statistical methods and pattern recognition.

**Request Body:**
```json
{
  "data_sources": ["cameras", "sensors", "logs"],
  "time_range": "last_7_days",
  "analytics_type": "trend_analysis",
  "metrics": ["object_count", "motion_events", "alert_frequency"],
  "filters": {
    "location": "building_a",
    "camera_ids": ["cam_001", "cam_002"]
  }
}
```

**Response:**
```json
{
  "trends": [
    {
      "id": "trend_001",
      "type": "trend_analysis",
      "title": "Motion Events Trend",
      "description": "Increasing motion events detected during evening hours",
      "confidence": 0.85,
      "timestamp": "2025-06-19T10:30:00.000Z",
      "data": {
        "metric": "motion_events",
        "trend_direction": "increasing",
        "percentage_change": 15.3,
        "time_periods": [
          {"period": "2025-06-12", "value": 120},
          {"period": "2025-06-13", "value": 135},
          {"period": "2025-06-14", "value": 142}
        ]
      },
      "recommendations": [
        "Investigate increased activity during evening hours",
        "Consider adjusting sensor sensitivity"
      ],
      "impact_level": "medium"
    }
  ],
  "analysis_timestamp": "2025-06-19T10:30:00.000Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/api/v1/analytics/trends \
  -H "Content-Type: application/json" \
  -d '{
    "data_sources": ["cameras"],
    "time_range": "last_24_hours",
    "analytics_type": "trend_analysis",
    "metrics": ["object_count"]
  }'
```

#### POST /api/v1/analytics/anomalies

Detect anomalies and unusual patterns in surveillance data.

**Request Body:**
```json
{
  "data_sources": ["cameras", "sensors"],
  "time_range": "last_24_hours",
  "analytics_type": "anomaly_detection",
  "metrics": ["motion_events", "object_count"],
  "threshold": 2.0,
  "filters": {
    "location": "parking_lot"
  }
}
```

**Response:**
```json
{
  "anomalies": [
    {
      "id": "anomaly_001",
      "type": "anomaly_detection",
      "title": "Unusual Activity Spike",
      "description": "Abnormal increase in motion events at 3:00 AM",
      "confidence": 0.92,
      "timestamp": "2025-06-19T03:00:00.000Z",
      "data": {
        "metric": "motion_events",
        "expected_value": 5,
        "actual_value": 45,
        "deviation_score": 3.2,
        "severity": "high"
      },
      "recommendations": [
        "Review security footage for the specified time",
        "Check sensor calibration"
      ],
      "impact_level": "high"
    }
  ],
  "detection_timestamp": "2025-06-19T10:30:00.000Z",
  "total_anomalies": 1
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/api/v1/analytics/anomalies \
  -H "Content-Type: application/json" \
  -d '{
    "data_sources": ["cameras"],
    "time_range": "last_24_hours",
    "analytics_type": "anomaly_detection",
    "threshold": 2.0
  }'
```

---

### Predictions

#### POST /api/v1/predictions

Generate predictive analytics for various surveillance scenarios.

**Request Body:**
```json
{
  "prediction_type": "security_threat",
  "time_horizon": "next_24_hours",
  "data_sources": ["cameras", "sensors"],
  "parameters": {
    "confidence_threshold": 0.7,
    "include_recommendations": true
  }
}
```

**Response:**
```json
{
  "message": "Predictions endpoint available - requires predictive service refactoring",
  "prediction_type": "security_threat",
  "generated_at": "2025-06-19T10:30:00.000Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/api/v1/predictions \
  -H "Content-Type: application/json" \
  -d '{
    "prediction_type": "equipment_failure",
    "time_horizon": "next_week"
  }'
```

---

### Reports

#### POST /api/v1/reports/generate

Generate intelligent surveillance reports with AI-powered insights.

**Request Body:**
```json
{
  "report_type": "security_summary",
  "time_range": "last_week",
  "include_analytics": true,
  "include_recommendations": true,
  "format": "json",
  "filters": {
    "locations": ["building_a", "parking_lot"],
    "severity_levels": ["medium", "high", "critical"]
  }
}
```

**Response:**
```json
{
  "message": "Report generation endpoint available - requires report service refactoring",
  "report_type": "security_summary",
  "generated_at": "2025-06-19T10:30:00.000Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "daily_summary",
    "time_range": "yesterday",
    "format": "json"
  }'
```

#### GET /api/v1/reports/{report_id}

Retrieve a previously generated report by its ID.

**Path Parameters:**
- `report_id` (string): Unique identifier of the report

**Response:**
```json
{
  "id": "report_12345",
  "type": "security_summary",
  "generated_at": "2025-06-19T10:30:00.000Z",
  "content": {
    "summary": "Security report for June 18, 2025",
    "incidents": 3,
    "recommendations": ["Increase patrol frequency", "Update camera positioning"]
  },
  "status": "completed"
}
```

**Example:**
```bash
curl -X GET http://localhost:8004/api/v1/reports/report_12345
```

---

### Real-time Insights

#### GET /api/v1/insights/realtime

Get real-time AI-powered insights about current surveillance status.

**Query Parameters:**
- `include_predictions` (boolean, optional): Include predictive insights
- `time_window` (string, optional): Time window for analysis (default: "last_hour")

**Response:**
```json
{
  "insights": [
    {
      "type": "alert",
      "title": "High Activity Detected",
      "description": "Unusual activity patterns in parking area",
      "confidence": 0.88,
      "priority": "high",
      "timestamp": "2025-06-19T10:30:00.000Z"
    }
  ],
  "summary": {
    "active_alerts": 2,
    "system_health": "good",
    "ai_confidence": 0.92
  },
  "generated_at": "2025-06-19T10:30:00.000Z"
}
```

**Example:**
```bash
curl -X GET "http://localhost:8004/api/v1/insights/realtime?include_predictions=true"
```

---

### Dashboard Widgets

#### POST /api/v1/widgets/create

Create a new dashboard widget with custom configuration.

**Request Body:**
```json
{
  "widget_type": "analytics_chart",
  "title": "Motion Events Trend",
  "description": "24-hour motion events monitoring",
  "configuration": {
    "chart_type": "line",
    "metrics": ["motion_events"],
    "time_range": "24h",
    "refresh_interval": 300
  },
  "filters": {
    "location": "main_entrance",
    "camera_ids": ["cam_001", "cam_002"]
  }
}
```

**Response:**
```json
{
  "widget_id": "widget_12345",
  "widget": {
    "id": "widget_12345",
    "type": "analytics_chart",
    "title": "Motion Events Trend",
    "description": "24-hour motion events monitoring",
    "configuration": {
      "chart_type": "line",
      "metrics": ["motion_events"],
      "time_range": "24h",
      "refresh_interval": 300
    },
    "data_source": "analytics_api",
    "refresh_interval": 30,
    "filters": {
      "location": "main_entrance",
      "camera_ids": ["cam_001", "cam_002"]
    },
    "layout": {"x": 0, "y": 0, "w": 4, "h": 3}
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/api/v1/widgets/create \
  -H "Content-Type: application/json" \
  -d '{
    "widget_type": "alert_summary",
    "title": "Active Alerts",
    "description": "Current system alerts"
  }'
```

#### GET /api/v1/widgets

List all configured dashboard widgets.

**Response:**
```json
{
  "widgets": [
    {
      "id": "widget_12345",
      "type": "analytics_chart",
      "title": "Motion Events Trend",
      "created_at": "2025-06-19T10:30:00.000Z",
      "last_updated": "2025-06-19T10:30:00.000Z"
    }
  ]
}
```

**Example:**
```bash
curl -X GET http://localhost:8004/api/v1/widgets
```

---

### Dashboard Summary

#### GET /api/v1/dashboard/summary

Get an AI-powered summary of current dashboard status and key insights.

**Response:**
```json
{
  "summary": {
    "overall_status": "operational",
    "key_insights": [
      "Motion activity 15% above normal during evening hours",
      "All cameras operational and connected",
      "2 minor alerts requiring attention"
    ],
    "recommendations": [
      "Review evening patrol schedules",
      "Investigate parking lot sensor calibration"
    ],
    "metrics": {
      "active_cameras": 24,
      "total_alerts": 2,
      "system_uptime": "99.8%"
    }
  },
  "generated_at": "2025-06-19T10:30:00.000Z",
  "ai_confidence": 0.91
}
```

**Example:**
```bash
curl -X GET http://localhost:8004/api/v1/dashboard/summary
```

## Data Schemas

### Common Enums

**AnalyticsType:**
- `trend_analysis`
- `anomaly_detection`
- `pattern_recognition`
- `comparative_analysis`

**TimeRange:**
- `last_hour`
- `last_24_hours`
- `last_7_days`
- `last_30_days`
- `custom`

**WidgetType:**
- `analytics_chart`
- `alert_summary`  
- `kpi_metric`
- `trend_visualization`
- `anomaly_heatmap`

**PredictionType:**
- `security_threat`
- `equipment_failure`
- `traffic_pattern`
- `occupancy_level`

### Request Schemas

All requests should include proper `Content-Type: application/json` headers and valid JSON payloads matching the schemas shown in the endpoint documentation above.

### Response Schemas

All successful responses return JSON with consistent structure. Error responses follow the format shown in the Error Handling section.

## Rate Limiting

The service implements rate limiting with the following default limits:
- 100 requests per minute per IP address
- Rate limiting can be configured via `RATE_LIMIT_REQUESTS` environment variable
- Rate limiting can be disabled by setting `RATE_LIMIT_ENABLED=false`

When rate limits are exceeded, the service returns:
```json
{
  "detail": "Rate limit exceeded",
  "status_code": 429
}
```

## Interactive Documentation

For interactive API exploration:
- **Swagger UI**: http://localhost:8004/docs
- **ReDoc**: http://localhost:8004/redoc

These interfaces provide:
- Interactive request/response testing
- Complete schema documentation
- Authentication testing (when enabled)
- Response format examples
