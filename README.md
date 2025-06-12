# Surveillance System

A comprehensive, microservices-based surveillance system built with Python, featuring AI-powered video analysis, intelligent notifications, and scalable architecture.

## Overview

This surveillance system is designed as a distributed, cloud-native application that processes video streams, performs AI-based analysis, and provides intelligent alerting capabilities. The system is built using a microservices architecture with Docker containers and includes monitoring, data persistence, and real-time processing capabilities.

## Architecture

The system consists of the following microservices:

### Core Services
- **Edge Service** - Video stream processing and AI inference at the edge
- **VMS Service** - Video Management System for clip generation and storage
- **Ingest Service** - Data ingestion and initial processing pipeline
- **Prompt Service** - AI prompt management and processing
- **RAG Service** - Retrieval-Augmented Generation for intelligent responses
- **Rule Generation Service** - Dynamic rule creation and management
- **Notifier** - Multi-channel notification system
- **Agent Orchestrator** - Centralized service for orchestrating AI agents and workflows
- **Predictive Service** - Time-series forecasting for intrusion count predictions

### Infrastructure Services
- **MQTT-Kafka Bridge** - Message broker integration
- **Monitoring** - Prometheus and Grafana-based monitoring stack
- **Shared Libraries** - Common utilities, authentication, and configuration

## Features

- 🎥 Real-time video stream processing
- 🤖 AI-powered object detection and analysis
- 📊 Comprehensive monitoring and alerting
- 🔔 Multi-channel notifications (email, SMS, webhooks)
- 📈 Scalable microservices architecture
- 🐳 Containerized deployment with Docker
- 📝 Dynamic rule generation and management
- 🔍 Vector-based search and retrieval
- ⚡ High-performance edge computing
- 🎭 Agent orchestration for complex workflows
- 🔄 Comprehensive API versioning with backwards compatibility

## API Versioning

The surveillance system implements comprehensive API versioning to ensure backwards compatibility and smooth migration paths for all clients.

### Versioned API Endpoints

All API endpoints now use the `/api/v1/` prefix for version 1:

#### REST API Endpoints
```bash
# Alerts Management
GET  /api/v1/alerts           # List alerts
POST /api/v1/alerts           # Create alert
GET  /api/v1/alerts/{id}      # Get specific alert

# Contact/Support
POST /api/v1/contact          # Submit contact form

# Notifications
POST /api/v1/notify           # Send notification
GET  /api/v1/notifications    # Get notification history

# Health & Status
GET  /api/v1/health           # Service health check
GET  /api/v1/status           # System status
```

#### WebSocket Endpoints
```bash
# Real-time Events
ws://localhost:8080/ws/v1/events/{client_id}    # Event stream
ws://localhost:8080/ws/v1/alerts/{client_id}    # Alert stream
```

### Backwards Compatibility

The system maintains full backwards compatibility through automatic HTTP 301 redirects:

```bash
# Old unversioned endpoints automatically redirect to v1
curl -i http://localhost:8080/api/alerts
# HTTP/1.1 301 Moved Permanently
# Location: /api/v1/alerts
# X-API-Version-Redirect: v1

# Query parameters are preserved in redirects
curl -i http://localhost:8080/api/alerts?status=active
# HTTP/1.1 301 Moved Permanently  
# Location: /api/v1/alerts?status=active
```

### WebSocket Deprecation Notices

Legacy WebSocket endpoints send deprecation notices before graceful termination:

```javascript
// Legacy WebSocket connection
const ws = new WebSocket('ws://localhost:8080/ws/events/client123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'deprecation_notice') {
    console.warn('WebSocket endpoint deprecated:', data.message);
    // Migrate to: ws://localhost:8080/ws/v1/events/client123
  }
};

// WebSocket closes with custom code 3000 after notice
ws.onclose = (event) => {
  if (event.code === 3000) {
    console.log('Deprecated endpoint closed:', event.reason);
  }
};
```

### Client Migration Guide

#### 1. Update Base URLs
```diff
# REST API Calls
- fetch('/api/alerts')
+ fetch('/api/v1/alerts')

- fetch('/api/contact', { method: 'POST', ... })
+ fetch('/api/v1/contact', { method: 'POST', ... })
```

