# AI Dashboard Service Setup Guide

## Prerequisites

- Python 3.8 or higher
- Redis server
- PostgreSQL database
- OpenAI API key

## Installation Steps

### 1. Environment Setup

Create a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the service root directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Database Configuration
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/surveillance

# Redis Configuration
REDIS_URL=redis://localhost:6379/8

# Service Configuration
CORS_ORIGINS=["http://localhost:3000", "https://your-frontend-domain.com"]
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8009
LOG_LEVEL=INFO

# Analytics Configuration
ANOMALY_THRESHOLD=2.0
PREDICTION_CACHE_TTL=3600

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
```

### 4. Database Setup

Ensure PostgreSQL is running and create the surveillance database:
```sql
CREATE DATABASE surveillance;
```

### 5. Redis Setup

Start Redis server:
```bash
redis-server
```

### 6. Running the Service

#### Development Mode
```bash
python -m app.main
```

#### Production Mode with Uvicorn
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8009
```

## Docker Setup

### Build Image
```bash
docker build -t ai-dashboard-service .
```

### Run Container
```bash
docker run -p 8009:8009 --env-file .env ai-dashboard-service
```

### Docker Compose
```yaml
version: '3.8'
services:
  ai-dashboard:
    build: .
    ports:
      - "8009:8009"
    env_file:
      - .env
    depends_on:
      - redis
      - postgres
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=surveillance
      - POSTGRES_USER=username
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
```

## Verification

### Health Check
```bash
curl http://localhost:8009/health
```

### API Documentation
Visit http://localhost:8009/docs to view the interactive API documentation.

### Test Analytics Endpoint
```bash
curl -X POST "http://localhost:8009/api/v1/analytics/trends" \
  -H "Content-Type: application/json" \
  -d '{
    "analytics_type": "trend_analysis",
    "time_range": "last_24_hours"
  }'
```

## Troubleshooting

### Common Issues

1. **OpenAI API Key Issues**
   - Ensure your API key is valid and has sufficient credits
   - Check the environment variable is properly set

2. **Database Connection Issues**
   - Verify PostgreSQL is running
   - Check database URL format and credentials
   - Ensure the database exists

3. **Redis Connection Issues**
   - Verify Redis server is running
   - Check Redis URL format

4. **Port Conflicts**
   - Ensure port 8009 is available
   - Change SERVICE_PORT in configuration if needed

### Logs

Check application logs for detailed error information:
```bash
tail -f logs/ai-dashboard.log
```

## Development Setup

### Pre-commit Hooks
```bash
pip install pre-commit
pre-commit install
```

### Running Tests
```bash
pytest tests/ -v
```

### Code Formatting
```bash
black app/
isort app/
```
