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
  Dimensions,
  Share,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { useFocusEffect } from '@react-navigation/native';
import {
  fetchAlertById,
  acknowledgeAlert,
  clearAlert,
  selectAlertById,
  selectAlertsLoading,
  selectAlertsError,
} from '../store/slices/alertsSlice';
import { COLORS, SIZES, FONTS, ALERT_TYPES, ALERT_PRIORITIES } from '../constants';
import { formatDateTime, formatRelativeTime } from '../utils/dateUtils';
import Card from '../components/Card';
import Button from '../components/Button';

const { width: screenWidth, height: screenHeight } = Dimensions.get('window');

const AlertDetailScreen = ({ route, navigation }) => {
  const { alertId } = route.params;
  const dispatch = useDispatch();
  
  const alert = useSelector(state => selectAlertById(state, alertId));
  const loading = useSelector(selectAlertsLoading);
  const error = useSelector(selectAlertsError);

  const [imageModalVisible, setImageModalVisible] = useState(false);
  const [videoModalVisible, setVideoModalVisible] = useState(false);

  useFocusEffect(
    useCallback(() => {
      if (alertId) {
        dispatch(fetchAlertById(alertId));
      }
    }, [dispatch, alertId])
  );

  useEffect(() => {
    if (alert) {
      navigation.setOptions({
        title: `Alert - ${alert.type?.replace('_', ' ').toUpperCase()}`,
      });
    }
  }, [alert, navigation]);

  const handleRefresh = useCallback(() => {
    if (alertId) {
      dispatch(fetchAlertById(alertId));
    }
  }, [dispatch, alertId]);

  const handleAcknowledge = async () => {
    try {
      await dispatch(acknowledgeAlert(alertId)).unwrap();
      Alert.alert('Success', 'Alert acknowledged successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to acknowledge alert');
    }
  };

  const handleClear = async () => {
    Alert.alert(
      'Clear Alert',
      'Are you sure you want to clear this alert?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            try {
              await dispatch(clearAlert(alertId)).unwrap();
              Alert.alert('Success', 'Alert cleared successfully');
              navigation.goBack();
            } catch (error) {
              Alert.alert('Error', 'Failed to clear alert');
            }
          },
        },
      ]
    );
  };

  const handleShare = async () => {
    try {
      const shareData = {
        title: 'Security Alert',
        message: `Alert: ${alert.message}\nCamera: ${alert.cameraName}\nTime: ${formatDateTime(alert.timestamp)}`,
      };
      
      await Share.share(shareData);
    } catch (error) {
      Alert.alert('Error', 'Failed to share alert');
    }
  };

  const handleViewCamera = () => {
    if (alert.cameraId) {
      navigation.navigate('CameraDetail', { cameraId: alert.cameraId });
    }
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case ALERT_TYPES.MOTION_DETECTED:
        return '🏃‍♂️';
      case ALERT_TYPES.PERSON_DETECTED:
        return '👤';
      case ALERT_TYPES.VEHICLE_DETECTED:
        return '🚗';
      case ALERT_TYPES.CAMERA_OFFLINE:
        return '📷';
      case ALERT_TYPES.SYSTEM_ERROR:
        return '⚠️';
      default:
        return '🔔';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case ALERT_PRIORITIES.CRITICAL:
        return COLORS.error;
      case ALERT_PRIORITIES.HIGH:
        return COLORS.warning;
      case ALERT_PRIORITIES.MEDIUM:
        return COLORS.info;
      case ALERT_PRIORITIES.LOW:
        return COLORS.textSecondary;
      default:
        return COLORS.textSecondary;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'new':
        return COLORS.error;
      case 'acknowledged':
        return COLORS.warning;
      case 'resolved':
        return COLORS.success;
      default:
        return COLORS.textSecondary;
    }
  };

  const renderImageModal = () => (
    <Modal
      visible={imageModalVisible}
      transparent
      animationType="fade"
      onRequestClose={() => setImageModalVisible(false)}
    >
      <View style={styles.fullscreenModal}>
        <TouchableOpacity
          style={styles.fullscreenOverlay}
          onPress={() => setImageModalVisible(false)}
        >
          <View style={styles.fullscreenContent}>
            <View style={styles.imagePlaceholder}>
              <Text style={styles.imagePlaceholderIcon}>📷</Text>
              <Text style={styles.imagePlaceholderText}>Alert Image/Thumbnail</Text>
              <Text style={styles.imagePlaceholderHint}>Tap outside to close</Text>
            </View>
          </View>
        </TouchableOpacity>
        
        <View style={styles.fullscreenActions}>
          <Button
            title="Download"
            variant="outline"
            size="small"
            onPress={() => Alert.alert('Download', 'Image download feature')}
            style={styles.fullscreenButton}
          />
          <Button
            title="Share"
            variant="outline"
            size="small"
            onPress={handleShare}
            style={styles.fullscreenButton}
          />
          <Button
            title="Close"
            variant="outline"
            size="small"
            onPress={() => setImageModalVisible(false)}
            style={styles.fullscreenButton}
          />
        </View>
      </View>
    </Modal>
  );

  const renderVideoModal = () => (
    <Modal
      visible={videoModalVisible}
      transparent
      animationType="fade"
      onRequestClose={() => setVideoModalVisible(false)}
    >
      <View style={styles.fullscreenModal}>
        <TouchableOpacity
          style={styles.fullscreenOverlay}
          onPress={() => setVideoModalVisible(false)}
        >
          <View style={styles.fullscreenContent}>
            <View style={styles.videoPlaceholder}>
              <Text style={styles.videoPlaceholderIcon}>📹</Text>
              <Text style={styles.videoPlaceholderText}>Alert Video Clip</Text>
              <Text style={styles.videoPlaceholderHint}>Tap outside to close</Text>
              <View style={styles.videoControls}>
                <TouchableOpacity style={styles.playButton}>
                  <Text style={styles.playButtonText}>▶️</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </TouchableOpacity>
        
        <View style={styles.fullscreenActions}>
          <Button
            title="Download"
            variant="outline"
            size="small"
            onPress={() => Alert.alert('Download', 'Video download feature')}
            style={styles.fullscreenButton}
          />
          <Button
            title="Share"
            variant="outline"
            size="small"
            onPress={handleShare}
            style={styles.fullscreenButton}
          />
          <Button
            title="Close"
            variant="outline"
            size="small"
            onPress={() => setVideoModalVisible(false)}
            style={styles.fullscreenButton}
          />
        </View>
      </View>
    </Modal>
  );

  if (loading && !alert) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading alert details...</Text>
      </View>
    );
  }

  if (error || !alert) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>Failed to load alert details</Text>
        <Button title="Retry" onPress={handleRefresh} />
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
      {/* Alert Header */}
      <Card style={styles.headerCard}>
        <View style={styles.alertHeader}>
          <View style={styles.iconContainer}>
            <Text style={styles.alertIcon}>{getAlertIcon(alert.type)}</Text>
            <View
              style={[
                styles.priorityIndicator,
                { backgroundColor: getPriorityColor(alert.priority) },
              ]}
            />
          </View>
          
          <View style={styles.headerInfo}>
            <Text style={styles.alertType}>
              {alert.type?.replace('_', ' ').toUpperCase()}
            </Text>
            <Text style={styles.alertMessage}>{alert.message}</Text>
            <Text style={styles.alertTime}>
              {formatDateTime(alert.timestamp)} ({formatRelativeTime(alert.timestamp)})
            </Text>
          </View>
          
          <View
            style={[
              styles.statusBadge,
              { backgroundColor: getStatusColor(alert.status) },
            ]}
          >
            <Text style={styles.statusText}>{alert.status.toUpperCase()}</Text>
          </View>
        </View>
      </Card>

      {/* Alert Details */}
      <Card style={styles.detailsCard}>
        <Text style={styles.sectionTitle}>Alert Details</Text>
        
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Camera:</Text>
          <TouchableOpacity onPress={handleViewCamera}>
            <Text style={[styles.detailValue, styles.linkText]}>
              {alert.cameraName}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Location:</Text>
          <Text style={styles.detailValue}>{alert.location || 'Not specified'}</Text>
        </View>

        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Priority:</Text>
          <Text style={[
            styles.detailValue,
            { color: getPriorityColor(alert.priority) }
          ]}>
            {alert.priority?.toUpperCase()}
          </Text>
        </View>

        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Confidence:</Text>
          <Text style={styles.detailValue}>
            {alert.confidence ? `${Math.round(alert.confidence * 100)}%` : 'N/A'}
          </Text>
        </View>

        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Duration:</Text>
          <Text style={styles.detailValue}>
            {alert.duration ? `${alert.duration}s` : 'N/A'}
          </Text>
        </View>

        {alert.description && (
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Description:</Text>
            <Text style={styles.detailValue}>{alert.description}</Text>
          </View>
        )}
      </Card>

      {/* Media */}
      {(alert.thumbnail || alert.videoClip) && (
        <Card style={styles.mediaCard}>
          <Text style={styles.sectionTitle}>Media</Text>
          
          <View style={styles.mediaContainer}>
            {alert.thumbnail && (
              <TouchableOpacity
                style={styles.mediaItem}
                onPress={() => setImageModalVisible(true)}
              >
                <View style={styles.thumbnailContainer}>
                  <Text style={styles.thumbnailIcon}>📷</Text>
                  <Text style={styles.thumbnailText}>Snapshot</Text>
                </View>
              </TouchableOpacity>
            )}

            {alert.videoClip && (
              <TouchableOpacity
                style={styles.mediaItem}
                onPress={() => setVideoModalVisible(true)}
              >
                <View style={styles.videoContainer}>
                  <Text style={styles.videoIcon}>📹</Text>
                  <Text style={styles.videoText}>Video Clip</Text>
                  <Text style={styles.videoDuration}>
                    {alert.videoDuration || '10s'}
                  </Text>
                </View>
              </TouchableOpacity>
            )}
          </View>
        </Card>
      )}

      {/* Detection Info */}
      {alert.detectionInfo && (
        <Card style={styles.detectionCard}>
          <Text style={styles.sectionTitle}>Detection Information</Text>
          
          {alert.detectionInfo.objects && (
            <View style={styles.detectionSection}>
              <Text style={styles.detectionLabel}>Detected Objects:</Text>
              {alert.detectionInfo.objects.map((obj, index) => (
                <View key={index} style={styles.objectItem}>
                  <Text style={styles.objectName}>{obj.name}</Text>
                  <Text style={styles.objectConfidence}>
                    {Math.round(obj.confidence * 100)}%
                  </Text>
                </View>
              ))}
            </View>
          )}

          {alert.detectionInfo.motion && (
            <View style={styles.detectionSection}>
              <Text style={styles.detectionLabel}>Motion Detection:</Text>
              <Text style={styles.detectionValue}>
                Intensity: {alert.detectionInfo.motion.intensity}%
              </Text>
              <Text style={styles.detectionValue}>
                Area: {alert.detectionInfo.motion.area}%
              </Text>
            </View>
          )}
        </Card>
      )}

      {/* Actions */}
      <Card style={styles.actionsCard}>
        <Text style={styles.sectionTitle}>Actions</Text>
        
        <View style={styles.actionsContainer}>
          {alert.status === 'new' && (
            <Button
              title="Acknowledge"
              onPress={handleAcknowledge}
              style={styles.actionButton}
            />
          )}
          
          <Button
            title="View Camera"
            variant="outline"
            onPress={handleViewCamera}
            style={styles.actionButton}
          />
          
          <Button
            title="Share"
            variant="outline"
            onPress={handleShare}
            style={styles.actionButton}
          />
          
          <Button
            title="Clear Alert"
            variant="danger"
            onPress={handleClear}
            style={styles.actionButton}
          />
        </View>
      </Card>

      {renderImageModal()}
      {renderVideoModal()}
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
  headerCard: {
    margin: SIZES.margin,
    padding: SIZES.padding,
  },
  alertHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  iconContainer: {
    alignItems: 'center',
    marginRight: SIZES.margin,
  },
  alertIcon: {
    fontSize: 32,
    marginBottom: 4,
  },
  priorityIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  headerInfo: {
    flex: 1,
    marginRight: SIZES.margin,
  },
  alertType: {
    color: COLORS.text,
    ...FONTS.h4,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  alertMessage: {
    color: COLORS.text,
    ...FONTS.body3,
    marginBottom: 4,
  },
  alertTime: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    color: COLORS.white,
    ...FONTS.body5,
    fontWeight: 'bold',
  },
  detailsCard: {
    margin: SIZES.margin,
    marginTop: 0,
    padding: SIZES.padding,
  },
  sectionTitle: {
    color: COLORS.text,
    ...FONTS.h3,
    fontWeight: 'bold',
    marginBottom: SIZES.margin,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: SIZES.margin,
  },
  detailLabel: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
    flex: 1,
  },
  detailValue: {
    color: COLORS.text,
    ...FONTS.body4,
    flex: 2,
    textAlign: 'right',
  },
  linkText: {
    color: COLORS.primary,
    textDecorationLine: 'underline',
  },
  mediaCard: {
    margin: SIZES.margin,
    marginTop: 0,
    padding: SIZES.padding,
  },
  mediaContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  mediaItem: {
    flex: 1,
    marginHorizontal: SIZES.margin / 2,
  },
  thumbnailContainer: {
    backgroundColor: COLORS.background,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  thumbnailIcon: {
    fontSize: 32,
    marginBottom: SIZES.margin / 2,
  },
  thumbnailText: {
    color: COLORS.text,
    ...FONTS.body4,
  },
  videoContainer: {
    backgroundColor: COLORS.background,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  videoIcon: {
    fontSize: 32,
    marginBottom: SIZES.margin / 2,
  },
  videoText: {
    color: COLORS.text,
    ...FONTS.body4,
    marginBottom: 2,
  },
  videoDuration: {
    color: COLORS.textSecondary,
    ...FONTS.body5,
  },
  detectionCard: {
    margin: SIZES.margin,
    marginTop: 0,
    padding: SIZES.padding,
  },
  detectionSection: {
    marginBottom: SIZES.margin,
  },
  detectionLabel: {
    color: COLORS.text,
    ...FONTS.body3,
    fontWeight: 'bold',
    marginBottom: SIZES.margin / 2,
  },
  detectionValue: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
    marginBottom: 2,
  },
  objectItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: COLORS.background,
    padding: SIZES.padding / 2,
    borderRadius: SIZES.radius / 2,
    marginBottom: 4,
  },
  objectName: {
    color: COLORS.text,
    ...FONTS.body4,
    flex: 1,
  },
  objectConfidence: {
    color: COLORS.primary,
    ...FONTS.body4,
    fontWeight: 'bold',
  },
  actionsCard: {
    margin: SIZES.margin,
    marginTop: 0,
    padding: SIZES.padding,
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
  fullscreenModal: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  fullscreenOverlay: {
    flex: 1,
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  fullscreenContent: {
    width: '90%',
    height: '70%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  imagePlaceholder: {
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    padding: SIZES.padding * 2,
    alignItems: 'center',
    width: '100%',
    height: '100%',
    justifyContent: 'center',
  },
  imagePlaceholderIcon: {
    fontSize: 64,
    marginBottom: SIZES.margin,
  },
  imagePlaceholderText: {
    color: COLORS.text,
    ...FONTS.h3,
    marginBottom: SIZES.margin / 2,
  },
  imagePlaceholderHint: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
  },
  videoPlaceholder: {
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    padding: SIZES.padding * 2,
    alignItems: 'center',
    width: '100%',
    height: '100%',
    justifyContent: 'center',
  },
  videoPlaceholderIcon: {
    fontSize: 64,
    marginBottom: SIZES.margin,
  },
  videoPlaceholderText: {
    color: COLORS.text,
    ...FONTS.h3,
    marginBottom: SIZES.margin,
  },
  videoPlaceholderHint: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
    marginBottom: SIZES.margin,
  },
  videoControls: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  playButton: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  playButtonText: {
    fontSize: 24,
  },
  fullscreenActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    position: 'absolute',
    bottom: 50,
    left: 0,
    right: 0,
    paddingHorizontal: SIZES.padding,
  },
  fullscreenButton: {
    minWidth: 80,
  },
});

export default AlertDetailScreen;
