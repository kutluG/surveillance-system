# PowerShell script to fix Docker Desktop WSL issues

Write-Host "🔧 Docker Desktop WSL Fix Script" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

Write-Host "`n📋 Checking current system status..." -ForegroundColor Yellow

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "❌ This script needs to run as Administrator!" -ForegroundColor Red
    Write-Host "   Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Running as Administrator" -ForegroundColor Green

# Check Windows version
$windowsVersion = [Environment]::OSVersion.Version
Write-Host "Windows Version: $windowsVersion" -ForegroundColor White

# Check if WSL is installed
try {
    $wslStatus = wsl --status 2>$null
    Write-Host "✅ WSL is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ WSL is not properly installed" -ForegroundColor Red
}

Write-Host "`n🔧 Applying fixes..." -ForegroundColor Yellow

# Enable WSL feature
Write-Host "Enabling WSL feature..." -ForegroundColor White
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Enable Virtual Machine Platform
Write-Host "Enabling Virtual Machine Platform..." -ForegroundColor White
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Enable Hyper-V (if available)
Write-Host "Enabling Hyper-V..." -ForegroundColor White
dism.exe /online /enable-feature /featurename:Microsoft-Hyper-V /all /norestart

Write-Host "`n✅ Features enabled successfully!" -ForegroundColor Green
Write-Host "`n⚠️  IMPORTANT: You need to restart your computer now!" -ForegroundColor Yellow
Write-Host "   After restart, run this script again to complete the setup." -ForegroundColor White

$restart = Read-Host "`nRestart now? (y/N)"
if ($restart -eq 'y' -or $restart -eq 'Y') {
    Write-Host "🔄 Restarting computer..." -ForegroundColor Blue
    Restart-Computer -Force
} else {
    Write-Host "📝 Please restart manually and run this script again." -ForegroundColor Yellow
}