#### 2. Update WebSocket Connections  
```diff
# WebSocket Connections
- new WebSocket('ws://localhost:8080/ws/events/client123')
+ new WebSocket('ws://localhost:8080/ws/v1/events/client123')

- new WebSocket('ws://localhost:8080/ws/alerts/client123')  
+ new WebSocket('ws://localhost:8080/ws/v1/alerts/client123')
```

#### 3. OpenAPI Documentation
All services now expose versioned OpenAPI documentation:
```bash
# Service OpenAPI specs are available at versioned endpoints
GET /api/v1/docs          # Interactive API documentation  
GET /api/v1/openapi.json  # OpenAPI specification
```

### Benefits

- **🔄 Zero-downtime migration**: Existing clients continue working
- **📋 Clear migration path**: All endpoints clearly documented
- **🚀 Future-proof**: Ready for v2, v3, etc.
- **🔍 Easy debugging**: Version headers help identify client versions
- **📈 Gradual adoption**: Teams can migrate at their own pace

## Audit Logging

The surveillance system implements immutable WORM (Write Once, Read Many) audit logging to ensure compliance and tamper-proof audit trails. All structured audit logs are automatically stored in AWS S3 with Object Lock enabled.

### Overview

All application logs at INFO level and above are automatically:
- ✅ Written to console (stdout) for immediate visibility
- ✅ Uploaded to AWS S3 with Object Lock for immutable storage
- ✅ Stored with 7-year retention for compliance requirements
- ✅ Organized with date-based hierarchy for easy retrieval

### Required Environment Variables

The following environment variables must be configured for WORM audit logging:

| Variable | Purpose | Example | Required |
|----------|---------|---------|----------|
| `AWS_S3_BUCKET` | S3 bucket name for audit logs | `surveillance-audit-logs` | ✅ Yes |
| `AWS_REGION` | AWS region of the S3 bucket | `us-east-1` | ✅ Yes |
| `AWS_S3_PREFIX` | S3 prefix for organizing logs | `audit-logs` | ❌ Optional |
| `AWS_ACCESS_KEY_ID` | AWS access key (prefer IAM roles) | `AKIA...` | ❌ Optional |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (prefer IAM roles) | `xxx...` | ❌ Optional |

### Prerequisites

#### 1. S3 Bucket Configuration

The S3 bucket **MUST** have Object Lock enabled in **Governance mode**:

```bash
# Create bucket with Object Lock enabled
aws s3api create-bucket \
  --bucket surveillance-audit-logs \
  --region us-east-1 \
  --object-lock-enabled-for-bucket

# Configure default Object Lock retention (7 years)
aws s3api put-object-lock-configuration \
  --bucket surveillance-audit-logs \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "GOVERNANCE",
        "Years": 7
      }
    }
  }'
```

#### 2. IAM Permissions

The application requires the following S3 permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectLegalHold",
        "s3:PutObjectRetention"
      ],
      "Resource": "arn:aws:s3:::surveillance-audit-logs/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketObjectLockConfiguration"
      ],
      "Resource": "arn:aws:s3:::surveillance-audit-logs"
    }
  ]
}
```

### Log Format

Audit logs are stored in structured JSON format with the following schema:

```json
{
  "timestamp": "2025-06-12T13:30:33.025676Z",
  "level": "INFO",
  "message": "User login successful",
  "service_name": "api_gateway",
  "request_id": "req-12345-abcde",
  "user_id": "user@example.com",
  "action": "user_login",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "custom_context": "additional_fields"
}
```

### S3 Storage Structure

Logs are organized in S3 with the following hierarchy:

```
s3://surveillance-audit-logs/
└── audit-logs/                    # AWS_S3_PREFIX
    └── 2025/                      # Year
        └── 06/                    # Month
            └── 12/                # Day
                ├── req-abc-uuid1.json
                ├── req-def-uuid2.json
                └── req-ghi-uuid3.json
```

### Usage Example

Enable WORM audit logging in your service:

```python
from shared.logging_config import configure_logging

# Configure logging with WORM enabled
logger = configure_logging(
    service_name='your_service',
    log_level='INFO',
    enable_worm=True  # Enables WORM audit logging
)

