# Enhanced Prompt Service

A sophisticated conversational AI service that provides intelligent, context-aware responses for surveillance system queries. This service combines semantic search, large language models, and conversation memory to deliver enhanced user experiences.

## 🎯 Core Capabilities

- **Semantic Search**: Advanced vector-based search through surveillance events using Weaviate
- **Conversational AI**: OpenAI-powered responses with conversation context and memory
- **Clip Integration**: Automatic video clip URL generation and metadata retrieval
- **Follow-up Questions**: Intelligent suggestion of relevant next questions
- **Proactive Insights**: Pattern detection and anomaly identification
- **Multi-turn Conversations**: Redis-backed conversation history and context management

## 📋 Prerequisites

- **Python**: 3.11+
- **Redis**: 5.0+ (for conversation memory)
- **Weaviate**: 1.20+ (for semantic search)
- **OpenAI API Key**: For GPT-4 integration
- **Docker**: For containerized deployment (optional)

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the repository
cd surveillance-system/enhanced_prompt_service

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 2. Required Environment Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Weaviate Configuration
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=your_weaviate_api_key

# Service Configuration
VMS_SERVICE_URL=http://localhost:8001
CLIP_BASE_URL=http://localhost:8001/clips
DEFAULT_CLIP_EXPIRY_MINUTES=60

# Authentication
JWT_SECRET_KEY=your_jwt_secret_key_here
```

### 3. Docker Deployment (Recommended)

```bash
# Start the service with dependencies
docker-compose up -d enhanced_prompt_service

# View logs
docker-compose logs -f enhanced_prompt_service
```

### 4. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start the service
uvicorn enhanced_prompt_service.main:app --reload --host 0.0.0.0 --port 8000

# Service will be available at http://localhost:8000
```

### 5. Quick Start Commands

```bash
# Copy environment template and configure
cp .env.example .env

# Start with Docker Compose
docker-compose up -d enhanced_prompt_service

# Start locally with uvicorn
uvicorn enhanced_prompt_service.main:app --reload
```

### 5. Health Check

```bash
curl http://localhost:8000/health
# Expected response: {"status": "ok"}
```

## 📚 Documentation

- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete REST API reference
- **[Integration Guide](docs/INTEGRATION.md)** - How to integrate with other services
- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design and patterns
- **[OpenAPI Specification](docs/enhanced_prompt_openapi.json)** - Machine-readable API spec

## 🔧 Configuration

The service uses a hierarchical configuration system:

1. **Default values** (in `shared/config.py`)
2. **Environment variables** (`.env` file or system environment)
3. **Runtime overrides** (for testing/development)

### Key Configuration Areas

- **LLM Settings**: Model selection, temperature, token limits
- **Search Parameters**: Result limits, confidence thresholds
- **Conversation Memory**: TTL settings, history depth
- **Rate Limiting**: Request limits per user/IP
- **Monitoring**: Metrics collection, logging levels

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │───▶│ Enhanced Prompt  │───▶│    Weaviate     │
│                 │    │    Service       │    │ (Semantic Search)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ├─────────▶┌─────────────────┐
                                │          │     OpenAI      │
                                │          │   (LLM API)     │
                                │          └─────────────────┘
                                │
                                ├─────────▶┌─────────────────┐
                                │          │      Redis      │
                                │          │ (Conversation)  │
                                │          └─────────────────┘
                                │
                                └─────────▶┌─────────────────┐
                                           │   Clip Store    │
                                           │ (Video URLs)    │
                                           └─────────────────┘
```

## 🚦 Service Status

- **Health Endpoint**: `GET /health`
- **Metrics**: Prometheus metrics available at `/metrics`
- **Logs**: Structured JSON logs with correlation IDs

## 🔐 Security

- **JWT Authentication**: All endpoints require valid JWT tokens
- **Rate Limiting**: Configurable per-user request limits
- **Input Validation**: Pydantic models for request validation
- **Audit Logging**: All requests tracked with user context

## 🧪 Testing

```bash
# Run unit tests
pytest enhanced_prompt_service/tests/

# Run integration tests
pytest enhanced_prompt_service/tests/integration/

# Run with coverage
pytest --cov=enhanced_prompt_service --cov-report=html
```

## 📊 Monitoring

The service provides comprehensive observability:

- **Metrics**: Request counts, latency, error rates
- **Tracing**: Distributed tracing with correlation IDs
- **Health Checks**: Liveness and readiness probes
- **Dashboards**: Grafana dashboards for operational visibility

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `docs/` directory for detailed guides
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Join technical discussions in GitHub Discussions

## 🔄 Version History

- **v1.0.0** - Initial release with basic conversational AI
- **v1.1.0** - Added proactive insights and pattern detection
- **v1.2.0** - Enhanced conversation memory and follow-up questions
- **v1.3.0** - Improved error handling and monitoring
