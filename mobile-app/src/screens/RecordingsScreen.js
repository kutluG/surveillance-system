import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  RefreshControl,
  TextInput,
  Modal,
  ScrollView,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { useFocusEffect } from '@react-navigation/native';
import { COLORS, SIZES, FONTS } from '../constants';
import { formatDateTime, formatDuration } from '../utils/dateUtils';
import Card from '../components/Card';
import Button from '../components/Button';
import VideoPlayer from '../components/VideoPlayer';

// Mock recordings service
const recordingsService = {
  async fetchRecordings(filters = {}) {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return {
      recordings: [
        {
          id: '1',
          cameraId: 'cam_001',
          cameraName: 'Front Door',
          filename: 'recording_001.mp4',
          startTime: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
          endTime: new Date(Date.now() - 3000000).toISOString(), // 50 minutes ago
          duration: 600, // 10 minutes
          size: 150000000, // 150MB
          quality: 'high',
          thumbnail: 'thumbnail_001.jpg',
          type: 'motion',
          tags: ['motion_detected', 'person'],
        },
        {
          id: '2',
          cameraId: 'cam_002',
          cameraName: 'Back Yard',
          filename: 'recording_002.mp4',
          startTime: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
          endTime: new Date(Date.now() - 6600000).toISOString(), // 1 hour 50 minutes ago
          duration: 600, // 10 minutes
          size: 120000000, // 120MB
          quality: 'medium',
          thumbnail: 'thumbnail_002.jpg',
          type: 'scheduled',
          tags: ['scheduled_recording'],
        },
        {
          id: '3',
          cameraId: 'cam_001',
          cameraName: 'Front Door',
          filename: 'recording_003.mp4',
          startTime: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
          endTime: new Date(Date.now() - 86100000).toISOString(), // 1 day ago + 5 minutes
          duration: 300, // 5 minutes
          size: 80000000, // 80MB
          quality: 'high',
          thumbnail: 'thumbnail_003.jpg',
          type: 'alert',
          tags: ['vehicle_detected', 'alert'],
        },
      ],
      total: 3,
      totalSize: 350000000, // 350MB
    };
  },

  async deleteRecording(recordingId) {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 500));
    return { success: true };
  },

  async downloadRecording(recordingId) {
    // Simulate download
    await new Promise(resolve => setTimeout(resolve, 2000));
    return { success: true, url: 'file://downloaded_recording.mp4' };
  },
};

