# Agent Orchestrator Service Documentation

## Overview

The Agent Orchestrator Service is a centralized coordination system for AI agents in the surveillance system. It has been completely refactored from a monolithic 3,400+ line main.py file into a clean, modular architecture.

## Architecture

### Directory Structure

```
agent_orchestrator/
├── api/                          # API endpoint modules
│   ├── agents.py                # Agent management endpoints
│   ├── task_endpoints.py        # Task management endpoints
│   └── health_monitoring.py     # Health and monitoring endpoints
├── core/                        # Core business logic
│   └── orchestrator.py          # Main orchestration service
├── models/                      # Data models
│   └── domain.py               # Database models and entities
├── services/                    # Service layer (extensible)
│   ├── distributed/            # Distributed orchestration features
│   ├── security/               # Authentication and authorization
│   ├── load_balancing/         # Load balancing algorithms
│   └── monitoring/             # Metrics and monitoring
├── utils/                       # Utility modules
│   ├── config.py               # Configuration management
│   └── validation.py           # Input validation
├── examples/                    # Demo files and examples
├── docs/                       # Documentation
├── tests/                      # Test files
└── main_clean.py               # Clean FastAPI application (80 lines)
```

## Key Features

### 1. Agent Management
- **Registration**: Register AI agents with capabilities and endpoints
- **Discovery**: Automatic agent discovery and capability matching
- **Health Monitoring**: Track agent status and performance
- **Load Balancing**: Distribute tasks based on agent availability

### 2. Task Orchestration
- **Task Creation**: Create tasks with priority and capability requirements
- **Assignment**: Automatic or manual task assignment to agents
- **Execution**: Coordinated task execution with retry logic
- **Monitoring**: Real-time task status tracking

### 3. Distributed Architecture
- **Redis Integration**: Shared state management across instances
- **Background Processing**: Asynchronous task processing
- **Circuit Breakers**: Fault tolerance and failure handling
- **Retry Logic**: Exponential backoff for failed operations

## API Endpoints

### Agent Management
```
POST   /api/v1/agents              # Register new agent
GET    /api/v1/agents              # List all agents
GET    /api/v1/agents/{agent_id}   # Get agent details
DELETE /api/v1/agents/{agent_id}   # Unregister agent
POST   /api/v1/agents/{agent_id}/heartbeat  # Update heartbeat
```

### Task Management
```
POST   /api/v1/tasks              # Create new task
GET    /api/v1/tasks              # List all tasks
GET    /api/v1/tasks/{task_id}    # Get task details
POST   /api/v1/tasks/{task_id}/assign    # Assign task to agent
POST   /api/v1/tasks/{task_id}/execute   # Execute task
DELETE /api/v1/tasks/{task_id}    # Cancel task
```

### Health & Monitoring
```
GET    /health                    # Basic health check
GET    /health/detailed           # Detailed health with metrics
GET    /metrics                   # System metrics
GET    /status                    # Comprehensive system status
```

## Configuration

Configuration is managed through environment variables with sensible defaults:

```python
# Service Configuration
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8006

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost/surveillance

# Service URLs
RAG_SERVICE_URL=http://advanced_rag_service:8000
RULEGEN_SERVICE_URL=http://rulegen_service:8000
NOTIFIER_SERVICE_URL=http://notifier:8000
```

## Usage Examples

### Registering an Agent
```python
import httpx

agent_data = {
    "type": "rag_agent",
    "name": "Advanced RAG Agent",
    "endpoint": "http://rag-service:8000",
    "capabilities": ["document_analysis", "question_answering"],
    "metadata": {"version": "1.0"}
}

response = httpx.post("http://localhost:8006/api/v1/agents", json=agent_data)
agent_id = response.json()["agent_id"]
```

### Creating and Executing a Task
```python
task_data = {
    "type": "document_analysis",
    "description": "Analyze security document for threats",
    "input_data": {"document_url": "https://example.com/doc.pdf"},
    "required_capabilities": ["document_analysis"],
    "priority": 1
}

# Create task
response = httpx.post("http://localhost:8006/api/v1/tasks", json=task_data)
task_id = response.json()["task_id"]

# Execute task (auto-assigns to suitable agent)
response = httpx.post(f"http://localhost:8006/api/v1/tasks/{task_id}/execute")
result = response.json()["result"]
```

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8006

CMD ["python", "main_clean.py"]
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-orchestrator
  template:
    metadata:
      labels:
        app: agent-orchestrator
    spec:
      containers:
      - name: agent-orchestrator
        image: agent-orchestrator:2.0.0
        ports:
        - containerPort: 8006
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: database-url
```

## Migration from Old Version

The refactoring consolidates multiple overlapping files:

### Removed/Consolidated Files
- `main.py` (3,457 lines) → `main_clean.py` (80 lines)
- `distributed_orchestrator.py` (2,028 lines) → Moved to `services/distributed/`
- `db_service.py` (2,088 lines) → Moved to `models/domain.py`
- 23 markdown documentation files → Single `docs/README.md`
- 8+ demo files → Moved to `examples/`

### Benefits of Refactoring
- **90% reduction** in main application file size
- **Clear separation** of concerns
- **Improved maintainability** with modular architecture
- **Better testability** with focused modules
- **Easier onboarding** for new developers
- **Reduced deployment complexity**

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

## Development

Start the service in development mode:
```bash
python main_clean.py
```

Or with auto-reload:
```bash
uvicorn main_clean:app --reload --host 0.0.0.0 --port 8006
```

## Monitoring

The service provides comprehensive monitoring:
- **Health checks** for service availability
- **Metrics collection** for performance monitoring
- **Task tracking** for operational visibility
- **Agent status** for resource management

Access the monitoring dashboard at: `http://localhost:8006/docs`

## Future Enhancements

1. **Authentication & Authorization**: Role-based access control
2. **Advanced Load Balancing**: Weighted round-robin and intelligent routing
3. **Workflow Engine**: Complex multi-step task orchestration
4. **Event Streaming**: Kafka integration for real-time events
5. **Machine Learning**: Predictive task assignment and optimization
