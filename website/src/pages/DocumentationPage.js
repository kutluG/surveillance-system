import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { getServiceUrls, getDisplayUrls } from '../config/urls';

export default function DocumentationPage() {
  const [activeSection, setActiveSection] = useState('overview');
  const serviceUrls = getServiceUrls();
  const displayUrls = getDisplayUrls();

  const sections = [
    { id: 'overview', title: 'Overview', icon: '📖' },
    { id: 'quick-start', title: 'Quick Start', icon: '🚀' },
    { id: 'installation', title: 'Installation', icon: '⚙️' },
    { id: 'configuration', title: 'Configuration', icon: '🔧' },
    { id: 'api', title: 'API Reference', icon: '🔌' },
    { id: 'troubleshooting', title: 'Troubleshooting', icon: '🔍' },
  ];

  const documentation = {
    overview: {
      title: 'SurveillanceAI Overview',
      content: (
        <div className="space-y-6">
          <p className="text-slate-300 leading-relaxed">
            SurveillanceAI is an enterprise-grade AI-powered surveillance system built with modern microservices architecture. 
            It provides real-time monitoring, intelligent threat detection, and comprehensive analytics for security operations.
          </p>
          
          <h3 className="text-xl font-semibold text-white">Key Features</h3>
          <ul className="space-y-2 text-slate-300">
            <li className="flex items-start space-x-2">
              <span className="text-blue-400 mt-1">•</span>
              <span>Real-time AI-powered object and behavior detection</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-blue-400 mt-1">•</span>
              <span>Microservices architecture with 8+ specialized services</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-blue-400 mt-1">•</span>
              <span>Enterprise monitoring with Prometheus and Grafana</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-blue-400 mt-1">•</span>
              <span>MQTT and Kafka event streaming</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-blue-400 mt-1">•</span>
              <span>Vector database integration with Weaviate</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-blue-400 mt-1">•</span>
              <span>Multi-channel notification system</span>
            </li>
          </ul>

          <h3 className="text-xl font-semibold text-white">Architecture</h3>
          <p className="text-slate-300 leading-relaxed">
            The system is built using a distributed microservices architecture, enabling scalability, 
            maintainability, and fault tolerance. Each service is containerized and can be deployed independently.
          </p>
        </div>
      )
    },
    'quick-start': {
      title: 'Quick Start Guide',
      content: (
        <div className="space-y-6">
          <p className="text-slate-300 leading-relaxed">
            Get your surveillance system up and running in minutes with our streamlined setup process.
          </p>
          
          <h3 className="text-xl font-semibold text-white">Prerequisites</h3>
          <ul className="space-y-2 text-slate-300">
            <li className="flex items-start space-x-2">
              <span className="text-green-400 mt-1">✓</span>
              <span>Docker and Docker Compose installed</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-green-400 mt-1">✓</span>
              <span>Python 3.11+ for development</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-green-400 mt-1">✓</span>
              <span>8GB+ RAM recommended</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-green-400 mt-1">✓</span>
              <span>50GB+ storage for video data</span>
            </li>
          </ul>

          <h3 className="text-xl font-semibold text-white">Step 1: Clone Repository</h3>
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <code className="text-green-400">
              git clone https://github.com/your-org/surveillance-system.git<br/>
              cd surveillance-system
            </code>
          </div>

          <h3 className="text-xl font-semibold text-white">Step 2: Start Services</h3>
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <code className="text-green-400">
              # For Windows<br/>
              .\start-surveillance-windows.ps1<br/><br/>
              # For Linux/Mac<br/>
              ./start-surveillance.sh
            </code>
          </div>

          <h3 className="text-xl font-semibold text-white">Step 3: Access Dashboard</h3>
          <p className="text-slate-300">
            Once all services are running, access your dashboard at:          </p>
          <ul className="space-y-2 text-slate-300">
            <li>• Grafana: <a href={serviceUrls.grafana} className="text-blue-400 hover:text-blue-300" target="_blank" rel="noopener noreferrer">{serviceUrls.grafana}</a></li>
            <li>• Prometheus: <a href={serviceUrls.prometheus} className="text-blue-400 hover:text-blue-300" target="_blank" rel="noopener noreferrer">{serviceUrls.prometheus}</a></li>
            <li>• API Gateway: <a href={serviceUrls.apiGateway} className="text-blue-400 hover:text-blue-300" target="_blank" rel="noopener noreferrer">{serviceUrls.apiGateway}</a></li>
          </ul>
        </div>
      )
    },
    installation: {
      title: 'Installation Guide',
      content: (
        <div className="space-y-6">
          <h3 className="text-xl font-semibold text-white">System Requirements</h3>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-semibold text-white mb-2">Minimum Requirements</h4>
                <ul className="text-slate-300 text-sm space-y-1">
                  <li>• CPU: 4 cores</li>
                  <li>• RAM: 8GB</li>
                  <li>• Storage: 100GB</li>
                  <li>• Network: 1Gbps</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold text-white mb-2">Recommended</h4>
                <ul className="text-slate-300 text-sm space-y-1">
                  <li>• CPU: 16+ cores</li>
                  <li>• RAM: 32GB+</li>
                  <li>• Storage: 1TB+ SSD</li>
                  <li>• Network: 10Gbps</li>
                </ul>
              </div>
            </div>
          </div>

          <h3 className="text-xl font-semibold text-white">Docker Installation</h3>
          <p className="text-slate-300">The recommended deployment method uses Docker containers:</p>
          
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <code className="text-green-400 text-sm">
              # Build all services<br/>
              docker-compose build<br/><br/>
              # Start the surveillance system<br/>
              docker-compose up -d<br/><br/>
              # Check service status<br/>
              docker-compose ps
            </code>
          </div>

          <h3 className="text-xl font-semibold text-white">Manual Installation</h3>
          <p className="text-slate-300">For development or custom deployments:</p>
          
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <code className="text-green-400 text-sm">
              # Install Python dependencies<br/>
              pip install -r requirements.txt<br/><br/>
              # Set up databases<br/>
              python scripts/setup-db.py<br/><br/>
              # Start individual services<br/>
              python edge_service/main.py &<br/>
              python ingest_service/main.py &<br/>
              # ... continue for all services
            </code>
          </div>
        </div>
      )
    },
    configuration: {
      title: 'Configuration',
      content: (
        <div className="space-y-6">
          <h3 className="text-xl font-semibold text-white">Environment Variables</h3>
          <p className="text-slate-300">
            Configure your system using environment variables in your <code className="bg-slate-700 px-2 py-1 rounded">.env</code> file:
          </p>
          
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <code className="text-green-400 text-sm">
              # Database Configuration<br/>
              POSTGRES_HOST=localhost<br/>
              POSTGRES_PORT=5432<br/>
              POSTGRES_DB=surveillance<br/>
              POSTGRES_USER=admin<br/>
              POSTGRES_PASSWORD=your_password<br/><br/>
              
              # AI Model Configuration<br/>
              AI_MODEL_PATH=./models/detection_model.pt<br/>
              AI_CONFIDENCE_THRESHOLD=0.8<br/>
              AI_BATCH_SIZE=32<br/><br/>
              
              # Notification Settings<br/>
              SMTP_HOST=smtp.gmail.com<br/>
              SMTP_PORT=587<br/>
              EMAIL_USER=alerts@yourcompany.com<br/>
              EMAIL_PASSWORD=your_app_password
            </code>
          </div>

          <h3 className="text-xl font-semibold text-white">Camera Configuration</h3>
          <p className="text-slate-300">
            Add your cameras in the <code className="bg-slate-700 px-2 py-1 rounded">cameras.yaml</code> configuration file:
          </p>
          
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <code className="text-green-400 text-sm">
              cameras:<br/>
              &nbsp;&nbsp;- id: "cam_001"<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;name: "Main Entrance"<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;url: "rtsp://192.168.1.100:554/stream"<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;location: "Building A - Entrance"<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;enabled: true<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;recording: true<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;ai_enabled: true
            </code>
          </div>

          <h3 className="text-xl font-semibold text-white">Alert Rules</h3>
          <p className="text-slate-300">
            Configure alert conditions in <code className="bg-slate-700 px-2 py-1 rounded">alert_rules.yaml</code>:
          </p>
          
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <code className="text-green-400 text-sm">
              rules:<br/>
              &nbsp;&nbsp;- name: "unauthorized_access"<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;condition: "person_detected AND access_denied"<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;severity: "high"<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;actions: ["email", "sms", "dashboard"]<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;cooldown: 300  # seconds
            </code>
          </div>
        </div>
      )
    },
    api: {
      title: 'API Reference',
      content: (
        <div className="space-y-6">
          <h3 className="text-xl font-semibold text-white">REST API Endpoints</h3>
          <p className="text-slate-300">
            The surveillance system provides a comprehensive REST API for integration and automation.
          </p>

          <h4 className="text-lg font-semibold text-white">Authentication</h4>
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <code className="text-green-400 text-sm">
              POST /api/v1/auth/login<br/>
              Content-Type: application/json<br/><br/>
              &#123;<br/>
              &nbsp;&nbsp;"username": "admin",<br/>
              &nbsp;&nbsp;"password": "your_password"<br/>
              &#125;
            </code>
          </div>

          <h4 className="text-lg font-semibold text-white">Camera Management</h4>
          <div className="space-y-4">
            <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
              <p className="text-white font-medium mb-2">Get All Cameras</p>
              <code className="text-green-400 text-sm">
                GET /api/v1/cameras<br/>
                Authorization: Bearer &#123;token&#125;
              </code>
            </div>
            
            <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
              <p className="text-white font-medium mb-2">Get Camera Feed</p>
              <code className="text-green-400 text-sm">
                GET /api/v1/cameras/&#123;camera_id&#125;/stream<br/>
                Authorization: Bearer &#123;token&#125;
              </code>
            </div>
          </div>

          <h4 className="text-lg font-semibold text-white">Alerts API</h4>
          <div className="space-y-4">
            <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
              <p className="text-white font-medium mb-2">Get Alerts</p>
              <code className="text-green-400 text-sm">
                GET /api/v1/alerts?severity=high&status=active<br/>
                Authorization: Bearer &#123;token&#125;
              </code>
            </div>
            
            <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
              <p className="text-white font-medium mb-2">Acknowledge Alert</p>
              <code className="text-green-400 text-sm">
                PUT /api/v1/alerts/&#123;alert_id&#125;/acknowledge<br/>
                Authorization: Bearer &#123;token&#125;<br/>
                Content-Type: application/json<br/><br/>
                &#123;<br/>
                &nbsp;&nbsp;"acknowledged_by": "operator_id",<br/>
                &nbsp;&nbsp;"notes": "Investigating incident"<br/>
                &#125;
              </code>
            </div>
          </div>

          <h4 className="text-lg font-semibold text-white">WebSocket Events</h4>          <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
            <code className="text-green-400 text-sm">
              // Connect to real-time events<br/>
              const ws = new WebSocket('{serviceUrls.websocket}');<br/><br/>
              
              ws.onmessage = function(event) &#123;<br/>
              &nbsp;&nbsp;const data = JSON.parse(event.data);<br/>
              &nbsp;&nbsp;console.log('New alert:', data);<br/>
              &#125;;
            </code>
          </div>
        </div>
      )
    },
    troubleshooting: {
      title: 'Troubleshooting',
      content: (
        <div className="space-y-6">
          <h3 className="text-xl font-semibold text-white">Common Issues</h3>
          
          <div className="space-y-6">
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <h4 className="font-semibold text-white mb-2">Services Won't Start</h4>
              <p className="text-slate-300 mb-3">
                If services fail to start, check the following:
              </p>
              <ul className="space-y-2 text-slate-300 text-sm">
                <li>• Ensure Docker is running and accessible</li>
                <li>• Check port availability (8000-8010, 3000, 9090)</li>
                <li>• Verify environment variables are set correctly</li>
                <li>• Check disk space and memory availability</li>
              </ul>
              <div className="mt-3 bg-slate-900 rounded p-3 border border-slate-600">
                <code className="text-green-400 text-sm">
                  # Check service logs<br/>
                  docker-compose logs service_name
                </code>
              </div>
            </div>

            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <h4 className="font-semibold text-white mb-2">AI Detection Not Working</h4>
              <p className="text-slate-300 mb-3">
                If AI detection is not functioning properly:
              </p>
              <ul className="space-y-2 text-slate-300 text-sm">
                <li>• Verify AI models are downloaded and accessible</li>
                <li>• Check GPU/CPU resources availability</li>
                <li>• Ensure camera feeds are accessible</li>
                <li>• Review confidence thresholds in settings</li>
              </ul>              <div className="mt-3 bg-slate-900 rounded p-3 border border-slate-600">
                <code className="text-green-400 text-sm">
                  # Test AI service directly<br/>
                  curl {serviceUrls.api}/health
                </code>
              </div>
            </div>

            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <h4 className="font-semibold text-white mb-2">Database Connection Issues</h4>
              <p className="text-slate-300 mb-3">
                For database connectivity problems:
              </p>
              <ul className="space-y-2 text-slate-300 text-sm">
                <li>• Verify database container is running</li>
                <li>• Check connection parameters in .env file</li>
                <li>• Ensure database is initialized properly</li>
                <li>• Test connectivity from application containers</li>
              </ul>
              <div className="mt-3 bg-slate-900 rounded p-3 border border-slate-600">
                <code className="text-green-400 text-sm">
                  # Test database connection<br/>
                  docker exec -it postgres_container psql -U admin -d surveillance
                </code>
              </div>
            </div>
          </div>

          <h3 className="text-xl font-semibold text-white">Getting Help</h3>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <p className="text-slate-300 mb-3">
              Need additional support? Here are your options:
            </p>
            <ul className="space-y-2 text-slate-300">
              <li>• 📧 Email: <a href="mailto:support@surveillanceai.com" className="text-blue-400 hover:text-blue-300">support@surveillanceai.com</a></li>
              <li>• 💬 Discord: <a href="#" className="text-blue-400 hover:text-blue-300">SurveillanceAI Community</a></li>
              <li>• 📚 GitHub Issues: <a href="#" className="text-blue-400 hover:text-blue-300">Report a Bug</a></li>
              <li>• 📞 Enterprise Support: Available 24/7 for enterprise customers</li>
            </ul>
          </div>
        </div>
      )
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 pt-20">
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold text-white mb-2">Documentation</h1>
          <p className="text-slate-400">Complete guide to setting up and using SurveillanceAI</p>
        </motion.div>

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:w-64"
          >
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-2 sticky top-24">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center space-x-3 px-4 py-3 text-left rounded-lg transition-colors ${
                    activeSection === section.id
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                  }`}
                >
                  <span className="text-lg">{section.icon}</span>
                  <span className="font-medium">{section.title}</span>
                </button>
              ))}
            </div>
          </motion.div>

          {/* Content */}
          <motion.div
            key={activeSection}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="flex-1"
          >
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-8">
              <h2 className="text-2xl font-bold text-white mb-6">
                {documentation[activeSection]?.title}
              </h2>
              {documentation[activeSection]?.content}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
