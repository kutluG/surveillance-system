"""
MQTT client wrapper for publishing camera events.
"""
import os
import json
import ssl
from typing import Any, Dict
import paho.mqtt.client as mqtt

MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt.example.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_TLS_CA = os.getenv("MQTT_TLS_CA", "/certs/ca.crt")
MQTT_TLS_CERT = os.getenv("MQTT_TLS_CERT", "/certs/client.crt")
MQTT_TLS_KEY = os.getenv("MQTT_TLS_KEY", "/certs/client.key")

class MQTTClient:
    def __init__(self, client_id: str):
        """
        Initialize and connect the MQTT client using TLS.
        :param client_id: Unique MQTT client ID.        """
        self.client = mqtt.Client(client_id=client_id)
        
        # Only configure TLS if certificate files exist
        if (os.path.exists(MQTT_TLS_CA) and 
            os.path.exists(MQTT_TLS_CERT) and 
            os.path.exists(MQTT_TLS_KEY)):
            self.client.tls_set(
                ca_certs=MQTT_TLS_CA,
                certfile=MQTT_TLS_CERT,
                keyfile=MQTT_TLS_KEY,
                tls_version=ssl.PROTOCOL_TLSv1_2,
            )
            self.client.tls_insecure_set(False)
            mqtt_port = MQTT_PORT
        else:
            # Use non-secure port for testing without certificates
            mqtt_port = int(os.getenv("MQTT_PORT_INSECURE", "1883"))
            
        self.client.connect(MQTT_BROKER, mqtt_port)
        self.client.loop_start()

    def publish_event(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Publish a JSON-serialized payload to the given topic.
        :param topic: MQTT topic to publish to.
        :param payload: JSON-serializable dictionary.
        """
        msg = json.dumps(payload, default=str)
        self.client.publish(topic, msg, qos=1)