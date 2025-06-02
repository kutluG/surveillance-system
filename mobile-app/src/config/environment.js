import Config from 'react-native-config';

/**
 * Environment Configuration Manager
 * Handles different environment configurations (development, staging, production)
 */
class EnvironmentConfig {
  constructor() {
    this.environment = Config.ENV || 'development';
    this.initializeConfig();
  }

  initializeConfig() {
    // Base configuration that can be overridden by environment
    this.config = {
      API_BASE_URL: Config.API_BASE_URL || 'http://localhost',
      WEBSOCKET_URL: Config.WEBSOCKET_URL || 'ws://localhost:8002',
      TIMEOUT: parseInt(Config.TIMEOUT || '10000'),
      DEBUG: Config.DEBUG === 'true',
      LOG_LEVEL: Config.LOG_LEVEL || 'info',
      
      // Service ports
      PORTS: {
        AUTH: parseInt(Config.PORT_AUTH || '8001'),
        CAMERA: parseInt(Config.PORT_CAMERA || '8008'),
        ALERTS: parseInt(Config.PORT_ALERTS || '8007'),
        DASHBOARD: parseInt(Config.PORT_DASHBOARD || '8003'),
        VMS: parseInt(Config.PORT_VMS || '8008'),
        RAG: parseInt(Config.PORT_RAG || '8004'),
        PROMPT: parseInt(Config.PORT_PROMPT || '8005'),
        RULEGEN: parseInt(Config.PORT_RULEGEN || '8006'),
        NOTIFIER: parseInt(Config.PORT_NOTIFIER || '8007'),
      },
    };

    // Build full URLs
    this.config.AUTH_URL = this.buildServiceUrl('AUTH');
    this.config.CAMERA_URL = this.buildServiceUrl('CAMERA');
    this.config.ALERTS_URL = this.buildServiceUrl('ALERTS');
    this.config.DASHBOARD_URL = this.buildServiceUrl('DASHBOARD');
    this.config.VMS_URL = this.buildServiceUrl('VMS');
    this.config.RAG_URL = this.buildServiceUrl('RAG');
    this.config.PROMPT_URL = this.buildServiceUrl('PROMPT');
    this.config.RULEGEN_URL = this.buildServiceUrl('RULEGEN');
    this.config.NOTIFIER_URL = this.buildServiceUrl('NOTIFIER');
  }

  buildServiceUrl(serviceName) {
    const port = this.config.PORTS[serviceName];
    if (this.environment === 'production') {
      // In production, all services are behind a load balancer
      return this.config.API_BASE_URL;
    }
    return `${this.config.API_BASE_URL}:${port}`;
  }

  get(key) {
    return this.config[key];
  }

  getEnvironment() {
    return this.environment;
  }

  isDevelopment() {
    return this.environment === 'development';
  }

  isProduction() {
    return this.environment === 'production';
  }

  isDebugEnabled() {
    return this.config.DEBUG;
  }

  getLogLevel() {
    return this.config.LOG_LEVEL;
  }

  // Get all configuration for debugging
  getAllConfig() {
    return { ...this.config };
  }
}

// Export singleton instance
export default new EnvironmentConfig();
