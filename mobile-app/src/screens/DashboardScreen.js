import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
  Alert,
  Dimensions
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { COLORS, SIZES, FONTS } from '../constants';
import { dashboardService } from '../services/dashboardService';
import { selectUnreadCount } from '../store/slices/alertsSlice';
import { formatNumber, formatFileSize } from '../utils/formatters';
import { getTimeAgo } from '../utils/dateUtils';

const { width } = Dimensions.get('window');

const DashboardScreen = ({ navigation }) => {
  const dispatch = useDispatch();
  const unreadAlerts = useSelector(selectUnreadCount);
  
  const [dashboardData, setDashboardData] = useState({
    overview: {},
    systemHealth: {},
    recentActivities: [],
    quickStats: {}
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboardData = useCallback(async () => {
    try {
      const [overview, systemHealth, recentActivities] = await Promise.all([
        dashboardService.getDashboardOverview(),
        dashboardService.getSystemHealth(),
        dashboardService.getRecentActivities(5)
      ]);

      setDashboardData({
        overview: overview.data,
        systemHealth: systemHealth.data,
        recentActivities: recentActivities.data,
        quickStats: overview.data.stats || {}
      });
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      Alert.alert('Error', 'Failed to load dashboard data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadDashboardData();
  }, [loadDashboardData]);

  const StatCard = ({ title, value, icon, color, onPress }) => (
    <TouchableOpacity style={[styles.statCard, { borderLeftColor: color }]} onPress={onPress}>
      <View style={styles.statContent}>
        <View style={styles.statHeader}>
          <Text style={styles.statTitle}>{title}</Text>
          <Icon name={icon} size={24} color={color} />
        </View>
        <Text style={styles.statValue}>{value}</Text>
      </View>
    </TouchableOpacity>
  );

  const SystemStatusCard = ({ status }) => (
    <View style={styles.systemStatusCard}>
      <Text style={styles.cardTitle}>System Status</Text>
      <View style={styles.statusGrid}>
        <View style={styles.statusItem}>
          <View style={[styles.statusIndicator, { 
            backgroundColor: status.overall === 'healthy' ? COLORS.success : COLORS.error 
          }]} />
          <Text style={styles.statusText}>Overall: {status.overall || 'Unknown'}</Text>
        </View>
        <View style={styles.statusItem}>
          <View style={[styles.statusIndicator, { 
            backgroundColor: status.cameras >= 90 ? COLORS.success : 
                           status.cameras >= 70 ? COLORS.warning : COLORS.error 
          }]} />
          <Text style={styles.statusText}>Cameras: {status.cameras || 0}% Online</Text>
        </View>
        <View style={styles.statusItem}>
          <View style={[styles.statusIndicator, { 
            backgroundColor: status.storage <= 80 ? COLORS.success : 
                           status.storage <= 90 ? COLORS.warning : COLORS.error 
          }]} />
          <Text style={styles.statusText}>Storage: {status.storage || 0}% Used</Text>
        </View>
        <View style={styles.statusItem}>
          <View style={[styles.statusIndicator, { 
            backgroundColor: status.network === 'stable' ? COLORS.success : COLORS.warning 
          }]} />
          <Text style={styles.statusText}>Network: {status.network || 'Unknown'}</Text>
        </View>
      </View>
    </View>
  );

  const RecentActivityCard = ({ activities }) => (
    <View style={styles.recentActivityCard}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle}>Recent Activity</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Alerts')}>
          <Text style={styles.viewAllText}>View All</Text>
        </TouchableOpacity>
      </View>
      {activities.length > 0 ? (
        activities.map((activity, index) => (
          <View key={index} style={styles.activityItem}>
            <View style={[styles.activityIcon, { backgroundColor: getActivityColor(activity.type) }]}>
              <Icon name={getActivityIcon(activity.type)} size={16} color={COLORS.white} />
            </View>
            <View style={styles.activityContent}>
              <Text style={styles.activityText}>{activity.description}</Text>
              <Text style={styles.activityTime}>{getTimeAgo(activity.timestamp)}</Text>
            </View>
          </View>
        ))
      ) : (
        <Text style={styles.noDataText}>No recent activity</Text>
      )}
    </View>
  );

  const QuickActionsCard = () => (
    <View style={styles.quickActionsCard}>
      <Text style={styles.cardTitle}>Quick Actions</Text>
      <View style={styles.quickActionsGrid}>
        <TouchableOpacity 
          style={styles.quickAction}
          onPress={() => navigation.navigate('Cameras')}
        >
          <Icon name="videocam" size={24} color={COLORS.primary} />
          <Text style={styles.quickActionText}>Cameras</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={styles.quickAction}
          onPress={() => navigation.navigate('Alerts')}
        >
          <View>
            <Icon name="warning" size={24} color={COLORS.warning} />
            {unreadAlerts > 0 && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{unreadAlerts}</Text>
              </View>
            )}
          </View>
          <Text style={styles.quickActionText}>Alerts</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={styles.quickAction}
          onPress={() => navigation.navigate('Settings')}
        >
          <Icon name="settings" size={24} color={COLORS.gray} />
          <Text style={styles.quickActionText}>Settings</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={styles.quickAction}
          onPress={() => {
            // TODO: Implement emergency action
            Alert.alert('Emergency', 'Emergency protocols activated');
          }}
        >
          <Icon name="emergency" size={24} color={COLORS.error} />
          <Text style={styles.quickActionText}>Emergency</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const getActivityColor = (type) => {
    switch (type) {
      case 'alert': return COLORS.error;
      case 'detection': return COLORS.warning;
      case 'recording': return COLORS.success;
      case 'system': return COLORS.info;
      default: return COLORS.gray;
    }
  };

  const getActivityIcon = (type) => {
    switch (type) {
      case 'alert': return 'warning';
      case 'detection': return 'visibility';
      case 'recording': return 'fiber-manual-record';
      case 'system': return 'settings';
      default: return 'info';
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Icon name="dashboard" size={60} color={COLORS.primary} />
        <Text style={styles.loadingText}>Loading Dashboard...</Text>
      </View>
    );
  }

  const { overview, systemHealth, recentActivities, quickStats } = dashboardData;

  return (
    <ScrollView 
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Dashboard</Text>
        <Text style={styles.headerSubtitle}>Welcome to your surveillance system</Text>
      </View>

      <View style={styles.statsContainer}>
        <StatCard
          title="Active Cameras"
          value={formatNumber(quickStats.activeCameras || 0)}
          icon="videocam"
          color={COLORS.success}
          onPress={() => navigation.navigate('Cameras')}
        />
        <StatCard
          title="Active Alerts"
          value={formatNumber(unreadAlerts)}
          icon="warning"
          color={COLORS.error}
          onPress={() => navigation.navigate('Alerts')}
        />
      </View>

      <View style={styles.statsContainer}>
        <StatCard
          title="Storage Used"
          value={formatFileSize(quickStats.storageUsed || 0)}
          icon="storage"
          color={COLORS.info}
          onPress={() => navigation.navigate('Settings')}
        />
        <StatCard
          title="Recordings Today"
          value={formatNumber(quickStats.recordingsToday || 0)}
          icon="fiber-manual-record"
          color={COLORS.warning}
          onPress={() => navigation.navigate('Cameras')}
        />
      </View>

      <SystemStatusCard status={systemHealth} />
      
      <QuickActionsCard />
      
      <RecentActivityCard activities={recentActivities} />
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
    backgroundColor: COLORS.background,
  },
  loadingText: {
    ...FONTS.body2,
    color: COLORS.text,
    marginTop: SIZES.base,
  },
  header: {
    padding: SIZES.padding,
    backgroundColor: COLORS.surface,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  headerTitle: {
    ...FONTS.h1,
    color: COLORS.text,
  },
  headerSubtitle: {
    ...FONTS.body3,
    color: COLORS.gray,
    marginTop: SIZES.base / 2,
  },
  statsContainer: {
    flexDirection: 'row',
    padding: SIZES.base,
    gap: SIZES.base,
  },
  statCard: {
    flex: 1,
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
    borderLeftWidth: 4,
  },
  statContent: {
    flex: 1,
  },
  statHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.base,
  },
  statTitle: {
    ...FONTS.body3,
    color: COLORS.gray,
  },
  statValue: {
    ...FONTS.h2,
    color: COLORS.text,
  },
  systemStatusCard: {
    margin: SIZES.base,
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
  },
  cardTitle: {
    ...FONTS.h3,
    color: COLORS.text,
    marginBottom: SIZES.padding,
  },
  statusGrid: {
    gap: SIZES.base,
  },
  statusItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: SIZES.base,
  },
  statusText: {
    ...FONTS.body3,
    color: COLORS.text,
  },
  quickActionsCard: {
    margin: SIZES.base,
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
  },
  quickActionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: SIZES.base,
  },
  quickAction: {
    flex: 1,
    minWidth: (width - SIZES.padding * 4) / 2 - SIZES.base,
    aspectRatio: 1,
    backgroundColor: COLORS.background,
    borderRadius: SIZES.radius,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  quickActionText: {
    ...FONTS.caption,
    color: COLORS.text,
    marginTop: SIZES.base / 2,
  },
  badge: {
    position: 'absolute',
    top: -6,
    right: -6,
    backgroundColor: COLORS.error,
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  badgeText: {
    ...FONTS.caption,
    color: COLORS.white,
    fontSize: 10,
  },
  recentActivityCard: {
    margin: SIZES.base,
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
    marginBottom: SIZES.padding * 2,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.padding,
  },
  viewAllText: {
    ...FONTS.body3,
    color: COLORS.primary,
  },
  activityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SIZES.base,
  },
  activityIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SIZES.base,
  },
  activityContent: {
    flex: 1,
  },
  activityText: {
    ...FONTS.body3,
    color: COLORS.text,
  },
  activityTime: {
    ...FONTS.caption,
    color: COLORS.gray,
    marginTop: 2,
  },
  noDataText: {
    ...FONTS.body3,
    color: COLORS.gray,
    textAlign: 'center',
    padding: SIZES.padding,
  },
});

export default DashboardScreen;
