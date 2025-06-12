import axios from 'axios';
import secureStorage from '../utils/secureStorage';
import { API_CONFIG } from '../constants';
import NetworkErrorHandler from '../utils/networkErrorHandler';

class AuthService {  constructor() {
    this.api = axios.create({
      baseURL: API_CONFIG.AUTH_URL,
      timeout: API_CONFIG.TIMEOUT,
    });    // Add token to requests
    this.api.interceptors.request.use(async (config) => {
      const token = await secureStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });    // Handle token expiration
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const errorInfo = NetworkErrorHandler.handleError(error, 'Auth Service');
        if (errorInfo.type === 'AUTH_ERROR') {
          await secureStorage.removeItem('auth_token');
          // Trigger logout in app
        }
        return Promise.reject(errorInfo);
      }
    );
  }

  async login(credentials) {
    try {
      const response = await this.api.post('/auth/login', credentials);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async verifyToken(token) {
    try {
      const response = await this.api.post('/auth/verify', {token});
      return response.data.user;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async refreshToken() {
    try {
      const response = await this.api.post('/auth/refresh');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }
  async logout() {
    try {
      await this.api.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always remove token even if logout fails
      await secureStorage.removeItem('auth_token');
    }
  }

  async getCurrentUser() {
    try {
      const token = await secureStorage.getItem('auth_token');
      if (!token) {
        return null;
      }
      const response = await this.api.get('/auth/me');
      return response.data;
    } catch (error) {
      // Invalid token, remove it
      await secureStorage.removeItem('auth_token');
      return null;
    }
  }

  async isAuthenticated() {
    const token = await secureStorage.getItem('auth_token');
    return !!token;
  }

  async getToken() {
    return await secureStorage.getItem('auth_token');
  }

  async updateProfile(profileData) {
    try {
      const response = await this.api.put('/auth/profile', profileData);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async changePassword(currentPassword, newPassword) {
    try {
      const response = await this.api.post('/auth/change-password', {
        currentPassword,
        newPassword
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  handleError(error) {
    if (error.response) {
      return new Error(error.response.data.message || 'Authentication failed');
    } else if (error.request) {
      return new Error('Network error. Please check your connection.');
    } else {
      return new Error('An unexpected error occurred');
    }
  }
}

export const authService = new AuthService();
