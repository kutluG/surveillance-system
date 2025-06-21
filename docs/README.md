# Documentation Overview

This directory contains the comprehensive documentation for the AI-Powered Surveillance System.

## 📚 Available Documentation

### ✅ Complete Documentation
- **[index.md](index.md)** - Documentation landing page
- **[architecture.md](architecture.md)** - System architecture and design
- **[api.md](api.md)** - Complete API reference
- **[annotation_user_guide.md](annotation_user_guide.md)** - Annotation interface user guide
- **[quickstart.md](quickstart.md)** - Quick start guide
- **[mlflow-quickstart.md](mlflow-quickstart.md)** - MLflow integration guide
- **[integration.md](integration.md)** - System integration documentation

### 📝 Referenced in Navigation (To Be Created)
The following files are referenced in `mkdocs.yml` but need to be created:

#### Getting Started
- `installation.md` - Detailed installation guide
- `configuration.md` - Configuration options and setup

#### Architecture
- `services.md` - Individual service documentation
- `data-flow.md` - Data flow diagrams and explanations
- `security.md` - Security implementation details

#### User Guides  
- `dashboard-guide.md` - Dashboard usage guide
- `mobile-guide.md` - Mobile app user guide
- `voice-guide.md` - Voice interface guide

#### API Reference
- `api-auth.md` - Authentication API details
- `api-vms.md` - Video Management System API
- `api-annotations.md` - Annotations API
- `api-alerts.md` - Alerts API  
- `api-analytics.md` - Analytics API

#### Development
- `dev-setup.md` - Development environment setup
- `contributing.md` - Contribution guidelines (exists in root)
- `testing.md` - Testing documentation
- `deployment.md` - Deployment procedures

#### Operations
- `monitoring.md` - Monitoring and observability
- `logging.md` - Logging configuration
- `backup.md` - Backup and recovery procedures
- `troubleshooting.md` - Common issues and solutions

#### Machine Learning
- `ml-training.md` - Model training procedures
- `continuous_learning/` - Continuous learning documentation
- `ml-metrics.md` - ML performance metrics

## 🛠️ Documentation System

### MkDocs Configuration
The documentation is built using MkDocs with the Material theme. Key features:
- Material Design theme with dark/light mode
- Code syntax highlighting
- Mermaid diagram support
- Search functionality
- Navigation with tabs and sections
- Git revision dates
- Social links and feedback

### CI/CD Pipeline
Documentation is automatically:
- Link-checked for broken references
- Linted for markdown quality
- Built and deployed to GitHub Pages
- Validated on every pull request

### Building Locally
```bash
# Install dependencies
pip install mkdocs-material mkdocs-jupyter mkdocs-mermaid2-plugin mkdocs-git-revision-date-localized-plugin mkdocs-minify-plugin

# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

## 🎯 Next Steps

1. **Create missing documentation files** listed above based on project needs
2. **Review and update** existing documentation for accuracy
3. **Add diagrams and screenshots** where helpful
4. **Set up GitHub Pages** for documentation hosting
5. **Configure analytics** and feedback collection

## 📞 Contributing to Documentation

See the main [CONTRIBUTING.md](../CONTRIBUTING.md) file for guidelines on:
- Documentation standards
- Review process
- Style guide
- How to add new documentation

---

For questions about the documentation system, please create an issue or reach out to the development team.
