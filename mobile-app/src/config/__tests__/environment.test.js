import EnvironmentConfig from '../environment';
import configValidator from '../configValidator';

// Mock environment variables
jest.mock('react-native-config', () => ({
  API_BASE_URL: 'http://localhost:8000',
  WEBSOCKET_URL: 'ws://localhost:8000/ws',
  ENVIRONMENT: 'development',
  DEBUG: 'true',
  TIMEOUT: '10000'
}));

describe('EnvironmentConfig', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Environment Detection', () => {
    it('should detect development environment', () => {
      const env = EnvironmentConfig.getEnvironment();
      expect(env).toBe('development');
    });

    it('should identify development mode correctly', () => {
      expect(EnvironmentConfig.isDevelopment()).toBe(true);
      expect(EnvironmentConfig.isProduction()).toBe(false);
    });
  });

  describe('Configuration Loading', () => {
    it('should load all configuration correctly', () => {
      const config = EnvironmentConfig.getAllConfig();
      
      expect(config.API_BASE_URL).toBe('http://localhost:8000');
      expect(config.WEBSOCKET_URL).toBe('ws://localhost:8000/ws');
      expect(config.DEBUG).toBe(true);
      expect(config.TIMEOUT).toBe(10000);
    });

    it('should build service URLs correctly', () => {
      const config = EnvironmentConfig.getAllConfig();
      
      expect(config.AUTH_URL).toBe('http://localhost:8001');
      expect(config.CAMERA_URL).toBe('http://localhost:8008');
      expect(config.ALERTS_URL).toBe('http://localhost:8007');
      expect(config.DASHBOARD_URL).toBe('http://localhost:8003');
    });

    it('should handle missing environment variables gracefully', () => {
      // Test with undefined environment variable
      const originalEnv = process.env.NODE_ENV;
      delete process.env.NODE_ENV;
      
      const config = EnvironmentConfig.getAllConfig();
      expect(config).toBeDefined();
      
      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('URL Building', () => {
    it('should build API URLs correctly', () => {
      const url = EnvironmentConfig.buildApiUrl('/test');
      expect(url).toBe('http://localhost:8000/test');
    });

    it('should build WebSocket URLs correctly', () => {
      const url = EnvironmentConfig.buildWebSocketUrl('/live');
      expect(url).toBe('ws://localhost:8000/ws/live');
    });

    it('should handle URL path formatting', () => {
      const url1 = EnvironmentConfig.buildApiUrl('test'); // without leading slash
      const url2 = EnvironmentConfig.buildApiUrl('/test'); // with leading slash
      
      expect(url1).toBe('http://localhost:8000/test');
      expect(url2).toBe('http://localhost:8000/test');
    });
  });

  describe('Type Conversion', () => {
    it('should convert string boolean to boolean', () => {
      const config = EnvironmentConfig.getAllConfig();
      expect(typeof config.DEBUG).toBe('boolean');
      expect(config.DEBUG).toBe(true);
    });

    it('should convert string number to number', () => {
      const config = EnvironmentConfig.getAllConfig();
      expect(typeof config.TIMEOUT).toBe('number');
      expect(config.TIMEOUT).toBe(10000);
    });
  });
});

describe('ConfigValidator', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Environment Validation', () => {
    it('should validate environment configuration successfully', async () => {
      const result = await configValidator.validateEnvironment();
      expect(configValidator.validationResults.environment).toBeDefined();
    });

    it('should detect invalid URLs', async () => {
      // Mock invalid URL
      jest.spyOn(EnvironmentConfig, 'getAllConfig').mockReturnValue({
        API_BASE_URL: 'invalid-url',
        WEBSOCKET_URL: 'ws://localhost:8000/ws',
        PORTS: { AUTH: 8001, CAMERA: 8008 }
      });

      await configValidator.validateEnvironment();
      const result = configValidator.validationResults.environment;
      
      expect(result.errors).toContain('API_BASE_URL is not a valid URL');
    });
  });

  describe('Service Validation', () => {
    it('should validate service configuration', async () => {
      await configValidator.validateServices();
      const result = configValidator.validationResults.services;
      
      expect(result).toBeDefined();
      expect(Array.isArray(result.errors)).toBe(true);
      expect(Array.isArray(result.warnings)).toBe(true);
    });
  });

  describe('API Configuration Validation', () => {
    it('should validate API configuration', async () => {
      await configValidator.validateApiConfig();
      const result = configValidator.validationResults.apiConfig;
      
      expect(result).toBeDefined();
    });
  });

  describe('Dependencies Validation', () => {
    it('should validate required dependencies', async () => {
      await configValidator.validateDependencies();
      const result = configValidator.validationResults.dependencies;
      
      expect(result).toBeDefined();
      expect(result.errors.length).toBe(0); // Should pass in test environment
    });
  });

  describe('Complete Validation', () => {
    it('should run complete validation suite', async () => {
      const isValid = await configValidator.validateAll();
      
      expect(typeof isValid).toBe('boolean');
      expect(configValidator.validationResults.environment).toBeDefined();
      expect(configValidator.validationResults.apiConfig).toBeDefined();
      expect(configValidator.validationResults.services).toBeDefined();
      expect(configValidator.validationResults.dependencies).toBeDefined();
    });
  });
});
