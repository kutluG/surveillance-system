import axios from 'axios';
import { API_CONFIG } from '../constants';
import secureStorage from '../utils/secureStorage';

// Create axios instance for dashboard service
const dashboardAPI = axios.create({
  baseURL: API_CONFIG.DASHBOARD_URL,
  timeout: API_CONFIG.TIMEOUT,
});

// Request interceptor to add auth token
dashboardAPI.interceptors.request.use(
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
dashboardAPI.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - logout user
      secureStorage.removeItem('token');
    }
    return Promise.reject(error);
  }
);

export const dashboardService = {
  // Get dashboard overview
  async getDashboardOverview(timeRange = '24h') {
    return dashboardAPI.get('/overview', {
      params: { timeRange }
    });
  },

  // Get system statistics
  async getSystemStats() {
    return dashboardAPI.get('/stats/system');
  },

  // Get camera statistics
  async getCameraStats(timeRange = '24h') {
    return dashboardAPI.get('/stats/cameras', {
      params: { timeRange }
    });
  },

  // Get alert statistics
  async getAlertStats(timeRange = '24h') {
    return dashboardAPI.get('/stats/alerts', {
      params: { timeRange }
    });
  },

  // Get detection statistics
  async getDetectionStats(timeRange = '24h') {
    return dashboardAPI.get('/stats/detections', {
      params: { timeRange }
    });
  },

  // Get activity timeline
  async getActivityTimeline(timeRange = '24h') {
    return dashboardAPI.get('/activity/timeline', {
      params: { timeRange }
    });
  },

  // Get recent activities
  async getRecentActivities(limit = 10) {
    return dashboardAPI.get('/activity/recent', {
      params: { limit }
    });
  },

  // Get system health
  async getSystemHealth() {
    return dashboardAPI.get('/health');
  },

  // Get storage usage
  async getStorageUsage() {
    return dashboardAPI.get('/storage/usage');
  },

  // Get bandwidth usage
  async getBandwidthUsage(timeRange = '24h') {
    return dashboardAPI.get('/bandwidth/usage', {
      params: { timeRange }
    });
  },

  // Get user activity
  async getUserActivity(timeRange = '24h') {
    return dashboardAPI.get('/activity/users', {
      params: { timeRange }
    });
  },

  // Get top locations by activity
  async getTopLocations(timeRange = '24h', limit = 5) {
    return dashboardAPI.get('/locations/top', {
      params: { timeRange, limit }
    });
  },

  // Get detection trends
  async getDetectionTrends(timeRange = '7d') {
    return dashboardAPI.get('/trends/detections', {
      params: { timeRange }
    });
  },

  // Get alert trends
  async getAlertTrends(timeRange = '7d') {
    return dashboardAPI.get('/trends/alerts', {
      params: { timeRange }
    });
  },

  // Get performance metrics
  async getPerformanceMetrics(timeRange = '1h') {
    return dashboardAPI.get('/metrics/performance', {
      params: { timeRange }
    });
  },

  // Get quick actions data
  async getQuickActions() {
    return dashboardAPI.get('/quick-actions');
  },

  // Execute quick action
  async executeQuickAction(actionId, params = {}) {
    return dashboardAPI.post(`/quick-actions/${actionId}/execute`, params);
  },

  // Get widget data
  async getWidgetData(widgetType, params = {}) {
    return dashboardAPI.get(`/widgets/${widgetType}`, { params });
  },

  // Get notification summary
  async getNotificationSummary() {
    return dashboardAPI.get('/notifications/summary');
  },

  // Get scheduled tasks
  async getScheduledTasks() {
    return dashboardAPI.get('/tasks/scheduled');
  },

  // Get system alerts
  async getSystemAlerts() {
    return dashboardAPI.get('/alerts/system');
  }
};