# Log audit events with context
logger.info(
    "User performed sensitive action",
    extra={
        'service_name': 'auth_service',
        'request_id': 'req-12345-abcde',
        'user_id': 'user@example.com',
        'action': 'password_change',
        'ip_address': '192.168.1.100',
        'success': True
    }
)
```

### Error Handling

The WORM logging system includes robust error handling:

- **Network Outages**: Logs are queued locally and retried when connectivity returns
- **S3 Failures**: Failed uploads are retried with exponential backoff
- **Object Lock Unavailable**: System falls back to standard S3 upload with metadata flag
- **Service Continuity**: Application continues running even if audit logging fails

### Monitoring

Monitor WORM audit logging through:

- **Console Logs**: WORM handler status messages appear in service logs
- **Local Error Logs**: Failed uploads are logged locally for debugging
- **CloudWatch Metrics**: S3 upload metrics and error rates (if configured)
- **Health Checks**: Services report WORM handler status in health endpoints

### Compliance Benefits

- **🔒 Tamper-Proof**: Object Lock prevents deletion or modification
- **📅 Long-term Retention**: 7-year retention meets regulatory requirements
- **🔍 Audit Trail**: Complete forensic audit trail for security events
- **📋 Structured Format**: Consistent JSON schema for automated analysis
- **⚡ Real-time**: Immediate upload ensures minimal data loss
- **🛡️ High Availability**: AWS S3 provides 99.999999999% durability

## Compliance APIs

The surveillance system provides secure, auditable APIs for GDPR/KVKK compliance, allowing data subjects to request deletion of their personal data (face recognition data) in accordance with privacy regulations.

### Data Subject Request Service

The Data Subject Request Service provides a secure endpoint for handling "right to be forgotten" requests by face hash ID, automating the purge across the database and storage systems.

#### Authentication & Authorization

- **JWT Authentication**: All requests must include a valid JWT token
- **Role-Based Access**: Requires `compliance_officer` role/scope
- **Audit Logging**: All deletion requests are logged via WORM audit system

#### API Endpoint

**POST** `/data-subject/delete`

Deletes all data associated with a face hash ID including:
- All events containing the face_hash_id in their privacy metadata
- All video segments associated with those events  
- All video files referenced by those segments (from S3 or local storage)

##### Request Format
```json
{
  "face_hash_id": "a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd"
}
```

##### Response Format
```json
{
  "status": "deleted",
  "events": 5,
  "files": 3,
  "face_hash_id": "a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",
  "timestamp": "2025-06-12T10:30:45Z"
}
```

##### Status Codes
- **200 OK**: Successful deletion (includes cases where no data was found)
- **422 Unprocessable Entity**: Invalid face_hash_id format
- **403 Forbidden**: Insufficient permissions (missing compliance_officer role)
- **500 Internal Server Error**: Database or storage errors

#### Usage Example

```bash
# Delete all data for a specific face hash
curl -X POST "http://localhost:8011/data-subject/delete" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "face_hash_id": "a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd"
  }'
```

#### Face Hash ID Format

- **Length**: Exactly 64 characters
- **Format**: Hexadecimal string (0-9, a-f, A-F)
- **Example**: `a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd`
- **Validation**: Regex pattern `^[a-fA-F0-9]{64}$`

#### Required JWT Scope

The JWT token must include the `compliance_officer` scope:

```json
{
  "sub": "compliance@surveillance.com",
  "scopes": ["compliance_officer"],
  "iat": 1718195445,
  "exp": 1718199045
}
```

#### Service Configuration

Configure the service using environment variables:

| Variable | Purpose | Example | Required |
|----------|---------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` | ✅ Yes |
| `STORAGE_PATH` | Storage location (S3 or local) | `s3://bucket-name` or `/data/clips` | ✅ Yes |
| `AWS_REGION` | AWS region for S3 operations | `us-east-1` | ❌ S3 only |
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIA...` | ❌ S3 only |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `xxx...` | ❌ S3 only |

#### Operational Features

- **🔄 Transactional**: All operations within a database transaction - rollback on any failure
- **📁 Multi-Storage**: Supports both S3 and local filesystem storage
- **🔍 Audit Trail**: Complete WORM audit logging for compliance
- **⚡ Efficient**: Batch operations for optimal performance
- **🛡️ Secure**: Role-based access control with JWT authentication
- **📋 Structured**: JSON request/response format with validation

#### Health Check

**GET** `/health`

Returns service health status:

```json
{
  "status": "healthy",
  "service": "data_subject_service",
  "timestamp": "2025-06-12T10:30:45Z"
}
```

#### Docker Deployment

The service runs on port 8011 and is included in the main docker-compose.yml:

```bash
# Start the compliance service
docker-compose up data_subject_service

# Check service health
curl http://localhost:8011/health
```
