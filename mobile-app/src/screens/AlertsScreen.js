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
import {
  fetchAlerts,
  acknowledgeAlert,
  acknowledgeMultipleAlerts,
  clearAlert,
  setFilter,
  selectAlerts,
  selectAlertsLoading,
  selectAlertsError,
  selectAlertsFilter,
} from '../store/slices/alertsSlice';
import { COLORS, SIZES, FONTS, ALERT_TYPES, ALERT_PRIORITIES } from '../constants';
import { formatDateTime, formatRelativeTime } from '../utils/dateUtils';
import Card from '../components/Card';
import Button from '../components/Button';

const AlertsScreen = ({ navigation }) => {
  const dispatch = useDispatch();
  const alerts = useSelector(selectAlerts);
  const loading = useSelector(selectAlertsLoading);
  const error = useSelector(selectAlertsError);
  const filter = useSelector(selectAlertsFilter);

  const [selectedAlerts, setSelectedAlerts] = useState(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [filterModalVisible, setFilterModalVisible] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Filter alerts based on search and filters
  const filteredAlerts = alerts.filter(alert => {
    const matchesSearch = searchQuery === '' || 
      alert.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.cameraName?.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesStatus = filter.status === 'all' || alert.status === filter.status;
    const matchesType = filter.type === 'all' || alert.type === filter.type;
    const matchesPriority = filter.priority === 'all' || alert.priority === filter.priority;
    
    return matchesSearch && matchesStatus && matchesType && matchesPriority;
  });

  useFocusEffect(
    useCallback(() => {
      dispatch(fetchAlerts());
    }, [dispatch])
  );

  const handleRefresh = useCallback(() => {
    dispatch(fetchAlerts());
  }, [dispatch]);

  const handleAlertPress = (alert) => {
    if (isSelectionMode) {
      toggleAlertSelection(alert.id);
    } else {
      navigation.navigate('AlertDetail', { alertId: alert.id });
    }
  };

  const handleAlertLongPress = (alert) => {
    if (!isSelectionMode) {
      setIsSelectionMode(true);
      setSelectedAlerts(new Set([alert.id]));
    }
  };

  const toggleAlertSelection = (alertId) => {
    const newSelected = new Set(selectedAlerts);
    if (newSelected.has(alertId)) {
      newSelected.delete(alertId);
    } else {
      newSelected.add(alertId);
    }
    setSelectedAlerts(newSelected);
    
    if (newSelected.size === 0) {
      setIsSelectionMode(false);
    }
  };

  const handleAcknowledgeSelected = async () => {
    if (selectedAlerts.size === 0) return;
    
    try {
      if (selectedAlerts.size === 1) {
        await dispatch(acknowledgeAlert([...selectedAlerts][0])).unwrap();
      } else {
        await dispatch(acknowledgeMultipleAlerts([...selectedAlerts])).unwrap();
      }
      setSelectedAlerts(new Set());
      setIsSelectionMode(false);
    } catch (error) {
      Alert.alert('Error', 'Failed to acknowledge alerts');
    }
  };

  const handleClearSelected = async () => {
    if (selectedAlerts.size === 0) return;
    
    Alert.alert(
      'Clear Alerts',
      `Are you sure you want to clear ${selectedAlerts.size} alert(s)?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            try {
              for (const alertId of selectedAlerts) {
                await dispatch(clearAlert(alertId)).unwrap();
              }
              setSelectedAlerts(new Set());
              setIsSelectionMode(false);
            } catch (error) {
              Alert.alert('Error', 'Failed to clear alerts');
            }
          },
        },
      ]
    );
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

  const renderAlert = ({ item }) => (
    <TouchableOpacity
      onPress={() => handleAlertPress(item)}
      onLongPress={() => handleAlertLongPress(item)}
      style={[
        styles.alertContainer,
        selectedAlerts.has(item.id) && styles.selectedAlert,
      ]}
    >
      <Card style={styles.alertCard}>
        <View style={styles.alertHeader}>
          <View style={styles.alertIconContainer}>
            <Text style={styles.alertIcon}>{getAlertIcon(item.type)}</Text>
            <View
              style={[
                styles.priorityIndicator,
                { backgroundColor: getPriorityColor(item.priority) },
              ]}
            />
          </View>
          <View style={styles.alertInfo}>
            <Text style={styles.alertMessage} numberOfLines={2}>
              {item.message}
            </Text>
            <Text style={styles.alertCamera}>{item.cameraName}</Text>
          </View>
          <View style={styles.alertMeta}>
            <Text style={styles.alertTime}>{formatRelativeTime(item.timestamp)}</Text>
            <View
              style={[
                styles.statusBadge,
                { backgroundColor: getStatusColor(item.status) },
              ]}
            >
              <Text style={styles.statusText}>{item.status.toUpperCase()}</Text>
            </View>
          </View>
        </View>
        
        {item.thumbnail && (
          <View style={styles.thumbnailContainer}>
            <Text style={styles.thumbnailPlaceholder}>📷 Thumbnail Available</Text>
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
          <Text style={styles.modalTitle}>Filter Alerts</Text>
          
          <ScrollView style={styles.filterContent}>
            <View style={styles.filterSection}>
              <Text style={styles.filterLabel}>Status</Text>
              {['all', 'new', 'acknowledged', 'resolved'].map(status => (
                <TouchableOpacity
                  key={status}
                  style={[
                    styles.filterOption,
                    filter.status === status && styles.filterOptionSelected,
                  ]}
                  onPress={() => dispatch(setFilter({ ...filter, status }))}
                >
                  <Text
                    style={[
                      styles.filterOptionText,
                      filter.status === status && styles.filterOptionTextSelected,
                    ]}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.filterSection}>
              <Text style={styles.filterLabel}>Type</Text>
              {['all', ...Object.values(ALERT_TYPES)].map(type => (
                <TouchableOpacity
                  key={type}
                  style={[
                    styles.filterOption,
                    filter.type === type && styles.filterOptionSelected,
                  ]}
                  onPress={() => dispatch(setFilter({ ...filter, type }))}
                >
                  <Text
                    style={[
                      styles.filterOptionText,
                      filter.type === type && styles.filterOptionTextSelected,
                    ]}
                  >
                    {type === 'all' ? 'All Types' : type.replace('_', ' ').toUpperCase()}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.filterSection}>
              <Text style={styles.filterLabel}>Priority</Text>
              {['all', ...Object.values(ALERT_PRIORITIES)].map(priority => (
                <TouchableOpacity
                  key={priority}
                  style={[
                    styles.filterOption,
                    filter.priority === priority && styles.filterOptionSelected,
                  ]}
                  onPress={() => dispatch(setFilter({ ...filter, priority }))}
                >
                  <Text
                    style={[
                      styles.filterOptionText,
                      filter.priority === priority && styles.filterOptionTextSelected,
                    ]}
                  >
                    {priority === 'all' ? 'All Priorities' : priority.toUpperCase()}
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
                dispatch(setFilter({ status: 'all', type: 'all', priority: 'all' }));
              }}
              style={styles.modalButton}
            />
            <Button
              title="Done"
              onPress={() => setFilterModalVisible(false)}
              style={styles.modalButton}
            />
          </View>
        </View>
      </View>
    </Modal>
  );

  if (error) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>Failed to load alerts</Text>
        <Button title="Retry" onPress={handleRefresh} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search alerts..."
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
            {selectedAlerts.size} selected
          </Text>
          <View style={styles.selectionActions}>
            <Button
              title="Acknowledge"
              variant="outline"
              size="small"
              onPress={handleAcknowledgeSelected}
              style={styles.selectionButton}
            />
            <Button
              title="Clear"
              variant="outline"
              size="small"
              onPress={handleClearSelected}
              style={styles.selectionButton}
            />
            <Button
              title="Cancel"
              variant="outline"
              size="small"
              onPress={() => {
                setIsSelectionMode(false);
                setSelectedAlerts(new Set());
              }}
              style={styles.selectionButton}
            />
          </View>
        </View>
      )}

      {/* Alerts List */}
      <FlatList
        data={filteredAlerts}
        renderItem={renderAlert}
        keyExtractor={item => item.id}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={handleRefresh} />
        }
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No alerts found</Text>
          </View>
        }
      />

      {renderFilterModal()}
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
  alertContainer: {
    marginBottom: SIZES.margin,
  },
  selectedAlert: {
    transform: [{ scale: 0.98 }],
  },
  alertCard: {
    padding: SIZES.padding,
  },
  alertHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  alertIconContainer: {
    marginRight: SIZES.margin,
    alignItems: 'center',
  },
  alertIcon: {
    fontSize: 24,
    marginBottom: 4,
  },
  priorityIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  alertInfo: {
    flex: 1,
    marginRight: SIZES.margin,
  },
  alertMessage: {
    color: COLORS.text,
    ...FONTS.body3,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  alertCamera: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
  },
  alertMeta: {
    alignItems: 'flex-end',
  },
  alertTime: {
    color: COLORS.textSecondary,
    ...FONTS.body5,
    marginBottom: 4,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  statusText: {
    color: COLORS.white,
    ...FONTS.body5,
    fontWeight: 'bold',
  },
  thumbnailContainer: {
    marginTop: SIZES.margin,
    padding: SIZES.padding / 2,
    backgroundColor: COLORS.background,
    borderRadius: SIZES.radius,
    alignItems: 'center',
  },
  thumbnailPlaceholder: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
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

export default AlertsScreen;
