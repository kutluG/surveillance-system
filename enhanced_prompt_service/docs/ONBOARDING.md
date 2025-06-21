# Enhanced Prompt Service - Developer Onboarding Guide

Welcome to the Enhanced Prompt Service development team! This guide will help you quickly get up to speed with our conversational AI service for surveillance systems.

## 🎯 Service Overview

The Enhanced Prompt Service is a microservice that provides intelligent conversational interfaces for surveillance systems. It combines:

- **Semantic Search** via Weaviate vector database
- **Conversational AI** powered by OpenAI GPT-4
- **Conversation Memory** using Redis
- **Video Clip Integration** through VMS service
- **Proactive Insights** and pattern detection

## 🚀 Quick Start for New Developers

### 1. Prerequisites Check

Before starting, ensure you have:

```bash
# Required software
python --version    # Should be 3.11+
docker --version    # For containerized development
git --version       # For version control

# Required accounts/keys
echo $OPENAI_API_KEY      # OpenAI API access
echo $WEAVIATE_API_KEY    # Weaviate cloud or local setup
```

### 2. Environment Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd surveillance-system/enhanced_prompt_service

# 2. Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# 4. Copy environment template
cp .env.example .env

# 5. Edit .env with your configuration
nano .env  # Add your API keys and service URLs
```

### 3. Local Development Setup

#### Option A: Full Docker Compose (Recommended for new developers)

```bash
# Start all dependencies
docker-compose -f docker-compose.dev.yml up -d

# This starts:
# - Redis (conversation memory)
# - Weaviate (vector search)
# - Mock VMS service (for testing)
# - Enhanced Prompt Service
```

#### Option B: Hybrid Development (Service local, dependencies containerized)

```bash
# Start only dependencies
docker-compose -f docker-compose.dev.yml up -d redis weaviate mock-vms

# Run service locally for development
uvicorn enhanced_prompt_service.main:app --reload --port 8000
```

#### Option C: Full Local Development

```bash
# Install and configure Redis locally
# Install and configure Weaviate locally
# Configure all services in .env to point to localhost

# Run the service
python -m uvicorn main:app --reload
```

### 4. Verify Setup

```bash
# Health check
curl http://localhost:8000/health

# Should return: {"status": "ok"}

# Test conversation endpoint (requires JWT - see Authentication section)
curl -X POST http://localhost:8000/api/v1/conversation \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello, test query"}'
```

## 🏗️ Development Workflow

### Project Structure

```
enhanced_prompt_service/
├── main.py                 # FastAPI application and routes
├── conversation_manager.py # Multi-turn conversation logic
├── llm_client.py          # OpenAI integration
├── weaviate_client.py     # Vector search client
├── clip_store.py          # Video clip URL generation
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── .env.example          # Environment template
├── docs/                 # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── INTEGRATION.md
│   ├── ARCHITECTURE.md
│   └── enhanced_prompt_openapi.json
└── tests/                # Test suites
    ├── unit/
    ├── integration/
    └── fixtures/
```

### Development Commands

```bash
# Run tests
pytest                              # All tests
pytest tests/unit/                  # Unit tests only
pytest tests/integration/          # Integration tests
pytest --cov=. --cov-report=html   # With coverage

# Code quality
black .                            # Code formatting
isort .                           # Import sorting
flake8 .                          # Linting
mypy .                            # Type checking

# Run security audit
pip-audit

# Generate API documentation
python scripts/generate_docs.py

# Database operations (if applicable)
python scripts/setup_weaviate_schema.py
```

### Git Workflow

```bash
# 1. Create feature branch
git checkout -b feature/your-feature-name

# 2. Make changes and commit
git add .
git commit -m "feat: add new conversation feature"

# 3. Run tests and quality checks
./scripts/pre-commit-checks.sh

# 4. Push and create PR
git push origin feature/your-feature-name
# Create Pull Request via GitHub/GitLab
```

## 🧪 Testing Strategy

### Test Types

1. **Unit Tests** (`tests/unit/`)
   - Test individual functions and classes
   - Mock external dependencies
   - Fast execution (< 1s per test)

2. **Integration Tests** (`tests/integration/`)
   - Test service integrations
   - Use test databases/services
   - Moderate execution time

3. **Contract Tests** (`tests/contract/`)
   - Test API contracts
   - Validate request/response schemas
   - OpenAPI spec validation

### Running Tests

```bash
# Quick development test run
pytest tests/unit/ -v

# Full test suite with coverage
pytest --cov=enhanced_prompt_service --cov-report=html

# Test specific functionality
pytest tests/unit/test_conversation_manager.py -v

# Integration tests (requires running services)
pytest tests/integration/ -v --slow
```

### Writing Tests

```python
# Example unit test
import pytest
from unittest.mock import Mock, patch
from enhanced_prompt_service.conversation_manager import ConversationManager

@pytest.fixture
def mock_redis():
    return Mock()

def test_create_conversation(mock_redis):
    manager = ConversationManager(mock_redis)
    # ... test implementation

