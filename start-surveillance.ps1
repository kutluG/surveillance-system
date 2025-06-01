# PowerShell script to start the Surveillance System
# Run this script to start your surveillance system

Write-Host "Starting Surveillance System..." -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "IMPORTANT: Edit .env file and set your OPENAI_API_KEY!" -ForegroundColor Red
    Write-Host "   Get your API key from: https://platform.openai.com/api-keys" -ForegroundColor Yellow
    Read-Host "Press Enter after you've set your API key in .env file"
}

# Check if OpenAI API key is set
$envContent = Get-Content ".env" | Out-String
if ($envContent -match "OPENAI_API_KEY=your-openai-api-key-here") {
    Write-Host "Please set your OPENAI_API_KEY in .env file first!" -ForegroundColor Red
    Write-Host "   Edit .env file and replace 'your-openai-api-key-here' with your actual API key" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting infrastructure services..." -ForegroundColor Blue
docker-compose up -d postgres redis zookeeper kafka weaviate prometheus grafana

Write-Host "Waiting 30 seconds for infrastructure to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "Starting application services..." -ForegroundColor Blue
docker-compose up -d edge_service mqtt_kafka_bridge ingest_service rag_service prompt_service rulegen_service notifier vms_service

Write-Host "Waiting 15 seconds for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "Surveillance System Started!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "   • Grafana Dashboard:  http://localhost:3000 (admin/admin)" -ForegroundColor White
Write-Host "   • Prometheus:         http://localhost:9090" -ForegroundColor White
Write-Host "   • Edge Service API:   http://localhost:8001/docs" -ForegroundColor White
Write-Host "   • RAG Service API:    http://localhost:8004/docs" -ForegroundColor White
Write-Host "   • Notifier API:       http://localhost:8007/docs" -ForegroundColor White
Write-Host "   • VMS Service API:    http://localhost:8008/docs" -ForegroundColor White

Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Cyan
Write-Host "   • Check status:       .\check-status.ps1" -ForegroundColor White
Write-Host "   • View logs:          docker-compose logs -f" -ForegroundColor White
Write-Host "   • Stop system:        .\stop-surveillance.ps1" -ForegroundColor White
Write-Host "   • Health check:       python scripts/health_check.py" -ForegroundColor White

Write-Host ""
Write-Host "Camera Setup:" -ForegroundColor Cyan
Write-Host "   • Default: Uses webcam (device 0)" -ForegroundColor White
Write-Host "   • For IP camera: Edit CAPTURE_DEVICE in .env file" -ForegroundColor White

Write-Host ""
Write-Host "What's happening now:" -ForegroundColor Cyan
Write-Host "   1. System is processing video from your camera" -ForegroundColor White
Write-Host "   2. AI is analyzing frames for objects and activities" -ForegroundColor White
Write-Host "   3. Events trigger notifications and video clips" -ForegroundColor White
Write-Host "   4. Everything is monitored in Grafana dashboards" -ForegroundColor White
