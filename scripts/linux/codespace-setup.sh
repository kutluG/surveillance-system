#!/bin/bash
# Surveillance System - Codespace Quick Setup
# Optimized for GitHub Codespaces Ubuntu environment

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}🚀 Surveillance System - Codespace Setup${NC}"
echo -e "${CYAN}=========================================${NC}"

# Update and install essential packages
echo -e "${CYAN}📦 Installing essential packages...${NC}"
sudo apt-get update -qq
sudo apt-get install -y curl wget jq python3-pip python3-venv

# Install Docker Compose (if not already installed)
if ! command -v docker-compose &> /dev/null; then
    echo -e "${CYAN}🐳 Installing Docker Compose...${NC}"
    sudo apt-get install -y docker-compose-plugin
fi

# Create environment file
echo -e "${CYAN}🔧 Setting up environment...${NC}"
cat > .env << EOF
ENVIRONMENT=development
POSTGRES_DB=events_db
POSTGRES_USER=surveillance_user
POSTGRES_PASSWORD=surveillance_pass_123
DATABASE_URL=postgresql://surveillance_user:surveillance_pass_123@postgres:5432/events_db
REDIS_URL=redis://redis:6379/0
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_PREFIX=surveillance
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET_KEY=surveillance_jwt_secret_codespace
OPENAI_API_KEY=your_openai_api_key_here
WEAVIATE_URL=http://weaviate:8080
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=admin123
VIDEO_STORAGE_PATH=./data/clips
MAX_CLIP_SIZE_MB=100
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=surveillance
MQTT_PASSWORD=mqtt_pass_123
DEBUG=true
LOG_LEVEL=INFO
EOF

# Create directories
echo -e "${CYAN}📁 Creating directories...${NC}"
mkdir -p data/{clips,postgres,redis} logs certs monitoring/{grafana,prometheus}/data

# Create Docker volumes and networks
echo -e "${CYAN}💾 Setting up Docker resources...${NC}"
docker volume create surveillance_postgres_data 2>/dev/null || true
docker volume create surveillance_redis_data 2>/dev/null || true
docker volume create surveillance_grafana_data 2>/dev/null || true
docker network create surveillance_network 2>/dev/null || true

# Start core services first (for faster startup)
echo -e "${CYAN}🚀 Starting core services...${NC}"
docker-compose up -d postgres redis

# Wait for databases
echo -e "${CYAN}⏳ Waiting for databases...${NC}"
sleep 15

# Start remaining services
echo -e "${CYAN}🌟 Starting application services...${NC}"
docker-compose up -d

# Create quick access scripts
echo -e "${CYAN}📝 Creating helper scripts...${NC}"

cat > start.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting Surveillance System..."
docker-compose up -d
echo "✅ System started!"
echo "🌐 Access URLs:"
echo "• API Gateway: http://localhost:8000"
echo "• API Docs: http://localhost:8000/docs"
echo "• Grafana: http://localhost:3000 (admin/admin123)"
EOF
chmod +x start.sh

cat > stop.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping Surveillance System..."
docker-compose down
echo "✅ System stopped!"
EOF
chmod +x stop.sh

cat > logs.sh << 'EOF'
#!/bin/bash
if [ -z "$1" ]; then
    echo "📋 Showing all service logs..."
    docker-compose logs -f
else
    echo "📋 Showing logs for: $1"
    docker-compose logs -f "$1"
fi
EOF
chmod +x logs.sh

cat > status.sh << 'EOF'
#!/bin/bash
echo "📊 Surveillance System Status"
echo "============================="
echo
echo "🐳 Docker Services:"
docker-compose ps
echo
echo "🌐 Service Health Check:"
services=(
    "API Gateway:http://localhost:8000/health"
    "Grafana:http://localhost:3000/api/health"
    "Prometheus:http://localhost:9090/-/healthy"
)

for service_info in "${services[@]}"; do
    name=$(echo $service_info | cut -d: -f1)
    url=$(echo $service_info | cut -d: -f2-)
    if curl -s "$url" > /dev/null 2>&1; then
        echo "✅ $name: Healthy"
    else
        echo "❌ $name: Not responding"
    fi
done

echo
echo "🌐 Quick Access URLs:"
echo "• API Gateway: http://localhost:8000"
echo "• API Documentation: http://localhost:8000/docs"
echo "• Grafana: http://localhost:3000 (admin/admin123)"
echo "• Prometheus: http://localhost:9090"
EOF
chmod +x status.sh

# Final health check
echo -e "${CYAN}🏥 Performing health check...${NC}"
sleep 10

# Check if API Gateway is responding
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API Gateway is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  API Gateway is starting up...${NC}"
fi

echo
echo -e "${GREEN}🎉 Codespace setup completed!${NC}"
echo -e "${GREEN}============================${NC}"
echo
echo -e "${CYAN}🌐 Access URLs:${NC}"
echo "• API Gateway: http://localhost:8000"
echo "• API Documentation: http://localhost:8000/docs"
echo "• Grafana Monitoring: http://localhost:3000 (admin/admin123)"
echo "• Prometheus: http://localhost:9090"
echo
echo -e "${CYAN}💡 Quick Commands:${NC}"
echo "• Start system: ./start.sh"
echo "• Stop system: ./stop.sh"
echo "• Check status: ./status.sh"
echo "• View logs: ./logs.sh [service-name]"
echo "• View all logs: docker-compose logs -f"
echo
echo -e "${CYAN}🔧 Development:${NC}"
echo "• Create Python env: python3 -m venv venv && source venv/bin/activate"
echo "• Install deps: pip install -r requirements.txt"
echo "• Run tests: pytest"
echo
echo -e "${GREEN}🚀 System is ready to use!${NC}"
