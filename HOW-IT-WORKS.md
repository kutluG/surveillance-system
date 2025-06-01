# 🎯 How Your Surveillance System Works

## Overview
Your surveillance system is a **complete AI-powered video surveillance platform** that processes video streams, detects events, and sends intelligent notifications.

## 🏗️ System Architecture

```
📹 Camera Feed → 🤖 AI Analysis → 🔔 Smart Alerts → 📊 Monitoring
      ↓              ↓              ↓              ↓
   Video Input → Object Detection → Notifications → Dashboards
      ↓              ↓              ↓              ↓
   Edge Service → RAG Service → Notifier Service → Grafana
```

## 🔧 What Each Service Does

### **Core Application Services**
- **Edge Service** (Port 8001): Captures video, runs AI object detection
- **VMS Service** (Port 8008): Manages video clips, storage
- **RAG Service** (Port 8004): AI-powered analysis and intelligent responses
- **Notifier** (Port 8007): Sends alerts via email, SMS, Slack, webhooks
- **Rule Engine** (Port 8006): Creates dynamic rules for when to alert
- **Ingest Service** (Port 8003): Processes and stores event data

### **Infrastructure Services**
- **PostgreSQL** (Port 5432): Stores events, rules, user data
- **Redis** (Port 6379): Caching and session storage
- **Kafka** (Port 9092): Message queue for real-time event processing
- **Weaviate** (Port 8080): Vector database for AI embeddings
- **Prometheus** (Port 9090): Metrics collection
- **Grafana** (Port 3000): Monitoring dashboards

### **Integration Services**
- **MQTT-Kafka Bridge** (Port 8002): Connects MQTT cameras to Kafka

## 🚀 How to Use Your System

### **1. First Time Setup**
```powershell
# Edit your API key in .env file
notepad .env
# Replace 'your-openai-api-key-here' with actual OpenAI API key

# Start the system
.\start-surveillance.ps1
```

### **2. Access the System**
- **Main Dashboard**: http://localhost:3000 (Grafana - admin/admin)
- **Video Analysis API**: http://localhost:8001/docs
- **AI Analysis API**: http://localhost:8004/docs
- **Notification System**: http://localhost:8007/docs

### **3. Check System Status**
```powershell
.\check-status.ps1
```

### **4. Stop the System**
```powershell
.\stop-surveillance.ps1
```

## 📹 Camera Configuration

### **Webcam (Default)**
- System automatically uses your computer's webcam
- No additional setup needed

### **IP Camera**
Edit `.env` file:
```
CAPTURE_DEVICE=rtsp://username:password@192.168.1.100/stream
```

### **Multiple Cameras**
Edit `docker-compose.yml` to add more edge service instances with different camera IDs.

## 🤖 What the AI Does

1. **Object Detection**: Identifies people, vehicles, animals, packages
2. **Activity Recognition**: Detects suspicious activities, intrusions
3. **Smart Filtering**: Only alerts on relevant events (not every motion)
4. **Context Understanding**: Explains what's happening in plain English
5. **Rule Generation**: Creates custom rules based on your environment

## 🔔 Notification Types

The system can send alerts via:
- **Email**: SMTP configuration in .env
- **SMS**: Twilio integration
- **Slack**: Webhook integration
- **Custom Webhooks**: For integration with other systems

## 📊 Monitoring & Dashboards

### **Grafana Dashboard** (http://localhost:3000)
- Real-time video processing metrics
- Alert frequency and types
- System performance monitoring
- Camera feed status

### **Prometheus** (http://localhost:9090)
- Raw metrics collection
- Alert rule management
- System health monitoring

## 🎯 Real-World Use Cases

1. **Home Security**: Detect intruders, package deliveries
2. **Business Monitoring**: Track employee activity, customer behavior
3. **Pet Monitoring**: Watch pets when away from home
4. **Elderly Care**: Monitor for falls or emergencies
5. **Industrial Safety**: Detect safety violations, equipment issues

## 🔧 Configuration Files

- **`.env`**: Main configuration (API keys, database settings)
- **`docker-compose.yml`**: Service orchestration
- **`monitoring/prometheus.yml`**: Metrics configuration
- **`shared/config.py`**: Application settings

## 🚨 Common Issues & Solutions

### **Service Won't Start**
```powershell
# Check Docker is running
docker version

# Check port conflicts
netstat -an | findstr "8001"

# Restart Docker Desktop
```

### **No Video Input**
- Check camera permissions
- Verify CAPTURE_DEVICE setting in .env
- Test camera with other applications

### **AI Not Working**
- Verify OPENAI_API_KEY is set correctly
- Check internet connection
- View logs: `docker-compose logs rag_service`

### **No Alerts**
- Check notification settings in .env
- Verify email/SMS credentials
- Test notification endpoints manually

## 📈 Performance Tuning

### **For Better Performance**
- Increase Docker Desktop memory allocation (8GB+)
- Use dedicated GPU for AI processing (NVIDIA)
- Optimize video resolution in .env file

### **For Lower Resource Usage**
- Reduce video quality
- Increase AI processing intervals
- Disable unused notification channels

## 🔐 Security Considerations

- Change default passwords in .env
- Use HTTPS in production
- Secure API endpoints with authentication
- Regular security updates via Docker images

## 📝 Logs & Troubleshooting

```powershell
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f edge_service

# Check service health
python scripts/health_check.py
```

## 🎉 What You Can Do Now

1. **Monitor Live Video**: See real-time AI analysis in Grafana
2. **Get Smart Alerts**: Receive notifications for important events
3. **Review Video Clips**: Access saved clips when events occur
4. **Customize Rules**: Modify when and how you get alerted
5. **Scale Up**: Add more cameras and processing power
6. **Integrate**: Connect to existing security systems

Your surveillance system is now a complete, production-ready platform that rivals commercial solutions!
