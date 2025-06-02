import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
  TextInput,
  Alert
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { COLORS, SIZES, FONTS, CAMERA_STATUS } from '../constants';
import { 
  fetchCameras, 
  selectFilteredCameras, 
  selectCamerasLoading,
  setFilters,
  selectCameraFilters
} from '../store/slices/camerasSlice';
import { formatCameraName, formatStatus } from '../utils/formatters';
import { getTimeAgo } from '../utils/dateUtils';

const CamerasScreen = ({ navigation }) => {
  const dispatch = useDispatch();
  const cameras = useSelector(selectFilteredCameras);
  const loading = useSelector(selectCamerasLoading);
  const filters = useSelector(selectCameraFilters);
  
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadCameras();
  }, []);

  const loadCameras = useCallback(async () => {
    try {
      await dispatch(fetchCameras()).unwrap();
    } catch (error) {
      Alert.alert('Error', 'Failed to load cameras');
    } finally {
      setRefreshing(false);
    }
  }, [dispatch]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadCameras();
  }, [loadCameras]);

  const handleCameraPress = (camera) => {
    navigation.navigate('CameraDetail', { cameraId: camera.id, camera });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case CAMERA_STATUS.ONLINE: return COLORS.success;
      case CAMERA_STATUS.RECORDING: return COLORS.warning;
      case CAMERA_STATUS.OFFLINE: return COLORS.error;
      case CAMERA_STATUS.MAINTENANCE: return COLORS.info;
      default: return COLORS.gray;
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case CAMERA_STATUS.ONLINE: return 'videocam';
      case CAMERA_STATUS.RECORDING: return 'fiber-manual-record';
      case CAMERA_STATUS.OFFLINE: return 'videocam-off';
      case CAMERA_STATUS.MAINTENANCE: return 'build';
      default: return 'help';
    }
  };

  const filteredCameras = cameras.filter(camera =>
    formatCameraName(camera.name).toLowerCase().includes(searchQuery.toLowerCase()) ||
    camera.location?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const CameraCard = ({ camera }) => (
    <TouchableOpacity
      style={styles.cameraCard}
      onPress={() => handleCameraPress(camera)}
    >
      <View style={styles.cameraHeader}>
        <View style={styles.cameraInfo}>
          <Text style={styles.cameraName}>{formatCameraName(camera.name)}</Text>
          <Text style={styles.cameraLocation}>{camera.location || 'Unknown Location'}</Text>
        </View>
        <View style={[styles.statusIndicator, { backgroundColor: getStatusColor(camera.status) }]}>
          <Icon 
            name={getStatusIcon(camera.status)} 
            size={16} 
            color={COLORS.white} 
          />
        </View>
      </View>
      
      <View style={styles.cameraDetails}>
        <View style={styles.detailItem}>
          <Icon name="signal-wifi-4-bar" size={16} color={COLORS.gray} />
          <Text style={styles.detailText}>
            {camera.signal || 'N/A'}
          </Text>
        </View>
        <View style={styles.detailItem}>
          <Icon name="hd" size={16} color={COLORS.gray} />
          <Text style={styles.detailText}>
            {camera.resolution || 'Unknown'}
          </Text>
        </View>
        <View style={styles.detailItem}>
          <Icon name="access-time" size={16} color={COLORS.gray} />
          <Text style={styles.detailText}>
            {camera.lastActivity ? getTimeAgo(camera.lastActivity) : 'Never'}
          </Text>
        </View>
      </View>

      <View style={styles.cameraFooter}>
        <Text style={styles.statusText}>{formatStatus(camera.status)}</Text>
        {camera.recording && (
          <View style={styles.recordingBadge}>
            <Icon name="fiber-manual-record" size={12} color={COLORS.error} />
            <Text style={styles.recordingText}>REC</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );

  const FilterButton = ({ title, value, isActive, onPress }) => (
    <TouchableOpacity
      style={[styles.filterButton, isActive && styles.activeFilterButton]}
      onPress={onPress}
    >
      <Text style={[styles.filterButtonText, isActive && styles.activeFilterButtonText]}>
        {title}
      </Text>
    </TouchableOpacity>
  );

  const renderHeader = () => (
    <View style={styles.header}>
      <View style={styles.searchContainer}>
        <Icon name="search" size={20} color={COLORS.gray} style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search cameras..."
          placeholderTextColor={COLORS.gray}
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity onPress={() => setSearchQuery('')}>
            <Icon name="clear" size={20} color={COLORS.gray} />
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.filtersContainer}>
        <FilterButton
          title="All"
          value="all"
          isActive={filters.status === 'all'}
          onPress={() => dispatch(setFilters({ status: 'all' }))}
        />
        <FilterButton
          title="Online"
          value="online"
          isActive={filters.status === 'online'}
          onPress={() => dispatch(setFilters({ status: 'online' }))}
        />
        <FilterButton
          title="Recording"
          value="recording"
          isActive={filters.status === 'recording'}
          onPress={() => dispatch(setFilters({ status: 'recording' }))}
        />
        <FilterButton
          title="Offline"
          value="offline"
          isActive={filters.status === 'offline'}
          onPress={() => dispatch(setFilters({ status: 'offline' }))}
        />
      </View>
    </View>
  );

  const renderEmptyComponent = () => (
    <View style={styles.emptyContainer}>
      <Icon name="videocam-off" size={60} color={COLORS.gray} />
      <Text style={styles.emptyTitle}>No Cameras Found</Text>
      <Text style={styles.emptyText}>
        {searchQuery ? 'Try adjusting your search' : 'No cameras are currently configured'}
      </Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={filteredCameras}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => <CameraCard camera={item} />}
        ListHeaderComponent={renderHeader}
        ListEmptyComponent={renderEmptyComponent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  listContainer: {
    flexGrow: 1,
  },
  header: {
    padding: SIZES.base,
    backgroundColor: COLORS.surface,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.background,
    borderRadius: SIZES.radius,
    paddingHorizontal: SIZES.base,
    marginBottom: SIZES.base,
    height: 40,
  },
  searchIcon: {
    marginRight: SIZES.base,
  },
  searchInput: {
    flex: 1,
    ...FONTS.body3,
    color: COLORS.text,
  },
  filtersContainer: {
    flexDirection: 'row',
    gap: SIZES.base / 2,
  },
  filterButton: {
    paddingHorizontal: SIZES.base,
    paddingVertical: SIZES.base / 2,
    borderRadius: SIZES.radius / 2,
    backgroundColor: COLORS.background,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  activeFilterButton: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  filterButtonText: {
    ...FONTS.caption,
    color: COLORS.text,
  },
  activeFilterButtonText: {
    color: COLORS.white,
  },
  cameraCard: {
    backgroundColor: COLORS.surface,
    marginHorizontal: SIZES.base,
    marginVertical: SIZES.base / 2,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cameraHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: SIZES.base,
  },
  cameraInfo: {
    flex: 1,
  },
  cameraName: {
    ...FONTS.h3,
    color: COLORS.text,
  },
  cameraLocation: {
    ...FONTS.body3,
    color: COLORS.gray,
    marginTop: 2,
  },
  statusIndicator: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cameraDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SIZES.base,
  },
  detailItem: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  detailText: {
    ...FONTS.caption,
    color: COLORS.gray,
    marginLeft: SIZES.base / 2,
  },
  cameraFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusText: {
    ...FONTS.body3,
    color: COLORS.text,
  },
  recordingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.surface,
    paddingHorizontal: SIZES.base / 2,
    paddingVertical: 2,
    borderRadius: SIZES.radius / 2,
    borderWidth: 1,
    borderColor: COLORS.error,
  },
  recordingText: {
    ...FONTS.caption,
    color: COLORS.error,
    marginLeft: 2,
    fontSize: 10,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: SIZES.padding * 2,
  },
  emptyTitle: {
    ...FONTS.h2,
    color: COLORS.text,
    marginTop: SIZES.base,
    marginBottom: SIZES.base / 2,
  },
  emptyText: {
    ...FONTS.body3,
    color: COLORS.gray,
    textAlign: 'center',
  },
});

export default CamerasScreen;
