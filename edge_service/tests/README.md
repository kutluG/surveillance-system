# MQTT Client Integration Tests

This directory contains comprehensive integration tests for the Edge Service MQTT client module (`mqtt_client.py`). The tests verify that the MQTT client correctly publishes JSON events to configured MQTT brokers and handles reconnection logic under various failure scenarios.

## 📋 Test Coverage

### 1. Connection & Configuration Tests
- ✅ **Insecure Connection**: Verifies client connects in insecure mode when certificates are unavailable
- ✅ **Secure Connection**: Tests TLS configuration when certificates are present  
- ✅ **Certificate Validation**: Checks certificate availability detection logic
- ✅ **Configuration Fallback**: Tests fallback to insecure connection when TLS fails

### 2. Message Publishing Tests
- ✅ **Single Event Publishing**: Publishes a detection event and verifies receipt
- ✅ **Multiple Events**: Tests publishing multiple events in sequence
- ✅ **JSON Serialization**: Verifies datetime objects are properly serialized
- ✅ **QoS Level 1**: Confirms messages are published with correct Quality of Service

### 3. Error Handling Tests
- ✅ **Invalid Payload**: Tests error handling for non-serializable objects
- ✅ **Empty/Null Topics**: Validates topic parameter validation
- ✅ **Connection Failures**: Tests behavior with invalid broker configuration
- ✅ **Client ID Validation**: Verifies client ID parameter validation

### 4. Reconnection Logic Tests
- ✅ **Connection Callbacks**: Tests connection/disconnection event handling
- ✅ **Reconnection Simulation**: Simulates broker disconnection scenarios
- ✅ **Message Queuing**: Verifies message handling during reconnection

### 5. Integration Tests
- ✅ **Context Manager**: Tests client as Python context manager
- ✅ **Test Subscriber**: Custom MQTT subscriber for message verification
- ✅ **Broker Lifecycle**: Ephemeral broker setup and teardown

## 🛠️ Test Infrastructure

### MQTT Broker Fixtures
The tests use an ephemeral MQTT broker for reliable testing:

1. **Primary**: Subprocess-based mosquitto broker on random port
2. **Fallback**: Docker container with eclipse-mosquitto image
3. **Configuration**: Minimal broker config allowing anonymous connections

### Test Utilities
- **TestSubscriber**: Helper class to subscribe and collect MQTT messages
- **Mock Certificates**: Temporary certificate files for TLS testing
- **Port Management**: Automatic free port detection to avoid conflicts

## 🚀 Running the Tests

### Prerequisites
Install the test dependencies:
```bash
pip install -r requirements.txt
```

### Option 1: Using the Test Runner (Recommended)
```bash
# Run all tests with summary
python run_mqtt_tests.py

# Run with verbose output
python run_mqtt_tests.py --verbose

# Run with coverage report
python run_mqtt_tests.py --coverage

# Check broker availability
python run_mqtt_tests.py --broker-check
```

### Option 2: Direct pytest
```bash
# Run MQTT client tests only
pytest tests/test_mqtt_client.py -v

# Run with coverage
pytest tests/test_mqtt_client.py --cov=mqtt_client --cov-report=term-missing

# Run specific test
pytest tests/test_mqtt_client.py::TestMQTTClientIntegration::test_publish_detection_event -v
```

### Option 3: All Edge Service Tests
```bash
# Run all edge service tests
pytest tests/ -v

# Run with coverage for all modules
pytest tests/ --cov=. --cov-report=html
```

## 📊 Test Results

When running successfully, you should see output similar to:
```
🧪 MQTT Client Integration Tests
========================================
Running: python -m pytest -v tests/test_mqtt_client.py

tests/test_mqtt_client.py::TestMQTTClientIntegration::test_mqtt_client_connection_insecure PASSED
tests/test_mqtt_client.py::TestMQTTClientIntegration::test_publish_detection_event PASSED  
tests/test_mqtt_client.py::TestMQTTClientIntegration::test_publish_multiple_events PASSED
tests/test_mqtt_client.py::TestMQTTClientIntegration::test_invalid_payload_handling PASSED
tests/test_mqtt_client.py::TestMQTTClientIntegration::test_json_serialization_with_datetime PASSED
tests/test_mqtt_client.py::TestMQTTClientReconnection::test_reconnection_logic_simulation PASSED
tests/test_mqtt_client.py::TestMQTTClientConfiguration::test_secure_connection_configuration PASSED

✅ All MQTT client tests passed!
```

