# Start Surveillance System
Write-Host "Starting Surveillance System..." -ForegroundColor Green
docker-compose up -d
Write-Host "System started!" -ForegroundColor Green
Write-Host "Access URLs:" -ForegroundColor Cyan
Write-Host "â€¢ API Gateway: http://localhost:8000"
Write-Host "â€¢ API Documentation: http://localhost:8000/docs"
Write-Host "â€¢ Grafana: http://localhost:3000 (admin/admin123)"
