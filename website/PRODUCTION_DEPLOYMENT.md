# Website Production Deployment Guide

## Overview
This guide explains how to deploy the AI-Powered Surveillance System website for production use, enabling real user signups and access.

## Current Status
- ✅ **Development**: Website works on localhost
- ❌ **Production**: Not yet deployed (people cannot sign up)

## What's Been Fixed
1. **Environment Configuration**: Created proper `.env.production` and `.env.development` files
2. **API URLs**: Configured production URLs (https://api.surveillance-ai.com)
3. **WebSocket URLs**: Configured production WebSocket (wss://ws.surveillance-ai.com)
4. **Build Scripts**: Added production build commands

## Files Modified/Created
- `.env.production` - Production environment variables
- `.env.development` - Development environment variables  
- `src/contexts/AppContext.js` - Updated to use environment variables
- `package.json` - Added production build scripts
- `deploy-production.sh` - Production deployment script

## Environment Variables

### Production (`.env.production`)
```
REACT_APP_API_URL=https://api.surveillance-ai.com
REACT_APP_WEBSOCKET_URL=wss://ws.surveillance-ai.com
REACT_APP_ENV=production
```

### Development (`.env.development`)
```
REACT_APP_API_URL=http://localhost:8001
REACT_APP_WEBSOCKET_URL=ws://localhost:8002/ws
REACT_APP_ENV=development
```

## Deployment Steps

### 1. Backend Infrastructure
Before deploying the website, ensure your backend is running on production servers:

```bash
# From the main project directory
cd surveillance-system

# Deploy backend services (choose one option):

# Option A: Docker Compose (recommended)
docker-compose -f docker-compose.production.yml up -d

# Option B: Kubernetes
kubectl apply -f k8s/

# Option C: Individual service deployment
# Deploy each microservice to your cloud provider
```

### 2. Domain Setup
Ensure these domains point to your backend infrastructure:
- `api.surveillance-ai.com` → Your API Gateway/Load Balancer
- `ws.surveillance-ai.com` → Your WebSocket service

### 3. Website Deployment

#### Option A: Automated Script
```bash
cd website
chmod +x deploy-production.sh
./deploy-production.sh
```

#### Option B: Manual Build
```bash
cd website
npm install
npm run build:production
```

### 4. Deploy to Hosting Platform

#### Netlify
1. Drag and drop the `build` folder to Netlify
2. Configure redirects for SPA routing

#### Vercel
1. Connect your GitHub repository
2. Set build command: `npm run build:production`
3. Set output directory: `build`

#### AWS S3 + CloudFront
```bash
# Upload to S3
aws s3 sync build/ s3://your-bucket-name --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths "/*"
```

#### Traditional Web Server (Apache/Nginx)
```bash
# Copy built files to web root
cp -r build/* /var/www/html/
```

## Testing Production Deployment

1. **Website Access**: Visit your production domain
2. **User Registration**: Test creating a new account
3. **API Connectivity**: Verify dashboard loads data
4. **WebSocket Connection**: Check real-time updates work
5. **Mobile Compatibility**: Test on mobile devices

## Troubleshooting

### Common Issues

#### "Cannot connect to API"
- Verify backend services are running on production
- Check CORS configuration allows your domain
- Ensure SSL certificates are properly configured

#### "WebSocket connection failed"
- Verify WebSocket service is accessible
- Check firewall rules for WebSocket ports
- Ensure SSL is configured for WebSocket endpoint

#### "404 on page refresh"
- Configure your web server for SPA routing
- Add redirect rules to serve `index.html` for all routes

## Security Considerations

1. **HTTPS Only**: Ensure all production URLs use HTTPS
2. **CORS Configuration**: Limit allowed origins to your domain
3. **API Keys**: Use production API keys, not development ones
4. **Content Security Policy**: Configure CSP headers
5. **Rate Limiting**: Implement rate limiting on backend APIs

## Monitoring

After deployment, monitor:
- Website uptime and performance
- API response times
- Error rates in browser console
- User registration success rates
- WebSocket connection stability

## Next Steps

1. **Deploy Backend**: Ensure all 8 microservices are running in production
2. **Configure Domains**: Set up DNS for api.surveillance-ai.com and ws.surveillance-ai.com
3. **Deploy Website**: Use one of the deployment options above
4. **Test Everything**: Verify all functionality works end-to-end
5. **Monitor**: Set up monitoring and alerts

## Support

If you encounter issues:
1. Check browser console for errors
2. Verify environment variables are correct
3. Test API endpoints directly
4. Check backend service logs
5. Verify SSL certificates are valid

---

**Important**: Once deployed to production, users will be able to:
- Sign up for new accounts
- Access the full surveillance system
- Use all features including real-time monitoring
- Connect mobile apps to the system
