"""
MQTT → Kafka bridge service: subscribes to camera event topics on MQTT,
forwards messages to a Kafka topic, and exposes health/metrics endpoints.
"""
import os
import ssl
import json
from typing import Optional

import paho.mqtt.client as mqtt
from confluent_kafka import Producer
from fastapi import FastAPI, HTTPException
from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.middleware import add_rate_limiting

# Configure logging first
logger = configure_logging("mqtt_kafka_bridge")

app = FastAPI(title="MQTT-Kafka Bridge")

# Add audit middleware
add_audit_middleware(app, service_name="mqtt_kafka_bridge")
instrument_app(app, service_name="mqtt_kafka_bridge")

# Add rate limiting middleware
add_rate_limiting(app, service_name="mqtt_kafka_bridge")

# MQTT configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt.example.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_TLS_CA = os.getenv("MQTT_TLS_CA", "/certs/ca.crt")
MQTT_TLS_CERT = os.getenv("MQTT_TLS_CERT", "/certs/client.crt")
MQTT_TLS_KEY = os.getenv("MQTT_TLS_KEY", "/certs/client.key")
MQTT_TOPIC_SUB = os.getenv("MQTT_TOPIC_SUB", "camera/events/#")

# Kafka configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "camera.events")

bridge_client: Optional[mqtt.Client] = None
kafka_producer: Optional[Producer] = None

def delivery_report(err, msg):
    if err:
        logger.error("Kafka delivery failed", error=str(err), topic=msg.topic())
    else:
        logger.debug("Kafka message delivered", topic=msg.topic(), partition=msg.partition())

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker", broker=MQTT_BROKER, port=MQTT_PORT)
        client.subscribe(MQTT_TOPIC_SUB, qos=1)
        logger.info("Subscribed to MQTT topic", topic=MQTT_TOPIC_SUB)
    else:
        logger.error("Failed to connect to MQTT", rc=rc)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        # Validate JSON
        data = json.loads(payload)
        # Forward raw JSON string to Kafka
        kafka_producer.produce(KAFKA_TOPIC, payload.encode("utf-8"), callback=delivery_report)
        kafka_producer.poll(0)
        logger.info("Bridged MQTT→Kafka", mqtt_topic=msg.topic, kafka_topic=KAFKA_TOPIC)
    except json.JSONDecodeError:
        logger.error("Invalid JSON on MQTT", topic=msg.topic, payload=payload)

@app.on_event("startup")
async def startup_event():
    global bridge_client, kafka_producer
    logger.info("Starting MQTT-Kafka bridge")
    # Kafka producer
    kafka_producer = Producer({"bootstrap.servers": KAFKA_BROKER})
    # MQTT client
    bridge_client = mqtt.Client()
    
    # Only configure TLS if certificate files exist
    if (os.path.exists(MQTT_TLS_CA) and 
        os.path.exists(MQTT_TLS_CERT) and 
        os.path.exists(MQTT_TLS_KEY)):
        logger.info("Configuring MQTT with TLS")
        bridge_client.tls_set(
            ca_certs=MQTT_TLS_CA,
            certfile=MQTT_TLS_CERT,
            keyfile=MQTT_TLS_KEY,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )
        bridge_client.tls_insecure_set(False)
    else:
        logger.warning("TLS certificates not found - connecting without TLS")
        # Use non-secure port for testing
        global MQTT_PORT
        MQTT_PORT = int(os.getenv("MQTT_PORT_INSECURE", "1883"))
    
    bridge_client.on_connect = on_connect
    bridge_client.on_message = on_message
    bridge_client.connect(MQTT_BROKER, MQTT_PORT)
    bridge_client.loop_start()

@app.on_event("shutdown")
async def shutdown_event():
    if bridge_client:
        bridge_client.loop_stop()
        bridge_client.disconnect()
    if kafka_producer:
        kafka_producer.flush()
    logger.info("MQTT-Kafka bridge shutdown complete")

@app.get("/health")
async def health():
    """
    Health check: ensure both MQTT and Kafka clients are initialized.
    """
    if bridge_client is None or kafka_producer is None:
        raise HTTPException(status_code=503, detail="bridge not initialized")
    return {"status": "ok"}
