```markdown
# Edge AI Service

This service captures frames from a camera, runs object detection and activity recognition models, and publishes JSON events to an MQTT broker.

## Requirements

- Python 3.9+
- Docker & Docker Compose

## Setup

1. Copy `.env.example` to `.env` and fill in:
   ```bash
   CAMERA_ID=camera-01
   CAPTURE_DEVICE=0
   MODEL_DIR=/models
   TARGET_RESOLUTION=224,224
   MQTT_BROKER=mqtt.example.com
   MQTT_PORT=8883
   MQTT_TLS_CA=/certs/ca.crt
   MQTT_TLS_CERT=/certs/client.crt
   MQTT_TLS_KEY=/certs/client.key
   ```

2. Build & run with Docker Compose:
   ```bash
   docker-compose up --build edge_service
   ```

## Endpoints

- POST `/capture` &rarr; Schedule one frame capture & inference
- GET `/health` &rarr; Health check
- POST `/ota` &rarr; OTA model update (stub)

## Testing

```bash
cd edge_service
pytest -q
```