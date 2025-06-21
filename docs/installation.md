# Installation Guide

This guide covers the installation and setup of the AI-Powered Surveillance System.

## 🔧 Prerequisites

### System Requirements
- **OS**: Linux Ubuntu 20.04+ (recommended), Windows 10+, or macOS 11+
- **CPU**: 4+ cores (8+ cores recommended for ML workloads)
- **RAM**: 16GB minimum (32GB recommended)
- **Storage**: 100GB+ available space
- **GPU**: NVIDIA GPU with CUDA support (optional but recommended for AI processing)

### Software Dependencies
- **Docker**: 20.10+ with Docker Compose v2
- **Python**: 3.9+ (if running without Docker)
- **Node.js**: 16+ (for frontend development)
- **Git**: Latest version

## 🚀 Quick Installation (Docker)

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/surveillance-system.git
cd surveillance-system
```

### 2. Environment Setup
```bash
# Copy the example environment file
cp .env.example .env

# Edit configuration (see Configuration section)
nano .env
```

### 3. Start the System
```bash
# Development environment
docker-compose -f docker-compose.dev.yml up -d

# Production environment
docker-compose up -d
```

### 4. Verify Installation
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Access the web interface
open http://localhost:8080
```

## 🔧 Manual Installation

### 1. Python Services Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize databases
python scripts/init_db.py
```

### 2. Frontend Setup
```bash
cd annotation_frontend
npm install
npm run build
```

### 3. Start Services
```bash
# Start core services (in separate terminals)
python vms_service/main.py
python api_gateway/main.py
python annotation_service/main.py
python ai_dashboard_service/main.py
```

## 🐳 Docker Installation Details

### Development Setup
```bash
# Start with hot reload and debug ports
docker-compose -f docker-compose.dev.yml up -d

# Rebuild specific service
docker-compose -f docker-compose.dev.yml build vms-service
docker-compose -f docker-compose.dev.yml up -d vms-service
```

### Production Setup
```bash
# Production optimized containers
docker-compose up -d

# Scale specific services
docker-compose up -d --scale ai-processor=3
```

### Data Persistence
The system uses Docker volumes for data persistence:
- `surveillance_data`: Video files and metadata
- `surveillance_db`: Database files
- `surveillance_logs`: Application logs
- `surveillance_models`: ML models and cache

## ⚙️ Configuration

### Environment Variables
Key configuration options in `.env`:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=surveillance
POSTGRES_USER=surveillance_user
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# Security
JWT_SECRET_KEY=your_jwt_secret
API_KEY=your_api_key
ENCRYPTION_KEY=your_encryption_key

# AI/ML
CUDA_VISIBLE_DEVICES=0
MODEL_CACHE_DIR=/app/models
INFERENCE_BATCH_SIZE=4

# Monitoring
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
```

### Service Ports
| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | Main API endpoint |
| Web Interface | 8080 | Frontend application |
| VMS Service | 8001 | Video management |
| Annotation Service | 8002 | Annotation API |
| AI Dashboard | 8003 | AI analytics dashboard |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Monitoring dashboard |

## 🔒 Security Setup

### SSL/TLS Configuration
```bash
# Generate certificates (for production)
mkdir -p certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/server.key -out certs/server.crt

# Update docker-compose.yml to use HTTPS
```

### Authentication Setup
```bash
# Create initial admin user
python scripts/create_admin_user.py

# Configure OAuth (optional)
# See docs/security.md for details
```

## 📊 Monitoring Setup

### Prometheus Configuration
```bash
# Prometheus config is in monitoring/prometheus/
# Grafana dashboards in monitoring/grafana/dashboards/
```

### Log Aggregation
```bash
# ELK Stack (optional)
docker-compose -f docker-compose.elk.yml up -d
```

## 🧪 Verify Installation

### Health Checks
```bash
# Check all services
curl http://localhost:8000/health

# Check specific services
curl http://localhost:8001/health  # VMS
curl http://localhost:8002/health  # Annotations
curl http://localhost:8003/health  # AI Dashboard
```

### Test Upload
```bash
# Upload test video
curl -X POST "http://localhost:8000/api/v1/videos/upload" \
  -H "Authorization: Bearer $API_TOKEN" \
  -F "file=@test_video.mp4"
```

## 🐛 Troubleshooting

### Common Issues

#### Docker Issues
```bash
# Reset Docker environment
docker-compose down -v
docker system prune -a
docker-compose up -d
```

#### Permission Issues
```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/
sudo chmod -R 755 data/
```

#### Port Conflicts
```bash
# Check port usage
netstat -tulnp | grep :8000

# Stop conflicting services
sudo systemctl stop apache2  # If using port 80
```

#### Database Connection Issues
```bash
# Check database container
docker-compose logs postgres

# Reset database
docker-compose down
docker volume rm surveillance_db
docker-compose up -d postgres
```

### Log Locations
- **Docker logs**: `docker-compose logs [service-name]`
- **Application logs**: `logs/` directory
- **Service logs**: Each service's `logs/` subdirectory

## 📚 Next Steps

1. **Configure your environment**: Review and customize `.env` file
2. **Set up monitoring**: Configure Prometheus and Grafana
3. **Add cameras**: Connect your IP cameras or video sources
4. **Create users**: Set up user accounts and permissions
5. **Configure AI models**: Download and configure ML models
6. **Test the system**: Upload test videos and verify processing

## 🆘 Support

- **Documentation**: See [docs/](index.md) for detailed guides
- **Issues**: Report bugs on GitHub Issues
- **Community**: Join our Discord/Slack for support
- **Commercial**: Contact support@surveillance-system.com

---

**Next**: [Configuration Guide](configuration.md) | [Quick Start](quickstart.md)
