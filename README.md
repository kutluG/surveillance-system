# Surveillance System

A comprehensive, microservices-based surveillance system built with Python, featuring AI-powered video analysis, intelligent notifications, and scalable architecture.

## Overview

This surveillance system is designed as a distributed, cloud-native application that processes video streams, performs AI-based analysis, and provides intelligent alerting capabilities. The system is built using a microservices architecture with Docker containers and includes monitoring, data persistence, and real-time processing capabilities.

## Architecture

The system consists of the following microservices:

### Core Services
- **Edge Service** - Video stream processing and AI inference at the edge
- **VMS Service** - Video Management System for clip generation and storage
- **Ingest Service** - Data ingestion and initial processing pipeline
- **Prompt Service** - AI prompt management and processing
- **RAG Service** - Retrieval-Augmented Generation for intelligent responses
- **Rule Generation Service** - Dynamic rule creation and management
- **Notifier** - Multi-channel notification system

### Infrastructure Services
- **MQTT-Kafka Bridge** - Message broker integration
- **Monitoring** - Prometheus and Grafana-based monitoring stack
- **Shared Libraries** - Common utilities, authentication, and configuration

## Features

- 🎥 Real-time video stream processing
- 🤖 AI-powered object detection and analysis
- 📊 Comprehensive monitoring and alerting
- 🔔 Multi-channel notifications (email, SMS, webhooks)
- 📈 Scalable microservices architecture
- 🐳 Containerized deployment with Docker
- 📝 Dynamic rule generation and management
- 🔍 Vector-based search and retrieval
- ⚡ High-performance edge computing

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd surveillance-system
```

2. Configure environment variables:
```bash
cp .env.example .env
```

3. Set up the development environment:
```bash
./scripts/setup-dev.sh
```

4. Start the system:
```bash
./scripts/start-system.sh
```

5. Stop the system:
```bash
./scripts/stop-system.sh
```

## Services Overview

### Edge Service
Handles video stream processing at the edge with AI inference capabilities.
- Real-time video analysis
- MQTT communication
- Preprocessing and inference pipelines

### VMS Service
Video Management System for clip storage and retrieval.
- Clip generation and storage
- Video metadata management
- Storage optimization

### Ingest Service
Primary data ingestion pipeline with database integration.
- Data validation and processing
- Weaviate vector database integration
- Batch and stream processing

### Prompt Service
AI prompt management and processing service.
- Dynamic prompt generation
- Context-aware processing
- Integration with vector databases

### RAG Service
Retrieval-Augmented Generation for intelligent responses.
- Vector similarity search
- LLM integration
- Context-aware responses

### Rule Generation Service
Dynamic rule creation and management system.
- Intelligent rule generation
- Rule validation and testing
- Integration with monitoring systems

### Notifier
Multi-channel notification system.
- Email notifications
- SMS alerts
- Webhook integrations
- Notification templating

## Configuration

Configuration files are located in each service directory. Key configuration includes:

- Database connections
- MQTT/Kafka settings
- AI model configurations
- Notification channels
- Monitoring thresholds

# Environment Variables and Secrets
Before running the system, copy the example file and configure your secrets:

```bash
cp .env.example .env  # or copy in PowerShell: Copy-Item .env.example .env
# Then edit .env and set values for:
# - DATABASE_URL or POSTGRES_* variables
# - REDIS_URL
# - KAFKA_BROKER and related Kafka settings
# - OPENAI_API_KEY and other AI credentials
# - JWT_SECRET_KEY, SMTP_USERNAME/PASSWORD, AWS credentials, etc.
```

Ensure that the `.env` file is listed in `.gitignore` so secrets are not committed.

## Monitoring

The system includes comprehensive monitoring with:

- **Prometheus** - Metrics collection
- **Grafana** - Visualization dashboards
- **Health checks** - Service availability monitoring
- **Performance monitoring** - System resource tracking

Access Grafana dashboard at: `http://localhost:3000`

## Development

### Running Tests
```bash
# Run all tests
python -m pytest

# Run service-specific tests
cd <service-name>
python -m pytest tests/
```

### Adding New Services
1. Create service directory
2. Add Dockerfile and requirements.txt
3. Implement service logic
4. Add tests
5. Update docker-compose.yml
6. Update monitoring configuration

## Deployment

### Production Deployment
```bash
./scripts/deployment/deploy.sh
```

### Health Checks
```bash
python scripts/deployment/health_check.py
```

## Data Migration

For database migrations:
```bash
python scripts/data_migration/migrate_v1_to_v2.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue in the GitHub repository.
