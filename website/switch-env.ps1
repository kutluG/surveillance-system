# Environment Switcher for Development and Production
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("development", "production")]
    [string]$Environment
)

Write-Host "🔄 Switching to $Environment environment..." -ForegroundColor Cyan

# Check if we're in the website directory
if (-not (Test-Path "package.json")) {
    Write-Host "❌ Error: This script must be run from the website directory!" -ForegroundColor Red
    exit 1
}

# Copy the appropriate environment file to .env
$envFile = ".env.$Environment"
if (Test-Path $envFile) {
    Copy-Item $envFile ".env" -Force
    Write-Host "✅ Switched to $Environment environment" -ForegroundColor Green
    
    # Display current configuration
    Write-Host ""
    Write-Host "📋 Current Configuration:" -ForegroundColor Cyan
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^REACT_APP_") {
            Write-Host "   $_" -ForegroundColor White
        }
    }
    
    Write-Host ""
    if ($Environment -eq "development") {
        Write-Host "🏠 Development Mode Active" -ForegroundColor Green
        Write-Host "   • API: http://localhost:8001" -ForegroundColor White
        Write-Host "   • WebSocket: ws://localhost:8002/ws" -ForegroundColor White
        Write-Host "   • Start with: npm start" -ForegroundColor Yellow
    } else {
        Write-Host "🚀 Production Mode Active" -ForegroundColor Green
        Write-Host "   • API: https://api.surveillance-ai.com" -ForegroundColor White
        Write-Host "   • WebSocket: wss://ws.surveillance-ai.com" -ForegroundColor White
        Write-Host "   • Build with: npm run build:production" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Error: Environment file $envFile not found!" -ForegroundColor Red
    exit 1
}
