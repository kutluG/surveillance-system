"""
MQTT Client Module for Edge Service Event Publishing

This module provides a secure MQTT client wrapper for publishing camera events
and detection data from the edge service to the central monitoring system.
It handles both secure (TLS) and insecure connections with automatic fallback.

Key Features:
    - TLS/SSL encrypted communication with certificate validation
    - Automatic fallback to insecure connection for development/testing
    - JSON payload serialization with datetime handling
    - Quality of Service (QoS) level 1 for reliable message delivery
    - Connection management with proper error handling

Security Features:
    - Client certificate authentication
    - CA certificate validation
    - TLS 1.2 protocol enforcement
    - Secure certificate file validation

Dependencies:
    - paho-mqtt: MQTT client library for Python
    - ssl: Built-in SSL/TLS support
    - json: JSON serialization for message payloads

Environment Variables:
    - MQTT_BROKER: MQTT broker hostname or IP address
    - MQTT_PORT: Secure MQTT port (default: 8883)
    - MQTT_PORT_INSECURE: Insecure MQTT port (default: 1883)
    - MQTT_TLS_CA: Path to Certificate Authority file
    - MQTT_TLS_CERT: Path to client certificate file
    - MQTT_TLS_KEY: Path to client private key file

Author: Edge AI Service Team
Version: 1.0.0
"""
import os
import json
import ssl
import logging
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

# Configure module logger
logger = logging.getLogger(__name__)

# MQTT connection configuration from environment variables
def get_mqtt_config():
    """Get MQTT configuration from environment variables."""
    return {
        'broker': os.getenv("MQTT_BROKER", "mqtt.example.com"),
        'port': int(os.getenv("MQTT_PORT", "8883")),
        'port_insecure': int(os.getenv("MQTT_PORT_INSECURE", "1883")),
        'tls_ca': os.getenv("MQTT_TLS_CA", "/certs/ca.crt"),
        'tls_cert': os.getenv("MQTT_TLS_CERT", "/certs/client.crt"),
        'tls_key': os.getenv("MQTT_TLS_KEY", "/certs/client.key")
    }


