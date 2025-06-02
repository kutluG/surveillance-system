import axios from 'axios';
import { API_CONFIG } from '../constants';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Create axios instance for camera service
const cameraAPI = axios.create({
  baseURL: API_CONFIG.CAMERA_URL,
  timeout: API_CONFIG.TIMEOUT,
});

// Request interceptor to add auth token
cameraAPI.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem('token');
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
cameraAPI.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - logout user
      AsyncStorage.removeItem('token');
    }
    return Promise.reject(error);
  }
);

export const cameraService = {
  // Get all cameras
  async getCameras(params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    return cameraAPI.get(`/cameras${queryParams ? `?${queryParams}` : ''}`);
  },

  // Get specific camera details
  async getCameraDetails(cameraId) {
    return cameraAPI.get(`/cameras/${cameraId}`);
  },

  // Get camera live feed URL
  async getCameraFeedUrl(cameraId, quality = 'high') {
    return cameraAPI.get(`/cameras/${cameraId}/feed`, {
      params: { quality }
    });
  },

  // Get camera recordings
  async getCameraRecordings(cameraId, params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    return cameraAPI.get(`/cameras/${cameraId}/recordings${queryParams ? `?${queryParams}` : ''}`);
  },

  // Start/stop camera recording
  async toggleRecording(cameraId, recording) {
    return cameraAPI.post(`/cameras/${cameraId}/recording`, { recording });
  },

  // Update camera settings
  async updateCameraSettings(cameraId, settings) {
    return cameraAPI.put(`/cameras/${cameraId}/settings`, settings);
  },

  // Get camera status
  async getCameraStatus(cameraId) {
    return cameraAPI.get(`/cameras/${cameraId}/status`);
  },

  // Control camera (pan, tilt, zoom)
  async controlCamera(cameraId, action, params = {}) {
    return cameraAPI.post(`/cameras/${cameraId}/control`, { action, ...params });
  },

  // Get camera snapshots
  async getCameraSnapshot(cameraId) {
    return cameraAPI.get(`/cameras/${cameraId}/snapshot`, {
      responseType: 'blob'
    });
  },

  // Get camera detection zones
  async getDetectionZones(cameraId) {
    return cameraAPI.get(`/cameras/${cameraId}/detection-zones`);
  },

  // Update camera detection zones
  async updateDetectionZones(cameraId, zones) {
    return cameraAPI.put(`/cameras/${cameraId}/detection-zones`, { zones });
  },

  // Get camera analytics
  async getCameraAnalytics(cameraId, timeRange = '24h') {
    return cameraAPI.get(`/cameras/${cameraId}/analytics`, {
      params: { timeRange }
    });
  },

  // Test camera connection
  async testCameraConnection(cameraId) {
    return cameraAPI.post(`/cameras/${cameraId}/test`);
  },

  // Get camera presets
  async getCameraPresets(cameraId) {
    return cameraAPI.get(`/cameras/${cameraId}/presets`);
  },

  // Set camera preset
  async setCameraPreset(cameraId, presetName, position) {
    return cameraAPI.post(`/cameras/${cameraId}/presets`, {
      name: presetName,
      position
    });
  },

  // Go to camera preset
  async goToCameraPreset(cameraId, presetId) {
    return cameraAPI.post(`/cameras/${cameraId}/presets/${presetId}/goto`);
  },

  // Delete camera preset
  async deleteCameraPreset(cameraId, presetId) {
    return cameraAPI.delete(`/cameras/${cameraId}/presets/${presetId}`);
  },

  // Get camera permissions
  async getCameraPermissions(cameraId) {
    return cameraAPI.get(`/cameras/${cameraId}/permissions`);
  },

  // Update camera permissions
  async updateCameraPermissions(cameraId, permissions) {
    return cameraAPI.put(`/cameras/${cameraId}/permissions`, permissions);
  }
};
