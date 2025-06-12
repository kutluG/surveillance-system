import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  StatusBar,
  Alert,
  ActivityIndicator,
  Modal,
  Switch,
} from 'react-native';
import Video from 'react-native-video';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Orientation from 'react-native-orientation-locker';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { COLORS, SIZES, FONTS } from '../constants';
import { HLSParser } from '../utils/hlsParser';

const { width: screenWidth, height: screenHeight } = Dimensions.get('window');

interface CameraViewProps {
  hlsMasterPlaylistUrl: string;
  isLive?: boolean;
  autoPlay?: boolean;
  controls?: boolean;
  fullscreenEnabled?: boolean;
  onFullscreenChange?: (isFullscreen: boolean) => void;
  onError?: (error: any) => void;
  onLoad?: (data: any) => void;
  style?: any;
}

interface QualityLevel {
  bandwidth: number;
  resolution: string;
  url: string;
  label: string;
}

const STORAGE_KEYS = {
  AUTO_QUALITY: 'camera_auto_quality_enabled',
  SELECTED_QUALITY: 'camera_selected_quality',
};

const CameraView: React.FC<CameraViewProps> = ({
  hlsMasterPlaylistUrl,
  isLive = true,
  autoPlay = true,
  controls = true,
  fullscreenEnabled = true,
  onFullscreenChange,
  onError,
  onLoad,
  style,
}) => {
  // Video state
  const [isPlaying, setIsPlaying] = useState(autoPlay);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [buffering, setBuffering] = useState(false);

  // HLS and quality state
  const [qualityLevels, setQualityLevels] = useState<QualityLevel[]>([]);
  const [currentQuality, setCurrentQuality] = useState<string>('auto');
  const [autoQualityEnabled, setAutoQualityEnabled] = useState(true);
  const [showQualityModal, setShowQualityModal] = useState(false);
  const [currentVideoUrl, setCurrentVideoUrl] = useState<string>(hlsMasterPlaylistUrl);

  // Progress state
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [seekableDuration, setSeekableDuration] = useState(0);

  const controlsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const videoRef = useRef<Video>(null);
  const hlsParserRef = useRef<HLSParser | null>(null);

  // Initialize HLS parser and load preferences
  useEffect(() => {
    initializeComponent();
    return () => {
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
    };
  }, []);

  // Parse HLS playlist when URL changes
  useEffect(() => {
    if (hlsMasterPlaylistUrl) {
      parseHLSPlaylist();
    }
  }, [hlsMasterPlaylistUrl]);

  const initializeComponent = async () => {
    try {
      // Load user preferences
      const autoQuality = await AsyncStorage.getItem(STORAGE_KEYS.AUTO_QUALITY);
      const selectedQuality = await AsyncStorage.getItem(STORAGE_KEYS.SELECTED_QUALITY);

      if (autoQuality !== null) {
        setAutoQualityEnabled(JSON.parse(autoQuality));
      }

      if (selectedQuality && autoQuality === 'false') {
        setCurrentQuality(selectedQuality);
      }

      // Initialize HLS parser
      hlsParserRef.current = new HLSParser();
    } catch (error) {
      console.error('Failed to initialize CameraView:', error);
    }
  };

  const parseHLSPlaylist = async () => {
    try {
      if (!hlsParserRef.current) return;

      const qualities = await hlsParserRef.current.parsePlaylist(hlsMasterPlaylistUrl);
      setQualityLevels(qualities);

      // Set initial video URL
      if (!autoQualityEnabled && currentQuality !== 'auto') {
        const selectedLevel = qualities.find(q => q.label === currentQuality);
        if (selectedLevel) {
          setCurrentVideoUrl(selectedLevel.url);
        }
      } else {
        // Use master playlist for auto quality
        setCurrentVideoUrl(hlsMasterPlaylistUrl);
      }
    } catch (error) {
      console.error('Failed to parse HLS playlist:', error);
      // Fallback to master playlist
      setCurrentVideoUrl(hlsMasterPlaylistUrl);
    }
  };

  const saveUserPreferences = async () => {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.AUTO_QUALITY, JSON.stringify(autoQualityEnabled));
      if (!autoQualityEnabled) {
        await AsyncStorage.setItem(STORAGE_KEYS.SELECTED_QUALITY, currentQuality);
      }
    } catch (error) {
      console.error('Failed to save user preferences:', error);
    }
  };

  const handleQualityChange = useCallback((qualityLabel: string) => {
    setCurrentQuality(qualityLabel);
    
    if (qualityLabel === 'auto') {
      setCurrentVideoUrl(hlsMasterPlaylistUrl);
    } else {
      const selectedLevel = qualityLevels.find(q => q.label === qualityLabel);
      if (selectedLevel) {
        setCurrentVideoUrl(selectedLevel.url);
      }
    }
    
    saveUserPreferences();
  }, [qualityLevels, hlsMasterPlaylistUrl]);
  const handleAutoQualityToggle = useCallback((enabled: boolean) => {
    setAutoQualityEnabled(enabled);
    
    if (enabled) {
      setCurrentQuality('auto');
      setCurrentVideoUrl(hlsMasterPlaylistUrl);
    } else if (qualityLevels.length > 0) {
      // Default to medium quality when auto is disabled
      const mediumQuality = qualityLevels.find(q => q.label.includes('360p')) || qualityLevels[0];
      setCurrentQuality(mediumQuality.label);
      setCurrentVideoUrl(mediumQuality.url);
    }
    
    saveUserPreferences();
  }, [qualityLevels, hlsMasterPlaylistUrl]);

  const getCurrentQualityBandwidth = useCallback((): number | undefined => {
    if (autoQualityEnabled || currentQuality === 'auto') {
      return undefined;
    }
    
    const selectedLevel = qualityLevels.find(q => q.label === currentQuality);
    return selectedLevel?.bandwidth;
  }, [autoQualityEnabled, currentQuality, qualityLevels]);

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

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
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

  const onVideoLoad = (data: any) => {
    setIsLoading(false);
    setDuration(data.duration);
    setSeekableDuration(data.duration);
    if (onLoad) {
      onLoad(data);
    }
  };

  const onVideoProgress = (data: any) => {
    setCurrentTime(data.currentTime);
    setSeekableDuration(data.seekableDuration);
  };

  const onVideoError = (error: any) => {
    setHasError(true);
    setIsLoading(false);
    console.error('Video error:', error);
    if (onError) {
      onError(error);
    }
  };

  const onVideoBuffer = ({ isBuffering }: { isBuffering: boolean }) => {
    setBuffering(isBuffering);
  };
  const getVideoSource = () => {
    return {
      uri: currentVideoUrl,
      // Enable HLS adaptive bitrate
      headers: {
        'User-Agent': 'SurveillanceApp/1.0.0',
      },
      // Ensure proper HLS configuration
      type: 'hls',
    };
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const renderVideoContent = () => {
    if (hasError) {
      return (
        <View style={styles.errorContainer}>
          <Icon name="error-outline" size={48} color={COLORS.error} />
          <Text style={styles.errorText}>Failed to load video stream</Text>
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

    return (      <Video
        ref={videoRef}
        source={getVideoSource()}
        style={styles.video}
        resizeMode="contain"
        paused={!isPlaying}
        volume={1.0}
        rate={1.0}
        onLoad={onVideoLoad}
        onProgress={onVideoProgress}
        onError={onVideoError}
        onBuffer={onVideoBuffer}
        testID="video-player"// HLS specific props
        skipProcessing={true}
        bufferConfig={{
          minBufferMs: 15000,
          maxBufferMs: 50000,
          bufferForPlaybackMs: 2500,
          bufferForPlaybackAfterRebufferMs: 5000,
        }}
        // Enable track selection for quality switching
        selectedVideoTrack={{
          type: autoQualityEnabled ? 'auto' : 'resolution',
          value: autoQualityEnabled ? undefined : currentQuality,
        }}
        // Disable picture-in-picture and background play for security
        pictureInPicture={false}
        playInBackground={false}
        playWhenInactive={false}        progressUpdateInterval={1000}
        // Additional HLS optimizations
        maxBitRate={autoQualityEnabled ? undefined : getCurrentQualityBandwidth()}
      />
    );
  };

  const renderQualityModal = () => (
    <Modal
      visible={showQualityModal}
      transparent
      animationType="slide"
      onRequestClose={() => setShowQualityModal(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Video Quality</Text>
          
          <View style={styles.qualitySection}>
            <View style={styles.qualityRow}>
              <Text style={styles.qualityLabel}>Auto Quality</Text>              <Switch
                value={autoQualityEnabled}
                onValueChange={handleAutoQualityToggle}
                trackColor={{ false: COLORS.border, true: COLORS.primary }}
                testID="auto-quality-switch"
              />
            </View>
            <Text style={styles.qualityHint}>
              Automatically adjusts quality based on network conditions
            </Text>
          </View>

          {!autoQualityEnabled && qualityLevels.length > 0 && (
            <View style={styles.qualitySection}>
              <Text style={styles.qualityLabel}>Manual Quality Selection</Text>
              {qualityLevels.map((quality) => (
                <TouchableOpacity
                  key={quality.label}
                  style={[
                    styles.qualityOption,
                    currentQuality === quality.label && styles.qualityOptionSelected,
                  ]}
                  onPress={() => handleQualityChange(quality.label)}
                >
                  <Text
                    style={[
                      styles.qualityOptionText,
                      currentQuality === quality.label && styles.qualityOptionTextSelected,
                    ]}
                  >
                    {quality.label} ({quality.resolution})
                  </Text>
                  <Text style={styles.qualityBandwidth}>
                    {Math.round(quality.bandwidth / 1000)} kbps
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}

          <View style={styles.modalButtons}>
            <TouchableOpacity
              style={styles.modalButton}
              onPress={() => setShowQualityModal(false)}
            >
              <Text style={styles.modalButtonText}>Close</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );

  const renderControls = () => {
    if (!controls || !showControls) {
      return null;
    }

    return (
      <View style={styles.controlsContainer}>
        {(isLoading || buffering) && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={COLORS.white} />
            <Text style={styles.loadingText}>
              {isLoading ? 'Loading...' : 'Buffering...'}
            </Text>
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
          
          <View style={styles.topRightControls}>            <TouchableOpacity
              style={styles.controlButton}
              onPress={() => setShowQualityModal(true)}
              testID="quality-button"
            >
              <Icon name="high-quality" size={24} color={COLORS.white} />
            </TouchableOpacity>
            
            {fullscreenEnabled && (
              <TouchableOpacity
                style={styles.controlButton}
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
              <Text style={styles.timeText}>{formatTime(duration)}</Text>
            </>
          )}

          <View style={styles.qualityIndicator}>
            <Text style={styles.qualityText}>
              {autoQualityEnabled ? 'AUTO' : currentQuality}
            </Text>
          </View>
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
      {renderQualityModal()}
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
    textAlign: 'center',
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
  loadingText: {
    ...FONTS.body4,
    color: COLORS.white,
    marginTop: SIZES.base,
  },
  topControls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: SIZES.padding,
    paddingTop: SIZES.padding,
  },
  topRightControls: {
    flexDirection: 'row',
    alignItems: 'center',
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
  controlButton: {
    padding: SIZES.base,
    marginLeft: SIZES.base,
  },
  centerPlayButton: {
    position: 'absolute',
    alignSelf: 'center',
    top: '50%',
    transform: [{ translateY: -30 }],
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    borderRadius: 30,
    width: 60,
    height: 60,
    justifyContent: 'center',
    alignItems: 'center',
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
  qualityIndicator: {
    marginLeft: 'auto',
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    paddingHorizontal: SIZES.base,
    paddingVertical: 4,
    borderRadius: SIZES.radius / 2,
  },
  qualityText: {
    ...FONTS.caption,
    color: COLORS.white,
    fontWeight: 'bold',
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius * 2,
    padding: SIZES.padding,
    width: '90%',
    maxWidth: 400,
  },
  modalTitle: {
    ...FONTS.h3,
    color: COLORS.text,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: SIZES.padding,
  },
  qualitySection: {
    marginBottom: SIZES.padding,
  },
  qualityRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.base,
  },
  qualityLabel: {
    ...FONTS.body3,
    color: COLORS.text,
    fontWeight: 'bold',
  },
  qualityHint: {
    ...FONTS.body4,
    color: COLORS.textSecondary,
    fontStyle: 'italic',
  },
  qualityOption: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: SIZES.base,
    paddingHorizontal: SIZES.padding,
    marginVertical: 2,
    borderRadius: SIZES.radius,
    backgroundColor: COLORS.background,
  },
  qualityOptionSelected: {
    backgroundColor: COLORS.primary,
  },
  qualityOptionText: {
    ...FONTS.body4,
    color: COLORS.text,
  },
  qualityOptionTextSelected: {
    color: COLORS.white,
    fontWeight: 'bold',
  },
  qualityBandwidth: {
    ...FONTS.caption,
    color: COLORS.textSecondary,
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: SIZES.padding,
  },
  modalButton: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: SIZES.padding * 2,
    paddingVertical: SIZES.base,
    borderRadius: SIZES.radius,
  },
  modalButtonText: {
    ...FONTS.body3,
    color: COLORS.white,
    fontWeight: 'bold',
  },
});

export default CameraView;
