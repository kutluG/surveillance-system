/**
 * Performance Optimized Configuration Manager
 * Implements caching and lazy loading for configuration
 */
import Config from 'react-native-config';

class PerformanceOptimizedConfig {
  constructor() {
    this._cache = new Map();
    this._loadPromise = null;
    this._isLoaded = false;
  }

  /**
   * Lazy load configuration with caching
   */
  async loadConfig() {
    if (this._isLoaded) {
      return this._cache.get('config');
    }

    if (this._loadPromise) {
      return this._loadPromise;
    }

    this._loadPromise = this._performConfigLoad();
    return this._loadPromise;
  }

  /**
   * Internal config loading with performance optimizations
   */
  async _performConfigLoad() {
    const startTime = performance.now();

    try {
      const config = {
        // Environment
        ENVIRONMENT: this._parseString(Config.ENVIRONMENT, 'development'),
        DEBUG: this._parseBoolean(Config.DEBUG, true),
        
        // API Configuration
        API_BASE_URL: this._parseString(Config.API_BASE_URL, 'http://localhost:8000'),
        WEBSOCKET_URL: this._parseString(Config.WEBSOCKET_URL, 'ws://localhost:8000/ws'),
        
        // Service Ports
        PORTS: {
          AUTH: this._parseNumber(Config.PORT_AUTH, 8001),
          CAMERA: this._parseNumber(Config.PORT_CAMERA, 8008),
          ALERTS: this._parseNumber(Config.PORT_ALERTS, 8007),
          DASHBOARD: this._parseNumber(Config.PORT_DASHBOARD, 8003),
          WEBSOCKET: this._parseNumber(Config.PORT_WEBSOCKET, 8000),
        },

        // Performance Settings
        TIMEOUT: this._parseNumber(Config.TIMEOUT, 10000),
        RETRY_ATTEMPTS: this._parseNumber(Config.RETRY_ATTEMPTS, 3),
        CACHE_TTL: this._parseNumber(Config.CACHE_TTL, 300000), // 5 minutes
        
        // Feature Flags
        ENABLE_BIOMETRICS: this._parseBoolean(Config.ENABLE_BIOMETRICS, true),
        ENABLE_PUSH_NOTIFICATIONS: this._parseBoolean(Config.ENABLE_PUSH_NOTIFICATIONS, true),
        ENABLE_ANALYTICS: this._parseBoolean(Config.ENABLE_ANALYTICS, false),
      };

      // Build derived URLs
      config.AUTH_URL = this._buildServiceUrl(config.API_BASE_URL, config.PORTS.AUTH);
      config.CAMERA_URL = this._buildServiceUrl(config.API_BASE_URL, config.PORTS.CAMERA);
      config.ALERTS_URL = this._buildServiceUrl(config.API_BASE_URL, config.PORTS.ALERTS);
      config.DASHBOARD_URL = this._buildServiceUrl(config.API_BASE_URL, config.PORTS.DASHBOARD);

      // Cache the configuration
      this._cache.set('config', config);
      this._cache.set('loadTime', Date.now());
      this._isLoaded = true;

      const loadTime = performance.now() - startTime;
      if (config.DEBUG) {
        console.log(`🔧 Configuration loaded in ${loadTime.toFixed(2)}ms`);
      }

      return config;
    } catch (error) {
      console.error('❌ Configuration loading failed:', error);
      throw error;
    } finally {
      this._loadPromise = null;
    }
  }

  /**
   * Get configuration with caching
   */
  async getConfig() {
    if (this._isConfigExpired()) {
      this._invalidateCache();
    }
    
    return this.loadConfig();
  }

  /**
   * Get specific configuration value with caching
   */
  async getConfigValue(key, defaultValue = null) {
    const config = await this.getConfig();
    return config[key] ?? defaultValue;
  }

  /**
   * Synchronous config access (returns cached value)
   */
  getCachedConfig() {
    if (!this._isLoaded) {
      console.warn('⚠️  Configuration not loaded yet, triggering async load');
      this.loadConfig(); // Trigger load for next time
      return this._getDefaultConfig();
    }
    
    return this._cache.get('config');
  }

