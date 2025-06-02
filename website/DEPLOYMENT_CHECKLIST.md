# 🚀 Production Deployment Checklist

## Pre-Deployment ✅

- [x] **Website Configuration Complete**
  - [x] Environment variables configured
  - [x] Production build scripts ready
  - [x] Dynamic URL configuration implemented
  - [x] Cross-platform build support added

- [x] **Mobile App Configuration**
  - [x] Production environment configured
  - [x] API endpoints set to production URLs

## Backend Deployment 🖥️

- [ ] **Deploy Microservices**
  - [ ] Authentication Service (Port 8001)
  - [ ] Camera Management Service (Port 8002) 
  - [ ] Alert Service (Port 8003)
  - [ ] Dashboard Service (Port 8004)
  - [ ] VMS Service (Port 8005)
  - [ ] RAG Service (Port 8006)
  - [ ] Prompt Service (Port 8007)
  - [ ] Rule Generation Service (Port 8008)
  - [ ] Notifier Service (Port 8009)

- [ ] **Configure Infrastructure**
  - [ ] Load balancer/API Gateway
  - [ ] Database connections
  - [ ] Redis/caching layer
  - [ ] Message queue (Kafka/RabbitMQ)
  - [ ] Object storage (S3/Azure Blob)

## Domain & DNS Configuration 🌐

- [ ] **Set up DNS Records**
  - [ ] `api.surveillance-ai.com` → Backend services
  - [ ] `ws.surveillance-ai.com` → WebSocket service
  - [ ] `monitoring.surveillance-ai.com` → Grafana
  - [ ] `metrics.surveillance-ai.com` → Prometheus
  - [ ] `app.surveillance-ai.com` → Website

- [ ] **SSL Certificates**
  - [ ] Obtain SSL certificates for all domains
  - [ ] Configure HTTPS redirects
  - [ ] Verify certificate chains

## Website Deployment 📱

- [ ] **Build & Deploy**
  - [ ] Run production build: `npm run build:production`
  - [ ] Upload to hosting platform
  - [ ] Configure SPA routing
  - [ ] Set up CDN (optional)

## Testing & Verification 🧪

- [ ] **Backend Testing**
  - [ ] Health check endpoints respond
  - [ ] API authentication works
  - [ ] Database connections established
  - [ ] WebSocket connections stable

- [ ] **Website Testing** 
  - [ ] User registration works
  - [ ] Login/logout functionality
  - [ ] Dashboard loads real data
  - [ ] Real-time updates via WebSocket
  - [ ] All pages load correctly

- [ ] **Mobile App Testing**
  - [ ] Can connect to production APIs
  - [ ] Push notifications work
  - [ ] Camera feeds stream correctly
  - [ ] Alerts display properly

## Security & Monitoring 🔒

- [ ] **Security Configuration**
  - [ ] CORS settings updated
  - [ ] Rate limiting enabled
  - [ ] Input validation active
  - [ ] SQL injection protection
  - [ ] XSS protection headers

- [ ] **Monitoring Setup**
  - [ ] Prometheus collecting metrics
  - [ ] Grafana dashboards configured
  - [ ] Log aggregation working
  - [ ] Alert rules configured
  - [ ] Error tracking enabled

## Performance Optimization ⚡

- [ ] **Frontend Optimization**
  - [ ] Static assets compressed
  - [ ] Images optimized
  - [ ] Lazy loading implemented
  - [ ] Bundle size optimized

- [ ] **Backend Optimization**
  - [ ] Database queries optimized
  - [ ] Caching strategies implemented
  - [ ] Connection pooling configured
  - [ ] Resource limits set

## Post-Deployment 📊

- [ ] **Monitor System Health**
  - [ ] Check error rates
  - [ ] Monitor response times
  - [ ] Verify user signups working
  - [ ] Confirm real-time features active

- [ ] **Documentation Update**
  - [ ] Update API documentation
  - [ ] Create user guides
  - [ ] Document deployment process
  - [ ] Update troubleshooting guides

---

## Quick Commands 💨

### Build Website for Production
```powershell
cd website
npm run build:production
```

### Deploy Backend Services
```powershell
cd surveillance-system
docker-compose -f docker-compose.production.yml up -d
```

### Test Production Build Locally
```powershell
cd website
npm install -g serve
serve -s build -l 3000
```

### Check Service Health
```powershell
# Test API endpoint
curl https://api.surveillance-ai.com/health

# Test WebSocket
# Use browser dev tools or WebSocket testing tool
```

---

## 🆘 Troubleshooting

### Common Issues
1. **"Cannot connect to API"** → Check backend deployment and DNS
2. **"WebSocket connection failed"** → Verify WebSocket service and SSL
3. **"404 on page refresh"** → Configure SPA routing on web server
4. **"CORS errors"** → Update CORS configuration for production domain

### Support Resources
- `PRODUCTION_DEPLOYMENT.md` - Detailed deployment guide
- `DEPLOYMENT_STATUS.md` - Current system status
- Health check scripts in `/scripts` folder
- Monitoring dashboards for real-time diagnostics