# Example integration test
@pytest.mark.integration
async def test_conversation_endpoint():
    # Test with real services
    async with TestClient(app) as client:
        response = await client.post("/api/v1/conversation", ...)
        assert response.status_code == 200
```

## 🔧 Configuration Management

### Environment Variables

The service uses a hierarchical configuration system:

1. **Default values** (in `config.py`)
2. **Environment variables** (`.env` file or system)
3. **Runtime overrides** (for testing)

### Adding New Configuration

```python
# In config.py
class Settings(BaseSettings):
    # Existing config...
    
    # Add new setting
    new_feature_enabled: bool = False
    new_feature_timeout: int = 30
    
    class Config:
        env_file = ".env"

# Usage in code
from config import settings

if settings.new_feature_enabled:
    # Use new feature
    pass
```

## 🎯 Common Development Tasks

### Adding a New API Endpoint

```python
# In main.py
from pydantic import BaseModel

class NewFeatureRequest(BaseModel):
    param1: str
    param2: int = 10

class NewFeatureResponse(BaseModel):
    result: str
    confidence: float

@app.post("/api/v1/new-feature", response_model=NewFeatureResponse)
async def new_feature_endpoint(
    req: NewFeatureRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Your new feature endpoint."""
    # Implementation here
    return NewFeatureResponse(result="success", confidence=0.95)
```

### Adding New Conversation Features

```python
# In conversation_manager.py
class ConversationManager:
    async def add_new_feature(self, conversation_id: str, feature_data: dict):
        """Add new conversation feature."""
        # Store in Redis
        await self.redis.hset(
            f"conversation:{conversation_id}:features",
            "new_feature",
            json.dumps(feature_data)
        )
```

### Integrating New AI Capabilities

```python
# In llm_client.py
async def generate_specialized_response(
    query: str,
    context: dict,
    response_type: str = "analysis"
) -> dict:
    """Generate specialized AI responses."""
    
    system_prompt = f"""
    You are a specialized AI assistant for {response_type}.
    Context: {context}
    
    Provide detailed analysis with:
    1. Key insights
    2. Confidence scores
    3. Recommended actions
    """
    
    # OpenAI API call
    response = await openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
    )
    
    return {"response": response.choices[0].message.content}
```

## 🚨 Troubleshooting Guide

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs
docker-compose logs enhanced-prompt-service

# Common causes:
# - Missing environment variables
# - Redis/Weaviate not accessible
# - Invalid OpenAI API key
# - Port already in use
```

#### 2. Authentication Errors

```bash
# Verify JWT token
python scripts/verify_jwt.py YOUR_JWT_TOKEN

# Check auth service connectivity
curl http://auth-service:8080/health
```

#### 3. Search Results Empty

```bash
# Check Weaviate connection
curl http://localhost:8080/v1/.well-known/ready

# Verify data in Weaviate
curl http://localhost:8080/v1/objects
```

#### 4. Redis Connection Issues

```bash
# Test Redis connectivity
redis-cli ping

# Check Redis logs
docker-compose logs redis
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debug info
python -m uvicorn main:app --reload --log-level debug
```

### Performance Debugging

```bash
# Profile API endpoints
python scripts/profile_endpoints.py

# Monitor resource usage
docker stats enhanced-prompt-service
```

## 📚 Learning Resources

### Internal Documentation

- [API Documentation](docs/API_DOCUMENTATION.md)
- [Integration Guide](docs/INTEGRATION.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [OpenAPI Specification](docs/enhanced_prompt_openapi.json)

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Weaviate Documentation](https://weaviate.io/developers/weaviate)
- [Redis Documentation](https://redis.io/documentation)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)

### Video Tutorials (Internal)

- Service Architecture Overview (30 min)
- Development Setup Walkthrough (20 min)
- Adding New Features Tutorial (45 min)
- Debugging and Troubleshooting (25 min)

## 🎯 Success Checklist

After completing this onboarding, you should be able to:

- [ ] Set up the development environment
- [ ] Run the service locally
- [ ] Execute the test suite
- [ ] Make a simple code change
- [ ] Add a new API endpoint
- [ ] Debug common issues
- [ ] Understand the service architecture
- [ ] Navigate the codebase confidently

## 🤝 Getting Help

### Team Contacts

- **Tech Lead**: [Lead Name] - lead@company.com
- **Senior Developer**: [Senior Name] - senior@company.com
- **DevOps Engineer**: [DevOps Name] - devops@company.com

### Communication Channels

- **Slack**: #enhanced-prompt-service
- **Email List**: enhanced-prompt-dev@company.com
- **Weekly Meetings**: Tuesdays 10 AM
- **Code Reviews**: GitHub PRs

### Documentation Updates

If you find outdated information or missing details:

1. Create an issue in the repository
2. Submit a PR with documentation fixes
3. Notify the team in Slack

Welcome to the team! 🎉

---

**Last Updated**: June 18, 2025  
**Document Version**: 1.0  
**Next Review**: July 18, 2025
