import messaging from '@react-native-firebase/messaging';
import notifee, { AndroidImportance, EventType } from '@notifee/react-native';
import secureStorage from '../utils/secureStorage';
import { Platform, Alert, AppState } from 'react-native';

class PushNotificationService {
  constructor() {
    this.isInitialized = false;
    this.fcmToken = null;
    this.unsubscribeTokenRefresh = null;
    this.unsubscribeMessageHandler = null;
    this.unsubscribeBackgroundHandler = null;
  }

  async initialize() {
    if (this.isInitialized) {
      return;
    }

    try {
      await this.requestPermissions();
      await this.setupFCM();
      await this.setupNotifee();
      await this.setupMessageHandlers();
      
      this.isInitialized = true;
      console.log('Push notification service initialized successfully');
    } catch (error) {
      console.error('Failed to initialize push notification service:', error);
    }
  }

  async requestPermissions() {
    try {
      const authStatus = await messaging().requestPermission();
      const enabled =
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;

      if (!enabled) {
        Alert.alert(
          'Notifications Disabled',
          'Please enable notifications to receive security alerts.',
          [{ text: 'OK' }]
        );
        return false;
      }

      // Request Notifee permission for Android 13+
      if (Platform.OS === 'android') {
        await notifee.requestPermission();
      }

      return true;
    } catch (error) {
      console.error('Error requesting notification permissions:', error);
      return false;
    }
  }

  async setupFCM() {
    try {
      // Get FCM token
      this.fcmToken = await messaging().getToken();
      console.log('FCM Token:', this.fcmToken);
        // Store token locally
      await secureStorage.setItem('fcm_token', this.fcmToken);
      
      // Send token to backend
      await this.sendTokenToBackend(this.fcmToken);

      // Listen for token refresh
      this.unsubscribeTokenRefresh = messaging().onTokenRefresh(async (token) => {
        console.log('FCM Token refreshed:', token);
        this.fcmToken = token;
        await secureStorage.setItem('fcm_token', token);
        await this.sendTokenToBackend(token);
      });
    } catch (error) {
      console.error('Error setting up FCM:', error);
    }
  }

  async setupNotifee() {
    try {
      // Create notification channels for Android
      if (Platform.OS === 'android') {
        await notifee.createChannels([
          {
            id: 'alerts',
            name: 'Security Alerts',
            description: 'Critical security alerts and detections',
            importance: AndroidImportance.HIGH,
            sound: 'alert_sound',
            vibration: true,
            badge: true,
          },
          {
            id: 'system',
            name: 'System Notifications',
            description: 'System status and maintenance notifications',
            importance: AndroidImportance.DEFAULT,
            badge: true,
          },
          {
            id: 'recordings',
            name: 'Recording Notifications',
            description: 'New recordings and storage notifications',
            importance: AndroidImportance.LOW,
            badge: false,
          },
        ]);
      }
    } catch (error) {
      console.error('Error setting up Notifee:', error);
    }
  }

  async setupMessageHandlers() {
    try {
      // Foreground message handler
      this.unsubscribeMessageHandler = messaging().onMessage(async (remoteMessage) => {
        console.log('Foreground message received:', remoteMessage);
        await this.displayNotification(remoteMessage);
      });

      // Background message handler
      this.unsubscribeBackgroundHandler = messaging().setBackgroundMessageHandler(
        async (remoteMessage) => {
          console.log('Background message received:', remoteMessage);
          await this.displayNotification(remoteMessage);
        }
      );

      // Notification interaction handler
      notifee.onForegroundEvent(({ type, detail }) => {
        if (type === EventType.PRESS) {
          this.handleNotificationPress(detail.notification);
        }
      });

      notifee.onBackgroundEvent(async ({ type, detail }) => {
        if (type === EventType.PRESS) {
          this.handleNotificationPress(detail.notification);
        }
      });
    } catch (error) {
      console.error('Error setting up message handlers:', error);
    }
  }

  async sendTokenToBackend(token) {
    try {
      // This would integrate with your auth service
      const authToken = await secureStorage.getItem('auth_token');
      if (!authToken) {
        console.log('No auth token available, skipping FCM token registration');
        return;
      }

      // API call to register FCM token
      const response = await fetch('http://localhost:8001/api/v1/notifications/register-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          fcm_token: token,
          platform: Platform.OS,
          app_version: '1.0.0',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to register FCM token');
      }

      console.log('FCM token registered successfully');
    } catch (error) {
      console.error('Error sending token to backend:', error);
    }
  }

