# Surveillance System - Detaylı Durum Kontrol Scripti
# Tüm servislerin durumunu kontrol eder ve detaylı raporlama yapar

param(
    [switch]$Detailed,
    [switch]$Json,
    [switch]$Watch
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
function Write-Error { Write-ColorOutput Red $args }

function Get-SystemStatus {
    $status = @{
        Timestamp = Get-Date
        Docker = $null
        Containers = @()
        Services = @()
        Resources = @{
            CPU = $null
            Memory = $null
            Disk = $null
        }
    }

    # Docker durumu kontrol et
    try {
        docker version | Out-Null
        $status.Docker = "Running"
        Write-Success "✅ Docker: Çalışıyor"
    }
    catch {
        $status.Docker = "Not Running"
        Write-Error "❌ Docker: Çalışmıyor"
        return $status
    }

    # Container durumları
    try {
        $containers = docker ps --format "{{.Names}},{{.Status}},{{.Ports}}" | ConvertFrom-Csv -Header "Name","Status","Ports"
        foreach ($container in $containers) {
            $status.Containers += @{
                Name = $container.Name
                Status = $container.Status
                Ports = $container.Ports
            }
        }
        Write-Info "📦 Çalışan container sayısı: $($containers.Count)"
    }
    catch {
        Write-Warning "⚠️  Container bilgileri alınamadı"
    }

    # Servis sağlık kontrolleri
    $services = @(
        @{Name="API Gateway"; URL="http://localhost:8000/health"; Port=8000},
        @{Name="Grafana"; URL="http://localhost:3000/api/health"; Port=3000},
        @{Name="Prometheus"; URL="http://localhost:9090/-/healthy"; Port=9090},
        @{Name="AI Dashboard"; URL="http://localhost:8001/health"; Port=8001},
        @{Name="Edge Service"; URL="http://localhost:8002/health"; Port=8002},
        @{Name="VMS Service"; URL="http://localhost:8003/health"; Port=8003},
        @{Name="Ingest Service"; URL="http://localhost:8004/health"; Port=8004},
        @{Name="Prompt Service"; URL="http://localhost:8005/health"; Port=8005},
        @{Name="RAG Service"; URL="http://localhost:8006/health"; Port=8006},
        @{Name="Notifier"; URL="http://localhost:8007/health"; Port=8007}
    )

    Write-Info "`n🏥 Servis sağlık kontrolleri:"
    foreach ($service in $services) {
        $serviceStatus = @{
            Name = $service.Name
            URL = $service.URL
            Port = $service.Port
            Status = "Unknown"
            ResponseTime = $null
        }

        try {
            $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
            $response = Invoke-WebRequest -Uri $service.URL -TimeoutSec 5 -UseBasicParsing
            $stopwatch.Stop()
            
            if ($response.StatusCode -eq 200) {
                $serviceStatus.Status = "Healthy"
                $serviceStatus.ResponseTime = $stopwatch.ElapsedMilliseconds
                Write-Success "✅ $($service.Name): Sağlıklı ($($stopwatch.ElapsedMilliseconds)ms)"
            }
        }
        catch {
            $serviceStatus.Status = "Unhealthy"
            Write-Error "❌ $($service.Name): Sağlıksız"
        }
        
        $status.Services += $serviceStatus
    }

    # Sistem kaynaklarını kontrol et
    if ($Detailed) {
        Write-Info "`n💻 Sistem kaynakları:"
        try {
            # CPU kullanımı
            $cpu = Get-WmiObject -Class WIN32_Processor | Measure-Object -Property LoadPercentage -Average
            $status.Resources.CPU = $cpu.Average
            Write-Info "• CPU: %$($cpu.Average)"

            # Bellek kullanımı
            $os = Get-WmiObject -Class WIN32_OperatingSystem
            $totalMemory = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
            $freeMemory = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
            $usedMemory = $totalMemory - $freeMemory
            $memoryPercent = [math]::Round(($usedMemory / $totalMemory) * 100, 2)
            $status.Resources.Memory = @{
                Total = $totalMemory
                Used = $usedMemory
                Free = $freeMemory
                Percent = $memoryPercent
            }
            Write-Info "• Bellek: $usedMemory GB / $totalMemory GB (%$memoryPercent)"

            # Disk kullanımı
            $disk = Get-WmiObject -Class WIN32_LogicalDisk -Filter "DriveType=3" | Where-Object {$_.DeviceID -eq "C:"}
            $totalDisk = [math]::Round($disk.Size / 1GB, 2)
            $freeDisk = [math]::Round($disk.FreeSpace / 1GB, 2)
            $usedDisk = $totalDisk - $freeDisk
            $diskPercent = [math]::Round(($usedDisk / $totalDisk) * 100, 2)
            $status.Resources.Disk = @{
                Total = $totalDisk
                Used = $usedDisk
                Free = $freeDisk
                Percent = $diskPercent
            }
            Write-Info "• Disk (C:): $usedDisk GB / $totalDisk GB (%$diskPercent)"
        }
        catch {
            Write-Warning "⚠️  Sistem kaynak bilgileri alınamadı"
        }
    }

    return $status
}

function Show-QuickActions {
    Write-Info "`n💡 Hızlı İşlemler:"
    Write-Host "• Sistemi başlat: .\quick-start.ps1" -ForegroundColor Cyan
    Write-Host "• Sistemi durdur: .\quick-start.ps1 -Stop" -ForegroundColor Cyan
    Write-Host "• Sistemi yeniden başlat: .\quick-start.ps1 -Restart" -ForegroundColor Cyan
    Write-Host "• Logları görüntüle: .\quick-start.ps1 -Logs" -ForegroundColor Cyan
    Write-Host "• Detaylı durum: .\check-status.ps1 -Detailed" -ForegroundColor Cyan
    Write-Host "• JSON çıktı: .\check-status.ps1 -Json" -ForegroundColor Cyan
    Write-Host "• Sürekli izleme: .\check-status.ps1 -Watch" -ForegroundColor Cyan

    Write-Info "`n🌐 Servis URL'leri:"
    Write-Host "• API Gateway: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "• Grafana Monitoring: http://localhost:3000 (admin/admin123)" -ForegroundColor Cyan
    Write-Host "• Prometheus: http://localhost:9090" -ForegroundColor Cyan
    Write-Host "• AI Dashboard: http://localhost:8001" -ForegroundColor Cyan
}

# Ana fonksiyon
function Start-StatusCheck {
    if ($Watch) {
        Write-Host "🔄 Sürekli izleme modu (Ctrl+C ile çıkış)" -ForegroundColor Yellow
        while ($true) {
            Clear-Host
            Write-Host "🚀 Surveillance System - Durum Kontrol ($((Get-Date).ToString()))" -ForegroundColor Magenta
            Write-Host "=" * 60 -ForegroundColor Magenta
            
            $status = Get-SystemStatus
            
            if (!$Json) {
                Show-QuickActions
            }
            
            Start-Sleep -Seconds 10
        }
    }
    else {
        Write-Host "🚀 Surveillance System - Durum Kontrol" -ForegroundColor Magenta
        Write-Host "=" * 45 -ForegroundColor Magenta
        
        $status = Get-SystemStatus
        
        if ($Json) {
            $status | ConvertTo-Json -Depth 4
        }
        else {
            Show-QuickActions
        }
    }
}

# Script'i çalıştır
Start-StatusCheck
