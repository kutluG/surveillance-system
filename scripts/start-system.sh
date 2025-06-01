#!/bin/bash
# System startup script with health checks

set -e

echo "🚀 Starting Surveillance System"
echo "==============================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    exit 1
fi

# Start infrastructure services first
echo -e "${YELLOW}📦 Starting infrastructure services...${NC}"
docker-compose up -d postgres redis zookeeper kafka weaviate prometheus grafana

# Wait for infrastructure to be ready
echo -e "${YELLOW}⏳ Waiting for infrastructure to be ready...${NC}"

wait_for_service() {
    local service_name=$1
    local check_command=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "Waiting for $service_name..."
    while [ $attempt -le $max_attempts ]; do
        if eval $check_command > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e " ${RED}✗ (timeout)${NC}"
    return 1
}

# Wait for each infrastructure service
wait_for_service "PostgreSQL" "docker-compose exec -T postgres pg_isready -U user -d events_db"
wait_for_service "Redis" "docker-compose exec -T redis redis-cli ping"
wait_for_service "Kafka" "docker-compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list"
wait_for_service "Weaviate" "curl -f http://localhost:8080/v1/.well-known/ready"

echo -e "${GREEN}✅ Infrastructure services ready${NC}"

# Build application services
echo -e "${YELLOW}🏗️  Building application services...${NC}"
make build

# Start application services
echo -e "${YELLOW}🚀 Starting application services...${NC}"
docker-compose up -d edge_service mqtt_kafka_bridge ingest_service rag_service prompt_service rulegen_service notifier vms_service

# Wait for application services
echo -e "${YELLOW}⏳ Waiting for application services...${NC}"

wait_for_http_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "Waiting for $service_name..."
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:$port/health > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 3
        attempt=$((attempt + 1))
    done
    
    echo -e " ${RED}✗ (timeout)${NC}"
    return 1
}

# Wait for each application service
wait_for_http_service "Edge Service" 8001
wait_for_http_service "MQTT-Kafka Bridge" 8002
wait_for_http_service "Ingest Service" 8003
wait_for_http_service "RAG Service" 8004
wait_for_http_service "Prompt Service" 8005
wait_for_http_service "RuleGen Service" 8006
wait_for_http_service "Notifier" 8007
wait_for_http_service "VMS Service" 8008

echo ""
echo -e "${GREEN}🎉 Surveillance System Started Successfully!${NC}"
echo ""
echo "Service Status:"
echo "==============="
make health

echo ""
echo "Access Points:"
echo "=============="
echo "📊 Grafana Dashboard:  http://localhost:3000 (admin/admin)"
echo "📈 Prometheus Metrics: http://localhost:9090"
echo "🔧 Service APIs:       http://localhost:800X/docs (X=1-8)"
echo ""
echo "Commands:"
echo "========="
echo "View logs:     make logs"
echo "Stop system:   make down"
echo "System status: make status"
echo "Run tests:     make test"