  async displayNotification(remoteMessage) {
    try {
      const { notification, data } = remoteMessage;
      
      if (!notification) {
        return;
      }

      const notificationData = {
        title: notification.title,
        body: notification.body,
        data: data || {},
      };

      // Only show notification if app is in foreground
      if (AppState.currentState === 'active') {
        await this.showLocalNotification(notificationData);
      }
    } catch (error) {
      console.error('Error displaying notification:', error);
    }
  }

  async showLocalNotification({ title, body, data = {} }) {
    try {
      const channelId = this.getChannelId(data.type);
      
      const notificationConfig = {
        title,
        body,
        data,
        android: {
          channelId,
          smallIcon: 'ic_notification',
          color: '#007AFF',
          pressAction: {
            id: 'default',
          },
        },
        ios: {
          sound: 'default',
          badge: true,
        },
      };

      // Add action buttons for alert notifications
      if (data.type === 'alert') {
        notificationConfig.android.actions = [
          {
            title: 'View Alert',
            pressAction: {
              id: 'view_alert',
            },
          },
          {
            title: 'Acknowledge',
            pressAction: {
              id: 'acknowledge_alert',
            },
          },
        ];
      }

      await notifee.displayNotification(notificationConfig);
    } catch (error) {
      console.error('Error showing local notification:', error);
    }
  }

  getChannelId(notificationType) {
    switch (notificationType) {
      case 'alert':
      case 'detection':
        return 'alerts';
      case 'recording':
      case 'storage':
        return 'recordings';
      default:
        return 'system';
    }
  }

  handleNotificationPress(notification) {
    try {
      const { data } = notification;
      
      if (!data) {
        return;
      }

      // Handle different notification types
      switch (data.type) {
        case 'alert':
          this.navigateToAlert(data.alertId);
          break;
        case 'camera':
          this.navigateToCamera(data.cameraId);
          break;
        case 'recording':
          this.navigateToRecordings(data.recordingId);
          break;
        default:
          this.navigateToDashboard();
          break;
      }
    } catch (error) {
      console.error('Error handling notification press:', error);
    }
  }

  navigateToAlert(alertId) {
    // This would use your navigation service
    console.log('Navigate to alert:', alertId);
  }

  navigateToCamera(cameraId) {
    console.log('Navigate to camera:', cameraId);
  }

  navigateToRecordings(recordingId) {
    console.log('Navigate to recordings:', recordingId);
  }

  navigateToDashboard() {
    console.log('Navigate to dashboard');
  }

  async scheduleLocalNotification({ title, body, trigger, data = {} }) {
    try {
      const channelId = this.getChannelId(data.type);
      
      await notifee.createTriggerNotification(
        {
          title,
          body,
          data,
          android: {
            channelId,
            smallIcon: 'ic_notification',
          },
        },
        trigger
      );
    } catch (error) {
      console.error('Error scheduling local notification:', error);
    }
  }

  async cancelNotification(notificationId) {
    try {
      await notifee.cancelNotification(notificationId);
    } catch (error) {
      console.error('Error canceling notification:', error);
    }
  }

  async cancelAllNotifications() {
    try {
      await notifee.cancelAllNotifications();
    } catch (error) {
      console.error('Error canceling all notifications:', error);
    }
  }

  async getBadgeCount() {
    try {
      return await notifee.getBadgeCount();
    } catch (error) {
      console.error('Error getting badge count:', error);
      return 0;
    }
  }

  async setBadgeCount(count) {
    try {
      await notifee.setBadgeCount(count);
    } catch (error) {
      console.error('Error setting badge count:', error);
    }
  }

  async checkInitialNotification() {
    try {
      // Check if app was opened from a notification
      const initialNotification = await messaging().getInitialNotification();
      
      if (initialNotification) {
        console.log('App opened from notification:', initialNotification);
        this.handleNotificationPress({ data: initialNotification.data });
      }
    } catch (error) {
      console.error('Error checking initial notification:', error);
    }
  }

  cleanup() {
    try {
      if (this.unsubscribeTokenRefresh) {
        this.unsubscribeTokenRefresh();
      }
      if (this.unsubscribeMessageHandler) {
        this.unsubscribeMessageHandler();
      }
      if (this.unsubscribeBackgroundHandler) {
        this.unsubscribeBackgroundHandler();
      }
      
      this.isInitialized = false;
    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }
}

export default new PushNotificationService();
