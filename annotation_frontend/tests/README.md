# Annotation Frontend Testing Suite

This directory contains comprehensive tests for the annotation frontend service, covering both unit tests for API endpoints and integration tests for Kafka functionality.

## Test Structure

```
tests/
├── conftest.py                 # Test fixtures and configuration
├── test_api_endpoints.py       # Unit tests for FastAPI endpoints
├── test_kafka_integration.py   # Integration tests for Kafka messaging
└── README.md                   # This file
```

## Test Categories

### 1. Unit Tests (test_api_endpoints.py)

Tests FastAPI endpoints with `TestClient` to validate:

- **GET `/api/v1/examples`** - Retrieve pending examples
  - Empty database scenarios
  - Pagination handling
  - Authentication requirements
  
- **GET `/api/v1/examples/{event_id}`** - Get specific example
  - Existing example retrieval
  - Non-existent example handling (404)
  
- **POST `/api/v1/examples/{event_id}/label`** - Submit annotations
  - Valid annotation submission
  - Invalid bounding box validation (422)
  - Missing required fields validation
  - Kafka producer integration
  - Error handling for Kafka failures
  
- **DELETE `/api/v1/examples/{event_id}`** - Skip examples
  - Successful example skipping
  - Non-existent example handling
  
- **GET `/health`** - Health check endpoint
  - Service status validation
  
- **GET `/api/v1/stats`** - Statistics endpoint
  - Annotation statistics retrieval
  - Authentication requirements

- **Authorization Testing**
  - Scope-based access control
  - Write vs. read permissions

### 2. Integration Tests (test_kafka_integration.py)

Tests Kafka messaging end-to-end flows:

- **Consumer Functionality**
  - Successful hard example consumption
  - Invalid JSON message handling
  - Kafka error handling
  - Queue size limit enforcement
  - Partition EOF handling
  
- **Producer Functionality**
  - Delivery report callbacks (success/error)
  - Message production from labeling API
  - Message serialization validation
  
- **End-to-End Flows**
  - Complete hard example → labeled example workflow
  - Connection resilience testing
  - Consumer group behavior
  - Concurrent message processing

## Test Fixtures

### Database Fixtures
- `test_db` - Temporary SQLite database for testing
- `db_session` - Database session for individual tests
- `annotation_example_in_db` - Pre-created database records
- `retry_queue_item` - Retry queue test data

### Authentication Fixtures
- `mock_user` - Mock authenticated user with scopes
- `test_settings` - Test-specific configuration

### Kafka Fixtures
- `kafka_container` - Testcontainers Kafka instance (with fallback)
- `kafka_producer` - Kafka producer for integration tests
- `kafka_consumer` - Kafka consumer for integration tests

### Sample Data Fixtures
- `sample_hard_example` - Sample hard example data
- `sample_labeled_detection` - Sample annotation data
- `invalid_bbox_data` - Invalid bounding box test cases

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements.txt
```

### Basic Test Execution 

```bash
# Run all tests
python -m pytest tests/

# Run with verbose output
python -m pytest -v tests/

# Run specific test file
python -m pytest tests/test_api_endpoints.py
python -m pytest tests/test_kafka_integration.py
```

### Using the Test Runner Script

```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py --unit

# Run only integration tests  
python run_tests.py --integration

# Run only Kafka tests
python run_tests.py --kafka

# Run with coverage report
python run_tests.py --coverage

# Verbose output
python run_tests.py --verbose
```

### Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.kafka` - Kafka-specific tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.auth` - Authentication tests

Run specific marker groups:
```bash
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m "not slow"    # Exclude slow tests
```

## Test Configuration

### pytest.ini
- Configures test discovery patterns
- Sets asyncio mode for async tests
- Defines test markers
- Configures warning filters

### Environment Variables
Tests use the following configuration:
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka connection (defaults to localhost:9092)
- `JWT_SECRET_KEY` - JWT secret for auth tests
- Database uses temporary SQLite for isolation

## Mocking Strategy

### Kafka Mocking
- Uses `testcontainers` for real Kafka when available
- Falls back to mocks when testcontainers unavailable
- Mocks producer/consumer for unit tests

### Database Mocking
- Uses temporary SQLite databases for isolation
- Each test gets a fresh database instance
- Fixtures handle cleanup automatically

### Authentication Mocking
- Overrides FastAPI dependencies for auth
- Provides configurable mock users with scopes
- Tests both authenticated and unauthenticated scenarios

## Coverage Goals

The test suite aims for:
- **90%+ code coverage** for core business logic
- **100% endpoint coverage** for all API routes
- **Integration coverage** for all Kafka interactions
- **Error path coverage** for exception handling

Generate coverage report:
```bash
python run_tests.py --coverage
# Opens htmlcov/index.html for detailed report
```

## Continuous Integration

Tests are designed to run in CI/CD environments:
- No external dependencies required (uses mocks/fallbacks)
- Fast execution (under 30 seconds for full suite)
- Clear pass/fail status with detailed error reporting
- Coverage reporting for quality gates

### CI Environment Variables
```bash
export PYTEST_CURRENT_TEST=true  # Enables CI-specific behavior
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure you're running from the annotation_frontend directory
   - Check that all dependencies are installed

2. **Kafka Connection Failures**
   - Tests fall back to mocks automatically
   - Real Kafka tests require Docker/testcontainers

3. **Database Lock Errors**
   - Each test uses isolated temporary databases
   - Restart tests if SQLite locks persist

4. **Authentication Failures**
   - Tests use mocked authentication by default
   - Check dependency overrides in conftest.py

### Debug Mode
```bash
# Run with Python debugger
python -m pytest --pdb tests/

# Run with detailed logging
python -m pytest -s --log-cli-level=DEBUG tests/
```

## Future Enhancements

Planned test improvements:
- Performance benchmarking tests
- Chaos engineering tests for resilience
- Property-based testing with Hypothesis
- Contract testing with consumer services
- Load testing with concurrent users
