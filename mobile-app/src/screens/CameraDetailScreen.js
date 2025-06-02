import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
  Modal,
  TextInput,
  Switch,
  Dimensions,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { useFocusEffect } from '@react-navigation/native';
import {
  fetchCameraById,
  updateCameraSettings,
  toggleCameraRecording,
  requestCameraSnapshot,
  selectCameraById,
  selectCamerasLoading,
  selectCamerasError,
} from '../store/slices/camerasSlice';
import { COLORS, SIZES, FONTS, CAMERA_STATUS } from '../constants';
import { formatDateTime } from '../utils/dateUtils';
import Card from '../components/Card';
import Button from '../components/Button';

const { width: screenWidth, height: screenHeight } = Dimensions.get('window');

const CameraDetailScreen = ({ route, navigation }) => {
  const { cameraId } = route.params;
  const dispatch = useDispatch();
  
  const camera = useSelector(state => selectCameraById(state, cameraId));
  const loading = useSelector(selectCamerasLoading);
  const error = useSelector(selectCamerasError);

  const [settingsModalVisible, setSettingsModalVisible] = useState(false);
  const [recordingModalVisible, setRecordingModalVisible] = useState(false);
  const [snapshotModalVisible, setSnapshotModalVisible] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [videoError, setVideoError] = useState(false);

  // Camera settings state
  const [settings, setSettings] = useState({
    name: '',
    description: '',
    enableMotionDetection: false,
    enablePersonDetection: false,
    enableVehicleDetection: false,
    recordingEnabled: false,
    alertsEnabled: false,
    sensitivity: 50,
    recordingQuality: 'high',
  });

  useFocusEffect(
    useCallback(() => {
      if (cameraId) {
        dispatch(fetchCameraById(cameraId));
      }
    }, [dispatch, cameraId])
  );

  useEffect(() => {
    if (camera) {
      setSettings({
        name: camera.name || '',
        description: camera.description || '',
        enableMotionDetection: camera.enableMotionDetection || false,
        enablePersonDetection: camera.enablePersonDetection || false,
        enableVehicleDetection: camera.enableVehicleDetection || false,
        recordingEnabled: camera.recordingEnabled || false,
        alertsEnabled: camera.alertsEnabled || false,
        sensitivity: camera.sensitivity || 50,
        recordingQuality: camera.recordingQuality || 'high',
      });
      
      // Set navigation title
      navigation.setOptions({
        title: camera.name || 'Camera Details',
      });
    }
  }, [camera, navigation]);

  const handleRefresh = useCallback(() => {
    if (cameraId) {
      dispatch(fetchCameraById(cameraId));
    }
  }, [dispatch, cameraId]);

  const handleSaveSettings = async () => {
    try {
      await dispatch(updateCameraSettings({ cameraId, settings })).unwrap();
      setSettingsModalVisible(false);
      Alert.alert('Success', 'Camera settings updated successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to update camera settings');
    }
  };

  const handleToggleRecording = async () => {
    try {
      await dispatch(toggleCameraRecording(cameraId)).unwrap();
      Alert.alert('Success', `Recording ${camera.recordingEnabled ? 'stopped' : 'started'}`);
    } catch (error) {
      Alert.alert('Error', 'Failed to toggle recording');
    }
  };

  const handleTakeSnapshot = async () => {
    try {
      await dispatch(requestCameraSnapshot(cameraId)).unwrap();
      setSnapshotModalVisible(true);
      Alert.alert('Success', 'Snapshot captured successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to capture snapshot');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case CAMERA_STATUS.ONLINE:
        return COLORS.success;
      case CAMERA_STATUS.OFFLINE:
        return COLORS.error;
      case CAMERA_STATUS.RECORDING:
        return COLORS.warning;
      case CAMERA_STATUS.ERROR:
        return COLORS.error;
      default:
        return COLORS.textSecondary;
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case CAMERA_STATUS.ONLINE:
        return '🟢';
      case CAMERA_STATUS.OFFLINE:
        return '🔴';
      case CAMERA_STATUS.RECORDING:
        return '🔴';
      case CAMERA_STATUS.ERROR:
        return '⚠️';
      default:
        return '⚫';
    }
  };

  const renderVideoPlayer = () => (
    <TouchableOpacity
      style={[
        styles.videoContainer,
        isFullscreen && styles.fullscreenVideo,
      ]}
      onPress={() => setIsFullscreen(!isFullscreen)}
    >
      {videoError ? (
        <View style={styles.videoError}>
          <Text style={styles.videoErrorText}>📷</Text>
          <Text style={styles.videoErrorMessage}>
            Unable to load video stream
          </Text>
          <Button
            title="Retry"
            size="small"
            onPress={() => setVideoError(false)}
          />
        </View>
      ) : (
        <View style={styles.videoPlaceholder}>
          <Text style={styles.videoPlaceholderText}>📹</Text>
          <Text style={styles.videoPlaceholderMessage}>
            Live Video Stream
          </Text>
          <Text style={styles.videoPlaceholderHint}>
            Tap to {isFullscreen ? 'exit' : 'enter'} fullscreen
          </Text>
        </View>
      )}
      
      {/* Video Controls Overlay */}
      <View style={styles.videoControls}>
        <View style={styles.statusIndicator}>
          <Text style={styles.statusIcon}>
            {getStatusIcon(camera?.status)}
          </Text>
          <Text style={[
            styles.statusText,
            { color: getStatusColor(camera?.status) }
          ]}>
            {camera?.status?.toUpperCase()}
          </Text>
        </View>
        
        {camera?.recordingEnabled && (
          <View style={styles.recordingIndicator}>
            <Text style={styles.recordingIcon}>🔴</Text>
            <Text style={styles.recordingText}>REC</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );

  const renderSettingsModal = () => (
    <Modal
      visible={settingsModalVisible}
      transparent
      animationType="slide"
      onRequestClose={() => setSettingsModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Camera Settings</Text>
          
          <ScrollView style={styles.settingsContent}>
            <View style={styles.settingSection}>
              <Text style={styles.settingLabel}>Camera Name</Text>
              <TextInput
                style={styles.settingInput}
                value={settings.name}
                onChangeText={(text) => setSettings({ ...settings, name: text })}
                placeholder="Enter camera name"
                placeholderTextColor={COLORS.textSecondary}
              />
            </View>

            <View style={styles.settingSection}>
              <Text style={styles.settingLabel}>Description</Text>
              <TextInput
                style={[styles.settingInput, styles.settingTextArea]}
                value={settings.description}
                onChangeText={(text) => setSettings({ ...settings, description: text })}
                placeholder="Enter camera description"
                placeholderTextColor={COLORS.textSecondary}
                multiline
                numberOfLines={3}
              />
            </View>

            <View style={styles.settingSection}>
              <View style={styles.settingRow}>
                <Text style={styles.settingLabel}>Motion Detection</Text>
                <Switch
                  value={settings.enableMotionDetection}
                  onValueChange={(value) => 
                    setSettings({ ...settings, enableMotionDetection: value })
                  }
                  trackColor={{ false: COLORS.border, true: COLORS.primary }}
                />
              </View>
            </View>

            <View style={styles.settingSection}>
              <View style={styles.settingRow}>
                <Text style={styles.settingLabel}>Person Detection</Text>
                <Switch
                  value={settings.enablePersonDetection}
                  onValueChange={(value) => 
                    setSettings({ ...settings, enablePersonDetection: value })
                  }
                  trackColor={{ false: COLORS.border, true: COLORS.primary }}
                />
              </View>
            </View>

            <View style={styles.settingSection}>
              <View style={styles.settingRow}>
                <Text style={styles.settingLabel}>Vehicle Detection</Text>
                <Switch
                  value={settings.enableVehicleDetection}
                  onValueChange={(value) => 
                    setSettings({ ...settings, enableVehicleDetection: value })
                  }
                  trackColor={{ false: COLORS.border, true: COLORS.primary }}
                />
              </View>
            </View>

            <View style={styles.settingSection}>
              <View style={styles.settingRow}>
                <Text style={styles.settingLabel}>Recording Enabled</Text>
                <Switch
                  value={settings.recordingEnabled}
                  onValueChange={(value) => 
                    setSettings({ ...settings, recordingEnabled: value })
                  }
                  trackColor={{ false: COLORS.border, true: COLORS.primary }}
                />
              </View>
            </View>

            <View style={styles.settingSection}>
              <View style={styles.settingRow}>
                <Text style={styles.settingLabel}>Alerts Enabled</Text>
                <Switch
                  value={settings.alertsEnabled}
                  onValueChange={(value) => 
                    setSettings({ ...settings, alertsEnabled: value })
                  }
                  trackColor={{ false: COLORS.border, true: COLORS.primary }}
                />
              </View>
            </View>

            <View style={styles.settingSection}>
              <Text style={styles.settingLabel}>
                Detection Sensitivity: {settings.sensitivity}%
              </Text>
              <View style={styles.sliderContainer}>
                <Text style={styles.sliderLabel}>Low</Text>
                <View style={styles.sliderTrack}>
                  <View
                    style={[
                      styles.sliderFill,
                      { width: `${settings.sensitivity}%` }
                    ]}
                  />
                  <TouchableOpacity
                    style={[
                      styles.sliderThumb,
                      { left: `${settings.sensitivity - 2}%` }
                    ]}
                  />
                </View>
                <Text style={styles.sliderLabel}>High</Text>
              </View>
            </View>
          </ScrollView>

          <View style={styles.modalButtons}>
            <Button
              title="Cancel"
              variant="outline"
              onPress={() => setSettingsModalVisible(false)}
              style={styles.modalButton}
            />
            <Button
              title="Save"
              onPress={handleSaveSettings}
              style={styles.modalButton}
            />
          </View>
        </View>
      </View>
    </Modal>
  );

  if (loading && !camera) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading camera details...</Text>
      </View>
    );
  }

  if (error || !camera) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>Failed to load camera details</Text>
        <Button title="Retry" onPress={handleRefresh} />
      </View>
    );
  }

  if (isFullscreen) {
    return (
      <View style={styles.fullscreenContainer}>
        {renderVideoPlayer()}
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={loading} onRefresh={handleRefresh} />
      }
    >
      {/* Video Stream */}
      {renderVideoPlayer()}

      {/* Quick Actions */}
      <Card style={styles.actionsCard}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <View style={styles.actionsContainer}>
          <Button
            title={camera.recordingEnabled ? "Stop Recording" : "Start Recording"}
            variant={camera.recordingEnabled ? "outline" : "primary"}
            onPress={handleToggleRecording}
            style={styles.actionButton}
          />
          <Button
            title="Take Snapshot"
            variant="outline"
            onPress={handleTakeSnapshot}
            style={styles.actionButton}
          />
          <Button
            title="Settings"
            variant="outline"
            onPress={() => setSettingsModalVisible(true)}
            style={styles.actionButton}
          />
        </View>
      </Card>

      {/* Camera Information */}
      <Card style={styles.infoCard}>
        <Text style={styles.sectionTitle}>Camera Information</Text>
        
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Status:</Text>
          <View style={styles.statusContainer}>
            <Text style={styles.statusIcon}>
              {getStatusIcon(camera.status)}
            </Text>
            <Text style={[
              styles.statusText,
              { color: getStatusColor(camera.status) }
            ]}>
              {camera.status?.toUpperCase()}
            </Text>
          </View>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Location:</Text>
          <Text style={styles.infoValue}>{camera.location || 'Not specified'}</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>IP Address:</Text>
          <Text style={styles.infoValue}>{camera.ipAddress || 'N/A'}</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Resolution:</Text>
          <Text style={styles.infoValue}>{camera.resolution || 'N/A'}</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Last Activity:</Text>
          <Text style={styles.infoValue}>
            {camera.lastActivity ? formatDateTime(camera.lastActivity) : 'N/A'}
          </Text>
        </View>
      </Card>

      {/* Detection Settings */}
      <Card style={styles.detectionCard}>
        <Text style={styles.sectionTitle}>Detection Settings</Text>
        
        <View style={styles.detectionItem}>
          <Text style={styles.detectionLabel}>Motion Detection</Text>
          <Text style={[
            styles.detectionStatus,
            { color: camera.enableMotionDetection ? COLORS.success : COLORS.textSecondary }
          ]}>
            {camera.enableMotionDetection ? 'Enabled' : 'Disabled'}
          </Text>
        </View>

        <View style={styles.detectionItem}>
          <Text style={styles.detectionLabel}>Person Detection</Text>
          <Text style={[
            styles.detectionStatus,
            { color: camera.enablePersonDetection ? COLORS.success : COLORS.textSecondary }
          ]}>
            {camera.enablePersonDetection ? 'Enabled' : 'Disabled'}
          </Text>
        </View>

        <View style={styles.detectionItem}>
          <Text style={styles.detectionLabel}>Vehicle Detection</Text>
          <Text style={[
            styles.detectionStatus,
            { color: camera.enableVehicleDetection ? COLORS.success : COLORS.textSecondary }
          ]}>
            {camera.enableVehicleDetection ? 'Enabled' : 'Disabled'}
          </Text>
        </View>

        <View style={styles.detectionItem}>
          <Text style={styles.detectionLabel}>Recording</Text>
          <Text style={[
            styles.detectionStatus,
            { color: camera.recordingEnabled ? COLORS.warning : COLORS.textSecondary }
          ]}>
            {camera.recordingEnabled ? 'Active' : 'Inactive'}
          </Text>
        </View>
      </Card>

      {renderSettingsModal()}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: COLORS.text,
    ...FONTS.body3,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: SIZES.padding,
  },
  errorText: {
    color: COLORS.error,
    ...FONTS.body3,
    textAlign: 'center',
    marginBottom: SIZES.margin,
  },
  fullscreenContainer: {
    flex: 1,
    backgroundColor: COLORS.black,
  },
  videoContainer: {
    height: 250,
    backgroundColor: COLORS.black,
    margin: SIZES.margin,
    borderRadius: SIZES.radius,
    overflow: 'hidden',
    position: 'relative',
  },
  fullscreenVideo: {
    height: screenHeight,
    margin: 0,
    borderRadius: 0,
  },
  videoPlaceholder: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.surface,
  },
  videoPlaceholderText: {
    fontSize: 48,
    marginBottom: SIZES.margin,
  },
  videoPlaceholderMessage: {
    color: COLORS.text,
    ...FONTS.h3,
    fontWeight: 'bold',
    marginBottom: SIZES.margin / 2,
  },
  videoPlaceholderHint: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
  },
  videoError: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.surface,
  },
  videoErrorText: {
    fontSize: 48,
    marginBottom: SIZES.margin,
  },
  videoErrorMessage: {
    color: COLORS.error,
    ...FONTS.body3,
    marginBottom: SIZES.margin,
  },
  videoControls: {
    position: 'absolute',
    top: SIZES.padding,
    left: SIZES.padding,
    right: SIZES.padding,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: SIZES.padding / 2,
    paddingVertical: 4,
    borderRadius: SIZES.radius,
  },
  statusIcon: {
    marginRight: 4,
  },
  statusText: {
    ...FONTS.body5,
    fontWeight: 'bold',
  },
  recordingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 0, 0, 0.8)',
    paddingHorizontal: SIZES.padding / 2,
    paddingVertical: 4,
    borderRadius: SIZES.radius,
  },
  recordingIcon: {
    marginRight: 4,
  },
  recordingText: {
    color: COLORS.white,
    ...FONTS.body5,
    fontWeight: 'bold',
  },
  actionsCard: {
    margin: SIZES.margin,
    padding: SIZES.padding,
  },
  sectionTitle: {
    color: COLORS.text,
    ...FONTS.h3,
    fontWeight: 'bold',
    marginBottom: SIZES.margin,
  },
  actionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  actionButton: {
    width: '48%',
    marginBottom: SIZES.margin / 2,
  },
  infoCard: {
    margin: SIZES.margin,
    marginTop: 0,
    padding: SIZES.padding,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.margin,
  },
  infoLabel: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
    flex: 1,
  },
  infoValue: {
    color: COLORS.text,
    ...FONTS.body4,
    flex: 2,
    textAlign: 'right',
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 2,
    justifyContent: 'flex-end',
  },
  detectionCard: {
    margin: SIZES.margin,
    marginTop: 0,
    padding: SIZES.padding,
  },
  detectionItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.margin,
  },
  detectionLabel: {
    color: COLORS.text,
    ...FONTS.body4,
  },
  detectionStatus: {
    ...FONTS.body4,
    fontWeight: 'bold',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: COLORS.surface,
    borderTopLeftRadius: SIZES.radius * 2,
    borderTopRightRadius: SIZES.radius * 2,
    maxHeight: '90%',
  },
  modalTitle: {
    color: COLORS.text,
    ...FONTS.h3,
    fontWeight: 'bold',
    textAlign: 'center',
    padding: SIZES.padding,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  settingsContent: {
    maxHeight: 400,
    padding: SIZES.padding,
  },
  settingSection: {
    marginBottom: SIZES.margin * 1.5,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  settingLabel: {
    color: COLORS.text,
    ...FONTS.body3,
    fontWeight: 'bold',
    marginBottom: SIZES.margin / 2,
  },
  settingInput: {
    backgroundColor: COLORS.background,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
    color: COLORS.text,
    ...FONTS.body4,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  settingTextArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  sliderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: SIZES.margin / 2,
  },
  sliderLabel: {
    color: COLORS.textSecondary,
    ...FONTS.body5,
    width: 30,
  },
  sliderTrack: {
    flex: 1,
    height: 4,
    backgroundColor: COLORS.border,
    borderRadius: 2,
    marginHorizontal: SIZES.margin,
    position: 'relative',
  },
  sliderFill: {
    height: 4,
    backgroundColor: COLORS.primary,
    borderRadius: 2,
  },
  sliderThumb: {
    position: 'absolute',
    top: -6,
    width: 16,
    height: 16,
    backgroundColor: COLORS.primary,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: COLORS.white,
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: SIZES.padding,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
  },
  modalButton: {
    flex: 1,
    marginHorizontal: SIZES.margin / 2,
  },
});

export default CameraDetailScreen;
