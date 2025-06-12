import React from 'react';
import { render, waitFor, act } from '@testing-library/react-native';
import CameraView from '../CameraView';

// Mock AsyncStorage with proper Promise resolution
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
  removeItem: jest.fn().mockResolvedValue(undefined),
  clear: jest.fn().mockResolvedValue(undefined),
}));

// Mock react-native-video
jest.mock('react-native-video', () => {
  const React = require('react');
  return React.forwardRef((props, ref) => {
    const MockVideo = require('react-native').View;
    return React.createElement(MockVideo, { ...props, ref, testID: 'video-component' });
  });
});

// Mock react-native-orientation-locker
jest.mock('react-native-orientation-locker', () => ({
  lockToPortrait: jest.fn(),
  lockToLandscape: jest.fn(),
  unlockAllOrientations: jest.fn(),
}));

// Mock react-native-vector-icons
jest.mock('react-native-vector-icons/MaterialIcons', () => {
  const React = require('react');
  return (props) => {
    const MockIcon = require('react-native').Text;
    return React.createElement(MockIcon, props, props.name);
  };
});

// Mock HLSParser
const mockHLSParser = {
  parsePlaylist: jest.fn().mockResolvedValue([
    {
      bandwidth: 500000,
      resolution: '640x360',
      url: 'https://example.com/low.m3u8',
      label: 'Low (360p)',
    },
  ]),
};

jest.mock('../../utils/hlsParser', () => ({
  HLSParser: jest.fn().mockImplementation(() => mockHLSParser),
}));

describe('CameraView Adaptive Bitrate Tests', () => {
  const mockHlsUrl = 'https://example.com/master.m3u8';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render without crashing', async () => {
    await act(async () => {
      const { getByTestId } = render(
        React.createElement(CameraView, { hlsMasterPlaylistUrl: mockHlsUrl })
      );
      
      await waitFor(() => {
        expect(getByTestId('video-component')).toBeTruthy();
      });
    });
  });
});
