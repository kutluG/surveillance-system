#!/bin/bash

# Production Deployment Script for Surveillance System Website
# This script builds and deploys the website for production use

echo "🚀 Starting production deployment for Surveillance System Website..."

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production file not found!"
    echo "Please ensure the production environment file exists with proper API URLs."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install --production

# Build for production
echo "🔨 Building for production..."
npm run build:production

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "✅ Production build completed successfully!"
    echo "📁 Built files are in the 'build' directory"
    echo ""
    echo "🌐 Next steps for deployment:"
    echo "1. Upload the 'build' directory contents to your web server"
    echo "2. Configure your web server to serve the static files"
    echo "3. Ensure your backend APIs are running at: https://api.surveillance-ai.com"
    echo "4. Ensure WebSocket endpoint is available at: wss://ws.surveillance-ai.com"
    echo ""
    echo "📋 Production URLs configured:"
    echo "   API: https://api.surveillance-ai.com"
    echo "   WebSocket: wss://ws.surveillance-ai.com"
    echo ""
    echo "🔧 For deployment to popular platforms:"
    echo "   - Netlify: Drag and drop the 'build' folder"
    echo "   - Vercel: Connect your GitHub repo and deploy"
    echo "   - AWS S3: Upload to S3 bucket with static website hosting"
    echo "   - Traditional server: Copy build/* to your web root directory"
else
    echo "❌ Production build failed!"
    exit 1
fi