class MQTTClient:
    """
    Secure MQTT client for publishing edge service events.
    
    This class provides a robust MQTT client implementation with TLS support,
    automatic connection management, and reliable message publishing capabilities.
    It's designed for edge devices that need to securely communicate with
    central monitoring and analytics systems.
    
    The client automatically detects available TLS certificates and configures
    the connection accordingly:
    - If certificates are available: Uses TLS 1.2 with client authentication
    - If certificates are missing: Falls back to insecure connection (dev/test only)
    
    Attributes:
        client: Paho MQTT client instance
        is_secure: Boolean indicating if TLS is enabled
        broker_host: MQTT broker hostname
        broker_port: MQTT broker port number    """
    
    def __init__(self, client_id: str):
        """
        Initialize and connect the MQTT client.
        
        Sets up the MQTT client with appropriate security configuration based on
        available certificate files. Establishes connection to the broker and
        starts the network loop for message handling.
        
        :param client_id: Unique MQTT client identifier for this edge device
        :raises ConnectionError: If connection to MQTT broker fails
        :raises ValueError: If client_id is empty or invalid
        """
        if not client_id or not isinstance(client_id, str):
            raise ValueError("client_id must be a non-empty string")
        
        # Get current MQTT configuration
        self.mqtt_config = get_mqtt_config()
            
        self.client = mqtt.Client(client_id=client_id)
        self.broker_host = self.mqtt_config['broker']
        self.is_secure = False
        
        # Configure connection callbacks for monitoring
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        
        # Determine connection type based on certificate availability
        if self._certificates_available():
            self._configure_tls_connection()
            self.broker_port = self.mqtt_config['port']
            self.is_secure = True
            logger.info("MQTT client configured for secure TLS connection")
        else:
            self._configure_insecure_connection()
            self.is_secure = False
            logger.warning("MQTT client using insecure connection - certificates not found")
        
        # Establish connection to broker
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            logger.info(f"MQTT client connected to {self.broker_host}:{self.broker_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise ConnectionError(f"MQTT connection failed: {e}")

    def _certificates_available(self) -> bool:
        """
        Check if all required TLS certificate files are available.
        
        Validates that the CA certificate, client certificate, and client private key
        files exist and are readable. This determines whether secure TLS connection
        can be established.
        
        :return: True if all certificate files are available, False otherwise
        """
        cert_files = [
            self.mqtt_config['tls_ca'], 
            self.mqtt_config['tls_cert'], 
            self.mqtt_config['tls_key']
        ]
        
        for cert_file in cert_files:
            if not os.path.exists(cert_file) or not os.path.isfile(cert_file):
                logger.debug(f"Certificate file not found: {cert_file}")
                return False
            
            # Check if file is readable
            if not os.access(cert_file, os.R_OK):
                logger.warning(f"Certificate file not readable: {cert_file}")
                return False
        
        return True

    def _configure_tls_connection(self):
        """
        Configure MQTT client for secure TLS connection.
        
        Sets up TLS encryption with client certificate authentication using:
        - TLS 1.2 protocol for security compliance
        - Client certificate for mutual authentication
        - CA certificate for broker validation
        - Strict certificate validation (not insecure)
        """
        try:
            self.client.tls_set(
                ca_certs=self.mqtt_config['tls_ca'],
                certfile=self.mqtt_config['tls_cert'],
                keyfile=self.mqtt_config['tls_key'],
                tls_version=ssl.PROTOCOL_TLSv1_2,
                ciphers=None  # Use default secure ciphers
            )
            # Enable certificate validation (secure mode)
            self.client.tls_insecure_set(False)
            logger.debug("TLS configuration completed successfully")
        except Exception as e:
            logger.error(f"TLS configuration failed: {e}")
            raise

    def _configure_insecure_connection(self):
        """
        Configure MQTT client for insecure connection (development/testing only).
        
        Sets up a plain-text MQTT connection without encryption. This should only
        be used in development or testing environments where certificates are not
        available. Production deployments should always use TLS.
        """
        self.broker_port = self.mqtt_config['port_insecure']
        logger.warning("Using insecure MQTT connection - not recommended for production")

    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback for MQTT connection events.
        
        :param client: MQTT client instance
        :param userdata: User data (unused)
        :param flags: Connection flags
        :param rc: Connection result code
        """
        if rc == 0:
            logger.info("MQTT client successfully connected")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """
        Callback for MQTT disconnection events.
        
        :param client: MQTT client instance
        :param userdata: User data (unused)
        :param rc: Disconnection result code
        """
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection (code: {rc})")
        else:
            logger.info("MQTT client disconnected gracefully")

    def _on_publish(self, client, userdata, mid):
        """
        Callback for message publish confirmation.
        
        :param client: MQTT client instance
        :param userdata: User data (unused)
        :param mid: Message ID of published message
        """
        logger.debug(f"Message published successfully (ID: {mid})")

    def publish_event(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Publish a JSON-serialized payload to the specified MQTT topic.
        
        Serializes the payload to JSON format with datetime handling and publishes
        it to the specified topic with QoS level 1 for reliable delivery.
        
        :param topic: MQTT topic to publish to (e.g., 'camera/events', 'detection/alerts')
        :param payload: JSON-serializable dictionary containing event data
        :raises ValueError: If topic is empty or payload is not serializable
        :raises Exception: If message publishing fails        """
        if not topic or not isinstance(topic, str):
            raise ValueError("Topic must be a non-empty string")
        
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a dictionary")
        
        try:
            # Serialize payload to JSON with datetime handling
            # The 'default=str' parameter handles datetime objects and other non-JSON types
            msg = json.dumps(payload, default=str, ensure_ascii=False)
            
            # Publish with QoS 1 for reliable delivery (at least once)
            result = self.client.publish(topic, msg, qos=1)
            # Check if publish was initiated successfully
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise Exception(f"Publish failed with code: {result.rc}")
            
            logger.debug(f"Published message to topic '{topic}' (size: {len(msg)} bytes)")
            
        except (TypeError, ValueError, Exception) as e:
            # Handle JSON serialization errors and other exceptions during serialization
            if "Cannot convert to string" in str(e) or isinstance(e, (TypeError, ValueError)):
                logger.error(f"JSON serialization failed: {e}")
                raise ValueError(f"Payload serialization failed: {e}")
            else:
                logger.error(f"Message publishing failed: {e}")
                raise

    def disconnect(self):
        """
        Gracefully disconnect from the MQTT broker.
        
        Stops the network loop and closes the connection to the broker.
        This should be called when the client is no longer needed.
        """
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT client disconnected successfully")
        except Exception as e:
            logger.error(f"Error during MQTT disconnect: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.disconnect()