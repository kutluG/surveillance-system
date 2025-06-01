# Simple WSL Fix Script - Run as Administrator

Write-Host "🔧 Fixing WSL for Docker Desktop" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "❌ Please run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Running as Administrator" -ForegroundColor Green

Write-Host "`n🔧 Enabling Windows features..." -ForegroundColor Yellow

# Enable WSL
Write-Host "Enabling WSL..." -ForegroundColor White
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Enable Virtual Machine Platform  
Write-Host "Enabling Virtual Machine Platform..." -ForegroundColor White
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Enable Hyper-V
Write-Host "Enabling Hyper-V..." -ForegroundColor White
dism.exe /online /enable-feature /featurename:Microsoft-Hyper-V /all /norestart

Write-Host "`n✅ Features enabled!" -ForegroundColor Green
Write-Host "`n⚠️ RESTART REQUIRED!" -ForegroundColor Yellow
Write-Host "Your computer needs to restart to apply changes." -ForegroundColor White

Write-Host "`nAfter restart:" -ForegroundColor Cyan
Write-Host "1. Download WSL2 kernel: https://aka.ms/wsl2kernel" -ForegroundColor White
Write-Host "2. Install the downloaded file" -ForegroundColor White
Write-Host "3. Open PowerShell as Admin and run: wsl --set-default-version 2" -ForegroundColor White
Write-Host "4. Start Docker Desktop" -ForegroundColor White

$restart = Read-Host "`nRestart now? (y/N)"
if ($restart -eq 'y' -or $restart -eq 'Y') {
    Write-Host "Restarting..." -ForegroundColor Blue
    Restart-Computer -Force
} else {
    Write-Host "Please restart manually." -ForegroundColor Yellow
}
