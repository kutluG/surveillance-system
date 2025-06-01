# Alternative: Start Surveillance System without WSL (Windows containers)

Write-Host "🚀 Starting Surveillance System (Windows Mode)" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

Write-Host "`n⚠️  Note: Running in Windows container mode due to WSL issues" -ForegroundColor Yellow
Write-Host "   This mode has some limitations but will work for basic functionality." -ForegroundColor White

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    Write-Host "   1. Open Docker Desktop" -ForegroundColor Yellow
    Write-Host "   2. Wait for it to start completely" -ForegroundColor Yellow
    Write-Host "   3. Run this script again" -ForegroundColor Yellow
    exit 1
}

# Switch to Windows containers if possible
Write-Host "`n🔄 Attempting to switch to Windows containers..." -ForegroundColor Blue
try {
    & "C:\Program Files\Docker\Docker\DockerCli.exe" -SwitchWindowsEngine
    Start-Sleep -Seconds 10
    Write-Host "✅ Switched to Windows containers" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not switch to Windows containers automatically" -ForegroundColor Yellow
    Write-Host "   You may need to right-click Docker Desktop system tray icon" -ForegroundColor White
    Write-Host "   and select 'Switch to Windows containers'" -ForegroundColor White
}

# Check .env file
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# Check OpenAI API key
$envContent = Get-Content ".env" | Out-String
if ($envContent -match "OPENAI_API_KEY=your-openai-api-key-here") {
    Write-Host "❌ Please set your OPENAI_API_KEY in .env file first!" -ForegroundColor Red
    Write-Host "   Edit .env file and add your OpenAI API key" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n🐳 Starting surveillance system..." -ForegroundColor Blue

# Start with reduced services for Windows compatibility
Write-Host "Starting core services..." -ForegroundColor White
docker-compose up -d postgres redis prometheus grafana

Write-Host "Starting application services..." -ForegroundColor White
docker-compose up -d edge_service rag_service notifier

Write-Host "`n🎉 Basic surveillance system started!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

Write-Host "`n📊 Available services:" -ForegroundColor Cyan
Write-Host "   • Grafana:      http://localhost:3000 (admin/admin)" -ForegroundColor White
Write-Host "   • Prometheus:   http://localhost:9090" -ForegroundColor White
Write-Host "   • Edge Service: http://localhost:8001/docs" -ForegroundColor White
Write-Host "   • RAG Service:  http://localhost:8004/docs" -ForegroundColor White
Write-Host "   • Notifier:     http://localhost:8007/docs" -ForegroundColor White

Write-Host "`n📝 Note: Some services may be limited in Windows container mode." -ForegroundColor Yellow
Write-Host "   For full functionality, fix WSL using fix-docker.ps1" -ForegroundColor White
