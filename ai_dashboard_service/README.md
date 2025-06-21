# AI Dashboard Service

The AI Dashboard Service provides advanced analytics, predictive insights, and intelligent reporting capabilities for surveillance systems. It serves as the intelligence layer of the surveillance system, leveraging OpenAI's GPT models to provide actionable insights and automated reporting.

## Features

- **Advanced Analytics**: Trend analysis, anomaly detection, and pattern recognition
- **Predictive Insights**: Forecasting for security threats, equipment failures, traffic patterns, and occupancy levels  
- **Intelligent Reporting**: AI-powered report generation with summaries and recommendations
- **Real-time Insights**: Live monitoring with AI-driven alerts and notifications
- **Dynamic Widgets**: Customizable dashboard components for data visualization
- **RESTful API**: Clean, well-documented API endpoints for easy integration

## Prerequisites

- **Python 3.11+**: The service is built and tested with Python 3.11
- **Redis**: Required for caching and session storage
- **PostgreSQL**: Database for persistent storage of reports and analytics
- **OpenAI API Key**: Required for AI-powered insights and report generation
- **Docker** (optional): For containerized deployment

## Quick Start

1. **Clone and Navigate**:
   ```bash
   git clone https://github.com/your-org/surveillance-system.git
   cd surveillance-system/ai_dashboard_service
   ```

2. **Environment Setup**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration values
   ```

3. **Docker Deployment** (Recommended):
   ```bash
   docker build -t ai_dashboard_service .
   docker run -d --env-file .env -p 8004:8004 ai_dashboard_service
   ```

4. **Local Development**:
   ```bash
   pip install -r requirements.txt
   python -m app.main
   ```

5. **Verify Installation**:
   ```bash
   curl http://localhost:8004/health
   ```

The service will be available at `http://localhost:8004` with API documentation at `http://localhost:8004/docs`.

## Architecture Overview

The service has been modularized into the following packages:

```
ai_dashboard_service/
├── app/                    # Main application package
│   ├── __init__.py
│   ├── main.py            # FastAPI application entry point
│   ├── models/            # Pydantic models and data schemas
│   │   ├── __init__.py
│   │   ├── enums.py       # Enumeration types
│   │   └── schemas.py     # Request/response models
│   ├── services/          # Business logic and external integrations
│   │   ├── __init__.py
│   │   ├── analytics.py   # Analytics engine
│   │   ├── llm_client.py  # OpenAI client
│   │   ├── predictive.py  # Predictive analytics engine
│   │   └── reports.py     # Report generation engine
│   ├── routers/           # FastAPI route handlers
│   │   ├── __init__.py
│   │   └── dashboard.py   # Dashboard API endpoints
│   └── utils/             # Shared utilities
│       ├── __init__.py
│       ├── database.py    # Database connections
│       └── helpers.py     # Helper functions
├── config/                # Configuration management
│   ├── __init__.py
│   └── config.py          # Pydantic settings
├── tests/                 # Test suite
├── docs/                  # Documentation
├── Dockerfile
├── requirements.txt
└── README.md
```

## API Documentation

### Core Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/health` | GET | Health check endpoint |
| `/api/v1/analytics/trends` | POST | Analyze trends in surveillance data |
| `/api/v1/analytics/anomalies` | POST | Detect anomalies in surveillance data |
| `/api/v1/predictions` | POST | Generate predictive analytics |
| `/api/v1/reports/generate` | POST | Generate intelligent surveillance reports |
| `/api/v1/reports/{report_id}` | GET | Retrieve generated reports |
| `/api/v1/insights/realtime` | GET | Get real-time AI insights |
| `/api/v1/widgets/create` | POST | Create dashboard widgets |
| `/api/v1/widgets` | GET | List dashboard widgets |
| `/api/v1/dashboard/summary` | GET | Get AI-powered dashboard summary |

### Interactive Documentation

- **Swagger UI**: `http://localhost:8004/docs`
- **ReDoc**: `http://localhost:8004/redoc`
- **Detailed API Guide**: `docs/API.md`

## Documentation

- **API Reference**: `docs/API.md` - Complete API documentation with examples
- **Deployment Guide**: `docs/DEPLOYMENT.md` - Production deployment instructions  
- **Architecture**: `docs/ARCHITECTURE.md` - System architecture and design
- **Setup Guide**: `docs/SETUP.md` - Detailed setup instructions

## Configuration

The service uses environment variables for configuration. Copy `.env.example` to `.env` and configure the following variables:

```env
# OpenAI API Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Database Configuration  
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/surveillance

# Redis Configuration
REDIS_URL=redis://localhost:6379/8

# Service Configuration
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8004

# Analytics Configuration
ANOMALY_THRESHOLD=2.0
PREDICTION_CACHE_TTL=3600

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
```

See `.env.example` for a complete list of configuration options.

## Installation & Setup

### Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Environment Variables**: 
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start Required Services**:
   ```bash
   # Start Redis
   docker run -d -p 6379:6379 redis:alpine
   
   # Start PostgreSQL
   docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:15
   ```

4. **Run the Service**:
   ```bash
   python -m app.main
   ```

   Or with uvicorn directly:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
   ```

### Production Deployment

See `docs/DEPLOYMENT.md` for detailed production deployment instructions.

## Docker Support

### Build and Run

```bash
# Build the Docker image
docker build -t ai_dashboard_service .

# Run with environment file
docker run -d --name ai_dashboard --env-file .env -p 8004:8004 ai_dashboard_service

# Or run with Docker Compose (see docs/DEPLOYMENT.md)
docker-compose up -d
```

### Health Check

The container includes health checks:
```bash
docker ps  # Check container health status
curl http://localhost:8004/health  # Manual health check
```

## Development

The service is structured for easy development and testing:

### Project Structure
- **Models**: Define new data models in `app/models/`
- **Services**: Add business logic in `app/services/`  
- **Routes**: Create new API endpoints in `app/routers/`
- **Utils**: Add shared utilities in `app/utils/`

### Code Quality
```bash
# Run linting
black --check .
isort --check-only .
flake8 .

# Run type checking
mypy .

# Auto-format code
black .
isort .
```

### Testing
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_analytics.py -v
```

## Dependencies

- **FastAPI** - Modern web framework for APIs
- **Pydantic** - Data validation and settings management
- **OpenAI** - AI/LLM integration for intelligent insights
- **Redis** - Caching and session storage
- **PostgreSQL** - Database for persistent storage
- **SQLAlchemy** - Database ORM
- **NumPy** - Numerical computations for analytics

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the project structure
4. Run tests and linting (`pytest && black . && isort .`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Testing

Run tests with:
```bash
pytest tests/
```

## Documentation

- API documentation is available at `/docs` when the service is running
- Architecture details are in `docs/ARCHITECTURE.md`
- Setup instructions are in `docs/SETUP.md`
