```markdown
# MQTT → Kafka Bridge

This service subscribes to camera event topics on an MQTT broker and republishes
them to a Kafka topic for downstream ingestion.

## Configuration

Copy and edit `.env`:

```bash
MQTT_BROKER=mqtt.example.com
MQTT_PORT=8883
MQTT_TLS_CA=/certs/ca.crt
MQTT_TLS_CERT=/certs/client.crt
MQTT_TLS_KEY=/certs/client.key
MQTT_TOPIC_SUB=camera/events/#
KAFKA_BROKER=kafka:9092
KAFKA_TOPIC=camera.events
```

## Build & Run

```bash
docker-compose up --build mqtt_kafka_bridge
```

## Endpoints

- GET `/health` – returns `{"status":"ok"}` when bridge is up.
- GET `/metrics` – Prometheus metrics.
```