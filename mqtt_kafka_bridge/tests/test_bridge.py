import json
import pytest
from mqtt_kafka_bridge.main import on_message, on_connect, delivery_report

class DummyMsg:
    def __init__(self, payload, topic="camera/events/01"):
        self.payload = payload
        self.topic = topic

class DummyProducer:
    def __init__(self):
        self.messages = []

    def produce(self, topic, value, callback):
        self.messages.append((topic, value))
        # simulate delivery
        callback(None, type("Msg", (), {"topic": lambda: topic, "partition": lambda: 0}))

    def poll(self, timeout):
        pass

    def flush(self):
        pass

class DummyMQTTClient:
    def __init__(self):
        self.subscribed = []

    def subscribe(self, topic, qos):
        self.subscribed.append((topic, qos))

@pytest.fixture(autouse=True)
def patch_clients(monkeypatch):
    # Patch kafka producer and mqtt client in module
    from mqtt_kafka_bridge import main
    monkeypatch.setattr(main, "kafka_producer", DummyProducer())
    monkeypatch.setattr(main, "bridge_client", DummyMQTTClient())
    yield

def test_on_connect_subscribes():
    client = DummyMQTTClient()
    on_connect(client, None, None, rc=0)
    assert ("camera/events/#", 1) in client.subscribed

def test_on_message_forwards_to_kafka(caplog):
    caplog.set_level("INFO")
    payload = json.dumps({"test": "data"}).encode("utf-8")
    msg = DummyMsg(payload)
    # Call on_message: should add to producer.messages
    on_message(None, None, msg)
    from mqtt_kafka_bridge.main import kafka_producer
    topics = [t for t, _ in kafka_producer.messages]
    assert "camera.events" in topics
    # ensure log was emitted
    assert any("Bridged MQTT→Kafka" in rec.getMessage() for rec in caplog.records)

def test_on_message_invalid_json(caplog):
    caplog.set_level("ERROR")
    msg = DummyMsg(b"not-a-json")
    on_message(None, None, msg)
    assert any("Invalid JSON on MQTT" in rec.getMessage() for rec in caplog.records)