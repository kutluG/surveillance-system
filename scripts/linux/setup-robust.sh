#!/bin/bash
# Surveillance System - Robust Setup Script
# Handles Docker startup and error recovery

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}🚀 Surveillance System - Robust Setup${NC}"
echo -e "${CYAN}====================================${NC}"

# Function to check if Docker is running
check_docker() {
    echo -e "${CYAN}🐳 Checking Docker status...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed. Please install Docker Desktop.${NC}"
        exit 1
    fi
    
    # Try to connect to Docker daemon
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✅ Docker is running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Docker daemon is not running${NC}"
        return 1
    fi
}

# Function to wait for Docker to start
wait_for_docker() {
    echo -e "${YELLOW}⏳ Waiting for Docker to start...${NC}"
    echo -e "${CYAN}Please start Docker Desktop manually if it's not starting automatically${NC}"
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker ps &> /dev/null; then
            echo -e "${GREEN}✅ Docker is now running!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}Attempt $attempt/$max_attempts - waiting for Docker...${NC}"
        sleep 10
        ((attempt++))
    done
    
    echo -e "${RED}❌ Docker failed to start after $max_attempts attempts${NC}"
    echo -e "${YELLOW}Please start Docker Desktop manually and run this script again${NC}"
    exit 1
}

# Main setup function
main_setup() {
    # Check if Docker is running, if not wait for it
    if ! check_docker; then
        wait_for_docker
    fi
    
    echo -e "${CYAN}📦 Installing essential packages...${NC}"
    # Skip apt-get in Windows/WSL2 if not available
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq || echo -e "${YELLOW}⚠️  Could not update packages${NC}"
        sudo apt-get install -y curl wget jq python3-pip python3-venv || echo -e "${YELLOW}⚠️  Some packages could not be installed${NC}"
    else
        echo -e "${YELLOW}⚠️  apt-get not available, skipping package installation${NC}"
    fi
    
    # Install Docker Compose if needed
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${CYAN}🐳 Installing Docker Compose...${NC}"
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y docker-compose-plugin || echo -e "${YELLOW}⚠️  Could not install docker-compose${NC}"
        else
            echo -e "${YELLOW}⚠️  Please install Docker Compose manually${NC}"
        fi
    fi
    
    # Create environment file
    echo -e "${CYAN}🔧 Setting up environment...${NC}"
    cat > .env << 'EOF'
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
JWT_SECRET_KEY=surveillance_jwt_secret_robust
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
    
    echo -e "${GREEN}✅ Environment file created${NC}"
    
    # Create directories
    echo -e "${CYAN}📁 Creating directories...${NC}"
    mkdir -p data/{clips,postgres,redis} logs certs monitoring/{grafana,prometheus}/data
    echo -e "${GREEN}✅ Directories created${NC}"
    
    # Create Docker resources
    echo -e "${CYAN}💾 Setting up Docker resources...${NC}"
    docker volume create surveillance_postgres_data 2>/dev/null || true
    docker volume create surveillance_redis_data 2>/dev/null || true
    docker volume create surveillance_grafana_data 2>/dev/null || true
    docker network create surveillance_network 2>/dev/null || true
    echo -e "${GREEN}✅ Docker resources created${NC}"
    
    # Check if docker-compose.yml exists
    if [ ! -f "docker-compose.yml" ]; then
        echo -e "${RED}❌ docker-compose.yml not found in current directory${NC}"
        echo -e "${YELLOW}Please make sure you're in the project root directory${NC}"
        exit 1
    fi
    
    # Start services
    echo -e "${CYAN}🚀 Starting services...${NC}"
    echo -e "${YELLOW}This may take a few minutes on first run...${NC}"
    
    # Start core services first
    echo -e "${CYAN}Starting core services (postgres, redis)...${NC}"
    docker-compose up -d postgres redis || {
        echo -e "${RED}❌ Failed to start core services${NC}"
        echo -e "${YELLOW}Checking docker-compose logs...${NC}"
        docker-compose logs
        exit 1
    }
    
    # Wait for databases
    echo -e "${CYAN}⏳ Waiting for databases to initialize...${NC}"
    sleep 20
    
    # Start remaining services
    echo -e "${CYAN}Starting application services...${NC}"
    docker-compose up -d || {
        echo -e "${RED}❌ Failed to start application services${NC}"
        echo -e "${YELLOW}Checking docker-compose logs...${NC}"
        docker-compose logs
        exit 1
    }
    
    # Create helper scripts
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
EOF
    chmod +x status.sh
    
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
    
    echo -e "${GREEN}✅ Helper scripts created${NC}"
    
    # Final health check
    echo -e "${CYAN}🏥 Performing final health check...${NC}"
    sleep 15
    
    echo -e "${CYAN}Checking service status...${NC}"
    docker-compose ps
    
    echo
    echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
    echo -e "${GREEN}==============================${NC}"
    echo
    echo -e "${CYAN}🌐 Access URLs:${NC}"
    echo "• API Gateway: http://localhost:8000"
    echo "• API Documentation: http://localhost:8000/docs"
    echo "• Grafana Monitoring: http://localhost:3000 (admin/admin123)"
    echo
    echo -e "${CYAN}💡 Quick Commands:${NC}"
    echo "• Start system: ./start.sh"
    echo "• Stop system: ./stop.sh"
    echo "• Check status: ./status.sh"
    echo "• View logs: ./logs.sh [service-name]"
    echo
    echo -e "${CYAN}🔧 Troubleshooting:${NC}"
    echo "• If services fail to start: docker-compose logs"
    echo "• To rebuild: docker-compose build"
    echo "• To reset: docker-compose down -v && docker-compose up -d"
    echo
    echo -e "${GREEN}🚀 System is ready to use!${NC}"
}

# Run main setup with error handling
main_setup || {
    echo -e "${RED}❌ Setup failed!${NC}"
    echo -e "${YELLOW}Please check the error messages above and try again${NC}"
    echo -e "${YELLOW}You may need to start Docker Desktop manually${NC}"
    exit 1
}
