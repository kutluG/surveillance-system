"""
Integration Tests for Edge Service MQTT Client

This test suite verifies that the MQTT client correctly publishes JSON events to 
the configured MQTT broker and handles reconnection logic under failure scenarios.

Tests included:
1. Local MQTT broker fixture using subprocess/Docker
2. Message publishing and subscription verification
3. Reconnection logic testing
4. Error handling for invalid payloads
5. Connection lifecycle management

Dependencies:
- pytest-mosquitto or subprocess mosquitto
- testcontainers-python (fallback)
- paho-mqtt for test subscriber
"""
import os
import sys
import json
import time
import threading
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import paho.mqtt.client as mqtt

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mqtt_client import MQTTClient


class MQTTTestSubscriber:
    """
    Helper class to subscribe to MQTT topics and collect messages for verification.
    """
    
    def __init__(self, broker_host: str, broker_port: int):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.received_messages: List[Dict[str, Any]] = []
        self.connected = False
        self.client = mqtt.Client(client_id="test_subscriber")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
    def _on_connect(self, client, userdata, flags, rc):
        """Connection callback."""
        if rc == 0:
            self.connected = True
            print(f"Test subscriber connected to {self.broker_host}:{self.broker_port}")
        else:
            print(f"Test subscriber connection failed with code {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Message received callback."""
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            message_data = {
                "topic": msg.topic,
                "payload": payload,
                "qos": msg.qos,
                "retain": msg.retain,
                "timestamp": datetime.now()
            }
            self.received_messages.append(message_data)
            print(f"Test subscriber received: {msg.topic} -> {payload}")
        except json.JSONDecodeError as e:
            print(f"Failed to decode message: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Disconnection callback."""
        self.connected = False
        print(f"Test subscriber disconnected (code: {rc})")
    
    def connect(self) -> bool:
        """Connect to the broker."""
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=10)
            self.client.loop_start()
            
            # Wait for connection
            start_time = time.time()
            while not self.connected and time.time() - start_time < 5:
                time.sleep(0.1)
            
            return self.connected
        except Exception as e:
            print(f"Test subscriber connection error: {e}")
            return False
    
    def subscribe(self, topic: str, qos: int = 0):
        """Subscribe to a topic."""
        if self.connected:
            result = self.client.subscribe(topic, qos)
            print(f"Subscribed to {topic} with result: {result}")
    
    def disconnect(self):
        """Disconnect from the broker."""
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
    
    def clear_messages(self):
        """Clear received messages."""
        self.received_messages.clear()
    
    def wait_for_messages(self, count: int, timeout: float = 10.0) -> bool:
        """Wait for a specific number of messages."""
        start_time = time.time()
        while len(self.received_messages) < count and time.time() - start_time < timeout:
            time.sleep(0.1)
        return len(self.received_messages) >= count


class TestMQTTClientIntegration:
    """
    Integration tests for MQTT client functionality.
    """
    
    def test_mqtt_client_connection_insecure(self, mqtt_config, mock_certificates_unavailable):
        """
        Test MQTT client can connect to broker in insecure mode.
        """
        with patch.dict(os.environ, mqtt_config):
            client = MQTTClient(client_id="test_client_insecure")
            
            # Verify connection attributes
            assert client.is_secure is False
            assert client.broker_host == mqtt_config["MQTT_BROKER"]
            assert client.broker_port == int(mqtt_config["MQTT_PORT_INSECURE"])
            
            # Clean up
            client.disconnect()
    
    def test_publish_detection_event(self, mqtt_config, mock_certificates_unavailable, 
                                   sample_detection_event, mosquitto_broker):
        """
        Test publishing a detection event and verifying it's received.
        """
        topic = "edge/detections"
        
        # Set up test subscriber
        subscriber = TestSubscriber(
            broker_host=mosquitto_broker["host"],
            broker_port=mosquitto_broker["port"]
        )
        
        try:
            # Connect subscriber and subscribe to topic
            assert subscriber.connect(), "Test subscriber failed to connect"
            subscriber.subscribe(topic, qos=1)
            
            # Give subscriber time to establish subscription
            time.sleep(1)
            
            # Create MQTT client and publish event
            with patch.dict(os.environ, mqtt_config):
                client = MQTTClient(client_id="test_publisher")
                
                try:
                    client.publish_event(topic, sample_detection_event)
                    
                    # Wait for message to be received
                    assert subscriber.wait_for_messages(1, timeout=5), \
                        "Message not received within timeout"
                    
                    # Verify message content
                    received = subscriber.received_messages[0]
                    assert received["topic"] == topic
                    assert received["payload"]["camera_id"] == sample_detection_event["camera_id"]
                    assert received["payload"]["event_type"] == sample_detection_event["event_type"]
                    assert received["qos"] == 1  # Should be QoS 1 as specified in client
                    
                finally:
                    client.disconnect()
                    
        finally:
            subscriber.disconnect()
    
    def test_publish_multiple_events(self, mqtt_config, mock_certificates_unavailable, 
                                   mosquitto_broker):
        """
        Test publishing multiple events in sequence.
        """
        topic = "edge/detections"
        num_messages = 5
        
        # Set up test subscriber
        subscriber = TestSubscriber(
            broker_host=mosquitto_broker["host"],
            broker_port=mosquitto_broker["port"]
        )
        
        try:
            assert subscriber.connect(), "Test subscriber failed to connect"
            subscriber.subscribe(topic, qos=1)
            time.sleep(1)
            
            # Create MQTT client and publish multiple events
            with patch.dict(os.environ, mqtt_config):
                client = MQTTClient(client_id="test_multi_publisher")
                
                try:
                    for i in range(num_messages):
                        event = {
                            "camera_id": f"cam_{i}",
                            "timestamp": datetime.now().isoformat(),
                            "message_id": i,
                            "event_type": "test"
                        }
                        client.publish_event(topic, event)
                    
                    # Wait for all messages
                    assert subscriber.wait_for_messages(num_messages, timeout=10), \
                        f"Expected {num_messages} messages, got {len(subscriber.received_messages)}"
                    
                    # Verify all messages received with correct content
                    assert len(subscriber.received_messages) == num_messages
                    
                    for i, received in enumerate(subscriber.received_messages):
                        assert received["payload"]["message_id"] == i
                        assert received["payload"]["camera_id"] == f"cam_{i}"
                        
                finally:
                    client.disconnect()
                    
        finally:
            subscriber.disconnect()
    
    def test_invalid_payload_handling(self, mqtt_config, mock_certificates_unavailable):
        """
        Test error handling for invalid payloads.
        """
        with patch.dict(os.environ, mqtt_config):
            client = MQTTClient(client_id="test_invalid_payload")
            
            try:
                # Test empty topic
                with pytest.raises(ValueError, match="Topic must be a non-empty string"):
                    client.publish_event("", {"test": "data"})
                
                # Test None topic
                with pytest.raises(ValueError, match="Topic must be a non-empty string"):
                    client.publish_event(None, {"test": "data"})
                
                # Test non-dict payload
                with pytest.raises(ValueError, match="Payload must be a dictionary"):
                    client.publish_event("test/topic", "not a dict")
                
                # Test non-serializable payload
                class NonSerializable:
                    def __init__(self):
                        self.circular_ref = self
                
                non_serializable_payload = {"obj": NonSerializable()}
                
                with pytest.raises(ValueError, match="Payload serialization failed"):
                    client.publish_event("test/topic", non_serializable_payload)
                    
            finally:
                client.disconnect()
    
    def test_json_serialization_with_datetime(self, mqtt_config, mock_certificates_unavailable,
                                            mosquitto_broker):
        """
        Test JSON serialization handles datetime objects correctly.
        """
        topic = "edge/datetime_test"
        
        # Set up test subscriber
        subscriber = TestSubscriber(
            broker_host=mosquitto_broker["host"],
            broker_port=mosquitto_broker["port"]
        )
        
        try:
            assert subscriber.connect(), "Test subscriber failed to connect"
            subscriber.subscribe(topic, qos=1)
            time.sleep(1)
            
            # Create event with datetime object
            event_with_datetime = {
                "timestamp": datetime.now(),
                "date_created": datetime(2023, 12, 25, 10, 30, 45),
                "camera_id": "cam_datetime_test",
                "event_type": "datetime_test"
            }
            
            with patch.dict(os.environ, mqtt_config):
                client = MQTTClient(client_id="test_datetime_publisher")
                
                try:
                    client.publish_event(topic, event_with_datetime)
                    
                    # Wait for message
                    assert subscriber.wait_for_messages(1, timeout=5), \
                        "Message not received within timeout"
                    
                    # Verify datetime was serialized as string
                    received = subscriber.received_messages[0]
                    payload = received["payload"]
                    
                    assert "timestamp" in payload
                    assert "date_created" in payload
                    assert isinstance(payload["timestamp"], str)
                    assert isinstance(payload["date_created"], str)
                    assert payload["camera_id"] == "cam_datetime_test"
                    
                finally:
                    client.disconnect()
                    
        finally:
            subscriber.disconnect()
    
    def test_connection_with_invalid_broker(self, mock_certificates_unavailable):
        """
        Test client behavior with invalid broker configuration.
        """
        invalid_config = {
            "MQTT_BROKER": "nonexistent.broker.com",
            "MQTT_PORT_INSECURE": "1883",
            "MQTT_PORT": "8883",
            "MQTT_TLS_CA": "/nonexistent/ca.crt",
            "MQTT_TLS_CERT": "/nonexistent/client.crt",
            "MQTT_TLS_KEY": "/nonexistent/client.key"
        }
        
        with patch.dict(os.environ, invalid_config):
            with pytest.raises(ConnectionError, match="MQTT connection failed"):
                MQTTClient(client_id="test_invalid_broker")
    
    def test_context_manager_usage(self, mqtt_config, mock_certificates_unavailable):
        """
        Test MQTT client as context manager.
        """
        with patch.dict(os.environ, mqtt_config):
            with MQTTClient(client_id="test_context_manager") as client:
                assert client is not None
                assert hasattr(client, 'client')
                # Context manager should automatically disconnect on exit
    
    def test_client_id_validation(self, mqtt_config, mock_certificates_unavailable):
        """
        Test client ID validation.
        """
        with patch.dict(os.environ, mqtt_config):
            # Test empty client ID
            with pytest.raises(ValueError, match="client_id must be a non-empty string"):
                MQTTClient(client_id="")
            
            # Test None client ID
            with pytest.raises(ValueError, match="client_id must be a non-empty string"):
                MQTTClient(client_id=None)
            
            # Test non-string client ID
            with pytest.raises(ValueError, match="client_id must be a non-empty string"):
                MQTTClient(client_id=123)


class TestMQTTClientReconnection:
    """
    Tests for MQTT client reconnection logic.
    
    Note: These tests simulate broker disconnection scenarios to verify
    the client's reconnection behavior.
    """
    
    @pytest.mark.asyncio
    async def test_reconnection_logic_simulation(self, mqtt_config, mock_certificates_unavailable):
        """
        Test reconnection logic using mocked connection scenarios.
        
        This test simulates broker disconnection and reconnection rather than
        actually stopping/starting the broker, as that's more reliable in CI/CD.
        """
        with patch.dict(os.environ, mqtt_config):
            client = MQTTClient(client_id="test_reconnection")
            
            try:
                # Mock the client's internal paho client
                mock_paho_client = MagicMock()
                client.client = mock_paho_client
                
                # Simulate successful initial connection
                mock_paho_client.connect.return_value = None
                mock_paho_client.loop_start.return_value = None
                
                # Test publish during normal operation
                mock_paho_client.publish.return_value.rc = mqtt.MQTT_ERR_SUCCESS
                
                test_payload = {"test": "reconnection", "timestamp": datetime.now().isoformat()}
                client.publish_event("test/reconnection", test_payload)
                
                # Verify publish was called
                mock_paho_client.publish.assert_called_once()
                
                # Simulate connection loss (would trigger automatic reconnection in real client)
                client._on_disconnect(mock_paho_client, None, mqtt.MQTT_ERR_CONN_LOST)
                
                # Simulate successful reconnection
                client._on_connect(mock_paho_client, None, None, 0)
                
                # Test publish after reconnection
                mock_paho_client.reset_mock()
                client.publish_event("test/after_reconnection", test_payload)
                mock_paho_client.publish.assert_called_once()
                
            finally:
                client.disconnect()
    
    def test_callback_methods(self, mqtt_config, mock_certificates_unavailable):
        """
        Test MQTT client callback methods.
        """
        with patch.dict(os.environ, mqtt_config):
            client = MQTTClient(client_id="test_callbacks")
            
            try:
                # Test connection callback
                client._on_connect(None, None, None, 0)  # Success
                client._on_connect(None, None, None, 1)  # Failure
                
                # Test disconnection callback
                client._on_disconnect(None, None, 0)  # Graceful
                client._on_disconnect(None, None, 1)  # Unexpected
                
                # Test publish callback
                client._on_publish(None, None, 12345)
                
                # All callbacks should handle parameters without raising exceptions
                
            finally:
                client.disconnect()


class TestMQTTClientConfiguration:
    """
    Tests for MQTT client configuration scenarios.
    """
      def test_secure_connection_configuration(self, temp_cert_dir):
        """
        Test secure connection configuration when certificates are available.
        """
        config_with_certs = {
            "MQTT_BROKER": "secure.broker.com",
            "MQTT_PORT": "8883",
            "MQTT_PORT_INSECURE": "1883",
            "MQTT_TLS_CA": os.path.join(temp_cert_dir, "ca.crt"),
            "MQTT_TLS_CERT": os.path.join(temp_cert_dir, "client.crt"),
            "MQTT_TLS_KEY": os.path.join(temp_cert_dir, "client.key")
        }
        
        with patch.dict(os.environ, config_with_certs):
            # Mock the actual MQTT connection to avoid connecting to real broker
            with patch('paho.mqtt.client.Client.connect') as mock_connect, \
                 patch('paho.mqtt.client.Client.loop_start') as mock_loop_start, \
                 patch('paho.mqtt.client.Client.tls_set') as mock_tls_set:
                
                mock_connect.return_value = None
                mock_loop_start.return_value = None
                mock_tls_set.return_value = None
                
                client = MQTTClient(client_id="test_secure")
                
                try:
                    # Verify secure configuration
                    assert client.is_secure is True
                    assert client.broker_port == 8883
                    
                    # Verify TLS configuration was called
                    mock_connect.assert_called_once_with("secure.broker.com", 8883, keepalive=60)
                    mock_tls_set.assert_called_once()
                    
                finally:
                    client.disconnect()
      def test_certificate_availability_check(self, temp_cert_dir):
        """
        Test certificate availability checking logic.
        """
        config_with_certs = {
            "MQTT_BROKER": "test.broker.com",
            "MQTT_PORT": "8883",
            "MQTT_TLS_CA": os.path.join(temp_cert_dir, "ca.crt"),
            "MQTT_TLS_CERT": os.path.join(temp_cert_dir, "client.crt"),
            "MQTT_TLS_KEY": os.path.join(temp_cert_dir, "client.key")
        }
        
        with patch.dict(os.environ, config_with_certs):
            with patch('paho.mqtt.client.Client.connect') as mock_connect, \
                 patch('paho.mqtt.client.Client.loop_start') as mock_loop_start, \
                 patch('paho.mqtt.client.Client.tls_set') as mock_tls_set:
                
                mock_connect.return_value = None
                mock_loop_start.return_value = None
                mock_tls_set.return_value = None
                
                client = MQTTClient(client_id="test_certs")
                
                try:
                    # Should detect certificates are available
                    assert client._certificates_available() is True
                    assert client.is_secure is True
                finally:
                    client.disconnect()
    
    def test_certificate_unavailable_fallback(self, mqtt_config, mock_certificates_unavailable):
        """
        Test fallback to insecure connection when certificates are unavailable.
        """
        with patch.dict(os.environ, mqtt_config):
            client = MQTTClient(client_id="test_fallback")
            
            try:
                # Should fall back to insecure connection
                assert client.is_secure is False
                assert client.broker_port == int(mqtt_config["MQTT_PORT_INSECURE"])
                
            finally:
                client.disconnect()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