  /**
   * Check if configuration cache is expired
   */
  _isConfigExpired() {
    const loadTime = this._cache.get('loadTime');
    if (!loadTime) return true;
    
    const config = this._cache.get('config');
    const ttl = config?.CACHE_TTL || 300000; // 5 minutes default
    
    return Date.now() - loadTime > ttl;
  }

  /**
   * Invalidate configuration cache
   */
  _invalidateCache() {
    this._cache.clear();
    this._isLoaded = false;
    this._loadPromise = null;
  }

  /**
   * Refresh configuration
   */
  async refreshConfig() {
    this._invalidateCache();
    return this.loadConfig();
  }

  /**
   * Build service URL with performance optimization
   */
  _buildServiceUrl(baseUrl, port) {
    // Cache URL building results
    const cacheKey = `url_${baseUrl}_${port}`;
    if (this._cache.has(cacheKey)) {
      return this._cache.get(cacheKey);
    }

    let url;
    if (baseUrl.includes('localhost')) {
      // Development environment - use specific ports
      url = baseUrl.replace(/:\d+/, `:${port}`);
    } else {
      // Production environment - use base URL (assuming load balancer/proxy)
      url = baseUrl;
    }

    this._cache.set(cacheKey, url);
    return url;
  }

  /**
   * Optimized type parsing functions
   */
  _parseString(value, defaultValue) {
    return value !== undefined && value !== null ? String(value) : defaultValue;
  }

  _parseBoolean(value, defaultValue) {
    if (value === undefined || value === null) return defaultValue;
    if (typeof value === 'boolean') return value;
    return value.toLowerCase() === 'true';
  }

  _parseNumber(value, defaultValue) {
    if (value === undefined || value === null) return defaultValue;
    const parsed = Number(value);
    return isNaN(parsed) ? defaultValue : parsed;
  }

  /**
   * Get default configuration for fallback
   */
  _getDefaultConfig() {
    return {
      ENVIRONMENT: 'development',
      DEBUG: true,
      API_BASE_URL: 'http://localhost:8000',
      WEBSOCKET_URL: 'ws://localhost:8000/ws',
      AUTH_URL: 'http://localhost:8001',
      CAMERA_URL: 'http://localhost:8008',
      ALERTS_URL: 'http://localhost:8007',
      DASHBOARD_URL: 'http://localhost:8003',
      TIMEOUT: 10000,
      RETRY_ATTEMPTS: 3,
      CACHE_TTL: 300000,
      PORTS: {
        AUTH: 8001,
        CAMERA: 8008,
        ALERTS: 8007,
        DASHBOARD: 8003,
        WEBSOCKET: 8000,
      },
      ENABLE_BIOMETRICS: true,
      ENABLE_PUSH_NOTIFICATIONS: true,
      ENABLE_ANALYTICS: false,
    };
  }

  /**
   * Get performance metrics
   */
  getPerformanceMetrics() {
    return {
      isLoaded: this._isLoaded,
      cacheSize: this._cache.size,
      loadTime: this._cache.get('loadTime'),
      isExpired: this._isConfigExpired(),
    };
  }

  /**
   * Utility methods for common operations
   */
  isDevelopment() {
    const config = this.getCachedConfig();
    return config.ENVIRONMENT === 'development';
  }

  isProduction() {
    const config = this.getCachedConfig();
    return config.ENVIRONMENT === 'production';
  }

  buildApiUrl(path) {
    const config = this.getCachedConfig();
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${config.API_BASE_URL}${cleanPath}`;
  }

  buildWebSocketUrl(path) {
    const config = this.getCachedConfig();
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${config.WEBSOCKET_URL}${cleanPath}`;
  }
}

// Create singleton instance
const performanceConfig = new PerformanceOptimizedConfig();

// Pre-load configuration for better startup performance
if (typeof global !== 'undefined') {
  // Load configuration asynchronously on startup
  performanceConfig.loadConfig().catch(error => {
    console.error('❌ Failed to pre-load configuration:', error);
  });
}

export default performanceConfig;
