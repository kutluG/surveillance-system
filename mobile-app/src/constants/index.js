import EnvironmentConfig from '../config/environment';

export const API_CONFIG = {
  BASE_URL: EnvironmentConfig.get('API_BASE_URL'),
  WEBSOCKET_URL: EnvironmentConfig.get('WEBSOCKET_URL'),
  TIMEOUT: EnvironmentConfig.get('TIMEOUT'),
  
  // Service URLs
  AUTH_URL: EnvironmentConfig.get('AUTH_URL'),
  CAMERA_URL: EnvironmentConfig.get('CAMERA_URL'),
  ALERTS_URL: EnvironmentConfig.get('ALERTS_URL'),
  DASHBOARD_URL: EnvironmentConfig.get('DASHBOARD_URL'),
  VMS_URL: EnvironmentConfig.get('VMS_URL'),
  RAG_URL: EnvironmentConfig.get('RAG_URL'),
  PROMPT_URL: EnvironmentConfig.get('PROMPT_URL'),
  RULEGEN_URL: EnvironmentConfig.get('RULEGEN_URL'),
  NOTIFIER_URL: EnvironmentConfig.get('NOTIFIER_URL'),
  
  // Service ports mapping to backend docker-compose
  PORTS: EnvironmentConfig.get('PORTS'),
};

export const COLORS = {
  primary: '#007AFF',
  secondary: '#5856D6',
  success: '#34C759',
  warning: '#FF9500',
  error: '#FF3B30',
  info: '#5AC8FA',
  
  // Dark theme
  background: '#000000',
  surface: '#1A1A2E',
  card: '#16213E',
  text: '#FFFFFF',
  textSecondary: '#8E8E93',
  border: '#38383A',
  
  // Alert severities
  alertHigh: '#FF3B30',
  alertMedium: '#FF9500',
  alertLow: '#34C759',
  
  // Camera status
  cameraOnline: '#34C759',
  cameraOffline: '#FF3B30',
  cameraWarning: '#FF9500',
};

export const SIZES = {
  // Padding and margins
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  
  // Font sizes
  textXS: 12,
  textSM: 14,
  textMD: 16,
  textLG: 18,
  textXL: 20,
  textXXL: 24,
  
  // Border radius
  radiusXS: 4,
  radiusSM: 8,
  radiusMD: 12,
  radiusLG: 16,
  radiusXL: 20,
  
  // Icon sizes
  iconXS: 16,
  iconSM: 20,
  iconMD: 24,
  iconLG: 32,
  iconXL: 40,
};

export const FONTS = {
  regular: 'System',
  medium: 'System',
  bold: 'System',
  light: 'System',
};

export const ALERT_TYPES = {
  MOTION_DETECTION: 'Motion Detection',
  UNAUTHORIZED_ACCESS: 'Unauthorized Access',
  PERIMETER_BREACH: 'Perimeter Breach',
  OBJECT_RECOGNITION: 'Object Recognition',
  SYSTEM_ERROR: 'System Error',
  CAMERA_OFFLINE: 'Camera Offline',
};

export const CAMERA_STATUS = {
  ONLINE: 'online',
  OFFLINE: 'offline',
  ERROR: 'error',
  MAINTENANCE: 'maintenance',
};

export const NOTIFICATION_TYPES = {
  ALERT: 'alert',
  SYSTEM: 'system',
  CAMERA: 'camera',
  UPDATE: 'update',
};