const RecordingsScreen = ({ navigation }) => {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedRecordings, setSelectedRecordings] = useState(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [filterModalVisible, setFilterModalVisible] = useState(false);
  const [playerModalVisible, setPlayerModalVisible] = useState(false);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  const [filters, setFilters] = useState({
    camera: 'all',
    type: 'all',
    quality: 'all',
    dateFrom: null,
    dateTo: null,
  });

  const [cameras] = useState([
    { id: 'cam_001', name: 'Front Door' },
    { id: 'cam_002', name: 'Back Yard' },
    { id: 'cam_003', name: 'Living Room' },
  ]);

  // Filter recordings based on search and filters
  const filteredRecordings = recordings.filter(recording => {
    const matchesSearch = searchQuery === '' || 
      recording.cameraName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      recording.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesCamera = filters.camera === 'all' || recording.cameraId === filters.camera;
    const matchesType = filters.type === 'all' || recording.type === filters.type;
    const matchesQuality = filters.quality === 'all' || recording.quality === filters.quality;
    
    return matchesSearch && matchesCamera && matchesType && matchesQuality;
  });

  useFocusEffect(
    useCallback(() => {
      fetchRecordings();
    }, [])
  );

  const fetchRecordings = async () => {
    setLoading(true);
    try {
      const data = await recordingsService.fetchRecordings(filters);
      setRecordings(data.recordings);
    } catch (error) {
      Alert.alert('Error', 'Failed to load recordings');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await recordingsService.fetchRecordings(filters);
      setRecordings(data.recordings);
    } catch (error) {
      Alert.alert('Error', 'Failed to refresh recordings');
    } finally {
      setRefreshing(false);
    }
  }, [filters]);

  const handleRecordingPress = (recording) => {
    if (isSelectionMode) {
      toggleRecordingSelection(recording.id);
    } else {
      setSelectedRecording(recording);
      setPlayerModalVisible(true);
    }
  };

  const handleRecordingLongPress = (recording) => {
    if (!isSelectionMode) {
      setIsSelectionMode(true);
      setSelectedRecordings(new Set([recording.id]));
    }
  };

  const toggleRecordingSelection = (recordingId) => {
    const newSelected = new Set(selectedRecordings);
    if (newSelected.has(recordingId)) {
      newSelected.delete(recordingId);
    } else {
      newSelected.add(recordingId);
    }
    setSelectedRecordings(newSelected);
    
    if (newSelected.size === 0) {
      setIsSelectionMode(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedRecordings.size === 0) return;
    
    Alert.alert(
      'Delete Recordings',
      `Are you sure you want to delete ${selectedRecordings.size} recording(s)?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              for (const recordingId of selectedRecordings) {
                await recordingsService.deleteRecording(recordingId);
              }
              
              // Remove deleted recordings from state
              setRecordings(prev => 
                prev.filter(recording => !selectedRecordings.has(recording.id))
              );
              
              setSelectedRecordings(new Set());
              setIsSelectionMode(false);
              Alert.alert('Success', 'Recordings deleted successfully');
            } catch (error) {
              Alert.alert('Error', 'Failed to delete recordings');
            }
          },
        },
      ]
    );
  };

  const handleDownloadSelected = async () => {
    if (selectedRecordings.size === 0) return;
    
    Alert.alert(
      'Download Recordings',
      `Download ${selectedRecordings.size} recording(s) to device?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Download',
          onPress: async () => {
            try {
              for (const recordingId of selectedRecordings) {
                await recordingsService.downloadRecording(recordingId);
              }
              
              setSelectedRecordings(new Set());
              setIsSelectionMode(false);
              Alert.alert('Success', 'Recordings downloaded successfully');
            } catch (error) {
              Alert.alert('Error', 'Failed to download recordings');
            }
          },
        },
      ]
    );
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'motion':
        return '🏃‍♂️';
      case 'alert':
        return '🚨';
      case 'scheduled':
        return '⏰';
      default:
        return '📹';
    }
  };

  const getQualityColor = (quality) => {
    switch (quality) {
      case 'high':
        return COLORS.success;
      case 'medium':
        return COLORS.warning;
      case 'low':
        return COLORS.error;
      default:
        return COLORS.textSecondary;
    }
  };

  const renderRecording = ({ item }) => (
    <TouchableOpacity
      onPress={() => handleRecordingPress(item)}
      onLongPress={() => handleRecordingLongPress(item)}
      style={[
        styles.recordingContainer,
        selectedRecordings.has(item.id) && styles.selectedRecording,
      ]}
    >
      <Card style={styles.recordingCard}>
        <View style={styles.recordingHeader}>
          <View style={styles.thumbnailContainer}>
            <Text style={styles.thumbnailIcon}>📹</Text>
            <Text style={styles.typeIcon}>{getTypeIcon(item.type)}</Text>
          </View>
          
          <View style={styles.recordingInfo}>
            <Text style={styles.recordingCamera}>{item.cameraName}</Text>
            <Text style={styles.recordingTime}>
              {formatDateTime(item.startTime)}
            </Text>
            <Text style={styles.recordingDuration}>
              Duration: {formatDuration(item.duration)}
            </Text>
          </View>
          
          <View style={styles.recordingMeta}>
            <Text style={[
              styles.qualityBadge,
              { color: getQualityColor(item.quality) }
            ]}>
              {item.quality.toUpperCase()}
            </Text>
            <Text style={styles.fileSize}>
              {formatFileSize(item.size)}
            </Text>
          </View>
        </View>
        
        {item.tags && item.tags.length > 0 && (
          <View style={styles.tagsContainer}>
            {item.tags.map((tag, index) => (
              <View key={index} style={styles.tag}>
                <Text style={styles.tagText}>
                  {tag.replace('_', ' ').toUpperCase()}
                </Text>
              </View>
            ))}
          </View>
        )}
      </Card>
    </TouchableOpacity>
  );

  const renderFilterModal = () => (
    <Modal
      visible={filterModalVisible}
      transparent
      animationType="slide"
      onRequestClose={() => setFilterModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Filter Recordings</Text>
          
          <ScrollView style={styles.filterContent}>
            <View style={styles.filterSection}>
              <Text style={styles.filterLabel}>Camera</Text>
              {[{ id: 'all', name: 'All Cameras' }, ...cameras].map(camera => (
                <TouchableOpacity
                  key={camera.id}
                  style={[
                    styles.filterOption,
                    filters.camera === camera.id && styles.filterOptionSelected,
                  ]}
                  onPress={() => setFilters({ ...filters, camera: camera.id })}
                >
                  <Text
                    style={[
                      styles.filterOptionText,
                      filters.camera === camera.id && styles.filterOptionTextSelected,
                    ]}
                  >
                    {camera.name}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.filterSection}>
              <Text style={styles.filterLabel}>Type</Text>
              {['all', 'motion', 'alert', 'scheduled'].map(type => (
                <TouchableOpacity
                  key={type}
                  style={[
                    styles.filterOption,
                    filters.type === type && styles.filterOptionSelected,
                  ]}
                  onPress={() => setFilters({ ...filters, type })}
                >
                  <Text
                    style={[
                      styles.filterOptionText,
                      filters.type === type && styles.filterOptionTextSelected,
                    ]}
                  >
                    {type === 'all' ? 'All Types' : type.charAt(0).toUpperCase() + type.slice(1)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.filterSection}>
              <Text style={styles.filterLabel}>Quality</Text>
              {['all', 'high', 'medium', 'low'].map(quality => (
                <TouchableOpacity
                  key={quality}
                  style={[
                    styles.filterOption,
                    filters.quality === quality && styles.filterOptionSelected,
                  ]}
                  onPress={() => setFilters({ ...filters, quality })}
                >
                  <Text
                    style={[
                      styles.filterOptionText,
                      filters.quality === quality && styles.filterOptionTextSelected,
                    ]}
                  >
                    {quality === 'all' ? 'All Qualities' : quality.charAt(0).toUpperCase() + quality.slice(1)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>

          <View style={styles.modalButtons}>
            <Button
              title="Reset"
              variant="outline"
              onPress={() => {
                setFilters({ camera: 'all', type: 'all', quality: 'all' });
              }}
              style={styles.modalButton}
            />
            <Button
              title="Apply"
              onPress={() => {
                setFilterModalVisible(false);
                fetchRecordings();
              }}
              style={styles.modalButton}
            />
          </View>
        </View>
      </View>
    </Modal>
  );

  const renderPlayerModal = () => (
    <Modal
      visible={playerModalVisible}
      transparent={false}
      animationType="slide"
      onRequestClose={() => setPlayerModalVisible(false)}
    >
      <View style={styles.playerContainer}>
        <View style={styles.playerHeader}>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => setPlayerModalVisible(false)}
          >
            <Text style={styles.backButtonText}>←</Text>
          </TouchableOpacity>
          <View style={styles.playerHeaderInfo}>
            <Text style={styles.playerTitle}>{selectedRecording?.cameraName}</Text>
            <Text style={styles.playerSubtitle}>
              {selectedRecording && formatDateTime(selectedRecording.startTime)}
            </Text>
          </View>
        </View>
        
        <VideoPlayer
          source={selectedRecording?.filename}
          isLive={false}
          autoPlay={true}
          controls={true}
          fullscreenEnabled={true}
          style={styles.videoPlayer}
        />
        
        <View style={styles.playerActions}>
          <Button
            title="Download"
            variant="outline"
            size="small"
            onPress={() => Alert.alert('Download', 'Download feature')}
            style={styles.playerButton}
          />
          <Button
            title="Share"
            variant="outline"
            size="small"
            onPress={() => Alert.alert('Share', 'Share feature')}
            style={styles.playerButton}
          />
          <Button
            title="Delete"
            variant="danger"
            size="small"
            onPress={() => {
              Alert.alert(
                'Delete Recording',
                'Are you sure you want to delete this recording?',
                [
                  { text: 'Cancel', style: 'cancel' },
                  {
                    text: 'Delete',
                    style: 'destructive',
                    onPress: () => {
                      setPlayerModalVisible(false);
                      // Handle delete
                    },
                  },
                ]
              );
            }}
            style={styles.playerButton}
          />
        </View>
      </View>
    </Modal>
  );

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search recordings..."
          placeholderTextColor={COLORS.textSecondary}
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        <TouchableOpacity
          style={styles.filterButton}
          onPress={() => setFilterModalVisible(true)}
        >
          <Text style={styles.filterButtonText}>🔍</Text>
        </TouchableOpacity>
      </View>

      {/* Selection Header */}
      {isSelectionMode && (
        <View style={styles.selectionHeader}>
          <Text style={styles.selectionText}>
            {selectedRecordings.size} selected
          </Text>
          <View style={styles.selectionActions}>
            <Button
              title="Download"
              variant="outline"
              size="small"
              onPress={handleDownloadSelected}
              style={styles.selectionButton}
            />
            <Button
              title="Delete"
              variant="outline"
              size="small"
              onPress={handleDeleteSelected}
              style={styles.selectionButton}
            />
            <Button
              title="Cancel"
              variant="outline"
              size="small"
              onPress={() => {
                setIsSelectionMode(false);
                setSelectedRecordings(new Set());
              }}
              style={styles.selectionButton}
            />
          </View>
        </View>
      )}

      {/* Recordings List */}
      <FlatList
        data={filteredRecordings}
        renderItem={renderRecording}
        keyExtractor={item => item.id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No recordings found</Text>
          </View>
        }
      />

      {renderFilterModal()}
      {renderPlayerModal()}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: SIZES.padding,
    backgroundColor: COLORS.surface,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  searchInput: {
    flex: 1,
    height: 40,
    backgroundColor: COLORS.background,
    borderRadius: SIZES.radius,
    paddingHorizontal: SIZES.padding,
    marginRight: SIZES.margin,
    color: COLORS.text,
    ...FONTS.body4,
  },
  filterButton: {
    width: 40,
    height: 40,
    backgroundColor: COLORS.primary,
    borderRadius: SIZES.radius,
    justifyContent: 'center',
    alignItems: 'center',
  },
  filterButtonText: {
    fontSize: 18,
  },
  selectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: SIZES.padding,
    backgroundColor: COLORS.primary + '20',
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  selectionText: {
    color: COLORS.text,
    ...FONTS.body3,
    fontWeight: 'bold',
  },
  selectionActions: {
    flexDirection: 'row',
  },
  selectionButton: {
    marginLeft: SIZES.margin / 2,
  },
  listContainer: {
    padding: SIZES.padding,
  },
  recordingContainer: {
    marginBottom: SIZES.margin,
  },
  selectedRecording: {
    transform: [{ scale: 0.98 }],
  },
  recordingCard: {
    padding: SIZES.padding,
  },
  recordingHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  thumbnailContainer: {
    alignItems: 'center',
    marginRight: SIZES.margin,
  },
  thumbnailIcon: {
    fontSize: 32,
    marginBottom: 4,
  },
  typeIcon: {
    fontSize: 16,
  },
  recordingInfo: {
    flex: 1,
    marginRight: SIZES.margin,
  },
  recordingCamera: {
    color: COLORS.text,
    ...FONTS.body3,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  recordingTime: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
    marginBottom: 2,
  },
  recordingDuration: {
    color: COLORS.textSecondary,
    ...FONTS.body5,
  },
  recordingMeta: {
    alignItems: 'flex-end',
  },
  qualityBadge: {
    ...FONTS.body5,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  fileSize: {
    color: COLORS.textSecondary,
    ...FONTS.body5,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: SIZES.margin,
  },
  tag: {
    backgroundColor: COLORS.primary + '20',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    marginRight: 6,
    marginBottom: 4,
  },
  tagText: {
    color: COLORS.primary,
    ...FONTS.body6,
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
    maxHeight: '80%',
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
  filterContent: {
    maxHeight: 400,
  },
  filterSection: {
    padding: SIZES.padding,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  filterLabel: {
    color: COLORS.text,
    ...FONTS.body3,
    fontWeight: 'bold',
    marginBottom: SIZES.margin,
  },
  filterOption: {
    paddingVertical: SIZES.padding / 2,
    paddingHorizontal: SIZES.padding,
    marginVertical: 2,
    borderRadius: SIZES.radius,
    backgroundColor: COLORS.background,
  },
  filterOptionSelected: {
    backgroundColor: COLORS.primary,
  },
  filterOptionText: {
    color: COLORS.text,
    ...FONTS.body4,
  },
  filterOptionTextSelected: {
    color: COLORS.white,
    fontWeight: 'bold',
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
  playerContainer: {
    flex: 1,
    backgroundColor: COLORS.black,
  },
  playerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: SIZES.padding,
    backgroundColor: COLORS.surface,
  },
  backButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SIZES.margin,
  },
  backButtonText: {
    color: COLORS.text,
    fontSize: 24,
  },
  playerHeaderInfo: {
    flex: 1,
  },
  playerTitle: {
    color: COLORS.text,
    ...FONTS.h4,
    fontWeight: 'bold',
  },
  playerSubtitle: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
  },
  videoPlayer: {
    flex: 1,
  },
  playerActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: SIZES.padding,
    backgroundColor: COLORS.surface,
  },
  playerButton: {
    minWidth: 80,
  },
  emptyContainer: {
    padding: SIZES.padding * 2,
    alignItems: 'center',
  },
  emptyText: {
    color: COLORS.textSecondary,
    ...FONTS.body3,
    textAlign: 'center',
  },
});

export default RecordingsScreen;
