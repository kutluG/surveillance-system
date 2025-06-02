import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  StatusBar,
  Alert,
  ActivityIndicator,
} from 'react-native';
import Video from 'react-native-video';
import Orientation from 'react-native-orientation-locker';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { COLORS, SIZES, FONTS } from '../constants';

const { width: screenWidth, height: screenHeight } = Dimensions.get('window');

const VideoPlayer = ({
  source,
  isLive = false,
  autoPlay = true,
  controls = true,
  fullscreenEnabled = true,
  onFullscreenChange,
  onError,
  onLoad,
  style,
}) => {
  const [isPlaying, setIsPlaying] = useState(autoPlay);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1.0);
  const [isMuted, setIsMuted] = useState(false);
  const [buffering, setBuffering] = useState(false);
  const [quality, setQuality] = useState('auto');

  const controlsTimeoutRef = useRef(null);
  const playerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!isLive && isPlaying && !isLoading && !hasError) {
      const interval = setInterval(() => {
        setCurrentTime(prev => {
          const newTime = prev + 1;
          if (newTime >= duration && duration > 0) {
            setIsPlaying(false);
            return duration;
          }
          return newTime;
        });
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [isPlaying, isLoading, hasError, duration, isLive]);

  const hideControlsAfterDelay = () => {
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    controlsTimeoutRef.current = setTimeout(() => {
      setShowControls(false);
    }, 3000);
  };

  const handlePlayPause = () => {
    if (isLive) {
      // For live streams, we just simulate play/pause
      setIsPlaying(!isPlaying);
    } else {
      setIsPlaying(!isPlaying);
    }
    showControlsTemporarily();
  };

  const handleSeek = (position) => {
    if (!isLive) {
      setCurrentTime(Math.max(0, Math.min(duration, position)));
    }
  };

  const handleMute = () => {
    setIsMuted(!isMuted);
    showControlsTemporarily();
  };

  const handleFullscreen = () => {
    const newFullscreenState = !isFullscreen;
    setIsFullscreen(newFullscreenState);
    
    if (onFullscreenChange) {
      onFullscreenChange(newFullscreenState);
    }
    
    showControlsTemporarily();
  };

  const showControlsTemporarily = () => {
    setShowControls(true);
    hideControlsAfterDelay();
  };

  const handleVideoPress = () => {
    showControlsTemporarily();
  };

  const handleError = (error) => {
    setHasError(true);
    setIsLoading(false);
    if (onError) {
      onError(error);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const renderVideoContent = () => {
    if (isLoading) {
      return (
        <View style={styles.videoPlaceholder}>
          <Text style={styles.loadingIcon}>⏳</Text>
          <Text style={styles.loadingText}>Loading video...</Text>
        </View>
      );
    }

    if (hasError) {
      return (
        <View style={styles.videoPlaceholder}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={styles.errorText}>Failed to load video</Text>
          <TouchableOpacity
            style={styles.retryButton}
            onPress={() => {
              setHasError(false);
              setIsLoading(true);
            }}
          >
            <Text style={styles.retryButtonText}>Retry</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return (
      <View style={styles.videoPlaceholder}>
        <Text style={styles.videoIcon}>
          {isLive ? '📡' : '📹'}
        </Text>
        <Text style={styles.videoText}>
          {isLive ? 'Live Video Stream' : 'Video Playback'}
        </Text>
        {!isPlaying && (
          <TouchableOpacity style={styles.playOverlay} onPress={handlePlayPause}>
            <Text style={styles.playIcon}>▶️</Text>
          </TouchableOpacity>
        )}
        {isLive && (
          <View style={styles.liveIndicator}>
            <Text style={styles.liveText}>🔴 LIVE</Text>
          </View>
        )}
      </View>
    );
  };

  const renderControls = () => {
    if (!controls || !showControls) return null;

    return (
      <View style={styles.controlsContainer}>
        {/* Top Controls */}
        <View style={styles.topControls}>
          {isLive && (
            <View style={styles.liveIndicator}>
              <Text style={styles.liveText}>🔴 LIVE</Text>
            </View>
          )}
          <View style={styles.spacer} />
          {fullscreenEnabled && (
            <TouchableOpacity style={styles.controlButton} onPress={handleFullscreen}>
              <Text style={styles.controlIcon}>
                {isFullscreen ? '⛶' : '⛶'}
              </Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Bottom Controls */}
        <View style={styles.bottomControls}>
          <TouchableOpacity style={styles.controlButton} onPress={handlePlayPause}>
            <Text style={styles.controlIcon}>
              {isPlaying ? '⏸️' : '▶️'}
            </Text>
          </TouchableOpacity>

          {!isLive && (
            <>
              <Text style={styles.timeText}>{formatTime(currentTime)}</Text>
              <View style={styles.progressContainer}>
                <View style={styles.progressTrack}>
                  <View
                    style={[
                      styles.progressFill,
                      { width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }
                    ]}
                  />
                  <TouchableOpacity
                    style={[
                      styles.progressThumb,
                      { left: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }
                    ]}
                    onPress={() => {
                      // Handle seek gesture
                    }}
                  />
                </View>
              </View>
              <Text style={styles.timeText}>{formatTime(duration)}</Text>
            </>
          )}

          <TouchableOpacity style={styles.controlButton} onPress={handleMute}>
            <Text style={styles.controlIcon}>
              {isMuted ? '🔇' : '🔊'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  const containerStyle = [
    styles.container,
    style,
    isFullscreen && styles.fullscreenContainer,
  ];

  return (
    <View style={containerStyle}>
      {isFullscreen && <StatusBar hidden />}
      
      <TouchableOpacity
        style={styles.videoContainer}
        onPress={handleVideoPress}
        activeOpacity={1}
      >
        {renderVideoContent()}
        {renderControls()}
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: COLORS.black,
    borderRadius: SIZES.radius,
    overflow: 'hidden',
  },
  fullscreenContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: screenWidth,
    height: screenHeight,
    borderRadius: 0,
    zIndex: 1000,
  },
  videoContainer: {
    width: '100%',
    height: '100%',
    minHeight: 200,
    position: 'relative',
  },
  videoPlaceholder: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.surface,
  },
  loadingIcon: {
    fontSize: 48,
    marginBottom: SIZES.margin,
  },
  loadingText: {
    color: COLORS.text,
    ...FONTS.body3,
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: SIZES.margin,
  },
  errorText: {
    color: COLORS.error,
    ...FONTS.body3,
    marginBottom: SIZES.margin,
  },
  retryButton: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: SIZES.padding,
    paddingVertical: SIZES.padding / 2,
    borderRadius: SIZES.radius,
  },
  retryButtonText: {
    color: COLORS.white,
    ...FONTS.body4,
    fontWeight: 'bold',
  },
  videoIcon: {
    fontSize: 64,
    marginBottom: SIZES.margin,
  },
  videoText: {
    color: COLORS.text,
    ...FONTS.h3,
    textAlign: 'center',
  },
  playOverlay: {
    position: 'absolute',
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  playIcon: {
    fontSize: 32,
  },
  liveIndicator: {
    backgroundColor: COLORS.error,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  liveText: {
    color: COLORS.white,
    ...FONTS.body5,
    fontWeight: 'bold',
  },
  controlsContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'space-between',
    padding: SIZES.padding,
  },
  topControls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  bottomControls: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingVertical: SIZES.padding / 2,
    paddingHorizontal: SIZES.padding,
    borderRadius: SIZES.radius,
  },
  spacer: {
    flex: 1,
  },
  controlButton: {
    padding: SIZES.padding / 2,
    marginHorizontal: 4,
  },
  controlIcon: {
    fontSize: 24,
  },
  timeText: {
    color: COLORS.white,
    ...FONTS.body5,
    marginHorizontal: SIZES.margin / 2,
    minWidth: 40,
    textAlign: 'center',
  },
  progressContainer: {
    flex: 1,
    marginHorizontal: SIZES.margin,
  },
  progressTrack: {
    height: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: 2,
    position: 'relative',
  },
  progressFill: {
    height: 4,
    backgroundColor: COLORS.primary,
    borderRadius: 2,
  },
  progressThumb: {
    position: 'absolute',
    top: -6,
    width: 16,
    height: 16,
    backgroundColor: COLORS.primary,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: COLORS.white,
  },
});

export default VideoPlayer;
