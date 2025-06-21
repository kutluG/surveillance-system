# AI-Powered Surveillance System Documentation

Welcome to the comprehensive documentation for the AI-Powered Surveillance System. This documentation provides everything you need to understand, deploy, use, and contribute to the system.

## 🚀 Getting Started

New to the system? Start here:

- **[Quick Start Guide](quickstart.md)** - Get up and running in minutes
- **[Architecture Overview](architecture.md)** - Understand the system design
- **[API Reference](api.md)** - Complete API documentation

## 📚 User Guides

Step-by-step guides for different user roles:

- **[Annotation User Guide](annotation_user_guide.md)** - Human annotation interface
- **[Dashboard Usage](dashboard-guide.md)** - Analytics and monitoring
- **[Mobile App Guide](mobile-guide.md)** - iOS/Android app usage
- **[Voice Interface](voice-guide.md)** - Voice-controlled interactions

## 🔧 Technical Documentation

Deep dive into technical details:

- **[System Architecture](architecture.md)** - Microservices design and data flow
- **[API Documentation](api.md)** - RESTful APIs and WebSocket endpoints
- **[Security Guide](security.md)** - Authentication, authorization, and compliance
- **[Deployment](deployment.md)** - Production deployment instructions

## 🤖 Machine Learning

AI and ML aspects of the system:

- **[Model Training](ml-training.md)** - Training AI models
- **[Continuous Learning](continuous_learning/)** - Human-in-the-loop improvement
- **[MLflow Integration](mlflow-quickstart.md)** - Model versioning and tracking
- **[Performance Metrics](ml-metrics.md)** - Model evaluation and monitoring

## 🛠️ Development

For developers and contributors:

- **[Development Setup](dev-setup.md)** - Local development environment
- **[Contributing Guide](contributing.md)** - How to contribute to the project
- **[Testing](testing.md)** - Testing strategies and tools
- **[Integration Guide](integration.md)** - Third-party integrations

## 🔍 Operations

For system administrators and DevOps:

- **[Monitoring](monitoring.md)** - System health and performance monitoring
- **[Logging](logging.md)** - Structured logging and audit trails
- **[Backup & Recovery](backup.md)** - Data protection and disaster recovery
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

## 📖 Quick Reference

Frequently accessed information:

### Core Services Ports
- **API Gateway**: `http://localhost:8000`
- **VMS Service**: `http://localhost:8001`
- **Agent Orchestrator**: `http://localhost:8002`
- **Dashboard Service**: `http://localhost:8003`
- **Annotation Frontend**: `http://localhost:8011`

### Common Commands
```bash
# Start the entire system
docker-compose up -d

# View service logs
docker-compose logs -f annotation_frontend

# Check service health
curl http://localhost:8000/health

# Run tests
pytest
```

### Key Concepts
- **Hard Examples**: Difficult cases requiring human annotation
- **Continuous Learning**: AI improvement through human feedback
- **WORM Logging**: Write-once, read-many audit trails
- **GDPR Compliance**: Privacy-focused data handling

## 🆘 Getting Help

Need assistance?

- **Documentation Issues**: [Create an issue](https://github.com/your-org/surveillance-system/issues)
- **Technical Support**: support@surveillance-system.com
- **Community Discussions**: [GitHub Discussions](https://github.com/your-org/surveillance-system/discussions)

## 📊 System Status

- **Current Version**: v1.0.0
- **Documentation Version**: Latest
- **Last Updated**: June 16, 2025
- **Compatibility**: Python 3.8+, Docker 20.10+, Node.js 16+

---

*This documentation is automatically built and deployed. Report issues or suggest improvements through our [GitHub repository](https://github.com/your-org/surveillance-system).*
