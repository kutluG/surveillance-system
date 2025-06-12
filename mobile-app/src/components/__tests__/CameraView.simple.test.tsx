import React from 'react';
import { render } from '@testing-library/react-native';
import CameraView from '../CameraView';

// Mock AsyncStorage with proper Promise resolution
const mockAsyncStorage = {
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
  removeItem: jest.fn().mockResolvedValue(undefined),
  clear: jest.fn().mockResolvedValue(undefined),
  getAllKeys: jest.fn().mockResolvedValue([]),
  multiGet: jest.fn().mockResolvedValue([]),
  multiSet: jest.fn().mockResolvedValue(undefined),
  multiRemove: jest.fn().mockResolvedValue(undefined),
};

jest.mock('@react-native-async-storage/async-storage', () => mockAsyncStorage);

// Mock react-native-video
jest.mock('react-native-video', () => {
  const React = require('react');
  return React.forwardRef((props: any, ref: any) => {
    const MockVideo = require('react-native').View;
    return <MockVideo {...props} ref={ref} testID="video-component" />;
  });
});

// Mock react-native-orientation-locker
jest.mock('react-native-orientation-locker', () => ({
  lockToPortrait: jest.fn(),
  lockToLandscape: jest.fn(),
  unlockAllOrientations: jest.fn(),
  getOrientation: jest.fn().mockResolvedValue('PORTRAIT'),
}));

// Mock react-native-vector-icons
jest.mock('react-native-vector-icons/MaterialIcons', () => {
  const React = require('react');
  return ({ name, size, color, ...props }: any) => {
    const MockIcon = require('react-native').Text;
    return <MockIcon {...props}>{name}</MockIcon>;
  };
});

// Mock HLSParser
const mockHLSParser = {
  parsePlaylist: jest.fn().mockResolvedValue([]),
};

jest.mock('../../utils/hlsParser', () => ({
  HLSParser: jest.fn().mockImplementation(() => mockHLSParser),
}));

describe('CameraView Simple Tests', () => {
  const mockHlsUrl = 'https://example.com/master.m3u8';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render without crashing', () => {
    const { getByTestId } = render(
      <CameraView hlsMasterPlaylistUrl={mockHlsUrl} />
    );
    expect(getByTestId('video-component')).toBeTruthy();
  });

  it('should call AsyncStorage.getItem during initialization', async () => {
    render(<CameraView hlsMasterPlaylistUrl={mockHlsUrl} />);
    
    // Wait for async operations to complete
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect(mockAsyncStorage.getItem).toHaveBeenCalled();
  });
});
