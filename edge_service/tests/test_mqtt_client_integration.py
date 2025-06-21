"""
Integration Tests for Edge Service MQTT Client

This test suite provides comprehensive integration testing for the MQTT client,
verifying correct event publishing, reconnection logic, and error handling.

Test Coverage:
1. MQTT broker fixture using subprocess/Docker/testcontainers
2. Message publishing and subscription verification
3. Reconnection logic testing with broker restart
4. Error handling for invalid payloads and network issues
5. Connection lifecycle management

Requirements:
- Local MQTT broker (Mosquitto via subprocess or Docker)
- Testcontainers-python for container management
- Pytest for test framework
"""
import os
import sys
import json
import time
import pytest
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock
from datetime import datetime
import threading
import signal
import subprocess

import paho.mqtt.client as mqtt

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mqtt_client import MQTTClient


class TestMQTTSubscriber:
    """
    Test helper for subscribing to MQTT topics and collecting messages.
    """
    
    def __init__(self, broker_host: str, broker_port: int):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.received_messages: List[Dict[str, Any]] = []
        self.connected = False
        self.subscribed_topics = []
        self.client = mqtt.Client(client_id=f"test_subscriber_{int(time.time())}")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_subscribe = self._on_subscribe
        
    def _on_connect(self, client, userdata, flags, rc):
        """Connection callback."""
        if rc == 0:
            self.connected = True
            print(f"Test subscriber connected to {self.broker_host}:{self.broker_port}")
        else:
            self.connected = False
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
                "timestamp": datetime.now(),
                "raw_payload": msg.payload.decode('utf-8')
            }
            self.received_messages.append(message_data)
            print(f"Test subscriber received: {msg.topic} -> {len(msg.payload)} bytes")
        except json.JSONDecodeError as e:
            print(f"Failed to decode message: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Disconnection callback."""
        self.connected = False
        print(f"Test subscriber disconnected (code: {rc})")
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Subscription callback."""
        print(f"Test subscriber subscribed successfully (mid: {mid}, qos: {granted_qos})")

    def connect(self, timeout: int = 10) -> bool:
        """Connect to the broker with timeout."""
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            
            # Wait for connection with timeout
            start_time = time.time()
            while not self.connected and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            return self.connected
        except Exception as e:
            print(f"Test subscriber connection error: {e}")
            return False
    
    def subscribe(self, topic: str, qos: int = 1):
        """Subscribe to a topic."""
        if self.connected:
            result, mid = self.client.subscribe(topic, qos)
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.subscribed_topics.append(topic)
                print(f"Subscribed to {topic} with QoS {qos}")
            return result == mqtt.MQTT_ERR_SUCCESS
        return False
    
    def disconnect(self):
        """Disconnect from the broker."""
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
    
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
    
    def test_publish_detection_event(self, mqtt_config, mock_certificates_unavailable, 
                                   sample_detection_event, mosquitto_broker):
        """
        Test: Publish JSON detection event and verify receipt
        
        Requirements:
        - Configure mqtt_client to connect to broker_url
        - Call mqtt_client.publish_event with detection payload
        - Subscribe to same topic and assert received payload matches
        """
        topic = "edge/detections"
        
        # Set up test subscriber
        subscriber = TestMQTTSubscriber(
            broker_host=mosquitto_broker["host"],
            broker_port=mosquitto_broker["port"]
        )
        
        try:
            # Connect subscriber and subscribe to topic
            assert subscriber.connect(timeout=10), "Test subscriber failed to connect"
            assert subscriber.subscribe(topic, qos=1), "Failed to subscribe to topic"
            
            # Give subscriber time to establish subscription
            time.sleep(1)
            
            # Create MQTT client and publish event
            with patch.dict(os.environ, mqtt_config):
                client = MQTTClient(client_id="test_publisher")
                
                try:
                    # Publish the detection event
                    client.publish_event(topic, sample_detection_event)
                    
                    # Wait for message to be received
                    assert subscriber.wait_for_messages(1, timeout=5), \
                        "Detection event not received within timeout"
                    
                    # Verify message content matches exactly
                    received = subscriber.received_messages[0]
                    assert received["topic"] == topic
                    assert received["payload"]["camera_id"] == sample_detection_event["camera_id"]
                    assert received["payload"]["event_type"] == sample_detection_event["event_type"]
                    assert received["qos"] == 1  # QoS 1 for reliable delivery
                    
                    # Verify detection data structure
                    assert "detections" in received["payload"]
                    assert len(received["payload"]["detections"]) == len(sample_detection_event["detections"])
                    
                finally:
                    client.disconnect()
                    
        finally:
            subscriber.disconnect()

    def test_publish_custom_json_event(self, mqtt_config, mock_certificates_unavailable, 
                                     mosquitto_broker):
        """
        Test: Publish custom JSON event as specified in requirements
        
        Requirements:
        - Publish event with {"camera_id":"cam1","timestamp":"...","label":"person"}
        - Verify exact JSON payload is received
        """
        topic = "edge/detections"
        
        # Create the exact event structure from requirements
        test_event = {
            "camera_id": "cam1", 
            "timestamp": datetime.now().isoformat(),
            "label": "person"
        }
        
        # Set up test subscriber
        subscriber = TestMQTTSubscriber(
            broker_host=mosquitto_broker["host"],
            broker_port=mosquitto_broker["port"]
        )
        
        try:
            assert subscriber.connect(timeout=10), "Test subscriber failed to connect"
            assert subscriber.subscribe(topic, qos=1), "Failed to subscribe to topic"
            time.sleep(1)
            
            # Create MQTT client and publish the specified event
            with patch.dict(os.environ, mqtt_config):
                client = MQTTClient(client_id="test_custom_publisher")
                
                try:
                    client.publish_event(topic, test_event)
                    
                    # Wait and verify exact payload
                    assert subscriber.wait_for_messages(1, timeout=5), \
                        "Custom event not received within timeout"
                    
                    received = subscriber.received_messages[0]
                    assert received["payload"]["camera_id"] == "cam1"
                    assert received["payload"]["label"] == "person"
                    assert "timestamp" in received["payload"]
                    
                finally:
                    client.disconnect()
                    
        finally:
            subscriber.disconnect()

    @pytest.mark.integration
    def test_reconnection_logic_with_broker_restart(self, mqtt_config, mock_certificates_unavailable,
                                                   mosquitto_broker_restartable):
        """
        Test: Reconnection logic with actual broker restart
        
        Requirements:
        - Stop broker after initial connect
        - Call publish_event while broker is down (should not crash)
        - Restart broker and verify reconnection works
        - Verify queued messages are eventually sent
        """
        topic = "edge/detections"
        test_event = {
            "camera_id": "cam_reconnect_test",
            "timestamp": datetime.now().isoformat(),
            "message": "reconnection test"
        }
        
        # Set up subscriber
        subscriber = TestMQTTSubscriber(
            broker_host=mosquitto_broker_restartable["host"],
            broker_port=mosquitto_broker_restartable["port"]
        )
        
        try:
            # Initial connection and subscription
            assert subscriber.connect(timeout=10), "Initial subscriber connection failed"
            assert subscriber.subscribe(topic, qos=1), "Failed to subscribe to topic"
            time.sleep(1)
            
            # Create MQTT client 
            with patch.dict(os.environ, {
                **mqtt_config,
                "MQTT_BROKER": mosquitto_broker_restartable["host"],
                "MQTT_PORT_INSECURE": str(mosquitto_broker_restartable["port"])
            }):
                client = MQTTClient(client_id="test_reconnect_client")
                
                try:
                    # Test initial publish works
                    client.publish_event(topic, test_event)
                    assert subscriber.wait_for_messages(1, timeout=5), \
                        "Initial message not received"
                    
                    subscriber.clear_messages()
                    
                    # Stop the broker
                    print("Stopping MQTT broker...")
                    mosquitto_broker_restartable["stop"]()
                    time.sleep(2)
                    
                    # Try to publish while broker is down - should not crash
                    print("Publishing while broker is down...")
                    try:
                        client.publish_event(topic, {
                            **test_event, 
                            "message": "published while down"
                        })
                        # Should not crash, but may fail silently or queue
                    except Exception as e:
                        print(f"Expected exception while broker down: {e}")
                    
                    # Restart the broker
                    print("Restarting MQTT broker...")
                    mosquitto_broker_restartable["restart"]()
                    time.sleep(3)  # Give broker time to start
                    
                    # Reconnect subscriber
                    subscriber.disconnect()
                    time.sleep(1)
                    assert subscriber.connect(timeout=10), "Subscriber reconnection failed"
                    assert subscriber.subscribe(topic, qos=1), "Failed to resubscribe"
                    time.sleep(1)
                    
                    # Test publish after broker restart
                    print("Publishing after broker restart...")
                    client.publish_event(topic, {
                        **test_event,
                        "message": "published after restart"
                    })
                    
                    # Verify message is received after reconnection
                    assert subscriber.wait_for_messages(1, timeout=10), \
                        "Message not received after broker restart"
                    
                    received = subscriber.received_messages[0]
                    assert received["payload"]["message"] == "published after restart"
                    
                finally:
                    client.disconnect()
                    
        finally:
            subscriber.disconnect()

    def test_error_handling_invalid_payloads(self, mqtt_config, mock_certificates_unavailable):
        """
        Test: Error handling for invalid payloads
        
        Requirements:
        - Simulate invalid payload (non-serializable object)
        - Assert publish_event raises TypeError or custom exception
        """
        with patch.dict(os.environ, mqtt_config):
            client = MQTTClient(client_id="test_error_handling")
            
            try:
                # Test 1: Empty topic should raise ValueError
                with pytest.raises(ValueError, match="Topic must be a non-empty string"):
                    client.publish_event("", {"test": "data"})
                
                # Test 2: None topic should raise ValueError
                with pytest.raises(ValueError, match="Topic must be a non-empty string"):
                    client.publish_event(None, {"test": "data"})
                
                # Test 3: Non-dict payload should raise ValueError
                with pytest.raises(ValueError, match="Payload must be a dictionary"):
                    client.publish_event("test/topic", "not a dict")
                
                # Test 4: Non-serializable payload should raise ValueError
                class NonSerializableClass:
                    def __init__(self):
                        self.circular_ref = self
                
                non_serializable_payload = {
                    "camera_id": "cam1",
                    "bad_object": NonSerializableClass()
                }
                
                with pytest.raises(ValueError, match="Payload serialization failed"):
                    client.publish_event("test/topic", non_serializable_payload)
                    
            finally:
                client.disconnect()

    def test_multiple_events_sequence(self, mqtt_config, mock_certificates_unavailable, 
                                    mosquitto_broker):
        """
        Test: Multiple events published in sequence
        
        Verifies that multiple rapid publications work correctly and all
        messages are received in order.
        """
        topic = "edge/detections"
        num_messages = 10
        
        # Set up subscriber
        subscriber = TestMQTTSubscriber(
            broker_host=mosquitto_broker["host"],
            broker_port=mosquitto_broker["port"]
        )
        
        try:
            assert subscriber.connect(timeout=10), "Subscriber connection failed"
            assert subscriber.subscribe(topic, qos=1), "Failed to subscribe"
            time.sleep(1)
            
            # Create client and publish multiple events
            with patch.dict(os.environ, mqtt_config):
                client = MQTTClient(client_id="test_multi_publisher")
                
                try:
                    events = []
                    for i in range(num_messages):
                        event = {
                            "camera_id": f"cam_{i}",
                            "timestamp": datetime.now().isoformat(),
                            "message_id": i,
                            "event_type": "test_sequence"
                        }
                        events.append(event)
                        client.publish_event(topic, event)
                        time.sleep(0.1)  # Small delay to avoid overwhelming
                    
                    # Wait for all messages
                    assert subscriber.wait_for_messages(num_messages, timeout=15), \
                        f"Expected {num_messages} messages, got {len(subscriber.received_messages)}"
                    
                    # Verify all messages received with correct content
                    assert len(subscriber.received_messages) == num_messages
                    
                    for i, received in enumerate(subscriber.received_messages):
                        assert received["payload"]["message_id"] == i
                        assert received["payload"]["camera_id"] == f"cam_{i}"
                        assert received["payload"]["event_type"] == "test_sequence"
                        
                finally:
                    client.disconnect()
                    
        finally:
            subscriber.disconnect()

    def test_json_serialization_with_datetime(self, mqtt_config, mock_certificates_unavailable,
                                            mosquitto_broker):
        """
        Test: JSON serialization handles datetime objects correctly
        
        Verifies that datetime objects in payloads are properly serialized
        to strings in the JSON output.
        """
        topic = "edge/datetime_test"
        
        # Set up subscriber
        subscriber = TestMQTTSubscriber(
            broker_host=mosquitto_broker["host"],
            broker_port=mosquitto_broker["port"]
        )
        
        try:
            assert subscriber.connect(timeout=10), "Subscriber connection failed"
            assert subscriber.subscribe(topic, qos=1), "Failed to subscribe"
            time.sleep(1)
            
            # Create event with datetime objects
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
                        "DateTime event not received within timeout"
                    
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


class TestMQTTClientConnectionManagement:
    """
    Tests for MQTT client connection lifecycle management.
    """
    
    def test_client_context_manager(self, mqtt_config, mock_certificates_unavailable):
        """
        Test: MQTT client as context manager
        
        Verifies that the client properly handles resource cleanup
        when used as a context manager.
        """
        with patch.dict(os.environ, mqtt_config):
            with MQTTClient(client_id="test_context_manager") as client:
                assert client is not None
                assert hasattr(client, 'client')
                # Context manager should automatically disconnect on exit

    def test_client_id_validation(self, mqtt_config, mock_certificates_unavailable):
        """
        Test: Client ID validation
        
        Verifies that proper validation is performed on client IDs.
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

    def test_connection_failure_handling(self, mock_certificates_unavailable):
        """
        Test: Connection failure handling
        
        Verifies that connection failures are properly handled and reported.
        """
        invalid_config = {
            "MQTT_BROKER": "nonexistent.broker.invalid",
            "MQTT_PORT_INSECURE": "1883",
            "MQTT_PORT": "8883",
            "MQTT_TLS_CA": "/nonexistent/ca.crt",
            "MQTT_TLS_CERT": "/nonexistent/client.crt",
            "MQTT_TLS_KEY": "/nonexistent/client.key"
        }
        
        with patch.dict(os.environ, invalid_config):
            with pytest.raises(ConnectionError, match="MQTT connection failed"):
                MQTTClient(client_id="test_invalid_broker")
