# Unit Testing Guide

This directory contains comprehensive unit tests for the Enhanced Prompt Service modules with 100% coverage targeting.

## Overview

The test suite covers three critical modules:
- **`llm_client.py`** - OpenAI integration and conversational AI responses
- **`weaviate_client.py`** - Vector database operations and semantic search  
- **`conversation_manager.py`** - Redis-backed conversation memory management

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and test configuration
├── test_conversation_manager.py   # ConversationManager tests (100% coverage)
├── test_llm_client.py            # LLM client tests (100% coverage)
├── test_weaviate_client.py       # Weaviate client tests (100% coverage)
└── __init__.py                   # Test package marker
```

## Key Features

### 🔧 **Comprehensive Mocking**
- **Redis**: Uses `fakeredis` for realistic Redis simulation
- **OpenAI**: Mocks API responses, errors, and edge cases
- **Weaviate**: Stubs vector search operations and connection failures

### 🧪 **Test Categories**
- **Happy Path**: Normal operation scenarios
- **Error Handling**: API failures, connection issues, timeouts
- **Edge Cases**: Malformed data, empty responses, large inputs
- **Async Operations**: Proper async/await testing patterns

### 📊 **High Coverage Targets**
- **100% line coverage** for all three modules
- **Branch coverage** for conditional logic
- **Exception path coverage** for error scenarios

## Quick Start

### 1. Install Dependencies
```bash
# Install test dependencies
python run_tests.py --install-deps

# Or manually:
pip install pytest pytest-mock pytest-asyncio fakeredis pytest-cov
```

### 2. Run All Tests
```bash
# With coverage report
python run_tests.py

# Without coverage
python run_tests.py --no-coverage

# Generate HTML coverage report
python run_tests.py --html
```

### 3. Run Specific Module Tests
```bash
# Test only LLM client
python run_tests.py --module llm

# Test only Weaviate client  
python run_tests.py --module weaviate

# Test only Conversation Manager
python run_tests.py --module conversation
```

### 4. Development Mode
```bash
# Fail fast on first error
python run_tests.py --fail-fast

# Quiet output
python run_tests.py --quiet

# Specific test file
python run_tests.py tests/test_llm_client.py
```

## Test Details

### ConversationManager Tests (`test_conversation_manager.py`)

**Coverage Areas:**
- ✅ Conversation CRUD operations (create, read, update, delete)
- ✅ Message management (add, retrieve, count)
- ✅ User conversation history
- ✅ Redis pipeline operations
- ✅ TTL and expiration handling
- ✅ JSON serialization/deserialization
- ✅ Error handling (connection failures, timeouts)
- ✅ Edge cases (malformed data, special characters, long content)

**Key Test Scenarios:**
```python
# Test conversation creation with context
await manager.create_conversation("user-123", {"camera": "main_entrance"})

# Test message round-trip
message_id = await manager.add_message(conv_id, "user", "Show security events")
messages = await manager.get_recent_messages(conv_id)

# Test Redis connection failures
redis_client.get.side_effect = redis.ConnectionError("Connection failed")
```

### LLM Client Tests (`test_llm_client.py`)

**Coverage Areas:**
- ✅ Conversational response generation
- ✅ Follow-up question generation  
- ✅ Proactive insights generation
- ✅ OpenAI API integration
- ✅ Context building and enhancement
- ✅ Confidence score calculation
- ✅ Error handling (API errors, malformed responses)
- ✅ Helper function validation

**Key Test Scenarios:**
```python
# Test successful response generation
result = generate_conversational_response(
    query="What security events happened today?",
    conversation_history=history,
    search_results=events
)

# Test API error handling
mock_client.chat.completions.create.side_effect = Exception("API Error")

# Test follow-up generation
questions = generate_follow_up_questions(query, response, history, results)
```

### Weaviate Client Tests (`test_weaviate_client.py`)

**Coverage Areas:**
- ✅ Semantic search operations
- ✅ Pattern analysis and temporal search
- ✅ Related event discovery
- ✅ Client initialization and connection handling
- ✅ Query enhancement with conversation context
- ✅ Filter building and where clauses
- ✅ Relevance score calculation
- ✅ Error handling (connection failures, malformed objects)

**Key Test Scenarios:**
```python
# Test semantic search with filters
results = semantic_search(
    query="person detected at entrance",
    filters={"camera_id": "cam-001", "min_confidence": 0.8}
)

