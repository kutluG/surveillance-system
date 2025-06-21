# MQTT Client Integration Tests

## Overview

This directory contains comprehensive integration tests for the Edge Service MQTT client, addressing all requirements specified in the original request.

## Test Coverage

### 1. Local MQTT Broker Fixtures

**Requirement**: Use `pytest-mosquitto` or `testcontainers-python` to spin up an ephemeral MQTT broker for tests.

**Implementation**:
- `mosquitto_broker` fixture in `conftest.py` - Uses subprocess or Docker fallback
- `mosquitto_broker_restartable` fixture - Supports stop/start/restart operations for reconnection tests
- `testcontainers_mosquitto_broker` fixture - Uses testcontainers-python for CI/CD environments

### 2. Publish Test

**Requirement**: 
- Configure `mqtt_client` to connect to `broker_url`
- Call `mqtt_client.publish_event({"camera_id":"cam1","timestamp":"...","label":"person"})`
- Subscribe to the same topic and assert received payload matches

**Implementation**:
- `test_publish_detection_event()` - Tests complex detection event publishing
- `test_publish_custom_json_event()` - Tests exact JSON format from requirements
- `test_multiple_events_sequence()` - Tests multiple rapid publications
- Uses `TestMQTTSubscriber` helper class for reliable message verification

### 3. Reconnection Logic Test

**Requirement**:
- Stop broker after initial connect
- Call `publish_event(...)` while broker is down (should not crash)
- Restart broker, allow retry loop to reconnect
- Verify queued messages are sent

**Implementation**:
- `test_reconnection_logic_with_broker_restart()` - Full reconnection test
- Uses `mosquitto_broker_restartable` fixture with actual broker stop/start
- Verifies client doesn't crash during disconnection
- Tests message delivery after reconnection

### 4. Error Handling

**Requirement**: Simulate invalid payload → assert `publish_event` raises `TypeError` or custom exception

**Implementation**:
- `test_error_handling_invalid_payloads()` - Comprehensive error testing
- Tests empty/None topics → `ValueError`
- Tests non-dict payloads → `ValueError`
- Tests non-serializable objects → `ValueError` with "Payload serialization failed"

## Files Structure

```
tests/
├── conftest.py                      # Test fixtures and configuration
├── test_mqtt_client_integration.py  # Main integration test suite
├── run_mqtt_tests.py               # Test runner script
└── README.md                       # This file
```

## Test Classes

### `TestMQTTSubscriber`
Helper class for subscribing to MQTT topics and collecting messages for verification.

**Features**:
- Reliable connection management
- Message collection with metadata
- Timeout-based message waiting
- JSON deserialization with error handling

### `TestMQTTClientIntegration`
Main integration test class covering all core functionality.

**Test Methods**:
- `test_publish_detection_event()` - Basic detection event publishing
- `test_publish_custom_json_event()` - Requirements-specific JSON format
- `test_reconnection_logic_with_broker_restart()` - Full reconnection testing
- `test_error_handling_invalid_payloads()` - Error condition testing
- `test_multiple_events_sequence()` - Rapid publishing sequence
- `test_json_serialization_with_datetime()` - DateTime serialization

### `TestMQTTClientConnectionManagement`
Connection lifecycle and validation tests.

**Test Methods**:
- `test_client_context_manager()` - Context manager usage
- `test_client_id_validation()` - Client ID validation
- `test_connection_failure_handling()` - Connection error handling

## Running Tests

### Prerequisites

1. **Python Dependencies**:
   ```bash
   pip install pytest paho-mqtt testcontainers
   ```

2. **MQTT Broker** (one of the following):
   - Mosquitto installed locally: `apt-get install mosquitto` (Linux) or `brew install mosquitto` (macOS)
   - Docker: `docker pull eclipse-mosquitto:2.0`

### Quick Tests (Basic Functionality)
```bash
python run_mqtt_tests.py --quick
```

### Full Integration Tests (Including Reconnection)
```bash
python run_mqtt_tests.py --integration
```

### All Tests
```bash
python run_mqtt_tests.py --all
```

### Manual Pytest Execution
```bash
# Run all integration tests
pytest tests/test_mqtt_client_integration.py -v

# Run only quick tests (skip integration marker)
pytest tests/test_mqtt_client_integration.py -m "not integration" -v

# Run only integration tests
pytest tests/test_mqtt_client_integration.py -m "integration" -v
```

## Test Configuration

### Environment Variables
Tests use these environment variables (automatically configured by fixtures):

- `MQTT_BROKER` - MQTT broker hostname (default: localhost) 
- `MQTT_PORT` - Secure MQTT port (default: 8883)
- `MQTT_PORT_INSECURE` - Insecure MQTT port (default: 1883)
- `MQTT_TLS_CA` - CA certificate path (mocked as unavailable in tests)
- `MQTT_TLS_CERT` - Client certificate path (mocked as unavailable in tests)
- `MQTT_TLS_KEY` - Client private key path (mocked as unavailable in tests)

### Fixtures

- `mosquitto_broker` - Basic MQTT broker for standard tests
- `mosquitto_broker_restartable` - Restartable broker for reconnection tests
- `mqtt_config` - MQTT client configuration dictionary
- `mock_certificates_unavailable` - Forces insecure connection mode
- `sample_detection_event` - Sample detection event data

## CI/CD Integration

The tests are designed to work reliably in CI/CD environments:

1. **Container Support**: Uses testcontainers-python as fallback
2. **Port Management**: Automatically finds free ports to avoid conflicts
3. **Timeout Handling**: Reasonable timeouts for network operations
4. **Cleanup**: Proper resource cleanup even on test failures
5. **Docker Fallback**: Falls back to Docker if local Mosquitto unavailable

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Tests automatically find free ports
2. **Docker Not Available**: Install Docker or Mosquitto locally
3. **Permission Issues**: Ensure user can run Docker/start processes
4. **Network Timeouts**: Increase timeout values in test configuration

### Debug Mode
```bash
pytest tests/test_mqtt_client_integration.py -v -s --tb=long
```

### Logs
Test output includes detailed connection and message information for debugging.

## Requirements Compliance

✅ **Local MQTT Broker Fixture**: Multiple fixture options with fallbacks  
✅ **Publish Test**: Exact JSON payload verification  
✅ **Reconnect Logic Test**: Actual broker restart with reconnection verification  
✅ **Error Handling**: Comprehensive invalid payload testing  
✅ **Integration**: Full end-to-end testing with real MQTT broker  

All requirements from the original specification are fully implemented and tested.
