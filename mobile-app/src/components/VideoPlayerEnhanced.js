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
  Platform,
} from 'react-native';
import Video from 'react-native-video';
import Orientation from 'react-native-orientation-locker';
import Icon from 'react-native-vector-icons/MaterialIcons';
import Slider from '@react-native-community/slider';
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
  const [seekableDuration, setSeekableDuration] = useState(0);

  const controlsTimeoutRef = useRef(null);
  const videoRef = useRef(null);

  useEffect(() => {
    return () => {
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
    };
  }, []);

  const hideControlsAfterDelay = () => {
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    controlsTimeoutRef.current = setTimeout(() => {
      setShowControls(false);
    }, 3000);
  };

  const showControlsTemporarily = () => {
    setShowControls(true);
    hideControlsAfterDelay();
  };

  const onVideoLoad = (data) => {
    setIsLoading(false);
    setDuration(data.duration);
    setSeekableDuration(data.duration);
    if (onLoad) {
      onLoad(data);
    }
  };

  const onVideoProgress = (data) => {
    setCurrentTime(data.currentTime);
    setSeekableDuration(data.seekableDuration);
  };

  const onVideoError = (error) => {
    setHasError(true);
    setIsLoading(false);
    console.error('Video error:', error);
    if (onError) {
      onError(error);
    }
  };

  const onVideoBuffer = ({ isBuffering }) => {
    setBuffering(isBuffering);
  };

  const onVideoEnd = () => {
    if (!isLive) {
      setIsPlaying(false);
      setCurrentTime(0);
    }
  };

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
    showControlsTemporarily();
  };

  const handleSeek = (value) => {
    if (!isLive && videoRef.current) {
      videoRef.current.seek(value);
      setCurrentTime(value);
    }
  };

  const handleMute = () => {
    setIsMuted(!isMuted);
    showControlsTemporarily();
  };

  const handleFullscreen = () => {
    const newFullscreenState = !isFullscreen;
    setIsFullscreen(newFullscreenState);
    
    if (newFullscreenState) {
      Orientation.lockToLandscape();
      StatusBar.setHidden(true);
    } else {
      Orientation.lockToPortrait();
      StatusBar.setHidden(false);
    }
    
    if (onFullscreenChange) {
      onFullscreenChange(newFullscreenState);
    }
    
    showControlsTemporarily();
  };

  const handleVideoPress = () => {
    showControlsTemporarily();
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getVideoSource = () => {
    if (typeof source === 'string') {
      return { uri: source };
    }
    return source;
  };

  const renderVideoContent = () => {
    if (hasError) {
      return (
        <View style={styles.errorContainer}>
          <Icon name="error-outline" size={48} color={COLORS.error} />
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
      <Video
        ref={videoRef}
        source={getVideoSource()}
        style={styles.video}
        resizeMode="contain"
        paused={!isPlaying}
        volume={isMuted ? 0 : volume}
        rate={1.0}
        onLoad={onVideoLoad}
        onProgress={onVideoProgress}
        onError={onVideoError}
        onBuffer={onVideoBuffer}
        onEnd={onVideoEnd}
        poster={Platform.OS === 'ios' ? undefined : ''}
        pictureInPicture={false}
        playInBackground={false}
        playWhenInactive={false}
        ignoreSilentSwitch="ignore"
        mixWithOthers="mix"
        progressUpdateInterval={1000}
      />
    );
  };

  const renderControls = () => {
    if (!controls || !showControls) {
      return null;
    }

    return (
      <View style={styles.controlsContainer}>
        {(isLoading || buffering) && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={COLORS.white} />
          </View>
        )}
        
        {/* Top controls */}
        <View style={styles.topControls}>
          {isLive && (
            <View style={styles.liveIndicator}>
              <View style={styles.liveDot} />
              <Text style={styles.liveText}>LIVE</Text>
            </View>
          )}
          
          {fullscreenEnabled && (
            <TouchableOpacity
              style={styles.fullscreenButton}
              onPress={handleFullscreen}
            >
              <Icon 
                name={isFullscreen ? "fullscreen-exit" : "fullscreen"} 
                size={24} 
                color={COLORS.white} 
              />
            </TouchableOpacity>
          )}
        </View>

        {/* Center play/pause button */}
        {!isPlaying && !isLoading && !buffering && (
          <TouchableOpacity
            style={styles.centerPlayButton}
            onPress={handlePlayPause}
          >
            <Icon name="play-arrow" size={60} color={COLORS.white} />
          </TouchableOpacity>
        )}

        {/* Bottom controls */}
        <View style={styles.bottomControls}>
          <TouchableOpacity
            style={styles.playPauseButton}
            onPress={handlePlayPause}
          >
            <Icon 
              name={isPlaying ? "pause" : "play-arrow"} 
              size={24} 
              color={COLORS.white} 
            />
          </TouchableOpacity>

          {!isLive && (
            <>
              <Text style={styles.timeText}>{formatTime(currentTime)}</Text>
              
              <Slider
                style={styles.progressSlider}
                minimumValue={0}
                maximumValue={seekableDuration}
                value={currentTime}
                onValueChange={handleSeek}
                minimumTrackTintColor={COLORS.primary}
                maximumTrackTintColor={COLORS.gray}
                thumbStyle={styles.sliderThumb}
              />
              
              <Text style={styles.timeText}>{formatTime(duration)}</Text>
            </>
          )}

          <TouchableOpacity
            style={styles.muteButton}
            onPress={handleMute}
          >
            <Icon 
              name={isMuted ? "volume-off" : "volume-up"} 
              size={24} 
              color={COLORS.white} 
            />
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  const containerStyle = [
    styles.container,
    isFullscreen && styles.fullscreenContainer,
    style,
  ];

  return (
    <TouchableOpacity 
      style={containerStyle} 
      onPress={handleVideoPress}
      activeOpacity={1}
    >
      {renderVideoContent()}
      {renderControls()}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: COLORS.black,
    borderRadius: SIZES.radius,
    overflow: 'hidden',
    aspectRatio: 16 / 9,
  },
  fullscreenContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: screenWidth,
    height: screenHeight,
    zIndex: 1000,
    borderRadius: 0,
  },
  video: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.surface,
  },
  errorText: {
    ...FONTS.body3,
    color: COLORS.error,
    marginTop: SIZES.base,
    marginBottom: SIZES.padding,
  },
  retryButton: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: SIZES.padding,
    paddingVertical: SIZES.base,
    borderRadius: SIZES.radius,
  },
  retryButtonText: {
    ...FONTS.body3,
    color: COLORS.white,
  },
  controlsContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'space-between',
  },
  loadingContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  topControls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: SIZES.padding,
    paddingTop: SIZES.padding,
  },
  liveIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.error,
    paddingHorizontal: SIZES.base,
    paddingVertical: SIZES.base / 2,
    borderRadius: SIZES.radius,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: COLORS.white,
    marginRight: SIZES.base / 2,
  },
  liveText: {
    ...FONTS.caption,
    color: COLORS.white,
    fontWeight: 'bold',
  },
  fullscreenButton: {
    padding: SIZES.base,
  },
  centerPlayButton: {
    position: 'absolute',
    alignSelf: 'center',
    top: '50%',
    transform: [{ translateY: -30 }],
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    borderRadius: 30,
    padding: SIZES.padding,
  },
  bottomControls: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: SIZES.padding,
    paddingBottom: SIZES.padding,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
  },
  playPauseButton: {
    padding: SIZES.base,
  },
  timeText: {
    ...FONTS.caption,
    color: COLORS.white,
    marginHorizontal: SIZES.base,
    minWidth: 40,
  },
  progressSlider: {
    flex: 1,
    height: 40,
  },
  sliderThumb: {
    width: 12,
    height: 12,
    backgroundColor: COLORS.primary,
  },
  muteButton: {
    padding: SIZES.base,
  },
});

export default VideoPlayer;
