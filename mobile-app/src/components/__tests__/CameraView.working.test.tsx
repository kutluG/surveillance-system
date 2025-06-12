import React from 'react';
import { render } from '@testing-library/react-native';
import CameraView from '../CameraView';

// Mock react-native-video
jest.mock('react-native-video', () => {
  const mockReact = require('react');
  return mockReact.forwardRef((props: any, ref: any) => {
    mockReact.useImperativeHandle(ref, () => ({
      seek: jest.fn(),
      presentFullscreenPlayer: jest.fn(),
      dismissFullscreenPlayer: jest.fn(),
    }));
    return null; // Return null for testing
  });
});

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(),
  removeItem: jest.fn().mockResolvedValue(),
  clear: jest.fn().mockResolvedValue(),
}));

// Mock HLSParser
jest.mock('../../utils/hlsParser', () => ({
  HLSParser: jest.fn().mockImplementation(() => ({
    parsePlaylist: jest.fn().mockResolvedValue([
      { label: '360p', url: 'test-360p.m3u8', bandwidth: 500000 },
      { label: '720p', url: 'test-720p.m3u8', bandwidth: 1000000 },
    ]),
  })),
}));

// Mock react-native-orientation-locker
jest.mock('react-native-orientation-locker', () => ({
  lockToLandscape: jest.fn(),
  lockToPortrait: jest.fn(),
  unlockAllOrientations: jest.fn(),
}));

// Mock react-native-vector-icons
jest.mock('react-native-vector-icons/MaterialIcons', () => 'Icon');

describe('CameraView', () => {
  const mockHLSUrl = 'https://example.com/master.m3u8';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render without crashing', () => {
    const { UNSAFE_root } = render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);
    expect(UNSAFE_root).toBeTruthy();
  });

  it('should accept required props', () => {
    expect(() => {
      render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);
    }).not.toThrow();
  });

  it('should handle optional props', () => {
    const mockOnLoad = jest.fn();
    const mockOnError = jest.fn();
    const mockOnFullscreenChange = jest.fn();

    expect(() => {
      render(
        <CameraView
          hlsMasterPlaylistUrl={mockHLSUrl}
          onLoad={mockOnLoad}
          onError={mockOnError}
          onFullscreenPlayerDidPresent={mockOnFullscreenChange}
          onFullscreenPlayerDidDismiss={mockOnFullscreenChange}
        />
      );
    }).not.toThrow();
  });
});
