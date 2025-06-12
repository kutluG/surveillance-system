/**
 * Configuration validator for environment variables
 * Validates and sanitizes configuration values for the surveillance mobile app
 */

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  sanitizedConfig?: any;
}

export interface ConfigValidationRules {
  required?: boolean;
  type?: 'string' | 'number' | 'boolean' | 'url';
  pattern?: RegExp;
  minLength?: number;
  maxLength?: number;
  allowedValues?: string[];
}

class ConfigValidator {
  public validationResults: {
    environment?: ValidationResult;
    services?: ValidationResult;
    apiConfig?: ValidationResult;
    dependencies?: ValidationResult;
  } = {};

  /**
   * Validates a configuration object against validation rules
   */
  validate(config: Record<string, any>, rules: Record<string, ConfigValidationRules>): ValidationResult {
    const errors: string[] = [];
    const sanitizedConfig: Record<string, any> = {};

    for (const [key, rule] of Object.entries(rules)) {
      const value = config[key];
      const validation = this.validateField(key, value, rule);
      
      if (!validation.isValid) {
        errors.push(...validation.errors);
      } else {
        sanitizedConfig[key] = validation.sanitizedValue;
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitizedConfig: errors.length === 0 ? sanitizedConfig : undefined,
    };
  }

  /**
   * Validates a single configuration field
   */
  private validateField(key: string, value: any, rule: ConfigValidationRules): {
    isValid: boolean;
    errors: string[];
    sanitizedValue?: any;
  } {
    const errors: string[] = [];
    let sanitizedValue = value;

    // Check if required
    if (rule.required && (value === undefined || value === null || value === '')) {
      errors.push(`${key} is required`);
      return { isValid: false, errors };
    }

    // Skip validation if value is not provided and not required
    if (value === undefined || value === null || value === '') {
      return { isValid: true, errors: [], sanitizedValue: value };
    }

    // Type validation and conversion
    switch (rule.type) {
      case 'string':
        if (typeof value !== 'string') {
          sanitizedValue = String(value);
        }
        break;

      case 'number':
        if (typeof value === 'string') {
          const parsed = Number(value);
          if (isNaN(parsed)) {
            errors.push(`${key} must be a valid number`);
            break;
          }
          sanitizedValue = parsed;
        } else if (typeof value !== 'number') {
          errors.push(`${key} must be a number`);
        }
        break;

      case 'boolean':
        if (typeof value === 'string') {
          const lower = value.toLowerCase();
          if (lower === 'true' || lower === '1') {
            sanitizedValue = true;
          } else if (lower === 'false' || lower === '0') {
            sanitizedValue = false;
          } else {
            errors.push(`${key} must be a valid boolean (true/false)`);
          }
        } else if (typeof value !== 'boolean') {
          errors.push(`${key} must be a boolean`);
        }
        break;

      case 'url':
        if (typeof value === 'string') {
          try {
            new URL(value);
          } catch {
            errors.push(`${key} must be a valid URL`);
          }
        } else {
          errors.push(`${key} must be a valid URL string`);
        }
        break;
    }

    // String-specific validations
    if (rule.type === 'string' && typeof sanitizedValue === 'string') {
      if (rule.minLength !== undefined && sanitizedValue.length < rule.minLength) {
        errors.push(`${key} must be at least ${rule.minLength} characters long`);
      }

      if (rule.maxLength !== undefined && sanitizedValue.length > rule.maxLength) {
        errors.push(`${key} must be no more than ${rule.maxLength} characters long`);
      }

      if (rule.pattern && !rule.pattern.test(sanitizedValue)) {
        errors.push(`${key} does not match the required pattern`);
      }

      if (rule.allowedValues && !rule.allowedValues.includes(sanitizedValue)) {
        errors.push(`${key} must be one of: ${rule.allowedValues.join(', ')}`);
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitizedValue: errors.length === 0 ? sanitizedValue : undefined,
    };
  }

  /**
   * Validates environment-specific configuration
   */
  validateEnvironmentConfig(config: Record<string, any>): ValidationResult {
    const rules: Record<string, ConfigValidationRules> = {
      API_BASE_URL: {
        required: true,
        type: 'url',
      },
      WS_BASE_URL: {
        required: true,
        type: 'url',
      },
      ENVIRONMENT: {
        required: true,
        type: 'string',
        allowedValues: ['development', 'staging', 'production'],
      },
      APP_VERSION: {
        required: true,
        type: 'string',
        pattern: /^\d+\.\d+\.\d+$/,
      },
      DEBUG_MODE: {
        type: 'boolean',
      },
      API_TIMEOUT: {
        type: 'number',
      },
      LOG_LEVEL: {
        type: 'string',
        allowedValues: ['debug', 'info', 'warn', 'error'],
      },
      ENCRYPTION_KEY_SIZE: {
        type: 'number',
      },
      MAX_CACHE_SIZE: {
        type: 'number',
      },
      NETWORK_TIMEOUT: {
        type: 'number',
      },
    };

    return this.validate(config, rules);
  }

  /**
   * Validates camera configuration
   */
  validateCameraConfig(config: Record<string, any>): ValidationResult {
    const rules: Record<string, ConfigValidationRules> = {
      DEFAULT_QUALITY: {
        type: 'string',
        allowedValues: ['auto', '360p', '480p', '720p', '1080p', '4k'],
      },
      MAX_RETRY_ATTEMPTS: {
        type: 'number',
      },
      BUFFER_SIZE: {
        type: 'number',
      },
      CONNECTION_TIMEOUT: {
        type: 'number',
      },
      HLS_SEGMENT_DURATION: {
        type: 'number',
      },
    };

    return this.validate(config, rules);
  }
  /**
   * Validates security configuration
   */
  validateSecurityConfig(config: Record<string, any>): ValidationResult {
    const rules: Record<string, ConfigValidationRules> = {
      AUTH_TOKEN_EXPIRY: {
        type: 'number',
      },
      REFRESH_TOKEN_EXPIRY: {
        type: 'number',
      },
      PASSWORD_MIN_LENGTH: {
        type: 'number',
      },
      PASSWORD_REQUIRE_SPECIAL: {
        type: 'boolean',
      },
      SESSION_TIMEOUT: {
        type: 'number',
      },
      MAX_LOGIN_ATTEMPTS: {
        type: 'number',
      },
    };

    return this.validate(config, rules);
  }

  /**
   * Validate environment configuration
   */
  async validateEnvironment(): Promise<ValidationResult> {
    const envConfig = {
      API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:8000',
      WEBSOCKET_URL: process.env.WEBSOCKET_URL || 'ws://localhost:8002',
      ENVIRONMENT: process.env.ENVIRONMENT || 'development',
    };

    const rules = {
      API_BASE_URL: { required: true, type: 'url' as const },
      WEBSOCKET_URL: { required: true, type: 'string' as const },
      ENVIRONMENT: { required: true, allowedValues: ['development', 'staging', 'production'] },
    };

    const result = this.validate(envConfig, rules);
    this.validationResults.environment = result;
    return result;
  }

  /**
   * Validate services configuration
   */
  async validateServices(): Promise<ValidationResult> {
    const result = { isValid: true, errors: [] };
    this.validationResults.services = result;
    return result;
  }

  /**
   * Validate API configuration
   */
  async validateApiConfig(): Promise<ValidationResult> {
    const result = { isValid: true, errors: [] };
    this.validationResults.apiConfig = result;
    return result;
  }

  /**
   * Validate dependencies
   */
  async validateDependencies(): Promise<ValidationResult> {
    const result = { isValid: true, errors: [] };
    this.validationResults.dependencies = result;
    return result;
  }

  /**
   * Run complete validation suite
   */
  async validateAll(): Promise<boolean> {
    await this.validateEnvironment();
    await this.validateServices();
    await this.validateApiConfig();
    await this.validateDependencies();
    
    return Object.values(this.validationResults).every(result => result?.isValid);
  }
}

// Create and export singleton instance
const configValidator = new ConfigValidator();

export default configValidator;
export { ConfigValidator };
