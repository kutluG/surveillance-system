# Complete WSL2 Setup Script
# Run this AFTER system restart

Write-Host "🔧 Completing WSL2 Setup..." -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green

Write-Host "📋 Step 1: Checking WSL status..." -ForegroundColor Yellow
try {
    $wslStatus = wsl --status 2>$null
    if ($wslStatus) {
        Write-Host "✅ WSL is installed and working!" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  WSL needs to be configured..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📋 Step 2: Download WSL2 Kernel Update" -ForegroundColor Yellow
Write-Host "   Please download from: https://aka.ms/wsl2kernel" -ForegroundColor Cyan
Write-Host "   This will open in your browser..." -ForegroundColor White
Start-Process "https://aka.ms/wsl2kernel"
Read-Host "   Press Enter AFTER you've downloaded and installed the kernel update"

Write-Host ""
Write-Host "📋 Step 3: Setting WSL2 as default..." -ForegroundColor Yellow
try {
    wsl --set-default-version 2
    Write-Host "✅ WSL2 set as default version!" -ForegroundColor Green
} catch {
    Write-Host "❌ Error setting WSL2 as default" -ForegroundColor Red
}

Write-Host ""
Write-Host "📋 Step 4: Installing Ubuntu distribution..." -ForegroundColor Yellow
try {
    wsl --install Ubuntu
    Write-Host "✅ Ubuntu installation started!" -ForegroundColor Green
    Write-Host "   Note: This may take several minutes..." -ForegroundColor White
} catch {
    Write-Host "⚠️  Ubuntu may already be installed or there was an issue" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📋 Step 5: Checking Docker Desktop..." -ForegroundColor Yellow
$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProcess) {
    Write-Host "✅ Docker Desktop is running!" -ForegroundColor Green
} else {
    Write-Host "🐳 Starting Docker Desktop..." -ForegroundColor Blue
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Write-Host "   Waiting for Docker Desktop to start..." -ForegroundColor White
    Start-Sleep -Seconds 30
}

Write-Host ""
Write-Host "🎉 WSL2 Setup Complete!" -ForegroundColor Green
Write-Host "========================" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Wait for Docker Desktop to fully start" -ForegroundColor White
Write-Host "   2. Run: .\start-surveillance.ps1" -ForegroundColor White
Write-Host "   3. Check status: .\check-status.ps1" -ForegroundColor White
Write-Host ""
Write-Host "💡 If you encounter issues:" -ForegroundColor Yellow
Write-Host "   • Restart Docker Desktop" -ForegroundColor White
Write-Host "   • Run: .\fix-wsl-simple.ps1" -ForegroundColor White
Write-Host "   • Use Windows containers: .\start-surveillance-windows.ps1" -ForegroundColor White
