# Enhanced Surveillance System Startup Script
# This script starts all services including the new enhanced AI components

Write-Host "🚀 Starting Enhanced Surveillance System..." -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Cyan

# Check if Docker is running
Write-Host "🔍 Checking Docker status..." -ForegroundColor Yellow
try {
    docker info > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not installed or not accessible." -ForegroundColor Red
    exit 1
}

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  No .env file found. Creating from example..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "📄 Created .env file from .env.example" -ForegroundColor Green
        Write-Host "⚠️  Please edit .env file with your configuration before continuing." -ForegroundColor Yellow
        Write-Host "Press any key to continue once you've configured .env..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } else {
        Write-Host "❌ No .env.example file found. Please create .env manually." -ForegroundColor Red
        exit 1
    }
}

# Pull latest images
Write-Host "📦 Pulling latest Docker images..." -ForegroundColor Yellow
docker-compose pull

# Build services
Write-Host "🔨 Building all services..." -ForegroundColor Yellow
docker-compose build

# Start infrastructure services first
Write-Host "🏗️  Starting infrastructure services..." -ForegroundColor Yellow
docker-compose up -d postgres redis zookeeper kafka weaviate prometheus grafana

# Wait for infrastructure to be ready
Write-Host "⏳ Waiting for infrastructure services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check infrastructure health
Write-Host "🏥 Checking infrastructure health..." -ForegroundColor Yellow
$infrastructureServices = @("postgres", "redis", "kafka", "weaviate")
foreach ($service in $infrastructureServices) {
    $healthStatus = docker-compose ps $service --format "{{.Health}}"
    if ($healthStatus -eq "healthy" -or $healthStatus -eq "") {
        Write-Host "✅ $service is ready" -ForegroundColor Green
    } else {
        Write-Host "⚠️  $service status: $healthStatus" -ForegroundColor Yellow
    }
}

# Start core application services
Write-Host "🚀 Starting core application services..." -ForegroundColor Yellow
$coreServices = @(
    "edge_service",
    "mqtt_kafka_bridge", 
    "ingest_service",
    "rag_service",
    "prompt_service",
    "rulegen_service",
    "notifier",
    "vms_service"
)

foreach ($service in $coreServices) {
    Write-Host "  Starting $service..." -ForegroundColor Cyan
    docker-compose up -d $service
    Start-Sleep -Seconds 5
}

# Start enhanced AI services
Write-Host "🧠 Starting enhanced AI services..." -ForegroundColor Yellow
$enhancedServices = @(
    "enhanced_prompt_service",
    "websocket_service",
    "agent_orchestrator",
    "rule_builder_service",
    "advanced_rag_service",
    "ai_dashboard_service",
    "voice_interface_service"
)

foreach ($service in $enhancedServices) {
    Write-Host "  Starting $service..." -ForegroundColor Cyan
    docker-compose up -d $service
    Start-Sleep -Seconds 5
}

# Wait for all services to be ready
Write-Host "⏳ Waiting for all services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check service status
Write-Host "📊 Checking service status..." -ForegroundColor Yellow
Write-Host "=====================================================" -ForegroundColor Cyan

# Core Services Status
Write-Host "🔧 Core Services:" -ForegroundColor Yellow
$coreServicePorts = @{
    "edge_service" = 8001
    "mqtt_kafka_bridge" = 8002
    "ingest_service" = 8003
    "rag_service" = 8004
    "prompt_service" = 8005
    "rulegen_service" = 8006
    "notifier" = 8007
    "vms_service" = 8008
}

foreach ($service in $coreServicePorts.Keys) {
    $port = $coreServicePorts[$service]
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$port/health" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✅ $service (port $port)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  $service (port $port) - Status: $($response.StatusCode)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ❌ $service (port $port) - Not responding" -ForegroundColor Red
    }
}

# Enhanced AI Services Status
Write-Host "🧠 Enhanced AI Services:" -ForegroundColor Yellow
$enhancedServicePorts = @{
    "enhanced_prompt_service" = 8009
    "websocket_service" = 8010
    "agent_orchestrator" = 8011
    "rule_builder_service" = 8012
    "advanced_rag_service" = 8013
    "ai_dashboard_service" = 8014
    "voice_interface_service" = 8015
}

foreach ($service in $enhancedServicePorts.Keys) {
    $port = $enhancedServicePorts[$service]
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$port/health" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✅ $service (port $port)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  $service (port $port) - Status: $($response.StatusCode)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ❌ $service (port $port) - Not responding" -ForegroundColor Red
    }
}

# Infrastructure Services Status
Write-Host "🏗️  Infrastructure Services:" -ForegroundColor Yellow
Write-Host "  📊 Grafana Dashboard: http://localhost:3000 (admin/admin)" -ForegroundColor Cyan
Write-Host "  📈 Prometheus: http://localhost:9090" -ForegroundColor Cyan
Write-Host "  🔍 Weaviate: http://localhost:8080" -ForegroundColor Cyan

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "🎉 Enhanced Surveillance System Started!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Quick Access URLs:" -ForegroundColor Yellow
Write-Host "  🌐 Web Dashboard: http://localhost:3000" -ForegroundColor Cyan
Write-Host "  🤖 Enhanced AI Chat: http://localhost:8009/docs" -ForegroundColor Cyan
Write-Host "  🔊 Voice Interface: http://localhost:8015/docs" -ForegroundColor Cyan
Write-Host "  📡 WebSocket Connection: ws://localhost:8010/ws" -ForegroundColor Cyan
Write-Host "  🎛️  Agent Orchestrator: http://localhost:8011/docs" -ForegroundColor Cyan
Write-Host "  📊 AI Dashboard: http://localhost:8014/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "🧪 To run integration tests:" -ForegroundColor Yellow
Write-Host "  python integration_tests/test_enhanced_services.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "🛑 To stop all services:" -ForegroundColor Yellow
Write-Host "  ./stop-surveillance.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "📚 For more information, see:" -ForegroundColor Yellow
Write-Host "  - README.md" -ForegroundColor Cyan
Write-Host "  - QUICKSTART.md" -ForegroundColor Cyan
Write-Host "  - MISSING_COMPONENTS_ANALYSIS.md" -ForegroundColor Cyan
