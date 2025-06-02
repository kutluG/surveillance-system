# 🔧 Configuration Management System

## Overview

The surveillance mobile app uses a comprehensive configuration management system that handles environment-specific settings, service URLs, and runtime validation. This system ensures proper setup across development, testing, and production environments.

## Architecture

### Components

1. **Environment Manager** (`src/config/environment.js`)
   - Loads environment-specific configuration
   - Builds service URLs dynamically
   - Handles type conversion and validation

2. **Configuration Validator** (`src/utils/configValidator.js`)
   - Validates environment setup
   - Tests service connectivity
   - Checks dependency availability

3. **Build Validator** (`scripts/validate-build.js`)
   - Pre-build configuration validation
   - Security scanning
   - Asset verification

## Environment Configuration

### Development Environment (`.env.development`)

```env
# API Configuration
API_BASE_URL=http://localhost:8000
WEBSOCKET_URL=ws://localhost:8000/ws

# Service Ports (must match docker-compose.yml)
PORT_AUTH=8001
PORT_CAMERA=8008  
PORT_ALERTS=8007
PORT_DASHBOARD=8003
PORT_WEBSOCKET=8000

# Development Settings
DEBUG=true
TIMEOUT=10000
LOG_LEVEL=debug
ENABLE_FLIPPER=true

# Environment
ENVIRONMENT=development
```

### Production Environment (`.env.production`)

```env
# API Configuration
API_BASE_URL=https://api.surveillance-system.com
WEBSOCKET_URL=wss://api.surveillance-system.com/ws

# Service Ports
PORT_AUTH=443
PORT_CAMERA=443
PORT_ALERTS=443
PORT_DASHBOARD=443
PORT_WEBSOCKET=443

# Production Settings
DEBUG=false
TIMEOUT=30000
LOG_LEVEL=error
ENABLE_FLIPPER=false

# Environment
ENVIRONMENT=production
```

## Service URL Mapping

The configuration system automatically maps service URLs based on the backend infrastructure:

```javascript
// Automatic URL building
const config = EnvironmentConfig.getAllConfig();

// Service URLs are built as:
// AUTH_URL: http://localhost:8001 (development)
// CAMERA_URL: http://localhost:8008 (development)
// ALERTS_URL: http://localhost:8007 (development)
// DASHBOARD_URL: http://localhost:8003 (development)
```

## Usage in Services

### API Service Configuration

```javascript
import EnvironmentConfig from '../config/environment';

class ApiService {
  constructor() {
    const config = EnvironmentConfig.getAllConfig();
    this.baseURL = config.AUTH_URL;
    this.timeout = config.TIMEOUT;
  }

  async makeRequest(endpoint) {
    const url = EnvironmentConfig.buildApiUrl(endpoint);
    // Make API call...
  }
}
```

### WebSocket Service Configuration

```javascript
import EnvironmentConfig from '../config/environment';

class WebSocketService {
  connect() {
    const wsUrl = EnvironmentConfig.buildWebSocketUrl('/live');
    this.ws = new WebSocket(wsUrl);
  }
}
```

## Validation System

### Runtime Validation

The app performs comprehensive validation during startup:

```javascript
import configValidator from '../utils/configValidator';

// In App.js initialization
const initializeApp = async () => {
  if (EnvironmentConfig.isDevelopment()) {
    const isValid = await configValidator.validateAll();
    if (!isValid) {
      console.error('❌ Configuration validation failed');
    }
  }
};
```

### Validation Checks

1. **Environment Validation**
   - Required environment variables
   - URL format validation
   - Service port configuration

2. **API Configuration**
   - Service connectivity testing
   - Timeout settings validation
   - Authentication endpoint verification

3. **Service Validation**
   - Health check endpoints
   - Service availability testing
   - Port accessibility

4. **Dependency Validation**
   - AsyncStorage functionality
   - Network capabilities
   - Required packages

### Build-time Validation

Pre-build validation ensures configuration integrity:

```bash
# Run validation before building
node scripts/validate-build.js
```

Validates:
- Environment files existence
- Package.json dependencies
- Constants configuration
- Asset availability
- Security settings

## Error Handling

### Configuration Errors

The system handles configuration errors gracefully:

```javascript
try {
  const config = EnvironmentConfig.getAllConfig();
  // Use configuration...
} catch (error) {
  console.error('Configuration loading failed:', error);
  // Fallback to default configuration
}
```

### Validation Errors

Validation errors are displayed to developers in development mode:

```javascript
// Development mode - show detailed errors
if (EnvironmentConfig.isDevelopment()) {
  configValidator.showValidationErrors();
}

// Production mode - silent failure with logging
if (EnvironmentConfig.isProduction()) {
  console.error('Configuration validation failed');
}
```

## Testing Configuration

### Unit Tests

Test configuration loading and validation:

```javascript
// src/config/__tests__/environment.test.js
describe('EnvironmentConfig', () => {
  it('should load configuration correctly', () => {
    const config = EnvironmentConfig.getAllConfig();
    expect(config.API_BASE_URL).toBeDefined();
  });
});
```

### Integration Tests

Test configuration integration with app components:

```javascript
// src/integration/__tests__/configuration.test.js
describe('Configuration Integration', () => {
  it('should initialize app with valid configuration', async () => {
    // Test app initialization with configuration
  });
});
```

## Best Practices

### Environment Variables

1. **Naming Convention**: Use UPPER_CASE with underscores
2. **Required Variables**: Always define default values
3. **Sensitive Data**: Never commit secrets to version control
4. **Documentation**: Document all environment variables

### Service Configuration

1. **URL Building**: Use helper functions for consistent URL construction
2. **Port Mapping**: Keep ports consistent with backend infrastructure
3. **Timeouts**: Set appropriate timeouts for different environments
4. **Error Handling**: Always handle configuration errors gracefully

### Validation

1. **Development**: Run full validation during development
2. **Production**: Skip expensive validation checks in production
3. **Build Time**: Validate configuration before builds
4. **CI/CD**: Include validation in automated pipelines

## Troubleshooting

### Common Issues

1. **Service Unreachable**
   ```
   Error: Auth service is not reachable
   Solution: Check if backend services are running and ports match
   ```

2. **Invalid URL Format**
   ```
   Error: API_BASE_URL is not a valid URL
   Solution: Ensure URL includes protocol (http/https)
   ```

3. **Missing Environment Variables**
   ```
   Error: API_BASE_URL is not configured
   Solution: Create .env.development file with required variables
   ```

### Debug Steps

1. Check environment file exists and has correct variables
2. Verify backend services are running on expected ports
3. Test service connectivity manually
4. Review validation results in development mode
5. Check CI/CD pipeline validation logs

## Migration Guide

### From Previous Configuration

If upgrading from the previous configuration system:

1. **Create Environment Files**: Add `.env.development` and `.env.production`
2. **Update Service Calls**: Replace hardcoded URLs with EnvironmentConfig calls
3. **Add Validation**: Include configuration validation in app initialization
4. **Update Build Scripts**: Add pre-build validation step

### Example Migration

```javascript
// Before (hardcoded)
const authUrl = 'http://localhost:8001/auth/login';

// After (configuration-based)
const authUrl = `${EnvironmentConfig.getAllConfig().AUTH_URL}/auth/login`;
// or
const authUrl = EnvironmentConfig.buildApiUrl('/auth/login');
```
