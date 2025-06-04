# Surveillance System - Hızlı Başlatma Scripti
# Bu script sistemi hızlıca başlatır ve temel kontrolleri yapar

param(
    [switch]$Stop,
    [switch]$Restart,
    [switch]$Status,
    [switch]$Logs,
    [string]$Service = ""
)

function Write-ColorOutput($ForegroundColor) {
    if ($Host.UI.RawUI.ForegroundColor) {
        $fc = $Host.UI.RawUI.ForegroundColor
        $Host.UI.RawUI.ForegroundColor = $ForegroundColor
        if ($args) {
            Write-Output $args
        } else {
            $input | Write-Output
        }
        $Host.UI.RawUI.ForegroundColor = $fc
    } else {
        if ($args) {
            Write-Output $args
        } else {
            $input | Write-Output
        }
    }
}

function Write-Success { Write-ColorOutput Green $args }
function Write-Info { Write-ColorOutput Cyan $args }
function Write-Warning { Write-ColorOutput Yellow $args }

Write-Host "🚀 Surveillance System - Quick Start" -ForegroundColor Magenta

if ($Stop) {
    Write-Info "🛑 Sistem durduruluyor..."
    docker-compose down
    Write-Success "✅ Sistem durduruldu"
}
elseif ($Restart) {
    Write-Info "🔄 Sistem yeniden başlatılıyor..."
    docker-compose restart
    Write-Success "✅ Sistem yeniden başlatıldı"
}
elseif ($Status) {
    Write-Info "📊 Sistem durumu kontrol ediliyor..."
    docker-compose ps
    Write-Host "`n🌐 Servis URL'leri:" -ForegroundColor Yellow
    Write-Host "• API Gateway: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "• Grafana: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "• Prometheus: http://localhost:9090" -ForegroundColor Cyan
}
elseif ($Logs) {
    if ($Service) {
        Write-Info "📋 $Service logları gösteriliyor..."
        docker-compose logs -f $Service
    } else {
        Write-Info "📋 Tüm servis logları gösteriliyor..."
        docker-compose logs -f
    }
}
else {
    Write-Info "🚀 Sistem başlatılıyor..."
    
    # Docker'ın çalışıp çalışmadığını kontrol et
    try {
        docker ps | Out-Null
    }
    catch {
        Write-Warning "⚠️  Docker çalışmıyor. Docker Desktop'ı başlatın."
        exit 1
    }
    
    # Servisleri başlat
    docker-compose up -d
    
    Write-Success "✅ Sistem başlatıldı"
    Write-Host "`n🌐 Servis URL'leri:" -ForegroundColor Yellow
    Write-Host "• API Gateway: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "• Grafana: http://localhost:3000 (admin/admin123)" -ForegroundColor Cyan
    Write-Host "• Prometheus: http://localhost:9090" -ForegroundColor Cyan
    
    Write-Host "`n💡 Kullanışlı komutlar:" -ForegroundColor Yellow
    Write-Host "• Durdur: .\quick-start.ps1 -Stop" -ForegroundColor Cyan
    Write-Host "• Yeniden başlat: .\quick-start.ps1 -Restart" -ForegroundColor Cyan
    Write-Host "• Durum: .\quick-start.ps1 -Status" -ForegroundColor Cyan
    Write-Host "• Loglar: .\quick-start.ps1 -Logs" -ForegroundColor Cyan
}
