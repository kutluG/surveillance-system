import BackgroundJob from 'react-native-background-job';
import BackgroundTimer from 'react-native-background-timer';
import secureStorage from '../utils/secureStorage';
import { AppState, Platform } from 'react-native';
import NetInfo from '@react-native-netinfo/netinfo';
import { store } from '../store';
import { updateDashboardStats } from '../store/slices/appSlice';
import { fetchCameras } from '../store/slices/camerasSlice';
import { fetchAlerts } from '../store/slices/alertsSlice';
import websocketService from './websocketService';
import pushNotificationService from './pushNotificationService';

class BackgroundTaskService {
  constructor() {
    this.isInitialized = false;
    this.appStateSubscription = null;
    this.networkSubscription = null;
    this.backgroundTimers = new Map();
    this.lastSyncTime = null;
    this.isAppInBackground = false;
  }

  async initialize() {
    if (this.isInitialized) {
      return;
    }

    try {
      await this.setupAppStateHandling();
      await this.setupNetworkMonitoring();
      await this.setupBackgroundSync();
      
      this.isInitialized = true;
      console.log('Background task service initialized successfully');
    } catch (error) {
      console.error('Failed to initialize background task service:', error);
    }
  }

  setupAppStateHandling() {
    this.appStateSubscription = AppState.addEventListener('change', (nextAppState) => {
      console.log('App state changed to:', nextAppState);
      
      if (nextAppState === 'background') {
        this.handleAppBackground();
      } else if (nextAppState === 'active') {
        this.handleAppForeground();
      }
    });
  }

  setupNetworkMonitoring() {
    this.networkSubscription = NetInfo.addEventListener((state) => {
      console.log('Network state changed:', state);
      
      if (state.isConnected && !this.isAppInBackground) {
        this.handleNetworkReconnection();
      }
    });
  }

  async setupBackgroundSync() {
    // Start background job for critical updates
    if (Platform.OS === 'android') {
      BackgroundJob.register({
        jobKey: 'surveillance_sync',
        period: 15000, // 15 seconds
      });

      BackgroundJob.on('surveillance_sync', async () => {
        await this.performBackgroundSync();
      });
    }
  }

  async handleAppBackground() {
    try {
      this.isAppInBackground = true;
      console.log('App entering background, starting background tasks...');

      // Save current state
      await this.saveCurrentState();

      // Start background monitoring
      await this.startBackgroundMonitoring();

      // Reduce WebSocket activity for battery optimization
      websocketService.setBackgroundMode(true);

      // Schedule periodic sync
      this.schedulePeriodicSync();
    } catch (error) {
      console.error('Error handling app background:', error);
    }
  }

  async handleAppForeground() {
    try {
      this.isAppInBackground = false;
      console.log('App entering foreground, resuming normal operation...');

      // Stop background monitoring
      this.stopBackgroundMonitoring();

      // Resume full WebSocket activity
      websocketService.setBackgroundMode(false);

      // Perform immediate sync to catch up on missed data
      await this.performForegroundSync();

      // Clear periodic sync
      this.clearPeriodicSync();
    } catch (error) {
      console.error('Error handling app foreground:', error);
    }
  }

  async handleNetworkReconnection() {
    try {
      console.log('Network reconnected, performing sync...');
      
      // Reconnect WebSocket if needed
      if (!websocketService.isConnected()) {
        await websocketService.connect();
      }

      // Sync missed data
      await this.performNetworkRecoverySync();
    } catch (error) {
      console.error('Error handling network reconnection:', error);
    }
  }
  async saveCurrentState() {
    try {
      const state = store.getState();
      
      const stateToSave = {
        timestamp: new Date().toISOString(),
        cameras: state.cameras,
        alerts: state.alerts,
        app: state.app,
      };

      await secureStorage.setItem('app_background_state', JSON.stringify(stateToSave));
    } catch (error) {
      console.error('Error saving current state:', error);
    }
  }

