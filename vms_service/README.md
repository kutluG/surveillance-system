```markdown
# VMS (Video Management System) Service

Handles video clip generation, storage, and retrieval for surveillance events.

## Features

- **Clip Generation**: Create video clips around event timestamps
- **Multiple Storage Backends**: Support for AWS S3 and local filesystem
- **Clip Management**: List, retrieve, and delete video clips
- **Automatic Cleanup**: Remove old clips based on retention policies
- **Presigned URLs**: Secure, time-limited access to video clips

## Configuration

Copy and edit `.env`:

```bash
# Storage Configuration
VIDEO_STORAGE_TYPE=s3  # or "local"

# S3 Storage (if using S3)
S3_BUCKET_NAME=surveillance-clips
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Local Storage (if using local)
LOCAL_STORAGE_PATH=/data/clips
CLIP_BASE_URL=http://localhost:8000/clips

# Clip Generation Settings
CLIP_DURATION_SECONDS=30
PRE_EVENT_BUFFER_SECONDS=10
POST_EVENT_BUFFER_SECONDS=20
CLIP_FPS=15
CLIP_RESOLUTION=640,480

# Camera URLs (pattern: CAMERA_{ID}_URL)
CAMERA_CAM01_URL=rtsp://admin:password@camera-01:554/stream
CAMERA_CAM02_URL=rtsp://admin:password@camera-02:554/stream
```

## Build & Run

```bash
docker-compose up --build vms_service
```

## Endpoints

- POST `/clips/generate` - Generate video clip for an event
- GET `/clips/{event_id}` - Get video clip (redirect to actual URL)
- GET `/clips/{event_id}/url` - Get direct clip URL
- GET `/clips` - List clips with optional filters
- DELETE `/clips/{event_id}` - Delete a clip
- POST `/clips/cleanup` - Clean up old clips
- GET `/health` - Health check

## Example Usage

Generate a clip for an event:
```bash
curl -X POST http://localhost:8000/clips/generate \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "id": "event-123",
      "camera_id": "cam01",
      "event_type": "detection",
      "timestamp": "2025-05-31T10:30:00Z"
    }
  }'
```

List clips for a specific camera:
```bash
curl "http://localhost:8000/clips?camera_id=cam01&start_date=2025-05-31T00:00:00Z"
```

Get a clip URL:
```bash
curl "http://localhost:8000/clips/event-123/url?expiry_minutes=120"
```

Clean up clips older than 7 days:
```bash
curl -X POST "http://localhost:8000/clips/cleanup?days_old=7"
```

## Storage Backends

### AWS S3
- Scalable cloud storage
- Presigned URLs for secure access
- Metadata stored as S3 object metadata
- Automatic bucket lifecycle policies supported

### Local Filesystem
- Simple local storage for development
- Metadata stored as companion JSON files
- Direct HTTP serving of clips
- Manual cleanup required

## Video Clip Format

- **Format**: MP4 (H.264)
- **Duration**: Configurable (default 30 seconds)
- **Pre/Post Buffers**: Configurable timing around events
- **Resolution**: Configurable (default 640x480)
- **Frame Rate**: Configurable (default 15 FPS)
```