#!/bin/bash
# Surveillance System - Ubuntu/Linux Setup Script
# This script installs and configures the surveillance system in Ubuntu/Linux environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Print functions
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ️  $1${NC}"; }
print_header() { echo -e "${MAGENTA}$1${NC}"; }

# Parse command line arguments
SKIP_PREREQUISITES=false
DEV_MODE=false
QUICK_MODE=false
BUILD_ONLY=false
ENVIRONMENT="development"
CLEAN_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-prerequisites)
            SKIP_PREREQUISITES=true
            shift
            ;;
        --dev-mode)
            DEV_MODE=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        clean)
            CLEAN_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --skip-prerequisites  Skip prerequisite checks"
            echo "  --dev-mode           Enable development mode"
            echo "  --quick              Quick setup (basic services only)"
            echo "  --build-only         Only build Docker images"
            echo "  --environment ENV    Set environment (default: development)"
            echo "  clean                Clean up the system"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Main header
print_header "🚀 Surveillance System - Ubuntu Setup Script"
print_header "=============================================="
print_info "Environment: $ENVIRONMENT"
echo

# Check prerequisites
check_prerequisites() {
    if [[ "$SKIP_PREREQUISITES" == "true" ]]; then
        print_warning "Skipping prerequisite checks..."
        return
    fi

    print_info "📋 Checking prerequisites..."
    
    # Check if running as root or with sudo access
    if [[ $EUID -eq 0 ]] || sudo -n true 2>/dev/null; then
        print_success "Running with sufficient privileges"
    else
        print_error "This script requires sudo access. Please run with sudo or ensure your user has sudo privileges."
        exit 1
    fi
    
    # Update package list
    print_info "Updating package list..."
    sudo apt-get update -qq
    
    # Check and install Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker found: $DOCKER_VERSION"
    else
        print_info "Installing Docker..."
        # Install Docker using official script
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        print_success "Docker installed successfully"
    fi
    
    # Check and install Docker Compose
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
        print_success "Docker Compose found: $COMPOSE_VERSION"
    else
        print_info "Installing Docker Compose..."
        sudo apt-get install -y docker-compose-plugin
        print_success "Docker Compose installed successfully"
    fi
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python found: $PYTHON_VERSION"
    else
        print_info "Installing Python..."
        sudo apt-get install -y python3 python3-pip python3-venv
        print_success "Python installed successfully"
    fi
    
    # Check Git
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version)
        print_success "Git found: $GIT_VERSION"
    else
        print_info "Installing Git..."
        sudo apt-get install -y git
        print_success "Git installed successfully"
    fi
    
    # Install additional required packages
    print_info "Installing additional packages..."
    sudo apt-get install -y curl wget jq htop tree make
    
    # Check if Docker service is running
    if sudo systemctl is-active --quiet docker; then
        print_success "Docker service is running"
    else
        print_info "Starting Docker service..."
        sudo systemctl start docker
        sudo systemctl enable docker
        print_success "Docker service started and enabled"
    fi
    
    # Check Docker access without sudo
    if docker ps &> /dev/null; then
        print_success "Docker accessible without sudo"
    else
        print_warning "Docker requires sudo. You may need to log out and back in for group changes to take effect."
    fi
}

# Set up environment variables
setup_environment() {
    print_info "🔧 Setting up environment variables..."
    
    # Generate random passwords
    POSTGRES_PASSWORD="surveillance_pass_$(openssl rand -hex 4)"
    JWT_SECRET="surveillance_jwt_secret_$(openssl rand -hex 8)"
    MQTT_PASSWORD="mqtt_pass_$(openssl rand -hex 4)"
    
    # Create .env file
    cat > .env << EOF
# Surveillance System Environment Configuration
# Generated by setup script on $(date)

# Environment
ENVIRONMENT=$ENVIRONMENT

# Database Configuration
POSTGRES_DB=events_db
POSTGRES_USER=surveillance_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=postgresql://surveillance_user:$POSTGRES_PASSWORD@postgres:5432/events_db

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_PREFIX=surveillance

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET_KEY=$JWT_SECRET

# AI Service Configuration
OPENAI_API_KEY=your_openai_api_key_here
WEAVIATE_URL=http://weaviate:8080

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=admin123

# Video Storage
VIDEO_STORAGE_PATH=./data/clips
MAX_CLIP_SIZE_MB=100

# MQTT Configuration
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=surveillance
MQTT_PASSWORD=$MQTT_PASSWORD

# Development Settings
DEBUG=true
LOG_LEVEL=INFO
EOF
    
    print_success "Environment file (.env) created"
}