  async startBackgroundMonitoring() {
    try {
      // Monitor critical alerts
      this.backgroundTimers.set('alertMonitor', 
        BackgroundTimer.setInterval(async () => {
          await this.checkCriticalAlerts();
        }, 30000) // Every 30 seconds
      );

      // Monitor system health
      this.backgroundTimers.set('healthMonitor',
        BackgroundTimer.setInterval(async () => {
          await this.checkSystemHealth();
        }, 60000) // Every minute
      );

      // Sync essential data
      this.backgroundTimers.set('dataSync',
        BackgroundTimer.setInterval(async () => {
          await this.performBackgroundSync();
        }, 120000) // Every 2 minutes
      );
    } catch (error) {
      console.error('Error starting background monitoring:', error);
    }
  }

  stopBackgroundMonitoring() {
    try {
      this.backgroundTimers.forEach((timerId, timerName) => {
        BackgroundTimer.clearInterval(timerId);
        console.log(`Stopped background timer: ${timerName}`);
      });
      
      this.backgroundTimers.clear();
    } catch (error) {
      console.error('Error stopping background monitoring:', error);
    }
  }

  schedulePeriodicSync() {
    try {
      if (Platform.OS === 'android') {
        BackgroundJob.start({
          jobKey: 'surveillance_sync',
        });
      }
    } catch (error) {
      console.error('Error scheduling periodic sync:', error);
    }
  }

  clearPeriodicSync() {
    try {
      if (Platform.OS === 'android') {
        BackgroundJob.stop({
          jobKey: 'surveillance_sync',
        });
      }
    } catch (error) {
      console.error('Error clearing periodic sync:', error);
    }
  }

  async performBackgroundSync() {
    try {
      const networkState = await NetInfo.fetch();
      
      if (!networkState.isConnected) {
        console.log('No network connection, skipping background sync');
        return;
      }

      console.log('Performing background sync...');

      // Sync critical data only
      await this.syncCriticalData();
        this.lastSyncTime = new Date().toISOString();
      await secureStorage.setItem('last_background_sync', this.lastSyncTime);
    } catch (error) {
      console.error('Error performing background sync:', error);
    }
  }

  async performForegroundSync() {
    try {
      console.log('Performing foreground sync...');      // Get last sync time
      const lastSync = await secureStorage.getItem('last_background_sync');
      const lastSyncTime = lastSync ? new Date(lastSync) : null;

      // Sync all data that might have changed
      await this.syncAllData(lastSyncTime);
      
      // Update last sync time
      await secureStorage.setItem('last_foreground_sync', new Date().toISOString());
    } catch (error) {
      console.error('Error performing foreground sync:', error);
    }
  }

  async performNetworkRecoverySync() {
    try {
      console.log('Performing network recovery sync...');
        // Get last successful sync time
      const lastSync = await secureStorage.getItem('last_successful_sync');
      const lastSyncTime = lastSync ? new Date(lastSync) : null;

      // Sync data that might have been missed during network outage
      await this.syncMissedData(lastSyncTime);
      
      await secureStorage.setItem('last_successful_sync', new Date().toISOString());
    } catch (error) {
      console.error('Error performing network recovery sync:', error);
    }
  }

  async syncCriticalData() {
    try {
      // Only sync the most important data in background
      const promises = [
        this.syncCriticalAlerts(),
        this.syncSystemStatus(),
      ];

      await Promise.allSettled(promises);
    } catch (error) {
      console.error('Error syncing critical data:', error);
    }
  }

  async syncAllData(since = null) {
    try {
      const promises = [
        store.dispatch(fetchCameras()),
        store.dispatch(fetchAlerts({ since })),
        this.syncSystemStatus(),
        this.syncRecordings(since),
      ];

      const results = await Promise.allSettled(promises);
      
      // Log any failures
      results.forEach((result, index) => {
        if (result.status === 'rejected') {
          console.error(`Sync failed for item ${index}:`, result.reason);
        }
      });
    } catch (error) {
      console.error('Error syncing all data:', error);
    }
  }

  async syncMissedData(since) {
    try {
      // Sync data that might have been missed during network outage
      await this.syncAllData(since);
      
      // Also check for any push notifications that might have been missed
      await this.syncMissedNotifications(since);
    } catch (error) {
      console.error('Error syncing missed data:', error);
    }
  }

  async syncCriticalAlerts() {
    try {
      // Fetch only high-priority alerts
      const response = await fetch('http://localhost:8002/api/v1/alerts?priority=high&limit=50');
      
      if (!response.ok) {
        throw new Error('Failed to fetch critical alerts');
      }

      const alerts = await response.json();
      
      // Check for new critical alerts and show notifications
      alerts.forEach(alert => {
        if (this.isNewCriticalAlert(alert)) {
          this.showCriticalAlertNotification(alert);
        }
      });
    } catch (error) {
      console.error('Error syncing critical alerts:', error);
    }
  }

