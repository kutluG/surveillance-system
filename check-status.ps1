# PowerShell script to check Surveillance System status

Write-Host "🔍 Surveillance System Status" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

Write-Host "`n🐳 Docker Services:" -ForegroundColor Yellow
docker-compose ps

Write-Host "`n🌐 Service Health Check:" -ForegroundColor Yellow
$services = @(
    @{Name="Edge Service"; URL="http://localhost:8001/health"},
    @{Name="RAG Service"; URL="http://localhost:8004/health"},
    @{Name="Notifier"; URL="http://localhost:8007/health"},
    @{Name="VMS Service"; URL="http://localhost:8008/health"},
    @{Name="Prometheus"; URL="http://localhost:9090/-/healthy"},
    @{Name="Grafana"; URL="http://localhost:3000/api/health"}
)

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri $service.URL -Method GET -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "   ✅ $($service.Name): Healthy" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  $($service.Name): Status $($response.StatusCode)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "   ❌ $($service.Name): Not responding" -ForegroundColor Red
    }
}

Write-Host "`n📊 Quick Access Links:" -ForegroundColor Cyan
Write-Host "   • Grafana: http://localhost:3000" -ForegroundColor White
Write-Host "   • Prometheus: http://localhost:9090" -ForegroundColor White
Write-Host "   • API Docs: http://localhost:8001/docs" -ForegroundColor White
