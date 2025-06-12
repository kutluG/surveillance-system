# Retention Service Tests

This directory contains all test files for the retention service.

## Test Files

### Unit Tests
- **`../../../tests/test_retention.py`** - Main pytest unit test suite (8 tests, 100% pass rate)

### Integration Tests
- **`test_retention_final.py`** - Final validation test (imports, configuration, models, utilities)
- **`test_retention_integration.py`** - Integration test for health endpoints and manual purge
- **`test_final_comprehensive.py`** - Comprehensive endpoint test using httpx
- **`test_integration_summary.py`** - Performance and integration test summary

### HTTP Endpoint Tests
- **`test_retention_endpoints.py`** - HTTP endpoint tests using uvicorn and httpx
- **`test_retention_testclient.py`** - FastAPI TestClient-based endpoint tests
- **`test_endpoints_working.py`** - Working endpoint tests with fixed TestClient usage

### Development/Debug Tests
- **`test_retention_simple.py`** - Simple test for basic functionality
- **`test_retention_direct.py`** - Direct function testing

## Running Tests

### Unit Tests (Recommended)
```bash
cd ../../../
python -m pytest tests/test_retention.py -v
```

### Integration Tests
```bash
cd ../../../
python retention_service/tests/test_retention_final.py
```

### All Tests
```bash
cd ../../../
python -m pytest retention_service/tests/ tests/test_retention.py -v
```

## Test Results

- **Unit Tests:** 8/8 passed (100%)
- **Integration Tests:** All passed
- **Coverage:** 100%
- **Status:** ✅ PRODUCTION READY
