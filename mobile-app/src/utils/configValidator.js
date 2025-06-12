/**
 * Configuration Validator
 * Validates app configuration and environment setup
 */
import EnvironmentConfig from '../config/environment';
import { Alert } from 'react-native';

class ConfigValidator {
  constructor() {
    this.validationResults = {
      environment: null,
      apiConfig: null,
      services: null,
      dependencies: null,
    };
  }

  /**
   * Validate entire configuration
   */
  async validateAll() {
    console.log('🔍 Validating application configuration...');
    
    try {
      await this.validateEnvironment();
      await this.validateApiConfig();
      await this.validateServices();
      await this.validateDependencies();
      
      const hasErrors = Object.values(this.validationResults).some(result => 
        result && result.errors && result.errors.length > 0
      );

      if (hasErrors) {
        this.showValidationErrors();
      } else {
        console.log('✅ Configuration validation passed');
      }

      return !hasErrors;
    } catch (error) {
      console.error('❌ Configuration validation failed:', error);
      return false;
    }
  }

  /**
   * Validate environment configuration
   */
  async validateEnvironment() {
    const errors = [];
    const warnings = [];

    try {
      const env = EnvironmentConfig.getEnvironment();
      const config = EnvironmentConfig.getAllConfig();

      // Check required configuration
      if (!config.API_BASE_URL) {
        errors.push('API_BASE_URL is not configured');
      }

      if (!config.WEBSOCKET_URL) {
        errors.push('WEBSOCKET_URL is not configured');
      }

      // Validate URLs format
      if (config.API_BASE_URL && !this.isValidUrl(config.API_BASE_URL)) {
        errors.push('API_BASE_URL is not a valid URL');
      }

      if (config.WEBSOCKET_URL && !this.isValidWebSocketUrl(config.WEBSOCKET_URL)) {
        errors.push('WEBSOCKET_URL is not a valid WebSocket URL');
      }

      // Check service ports
      const ports = config.PORTS;
      if (!ports || typeof ports !== 'object') {
        errors.push('Service ports are not properly configured');
      } else {
        const requiredServices = ['AUTH', 'CAMERA', 'ALERTS', 'DASHBOARD'];
        requiredServices.forEach(service => {
          if (!ports[service] || !Number.isInteger(ports[service])) {
            errors.push(`${service} service port is not configured or invalid`);
          }
        });
      }

      // Environment-specific validations
      if (env === 'production') {
        if (config.API_BASE_URL.includes('localhost')) {
          warnings.push('Using localhost URL in production environment');
        }
        if (config.DEBUG) {
          warnings.push('Debug mode is enabled in production');
        }
      }

      this.validationResults.environment = { errors, warnings };
      
      if (errors.length > 0) {
        console.error('❌ Environment validation errors:', errors);
      }
      if (warnings.length > 0) {
        console.warn('⚠️  Environment validation warnings:', warnings);
      }

    } catch (error) {
      this.validationResults.environment = { 
        errors: [`Environment validation failed: ${error.message}`], 
        warnings: [] 
      };
    }
  }

  /**
   * Validate API configuration
   */
  async validateApiConfig() {
    const errors = [];
    const warnings = [];

    try {
      const config = EnvironmentConfig.getAllConfig();
      
      // Test API connectivity
      const isReachable = await this.testApiConnectivity(config.AUTH_URL);
      if (!isReachable) {
        warnings.push('Auth service is not reachable');
      }

      // Validate timeout settings
      if (!config.TIMEOUT || config.TIMEOUT < 1000) {
        warnings.push('Request timeout is too low (< 1000ms)');
      }

      this.validationResults.apiConfig = { errors, warnings };

    } catch (error) {
      this.validationResults.apiConfig = { 
        errors: [`API configuration validation failed: ${error.message}`], 
        warnings: [] 
      };
    }
  }

  /**
   * Validate required services
   */
  async validateServices() {
    const errors = [];
    const warnings = [];

    try {
      const config = EnvironmentConfig.getAllConfig();
      const services = [
        { name: 'Auth', url: config.AUTH_URL },
        { name: 'Camera', url: config.CAMERA_URL },
        { name: 'Alerts', url: config.ALERTS_URL },
        { name: 'Dashboard', url: config.DASHBOARD_URL },
      ];

      // Test service connectivity (in development mode only)
      if (EnvironmentConfig.isDevelopment()) {
        for (const service of services) {
          try {
            const isAvailable = await this.testServiceHealth(service.url);
            if (!isAvailable) {
              warnings.push(`${service.name} service is not available at ${service.url}`);
            }
          } catch (error) {
            warnings.push(`Could not test ${service.name} service connectivity`);
          }
        }
      }

      this.validationResults.services = { errors, warnings };

    } catch (error) {
      this.validationResults.services = { 
        errors: [`Service validation failed: ${error.message}`], 
        warnings: [] 
      };
    }
  }

  /**
   * Validate required dependencies
   */
  async validateDependencies() {
    const errors = [];
    const warnings = [];    try {
      // Check SecureStorage
      const secureStorage = require('./secureStorage').default;
      try {
        await secureStorage.setItem('test_key', 'test_value');
        await secureStorage.removeItem('test_key');
      } catch (error) {
        errors.push('SecureStorage is not working properly');
      }

      // Check network capabilities
      if (typeof fetch === 'undefined') {
        errors.push('Fetch API is not available');
      }

      this.validationResults.dependencies = { errors, warnings };

    } catch (error) {
      this.validationResults.dependencies = { 
        errors: [`Dependency validation failed: ${error.message}`], 
        warnings: [] 
      };
    }
  }

  /**
   * Test API connectivity
   */
  async testApiConnectivity(url) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${url}/health`, {
        method: 'GET',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  /**
   * Test service health
   */
  async testServiceHealth(url) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);

      const response = await fetch(`${url}/health`, {
        method: 'HEAD',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  /**
   * Validate URL format
   */
  isValidUrl(string) {
    try {
      new URL(string);
      return true;
    } catch (_) {
      return false;
    }
  }

  /**
   * Validate WebSocket URL format
   */
  isValidWebSocketUrl(string) {
    return string.startsWith('ws://') || string.startsWith('wss://');
  }

  /**
   * Show validation errors to user
   */
  showValidationErrors() {
    const allErrors = [];
    const allWarnings = [];

    Object.values(this.validationResults).forEach(result => {
      if (result && result.errors) {
        allErrors.push(...result.errors);
      }
      if (result && result.warnings) {
        allWarnings.push(...result.warnings);
      }
    });

    if (allErrors.length > 0) {
      Alert.alert(
        'Configuration Errors',
        `The following configuration errors were found:\n\n${allErrors.join('\n')}`,
        [{ text: 'OK' }]
      );
    }

    if (allWarnings.length > 0 && EnvironmentConfig.isDevelopment()) {
      console.warn('⚠️  Configuration warnings:', allWarnings);
    }
  }

  /**
   * Get validation results
   */
  getValidationResults() {
    return this.validationResults;
  }
}

export default new ConfigValidator();
