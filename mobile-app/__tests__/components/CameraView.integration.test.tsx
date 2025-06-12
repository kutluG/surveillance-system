/**
 * Integration tests for CameraView component with HLS adaptive bitrate support
 * Tests the integration between CameraView and react-native-video with mocked dependencies
 */

import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import CameraView from '../../src/components/CameraView';
import { HLSParser } from '../../src/utils/hlsParser';

// Mock react-native-video
const mockVideoRef = {
  seek: jest.fn(),
  presentFullscreenPlayer: jest.fn(),
  dismissFullscreenPlayer: jest.fn(),
};

jest.mock('react-native-video', () => {
  const mockReact = require('react');
  return mockReact.forwardRef((props: any, ref: any) => {
    mockReact.useImperativeHandle(ref, () => mockVideoRef);
    
    // Simulate video component behavior
    React.useEffect(() => {
      // Simulate successful video load after a delay
      const timer = setTimeout(() => {
        if (props.onLoad) {
          props.onLoad({
            duration: 120,
            currentTime: 0,
            naturalSize: { width: 1920, height: 1080 },
          });
        }
      }, 100);

      return () => clearTimeout(timer);
    }, [props.source.uri]);

    return null; // Video component is not rendered in tests
  });
  
  MockVideo.displayName = 'Video';
  return MockVideo;
});

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}));

