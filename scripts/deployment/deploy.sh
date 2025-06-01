#!/bin/bash
# Production deployment script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
BACKUP_DIR="/backups/surveillance-$(date +%Y%m%d_%H%M%S)"
MAX_DOWNTIME=120  # seconds

echo -e "${BLUE}🚀 Surveillance System Deployment${NC}"
echo -e "${BLUE}====================================${NC}"
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"
echo "Backup Directory: $BACKUP_DIR"
echo ""

# Pre-deployment checks
pre_deployment_checks() {
    echo -e "${YELLOW}📋 Running pre-deployment checks...${NC}"
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        echo -e "${RED}❌ .env file not found!${NC}"
        exit 1
    fi
    
    # Check disk space
    AVAILABLE_SPACE=$(df / | awk 'NR==2 {print $4}')
    REQUIRED_SPACE=5000000  # 5GB in KB
    
    if [ $AVAILABLE_SPACE -lt $REQUIRED_SPACE ]; then
        echo -e "${RED}❌ Insufficient disk space!${NC}"
        echo "Available: $(($AVAILABLE_SPACE / 1024))MB, Required: $(($REQUIRED_SPACE / 1024))MB"
        exit 1
    fi
    
    # Check Docker availability
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not available!${NC}"
        exit 1
    fi
    
    # Check network connectivity
    if ! ping -c 1 google.com > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Limited network connectivity${NC}"
    fi
    
    echo -e "${GREEN}✅ Pre-deployment checks passed${NC}"
}

# Backup current system
backup_system() {
    echo -e "${YELLOW}💾 Creating system backup...${NC}"
    
    mkdir -p $BACKUP_DIR
    
    # Backup database
    if docker-compose ps postgres | grep -q "Up"; then
        echo "Backing up PostgreSQL database..."
        docker-compose exec -T postgres pg_dump -U user events_db > $BACKUP_DIR/postgres_backup.sql
    fi
    
    # Backup configuration
    echo "Backing up configuration..."
    cp .env $BACKUP_DIR/
    cp docker-compose.yml $BACKUP_DIR/
    
    # Backup volumes
    echo "Backing up data volumes..."
    docker run --rm -v surveillance_postgres_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/postgres_data.tar.gz /data
    docker run --rm -v surveillance_weaviate_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/weaviate_data.tar.gz /data
    
    # Backup local storage
    if [ -d "data/clips" ]; then
        echo "Backing up video clips..."
        tar czf $BACKUP_DIR/clips_backup.tar.gz data/clips/
    fi
    
    echo -e "${GREEN}✅ Backup completed: $BACKUP_DIR${NC}"
}

# Pull new images
pull_images() {
    echo -e "${YELLOW}📥 Pulling new images...${NC}"
    
    # If using a registry, pull specific version
    if [ "$VERSION" != "latest" ]; then
        echo "Pulling version $VERSION from registry..."
        # Add registry pull commands here
        # docker pull registry.example.com/surveillance/edge_service:$VERSION
    fi
    
    # Build local images
    echo "Building images..."
    docker-compose build --parallel
    
    echo -e "${GREEN}✅ Images ready${NC}"
}

# Health check function
wait_for_health() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "Waiting for $service_name..."
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s http://localhost:$port/health > /dev/null 2>&1; then
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

# Rolling deployment
rolling_deployment() {
    echo -e "${YELLOW}🔄 Starting rolling deployment...${NC}"
    
    # Services in dependency order
    SERVICES=(
        "postgres:5432"
        "redis:6379" 
        "kafka:9092"
        "weaviate:8080"
        "ingest_service:8003"
        "rag_service:8004"
        "prompt_service:8005"
        "rulegen_service:8006"
        "notifier:8007"
        "vms_service:8008"
        "edge_service:8001"
        "mqtt_kafka_bridge:8002"
    )
    
    for service_info in "${SERVICES[@]}"; do
        IFS=':' read -r service_name port <<< "$service_info"
        
        echo -e "${BLUE}Deploying $service_name...${NC}"
        
        # Stop old container
        docker-compose stop $service_name || true
        
        # Start new container
        docker-compose up -d $service_name
        
        # Wait for health check
        if [ "$port" != "" ]; then
            if ! wait_for_health $service_name $port; then
                echo -e "${RED}❌ $service_name failed to start properly${NC}"
                echo "Rolling back..."
                rollback_deployment
                exit 1
            fi
        else
            sleep 5  # Basic wait for infrastructure services
        fi
        
        echo -e "${GREEN}✅ $service_name deployed${NC}"
    done
}

