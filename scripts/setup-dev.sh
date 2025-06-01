#!/bin/bash
# Development environment setup script

set -e

echo "🚀 Setting up Surveillance System Development Environment"
echo "========================================================"

# Check prerequisites
check_prerequisites() {
    echo "📋 Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is not installed. Please install Python 3.9+ first."
        exit 1
    fi
    
    # Check Make
    if ! command -v make &> /dev/null; then
        echo "❌ Make is not installed. Please install Make first."
        exit 1
    fi
    
    echo "✅ Prerequisites check passed"
}

# Setup environment file
setup_env() {
    echo "🔧 Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        cp .env.example .env
        echo "📝 Created .env file from template"
        echo "⚠️  Please edit .env file with your configuration before starting services"
    else
        echo "✅ .env file already exists"
    fi
}

# Create required directories
setup_directories() {
    echo "📁 Creating required directories..."
    
    mkdir -p data/clips
    mkdir -p models
    mkdir -p certs
    mkdir -p logs
    
    echo "✅ Directories created"
}

# Setup Python development environment
setup_python_env() {
    echo "🐍 Setting up Python development environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install development dependencies
    pip install --upgrade pip
    pip install pytest pytest-asyncio black flake8 requests aiohttp
    
    echo "✅ Python dependencies installed"
}

# Download sample models
download_models() {
    echo "🤖 Setting up AI models..."
    
    if [ ! -f "models/yolov5s.pt" ]; then
        echo "📥 Downloading YOLOv5 model..."
        curl -L -o models/yolov5s.pt https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5s.pt
        echo "✅ YOLOv5 model downloaded"
    else
        echo "✅ YOLOv5 model already exists"
    fi
}

# Setup SSL certificates for MQTT (self-signed for development)
setup_certificates() {
    echo "🔐 Setting up SSL certificates..."
    
    if [ ! -f "certs/ca.crt" ]; then
        echo "📝 Generating self-signed certificates for development..."
        
        # Generate CA key
        openssl genrsa -out certs/ca.key 4096
        
        # Generate CA certificate
        openssl req -new -x509 -days 365 -key certs/ca.key -out certs/ca.crt \
            -subj "/C=US/ST=CA/L=San Francisco/O=Surveillance System/CN=ca"
        
        # Generate client key
        openssl genrsa -out certs/client.key 4096
        
        # Generate client certificate request
        openssl req -new -key certs/client.key -out certs/client.csr \
            -subj "/C=US/ST=CA/L=San Francisco/O=Surveillance System/CN=client"
        
        # Generate client certificate
        openssl x509 -req -days 365 -in certs/client.csr -CA certs/ca.crt -CAkey certs/ca.key \
            -CAcreateserial -out certs/client.crt
        
        # Clean up CSR
        rm certs/client.csr
        
        echo "✅ SSL certificates generated"
    else
        echo "✅ SSL certificates already exist"
    fi
}

# Build services
build_services() {
    echo "🏗️  Building services..."
    
    make build
    
    echo "✅ Services built successfully"
}

# Main setup function
main() {
    echo "Starting development environment setup..."
    
    check_prerequisites
    setup_env
    setup_directories
    setup_python_env
    download_models
    setup_certificates
    
    echo ""
    echo "🎉 Development environment setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your configuration (OpenAI API key, etc.)"
    echo "2. Start infrastructure: make infra-up"
    echo "3. Wait 30 seconds, then start services: make up"
    echo "4. Check system health: make health"
    echo "5. Open dashboards: make dashboard"
    echo ""
    echo "For more commands, run: make help"
}

# Run main function
main "$@"