# Test pattern analysis
analysis = semantic_search_with_patterns(
    query="security events", 
    include_patterns=True,
    time_window_hours=24
)

# Test connection failure handling
mock_get_client.return_value = None  # Simulate unavailable client
```

## Fixtures and Test Data

### Core Fixtures (`conftest.py`)
```python
@pytest.fixture
def fake_redis():
    """Fake Redis server for testing"""
    return fakeredis.FakeRedis()

@pytest.fixture  
def mock_openai_response():
    """Mock OpenAI API response"""
    response = Mock()
    response.choices[0].message.content = "Test AI response"
    return response

@pytest.fixture
def sample_search_results():
    """Sample Weaviate search results"""
    return [
        {
            "event_id": "event-001",
            "camera_id": "cam-001", 
            "event_type": "person_detected",
            "confidence": 0.95
        }
    ]
```

## Error Simulation

The tests extensively simulate various failure scenarios:

### Redis Failures
```python
# Connection errors
redis_client.get.side_effect = redis.ConnectionError("Connection failed")

# Timeout errors  
redis_client.setex.side_effect = redis.TimeoutError("Timeout")

# Data corruption
redis_client.get.return_value = b"invalid-json"
```

### OpenAI API Failures
```python
# Rate limiting
mock_client.side_effect = openai.error.RateLimitError("Rate limited")

# Invalid responses
response.choices[0].message.content = "Not valid JSON"

# Network errors
mock_client.side_effect = Exception("Network error")
```

### Weaviate Failures
```python  
# Connection unavailable
mock_get_client.return_value = None

# Search errors
collection.query.near_text.side_effect = Exception("Search failed")

# Malformed objects
obj.properties = {}  # Missing required fields
obj.metadata = None  # No metadata
```

## Coverage Reports

### Terminal Output
```bash
Name                     Stmts   Miss  Cover   Missing
----------------------------------------------------
conversation_manager.py    85      0   100%
llm_client.py             120      0   100%  
weaviate_client.py        140      0   100%
----------------------------------------------------
TOTAL                     345      0   100%
```

### HTML Report  
```bash
python run_tests.py --html
# Open htmlcov/index.html in browser
```

## CI/CD Integration

### GitHub Actions
The `.github/workflows/test.yml` file provides:
- ✅ Multi-Python version testing (3.9, 3.10, 3.11)
- ✅ Automated dependency installation
- ✅ Coverage reporting with Codecov integration
- ✅ PR comment with coverage changes
- ✅ Lint checking with flake8

### Local Pre-commit
```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
cd enhanced_prompt_service
python run_tests.py --fail-fast --quiet
```

## Best Practices

### ✅ **Do's**
- Mock all external dependencies (Redis, OpenAI, Weaviate)
- Test both success and failure scenarios  
- Use realistic test data that matches production patterns
- Test async functions with proper `@pytest.mark.asyncio`
- Verify mock calls and arguments
- Test edge cases and boundary conditions

### ❌ **Don'ts**  
- Don't make real API calls in unit tests
- Don't test implementation details, focus on behavior
- Don't ignore test failures or reduce coverage
- Don't create interdependent tests
- Don't hardcode sensitive data in tests

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Make sure you're in the right directory
cd enhanced_prompt_service

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Async Test Failures**
```python 
# Always use @pytest.mark.asyncio for async tests
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

**Mock Not Working**
```python
# Patch at the right location (where imported, not where defined)
@patch('llm_client.client')  # Not 'openai.OpenAI'
def test_function(mock_client):
    pass
```

**Redis Fake Issues**
```python
# Use fakeredis.FakeRedis(), not fakeredis.FakeStrictRedis()
fake_redis = fakeredis.FakeRedis()
```

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_[function_name]_[scenario]`
2. **Add docstrings**: Explain what each test validates
3. **Update fixtures**: Add new test data to `conftest.py` if reusable
4. **Maintain coverage**: Ensure new code has corresponding tests
5. **Test error paths**: Don't just test happy paths

### Example Test Template
```python
@pytest.mark.asyncio
async def test_function_name_success_scenario(self, fixture1, fixture2):
    """Test successful execution of function_name with valid inputs."""
    # Arrange
    mock_dependency.method.return_value = expected_value
    
    # Act  
    result = await function_under_test(input_params)
    
    # Assert
    assert result == expected_result
    mock_dependency.method.assert_called_once_with(expected_args)
```

---

**Target Achievement: 100% unit test coverage across all three critical modules** ✅
