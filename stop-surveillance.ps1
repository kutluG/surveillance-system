# PowerShell script to stop the Surveillance System

Write-Host "🛑 Stopping Surveillance System..." -ForegroundColor Red
Write-Host "===================================" -ForegroundColor Red

docker-compose down

Write-Host "`n✅ Surveillance System Stopped!" -ForegroundColor Green
Write-Host "`n🔄 To start again, run: .\start-surveillance.ps1" -ForegroundColor Cyan