  async syncSystemStatus() {
    try {
      const response = await fetch('http://localhost:8001/api/v1/system/status');
      
      if (!response.ok) {
        throw new Error('Failed to fetch system status');
      }

      const status = await response.json();
      store.dispatch(updateDashboardStats(status));
    } catch (error) {
      console.error('Error syncing system status:', error);
    }
  }

  async syncRecordings(since) {
    try {
      const params = new URLSearchParams();
      if (since) {
        params.append('since', since.toISOString());
      }

      const response = await fetch(`http://localhost:8006/api/v1/recordings?${params}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch recordings');
      }      const recordings = await response.json();
      
      // Update recordings in local storage or state
      await secureStorage.setItem('recent_recordings', JSON.stringify(recordings));
    } catch (error) {
      console.error('Error syncing recordings:', error);
    }
  }

  async syncMissedNotifications(since) {
    try {
      // Check for any server-side notifications that might have been missed
      const params = new URLSearchParams();
      if (since) {
        params.append('since', since.toISOString());
      }

      const response = await fetch(`http://localhost:8001/api/v1/notifications/missed?${params}`);
      
      if (!response.ok) {
        return; // Not critical if this fails
      }

      const missedNotifications = await response.json();
      
      // Show missed notifications
      missedNotifications.forEach(notification => {
        pushNotificationService.showLocalNotification(notification);
      });
    } catch (error) {
      console.error('Error syncing missed notifications:', error);
    }
  }

  async checkCriticalAlerts() {
    try {
      // Quick check for any critical alerts that need immediate attention
      const response = await fetch('http://localhost:8002/api/v1/alerts/critical?limit=10');
      
      if (!response.ok) {
        return;
      }

      const criticalAlerts = await response.json();
      
      criticalAlerts.forEach(alert => {
        if (this.shouldNotifyForAlert(alert)) {
          this.showCriticalAlertNotification(alert);
        }
      });
    } catch (error) {
      console.error('Error checking critical alerts:', error);
    }
  }

  async checkSystemHealth() {
    try {
      const response = await fetch('http://localhost:8001/api/v1/system/health');
      
      if (!response.ok) {
        this.showSystemDownNotification();
        return;
      }

      const health = await response.json();
      
      if (health.status !== 'healthy') {
        this.showSystemIssueNotification(health);
      }
    } catch (error) {
      console.error('Error checking system health:', error);
      this.showSystemDownNotification();
    }
  }

  isNewCriticalAlert(alert) {
    // Check if this is a new alert that we haven't seen before
    // This would typically check against stored alert IDs
    return true; // Simplified for now
  }

  shouldNotifyForAlert(alert) {
    // Check if we should notify for this alert based on user preferences
    return alert.priority === 'critical' || alert.priority === 'high';
  }

  showCriticalAlertNotification(alert) {
    pushNotificationService.showLocalNotification({
      title: 'Critical Security Alert',
      body: `${alert.type} detected at ${alert.location}`,
      data: {
        type: 'alert',
        alertId: alert.id,
        priority: alert.priority,
      },
    });
  }

  showSystemDownNotification() {
    pushNotificationService.showLocalNotification({
      title: 'System Alert',
      body: 'Surveillance system appears to be offline',
      data: {
        type: 'system',
        issue: 'offline',
      },
    });
  }

  showSystemIssueNotification(health) {
    pushNotificationService.showLocalNotification({
      title: 'System Health Alert',
      body: `System health: ${health.status}`,
      data: {
        type: 'system',
        issue: 'health',
        status: health.status,
      },
    });
  }

  cleanup() {
    try {
      this.stopBackgroundMonitoring();
      this.clearPeriodicSync();
      
      if (this.appStateSubscription) {
        this.appStateSubscription.remove();
      }
      
      if (this.networkSubscription) {
        this.networkSubscription();
      }
      
      this.isInitialized = false;
    } catch (error) {
      console.error('Error during background service cleanup:', error);
    }
  }
}

export default new BackgroundTaskService();