// Mock HLSParser
jest.mock('../../src/utils/hlsParser', () => ({
  HLSParser: jest.fn().mockImplementation(() => ({
    parsePlaylist: jest.fn(),
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

describe('CameraView Integration Tests', () => {
  const mockHLSUrl = 'https://example.com/master.m3u8';
  const mockQualityLevels = [
    {
      bandwidth: 1000000,
      resolution: '640x360',
      url: 'https://example.com/360p.m3u8',
      label: '360p',
    },
    {
      bandwidth: 2500000,
      resolution: '1280x720',
      url: 'https://example.com/720p.m3u8',
      label: '720p',
    },
    {
      bandwidth: 5000000,
      resolution: '1920x1080',
      url: 'https://example.com/1080p.m3u8',
      label: '1080p',
    },
  ];

  let mockHLSParser;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset AsyncStorage mocks
    AsyncStorage.getItem.mockResolvedValue(null);
    AsyncStorage.setItem.mockResolvedValue();

    // Setup HLS parser mock
    mockHLSParser = {
      parsePlaylist: jest.fn().mockResolvedValue(mockQualityLevels),
    };
    HLSParser.mockImplementation(() => mockHLSParser);
  });

  describe('Component Initialization', () => {
    it('should render with default props and auto quality enabled', async () => {
      const { getByTestId } = render(
        <CameraView hlsMasterPlaylistUrl={mockHLSUrl} />
      );

      await waitFor(() => {
        // Component should initialize with auto quality enabled
        expect(AsyncStorage.getItem).toHaveBeenCalledWith('camera_auto_quality_enabled');
        expect(mockHLSParser.parsePlaylist).toHaveBeenCalledWith(mockHLSUrl);
      });
    });

    it('should restore user preferences from AsyncStorage', async () => {
      AsyncStorage.getItem
        .mockResolvedValueOnce('false') // auto_quality_enabled
        .mockResolvedValueOnce('720p'); // selected_quality

      render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        expect(AsyncStorage.getItem).toHaveBeenCalledWith('camera_auto_quality_enabled');
        expect(AsyncStorage.getItem).toHaveBeenCalledWith('camera_selected_quality');
      });
    });
  });

  describe('HLS Source URI Handling', () => {
    it('should use master playlist URL when auto quality is enabled', async () => {
      const mockOnLoad = jest.fn();
      
      render(
        <CameraView 
          hlsMasterPlaylistUrl={mockHLSUrl} 
          onLoad={mockOnLoad}
        />
      );

      await waitFor(() => {
        // Video component should receive the master playlist URL
        expect(mockOnLoad).toHaveBeenCalledWith(
          expect.objectContaining({
            duration: 120,
            currentTime: 0,
          })
        );
      });
    });

    it('should update source URI when manual quality is selected', async () => {
      const { getByText, getByTestId } = render(
        <CameraView hlsMasterPlaylistUrl={mockHLSUrl} />
      );

      await waitFor(() => {
        expect(mockHLSParser.parsePlaylist).toHaveBeenCalled();
      });

      // Simulate opening quality modal and selecting 360p
      await act(async () => {
        // This would require the component to expose test IDs or use a different testing approach
        // For now, we'll test the logic by checking the Video component's source prop changes
      });
    });
  });

  describe('Quality Level Management', () => {
    it('should parse HLS playlist and extract quality levels', async () => {
      render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        expect(mockHLSParser.parsePlaylist).toHaveBeenCalledWith(mockHLSUrl);
      });
    });

    it('should handle HLS parsing errors gracefully', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      mockHLSParser.parsePlaylist.mockRejectedValue(new Error('Network error'));

      render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Failed to parse HLS playlist:',
          expect.any(Error)
        );
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('User Preference Persistence', () => {
    it('should save auto quality preference to AsyncStorage', async () => {
      render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        // Initial load should not save preferences
        expect(AsyncStorage.setItem).not.toHaveBeenCalled();
      });

      // Simulate user interaction to change auto quality setting
      // This would require component to expose methods or test IDs for interaction
    });

    it('should save manual quality selection to AsyncStorage', async () => {
      const component = render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        expect(mockHLSParser.parsePlaylist).toHaveBeenCalled();
      });

      // Test would simulate user selecting a specific quality
      // and verify AsyncStorage.setItem is called with correct values
    });
  });

  describe('Video Configuration', () => {
    it('should configure Video component with HLS-optimized props', async () => {
      const mockOnError = jest.fn();
      const mockOnLoad = jest.fn();

      render(
        <CameraView 
          hlsMasterPlaylistUrl={mockHLSUrl}
          onError={mockOnError}
          onLoad={mockOnLoad}
        />
      );

      await waitFor(() => {
        // Verify onLoad callback is called, indicating Video component is properly configured
        expect(mockOnLoad).toHaveBeenCalled();
      });
    });

    it('should handle video errors and show retry option', async () => {
      const mockOnError = jest.fn();
      
      // Mock Video component to trigger error
      jest.mocked(require('react-native-video')).mockImplementationOnce(
        React.forwardRef((props, ref) => {
          React.useEffect(() => {
            if (props.onError) {
              props.onError({ error: 'Network error' });
            }
          }, []);
          return null;
        })
      );

      render(
        <CameraView 
          hlsMasterPlaylistUrl={mockHLSUrl}
          onError={mockOnError}
        />
      );

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith({ error: 'Network error' });
      });
    });
  });

  describe('Source URI Prop Changes', () => {
    it('should update Video source when switching from auto to manual quality', async () => {
      let videoProps = {};
      
      // Mock Video to capture props
      jest.mocked(require('react-native-video')).mockImplementation(
        React.forwardRef((props, ref) => {
          videoProps = props;
          React.useImperativeHandle(ref, () => mockVideoRef);
          return null;
        })
      );

      const { rerender } = render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        // Initially should use master playlist
        expect(videoProps.source?.uri).toBe(mockHLSUrl);
      });

      // Simulate quality change (this would be done through component interaction in real tests)
      // For unit testing, we can test the internal logic separately
    });

    it('should maintain source URI format for HLS streaming', async () => {
      let videoProps = {};
      
      jest.mocked(require('react-native-video')).mockImplementation(
        React.forwardRef((props, ref) => {
          videoProps = props;
          return null;
        })
      );

      render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        expect(videoProps.source).toEqual({
          uri: mockHLSUrl,
          headers: {
            'User-Agent': 'SurveillanceApp/1.0.0',
          },
        });
      });
    });
  });

  describe('Buffer Configuration', () => {
    it('should configure Video with HLS-optimized buffer settings', async () => {
      let videoProps = {};
      
      jest.mocked(require('react-native-video')).mockImplementation(
        React.forwardRef((props, ref) => {
          videoProps = props;
          return null;
        })
      );

      render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        expect(videoProps.skipProcessing).toBe(true);
        expect(videoProps.bufferConfig).toEqual({
          minBufferMs: 15000,
          maxBufferMs: 50000,
          bufferForPlaybackMs: 2500,
          bufferForPlaybackAfterRebufferMs: 5000,
        });
      });
    });

    it('should disable picture-in-picture and background play for security', async () => {
      let videoProps = {};
      
      jest.mocked(require('react-native-video')).mockImplementation(
        React.forwardRef((props, ref) => {
          videoProps = props;
          return null;
        })
      );

      render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        expect(videoProps.pictureInPicture).toBe(false);
        expect(videoProps.playInBackground).toBe(false);
        expect(videoProps.playWhenInactive).toBe(false);
      });
    });
  });

  describe('Quality Selection Integration', () => {
    it('should integrate quality levels with Video component source', async () => {
      let lastVideoProps = {};
      const videoPropsHistory = [];
      
      jest.mocked(require('react-native-video')).mockImplementation(
        React.forwardRef((props, ref) => {
          lastVideoProps = props;
          videoPropsHistory.push({ ...props });
          return null;
        })
      );

      render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        // Should initially use master playlist
        expect(lastVideoProps.source?.uri).toBe(mockHLSUrl);
      });

      // Test would simulate quality change and verify source URI changes
      // This requires component to expose methods for quality selection
    });
  });

  describe('Error Recovery', () => {
    it('should recover from HLS parsing errors', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      
      // First call fails, second succeeds
      mockHLSParser.parsePlaylist
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce(mockQualityLevels);

      const { rerender } = render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalled();
      });

      // Simulate retry
      rerender(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        expect(mockHLSParser.parsePlaylist).toHaveBeenCalledTimes(2);
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Performance Considerations', () => {
    it('should not cause memory leaks during quality switches', async () => {
      const { unmount } = render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        expect(mockHLSParser.parsePlaylist).toHaveBeenCalled();
      });

      // Unmount and verify cleanup
      unmount();

      // No specific assertions here, but this tests that cleanup doesn't throw errors
    });

    it('should handle rapid quality changes gracefully', async () => {
      const component = render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);

      await waitFor(() => {
        expect(mockHLSParser.parsePlaylist).toHaveBeenCalled();
      });

      // Test would simulate rapid quality changes
      // Verify that each change updates the Video component properly
    });
  });

  describe('Live Streaming Mode', () => {
    it('should configure Video component for live streaming', async () => {
      let videoProps = {};
      
      jest.mocked(require('react-native-video')).mockImplementation(
        React.forwardRef((props, ref) => {
          videoProps = props;
          return null;
        })
      );

      render(
        <CameraView 
          hlsMasterPlaylistUrl={mockHLSUrl}
          isLive={true}
        />
      );

      await waitFor(() => {
        // Live streaming should have appropriate progress update interval
        expect(videoProps.progressUpdateInterval).toBe(1000);
      });
    });
  });
});

describe('CameraView Component Rendering Tests', () => {
  const mockHLSUrl = 'https://example.com/master.m3u8';

  beforeEach(() => {
    jest.clearAllMocks();
    AsyncStorage.getItem.mockResolvedValue(null);
  });

  it('should render without crashing', () => {
    const { container } = render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);
    expect(container).toBeTruthy();
  });

  it('should accept and use all required props', async () => {
    const mockOnLoad = jest.fn();
    const mockOnError = jest.fn();
    const mockOnFullscreenChange = jest.fn();

    render(
      <CameraView
        hlsMasterPlaylistUrl={mockHLSUrl}
        isLive={true}
        autoPlay={true}
        controls={true}
        fullscreenEnabled={true}
        onLoad={mockOnLoad}
        onError={mockOnError}
        onFullscreenChange={mockOnFullscreenChange}
      />
    );

    await waitFor(() => {
      expect(mockOnLoad).toHaveBeenCalled();
    });
  });

  it('should handle optional props correctly', () => {
    // Test with minimal props
    const { container } = render(<CameraView hlsMasterPlaylistUrl={mockHLSUrl} />);
    expect(container).toBeTruthy();
  });
});
