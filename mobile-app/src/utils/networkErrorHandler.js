/**
 * Network Error Handling Utility
 * Provides consistent error handling across all API services
 */
import { Alert } from 'react-native';
import secureStorage from './secureStorage';
import EnvironmentConfig from '../config/environment';

export const ERROR_TYPES = {
  NETWORK: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT_ERROR',
  AUTH: 'AUTH_ERROR',
  SERVER: 'SERVER_ERROR',
  CLIENT: 'CLIENT_ERROR',
  UNKNOWN: 'UNKNOWN_ERROR',
};

export const ERROR_MESSAGES = {
  [ERROR_TYPES.NETWORK]: 'Network connection error. Please check your internet connection.',
  [ERROR_TYPES.TIMEOUT]: 'Request timed out. Please try again.',
  [ERROR_TYPES.AUTH]: 'Authentication failed. Please log in again.',
  [ERROR_TYPES.SERVER]: 'Server error. Please try again later.',
  [ERROR_TYPES.CLIENT]: 'Invalid request. Please check your input.',
  [ERROR_TYPES.UNKNOWN]: 'An unexpected error occurred. Please try again.',
};

class NetworkErrorHandler {
  constructor() {
    this.retryCount = new Map();
    this.maxRetries = 3;
    this.retryDelay = 1000; // 1 second
  }

  /**
   * Handle API errors consistently
   */
  handleError(error, context = '') {
    const errorInfo = this.parseError(error);
    
    if (EnvironmentConfig.isDebugEnabled()) {
      console.error(`[${context}] API Error:`, {
        type: errorInfo.type,
        message: errorInfo.message,
        status: errorInfo.status,
        url: errorInfo.url,
        stack: error.stack,
      });
    }

    // Handle specific error types
    switch (errorInfo.type) {
      case ERROR_TYPES.AUTH:
        this.handleAuthError();
        break;
      case ERROR_TYPES.NETWORK:
        this.handleNetworkError(errorInfo);
        break;
      case ERROR_TYPES.TIMEOUT:
        this.handleTimeoutError(errorInfo);
        break;
      case ERROR_TYPES.SERVER:
        this.handleServerError(errorInfo);
        break;
      default:
        this.handleGenericError(errorInfo);
    }

    return errorInfo;
  }

  /**
   * Parse error object to extract relevant information
   */
  parseError(error) {
    let type = ERROR_TYPES.UNKNOWN;
    let message = ERROR_MESSAGES[ERROR_TYPES.UNKNOWN];
    let status = null;
    let url = null;

    if (error.response) {
      // Server responded with error status
      status = error.response.status;
      url = error.response.config?.url;
      message = error.response.data?.message || error.response.statusText;

      if (status === 401 || status === 403) {
        type = ERROR_TYPES.AUTH;
        message = ERROR_MESSAGES[ERROR_TYPES.AUTH];
      } else if (status >= 400 && status < 500) {
        type = ERROR_TYPES.CLIENT;
        message = ERROR_MESSAGES[ERROR_TYPES.CLIENT];
      } else if (status >= 500) {
        type = ERROR_TYPES.SERVER;
        message = ERROR_MESSAGES[ERROR_TYPES.SERVER];
      }
    } else if (error.request) {
      // Network error
      type = ERROR_TYPES.NETWORK;
      message = ERROR_MESSAGES[ERROR_TYPES.NETWORK];
      url = error.config?.url;
    } else if (error.code === 'ECONNABORTED') {
      // Timeout error
      type = ERROR_TYPES.TIMEOUT;
      message = ERROR_MESSAGES[ERROR_TYPES.TIMEOUT];
    }

    return { type, message, status, url, originalError: error };
  }

  /**
   * Handle authentication errors
   */  async handleAuthError() {
    try {
      // Clear stored auth token
      await secureStorage.removeItem('auth_token');
      await secureStorage.removeItem('refresh_token');
      
      // Show auth error message
      Alert.alert(
        'Authentication Failed',
        'Your session has expired. Please log in again.',
        [{ text: 'OK' }]
      );

      // Navigate to login screen
      // NavigationService.navigate('Login');
    } catch (error) {
      console.error('Error handling auth failure:', error);
    }
  }

  /**
   * Handle network errors
   */
  handleNetworkError(errorInfo) {
    Alert.alert(
      'Connection Error',
      errorInfo.message,
      [
        { text: 'OK' },
        { text: 'Retry', onPress: () => this.retryLastRequest(errorInfo) }
      ]
    );
  }

  /**
   * Handle timeout errors
   */
  handleTimeoutError(errorInfo) {
    Alert.alert(
      'Request Timeout',
      errorInfo.message,
      [
        { text: 'OK' },
        { text: 'Retry', onPress: () => this.retryLastRequest(errorInfo) }
      ]
    );
  }

  /**
   * Handle server errors
   */
  handleServerError(errorInfo) {
    if (errorInfo.status >= 500) {
      Alert.alert(
        'Server Error',
        'Our servers are experiencing issues. Please try again later.',
        [{ text: 'OK' }]
      );
    }
  }

  /**
   * Handle generic errors
   */
  handleGenericError(errorInfo) {
    Alert.alert(
      'Error',
      errorInfo.message,
      [{ text: 'OK' }]
    );
  }

  /**
   * Retry mechanism for failed requests
   */
  async retryLastRequest(errorInfo) {
    const requestKey = errorInfo.url || 'unknown';
    const currentRetries = this.retryCount.get(requestKey) || 0;

    if (currentRetries < this.maxRetries) {
      this.retryCount.set(requestKey, currentRetries + 1);
      
      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, this.retryDelay * (currentRetries + 1)));
      
      // Retry logic would be implemented by the calling service
      console.log(`Retrying request to ${requestKey} (attempt ${currentRetries + 1})`);
      return true;
    } else {
      this.retryCount.delete(requestKey);
      Alert.alert(
        'Retry Failed',
        'Unable to complete the request after multiple attempts.',
        [{ text: 'OK' }]
      );
      return false;
    }
  }

  /**
   * Reset retry count for a specific request
   */
  resetRetryCount(url) {
    this.retryCount.delete(url);
  }

  /**
   * Check if app is offline
   */
  async checkConnectivity() {
    try {
      const response = await fetch('https://www.google.com/generate_204', {
        method: 'HEAD',
        timeout: 5000,
      });
      return response.status === 204;
    } catch (error) {
      return false;
    }
  }

  /**
   * Create axios error interceptor
   */
  createErrorInterceptor() {
    return (error) => {
      const errorInfo = this.handleError(error, 'API Request');
      return Promise.reject(errorInfo);
    };
  }
}

// Export singleton instance
export default new NetworkErrorHandler();
