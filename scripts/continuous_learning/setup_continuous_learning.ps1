# Test and Setup Script for Continuous Learning Pipeline
# This script validates the implementation and sets up the necessary components
# for the hard example collection, annotation and model retraining pipeline

param(
    [switch]$SkipDockerCheck = $false,
    [switch]$InstallDependencies = $false,
    [string]$KafkaHost = "localhost:9092",
    [switch]$CreateTopics = $false,
    [switch]$RunTests = $true,
    [switch]$Help = $false
)

function Show-Help {
    Write-Host "Continuous Learning Pipeline Setup and Test Script"
    Write-Host "=================================================="
    Write-Host ""
    Write-Host "This script helps set up and test the continuous learning pipeline"
    Write-Host "for hard example collection, annotation, and model retraining."
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -SkipDockerCheck       : Skip checking if Docker is running"
    Write-Host "  -InstallDependencies   : Install required Python dependencies"
    Write-Host "  -KafkaHost             : Kafka host (default: localhost:9092)"
    Write-Host "  -CreateTopics          : Create required Kafka topics"
    Write-Host "  -RunTests              : Run pipeline tests (default: true)"
    Write-Host "  -Help                  : Display this help message"
    Write-Host ""
    Write-Host "Example usage:"
    Write-Host "  .\setup_continuous_learning.ps1 -InstallDependencies -CreateTopics"
    Write-Host ""
}

if ($Help) {
    Show-Help
    exit 0
}

# Set error action preference
$ErrorActionPreference = "Stop"

# Display banner
Write-Host "=== Continuous Learning Pipeline Setup and Test ===" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
if (-not $SkipDockerCheck) {
    Write-Host "Checking if Docker is running..." -ForegroundColor Yellow
    try {
        $dockerStatus = docker info 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
            exit 1
        }
        Write-Host "✅ Docker is running" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Docker is not installed or not running. Please install Docker Desktop." -ForegroundColor Red
        exit 1
    }
}

# Install dependencies if requested
if ($InstallDependencies) {
    Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
    try {
        pip install confluent-kafka requests numpy pydantic fastapi uvicorn opencv-python 
        Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Failed to install dependencies: $_" -ForegroundColor Red
    }
}

# Create Kafka topics if requested
if ($CreateTopics) {
    Write-Host "`nCreating Kafka topics for continuous learning..." -ForegroundColor Yellow
    
    # First check if Kafka is accessible
    try {
        $kafkaCheck = docker exec -it $(docker ps -q -f name=kafka) kafka-topics --bootstrap-server $KafkaHost --list 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️ Cannot connect to Kafka at $KafkaHost. Make sure Kafka is running." -ForegroundColor Red
            exit 1
        }
        
        # Create required topics
        $topics = @(
            "hard.examples", 
            "labeled.examples", 
            "model.updates"
        )
        
        foreach ($topic in $topics) {
            Write-Host "Creating topic: $topic"
            docker exec -it $(docker ps -q -f name=kafka) kafka-topics --create --if-not-exists --bootstrap-server $KafkaHost --topic $topic --partitions 1 --replication-factor 1
        }
        
        Write-Host "✅ Kafka topics created successfully" -ForegroundColor Green
        
    } catch {
        Write-Host "⚠️ Failed to create Kafka topics: $_" -ForegroundColor Red
        Write-Host "  Make sure Kafka container is running by using docker-compose up -d" -ForegroundColor Yellow
    }
}

# Run tests if requested
if ($RunTests) {
    Write-Host "`nRunning continuous learning pipeline tests..." -ForegroundColor Yellow
    
    # Set environment variables for the test
    $env:KAFKA_HOST = $KafkaHost
    
    # Run the Python test script
    try {
        Write-Host "`n1. Testing hard example detection on EdgeInference class:"
        python test_hard_examples_fixed.py
        
        Write-Host "`n2. Testing full pipeline implementation:"
        python test_continuous_learning_pipeline.py
        
        Write-Host "`nℹ️ To test with all services running:" -ForegroundColor Blue
        Write-Host "1. Start all services: docker-compose up -d" -ForegroundColor Blue
        Write-Host "2. Create topics: ./create_kafka_topics.ps1" -ForegroundColor Blue
        Write-Host "3. Test full system: ./test_continuous_learning.ps1" -ForegroundColor Blue
        
    } catch {
        Write-Host "⚠️ Test execution failed: $_" -ForegroundColor Red
    }
}

Write-Host "`n=== Setup and Tests Completed ===" -ForegroundColor Cyan
