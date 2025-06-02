# Production Setup Script for Windows
# This script configures the website for production deployment

Write-Host "🚀 Setting up Surveillance System Website for Production..." -ForegroundColor Green

# Check if we're in the website directory
if (-not (Test-Path "package.json")) {
    Write-Host "❌ Error: This script must be run from the website directory!" -ForegroundColor Red
    Write-Host "Navigate to: surveillance-system\website" -ForegroundColor Yellow
    exit 1
}

# Check Node.js installation
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js detected: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Node.js not found! Please install Node.js first." -ForegroundColor Red
    exit 1
}

# Check if environment files exist
if (-not (Test-Path ".env.production")) {
    Write-Host "❌ Error: .env.production file not found!" -ForegroundColor Red
    Write-Host "The production environment file should have been created automatically." -ForegroundColor Yellow
    exit 1
}

Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
npm install

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies!" -ForegroundColor Red
    exit 1
}

Write-Host "🔨 Building for production..." -ForegroundColor Cyan
npm run build:production

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Production build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Production build completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Built files are in the 'build' directory" -ForegroundColor Yellow
Write-Host ""
Write-Host "🌐 Production Configuration:" -ForegroundColor Cyan
Write-Host "   API URL: https://api.surveillance-ai.com" -ForegroundColor White
Write-Host "   WebSocket: wss://ws.surveillance-ai.com" -ForegroundColor White
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. 🖥️  Deploy backend services to production servers" -ForegroundColor White
Write-Host "2. 🌍  Configure DNS for api.surveillance-ai.com and ws.surveillance-ai.com" -ForegroundColor White
Write-Host "3. 📤  Upload the 'build' directory to your web hosting platform" -ForegroundColor White
Write-Host "4. 🔧  Configure your web server for SPA routing" -ForegroundColor White
Write-Host "5. 🧪  Test the production deployment" -ForegroundColor White
Write-Host ""
Write-Host "🚀 Deployment Options:" -ForegroundColor Cyan
Write-Host "   • Netlify: Drag and drop the 'build' folder" -ForegroundColor White
Write-Host "   • Vercel: Connect GitHub repo and deploy" -ForegroundColor White
Write-Host "   • AWS S3: Enable static website hosting" -ForegroundColor White
Write-Host "   • Azure Static Web Apps: Connect to repository" -ForegroundColor White
Write-Host "   • Traditional server: Copy build/* to web root" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  Important: Users can only sign up once backend is deployed!" -ForegroundColor Yellow
Write-Host ""
Write-Host "📖 For detailed instructions, see: PRODUCTION_DEPLOYMENT.md" -ForegroundColor Cyan
