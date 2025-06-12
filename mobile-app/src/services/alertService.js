import axios from 'axios';
import { API_CONFIG } from '../constants';
import secureStorage from '../utils/secureStorage';

// Create axios instance for alert service
const alertAPI = axios.create({
  baseURL: API_CONFIG.ALERTS_URL,
  timeout: API_CONFIG.TIMEOUT,
});

// Request interceptor to add auth token
alertAPI.interceptors.request.use(
  async (config) => {
    const token = await secureStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
alertAPI.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - logout user
      secureStorage.removeItem('token');
    }
    return Promise.reject(error);
  }
);

export const alertService = {
  // Get all alerts
  async getAlerts(params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    return alertAPI.get(`/alerts${queryParams ? `?${queryParams}` : ''}`);
  },

  // Get specific alert details
  async getAlertDetails(alertId) {
    return alertAPI.get(`/alerts/${alertId}`);
  },

  // Acknowledge an alert
  async acknowledgeAlert(alertId) {
    return alertAPI.post(`/alerts/${alertId}/acknowledge`);
  },

  // Dismiss an alert
  async dismissAlert(alertId) {
    return alertAPI.post(`/alerts/${alertId}/dismiss`);
  },

  // Get alert statistics
  async getAlertStats(timeRange = '24h') {
    return alertAPI.get('/alerts/stats', {
      params: { timeRange }
    });
  },

  // Get active alerts count
  async getActiveAlertsCount() {
    return alertAPI.get('/alerts/count/active');
  },

  // Get alerts by camera
  async getAlertsByCamera(cameraId, params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    return alertAPI.get(`/alerts/camera/${cameraId}${queryParams ? `?${queryParams}` : ''}`);
  },

  // Get alerts by type
  async getAlertsByType(alertType, params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    return alertAPI.get(`/alerts/type/${alertType}${queryParams ? `?${queryParams}` : ''}`);
  },

  // Get alerts by severity
  async getAlertsBySeverity(severity, params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    return alertAPI.get(`/alerts/severity/${severity}${queryParams ? `?${queryParams}` : ''}`);
  },

  // Create manual alert
  async createAlert(alertData) {
    return alertAPI.post('/alerts', alertData);
  },

  // Update alert
  async updateAlert(alertId, updateData) {
    return alertAPI.put(`/alerts/${alertId}`, updateData);
  },

  // Delete alert
  async deleteAlert(alertId) {
    return alertAPI.delete(`/alerts/${alertId}`);
  },

  // Bulk acknowledge alerts
  async bulkAcknowledgeAlerts(alertIds) {
    return alertAPI.post('/alerts/bulk/acknowledge', { alertIds });
  },

  // Bulk dismiss alerts
  async bulkDismissAlerts(alertIds) {
    return alertAPI.post('/alerts/bulk/dismiss', { alertIds });
  },

  // Get alert trends
  async getAlertTrends(timeRange = '7d') {
    return alertAPI.get('/alerts/trends', {
      params: { timeRange }
    });
  },

  // Get alert locations
  async getAlertLocations(timeRange = '24h') {
    return alertAPI.get('/alerts/locations', {
      params: { timeRange }
    });
  },

  // Get alert timeline
  async getAlertTimeline(params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    return alertAPI.get(`/alerts/timeline${queryParams ? `?${queryParams}` : ''}`);
  },

  // Export alerts
  async exportAlerts(params = {}) {
    return alertAPI.get('/alerts/export', {
      params,
      responseType: 'blob'
    });
  },

  // Get alert rules
  async getAlertRules() {
    return alertAPI.get('/alert-rules');
  },

  // Create alert rule
  async createAlertRule(ruleData) {
    return alertAPI.post('/alert-rules', ruleData);
  },

  // Update alert rule
  async updateAlertRule(ruleId, ruleData) {
    return alertAPI.put(`/alert-rules/${ruleId}`, ruleData);
  },

  // Delete alert rule
  async deleteAlertRule(ruleId) {
    return alertAPI.delete(`/alert-rules/${ruleId}`);
  },

  // Toggle alert rule
  async toggleAlertRule(ruleId, enabled) {
    return alertAPI.post(`/alert-rules/${ruleId}/toggle`, { enabled });
  },

  // Get notification settings
  async getNotificationSettings() {
    return alertAPI.get('/notifications/settings');
  },

  // Update notification settings
  async updateNotificationSettings(settings) {
    return alertAPI.put('/notifications/settings', settings);
  },

  // Test notification
  async testNotification(notificationType = 'push') {
    return alertAPI.post('/notifications/test', { type: notificationType });
  },

  // Register device for push notifications
  async registerDevice(deviceToken, platform) {
    return alertAPI.post('/notifications/register', {
      deviceToken,
      platform
    });
  },

  // Unregister device for push notifications
  async unregisterDevice(deviceToken) {
    return alertAPI.post('/notifications/unregister', {
      deviceToken
    });
  }
};
