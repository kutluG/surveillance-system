# Continuous Learning Pipeline Test Script
# Tests the complete flow from hard example detection to training

param(
    [switch]$StartServices = $false,
    [switch]$TestOnly = $false,
    [switch]$CleanUp = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=== Continuous Learning Pipeline Test ===" -ForegroundColor Cyan

if ($StartServices) {
    Write-Host "`n1. Starting surveillance system..." -ForegroundColor Yellow
    docker-compose up -d
    
    # Wait for services to be ready
    Write-Host "Waiting for services to start..."
    Start-Sleep -Seconds 30
    
    # Create Kafka topics
    Write-Host "`n2. Creating Kafka topics..." -ForegroundColor Yellow
    .\create_kafka_topics.ps1
}

if (-not $TestOnly) {
    Write-Host "`n3. Testing service health..." -ForegroundColor Yellow
    
    # Test edge service
    try {
        $edgeHealth = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET
        Write-Host "✓ Edge Service: $($edgeHealth.status)" -ForegroundColor Green
    } catch {
        Write-Host "✗ Edge Service: Failed" -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
    
    # Test hard example collector
    try {
        $hardExampleHealth = Invoke-RestMethod -Uri "http://localhost:8010/health" -Method GET
        Write-Host "✓ Hard Example Collector: $($hardExampleHealth.status)" -ForegroundColor Green
    } catch {
        Write-Host "✗ Hard Example Collector: Failed" -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
    
    # Test annotation frontend
    try {
        $annotationHealth = Invoke-RestMethod -Uri "http://localhost:8011/health" -Method GET
        Write-Host "✓ Annotation Frontend: $($annotationHealth.status)" -ForegroundColor Green
    } catch {
        Write-Host "✗ Annotation Frontend: Failed" -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
    
    # Test training service
    try {
        $trainingHealth = Invoke-RestMethod -Uri "http://localhost:8012/health" -Method GET
        Write-Host "✓ Training Service: $($trainingHealth.status)" -ForegroundColor Green
    } catch {
        Write-Host "✗ Training Service: Failed" -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
}

Write-Host "`n4. Testing continuous learning pipeline..." -ForegroundColor Yellow

# Generate some inference events to trigger hard examples
Write-Host "Triggering frame processing to generate hard examples..."
for ($i = 1; $i -le 5; $i++) {
    try {
        $result = Invoke-RestMethod -Uri "http://localhost:8000/capture" -Method POST
        Write-Host "✓ Frame $i processed: $($result.status)" -ForegroundColor Green
        Start-Sleep -Seconds 2
    } catch {
        Write-Host "✗ Frame $i failed" -ForegroundColor Red
    }
}

Start-Sleep -Seconds 5

# Check hard example collector stats
Write-Host "`nChecking hard example collection..."
try {
    $hardExampleStats = Invoke-RestMethod -Uri "http://localhost:8010/stats" -Method GET
    Write-Host "Hard examples collected: $($hardExampleStats.hard_examples_collected)" -ForegroundColor Cyan
    Write-Host "Messages processed: $($hardExampleStats.messages_processed)" -ForegroundColor Cyan
} catch {
    Write-Host "Could not retrieve hard example stats" -ForegroundColor Yellow
}

# Check annotation frontend for pending examples
Write-Host "`nChecking annotation frontend..."
try {
    $pendingExamples = Invoke-RestMethod -Uri "http://localhost:8011/api/examples" -Method GET
    Write-Host "Pending examples for annotation: $($pendingExamples.Count)" -ForegroundColor Cyan
} catch {
    Write-Host "Could not retrieve pending examples" -ForegroundColor Yellow
}

# Check training service stats
Write-Host "`nChecking training service..."
try {
    $trainingStats = Invoke-RestMethod -Uri "http://localhost:8012/stats" -Method GET
    Write-Host "Labeled examples processed: $($trainingStats.labeled_examples_processed)" -ForegroundColor Cyan
    Write-Host "Training jobs completed: $($trainingStats.training_jobs_completed)" -ForegroundColor Cyan
} catch {
    Write-Host "Could not retrieve training stats" -ForegroundColor Yellow
}

# Test manual training trigger
Write-Host "`nTesting manual training trigger..."
try {
    $trainingResult = Invoke-RestMethod -Uri "http://localhost:8012/train" -Method POST
    Write-Host "✓ Training job triggered: $($trainingResult.status)" -ForegroundColor Green
    Write-Host "Job ID: $($trainingResult.job_id)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ Training trigger failed" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Write-Host "`n5. Testing annotation workflow..." -ForegroundColor Yellow

# Open annotation frontend in browser for manual testing
Write-Host "Opening annotation frontend in browser..."
try {
    Start-Process "http://localhost:8011"
    Write-Host "✓ Annotation interface opened" -ForegroundColor Green
} catch {
    Write-Host "Could not open browser - please navigate to http://localhost:8011 manually" -ForegroundColor Yellow
}

Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
Write-Host "1. Services started and health checked"
Write-Host "2. Hard examples generated from edge inference"
Write-Host "3. Continuous learning pipeline components tested"
Write-Host "4. Manual training triggered"
Write-Host "5. Annotation interface available at http://localhost:8011"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "- Annotate hard examples in the web interface"
Write-Host "- Monitor training service logs for job progress"
Write-Host "- Check for model updates in the model-updates Kafka topic"

if ($CleanUp) {
    Write-Host "`nCleaning up..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "Services stopped" -ForegroundColor Green
}