# Create required directories
create_directories() {
    print_info "📁 Creating required directories..."
    
    DIRECTORIES=(
        "data"
        "data/clips"
        "data/postgres"
        "data/redis"
        "logs"
        "certs"
        "monitoring/grafana/data"
        "monitoring/prometheus/data"
    )
    
    for dir in "${DIRECTORIES[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            print_success "Directory created: $dir"
        fi
    done
    
    # Set proper permissions
    chmod -R 755 data logs certs monitoring 2>/dev/null || true
}

# Create Docker volumes
create_docker_volumes() {
    print_info "💾 Creating Docker volumes..."
    
    VOLUMES=(
        "surveillance_postgres_data"
        "surveillance_redis_data"
        "surveillance_kafka_data"
        "surveillance_weaviate_data"
        "surveillance_grafana_data"
        "surveillance_prometheus_data"
    )
    
    for volume in "${VOLUMES[@]}"; do
        if docker volume create "$volume" &> /dev/null; then
            print_success "Volume created: $volume"
        else
            print_warning "Volume already exists or could not be created: $volume"
        fi
    done
}

# Create Docker networks
create_docker_networks() {
    print_info "🌐 Creating Docker networks..."
    
    NETWORKS=(
        "surveillance_network"
        "surveillance_monitoring"
    )
    
    for network in "${NETWORKS[@]}"; do
        if docker network create "$network" &> /dev/null; then
            print_success "Network created: $network"
        else
            print_warning "Network already exists or could not be created: $network"
        fi
    done
}

# Build Docker images
build_docker_images() {
    print_info "🐳 Building Docker images..."
    
    SERVICES=(
        "api_gateway"
        "edge_service"
        "vms_service"
        "ingest_service"
        "prompt_service"
        "enhanced_prompt_service"
        "rag_service"
        "advanced_rag_service"
        "rule_builder_service"
        "rulegen_service"
        "notifier"
        "mqtt_kafka_bridge"
        "websocket_service"
        "voice_interface_service"
        "ai_dashboard_service"
        "agent_orchestrator"
    )
    
    for service in "${SERVICES[@]}"; do
        if [[ -f "$service/Dockerfile" ]]; then
            print_info "🏗️  Building $service..."
            if docker build -t "surveillance-$service" -f "$service/Dockerfile" . &> /dev/null; then
                print_success "$service built successfully"
            else
                print_warning "$service build failed"
            fi
        fi
    done
}

# Start services
start_services() {
    print_info "🚀 Starting services..."
    
    if [[ "$QUICK_MODE" == "true" ]]; then
        print_info "⚡ Quick mode - starting basic services only"
        docker-compose up -d postgres redis kafka zookeeper api_gateway
    elif [[ "$DEV_MODE" == "true" ]]; then
        print_info "🛠️  Development mode - including monitoring services"
        docker-compose --profile development up -d
    else
        print_info "🌟 Starting all services..."
        docker-compose up -d
    fi
    
    print_success "Services started"
}

# Health check
check_service_health() {
    print_info "🏥 Checking service health..."
    
    # Wait for services to start
    sleep 10
    
    # Check API Gateway
    if curl -s http://localhost:8000/health &> /dev/null; then
        print_success "API Gateway is healthy"
    else
        print_warning "API Gateway is not ready yet"
    fi
    
    # Check database
    if docker exec surveillance-postgres pg_isready -U surveillance_user &> /dev/null; then
        print_success "PostgreSQL is healthy"
    else
        print_warning "PostgreSQL is not ready yet"
    fi
    
    # Check Redis
    if docker exec surveillance-redis redis-cli ping &> /dev/null; then
        print_success "Redis is healthy"
    else
        print_warning "Redis is not ready yet"
    fi
}

