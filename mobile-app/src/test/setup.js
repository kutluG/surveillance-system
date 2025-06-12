// Jest setup file for React Native testing
import 'react-native-gesture-handler/jestSetup';
import '@testing-library/jest-native/extend-expect';

// Mock react-native-reanimated
jest.mock('react-native-reanimated', () => {
  const Reanimated = require('react-native-reanimated/mock');
  Reanimated.default.call = () => {};
  return Reanimated;
});

// Mock @react-native-async-storage/async-storage
jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock')
);

// Mock @react-native-community/netinfo
jest.mock('@react-native-community/netinfo', () => ({
  addEventListener: jest.fn(),
  fetch: jest.fn(() => Promise.resolve({ 
    isConnected: true,
    type: 'wifi',
    isInternetReachable: true 
  })),
  useNetInfo: jest.fn(() => ({ 
    isConnected: true,
    type: 'wifi',
    isInternetReachable: true 
  })),
}));

// Mock react-native modules
jest.mock('react-native', () => {
  const ReactNative = jest.requireActual('react-native');
  
  // Mock Alert
  ReactNative.Alert = {
    alert: jest.fn(),
  };
  
  // Mock Dimensions
  ReactNative.Dimensions = {
    get: jest.fn(() => ({ width: 375, height: 812 })),
  };
  
  // Mock Animated
  ReactNative.Animated = {
    ...ReactNative.Animated,
    timing: jest.fn(() => ({
      start: jest.fn(),
    })),
    Value: jest.fn(() => ({
      setValue: jest.fn(),
    })),
  };
  
  return ReactNative;
});

// Mock react-navigation
jest.mock('@react-navigation/native', () => ({
  useNavigation: jest.fn(() => ({
    navigate: jest.fn(),
    goBack: jest.fn(),
  })),
  useFocusEffect: jest.fn(),
}));

// Mock react-native-config
jest.mock('react-native-config', () => ({
  API_BASE_URL: 'http://localhost:8001',
  WEBSOCKET_URL: 'ws://localhost:8002',
  ENV: 'test',
}));

// Mock react-native-encrypted-storage
jest.mock('react-native-encrypted-storage', () => ({
  setItem: jest.fn(() => Promise.resolve()),
  getItem: jest.fn(() => Promise.resolve(null)),
  removeItem: jest.fn(() => Promise.resolve()),
  clear: jest.fn(() => Promise.resolve()),
}));

// Mock react-native-aes-crypto
jest.mock('react-native-aes-crypto', () => ({
  AES: {
    encrypt: jest.fn((text) => Promise.resolve(`encrypted_${text}`)),
    decrypt: jest.fn((encrypted) => Promise.resolve(encrypted.replace('encrypted_', ''))),
  },
  SHA256: jest.fn((text) => `hashed_${text}`),
  PBKDF2: jest.fn((password) => `derived_${password}`),
  enc: {
    Utf8: {
      parse: jest.fn((text) => text),
      stringify: jest.fn((obj) => obj),
    },
  },
}));

// Mock react-native-device-info
jest.mock('react-native-device-info', () => ({
  getUniqueId: jest.fn(() => Promise.resolve('test-device-id')),
  getModel: jest.fn(() => 'Test Device'),
}));

// Mock react-native-keychain
jest.mock('react-native-keychain', () => ({
  setInternetCredentials: jest.fn(() => Promise.resolve()),
  getInternetCredentials: jest.fn(() => Promise.resolve({ username: 'test', password: 'test' })),
  resetInternetCredentials: jest.fn(() => Promise.resolve()),
}));

// Mock react-native-video
jest.mock('react-native-video', () => 'Video');

// Mock react-native-orientation-locker
jest.mock('react-native-orientation-locker', () => ({
  lockToPortrait: jest.fn(),
  lockToLandscape: jest.fn(),
  lockToLandscapeLeft: jest.fn(),
  lockToLandscapeRight: jest.fn(),
  unlockAllOrientations: jest.fn(),
  getOrientation: jest.fn((callback) => callback('portrait')),
  addOrientationListener: jest.fn(),
  removeOrientationListener: jest.fn(),
  PORTRAIT: 'portrait',
  LANDSCAPE: 'landscape',
  'LANDSCAPE-LEFT': 'landscape-left',
  'LANDSCAPE-RIGHT': 'landscape-right',
}));

// Silence the warning: Animated: `useNativeDriver` is not supported
jest.mock('react-native/Libraries/Animated/NativeAnimatedHelper');

// Global test timeout
jest.setTimeout(10000);