## 🔧 Dependencies

### Runtime Dependencies
- `paho-mqtt>=1.6.1` - MQTT client library
- `fastapi>=0.104.1` - Web framework (for main service)  
- `pydantic>=2.5.0` - Data validation

### Test Dependencies
- `pytest>=7.4.3` - Testing framework
- `pytest-asyncio>=0.21.1` - Async test support
- `pytest-mock>=3.12.0` - Mocking utilities
- `pytest-cov>=4.1.0` - Coverage reporting
- `testcontainers>=3.7.1` - Container testing (fallback)

### System Dependencies (Optional)
- `mosquitto` - MQTT broker (preferred for tests)
- `docker` - Container runtime (fallback broker)

## 🐛 Troubleshooting

### "Cannot start MQTT broker" Error
The tests automatically try multiple broker options:
1. If `mosquitto` is installed locally, it starts a subprocess broker
2. If Docker is available, it starts an `eclipse-mosquitto` container
3. If neither is available, tests are skipped with appropriate message

**Solutions:**
- Install mosquitto: `sudo apt-get install mosquitto` (Linux) or `brew install mosquitto` (macOS)
- Install Docker and ensure it's running
- Use a remote MQTT broker for testing (modify `conftest.py`)

### Port Conflicts
Tests automatically find free ports, but if you see port conflicts:
- Ensure no other services are using port 1883 (default MQTT)
- Check for existing mosquitto processes: `ps aux | grep mosquitto`
- Kill conflicting processes or restart your system

### Test Timeouts
If tests timeout waiting for messages:
- Check broker logs in test output
- Verify firewall isn't blocking local connections  
- Increase timeout values in test configuration

### Certificate Tests Failing
Certificate-related tests use mock files by default:
- Tests should pass with mock certificates
- For real certificate testing, place valid certificates in temporary directory
- Ensure certificate paths match configuration

## 📁 Test File Structure

```
edge_service/tests/
├── conftest.py                 # Test fixtures and configuration
├── test_mqtt_client.py         # Main MQTT client integration tests
└── run_mqtt_tests.py          # Test runner script (in parent directory)
```

## 🔄 CI/CD Integration

For continuous integration, use the test runner:

```yaml
# Example GitHub Actions step
- name: Run MQTT Client Tests
  run: |
    cd edge_service
    python run_mqtt_tests.py --coverage
    
# Example GitLab CI step  
mqtt_tests:
  script:
    - cd edge_service
    - python run_mqtt_tests.py --verbose --coverage
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

## 📝 Test Development

### Adding New Tests
1. Add new test methods to existing test classes in `test_mqtt_client.py`
2. Use existing fixtures from `conftest.py` 
3. Follow naming convention: `test_<functionality>_<scenario>`
4. Include docstrings explaining test purpose

### Custom Fixtures
Add new fixtures to `conftest.py`:
```python
@pytest.fixture
def custom_mqtt_config():
    """Custom MQTT configuration for specific tests."""
    return {"MQTT_BROKER": "custom.broker.com"}
```

### Mock Patterns
Common mocking patterns used in tests:
```python
# Mock environment variables
with patch.dict(os.environ, mqtt_config):
    # Test code

# Mock file system operations  
with patch('os.path.exists', return_value=False):
    # Test code
    
# Mock MQTT client internals
with patch('paho.mqtt.client.Client.connect') as mock_connect:
    # Test code
```

## 🎯 Test Goals Achieved

This test suite successfully addresses all requirements from the original specification:

1. ✅ **Local MQTT Broker Fixture**: Implemented with subprocess/Docker fallback
2. ✅ **Publish Test**: Verifies JSON events are published and received correctly  
3. ✅ **Reconnect Logic Test**: Simulates disconnection and validates recovery
4. ✅ **Error Handling**: Tests invalid payloads and connection failures

The tests provide comprehensive coverage of the MQTT client functionality while being reliable and maintainable for continuous integration environments.
