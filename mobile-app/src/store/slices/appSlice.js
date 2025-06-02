import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  theme: 'dark',
  isLoading: false,
  networkStatus: 'online',
  pushNotificationsEnabled: true,
  biometricsEnabled: false,
  autoLockTimeout: 300000, // 5 minutes
  videoQuality: 'high',
  alertSoundEnabled: true,
  vibrationEnabled: true,
  showNotificationBadge: true,
  language: 'en',
  systemInfo: {
    version: '1.0.0',
    buildNumber: '1',
    platform: '',
    deviceId: ''
  },
  permissions: {
    camera: false,
    microphone: false,
    notifications: false,
    location: false,
    biometrics: false
  },
  lastSyncTime: null,
  isFirstLaunch: true,
  debugMode: false
};

const appSlice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    setTheme: (state, action) => {
      state.theme = action.payload;
    },
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    setNetworkStatus: (state, action) => {
      state.networkStatus = action.payload;
    },
    setPushNotificationsEnabled: (state, action) => {
      state.pushNotificationsEnabled = action.payload;
    },
    setBiometricsEnabled: (state, action) => {
      state.biometricsEnabled = action.payload;
    },
    setAutoLockTimeout: (state, action) => {
      state.autoLockTimeout = action.payload;
    },
    setVideoQuality: (state, action) => {
      state.videoQuality = action.payload;
    },
    setAlertSoundEnabled: (state, action) => {
      state.alertSoundEnabled = action.payload;
    },
    setVibrationEnabled: (state, action) => {
      state.vibrationEnabled = action.payload;
    },
    setShowNotificationBadge: (state, action) => {
      state.showNotificationBadge = action.payload;
    },
    setLanguage: (state, action) => {
      state.language = action.payload;
    },
    setSystemInfo: (state, action) => {
      state.systemInfo = { ...state.systemInfo, ...action.payload };
    },
    setPermissions: (state, action) => {
      state.permissions = { ...state.permissions, ...action.payload };
    },
    updatePermission: (state, action) => {
      const { permission, granted } = action.payload;
      state.permissions[permission] = granted;
    },
    setLastSyncTime: (state, action) => {
      state.lastSyncTime = action.payload;
    },
    setFirstLaunch: (state, action) => {
      state.isFirstLaunch = action.payload;
    },
    setDebugMode: (state, action) => {
      state.debugMode = action.payload;
    },
    updateSettings: (state, action) => {
      Object.keys(action.payload).forEach(key => {
        if (key in state) {
          state[key] = action.payload[key];
        }
      });
    },
    resetAppState: () => initialState
  }
});

export const {
  setTheme,
  setLoading,
  setNetworkStatus,
  setPushNotificationsEnabled,
  setBiometricsEnabled,
  setAutoLockTimeout,
  setVideoQuality,
  setAlertSoundEnabled,
  setVibrationEnabled,
  setShowNotificationBadge,
  setLanguage,
  setSystemInfo,
  setPermissions,
  updatePermission,
  setLastSyncTime,
  setFirstLaunch,
  setDebugMode,
  updateSettings,
  resetAppState
} = appSlice.actions;

// Selectors
export const selectTheme = (state) => state.app.theme;
export const selectIsLoading = (state) => state.app.isLoading;
export const selectNetworkStatus = (state) => state.app.networkStatus;
export const selectPushNotificationsEnabled = (state) => state.app.pushNotificationsEnabled;
export const selectBiometricsEnabled = (state) => state.app.biometricsEnabled;
export const selectAutoLockTimeout = (state) => state.app.autoLockTimeout;
export const selectVideoQuality = (state) => state.app.videoQuality;
export const selectAlertSoundEnabled = (state) => state.app.alertSoundEnabled;
export const selectVibrationEnabled = (state) => state.app.vibrationEnabled;
export const selectShowNotificationBadge = (state) => state.app.showNotificationBadge;
export const selectLanguage = (state) => state.app.language;
export const selectSystemInfo = (state) => state.app.systemInfo;
export const selectPermissions = (state) => state.app.permissions;
export const selectLastSyncTime = (state) => state.app.lastSyncTime;
export const selectIsFirstLaunch = (state) => state.app.isFirstLaunch;
export const selectDebugMode = (state) => state.app.debugMode;

export const selectIsOnline = (state) => state.app.networkStatus === 'online';
export const selectHasPermission = (permission) => (state) => 
  state.app.permissions[permission] || false;

export default appSlice.reducer;
