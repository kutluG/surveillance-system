# Quick Start Guide - Surveillance System

## 🚀 Get Started in 5 Minutes

### Prerequisites
- **Docker Desktop** (Windows/Mac) or **Docker + Docker Compose** (Linux)
- **Git** for version control
- **8GB+ RAM** recommended for full stack

### Step 1: Clone and Setup
```bash
# Clone the repository
git clone https://github.com/kutluG/surveillance-system.git
cd surveillance-system

# Copy environment configuration
cp .env.example .env

# Edit .env file with your settings (especially OPENAI_API_KEY)
notepad .env  # Windows
# OR
nano .env     # Linux/Mac
```

### Step 2: Configure Your API Key
```bash
# REQUIRED: Set your OpenAI API key in .env file
OPENAI_API_KEY=your-actual-openai-api-key-here
```

### Step 3: Start the System
```bash
# Option 1: Quick start (recommended for first time)
make quick-start

# Option 2: Manual setup
make env           # Create .env from template
make up-infra      # Start infrastructure services
# Wait 30 seconds for services to initialize
make up-apps       # Start application services
```

### Step 4: Verify Installation
```bash
# Check service health
make health

# View logs
make logs

# Open monitoring dashboards
make dashboard
```

## 📊 Access Points

Once started, access the system at:

| Service | URL | Description |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | Monitoring dashboards (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics collection |
| **Edge Service** | http://localhost:8001/docs | Video processing API |
| **RAG Service** | http://localhost:8004/docs | AI analysis API |
| **Notifier** | http://localhost:8007/docs | Notification system |
| **VMS Service** | http://localhost:8008/docs | Video management |

## 🔧 Common Commands

```bash
# Development workflow
make build         # Build all services
make up           # Start all services
make down         # Stop all services
make restart      # Restart all services
make logs         # View all logs
make clean        # Clean up resources

# Individual services
make logs-service SERVICE=edge_service
make restart-service SERVICE=rag_service

# Testing
make test          # Run all tests
make test-service SERVICE=edge_service

# Database management
make db-shell      # Access PostgreSQL
make db-backup     # Backup database
```

## 🎥 Camera Setup

### Webcam (Default)
```bash
# Already configured in .env
CAPTURE_DEVICE=0
```

### IP Camera (RTSP)
```bash
# Edit .env file
CAPTURE_DEVICE=rtsp://192.168.1.100:554/stream
CAMERA_ID=ip-camera-01
```

### Multiple Cameras
```bash
# Scale the edge service
docker-compose up --scale edge_service=3
```

## 🔔 Notifications

Configure notifications in `.env`:

```bash
# Email
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

## 🐛 Troubleshooting

### Services won't start
```bash
# Check Docker status
docker info

# View service logs
make logs-service SERVICE=postgres

# Reset everything
make reset
```

### OpenAI API errors
```bash
# Verify API key in .env
grep OPENAI_API_KEY .env

# Test the API
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.openai.com/v1/models
```

### Camera not detected
```bash
# Linux: Check camera permissions
ls -la /dev/video*
sudo usermod -a -G video $USER

# Windows: Ensure camera isn't used by other apps
```

### Port conflicts
```bash
# Check what's using ports
netstat -tulpn | grep :3000

# Modify docker-compose.yml to use different ports
```

## 📱 Next Steps

1. **Configure your camera** - Update `CAPTURE_DEVICE` in `.env`
2. **Set up notifications** - Add email/Slack credentials
3. **Train custom models** - Add your detection models to `/models`
4. **Create custom rules** - Use the Rule Generation service
5. **Monitor the system** - Check Grafana dashboards

## 🆘 Getting Help

- **Documentation**: Check service READMEs in each directory
- **Health checks**: `make health` shows service status
- **Logs**: `make logs` for detailed troubleshooting
- **Issues**: Open GitHub issues for bugs/questions

## 🏗️ Development

```bash
# Set up development environment
make setup

# Run tests
make test

# Code formatting
make format

# Linting
make lint
```

---

**🎉 Congratulations!** Your surveillance system is now running. 

Monitor the dashboard at http://localhost:3000 and check the API documentation at http://localhost:800X/docs for each service.
