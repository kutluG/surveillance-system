import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Provider } from 'react-redux';
import { NavigationContainer } from '@react-navigation/native';
import configureStore from 'redux-mock-store';

// Test utilities for React Native components
export const createMockStore = (initialState = {}) => {
  const mockStore = configureStore([]);
  return mockStore({
    cameras: {
      cameras: [],
      loading: false,
      error: null,
      ...initialState.cameras,
    },
    alerts: {
      alerts: [],
      loading: false,
      error: null,
      ...initialState.alerts,
    },
    app: {
      theme: 'dark',
      isConnected: true,
      ...initialState.app,
    },
    ...initialState,
  });
};

export const renderWithProviders = (
  component,
  {
    initialState = {},
    store = createMockStore(initialState),
    navigationOptions = {},
    ...renderOptions
  } = {}
) => {
  const Wrapper = ({ children }) => (
    <Provider store={store}>
      <NavigationContainer {...navigationOptions}>
        {children}
      </NavigationContainer>
    </Provider>
  );

  return {
    ...render(component, { wrapper: Wrapper, ...renderOptions }),
    store,
  };
};

// Mock data generators
export const generateMockCamera = (overrides = {}) => ({
  id: 'camera-1',
  name: 'Front Door Camera',
  status: 'online',
  location: 'entrance',
  streamUrl: 'rtmp://example.com/stream1',
  thumbnailUrl: 'https://example.com/thumb1.jpg',
  isRecording: true,
  batteryLevel: 85,
  signalStrength: 75,
  lastSeen: new Date().toISOString(),
  ...overrides,
});

export const generateMockAlert = (overrides = {}) => ({
  id: 'alert-1',
  type: 'motion_detected',
  severity: 'medium',
  message: 'Motion detected at Front Door Camera',
  timestamp: new Date().toISOString(),
  cameraId: 'camera-1',
  cameraName: 'Front Door Camera',
  isRead: false,
  imageUrl: 'https://example.com/alert1.jpg',
  videoUrl: 'https://example.com/alert1.mp4',
  ...overrides,
});

export const generateMockUser = (overrides = {}) => ({
  id: 'user-1',
  email: 'test@example.com',
  name: 'Test User',
  role: 'admin',
  permissions: ['view_cameras', 'manage_alerts', 'system_settings'],
  preferences: {
    theme: 'dark',
    notifications: true,
    biometricAuth: true,
  },
  ...overrides,
});

export const generateMockRecording = (overrides = {}) => ({
  id: 'recording-1',
  cameraId: 'camera-1',
  cameraName: 'Front Door Camera',
  startTime: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
  endTime: new Date().toISOString(),
  duration: 3600, // 1 hour in seconds
  fileSize: 1024000, // 1MB
  thumbnailUrl: 'https://example.com/thumb1.jpg',
  videoUrl: 'https://example.com/recording1.mp4',
  tags: ['motion', 'person'],
  ...overrides,
});

// Test helper functions
export const waitForLoadingToFinish = async () => {
  await waitFor(() => {
    // Wait for any loading indicators to disappear
  }, { timeout: 3000 });
};

export const mockAsyncFunction = (returnValue, delay = 100) => {
  return jest.fn(() => 
    new Promise(resolve => setTimeout(() => resolve(returnValue), delay))
  );
};

export const mockFailingAsyncFunction = (error, delay = 100) => {
  return jest.fn(() => 
    new Promise((_, reject) => setTimeout(() => reject(error), delay))
  );
};

// Navigation test helpers
export const mockNavigation = {
  navigate: jest.fn(),
  goBack: jest.fn(),
  push: jest.fn(),
  pop: jest.fn(),
  replace: jest.fn(),
  reset: jest.fn(),
  setParams: jest.fn(),
  dispatch: jest.fn(),
  setOptions: jest.fn(),
  isFocused: jest.fn(() => true),
  addListener: jest.fn(),
  removeListener: jest.fn(),
};

export const mockRoute = {
  params: {},
  name: 'TestScreen',
  key: 'test-key',
};

// Custom matchers
expect.extend({
  toBeVisible(received) {
    const pass = received && received.props && !received.props.style?.display === 'none';
    return {
      message: () => `expected element to ${pass ? 'not ' : ''}be visible`,
      pass,
    };
  },
  
  toHaveStyle(received, expectedStyle) {
    const actualStyle = received.props.style || {};
    const pass = Object.keys(expectedStyle).every(
      key => actualStyle[key] === expectedStyle[key]
    );
    return {
      message: () => 
        `expected element to have style ${JSON.stringify(expectedStyle)}, ` +
        `but got ${JSON.stringify(actualStyle)}`,
      pass,
    };
  },
});

// Test data sets
export const testData = {
  cameras: [
    generateMockCamera({ id: 'camera-1', name: 'Front Door', status: 'online' }),
    generateMockCamera({ id: 'camera-2', name: 'Back Yard', status: 'offline' }),
    generateMockCamera({ id: 'camera-3', name: 'Garage', status: 'recording' }),
  ],
  
  alerts: [
    generateMockAlert({ id: 'alert-1', type: 'motion_detected', severity: 'high' }),
    generateMockAlert({ id: 'alert-2', type: 'person_detected', severity: 'medium' }),
    generateMockAlert({ id: 'alert-3', type: 'sound_detected', severity: 'low' }),
  ],
  
  recordings: [
    generateMockRecording({ id: 'rec-1', duration: 300 }),
    generateMockRecording({ id: 'rec-2', duration: 600 }),
    generateMockRecording({ id: 'rec-3', duration: 900 }),
  ],
  
  user: generateMockUser(),
};

// Performance test helpers
export const measureRenderTime = (component, iterations = 10) => {
  const times = [];
  
  for (let i = 0; i < iterations; i++) {
    const start = performance.now();
    render(component);
    const end = performance.now();
    times.push(end - start);
  }
  
  const average = times.reduce((sum, time) => sum + time, 0) / times.length;
  const min = Math.min(...times);
  const max = Math.max(...times);
  
  return { average, min, max, times };
};

// Accessibility test helpers
export const checkAccessibility = (component) => {
  const { getByRole, queryAllByRole } = render(component);
  
  // Check for basic accessibility requirements
  const buttons = queryAllByRole('button');
  const textInputs = queryAllByRole('textbox');
  const images = queryAllByRole('image');
  
  return {
    hasButtons: buttons.length > 0,
    hasTextInputs: textInputs.length > 0,
    hasImages: images.length > 0,
    buttonCount: buttons.length,
    textInputCount: textInputs.length,
    imageCount: images.length,
  };
};

export default {
  renderWithProviders,
  createMockStore,
  generateMockCamera,
  generateMockAlert,
  generateMockUser,
  generateMockRecording,
  waitForLoadingToFinish,
  mockAsyncFunction,
  mockFailingAsyncFunction,
  mockNavigation,
  mockRoute,
  testData,
  measureRenderTime,
  checkAccessibility,
};
