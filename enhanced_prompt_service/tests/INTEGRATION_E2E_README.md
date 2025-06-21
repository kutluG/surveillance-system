# Integration & E2E Tests - Quick Start Guide

This directory now includes comprehensive integration and end-to-end tests for the Enhanced Prompt Service.

## 🆕 New Test Files

### 1. `test_clip_store.py` - Integration Tests
Tests file system operations and URL generation with real temporary files:
- ✅ Clip URL generation with VMS service integration
- ✅ File availability checking with real filesystem
- ✅ Multiple clip URL retrieval
- ✅ Error handling for network timeouts and invalid responses
- ✅ Metadata inclusion and custom expiry handling

### 2. `test_api_endpoints.py` - E2E API Tests  
Tests the complete FastAPI application with TestClient:
- ✅ `/api/v1/conversation` endpoint (POST) - Full conversational flow
- ✅ `/api/v1/conversation/{id}/history` endpoint (GET) - History retrieval
- ✅ `/api/v1/conversation/{id}` endpoint (DELETE) - Conversation deletion
- ✅ `/api/v1/proactive-insights` endpoint (GET) - Insight generation
- ✅ Authentication and validation error handling
- ✅ Server error scenarios and edge cases

## 🚀 Running the Tests

### Quick Start (Single Command)
```bash
# Run all integration and E2E tests
python run_integration_tests.py
```

### Individual Test Suites
```bash
# Clip Store Integration Tests
python -m pytest tests/test_clip_store.py -v

# FastAPI E2E Tests  
python -m pytest tests/test_api_endpoints.py -v

# Quick test run (fail fast)
pytest --maxfail=1 --disable-warnings -q

# With coverage
pytest tests/ --cov=. --cov-report=term-missing
```

### Using the Enhanced Test Runner
```bash
# Run specific module tests
python run_tests.py --module clip_store
python run_tests.py --module api
python run_tests.py --module e2e
python run_tests.py --module integration

# Run with coverage
python run_tests.py --coverage

# Install test dependencies
python run_tests.py --install-deps
```

## 🔧 Test Structure

### Integration Tests (`test_clip_store.py`)
- **Real File System**: Uses `tempfile.TemporaryDirectory()` for isolated testing
- **Mock VMS Service**: Simulates VMS API responses with `requests.Mock`
- **Error Scenarios**: Network timeouts, invalid JSON, missing files
- **Configuration**: Mock configuration injection via `patch`

### E2E Tests (`test_api_endpoints.py`)
- **TestClient**: Real HTTP requests to FastAPI application
- **Full Mocking**: All external dependencies (Redis, OpenAI, Weaviate) mocked
- **Authentication**: JWT token simulation
- **Validation**: Request/response schema validation
- **Error Handling**: 422, 500, authentication errors

## 📊 CI Integration

The tests are now integrated into GitHub Actions CI (`.github/workflows/ci.yml`):

```yaml
- name: 🧪 Run Python Tests
  run: pytest --maxfail=1 --disable-warnings -q

- name: 🧪 Run integration tests  
  run: pytest tests/test_clip_store.py -v -k "integration" --disable-warnings

- name: 🧪 Run E2E API tests
  run: pytest tests/test_api_endpoints.py -v --disable-warnings
```

## 🧪 Test Scenarios Covered

### ClipStore Integration
- [x] Successful clip URL retrieval from VMS service
- [x] Fallback URL generation when VMS fails
- [x] File existence checking with real filesystem
- [x] Multiple clip URL batch processing
- [x] Thumbnail URL generation
- [x] Shareable link creation with expiry
- [x] Network timeout and error handling
- [x] Custom expiry time handling

### FastAPI E2E  
- [x] Complete conversation flow with context
- [x] Conversation history retrieval with pagination
- [x] Conversation deletion
- [x] Proactive insights generation
- [x] Authentication required for all endpoints
- [x] Request validation (missing fields, wrong types)
- [x] Server error handling (500 responses)
- [x] Large payload handling
- [x] Edge case inputs (empty strings, negative numbers)

## 🔍 Key Features

### Real Environment Simulation
- **Temporary Files**: Creates actual video files for testing
- **HTTP Requests**: Real FastAPI application via TestClient
- **Database Simulation**: FakeRedis for conversation storage

### Comprehensive Mocking
- **External APIs**: OpenAI, VMS Service, Weaviate
- **Authentication**: JWT token validation
- **Configuration**: Service configuration injection
- **Network Errors**: Timeout and connection failures

### Error Coverage
- **Network Issues**: Connection timeouts, service unavailable
- **Validation Errors**: Invalid JSON, missing fields, wrong types
- **Authentication**: Missing tokens, invalid credentials
- **Server Errors**: Database failures, API errors

## 📈 Coverage Goals

- **Integration Tests**: Focus on external service integration
- **E2E Tests**: Cover complete API request/response cycles
- **Unit Tests**: Existing tests for individual components
- **Combined Coverage**: Aim for >90% overall test coverage

## 🚨 Running in CI

The tests run automatically on every push to `main` or `develop` branches:

1. **Dependency Validation** → **Documentation Check** → **Tests**
2. **Security Scan** runs in parallel
3. **Coverage Reports** uploaded to Codecov
4. **Test Artifacts** saved for 30 days

## 🛠️ Development Workflow

1. **Add Feature** → Write unit tests first
2. **Integration Point** → Add integration test in `test_clip_store.py`
3. **API Endpoint** → Add E2E test in `test_api_endpoints.py`
4. **Run Locally** → `python run_integration_tests.py`
5. **Commit & Push** → CI runs all tests automatically

## 🎯 Success Criteria

✅ **Integration Tests**: File operations work with real filesystem  
✅ **E2E Tests**: Complete HTTP request/response cycles function  
✅ **CI Integration**: Tests run automatically on push  
✅ **Error Handling**: Graceful failure scenarios covered  
✅ **Documentation**: Clear instructions for running tests  

Your integration and E2E tests are now fully implemented and integrated into the CI pipeline!