# Blue-green deployment
blue_green_deployment() {
    echo -e "${YELLOW}🔵🟢 Starting blue-green deployment...${NC}"
    
    # Create new environment with suffix
    export COMPOSE_PROJECT_NAME="surveillance-green"
    
    # Start green environment
    echo "Starting green environment..."
    docker-compose up -d --force-recreate
    
    # Wait for green environment to be ready
    echo "Waiting for green environment..."
    sleep 60
    
    # Run health checks on green environment
    python3 scripts/deployment/health_check.py --wait --max-wait 300
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Green environment healthy${NC}"
        
        # Switch traffic (in real deployment, update load balancer)
        echo "Switching traffic to green environment..."
        
        # Stop blue environment
        export COMPOSE_PROJECT_NAME="surveillance"
        docker-compose down
        
        # Rename green to blue
        docker network create surveillance_default || true
        for container in $(docker ps --filter "label=com.docker.compose.project=surveillance-green" --format "{{.Names}}"); do
            docker rename $container ${container/-green/}
        done
        
        echo -e "${GREEN}✅ Blue-green deployment completed${NC}"
    else
        echo -e "${RED}❌ Green environment unhealthy, rolling back${NC}"
        export COMPOSE_PROJECT_NAME="surveillance-green"
        docker-compose down
        exit 1
    fi
}

# Rollback function
rollback_deployment() {
    echo -e "${RED}🔄 Rolling back deployment...${NC}"
    
    # Restore from backup
    if [ -d "$BACKUP_DIR" ]; then
        echo "Restoring configuration..."
        cp $BACKUP_DIR/.env .
        cp $BACKUP_DIR/docker-compose.yml .
        
        # Restore database if needed
        if [ -f "$BACKUP_DIR/postgres_backup.sql" ]; then
            echo "Restoring database..."
            docker-compose exec -T postgres psql -U user -d events_db < $BACKUP_DIR/postgres_backup.sql
        fi
    fi
    
    # Restart with previous version
    docker-compose down
    docker-compose up -d
    
    echo -e "${RED}🔄 Rollback completed${NC}"
}

# Post-deployment validation
post_deployment_validation() {
    echo -e "${YELLOW}🧪 Running post-deployment validation...${NC}"
    
    # Run comprehensive health check
    if ! python3 scripts/deployment/health_check.py --smoke-tests --exit-code; then
        echo -e "${RED}❌ Post-deployment validation failed${NC}"
        rollback_deployment
        exit 1
    fi
    
    # Run basic integration tests
    echo "Running integration tests..."
    if ! python3 -m pytest integration_tests/test_e2e.py::TestE2EFlow::test_service_health_endpoints -v; then
        echo -e "${RED}❌ Integration tests failed${NC}"
        rollback_deployment
        exit 1
    fi
    
    echo -e "${GREEN}✅ Post-deployment validation passed${NC}"
}

# Cleanup old resources
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up old resources...${NC}"
    
    # Remove old images
    docker image prune -f
    
    # Remove old volumes (keep backups)
    docker volume prune -f
    
    # Clean up old backup files (keep last 5)
    if [ -d "/backups" ]; then
        ls -t /backups/surveillance-* | tail -n +6 | xargs rm -rf
    fi
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Main deployment function
main() {
    echo -e "${BLUE}Starting deployment process...${NC}"
    
    # Record start time
    START_TIME=$(date +%s)
    
    # Run deployment steps
    pre_deployment_checks
    backup_system
    pull_images
    
    # Choose deployment strategy
    if [ "$ENVIRONMENT" = "production" ]; then
        blue_green_deployment
    else
        rolling_deployment
    fi
    
    post_deployment_validation
    cleanup
    
    # Calculate deployment time
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo -e "${GREEN}Total time: ${DURATION}s${NC}"
    echo ""
    echo "Access points:"
    echo "- Grafana: http://localhost:3000"
    echo "- Prometheus: http://localhost:9090"
    echo "- APIs: http://localhost:800X/docs"
}

# Trap errors and cleanup
trap 'echo -e "${RED}❌ Deployment failed!${NC}"; rollback_deployment; exit 1' ERR

# Run main function
main "$@"