# Install development tools
install_development_tools() {
    if [[ "$DEV_MODE" != "true" ]]; then
        return
    fi
    
    print_info "🛠️  Installing development tools..."
    
    # Create Python virtual environment
    if command -v python3 &> /dev/null; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        
        # Upgrade pip
        pip install --upgrade pip setuptools wheel
        
        # Install development tools
        pip install pytest pytest-cov black flake8 mypy pre-commit isort bandit safety
        
        # Install project requirements if they exist
        if [[ -f "requirements.txt" ]]; then
            pip install -r requirements.txt
            print_success "Python requirements installed"
        fi
        
        # Install service requirements
        for service_dir in */; do
            if [[ -f "$service_dir/requirements.txt" ]]; then
                print_info "Installing requirements for $service_dir"
                pip install -r "$service_dir/requirements.txt"
            fi
        done
        
        print_success "Development tools installed"
    fi
    
    # Install Node.js and npm if needed
    if [[ -f "mobile-app/package.json" ]] || [[ -f "website/package.json" ]]; then
        print_info "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
        print_success "Node.js installed"
        
        # Install mobile app dependencies
        if [[ -f "mobile-app/package.json" ]]; then
            print_info "Installing mobile app dependencies..."
            cd mobile-app && npm install && cd ..
            print_success "Mobile app dependencies installed"
        fi
        
        # Install website dependencies
        if [[ -f "website/package.json" ]]; then
            print_info "Installing website dependencies..."
            cd website && npm install && cd ..
            print_success "Website dependencies installed"
        fi
    fi
}

# Create helpful scripts
create_helper_scripts() {
    print_info "📝 Creating helper scripts..."
    
    # Create start script
    cat > start.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting Surveillance System..."
docker-compose up -d
echo "✅ System started!"
echo "📊 Access points:"
echo "• API Gateway: http://localhost:8000"
echo "• Grafana: http://localhost:3000 (admin/admin123)"
echo "• Prometheus: http://localhost:9090"
EOF
    chmod +x start.sh
    
    # Create stop script
    cat > stop.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping Surveillance System..."
docker-compose down
echo "✅ System stopped!"
EOF
    chmod +x stop.sh
    
    # Create status script
    cat > status.sh << 'EOF'
#!/bin/bash
echo "📊 Surveillance System Status"
echo "============================="
echo
echo "🐳 Docker Services:"
docker-compose ps
echo
echo "🌐 Service Health:"
services=("http://localhost:8000/health" "http://localhost:3000/api/health" "http://localhost:9090/-/healthy")
for service in "${services[@]}"; do
    if curl -s "$service" > /dev/null; then
        echo "✅ $service: Healthy"
    else
        echo "❌ $service: Not responding"
    fi
done
EOF
    chmod +x status.sh
    
    print_success "Helper scripts created (start.sh, stop.sh, status.sh)"
}

# Main installation function
install_surveillance_system() {
    print_header "🎯 Starting installation..."
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Setup environment
    setup_environment
    
    # Create directories
    create_directories
    
    # Create Docker resources
    create_docker_volumes
    create_docker_networks
    
    if [[ "$BUILD_ONLY" != "true" ]]; then
        # Build images
        build_docker_images
        
        # Start services
        start_services
        
        # Health check
        check_service_health
        
        # Install development tools
        install_development_tools
        
        # Create helper scripts
        create_helper_scripts
    else
        build_docker_images
    fi
    
    print_header ""
    print_header "🎉 Installation completed!"
    print_header "========================="
    echo
    print_info "Service URLs:"
    echo "• API Gateway: http://localhost:8000"
    echo "• API Documentation: http://localhost:8000/docs"
    echo "• Grafana Monitoring: http://localhost:3000 (admin/admin123)"
    echo "• Prometheus: http://localhost:9090"
    echo
    print_info "Useful commands:"
    echo "• Start system: ./start.sh or docker-compose up -d"
    echo "• Stop system: ./stop.sh or docker-compose down"
    echo "• Check status: ./status.sh"
    echo "• View logs: docker-compose logs -f"
    echo
    if [[ "$DEV_MODE" == "true" ]]; then
        print_info "Development:"
        echo "• Activate Python env: source venv/bin/activate"
        echo "• Run tests: pytest"
        echo "• Format code: black ."
        echo "• Lint code: flake8 ."
    fi
    echo
    print_success "For more information, check README.md"
}

# Cleanup function
cleanup_system() {
    print_warning "🧹 Cleaning up system..."
    
    # Stop and remove containers
    docker-compose down -v 2>/dev/null || true
    
    # Remove custom images
    docker images -q surveillance-* | xargs -r docker rmi -f
    
    # Remove volumes
    docker volume ls -q | grep surveillance_ | xargs -r docker volume rm
    
    # Remove networks
    docker network ls -q | xargs -I {} docker network inspect {} --format '{{.Name}}' | grep surveillance_ | xargs -r docker network rm
    
    # Remove created files
    rm -f .env start.sh stop.sh status.sh
    
    print_success "Cleanup completed"
}

# Main script logic
main() {
    if [[ "$CLEAN_MODE" == "true" ]]; then
        cleanup_system
    else
        install_surveillance_system
    fi
    
    print_header "🚀 Script completed!"
}

# Run main function
main "$@"
