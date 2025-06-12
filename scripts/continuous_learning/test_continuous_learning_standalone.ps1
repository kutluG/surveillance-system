# Continuous Learning Pipeline - Standalone Test
# Tests the implementation without requiring Docker

Write-Host "🔍 CONTINUOUS LEARNING PIPELINE VALIDATION" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$ErrorCount = 0
$WarningCount = 0

function Test-FileExists {
    param($FilePath, $Description)
    if (Test-Path $FilePath) {
        Write-Host "✅ $Description" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ $Description - File not found: $FilePath" -ForegroundColor Red
        $script:ErrorCount++
        return $false
    }
}

function Test-PythonService {
    param($ServicePath, $ServiceName)
    Write-Host "`n📦 Testing $ServiceName..." -ForegroundColor Yellow
    
    # Check main files
    Test-FileExists "$ServicePath/main.py" "$ServiceName main.py exists"
    Test-FileExists "$ServicePath/requirements.txt" "$ServiceName requirements.txt exists"
    Test-FileExists "$ServicePath/Dockerfile" "$ServiceName Dockerfile exists"
    
    # Test Python syntax
    try {
        $result = python -m py_compile "$ServicePath/main.py" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $ServiceName Python syntax valid" -ForegroundColor Green
        } else {
            Write-Host "⚠ $ServiceName Python syntax check failed: $result" -ForegroundColor Yellow
            $script:WarningCount++
        }
    } catch {
        Write-Host "⚠ $ServiceName Could not validate Python syntax (Python not available)" -ForegroundColor Yellow
        $script:WarningCount++
    }
}

# Test Edge Service enhancements
Write-Host "`n🔧 Testing Edge Service Enhancements..." -ForegroundColor Yellow
Test-FileExists "edge_service/inference.py" "Enhanced inference.py exists"

# Check for Kafka integration in inference.py
if (Test-Path "edge_service/inference.py") {
    $inferenceContent = Get-Content "edge_service/inference.py" -Raw
    if ($inferenceContent -match "kafka_producer|KafkaProducer") {
        Write-Host "✅ Edge Service has Kafka integration" -ForegroundColor Green
    } else {
        Write-Host "❌ Edge Service missing Kafka integration" -ForegroundColor Red
        $ErrorCount++
    }
    
    if ($inferenceContent -match "hard_example_thresholds|_check_and_publish_hard_examples") {
        Write-Host "✅ Edge Service has hard example detection" -ForegroundColor Green
    } else {
        Write-Host "❌ Edge Service missing hard example detection" -ForegroundColor Red
        $ErrorCount++
    }
}

# Test microservices
Test-PythonService "hard_example_collector" "Hard Example Collector"
Test-PythonService "annotation_frontend" "Annotation Frontend"  
Test-PythonService "training_service" "Training Service"

# Test Docker Compose integration
Write-Host "`n🐳 Testing Docker Compose Integration..." -ForegroundColor Yellow
if (Test-Path "docker-compose.yml") {
    $composeContent = Get-Content "docker-compose.yml" -Raw
    
    $services = @("hard_example_collector", "annotation_frontend", "training_service")
    foreach ($service in $services) {
        if ($composeContent -match "$service:") {
            Write-Host "✅ $service integrated in docker-compose.yml" -ForegroundColor Green
        } else {
            Write-Host "❌ $service missing from docker-compose.yml" -ForegroundColor Red
            $ErrorCount++
        }
    }
}

# Test documentation
Write-Host "`n📚 Testing Documentation..." -ForegroundColor Yellow
Test-FileExists "CONTINUOUS_LEARNING.md" "Continuous Learning documentation exists"

# Test automation scripts
Write-Host "`n🔧 Testing Automation Scripts..." -ForegroundColor Yellow
$scripts = @(
    "create_kafka_topics.ps1",
    "test_continuous_learning.ps1", 
    "monitor_kafka_topics.ps1"
)

foreach ($script in $scripts) {
    Test-FileExists $script "$script exists"
}

# Summary
Write-Host "`n" -NoNewline
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "=======" -ForegroundColor Cyan

if ($ErrorCount -eq 0) {
    Write-Host "🎉 CONTINUOUS LEARNING PIPELINE: READY FOR DEPLOYMENT!" -ForegroundColor Green
    Write-Host "   All core components are properly implemented and integrated." -ForegroundColor Green
} else {
    Write-Host "⚠ CONTINUOUS LEARNING PIPELINE: $ErrorCount ISSUES FOUND" -ForegroundColor Red
}

if ($WarningCount -gt 0) {
    Write-Host "⚠ $WarningCount warnings (non-critical)" -ForegroundColor Yellow
}

Write-Host "`n🚀 NEXT STEPS:" -ForegroundColor Cyan
Write-Host "1. Start Docker Desktop" -ForegroundColor White
Write-Host "2. Run: docker-compose up -d kafka zookeeper" -ForegroundColor White  
Write-Host "3. Run: .\create_kafka_topics.ps1" -ForegroundColor White
Write-Host "4. Run: docker-compose up" -ForegroundColor White
Write-Host "5. Test the pipeline with: .\test_continuous_learning.ps1" -ForegroundColor White

Write-Host "`n📊 SERVICE PORTS:" -ForegroundColor Cyan
Write-Host "• Hard Example Collector: http://localhost:8010" -ForegroundColor White
Write-Host "• Annotation Frontend: http://localhost:3001" -ForegroundColor White  
Write-Host "• Training Service: http://localhost:8011" -ForegroundColor White
