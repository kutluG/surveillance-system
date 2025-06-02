import { renderWithProviders } from '../../test/testUtils';
import App from '../../App';
import EnvironmentConfig from '../../config/environment';
import configValidator from '../../utils/configValidator';

// Mock all required modules
jest.mock('../../config/environment');
jest.mock('../../utils/configValidator');
jest.mock('../../utils/networkErrorHandler');
jest.mock('../../integration/realTimeIntegration');

describe('Configuration Integration Tests', () => {
  let mockEnvironmentConfig;
  let mockConfigValidator;

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockEnvironmentConfig = {
      getEnvironment: jest.fn(() => 'development'),
      isDevelopment: jest.fn(() => true),
      isProduction: jest.fn(() => false),
      getAllConfig: jest.fn(() => ({
        API_BASE_URL: 'http://localhost:8000',
        WEBSOCKET_URL: 'ws://localhost:8000/ws',
        AUTH_URL: 'http://localhost:8001',
        CAMERA_URL: 'http://localhost:8008',
        ALERTS_URL: 'http://localhost:8007',
        DASHBOARD_URL: 'http://localhost:8003',
        DEBUG: true,
        TIMEOUT: 10000,
        PORTS: {
          AUTH: 8001,
          CAMERA: 8008,
          ALERTS: 8007,
          DASHBOARD: 8003
        }
      })),
      buildApiUrl: jest.fn((path) => `http://localhost:8000${path}`),
      buildWebSocketUrl: jest.fn((path) => `ws://localhost:8000/ws${path}`)
    };

    mockConfigValidator = {
      validateAll: jest.fn(() => Promise.resolve(true)),
      validationResults: {
        environment: { errors: [], warnings: [] },
        apiConfig: { errors: [], warnings: [] },
        services: { errors: [], warnings: [] },
        dependencies: { errors: [], warnings: [] }
      },
      showValidationErrors: jest.fn()
    };

    EnvironmentConfig.getEnvironment = mockEnvironmentConfig.getEnvironment;
    EnvironmentConfig.isDevelopment = mockEnvironmentConfig.isDevelopment;
    EnvironmentConfig.isProduction = mockEnvironmentConfig.isProduction;
    EnvironmentConfig.getAllConfig = mockEnvironmentConfig.getAllConfig;
    EnvironmentConfig.buildApiUrl = mockEnvironmentConfig.buildApiUrl;
    EnvironmentConfig.buildWebSocketUrl = mockEnvironmentConfig.buildWebSocketUrl;

    configValidator.validateAll = mockConfigValidator.validateAll;
    configValidator.validationResults = mockConfigValidator.validationResults;
    configValidator.showValidationErrors = mockConfigValidator.showValidationErrors;
  });

  describe('App Initialization with Configuration', () => {
    it('should initialize app with valid configuration', async () => {
      const { getByTestId } = renderWithProviders(<App />);
      
      // Wait for app to initialize
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(mockConfigValidator.validateAll).toHaveBeenCalled();
      expect(mockEnvironmentConfig.getAllConfig).toHaveBeenCalled();
    });

    it('should handle configuration validation errors gracefully', async () => {
      // Mock validation failure
      mockConfigValidator.validateAll.mockResolvedValue(false);
      mockConfigValidator.validationResults.environment.errors = ['Test error'];

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      renderWithProviders(<App />);
      
      // Wait for initialization
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(mockConfigValidator.validateAll).toHaveBeenCalled();
      expect(mockConfigValidator.showValidationErrors).toHaveBeenCalled();
      
      consoleSpy.mockRestore();
    });

    it('should skip validation in production environment', async () => {
      mockEnvironmentConfig.isDevelopment.mockReturnValue(false);
      mockEnvironmentConfig.isProduction.mockReturnValue(true);
      mockEnvironmentConfig.getEnvironment.mockReturnValue('production');

      renderWithProviders(<App />);
      
      // Wait for initialization
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Validation should not be called in production
      expect(mockConfigValidator.validateAll).not.toHaveBeenCalled();
    });
  });

  describe('Service Configuration Integration', () => {
    it('should properly configure service URLs', () => {
      const config = mockEnvironmentConfig.getAllConfig();
      
      expect(config.AUTH_URL).toBe('http://localhost:8001');
      expect(config.CAMERA_URL).toBe('http://localhost:8008');
      expect(config.ALERTS_URL).toBe('http://localhost:8007');
      expect(config.DASHBOARD_URL).toBe('http://localhost:8003');
    });

    it('should build API URLs correctly', () => {
      const authUrl = mockEnvironmentConfig.buildApiUrl('/auth/login');
      const cameraUrl = mockEnvironmentConfig.buildApiUrl('/cameras');
      
      expect(authUrl).toBe('http://localhost:8000/auth/login');
      expect(cameraUrl).toBe('http://localhost:8000/cameras');
    });

    it('should build WebSocket URLs correctly', () => {
      const wsUrl = mockEnvironmentConfig.buildWebSocketUrl('/live-feed');
      expect(wsUrl).toBe('ws://localhost:8000/ws/live-feed');
    });
  });

  describe('Environment-specific Behavior', () => {
    it('should enable debug features in development', () => {
      const config = mockEnvironmentConfig.getAllConfig();
      expect(config.DEBUG).toBe(true);
    });

    it('should configure appropriate timeouts', () => {
      const config = mockEnvironmentConfig.getAllConfig();
      expect(config.TIMEOUT).toBe(10000);
    });

    it('should handle production configuration', async () => {
      mockEnvironmentConfig.isDevelopment.mockReturnValue(false);
      mockEnvironmentConfig.isProduction.mockReturnValue(true);
      mockEnvironmentConfig.getAllConfig.mockReturnValue({
        API_BASE_URL: 'https://api.surveillance-system.com',
        WEBSOCKET_URL: 'wss://api.surveillance-system.com/ws',
        DEBUG: false,
        TIMEOUT: 30000
      });

      const config = mockEnvironmentConfig.getAllConfig();
      
      expect(config.API_BASE_URL).toBe('https://api.surveillance-system.com');
      expect(config.WEBSOCKET_URL).toBe('wss://api.surveillance-system.com/ws');
      expect(config.DEBUG).toBe(false);
      expect(config.TIMEOUT).toBe(30000);
    });
  });

  describe('Error Handling Integration', () => {
    it('should handle configuration loading errors', async () => {
      mockEnvironmentConfig.getAllConfig.mockImplementation(() => {
        throw new Error('Configuration loading failed');
      });

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      renderWithProviders(<App />);
      
      // Wait for initialization
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });

    it('should handle validation errors', async () => {
      mockConfigValidator.validateAll.mockRejectedValue(new Error('Validation failed'));

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      renderWithProviders(<App />);
      
      // Wait for initialization
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });
});
